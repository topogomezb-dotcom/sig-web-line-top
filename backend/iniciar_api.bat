@echo off
REM Inicia la API y el visor en http://127.0.0.1:8000/  (Windows)
cd /d %~dp0
python -m uvicorn app.main:app --reload
pause
