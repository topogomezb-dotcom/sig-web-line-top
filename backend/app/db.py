"""
Conexión con PostgreSQL/PostGIS mediante Psycopg 3.

Las credenciales NO están en el código: se leen de variables de entorno
cargadas desde el archivo backend/.env (que no se publica en GitHub).
Ver backend/.env.example para la plantilla.
"""
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Carga backend/.env (ruta relativa a este archivo, funciona desde cualquier carpeta)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PARAMETROS_CONEXION = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "sig_line_top"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}


@contextmanager
def obtener_cursor():
    """Abre una conexión, entrega un cursor que devuelve filas como diccionarios
    y cierra la conexión al terminar la petición."""
    with psycopg.connect(**PARAMETROS_CONEXION, row_factory=dict_row) as conexion:
        with conexion.cursor() as cursor:
            yield cursor


def consultar_uno(sql: str, parametros: dict | None = None) -> dict | None:
    """Ejecuta una consulta parametrizada y devuelve la primera fila."""
    with obtener_cursor() as cur:
        cur.execute(sql, parametros or {})
        return cur.fetchone()


def consultar_todos(sql: str, parametros: dict | None = None) -> list[dict]:
    """Ejecuta una consulta parametrizada y devuelve todas las filas."""
    with obtener_cursor() as cur:
        cur.execute(sql, parametros or {})
        return cur.fetchall()
