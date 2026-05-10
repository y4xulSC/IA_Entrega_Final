# Guía de instalación detallada

## Requisitos del sistema

| Componente | Versión mínima | Notas |
|------------|----------------|-------|
| Python | 3.10 | Probado en 3.10 y 3.11 |
| PostgreSQL | 13 | El usuario tiene 18.3 con psqlODBC 13.02 |
| RAM | 8 GB | 16 GB recomendados para entrenar CNN |
| Disco | 15 GB | Para imágenes de café |
| Sistema | Windows / Linux / macOS | Probado en Windows 10/11 |

---

## Paso 1 · Clonar / abrir el proyecto

Si ya tienes la carpeta `IA_Entrega_Final` en tu OneDrive, salta este paso.
Si no, copia toda la carpeta.

---

## Paso 2 · Entorno Python

```bash
# Crear venv (recomendado)
python -m venv .venv

# Activar
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.\.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate

# Instalar dependencias del proyecto completo
pip install -r 03_scripts/descarga/requirements_descarga.txt
pip install -r 07_app_web/requirements.txt
```

---

## Paso 3 · PostgreSQL (BD `cafe_ia`)

### Si tienes PostgreSQL local (caso del usuario)
```bash
# Crear base
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE cafe_ia;"

# Cargar schema
psql -U postgres -h localhost -p 5432 -d cafe_ia -f 03_scripts/bd/01_ddl_schema.sql

# Verificar (debe listar 13 objetos)
psql -U postgres -d cafe_ia -c "\dt cafe.*"
```

### Si prefieres Docker
```bash
docker run -d --name cafe_pg \
  -e POSTGRES_DB=cafe_ia \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=root \
  -p 5432:5432 \
  -v $PWD/03_scripts/bd/01_ddl_schema.sql:/docker-entrypoint-initdb.d/01_ddl.sql:ro \
  postgres:18-alpine
```

---

## Paso 4 · Descargar nuevos datasets

```bash
cd 03_scripts/descarga

# Recomendado: ejecutar todo (~2-3 horas)
python 00_ejecutar_todo.py

# Alternativa: paso a paso para controlar
python 02_descargar_precios_extendidos.py    # ~3 min
python 03_descargar_clima_satelital.py       # ~5 min
python 04_descargar_eva_municipal.py         # ~5 min
python 05_descargar_dem_suelos.py            # ~5 min
python 01_descargar_imagenes_cafe.py         # ~30 min (lo más pesado)
python 06_consolidar_imagenes.py             # ~5 min
```

**Pre-requisitos para imágenes:**
- Cuenta Kaggle: https://www.kaggle.com/settings → Create API Token
- Token en `~/.kaggle/kaggle.json`

---

## Paso 5 · Cargar datos a PostgreSQL

```bash
cd 03_scripts/bd
python 02_carga_inicial.py

# Verificar
psql -U postgres -d cafe_ia -c "
SELECT 'dim_periodo' AS t, count(*) FROM cafe.dim_periodo
UNION ALL SELECT 'dim_municipio', count(*) FROM cafe.dim_municipio
UNION ALL SELECT 'fact_produccion', count(*) FROM cafe.fact_produccion
UNION ALL SELECT 'fact_clima', count(*) FROM cafe.fact_clima
UNION ALL SELECT 'fact_precio', count(*) FROM cafe.fact_precio
UNION ALL SELECT 'fact_imagen', count(*) FROM cafe.fact_imagen_enfermedad;"
```

---

## Paso 6 · Construir el dataset maestro

```bash
cd 03_scripts/utilidades
python construir_master_municipal.py
```

Esto produce `01_datos/procesados/master_cafe_municipal_mensual.csv`
y `master_cafe_municipal_anual.csv` que **todos los notebooks NB07-NB12
esperan encontrar**. Lee de PostgreSQL si está cargado, o de los CSVs
enriquecidos como fallback.

## Paso 7 · Entrenar modelos (notebooks)

```bash
cd 02_notebooks
jupyter notebook
```

Orden recomendado:
1. **NB07** — MLP profundo (Unidad III) · ~10 min CPU
2. **NB09** — ML rendimiento municipal · ~15 min CPU
3. **NB10** — LSTM extendido · ~25 min CPU
4. **NB11** — Clustering + Fairness · ~5 min CPU
5. **NB12** — Autoencoder + VAE · ~10 min CPU
6. **NB08** — CNN ampliado · ~1-3 horas (recomendado GPU; usar Colab si no)

---

## Paso 7 · Configurar agente RAG

```bash
# Opcional: API key Groq gratis para LLM rápido
# https://console.groq.com → API Keys
# Linux/Mac:
export GROQ_API_KEY=gsk_xxxxx
# Windows:
setx GROQ_API_KEY "gsk_xxxxx"

# Indexar documentos
cd 06_agente_rag
python rag_pipeline.py indexar

# Probar
python rag_pipeline.py demo
```

---

## Paso 8 · Lanzar app web

```bash
cd 07_app_web
streamlit run app.py
```

Abre http://localhost:8501

---

## Paso 9 · Deploy gratis (opcional)

### HuggingFace Spaces
1. https://huggingface.co/new-space → tipo "Streamlit"
2. Sube el contenido de `07_app_web/`
3. En Settings > Variables: `GROQ_API_KEY`

### Streamlit Cloud
1. Sube el repo a GitHub
2. https://streamlit.io/cloud → Deploy
3. Path: `IA_Entrega_Final/07_app_web/app.py`
4. Secrets: `[secrets]` con `GROQ_API_KEY = "..."`

### Docker en cualquier VPS
```bash
cd 08_docker
docker compose up -d --build
```

---

## Resolución de problemas

### "kaggle.json not found"
Crea cuenta en https://kaggle.com → Settings → API → Create New Token.
Mueve el JSON a `~/.kaggle/kaggle.json` y `chmod 600 ~/.kaggle/kaggle.json`

### "psycopg2 binary install failed"
```bash
pip install psycopg2-binary  # versión binaria, no requiere libpq
```

### "TensorFlow no usa GPU"
Las CNN entrenan en CPU pero más lento. Para GPU:
```bash
pip install tensorflow[and-cuda]
# o usa Google Colab gratis con GPU T4
```

### "ChromaDB error en Windows"
```bash
pip install chromadb --upgrade
# si persiste, usa SQLiteDB-only mode:
export CHROMA_DB_IMPL=duckdb+parquet
```

### App Streamlit muy lenta
Si el deploy gratis tiene memoria limitada, comenta TensorFlow en
`requirements.txt` y carga solo modelos sklearn (.pkl).

---

## Verificación final (checklist)

- [ ] BD `cafe_ia` creada con 13 objetos
- [ ] Datos enriquecidos descargados en `01_datos/enriquecidos/`
- [ ] Imágenes consolidadas en `01_datos/imagenes_cafe/{train,val,test}/`
- [ ] Tabla `cafe.fact_produccion` con > 100 filas
- [ ] Modelos en `04_modelos_entrenados/` (al menos 5 archivos)
- [ ] App en http://localhost:8501 abre las 6 páginas
- [ ] Chatbot RAG responde una pregunta de demo
- [ ] Documento `Documento_Final_IA_Cafe.docx` generado
- [ ] Presentación `Presentacion_Entrega_Final.pptx` generada
