@echo off
REM ════════════════════════════════════════════════════════════════════════
REM Sistema IA Café - Pipeline completo (Windows)
REM ════════════════════════════════════════════════════════════════════════
setlocal

echo.
echo =====================================================================
echo  SISTEMA IA CAFE - Pipeline completo
echo =====================================================================
echo.

REM 1. Verificar Python
where python >nul 2>nul
if errorlevel 1 (
    echo [X] Python no encontrado. Instala Python 3.10+ desde python.org
    exit /b 1
)

REM 2. Activar venv si existe
if exist .venv\Scripts\activate.bat (
    echo [+] Activando venv...
    call .venv\Scripts\activate.bat
) else (
    echo [!] No hay venv. Crear uno con: python -m venv .venv
)

REM 3. Instalar dependencias
echo.
echo [1/6] Instalando dependencias...
pip install -r 03_scripts\descarga\requirements_descarga.txt -q
pip install -r 07_app_web\requirements.txt -q

REM 4. Descargar datos
echo.
echo [2/6] Descargando nuevos datasets...
cd 03_scripts\descarga
python 00_ejecutar_todo.py
cd ..\..

REM 5. Crear BD y cargar
echo.
echo [3/6] Cargando datos a PostgreSQL...
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE IF NOT EXISTS cafe_ia;" 2>nul
psql -U postgres -h localhost -p 5432 -d cafe_ia -f 03_scripts\bd\01_ddl_schema.sql
python 03_scripts\bd\02_carga_inicial.py

REM 6. Indexar RAG
echo.
echo [4/6] Indexando agente RAG...
cd 06_agente_rag
python rag_pipeline.py indexar
cd ..

REM 7. Lanzar app
echo.
echo [5/6] Lanzando app web Streamlit...
echo Abre http://localhost:8501 en tu navegador
cd 07_app_web
streamlit run app.py
