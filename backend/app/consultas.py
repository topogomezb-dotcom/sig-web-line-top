"""
Consultas SQL/PostGIS ejecutadas por la API.

Todas las consultas que reciben valores del usuario usan parámetros con
nombre de Psycopg  —%(nombre)s—  y NUNCA concatenan texto del usuario
dentro de la sentencia SQL (prevención de inyección SQL).

Sistema de referencia:
  * Las geometrías se ALMACENAN en EPSG:9377 (MAGNA-SIRGAS / Origen-Nacional,
    CTM12), proyección plana oficial de Colombia con unidades en METROS.
    Por eso ST_Area, ST_Distance, ST_DWithin y ST_Perimeter entregan
    directamente m² y m.
  * Para enviarlas a Leaflet se transforman a EPSG:4326 (lat/lon WGS84),
    que es lo que exige el estándar GeoJSON (RFC 7946).
"""

# ---------------------------------------------------------------------
# Estado de la conexión (evidencia de integración)
# ---------------------------------------------------------------------
SQL_ESTADO = """
SELECT current_database()                         AS base_de_datos,
       split_part(version(), ',', 1)              AS postgresql,
       postgis_lib_version()                      AS postgis,
       (SELECT COUNT(*) FROM municipios)          AS municipios,
       (SELECT COUNT(*) FROM vertices_geodesicos) AS vertices_geodesicos,
       (SELECT COUNT(*) FROM clientes)            AS clientes,
       (SELECT COUNT(*) FROM proyectos)           AS proyectos,
       (SELECT COUNT(*) FROM equipos)             AS equipos,
       (SELECT COUNT(*) FROM proyecto_equipo)     AS proyecto_equipo;
"""

# ---------------------------------------------------------------------
# Catálogos para llenar los filtros del visor (salen de la BD, no del HTML)
# ---------------------------------------------------------------------
SQL_CATALOGOS = """
SELECT
  (SELECT json_agg(json_build_object('cod_dane', cod_dane, 'nombre', nombre) ORDER BY nombre)
     FROM municipios)                                                   AS municipios,
  (SELECT json_agg(DISTINCT tipo_servicio ORDER BY tipo_servicio) FROM proyectos) AS tipos_servicio,
  (SELECT json_agg(DISTINCT estado ORDER BY estado) FROM proyectos)    AS estados,
  (SELECT json_agg(DISTINCT EXTRACT(YEAR FROM fecha)::int
                   ORDER BY EXTRACT(YEAR FROM fecha)::int) FROM proyectos) AS anios;
"""

# ---------------------------------------------------------------------
# F1. Visualización: capas como FeatureCollection GeoJSON construida en PostGIS
# ---------------------------------------------------------------------
SQL_MUNICIPIOS_GEOJSON = """
SELECT json_build_object(
  'type', 'FeatureCollection',
  'features', COALESCE(json_agg(json_build_object(
      'type', 'Feature',
      'id', m.cod_dane,
      'geometry', ST_AsGeoJSON(
                    ST_Transform(ST_SimplifyPreserveTopology(m.geom, 5), 4326), 6)::json,
      'properties', json_build_object(
          'cod_dane', m.cod_dane,
          'nombre',   m.nombre,
          'area_km2', ROUND((ST_Area(m.geom) / 1000000)::numeric, 2))
  ) ORDER BY m.nombre), '[]'::json)
) AS geojson
FROM municipios m;
"""

SQL_VERTICES_GEOJSON = """
SELECT json_build_object(
  'type', 'FeatureCollection',
  'features', COALESCE(json_agg(json_build_object(
      'type', 'Feature',
      'id', v.id,
      'geometry', ST_AsGeoJSON(ST_Transform(v.geom, 4326), 7)::json,
      'properties', json_build_object(
          'id', v.id,
          'nomenclatura', v.nomenclatura,
          'nombre', v.nombre,
          'tipo', v.tipo,
          'estado', v.estado,
          'altura_elipsoidal', v.altura_elipsoidal,
          'municipio', m.nombre,
          'este_ctm12',  ROUND(ST_X(v.geom)::numeric, 3),
          'norte_ctm12', ROUND(ST_Y(v.geom)::numeric, 3))
  ) ORDER BY v.nomenclatura), '[]'::json)
) AS geojson
FROM vertices_geodesicos v
LEFT JOIN municipios m ON m.cod_dane = v.municipio_cod;
"""

# Proyectos con filtros opcionales (F1 + F2 búsqueda + F4 filtro combinado).
# Un parámetro en NULL desactiva ese filtro.
SQL_PROYECTOS_GEOJSON = """
WITH filtrados AS (
  SELECT p.id, p.codigo, p.nombre, p.tipo_servicio,
         to_char(p.fecha, 'YYYY-MM-DD') AS fecha, p.estado,
         c.nombre AS cliente, m.nombre AS municipio, p.municipio_cod,
         ROUND((ST_Area(p.geom) / 10000)::numeric, 2) AS area_ha,
         p.geom
  FROM proyectos p
  JOIN clientes   c ON c.id = p.cliente_id
  JOIN municipios m ON m.cod_dane = p.municipio_cod
  WHERE (%(municipio)s::varchar IS NULL OR p.municipio_cod = %(municipio)s)
    AND (%(tipo)s::varchar      IS NULL OR p.tipo_servicio = %(tipo)s)
    AND (%(estado)s::varchar    IS NULL OR p.estado = %(estado)s)
    AND (%(anio)s::int          IS NULL OR EXTRACT(YEAR FROM p.fecha) = %(anio)s)
    AND (%(buscar)s::varchar    IS NULL
         OR p.nombre ILIKE %(buscar)s OR p.codigo ILIKE %(buscar)s OR c.nombre ILIKE %(buscar)s)
)
SELECT json_build_object(
  'type', 'FeatureCollection',
  'features', COALESCE(json_agg(json_build_object(
      'type', 'Feature',
      'id', f.id,
      'geometry', ST_AsGeoJSON(ST_Transform(f.geom, 4326), 7)::json,
      'properties', to_jsonb(f) - 'geom'
  ) ORDER BY f.codigo), '[]'::json)
) AS geojson
FROM filtrados f;
"""

# ---------------------------------------------------------------------
# F2. Consulta de atributos: ficha completa de un proyecto (JOIN de 5 tablas)
# ---------------------------------------------------------------------
SQL_PROYECTO_DETALLE = """
SELECT p.id, p.codigo, p.nombre, p.tipo_servicio,
       to_char(p.fecha, 'YYYY-MM-DD') AS fecha, p.estado,
       json_build_object('id', c.id, 'nombre', c.nombre, 'tipo', c.tipo_cliente) AS cliente,
       m.cod_dane, m.nombre AS municipio,
       -- Área plana en CTM12 (m² → ha) y área sobre el elipsoide GRS80 (geography)
       ROUND((ST_Area(p.geom) / 10000)::numeric, 4)                               AS area_ctm12_ha,
       ROUND((ST_Area(ST_Transform(p.geom, 4326)::geography) / 10000)::numeric, 4) AS area_elipsoidal_ha,
       ROUND(ST_Perimeter(p.geom)::numeric, 2)                                    AS perimetro_m,
       ST_NPoints(p.geom) - 1                                                     AS vertices_poligono,
       ROUND(ST_X(ST_Centroid(p.geom))::numeric, 3)                               AS centroide_este,
       ROUND(ST_Y(ST_Centroid(p.geom))::numeric, 3)                               AS centroide_norte,
       ROUND(ST_Y(ST_Transform(ST_Centroid(p.geom), 4326))::numeric, 7)           AS centroide_lat,
       ROUND(ST_X(ST_Transform(ST_Centroid(p.geom), 4326))::numeric, 7)           AS centroide_lon,
       ST_Covers(m.geom, p.geom)                                                  AS dentro_del_municipio,
       COALESCE((
         SELECT json_agg(json_build_object('tipo', e.tipo, 'marca', e.marca,
                                           'modelo', e.modelo, 'codigo_inventario', e.codigo_inventario)
                         ORDER BY e.tipo)
         FROM proyecto_equipo pe
         JOIN equipos e ON e.id = pe.equipo_id
         WHERE pe.proyecto_id = p.id), '[]'::json)                                AS equipos
FROM proyectos p
JOIN clientes   c ON c.id = p.cliente_id
JOIN municipios m ON m.cod_dane = p.municipio_cod
WHERE p.id = %(id)s;
"""

# ---------------------------------------------------------------------
# F3. Consulta espacial: vértices geodésicos IGAC más cercanos a un proyecto
#     ST_DWithin  -> filtra los vértices a menos de radio_m metros (usa índice GiST)
#     ST_Distance -> distancia mínima polígono–punto en metros (CTM12)
#     ST_ShortestLine -> línea que materializa esa distancia mínima (se dibuja en Leaflet)
#     ST_Azimuth  -> azimut de cuadrícula desde el centroide del proyecto al vértice
# ---------------------------------------------------------------------
SQL_VERTICES_CERCANOS = """
WITH cercanos AS (
  SELECT v.id, v.nomenclatura, v.nombre, v.tipo, mv.nombre AS municipio,
         ROUND(ST_Distance(p.geom, v.geom)::numeric, 2)                          AS distancia_m,
         ROUND(degrees(ST_Azimuth(ST_Centroid(p.geom), v.geom))::numeric, 4)     AS azimut_grados,
         ROUND(ST_X(v.geom)::numeric, 3)                                         AS este_ctm12,
         ROUND(ST_Y(v.geom)::numeric, 3)                                         AS norte_ctm12,
         ROUND(ST_Y(ST_Transform(v.geom, 4326))::numeric, 7)                     AS lat,
         ROUND(ST_X(ST_Transform(v.geom, 4326))::numeric, 7)                     AS lon,
         ST_ShortestLine(p.geom, v.geom)                                         AS linea
  FROM proyectos p
  JOIN vertices_geodesicos v ON ST_DWithin(p.geom, v.geom, %(radio_m)s)
  LEFT JOIN municipios mv ON mv.cod_dane = v.municipio_cod
  WHERE p.id = %(id)s
  ORDER BY ST_Distance(p.geom, v.geom)
  LIMIT %(limite)s
)
SELECT json_build_object(
  'type', 'FeatureCollection',
  'features', COALESCE(json_agg(json_build_object(
      'type', 'Feature',
      'geometry', ST_AsGeoJSON(ST_Transform(c.linea, 4326), 7)::json,
      'properties', to_jsonb(c) - 'linea'
  ) ORDER BY c.distancia_m), '[]'::json)
) AS geojson
FROM cercanos c;
"""

# ---------------------------------------------------------------------
# F4. Funcionalidad complementaria: mapa temático por municipio.
#     Hectáreas levantadas por municipio según un filtro combinado
#     (tipo de servicio + estado + año). Se usa una SUPERPOSICIÓN espacial
#     (ST_Intersects + ST_Intersection), de modo que si un proyecto cruza
#     un límite municipal, su área se reparte entre ambos municipios.
# ---------------------------------------------------------------------
SQL_ESTADISTICAS_MUNICIPIOS = """
SELECT m.cod_dane, m.nombre,
       COUNT(p.id)                                                         AS num_proyectos,
       COALESCE(ROUND((SUM(ST_Area(ST_Intersection(p.geom, m.geom))) / 10000)::numeric, 2), 0)
                                                                           AS area_levantada_ha,
       ROUND((ST_Area(m.geom) / 10000)::numeric, 1)                        AS area_municipio_ha
FROM municipios m
LEFT JOIN proyectos p
       ON ST_Intersects(p.geom, m.geom)
      AND (%(tipo)s::varchar   IS NULL OR p.tipo_servicio = %(tipo)s)
      AND (%(estado)s::varchar IS NULL OR p.estado = %(estado)s)
      AND (%(anio)s::int       IS NULL OR EXTRACT(YEAR FROM p.fecha) = %(anio)s)
GROUP BY m.cod_dane, m.nombre, m.geom
ORDER BY area_levantada_ha DESC, m.nombre;
"""

# ---------------------------------------------------------------------
# F5. Punto de amarre: el usuario hace clic en el mapa y PostGIS devuelve
#     las coordenadas CTM12 del punto, el municipio que lo contiene
#     (ST_Contains), el proyecto donde cae (si existe) y los 3 vértices
#     geodésicos más cercanos (operador KNN <-> ) con distancia y azimut.
# ---------------------------------------------------------------------
SQL_PUNTO_AMARRE = """
WITH pt AS (
  SELECT ST_Transform(ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326), 9377) AS g
)
SELECT ROUND(ST_X(pt.g)::numeric, 3) AS este_ctm12,
       ROUND(ST_Y(pt.g)::numeric, 3) AS norte_ctm12,
       (SELECT json_build_object('cod_dane', m.cod_dane, 'nombre', m.nombre)
          FROM municipios m WHERE ST_Contains(m.geom, pt.g) LIMIT 1)          AS municipio,
       (SELECT json_build_object('id', p.id, 'codigo', p.codigo, 'nombre', p.nombre)
          FROM proyectos p WHERE ST_Contains(p.geom, pt.g) LIMIT 1)           AS proyecto,
       (SELECT COALESCE(json_agg(x ORDER BY x.distancia_m), '[]'::json) FROM (
          SELECT v.nomenclatura, v.nombre,
                 ROUND(ST_Distance(v.geom, pt.g)::numeric, 2)                AS distancia_m,
                 ROUND(degrees(ST_Azimuth(pt.g, v.geom))::numeric, 4)        AS azimut_grados,
                 ROUND(ST_Y(ST_Transform(v.geom, 4326))::numeric, 7)         AS lat,
                 ROUND(ST_X(ST_Transform(v.geom, 4326))::numeric, 7)         AS lon
          FROM vertices_geodesicos v
          ORDER BY v.geom <-> pt.g
          LIMIT 3) x)                                                         AS vertices_cercanos
FROM pt;
"""
