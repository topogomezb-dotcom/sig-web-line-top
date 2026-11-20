"""
API del SIG Web Agro Medición Line Top (FastAPI).

Ejecutar desde la carpeta backend/:
    uvicorn app.main:app --reload

Documentación interactiva de los endpoints: http://127.0.0.1:8000/docs
Visor web (frontend servido por la misma API): http://127.0.0.1:8000/
"""
from pathlib import Path
from typing import Optional

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import consultas as q
from .db import consultar_uno, consultar_todos

app = FastAPI(
    title="API SIG Web — Agro Medición Line Top",
    description="Servicios web sobre la geodatabase PostgreSQL/PostGIS de proyectos "
                "topográficos en el Quindío (CTM12, EPSG:9377).",
    version="1.0.0",
)

# CORS: permite abrir el frontend también con Live Server (puerto 5500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.exception_handler(psycopg.OperationalError)
async def error_conexion(_request, exc):
    """Si PostgreSQL no responde, se devuelve un JSON claro en vez de un error 500 genérico."""
    return JSONResponse(status_code=503,
                        content={"detail": "No hay conexión con PostgreSQL/PostGIS",
                                 "error": str(exc).strip()})


def _vacio_a_none(valor: Optional[str]) -> Optional[str]:
    """Los <select> del visor envían '' cuando no hay filtro; se convierte a NULL."""
    return valor if valor not in (None, "") else None


# ---------------------------------------------------------------------
# Estado y catálogos
# ---------------------------------------------------------------------
@app.get("/api/estado", tags=["Estado"])
def estado():
    """Verifica la conexión con PostgreSQL/PostGIS y cuenta los registros de cada tabla."""
    return consultar_uno(q.SQL_ESTADO)


@app.get("/api/catalogos", tags=["Estado"])
def catalogos():
    """Listas para los filtros del visor (municipios, tipos de servicio, estados y años)."""
    return consultar_uno(q.SQL_CATALOGOS)


# ---------------------------------------------------------------------
# F1. Visualización geográfica
# ---------------------------------------------------------------------
@app.get("/api/municipios", tags=["F1 Visualización"])
def municipios():
    """Límites municipales del Quindío (polígonos) como GeoJSON."""
    return consultar_uno(q.SQL_MUNICIPIOS_GEOJSON)["geojson"]


@app.get("/api/vertices", tags=["F1 Visualización"])
def vertices():
    """Vértices geodésicos del IGAC (puntos) como GeoJSON."""
    return consultar_uno(q.SQL_VERTICES_GEOJSON)["geojson"]


@app.get("/api/proyectos", tags=["F1 Visualización", "F2 Consulta de atributos"])
def proyectos(
    municipio: Optional[str] = Query(None, description="Código DANE del municipio, ej. 63001"),
    tipo: Optional[str] = Query(None, description="Tipo de servicio"),
    estado: Optional[str] = Query(None, description="Cotizado | En ejecución | Terminado"),
    anio: Optional[int] = Query(None, ge=2000, le=2100, description="Año del proyecto"),
    buscar: Optional[str] = Query(None, max_length=60,
                                  description="Texto a buscar en código, nombre o cliente"),
):
    """Proyectos topográficos (polígonos) como GeoJSON, con filtros opcionales."""
    buscar = _vacio_a_none(buscar)
    parametros = {
        "municipio": _vacio_a_none(municipio),
        "tipo": _vacio_a_none(tipo),
        "estado": _vacio_a_none(estado),
        "anio": anio,
        # El comodín % se agrega aquí, en Python; el texto viaja como parámetro.
        "buscar": f"%{buscar.strip()}%" if buscar else None,
    }
    return consultar_uno(q.SQL_PROYECTOS_GEOJSON, parametros)["geojson"]


# ---------------------------------------------------------------------
# F2. Consulta de atributos
# ---------------------------------------------------------------------
@app.get("/api/proyectos/{proyecto_id}", tags=["F2 Consulta de atributos"])
def proyecto_detalle(proyecto_id: int):
    """Ficha de un proyecto: cliente, municipio, equipos usados, área, perímetro y centroide."""
    fila = consultar_uno(q.SQL_PROYECTO_DETALLE, {"id": proyecto_id})
    if fila is None:
        raise HTTPException(status_code=404, detail=f"No existe el proyecto {proyecto_id}")
    return fila


# ---------------------------------------------------------------------
# F3. Consulta espacial
# ---------------------------------------------------------------------
@app.get("/api/proyectos/{proyecto_id}/vertices-cercanos", tags=["F3 Consulta espacial"])
def vertices_cercanos(
    proyecto_id: int,
    radio_m: float = Query(10000, gt=0, le=100000, description="Radio de búsqueda en metros"),
    limite: int = Query(5, ge=1, le=20, description="Número máximo de vértices"),
):
    """Vértices geodésicos a menos de `radio_m` metros del proyecto (ST_DWithin + ST_Distance
    en CTM12). Cada resultado es la línea más corta proyecto→vértice (ST_ShortestLine)."""
    if consultar_uno("SELECT 1 AS existe FROM proyectos WHERE id = %(id)s", {"id": proyecto_id}) is None:
        raise HTTPException(status_code=404, detail=f"No existe el proyecto {proyecto_id}")
    parametros = {"id": proyecto_id, "radio_m": radio_m, "limite": limite}
    return consultar_uno(q.SQL_VERTICES_CERCANOS, parametros)["geojson"]


# ---------------------------------------------------------------------
# F4. Mapa temático derivado de un filtro combinado
# ---------------------------------------------------------------------
@app.get("/api/estadisticas/municipios", tags=["F4 Mapa temático"])
def estadisticas_municipios(
    tipo: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    anio: Optional[int] = Query(None, ge=2000, le=2100),
):
    """Número de proyectos y hectáreas levantadas por municipio (ST_Intersection),
    según tipo de servicio, estado y año."""
    parametros = {"tipo": _vacio_a_none(tipo), "estado": _vacio_a_none(estado), "anio": anio}
    return consultar_todos(q.SQL_ESTADISTICAS_MUNICIPIOS, parametros)


# ---------------------------------------------------------------------
# F5. Punto de amarre (clic en el mapa)
# ---------------------------------------------------------------------
@app.get("/api/punto", tags=["F5 Punto de amarre"])
def punto_amarre(
    lat: float = Query(..., ge=-5, le=14, description="Latitud WGS84"),
    lon: float = Query(..., ge=-82, le=-66, description="Longitud WGS84"),
):
    """Coordenadas CTM12 del punto, municipio y proyecto que lo contienen,
    y los 3 vértices geodésicos más cercanos con distancia y azimut."""
    return consultar_uno(q.SQL_PUNTO_AMARRE, {"lat": lat, "lon": lon})


# ---------------------------------------------------------------------
# Frontend: la API también sirve los archivos del visor (carpeta frontend/)
# Se monta al final para que no tape las rutas /api/...
# ---------------------------------------------------------------------
CARPETA_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
if CARPETA_FRONTEND.exists():
    app.mount("/", StaticFiles(directory=CARPETA_FRONTEND, html=True), name="frontend")
