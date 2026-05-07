# Sistema Integral de IA Agrícola — Café Colombia
## Entrega Final · Inteligencia Artificial 2026-1

**Universidad Autónoma de Occidente · Ingeniería de Datos e IA**

**Autores:** Yáxul Santiago Cárdenas · Yesenia Díaz Urrego

---

## ¿Qué hay aquí?

Sistema integral de IA para el café colombiano que:

- Predice **rendimiento** (ton/ha) por municipio con ML clásico, MLP profundo y Stacking
- Pronostica **precios** FNC e ICO con LSTM, BiGRU, LSTM+Atención y Transformer
- Detecta **enfermedades** (Roya, Gotera, Cercospora, Phoma, Miner) con CNN + Grad-CAM
- Detecta **anomalías** de precio con Autoencoder y VAE
- Responde preguntas en lenguaje natural con un **agente RAG** (LangChain + Groq)
- Se sirve como **app web Streamlit** con dashboards interactivos
- Persiste en **PostgreSQL 18** con esquema en estrella documentado
- Se despliega vía **Docker + docker-compose** o en HuggingFace Spaces / Streamlit Cloud gratis

Cubre las **4 Unidades del syllabus** explícitamente (ver `00_documentos/00_PLAN_MAESTRO_ENTREGA_FINAL.md`).

---

## Estructura de carpetas

```
IA_Entrega_Final/
├── 00_documentos/             # Plan maestro, documento académico .md y .docx
├── 01_datos/
│   ├── originales/            # Copias de la 2da entrega
│   ├── enriquecidos/          # NUEVOS: precios, clima, suelos, DEM
│   ├── procesados/            # master_cafe_*.csv generados
│   └── imagenes_cafe/         # ~10000 imágenes consolidadas
├── 02_notebooks/              # NB07-NB12 (cubren U.II, III, IV)
├── 03_scripts/
│   ├── descarga/              # 6 scripts de descarga de fuentes nuevas
│   ├── bd/                    # DDL PostgreSQL + carga inicial
│   ├── modelos/               # (futuro) funciones reutilizables
│   └── utilidades/            # (futuro) limpieza, integración
├── 04_modelos_entrenados/     # .pkl, .keras
├── 05_resultados/
│   ├── figuras/               # PNG/SVG de los notebooks
│   ├── tablas/                # CSV de métricas
│   └── reportes/              # HTML/PDF
├── 06_agente_rag/             # Pipeline RAG + ChromaDB + docs
├── 07_app_web/                # App Streamlit multipágina
├── 08_docker/                 # Dockerfile + compose
├── 09_presentacion/           # PPTX final + script + Q&A
├── 10_diccionario_datos/      # Diccionario MD detallado
└── README.md                  # Este archivo
```

---

## Quick Start

### Opción A — Solo ver la app (más rápido)

```bash
cd 07_app_web
pip install -r requirements.txt
streamlit run app.py
```

Abre http://localhost:8501

### Opción B — Pipeline completo (~3 horas)

```bash
# 1. Descargar datos nuevos (1-3 horas según conexión)
cd 03_scripts/descarga
pip install -r requirements_descarga.txt
python 00_ejecutar_todo.py

# 2. Levantar PostgreSQL (con Docker o local) y crear BD
psql -U postgres -c "CREATE DATABASE cafe_ia;"
psql -U postgres -d cafe_ia -f ../bd/01_ddl_schema.sql
python ../bd/02_carga_inicial.py

# 3. Ejecutar notebooks (en orden)
cd ../../02_notebooks
jupyter notebook  # o vscode
# → ejecutar NB07, NB08, NB09, NB10, NB11, NB12

# 4. Indexar agente RAG
cd ../06_agente_rag
python rag_pipeline.py indexar

# 5. Lanzar app web
cd ../07_app_web
streamlit run app.py
```

### Opción C — Todo en Docker (más reproducible)

```bash
cd 08_docker
docker compose up -d --build
# → http://localhost:8501
```

---

## Cobertura por unidad del syllabus

| Unidad | Tema | Notebook(s) / Módulo |
|--------|------|----------------------|
| **I** | Introducción a la IA, riesgos y oportunidades | `00_documentos/Documento_Final_IA_Cafe.md` (Cap. 1) |
| **II** | ML clásico (regresión, clasificación, agrupamiento, sesgos) | NB02, NB05, NB09, NB11 |
| **III** | Redes neuronales (perceptrón, superficial, profunda, optimizadores) | NB07 |
| **IV** | CNN (inspiración biológica, arquitecturas, Grad-CAM) | NB08 |
| **IV** | Series secuenciales (LSTM, GRU, Atención, Transformer) | NB10 |
| **IV** | Generativas (Autoencoder, VAE, mención GAN/Difusión) | NB12 |
| **IV** | PLN (embeddings, transformers, RAG) | `06_agente_rag/` |
| **Transversal** | Ingeniería de datos, BD, despliegue | `03_scripts/`, `07_app_web/`, `08_docker/` |

---

## Decisiones técnicas

| Tema | Decisión | Por qué |
|------|----------|---------|
| Stack web | Streamlit | Demo ML-friendly en horas |
| BD | PostgreSQL 18.3 | El usuario ya la tiene instalada con psqlODBC |
| Agente | RAG con Groq/Ollama | Gratis, sin tener que entrenar LLM |
| Containerización | Docker + compose | Reproducibilidad y deploy gratis |
| Hosting | HuggingFace Spaces o Streamlit Cloud | Gratis, ML-friendly |
| Imágenes café | RoCoLe + BRACOL + JMuBEN + CALIBRO | Datasets públicos representativos |
| Series precios | FRED + WB + IMF + ICO + FNC | Cobertura 1990-2026 (vs 2018-2025 antes) |

---

## Resultados esperados

| Modelo | 2da entrega | Final esperado | Mejora |
|--------|-------------|-----------------|--------|
| ML Precio (Ridge) | R² = 0.945 | R² ≥ 0.945 | mantiene |
| ML Rendimiento Municipal | R² = 0.067 | R² > 0.5 | +0.43 |
| MLP profundo (NB07) | — | competitivo | nueva U.III |
| BiGRU/Transformer (NB10) | R² = −2.12 | R² > 0.5 | +2.6 |
| CNN EfficientNetB0 (NB08) | Acc = 48.9% | Acc > 85% | +36 pp |
| RAG Q&A | — | 5/5 demo | nueva U.IV |

---

## Documentos de soporte

- **Plan maestro:** `00_documentos/00_PLAN_MAESTRO_ENTREGA_FINAL.md`
- **Documento académico:** `00_documentos/Documento_Final_IA_Cafe.md` y `.docx`
- **Diccionario de datos:** `10_diccionario_datos/DICCIONARIO_DATOS.md`
- **Presentación:** `09_presentacion/Presentacion_Entrega_Final.pptx` + `Script_Presentacion.md`
- **READMEs por módulo:** descarga, bd, agente_rag, docker

---

## Flujo de validación / verificación

```bash
# 1. Verificar BD
psql -U postgres -d cafe_ia -c "
SELECT 'fact_produccion' AS t, count(*) FROM cafe.fact_produccion
UNION ALL SELECT 'fact_clima',     count(*) FROM cafe.fact_clima
UNION ALL SELECT 'fact_precio',    count(*) FROM cafe.fact_precio
UNION ALL SELECT 'fact_imagen',    count(*) FROM cafe.fact_imagen_enfermedad;"

# 2. Verificar modelos
ls -lh 04_modelos_entrenados/

# 3. Verificar app
streamlit run 07_app_web/app.py
# → abrir http://localhost:8501 y revisar las 6 páginas

# 4. Verificar RAG
cd 06_agente_rag && python rag_pipeline.py demo
```

---

## Limitaciones honestas

- Datasets de imágenes son foráneos (Brasil/Ecuador) → captura propia es trabajo futuro
- Modelos de series no extrapolan eventos atípicos (surge 2024-2025)
- Sin GPU local algunos notebooks toman varias horas (Colab recomendado)
- Hosting gratis tiene memoria limitada → comprimir modelos para deploy

Más detalle en `00_documentos/Documento_Final_IA_Cafe.md` capítulo 8.

---

## Licencia y créditos

Datos públicos del MADR, FNC, IDEAM, NOAA, Banco Mundial, FRED, IMF y datasets
académicos abiertos (RoCoLe, BRACOL, JMuBEN, CALIBRO). Modelos basados en
TensorFlow, scikit-learn, XGBoost, LightGBM, LangChain. Imágenes y precios
con sus respectivas atribuciones documentadas en el documento académico.

---

*Mayo 2026 · Universidad Autónoma de Occidente*
