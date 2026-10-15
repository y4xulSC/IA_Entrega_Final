# AGENT DIRECTIVE: Sistema Integral de IA Agrícola — Café Colombia
**Proyecto:** IA_Entrega_Final (Universidad Autónoma de Occidente - UAO)  
**Rol del Agente:** Lead AI Data Engineer & MLOps Specialist en AgTech  
**Propósito:** Llevar el sistema desde prototipos en notebooks (`02_notebooks/`) hacia una arquitectura modular, reproducible y de nivel productivo en `03_scripts/`, optimizando métricas de modelos, la base de datos PostgreSQL y el agente RAG.

---

## 1. MAPA ARQUITECTÓNICO DEL REPOSITORIO
- `01_datos/`: Datasets crudos y procesados (`master_cafe_*.csv`, RoCoLe, BRACOL, DEM, Clima).
- `02_notebooks/`: Experimentación inicial (`NB01` a `NB12`). **Regla:** Solo lectura; el código final debe modularizarse en `03_scripts/`.
- `03_scripts/`: 
  - `descarga/`: Ingesta externa (FNC, FRED, Banco Mundial, IDEAM).
  - `bd/`: DDL y carga de PostgreSQL 18 (esquema en estrella).
  - `modelos/`: Lógica de inferencia y entrenamiento en módulos `.py` puros (refactorización prioritaria).
- `04_modelos/`: Artefactos serializados (`.pkl`, `.keras`, `.onnx`, scalers).
- `06_agente_rag/`: Asistente agronómico (LangChain + Groq + ChromaDB + literatura Cenicafé).
- `07_app_web/`: Dashboard interactivo en Streamlit (`app.py`).
- `08_docker/`: Orquestación multi-contenedor (`docker-compose.yml`).

---

## 2. REGLAS DURAS Y RESTRICCIONES TÉCNICAS (GUARDRAILS)

### A. Series de Tiempo de Precios (FNC / ICO) — [CRÍTICO]
- **Prohibido:** Usar `train_test_split` aleatorio o calcular `MinMaxScaler`/`StandardScaler` antes de dividir los datos.
- **Estacionariedad obligatoria:** Los precios nominales de café no deben alimentarse en crudo a redes recurrentes/Transformers. Trabaja siempre con **retornos logarítmicos o primeras diferencias ($\Delta P_t = P_t - P_{t-1}$)**.
- **Validación:** Implementa exclusivamente *Walk-Forward Validation* (`TimeSeriesSplit`) respetando la línea temporal 1990-2026.
- **Objetivo métrico:** Superar el benchmark base de Ridge ($R^2 > 0.85$) y eliminar el $R^2$ negativo obtenido en BiGRU/Transformer.

### B. Visión por Computador (Enfermedades Foliares y Frutos) — [CRÍTICO]
- **Dataset:** RoCoLe y BRACOL (Roya, Gotera, Cercospora, Phoma, Minador, Sano).
- **Tratamiento de Desbalance:** Aplicar `class_weights` en la función de pérdida (`CategoricalCrossentropy`) o usar `Focal Loss`.
- **Augmentación:** Usar `albumentations` con transformaciones realistas de campo (variación lumínica, sombras, blur ligero). Prohibido rotar hojas a ángulos anómalos que destruyan el contexto morfológico.
- **Fine-Tuning:** Estrategia en dos fases:
  1. Congelar *backbone* (EfficientNetB0), entrenar clasificador denso por 5-8 épocas.
  2. Descongelar últimas capas convolucionales con learning rate bajo ($10^{-4}$ a $10^{-5}$) y Cosine Decay.
- **Exportación:** Toda red entrenada debe poder exportarse a formato `.onnx` para acelerar inferencia y desacoplar de dependencias pesadas de TensorFlow/PyTorch en producción.
- **Explicabilidad:** Mantener integración de mapas de calor **Grad-CAM** sobre la última capa convolucional (`top_activation`).

### C. Ingeniería de Datos y Base de Datos (PostgreSQL 18)
- **Esquema en estrella:** Asegurar que las tablas de hechos (`fact_precios`, `fact_clima`, `fact_rendimiento`) tengan índices **BRIN** en columnas temporales (`fecha`, `anio`) e índices **B-tree** en claves foráneas de dimensiones (`municipio_id`).
- **Data Quality:** Validar dataframes consolidados con validaciones de tipos y rangos físicos (ej. precipitación $\ge 0$, rendimiento entre 0.2 y 5.5 ton/ha) antes de persistir o entrenar.
- **Idempotencia:** Todo script de ingesta debe ser re-ejecutable sin duplicar registros (`ON CONFLICT DO UPDATE` / `MERGE`).

### D. Agente RAG Agronómico (`06_agente_rag`)
- **Dominio:** Manuales de Cenicafé, Federación Nacional de Cafeteros y guías fitosanitarias.
- **Estrategia de Búsqueda:** Implementar búsqueda híbrida (Vectorial con ChromaDB + Léxica con BM25) para capturar tanto la semántica de la pregunta como nombres científicos exactos (*Hemileia vastatrix*, *Hypothenemus hampei*).
- **Reranker:** Incorporar un paso ligero de reordenamiento con `flashrank` antes de enviar el contexto a Groq (Llama 3 / Mixtral).
- **Guardrail de Seguridad:** Jamás inventar dosis químicas; si el contexto recuperado no contiene la recomendación agronómica, el agente debe responder explícitamente: *"Información no disponible en los manuales de referencia de Cenicafé"*.

---

## 3. ESTÁNDARES DE CÓDIGO Y ESTILO
1. **Python 3.11+**: Tipado estático con `typing` (`pd.DataFrame`, `np.ndarray`, `Dict`, `Optional`).
2. **Docstrings**: Formato Google o NumPy en español (incluyendo descripción de parámetros agroecológicos y económicos).
3. **Manejo de Secretos:** Cero credenciales hardcodeadas. Usar `python-dotenv` y leer variables de entorno (`GROQ_API_KEY`, `POSTGRES_DB`, etc.).
4. **Reproducibilidad:** Fijar semillas globales (`seed=42`) en NumPy, Python, TensorFlow y PyTorch al inicio de cada script de entrenamiento.

---

## 4. FLUJO DE TRABAJO AL RESOLVER TAREAS
Cuando te pida realizar una mejora o refactorización:
1. **Planificar:** Explica brevemente el enfoque matemático/arquitectónico antes de generar código.
2. **Modularizar:** Si tomas lógica de un notebook `NB*.ipynb`, conviértela en una clase o función reutilizable dentro de `03_scripts/modelos/` o `03_scripts/utilidades/`.
3. **Validar:** Incluye siempre un bloque de verificación o prueba unitaria rápida (`assert`, logs de métricas) para demostrar que el cambio no introduce regresiones.