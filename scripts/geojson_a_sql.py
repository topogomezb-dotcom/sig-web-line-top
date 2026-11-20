"""
Convierte los GeoJSON descargados del IGAC en el script sql/02_datos_igac.sql.

Uso (desde la carpeta raíz del proyecto):
    python scripts/geojson_a_sql.py datos_fuente/municipios_quindio_igac.geojson datos_fuente/vertices_red_pasiva_quindio.csv

- Municipios: se conservan solo los del Quindío (código DANE que empieza por 63).
- Vértices: GeoJSON o el CSV de la tabla pública de la Red Pasiva (IGAC) filtrada al
  Quindío. El municipio de cada vértice se asigna en PostGIS con ST_Contains.
- Las geometrías se escriben en GeoJSON (EPSG:4326) y se transforman a CTM12
  (EPSG:9377) dentro del INSERT, de modo que la reproyección queda documentada.
"""
import json
import sys
import unicodedata

NOMBRES = {"63001": "Armenia", "63111": "Buenavista", "63130": "Calarcá", "63190": "Circasia",
           "63212": "Córdoba", "63272": "Filandia", "63302": "Génova", "63401": "La Tebaida",
           "63470": "Montenegro", "63548": "Pijao", "63594": "Quimbaya", "63690": "Salento"}


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().upper()
    return "".join(c for c in t if c.isalnum())


def buscar(props, *claves):
    """Devuelve el valor del primer atributo cuyo nombre contenga alguna de las claves."""
    norm = {normalizar(k): v for k, v in props.items()}
    for clave in claves:
        for k, v in norm.items():
            if clave in k and v not in (None, ""):
                return v
    return None


def texto_sql(valor):
    return "NULL" if valor is None else "'" + str(valor).replace("'", "''").strip() + "'"


def codigo_municipio(props):
    for v in props.values():
        s = str(v).strip()
        if len(s) == 5 and s.isdigit() and s.startswith("63"):
            return s
    dpto = str(buscar(props, "DPCODIGO", "DPTOCCDGO", "DPTO") or "")
    mpio = str(buscar(props, "MPCODIGO", "MPIOCCDGO", "MPIO") or "")
    if dpto == "63" and mpio.isdigit():
        return "63" + mpio.zfill(3)[-3:]
    return None


def leer_vertices(ruta):
    """Acepta GeoJSON o el CSV exportado de la tabla de la Red Pasiva (separado por ';')."""
    if not ruta.lower().endswith(".csv"):
        return json.load(open(ruta, encoding="utf-8"))
    import csv
    feats = []
    with open(ruta, encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            tipo = " · ".join(x for x in (r["orden"], r["tipo_materializacion"].replace("_", " ").capitalize()) if x)
            feats.append({"type": "Feature",
                          "geometry": {"type": "Point", "coordinates": [float(r["longitud"]), float(r["latitud"])]},
                          "properties": {"NOMENCLATURA": r["nomenclatura"], "TIPO": tipo,
                                         "ALTURA_ELIPSOIDAL": r["altura_elipsoidal"],
                                         "ESTADO": r["estado"].capitalize()}})
    return {"type": "FeatureCollection", "features": feats}


def geom_sql(geometria):
    gj = json.dumps(geometria, separators=(",", ":"))
    return f"ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON('{gj}'), 4326), 9377)"


def main(ruta_municipios, ruta_vertices, salida="sql/02_datos_igac.sql"):
    mun = json.load(open(ruta_municipios, encoding="utf-8"))
    ver = leer_vertices(ruta_vertices)

    lineas = ["-- =====================================================================",
              "-- Script 02: datos del IGAC — municipios y vértices geodésicos del Quindío",
              f"-- Generado con scripts/geojson_a_sql.py a partir de:",
              f"--   {ruta_municipios}",
              f"--   {ruta_vertices}",
              "-- Las geometrías vienen en EPSG:4326 y se transforman a CTM12 (EPSG:9377).",
              "-- =====================================================================", "",
              "BEGIN;", "", "-- Municipios del Quindío (polígonos)"]
    vistos = set()
    for f in mun["features"]:
        cod = codigo_municipio(f["properties"])
        if cod not in NOMBRES or cod in vistos or not f.get("geometry"):
            continue
        vistos.add(cod)
        lineas.append(f"INSERT INTO municipios (cod_dane, nombre, departamento, geom) VALUES "
                      f"('{cod}', '{NOMBRES[cod]}', 'Quindío', "
                      f"ST_Multi(ST_MakeValid({geom_sql(f['geometry'])})));")
    faltan = set(NOMBRES) - vistos
    if faltan:
        print("ADVERTENCIA: faltan municipios", faltan)

    lineas += ["", "-- Vértices geodésicos (puntos). Se cargan en una tabla temporal y el",
               "-- municipio de cada uno se asigna espacialmente (ST_Contains).",
               "CREATE TEMP TABLE tmp_vertices (LIKE vertices_geodesicos INCLUDING DEFAULTS) ON COMMIT DROP;"]
    usados = set()
    for f in ver["features"]:
        p, g = f["properties"], f.get("geometry")
        if not g or g.get("type") != "Point":
            continue
        nom = buscar(p, "NOMENCLATURA", "NOMENCL", "CODIGO", "NOMBRE")
        if nom is None or str(nom) in usados:
            continue
        usados.add(str(nom))
        altura = buscar(p, "ALTURAELIPSOIDAL", "ALTURAELIP", "ALTELIP")
        try:
            altura = round(float(str(altura).replace(",", ".")), 3) if altura is not None else None
        except ValueError:
            altura = None
        tipo = buscar(p, "TIPO", "ORDEN", "CLASE") or "Red Pasiva MAGNA-SIRGAS"
        estado = buscar(p, "ESTADO")
        nombre = buscar(p, "NOMBREVERTICE", "NOMBREESTACION", "SITIO", "NOMBREMUNICIPIO")
        lineas.append("INSERT INTO tmp_vertices (nomenclatura, nombre, tipo, altura_elipsoidal, estado, geom) VALUES ("
                      f"{texto_sql(nom)}, {texto_sql(nombre)}, {texto_sql(tipo)}, "
                      f"{'NULL' if altura is None else altura}, {texto_sql(estado)}, "
                      f"ST_Force2D({geom_sql(g)}));")

    lineas += ["",
               "INSERT INTO vertices_geodesicos (nomenclatura, nombre, tipo, altura_elipsoidal, estado, municipio_cod, geom)",
               "SELECT t.nomenclatura, t.nombre, t.tipo, t.altura_elipsoidal, t.estado, m.cod_dane, t.geom",
               "FROM tmp_vertices t",
               "LEFT JOIN municipios m ON ST_Contains(m.geom, t.geom);   -- asignación espacial del municipio",
               "", "COMMIT;", ""]
    open(salida, "w", encoding="utf-8").write("\n".join(lineas))
    print(f"{salida}: {len(vistos)} municipios, {len(usados)} vértices leídos (se filtran al Quindío al cargar)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
