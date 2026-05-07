#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════
# Sistema IA Café - Pipeline completo (Linux/Mac)
# ════════════════════════════════════════════════════════════════════════
set -e

echo
echo "====================================================================="
echo " SISTEMA IA CAFE — Pipeline completo"
echo "====================================================================="
echo

# 1. venv
if [ -d .venv ]; then
    echo "[+] Activando venv..."
    source .venv/bin/activate
else
    echo "[!] Sin venv. Crear: python3 -m venv .venv"
fi

# 2. Dependencias
echo
echo "[1/6] Instalando dependencias..."
pip install -r 03_scripts/descarga/requirements_descarga.txt -q
pip install -r 07_app_web/requirements.txt -q

# 3. Descargas
echo
echo "[2/6] Descargando nuevos datasets..."
(cd 03_scripts/descarga && python 00_ejecutar_todo.py)

# 4. BD
echo
echo "[3/6] Cargando datos a PostgreSQL..."
psql -U postgres -h localhost -p 5432 -tc "SELECT 1 FROM pg_database WHERE datname = 'cafe_ia'" | grep -q 1 || \
    psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE cafe_ia;"
psql -U postgres -h localhost -p 5432 -d cafe_ia -f 03_scripts/bd/01_ddl_schema.sql
python 03_scripts/bd/02_carga_inicial.py

# 5. RAG
echo
echo "[4/6] Indexando agente RAG..."
(cd 06_agente_rag && python rag_pipeline.py indexar)

# 6. App
echo
echo "[5/6] Lanzando app web Streamlit..."
echo "Abre http://localhost:8501 en tu navegador"
(cd 07_app_web && streamlit run app.py)
