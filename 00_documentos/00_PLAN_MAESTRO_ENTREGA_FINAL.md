# PLAN MAESTRO — ENTREGA FINAL
## Sistema Integral de Inteligencia Agrícola para Colombia — Módulo Café

**Curso:** Inteligencia Artificial · 2026-1
**Universidad:** Autónoma de Occidente · Ingeniería de Datos e IA
**Autores:** Yáxul Santiago Cárdenas · Yesenia Díaz Urrego
**Fecha:** Mayo 2026

---

## 1. Diagnóstico del estado actual (post-Segunda Entrega)

| Módulo | Métrica | Estado | Causa |
|--------|---------|--------|-------|
| ML Precio (Ridge) | R²=0.945 · MAPE=4.3% | ✅ Excelente | Correlación lineal ICO↔FNC fuerte (r=0.97) |
| ML Rendimiento (Stacking) | R²=0.067 · MAPE=14% | ⚠ Aceptable | Solo 14 obs en test (departamentales) |
| DL Series Tiempo (BiGRU) | R²=−2.12 · MAPE=23.1% | ❌ Limitado | Surge 2024-2025 fuera de distribución |
| CNN Enfermedades (EfficientNetB0) | Acc=48.9% · R²=−0.45 | ❌ Limitado | Solo 47 imágenes (CALIBRO) |

**Hipótesis del equipo (validada):** El modelo está bien hecho, **el problema es falta de datos**. La entrega final debe resolver esto.

---

## 2. Cobertura por Unidad del syllabus

La rúbrica del curso evalúa cobertura curricular además de resultados predictivos. Esta entrega cubre **las 4 unidades** explícitamente:

### Unidad I — Introducción a la IA
- **Cubierto en:** Documento académico (Cap. 1) + Slide 2 presentación
- **Contenido:** Definición de IA, breve historia (logical AI → expert systems → ML → DL), riesgos y oportunidades específicas para el sector cafetero colombiano (sesgo geográfico, brecha digital rural, sobreconfianza en alertas automáticas, oportunidad de transferencia tecnológica para 800K familias).
- **Marco institucional:** MADR, FNC, Cenicafé, IDEAM.

### Unidad II — Fundamentos de Aprendizaje Automático
- **Regresión:** NB02 (Stacking RF+XGB+LGB), NB05 (Ridge precio), NB09 (rendimiento municipal nuevo).
- **Clasificación:** NB11 (clasificación binaria de "riesgo de baja productividad" + clasificación severidad de enfermedad en NB08).
- **Agrupamiento:** NB11 (K-Means/DBSCAN de municipios cafeteros por perfil agroclimático).
- **Sesgos:** NB11 (Fairlearn — sesgo geográfico Huila vs Antioquia vs Nariño + sesgo por clase en CNN).
- **Aplicaciones reales:** todas presentadas con datos del agro colombiano.

### Unidad III — Fundamentos de Redes Neuronales Artificiales
- **Modelo de neurona artificial:** NB07 — perceptrón binario para clasificación de riesgo (didáctico).
- **Red superficial:** NB07 — MLP de 1 capa oculta vs MLP profundo.
- **Red profunda:** NB07 — MLP 5 capas ocultas con BatchNorm, Dropout, EarlyStopping.
- **Algoritmos de entrenamiento:** Comparación Adam vs SGD vs RMSprop, learning rate scheduling (cosine), regularización L2.
- **Aplicación:** Predicción de rendimiento municipal vs XGBoost (NB07 vs NB09).

### Unidad IV — Aprendizaje Profundo
- **CNN (NB08):** EfficientNetB0 + ResNet50 reentrenados con dataset combinado (~3000 imágenes café). Inspiración biológica (V1, simple/complex cells), funcionamiento 2D, dimensionamiento. Arquitecturas representativas (LeNet → AlexNet → VGG → ResNet → EfficientNet). Aplicaciones de CNN (visión médica, agricultura). Grad-CAM, MC-Dropout.
- **Generativas (NB12):** Autoencoder convencional + Variational Autoencoder (VAE) para detección de anomalías de precio del café. Mención conceptual de GANs y modelos de difusión (referencia).
- **Series secuenciales (NB10):** LSTM, GRU, BiGRU, LSTM+Atención Bahdanau, Transformer (Temporal Fusion Transformer simplificado). Comparación cuantitativa.
- **PLN/Transformers (06_agente_rag):** Agente RAG con LangChain + ChromaDB + Groq/Ollama LLM. Embeddings (sentence-transformers — representación vectorial de palabras). Transformer-based generation. Cubre: redes recurrentes vs transformers, embeddings, atención.

---

## 3. Necesidad de más datos — diagnóstico

### 3.1 Limitaciones identificadas

| # | Limitación | Impacto | Solución propuesta |
|---|-----------|---------|---------------------|
| 1 | Solo 47 imágenes para CNN | Acc 48.9%, sesgo clase Alto (53%) | Datasets públicos café: RoCoLe, BRACOL, JMuBEN, CoLeaf → ~3000 imgs balanceadas |
| 2 | 14 obs en test rendimiento | R²=0.067 | Escala municipal (UPRA/DANE) → ~1000+ obs |
| 3 | Surge 2024-2025 fuera de distribución | LSTM R²=−2.12 | Historia extendida 2000-2026 (FRED/ICE) → 312 obs vs 60 actuales |
| 4 | Sin variables agronómicas | Varianza no capturada | DEM SRTM (altitud), SoilGrids (suelos), variedad |
| 5 | Sin Unidad III | Syllabus incompleto | Notebook MLP profundo nuevo |
| 6 | Sin agente RAG | Unidad IV transformers no completa | LangChain + Groq |

### 3.2 Fuentes adicionales — café específicamente

#### A. Imágenes de enfermedades (CRÍTICO)

| Dataset | Cantidad | Tipo | Acceso |
|---------|----------|------|--------|
| **RoCoLe** (Robusta Coffee Leaf) | ~1560 imgs | Roya, otras enfermedades | Mendeley · público |
| **BRACOL** (Brazilian Arabica Coffee Leaf) | ~4707 imgs | Roya, miner, cercospora, phoma | GitHub esuiip/leaf-disease · público |
| **JMuBEN/JMuBEN2** | ~58k imgs | Roya, gotera, cercospora | Mendeley · público |
| **CoLeaf** | ~1747 imgs | Multi-enfermedad arábica | Mendeley · público |
| **Coffee Leaf Diseases (Kaggle)** | ~5000 imgs | Roya, sano, otros | Kaggle · libre con cuenta |
| **CALIBRO (existente)** | 47 imgs | Roya, Gotera Colombia | Local |
| **Total combinado** | ~10000+ | Variado | — |

#### B. Precios histórico extendido

| Fuente | Período | Variable | Acceso |
|--------|---------|----------|--------|
| **FRED St. Louis Fed** | 1990-presente | Precio Café Brasil/Colombia (USD/lb) | API libre |
| **World Bank Pink Sheet** | 1960-presente | Café Arabica + Robusta mensual | Excel libre |
| **IMF Primary Commodity Prices** | 1992-presente | Coffee composite | API libre |
| **FAOSTAT** | 1961-presente | Producción y precios productor | API libre |
| **ICO** | 1990-presente | Precio compuesto + 4 grupos | Web scraping/CSV |
| **FNC histórico** | 1970-presente | Precio interno COP | PDF/Excel scraping |

#### C. Climáticos satelitales (resuelven huecos IDEAM)

| Fuente | Resolución | Variable | Acceso |
|--------|-----------|----------|--------|
| **CHIRPS v2** | 0.05° (~5km) diario | Precipitación | API ClimateSERV/GEE |
| **ERA5-Land** | 0.1° (~9km) horario | Temperatura, humedad, viento | Copernicus CDS |
| **MODIS NDVI** | 250m, 16-días | Vegetación | GEE |
| **SRTM DEM** | 30m | Altitud | NASA Earthdata libre |

#### D. Producción a escala municipal

| Fuente | Granularidad | Período |
|--------|--------------|---------|
| **DANE EVA** | Municipio × año | 2007-2024 (ya tienes 2019-2024) — extender a 2007 |
| **DANE Censo Nacional Agropecuario** | Municipio × tipología productor | 2014 |
| **FNC Municipios cafeteros (Cenicafé)** | Municipio × variedad | 2018-2024 |

---

## 4. Cronograma (8 días intensivos)

### Día 1 — Estructura + descargas
- ✅ Crear carpetas
- ✅ Plan maestro y diccionario
- 🔄 Scripts de descarga
- → Usuario ejecuta descargas localmente

### Día 2 — Base de datos
- DDL PostgreSQL 18
- Carga inicial de todos los CSVs
- Vistas y queries de validación
- Diccionario de datos exportable

### Día 3 — Notebooks Unidad II (clustering, sesgos) + III (MLP)
- NB11: Clustering municipios + Fairlearn
- NB07: MLP profundo

### Día 4 — Notebooks Unidad IV (parte 1: CNN)
- NB08: Reentrenar CNN con dataset combinado

### Día 5 — Notebooks Unidad IV (parte 2: LSTM, generativas)
- NB10: LSTM extendido
- NB12: Autoencoder anomalías

### Día 6 — Agente RAG + ML Rendimiento Municipal
- NB09: ML rendimiento municipal
- 06_agente_rag: LangChain + ChromaDB + Groq

### Día 7 — App web Streamlit
- Multipágina: Home, Predicciones, CNN upload, Forecasting, Chatbot, Mapa

### Día 8 — Docker + Documento + Presentación + Verificación
- Dockerfile + docker-compose
- Deploy a HuggingFace Spaces / Streamlit Cloud
- Documento académico final + slides
- Lista de verificación

---

## 5. Criterios de éxito (rúbrica)

La rúbrica evalúa 4 criterios:

| Criterio | Peso | Cómo lo cumplimos |
|----------|------|-------------------|
| **Conocimiento del modelo** (30%) | Profundo conocimiento de cada modelo, datos y necesidades del MADR/FNC | Documento + notebooks comentados + sección por unidad |
| **Explicación del proceso** (25%) | Detalle de entrenamiento (hiperparámetros, splits, validación) | Cada notebook documenta esto + script principal de cada modelo |
| **Resultados** (25%) | Métricas, gráficas, conclusiones | Tablas comparativas, figuras Grad-CAM, intervalos de confianza |
| **Calidad de presentación** (20%) | Organización, fluidez, recursos visuales | App web demo en vivo + slides + script presentación |

**Restricción:** 15 min de presentación → script y demo cuidadosamente cronometrados.

---

## 6. Estructura de carpetas

```
IA_Entrega_Final/
├── 00_documentos/                # Plan maestro, documento académico, bibliografía
├── 01_datos/
│   ├── originales/               # Copias de la 2da entrega (EVA, FNC, ENSO, IDEAM, ICO, CALIBRO)
│   ├── enriquecidos/             # NUEVOS: FRED, World Bank, FAOSTAT, BanRep, CHIRPS, DANE municipal
│   ├── procesados/               # master_cafe_municipal.csv, dataset_modelado.parquet
│   └── imagenes_cafe/            # NUEVAS: RoCoLe, BRACOL, JMuBEN, CoLeaf consolidadas
├── 02_notebooks/
│   ├── NB07_MLP_profundo.ipynb            # Unidad III
│   ├── NB08_CNN_dataset_ampliado.ipynb    # Unidad IV — CNN
│   ├── NB09_ML_municipal.ipynb            # Mejor rendimiento (refinamiento NB02/05)
│   ├── NB10_LSTM_TFT_extendido.ipynb      # Unidad IV — RNN/Transformer
│   ├── NB11_Clustering_Fairness.ipynb     # Unidad II — agrupamiento + sesgos
│   └── NB12_Autoencoder_VAE.ipynb         # Unidad IV — generativas
├── 03_scripts/
│   ├── descarga/                 # Scripts ejecutables para datasets nuevos
│   ├── bd/                       # DDL PostgreSQL + carga
│   ├── modelos/                  # Funciones reutilizables (training loops, métricas)
│   └── utilidades/               # Limpieza, integración, evaluación
├── 04_modelos_entrenados/        # .pkl, .keras, .h5 de cada notebook
├── 05_resultados/
│   ├── figuras/                  # PNG/SVG para documento
│   ├── tablas/                   # CSV de métricas comparativas
│   └── reportes/                 # HTML/PDF de evaluación
├── 06_agente_rag/                # ChromaDB index, prompts, evaluación
│   ├── vectorstore/
│   ├── documentos_fuente/        # Papers, documentos MADR, datasets como contexto
│   └── rag_pipeline.py
├── 07_app_web/                   # App Streamlit
│   ├── app.py                    # Entry point
│   ├── pages/                    # Páginas multipage
│   ├── components/               # Componentes reutilizables
│   └── assets/                   # CSS, imágenes
├── 08_docker/                    # Dockerfile, docker-compose, .dockerignore
├── 09_presentacion/              # PPTX final + script + Q&A
└── 10_diccionario_datos/         # Schema PostgreSQL + diccionario MD/HTML
```

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| Descargas fallan (timeouts, captchas) | Scripts con reintentos + mirrors alternativos + descarga manual documentada |
| GPU insuficiente para CNN ampliado | Transfer Learning solo (head + last 20 layers); fallback a Colab |
| TFT/Transformer no converge | Mantener BiGRU como respaldo; documentar como trabajo futuro |
| Streamlit Cloud limita memoria | Modelos comprimidos (TFLite/ONNX); fallback a Render gratis |
| RAG sin internet (Ollama local) | API Groq gratis como backup (0.5s, modelos potentes) |
| PostgreSQL versión 18 muy nueva | Funciona con 13+; psqlODBC 13.02 ya instalado |

---

## 8. Decisiones técnicas tomadas

1. **Stack web:** Streamlit (rapidez de demo)
2. **Reentrenamiento:** Total (CNN + LSTM + ML rendimiento)
3. **Descargas:** Usuario ejecuta localmente (scripts listos)
4. **Agente:** RAG con Groq/Ollama gratis
5. **Base de datos:** PostgreSQL 18.3 (la que tiene el usuario)
6. **Hosting:** HuggingFace Spaces o Streamlit Cloud (gratis, ML-friendly)
7. **Containerización:** Docker + docker-compose para reproducibilidad

---

*Documento generado al iniciar la entrega final · actualizar conforme avance*
