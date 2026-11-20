-- =====================================================================
-- Script 04: consultas de verificación (ejecutar en pgAdmin o psql)
-- Sirven para contrastar, de forma independiente, los resultados de la
-- base de datos con lo que muestra el visor (apartado 6 de la tarea).
-- =====================================================================

-- ---------------------------------------------------------------
-- V0. Integridad: conteo de registros y claves foráneas
-- ---------------------------------------------------------------
SELECT 'municipios' AS tabla, COUNT(*) FROM municipios
UNION ALL SELECT 'vertices_geodesicos', COUNT(*) FROM vertices_geodesicos
UNION ALL SELECT 'clientes', COUNT(*) FROM clientes
UNION ALL SELECT 'proyectos', COUNT(*) FROM proyectos
UNION ALL SELECT 'equipos', COUNT(*) FROM equipos
UNION ALL SELECT 'proyecto_equipo', COUNT(*) FROM proyecto_equipo;

SELECT conrelid::regclass AS tabla, conname AS restriccion, pg_get_constraintdef(oid) AS definicion
FROM pg_constraint
WHERE contype = 'f' AND connamespace = 'public'::regnamespace
ORDER BY 1;

-- Sistema de referencia y tipo de geometría de cada capa
SELECT f_table_name AS tabla, f_geometry_column AS columna, type AS geometria, srid
FROM geometry_columns ORDER BY 1;

-- Prueba de integridad referencial: debe FALLAR (no existe el cliente 999)
-- INSERT INTO proyectos (codigo, nombre, tipo_servicio, fecha, cliente_id, municipio_cod, geom)
-- VALUES ('X', 'Prueba', 'Deslinde predial', now(), 999, '63001',
--         ST_GeomFromText('POLYGON((4700000 2060000,4700100 2060000,4700100 2060100,4700000 2060000))', 9377));

-- ---------------------------------------------------------------
-- V1 (F2). Ficha del proyecto LT-2024-003  → comparar con /api/proyectos/3
-- ---------------------------------------------------------------
SELECT p.codigo, p.nombre, c.nombre AS cliente, m.nombre AS municipio,
       ROUND((ST_Area(p.geom) / 10000)::numeric, 4)                                 AS area_ctm12_ha,
       ROUND((ST_Area(ST_Transform(p.geom, 4326)::geography) / 10000)::numeric, 4)  AS area_elipsoidal_ha,
       ROUND(ST_Perimeter(p.geom)::numeric, 2)                                      AS perimetro_m,
       string_agg(e.tipo || ' ' || e.marca || ' ' || e.modelo, ' | ')               AS equipos
FROM proyectos p
JOIN clientes c         ON c.id = p.cliente_id
JOIN municipios m       ON m.cod_dane = p.municipio_cod
JOIN proyecto_equipo pe ON pe.proyecto_id = p.id
JOIN equipos e          ON e.id = pe.equipo_id
WHERE p.codigo = 'LT-2024-003'
GROUP BY p.id, c.nombre, m.nombre;

-- ---------------------------------------------------------------
-- V2 (F3). Vértices geodésicos a menos de 10 km del proyecto LT-2024-003
--          → comparar con el botón "Buscar vértices cercanos" del visor
--            o con /api/proyectos/3/vertices-cercanos?radio_m=10000&limite=5
-- ---------------------------------------------------------------
SELECT v.nomenclatura,
       ROUND(ST_Distance(p.geom, v.geom)::numeric, 2)                         AS distancia_m,
       ROUND(degrees(ST_Azimuth(ST_Centroid(p.geom), v.geom))::numeric, 4)    AS azimut_grados
FROM proyectos p
JOIN vertices_geodesicos v ON ST_DWithin(p.geom, v.geom, 10000)
WHERE p.codigo = 'LT-2024-003'
ORDER BY distancia_m
LIMIT 5;

-- Comprobación de unidades: la misma distancia calculada sobre el elipsoide (geography)
-- debe diferir muy poco de la distancia plana en CTM12 (factor de escala de la proyección).
SELECT v.nomenclatura,
       ROUND(ST_Distance(p.geom, v.geom)::numeric, 2)                                         AS dist_ctm12_m,
       ROUND(ST_Distance(ST_Transform(p.geom, 4326)::geography,
                         ST_Transform(v.geom, 4326)::geography)::numeric, 2)                  AS dist_elipsoidal_m
FROM proyectos p
JOIN vertices_geodesicos v ON ST_DWithin(p.geom, v.geom, 10000)
WHERE p.codigo = 'LT-2024-003'
ORDER BY 2
LIMIT 5;

-- ---------------------------------------------------------------
-- V3 (F4). Hectáreas levantadas por municipio en proyectos de Agricultura de precisión
--          → comparar con la tabla del "Mapa temático" del visor
-- ---------------------------------------------------------------
SELECT m.nombre,
       COUNT(p.id) AS num_proyectos,
       ROUND((SUM(ST_Area(ST_Intersection(p.geom, m.geom))) / 10000)::numeric, 2) AS area_levantada_ha
FROM municipios m
JOIN proyectos p ON ST_Intersects(p.geom, m.geom)
WHERE p.tipo_servicio = 'Agricultura de precisión'
GROUP BY m.nombre
ORDER BY area_levantada_ha DESC;

-- ---------------------------------------------------------------
-- V4 (F5). Punto de amarre para un punto en Armenia (lat 4.535, lon -75.69)
--          → comparar con /api/punto?lat=4.535&lon=-75.69
-- ---------------------------------------------------------------
WITH pt AS (SELECT ST_Transform(ST_SetSRID(ST_MakePoint(-75.69, 4.535), 4326), 9377) AS g)
SELECT ROUND(ST_X(pt.g)::numeric, 3) AS este_ctm12,
       ROUND(ST_Y(pt.g)::numeric, 3) AS norte_ctm12,
       (SELECT nombre FROM municipios m WHERE ST_Contains(m.geom, pt.g)) AS municipio
FROM pt;

-- ---------------------------------------------------------------
-- V5. Control de calidad: proyectos que NO quedan dentro de su municipio
--     (debe devolver 0 filas, o proyectos que cruzan un límite municipal)
-- ---------------------------------------------------------------
SELECT p.codigo, m.nombre AS municipio_asignado
FROM proyectos p JOIN municipios m ON m.cod_dane = p.municipio_cod
WHERE NOT ST_Covers(m.geom, p.geom);
