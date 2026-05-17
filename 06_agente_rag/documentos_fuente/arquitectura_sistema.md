# Arquitectura técnica del Sistema IA Café Colombia

## Visión general

Sistema integral con 4 capas:

1. **Capa de datos**: PostgreSQL 18 esquema `cafe` con DDL en estrella.
2. **Capa de modelos**: archivos `.pkl` (sklearn) y `.keras` (TensorFlow)
   en `04_modelos_entrenados/`.
3. **Capa de servicio**: aplicación Streamlit multipágina en `07_app_web/`.
4. **Capa de despliegue**: Docker + docker-compose para deploy gratis.

## Pipeline de datos

```
Scripts descarga → CSVs raw → ETL pipeline → *_validado.csv → BD PostgreSQL → Notebooks → Modelos → App web
```

### Etapa 1 — Descarga (03_scripts/descarga/)

Scripts ejecutables:
- `01_descargar_imagenes_cafe.py`: RoCoLe, BRACOL, JMuBEN, Coffee Leaf desde Kaggle/Mendeley
- `02_descargar_precios_extendidos.py`: FRED, World Bank, IMF, BanRep
- `03_descargar_clima_satelital.py`: Open-Meteo histórico mensual
- `04_descargar_eva_municipal.py`: EVA municipal vía Socrata datos.gov.co
- `05_descargar_dem_suelos.py`: Open-Elevation + SoilGrids
- `06_consolidar_imagenes.py`: unifica datasets en train/val/test estratificado
- `07_procesar_bracol_yolo.py`: extrae crops por clase desde anotaciones YOLO

Orquestador: `00_ejecutar_todo.py` corre todos en orden con logging.

### Etapa 2 — ETL (03_scripts/etl/etl_pipeline.py)

Por cada categoría de fuente (precios, clima, ENSO, producción, geografía,
imágenes) aplica validación específica del dominio + consolidación canónica:

- Conversión de unidades (cents/lb → USD/kg, COP/125kg → COP/kg)
- Validación de rangos físicos (T en [-5,45], precip ≥ 0, etc.)
- Detección de outliers
- Detección de duplicados byte-exactos en imágenes (SHA1 completo)
- Detección de surge MoM > 25% en precios

Salidas: `01_datos/procesados/*_validado.csv` + reportes JSON.

### Etapa 3 — Validación pre-carga (03_scripts/bd/validar_pre_carga.py)

Reporta antes de cargar a BD:
- Compatibilidad de columnas con DDL
- Nulos en columnas clave (PK)
- Duplicados por PK natural
- Outliers fuera de rangos físicos
- Cobertura temporal y geográfica

Genera reporte markdown en `05_resultados/reportes/pre_carga_<timestamp>.md`.

### Etapa 4 — Carga a BD (03_scripts/bd/02_carga_inicial.py)

Idempotente (UPSERTs por PK natural). Orden:
`dim_periodo → ONI → dim_municipio → fact_clima → fact_precio → fact_produccion → fact_imagen_enfermedad → vista materializada`.

Auto-crea municipios faltantes desde EVA. Maneja chunks de 5000 filas
para imágenes (manifest >10K).

### Etapa 5 — Notebooks (02_notebooks/)

6 notebooks principales que cubren las Unidades II-IV del syllabus.
Orden recomendado: NB11 → NB09 → NB07 → NB10 → NB12 → NB08.

### Etapa 6 — Aplicación Streamlit (07_app_web/)

Multipágina:
1. Dashboard agroclimático
2. Predicción de rendimiento
3. Forecasting de precios
4. Detector de enfermedades (CNN con upload imagen)
5. Chatbot RAG conversacional
6. Mapa cafetero interactivo
7. Calculadora SCA → Precio
8. Asesor del Caficultor (recordatorios + alertas + tips)

## Esquema de seguridad

- Credenciales en archivo `.env` en raíz del proyecto.
- `.env` excluido de git vía `.gitignore`.
- `.env.example` como plantilla pública.
- Sin credenciales hardcodeadas en código.

## Módulo común de configuración

`03_scripts/bd/_config_bd.py` centraliza:
- Carga de `.env` (parser propio sin requerir python-dotenv)
- Configuración PostgreSQL (PG_CONFIG dict)
- Rutas absolutas del proyecto
- Logger configurado con doble salida (consola + archivo)
- Helper de conexión con manejo de errores

## Logging

Cada ejecución crea archivo en `05_resultados/logs/<script>_<timestamp>.log`.
Configurable vía `LOG_LEVEL=DEBUG|INFO|WARNING|ERROR` en `.env`.

## Containerización

- `08_docker/Dockerfile`: imagen Streamlit con TensorFlow + modelos.
- `08_docker/docker-compose.yml`: orquesta PostgreSQL + app.
- Deploy gratis en HuggingFace Spaces o Streamlit Cloud.

## Agente RAG (06_agente_rag/)

Pipeline en `rag_pipeline.py`:
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (multilingüe, CPU)
- Vector store: ChromaDB persistente local
- LLM: Llama-3.1-8b-instant vía Groq (gratis) o Ollama local
- Chunking: RecursiveCharacterTextSplitter 800 chars con overlap 120
- Indexa documentos markdown en `documentos_fuente/`

## Reproducibilidad

- Random seeds fijos en todos los notebooks (42)
- Versiones de dependencias en `requirements.txt`
- Docker para garantizar entorno consistente
- Scripts de descarga generan los mismos CSVs en cualquier ejecución
- Modelos guardados con timestamp implícito en los logs
