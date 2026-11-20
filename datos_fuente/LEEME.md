# Datos fuente (IGAC)

| Archivo | Contenido | Cómo se obtuvo |
|---|---|---|
| `municipios_quindio_igac.geojson` | Límites de los 12 municipios del Quindío | Consulta al servicio ArcGIS REST del geoportal del Ministerio de Ambiente, que publica los límites de entidades territoriales del IGAC: `https://geo.minambiente.gov.co/server/rest/services/MADS_Ministro/MADS_Geoportal_Lec/MapServer/1/query?where=dpcodigo%3D%2763%27&outFields=mpcodigo,mpnombre,depto&outSR=4326&f=geojson` |
| `vertices_red_pasiva_quindio.csv` | 157 vértices de la Red Pasiva GNSS MAGNA-SIRGAS en el Quindío | Tabla pública del portal de la Red Geodésica Nacional del IGAC (<https://redgeodesica.igac.gov.co/redes/red_pasiva.html>), filtrada por departamento = Quindío. Consultada el 19/11/2026 |

## Conversión a la geodatabase

```bash
python scripts/geojson_a_sql.py datos_fuente/municipios_quindio_igac.geojson datos_fuente/vertices_red_pasiva_quindio.csv
```

El script genera `sql/02_datos_igac.sql`:
- Cada geometría se escribe en GeoJSON (EPSG:4326) y se transforma a CTM12 con `ST_Transform(..., 9377)` dentro del `INSERT`.
- El municipio de cada vértice se asigna con `ST_Contains`.

Quien clone el repositorio no necesita repetir este paso: basta con ejecutar el script SQL.
