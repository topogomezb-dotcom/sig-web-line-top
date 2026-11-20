@echo off
chcp 65001 >nul
title Visor SIG Line Top
REM =====================================================================
REM  Inicia todo el proyecto en Windows con doble clic:
REM   1. Crea (solo la primera vez) una instancia local de PostgreSQL 16
REM      en la carpeta del usuario, puerto 5433, solo accesible desde este equipo.
REM   2. Crea la base sig_line_top y ejecuta los scripts 01, 02 y 03 (solo la primera vez).
REM   3. Instala las librerias de Python y arranca la API + visor en http://127.0.0.1:8000/
REM  Deje esta ventana abierta mientras usa el visor.
REM =====================================================================
cd /d "%~dp0"
set "PGBIN=C:\Program Files\PostgreSQL\16\bin"
set "PGDATA=%USERPROFILE%\sig_line_top_pgdata"
set PGPORT=5433
set PGCLIENTENCODING=UTF8

REM Variables que lee backend\app\db.py (no se necesita archivo .env)
set DB_HOST=localhost
set DB_PORT=5433
set DB_NAME=sig_line_top
set DB_USER=postgres
set DB_PASSWORD=

if not exist "%PGDATA%\PG_VERSION" (
  echo [1/4] Creando instancia local de PostgreSQL en %PGDATA% ...
  "%PGBIN%\initdb.exe" -D "%PGDATA%" -U postgres -A trust -E UTF8 --locale=C
)

echo [2/4] Iniciando PostgreSQL en el puerto 5433 ...
"%PGBIN%\pg_ctl.exe" -D "%PGDATA%" -o "-p 5433" -l "%PGDATA%\servidor.log" -w start

"%PGBIN%\psql.exe" -h localhost -p 5433 -U postgres -d sig_line_top -c "SELECT 1" >nul 2>nul
if errorlevel 1 (
  echo [3/4] Creando la base sig_line_top y cargando los scripts SQL ...
  "%PGBIN%\createdb.exe" -h localhost -p 5433 -U postgres sig_line_top
  "%PGBIN%\psql.exe" -h localhost -p 5433 -U postgres -d sig_line_top -q -v ON_ERROR_STOP=1 -f "sql\01_estructura.sql"
  "%PGBIN%\psql.exe" -h localhost -p 5433 -U postgres -d sig_line_top -q -v ON_ERROR_STOP=1 -f "sql\02_datos_igac.sql"
  "%PGBIN%\psql.exe" -h localhost -p 5433 -U postgres -d sig_line_top -q -v ON_ERROR_STOP=1 -f "sql\03_datos_empresa.sql"
) else (
  echo [3/4] La base sig_line_top ya existe.
)

echo [4/4] Instalando librerias de Python e iniciando la API ...
set PY=python
where python >nul 2>nul || set PY=py
%PY% -m pip install -q -r backend\requirements.txt
cd backend
start "" cmd /c "timeout /t 6 >nul & start http://127.0.0.1:8000/"
%PY% -m uvicorn app.main:app --port 8000
pause
