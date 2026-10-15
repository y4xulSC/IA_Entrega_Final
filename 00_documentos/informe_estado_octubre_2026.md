# INFORME TÉCNICO, ANALÍTICO, ESTRATÉGICO Y OPERATIVO: SISTEMA INTEGRAL DE IA AGRÍCOLA (CAFÉ COLOMBIA)

**Repositorio evaluado:** `https://github.com/y4xulSC/IA_Entrega_Final`  
**Institución / Contexto Académico:** Universidad Autónoma de Occidente (UAO) — Facultad de Ingeniería, Ingeniería de Datos e Inteligencia Artificial (Curso IA 2026-1)  
**Autores del proyecto original:** Yáxul Santiago Cárdenas & Yesenia Díaz Urrego  
**Fecha de auditoría técnica:** Octubre de 2026  
**Alcance de la auditoría:** Revisión arquitectural, matemática, metodológica y operativa de todos los artefactos del repositorio: documentación técnica (`00_documentos/`), fuentes de datos y almacenamiento (`01_datos/`, `10_diccionario_datos/`), canalizaciones de cómputo analítico (`02_notebooks/`, NB07 a NB12), scripts de infraestructura y ETL (`03_scripts/`), modelos serializados (`04_modelos_entrenados/`), resultados (`05_resultados/`), agente conversacional (`06_agente_rag/`), capa de servicio web (`07_app_web/`) y contenedorización (`08_docker/`, scripts de ejecución raíz).

---

## 1. RESUMEN EJECUTIVO Y MAPA GENERAL DEL PROYECTO

El proyecto **«Sistema Integral de IA Agrícola — Café Colombia»** constituye una plataforma analítica y de aprendizaje automático orientada a resolver cuatro problemáticas críticas de la cadena de valor de la caficultura en Colombia:

```
+----------------------------------------------------------------------------------------------------+
|                         PLATAFORMA INTEGRAL IA CAFÉ COLOMBIA (ARQUITECTURA)                        |
+----------------------------------------------------------------------------------------------------+
  |
  +---> 1. RENDIMIENTO AGRONÓMICO (ton/ha)
  |     - Modelos: Regresión Clásica (Ridge/Lasso/RF/LGBM), MLP Profundo (NB07), Stacking Ensemble
  |     - Datos: Agronet/EVA + Enriquecimiento Climático (IDEAM/ERA5) + Edafológico (Suelos/IGAC) + DEM
  |
  +---> 2. PRONÓSTICO DE MERCADO Y PRECIOS (FNC / ICO)
  |     - Modelos: Series Secuenciales (LSTM, BiGRU, LSTM con Mecanismo de Atención, Transformer)
  |     - Detección de Anomalías: Autoencoders Profundos y Variational Autoencoders (VAE) (NB12)
  |     - Datos: Históricos 1990-2026 (FRED, Banco Mundial, FMI, FNC, ICO)
  |
  +---> 3. VISIÓN POR COMPUTADOR (SANIDAD VEGETAL)
  |     - Modelos: CNN (Transfer Learning con EfficientNetB0, MobileNetV3) + Grad-CAM Explainability
  |     - Diagnóstico: Roya, Mancha de Hierro (Cercospora), Gotera, Phoma, Minador de la Hoja, Sano
  |     - Datos: ~10.000 imágenes multiorigen (RoCoLe, BRACOL, JMuBEN, CALIBRO)
  |
  +---> 4. AGENTE CONVERSACIONAL RAG (KNOWLEDGE BASE)
  |     - Motor: LangChain + ChromaDB (Vector Store) + LLM (Groq / Ollama LLaMA-3)
  |     - Corpus: Manuales Cenicafé, guías técnicas agronómicas y reportes del sistema
  |
  +---> CAPA DE DATOS Y SERVICIOS TRANSVERSALES
        - Base de Datos: PostgreSQL 18 (Esquema en Estrella Dimensional)
        - Aplicación: Streamlit Multi-Page Dashboard (07_app_web/)
        - Despliegue: Docker + Docker-Compose / Cloud Spaces
```

A pesar de su cobertura temática integral que abarca desde el aprendizaje supervisado tabular hasta el Deep Learning generativo y el procesamiento de lenguaje natural (RAG), el proyecto se encuentra en una fase de **transición desde prototipo académico/experimental hacia sistema de grado empresarial**. Presenta importantes asimetrías de rendimiento heredadas de entregas previas (por ejemplo, el $R^2 = 0.067$ en predicción de rendimiento municipal o el $R^2 = -2.12$ en redes recurrentes tempranas) y carece de desacoplamiento modular en su base de código fuente.

A continuación, se desglosa el informe de evaluación exhaustiva, diagnósticos de vulnerabilidad, planes de refactorización y hojas de ruta técnicas estructuradas por perfiles de especialización.

---

## 2. PROFESIONALES TÉCNICOS

```
====================================================================================================
ÁREA: PROFESIONALES TÉCNICOS
ROLES: ML/DS ENGINEERS | SOFTWARE ENGINEERS | DATA ENGINEERS
====================================================================================================
```

### 2.1. INGENIEROS DE MACHINE LEARNING / DATA SCIENCE

#### A. Diagnóstico de Rendimiento y Patologías de Modelado
1. **Pronóstico de Rendimiento Agronómico Municipal ($R^2$ histórico de $0.067$):**
   * *Patología identificada:* Discrepancia espacial y desacoplamiento fenológico. La agregación municipal anual/semestral enmascara la microvariabilidad climática (brillo solar, estrés hídrico durante la floración, déficit de nitrógeno en llenado de grano). El modelo previo intentó proyectar relaciones lineales directas sin retardos temporales (*lags*) acordes al ciclo fisiológico del cafeto (210–240 días desde antesis hasta cosecha).
   * *Métricas objetivo:* Elevar $R^2 \ge 0.55$, reducir el $MAE \le 0.18 \text{ ton/ha}$ y $MAPE \le 12\%$.
2. **Modelado Secuencial de Precios ($R^2$ histórico negativo de $-2.12$ en BiGRU vs. $0.945$ en Ridge):**
   * *Patología identificada:* Efecto de predicción trivial por persistencia autorregresiva de orden 1 ($y_t \approx y_{t-1}$). El modelo Ridge aparenta un $R^2 = 0.945$ porque predice con base en el valor inmediatamente anterior en series integradas de orden 1 ($I(1)$), lo cual oculta un error cuadrático acumulado catastrófico en horizontes de varios pasos (*multi-step ahead*). Por el contrario, la red BiGRU colapsó debido a la falta de diferenciación estacional, no estacionariedad estricta en el espacio de entrada y gradientes desvanecidos/explosivos al predecir valores nominales en lugar de rendimientos logarítmicos (*log-returns*).
3. **Visión por Computador para Fitopatología ($Accuracy$ histórico del $48.9\%$ en EfficientNetB0):**
   * *Patología identificada:* Desbalance severo de clases multietiqueta y cambio de dominio visual (*domain shift*). Al fusionar RoCoLe (imágenes tomadas en campo con iluminación silvestre y fondos con suelo/follaje) con BRACOL (fotografías bajo condiciones de estudio e iluminación controlada con fondo blanco), la red convolucional memorizó atajos visuales (*shortcut learning*, e.g., clasificar la patología por el fondo o balance de blancos en lugar de los patrones necróticos foliares).

#### B. Optimización, Algoritmos Avanzados y Escalabilidad Matemática

##### Pipeline de Rendimiento Agronómico:
* **Algoritmos propuestos:** Implementar un ensamble heterogéneo tipo *Stacking Regressor* de dos niveles con meta-aprendiz:
  $$\hat{y}_{\text{stack}} = \mathcal{M}_{\text{meta}}\Big(f_{\text{XGBoost}}(X), f_{\text{LightGBM}}(X), f_{\text{CatBoost}}(X), f_{\text{Deep-MLP}}(X)\Big)$$
  donde el meta-modelo $\mathcal{M}_{\text{meta}}$ es una regresión Ridge regularizada no negativa ($w_i \ge 0, \sum w_i = 1$) para mitigar la colinealidad de los predictores base.
* **Regularización del MLP Profundo (NB07):** Reemplazar la arquitectura secuencial estándar por un diseño con conexiones residuales (*Skip-Connections / ResNet-style tabular MLP*), incorporando capas de normalización por lotes (`BatchNorm`), regularización Dropout estocástico ($p=0.3$) y activación Mish:
  $$\text{Mish}(x) = x \cdot \tanh(\ln(1 + e^x))$$

##### Pipeline Secuencial de Precios:
* **Transformación y Estacionariedad:** Transformar la serie de precio interno FNC y compuesto ICO $P_t$ en rendimientos logarítmicos continuos y componentes ondulatorias mediante descomposición Wavelet o STL (*Seasonal and Trend decomposition using Loess*):
  $$r_t = \ln(P_t) - \ln(P_{t-1})$$
* **Implementación de Arquitecturas con Atención Temporal:**
  * Implementar el **Temporal Fusion Transformer (TFT)** o un modelo híbrido **BiGRU + Mecanismo de Atención Bahdanau (Additive Attention)**:
    $$e_{ij} = v_a^T \tanh(W_a s_{i-1} + U_a h_j), \quad \alpha_{ij} = \frac{\exp(e_{ij})}{\sum_{k=1}^{T_x} \exp(e_{ik})}, \quad c_i = \sum_{j=1}^{T_x} \alpha_{ij} h_j$$
    Esto permite que el pronosticador pondere qué meses históricos o choques climáticos (eventos El Niño/La Niña de hace 6 meses) tienen mayor peso en la formación del precio actual.

##### Pipeline de Visión por Computador:
* **Mitigación de Domain Shift:** Integrar *Adversarial Domain Adaptation* o normalización por lotes específica del dominio.
* **Estrategia de Entrenamiento:** Dos etapas con *Cosine Annealing Learning Rate Warmup*:
  1. *Etapa de calentamiento:* Congelar el *backbone* (EfficientNetB3 preentrenado en ImageNet) y entrenar únicamente el clasificador denso superior con optimizador AdamW ($\eta = 10^{-3}$, peso de decaimiento $\lambda = 10^{-2}$).
  2. *Etapa de ajuste fino:* Descongelar las últimas 3 etapas de bloques MBConv (*Inverted Residual Blocks*) reduciendo la tasa de aprendizaje a $\eta = 10^{-5}$ con función de pérdida focal multiclase (*Focal Loss*):
     $$\mathcal{FL}(p_t) = -\alpha_t (1 - p_t)^\gamma \log(p_t), \quad \gamma = 2.0$$
* **Validación de Grad-CAM:** Extraer gradientes de la última capa convolucional (`top_conv` de EfficientNet) para verificar que la activación $\alpha_k^c = \frac{1}{Z}\sum_i \sum_j \frac{\partial Y^c}{\partial A_{ij}^k}$ coincida topográficamente con las pústulas de roya (*Hemileia*) o los halos concéntricos de cercospora (*Cercospora coffeicola*).

##### Detección de Anomalías de Mercado (NB12):
* Reemplazar el Autoencoder simple por un **Variational Autoencoder (VAE)** condicional o una red **Isolation Forest multivariada** acoplada con embeddings latentes del VAE.
  * *Pérdida del VAE:* Minimizar el error de reconstrucción más la divergencia de Kullback-Leibler:
    $$\mathcal{L}_{\text{VAE}}(\theta, \phi; x) = \mathbb{E}_{q_\phi(z|x)}\big[\log p_\theta(x|z)\big] - D_{\text{KL}}\big(q_\phi(z|x) \,||\, p(z)\big)$$
  * Las anomalías se determinan calculando el *Reconstruction Probability Score*. Cuando el error excede el percentil 97.5 de la distribución latente, se levanta una alerta de distorsión especulativa o shock de oferta.

---

### 2.2. INGENIEROS DE SOFTWARE / DESARROLLO

#### A. Diagnóstico de Deuda Técnica y Modularidad
El repositorio presenta un antipatrón común en proyectos de transición de laboratorio: la lógica de ingestión, preprocesamiento, modelado y evaluación reside fragmentada en cuadernos Jupyter (`02_notebooks/NB07` a `NB12`) y en scripts sueltos en `03_scripts/`. 
- **Problema de reproducibilidad:** El script `07_app_web/app.py` carga directamente artefactos `.pkl` o `.keras` sin un contrato explícito de serialización ni validación de esquemas de entrada.
- **Acoplamiento:** El código de extracción de base de datos no está encapsulado en una capa de acceso a datos (DAO/Repository Pattern), exponiendo consultas SQL abiertas y rutas de archivo codificadas en duro (*hardcoded paths*).

#### B. Plan de Refactorización a Arquitectura Limpia (Hexagonal / Clean Architecture)
Se requiere desacoplar el proyecto en un paquete instalable de Python estructurado formalmente:

```
src/
├── cafe_ia/
│   ├── __init__.py
│   ├── domain/               # Entidades de negocio puras e interfaces (Ports)
│   │   ├── models.py         # Clases dataclass/Pydantic: PrediccionRendimiento, PrecioCafe
│   │   └── repositories.py   # Protocolos abstractos para persistencia y modelos
│   ├── application/          # Casos de uso
│   │   ├── use_cases/
│   │   │   ├── predict_yield.py
│   │   │   ├── forecast_prices.py
│   │   │   └── diagnose_leaf.py
│   ├── infrastructure/       # Implementaciones concretas (Adapters)
│   │   ├── db/
│   │   │   ├── postgres_adapter.py  # SQLAlchemy 2.0 / asyncpg
│   │   │   └── migrations/          # Alembic
│   │   ├── ml/
│   │   │   ├── predictors/
│   │   │   │   ├── stacking_yield.py
│   │   │   │   ├── transformer_price.py
│   │   │   │   └── vision_classifier.py
│   │   │   └── serialization.py     # Carga segura con verificación de hash SHA-256
│   │   └── rag/
│   │       ├── chroma_store.py
│   │       └── groq_client.py
│   └── interfaces/           # Puntos de entrada
│       ├── api/              # FastAPI REST endpoints
│       │   ├── v1/
│       │   │   └── routers.py
│       │   └── schemas.py    # Esquemas de solicitud y respuesta
│       └── web/              # Streamlit app consumiendo la API o el SDK
```

#### C. Estrategia de Testing Automatizado
Configurar una suite integral basada en `pytest` cubriendo al menos un 85% de cobertura de código (`pytest-cov`):

1. **Unit Testing:**
   * Pruebas para preprocesamiento de tensores y normalización de datos tabulares (asegurar que el imputador no sufra fuga de datos (*data leakage*)).
   * Pruebas sobre la función de inferencia de imágenes: verificar que una imagen corrupta o con formato no admitido lance una excepción controlada (`UnprocessableEntityException`).
2. **Integration Testing:**
   * Verificación de transacciones de lectura/escritura contra una instancia de PostgreSQL en contenedor efímero vía `testcontainers-python`.
   * Test de carga y generación de embeddings en ChromaDB.
3. **Data & Model Quality Testing:**
   * Validaciones de contrato de entrada mediante **Pydantic v2**:

```python
from pydantic import BaseModel, Field, field_validator

class YieldPredictionInput(BaseModel):
    municipio_id: int = Field(..., gt=0, description="Código DANE del municipio")
    precipitacion_trimestre_mm: float = Field(..., ge=0.0, le=3000.0)
    temperatura_promedio_c: float = Field(..., ge=5.0, le=42.0)
    ph_suelo: float = Field(..., ge=3.0, le=9.0)
    altitud_msnm: float = Field(..., ge=500.0, le=2600.0)

    @field_validator("ph_suelo")
    def validate_ph(cls, v):
        if v < 4.0 or v > 7.5:
            # Advertencia agronómica fuera de rango óptimo
            pass
        return v
```

#### D. Pipeline de Integración y Entrega Continua (CI/CD)
Implementar flujos de trabajo en `.github/workflows/ci-cd.yml`:
1. **Linting & Type Checking:** `ruff check .`, `black --check .`, `mypy --strict src/`.
2. **Security Scanning:** `bandit -r src/`, `pip-audit` o `Trivy` para detectar CVEs en dependencias.
3. **Automated Testing:** `pytest --cov=src --cov-report=xml tests/`.
4. **Artifact Build & Packaging:** Creación de imagen Docker optimizada de producción y publicación en GitHub Container Registry (GHCR) tras pasar la rama `main`.

---

### 2.3. INGENIEROS DE DATOS (DATA ENGINEERS)

#### A. Diagnóstico de la Infraestructura de Almacenamiento y Pipelines
- **Base de datos actual:** El esquema en estrella sobre **PostgreSQL 18** (`03_scripts/bd/01_ddl_schema.sql` y `02_carga_inicial.py`) es una base adecuada, pero carece de particionamiento físico, índices espaciales y orquestación programada.
- **Ingesta:** Los scripts de descarga (`03_scripts/descarga/00_ejecutar_todo.py` y scripts del 01 al 06) operan de manera síncrona, lineal y sin políticas de reintentos (*exponential backoff*), lo que hace que un error de red en fuentes como FRED o FNC interrumpa todo el proceso de actualización.

#### B. Optimización del Esquema Dimensional en PostgreSQL 18
El modelo en estrella debe incorporar índices analíticos BRIN (*Block Range Index*) para series temporales masivas e índices GiST para datos geográficos:

```sql
-- Optimizacion de Tablas de Hechos y Dimensiones en PostgreSQL 18

-- 1. Dimensión Municipio con soporte geoespacial
CREATE TABLE dim_municipio (
    sk_municipio SERIAL PRIMARY KEY,
    codigo_dane VARCHAR(10) UNIQUE NOT NULL,
    nombre_municipio VARCHAR(100) NOT NULL,
    departamento VARCHAR(100) NOT NULL,
    altitud_media NUMERIC(7,2),
    geom GEOMETRY(MultiPolygon, 4326) -- PostGIS para cruce vectorial con imágenes de satélite
);

CREATE INDEX idx_dim_municipio_geom ON dim_municipio USING GIST(geom);

-- 2. Hecho Precios Particionado por Rango Anual
CREATE TABLE hecho_precios_mercado (
    sk_tiempo INT NOT NULL,
    sk_mercado INT NOT NULL,
    precio_interno_fnc_carga NUMERIC(12,2),
    precio_ico_centavos_lb NUMERIC(8,2),
    trm_pesos_usd NUMERIC(8,2),
    fecha_registro DATE NOT NULL,
    CONSTRAINT pk_hecho_precios PRIMARY KEY (fecha_registro, sk_tiempo, sk_mercado)
) PARTITION BY RANGE (fecha_registro);

-- Particiones históricas y activas
CREATE TABLE hecho_precios_1990_2010 PARTITION OF hecho_precios_mercado
    FOR VALUES FROM ('1990-01-01') TO ('2011-01-01');

CREATE TABLE hecho_precios_2011_2020 PARTITION OF hecho_precios_mercado
    FOR VALUES FROM ('2011-01-01') TO ('2021-01-01');

CREATE TABLE hecho_precios_2021_2030 PARTITION OF hecho_precios_mercado
    FOR VALUES FROM ('2021-01-01') TO ('2031-01-01');

-- Índice BRIN para consultas ultrarrápidas de series de tiempo
CREATE INDEX idx_hecho_precios_fecha_brin ON hecho_precios_mercado USING BRIN(fecha_registro);
```

#### C. Orquestación y Gobernanza de Pipelines de Ingesta (ELT)
1. **Orquestación con Apache Airflow / Prefect:** Sustituir la ejecución por script manual (`00_ejecutar_todo.py`) por un DAG (*Directed Acyclic Graph*) estructurado:
   * **Task 1: `extract_climate_data`:** Consulta API satelital ERA5-Land y estaciones IDEAM concurrentemente mediante `aiohttp`.
   * **Task 2: `extract_market_data`:** Extracción paralela de APIs de FRED, FNC, Banco Mundial e ICO con reintentos automáticos y caché local.
   * **Task 3: `data_validation_gate`:** Ejecución de suites de validación con **Great Expectations**:
     * Comprobar que no haya valores nulos en el precio del café.
     * Validar que la precipitación se encuentre dentro de rangos físicamente admisibles ($[0, 500]\text{ mm/día}$).
     * Verificar que las coordenadas geográficas de los polígonos municipales caigan dentro de los límites de la República de Colombia.
   * **Task 4: `dbt_transformations`:** Transformación de tablas *staging* a capas *bronze*, *silver* y *gold* en el esquema estrella.
2. **Escalabilidad a Grandes Volúmenes de Imágenes:**
   * Almacenar las ~10.000 imágenes de patología no en el sistema de archivos del servidor web, sino en un *Object Storage* compatible con S3 (MinIO / AWS S3).
   * Almacenar únicamente los metadatos, firmas hash criptográficas y URLs pre-firmadas en la tabla `hecho_diagnostico_visual` de PostgreSQL.

---

## 3. PROFESIONALES ANALÍTICOS

```
====================================================================================================
ÁREA: PROFESIONALES ANALÍTICOS
ROLES: DATA ANALYSTS | DATA SCIENTISTS
====================================================================================================
```

### 3.1. ANALISTAS DE DATOS

#### A. Diagnóstico de Visualización y Análisis Descriptivo Actual
La aplicación actual en Streamlit (`07_app_web/app.py`) proporciona tableros funcionales pero con limitaciones en el diseño analítico:
- Predominio de gráficos de series temporales estándar sin bandas de confianza ni identificación de puntos de quiebre estructural.
- Visualización de rendimiento municipal restringida a tablas estáticas o mapas coropléticos sin normalización por tamaño de área cosechada.
- Ausencia de correlación interactiva entre variables climatológicas (anomalías de lluvia en fases de floración) y fluctuaciones de oferta.

#### B. Propuesta de Análisis Exploratorio Profundo (EDA Avanzado)
1. **Análisis de Descomposición Causal del Rendimiento Municipal:**
   * Construcción de una matriz de dispersión bivariada condicionada por pisos térmicos cafeteros (Óptimo: 1.200 – 1.800 m.s.n.m.; Marginal bajo: < 1.200 m.s.n.m.; Marginal alto: > 1.800 m.s.n.m.).
   * Cálculo de coeficientes de correlación de Spearman y de distancia (*Distance Correlation*) para detectar dependencias no lineales entre el pH del suelo, la concentración de materia orgánica y la productividad en sacos de 60 kg por hectárea.
2. **Análisis de Volatilidad Histórica y *Drawdowns* del Precio de Sustentación:**
   * Gráficos de distribución de densidad por periodos macroeconómicos (Pacto Internacional del Café antes de 1989 vs. Libre mercado posterior a 1989).
   * Identificación visual de los picos inflacionarios de los insumos agrícolas (fertilizantes durante la crisis geopolítica de 2022) contrastados contra el ingreso neto del caficultor.

#### C. Tableros Interactivos y Reportabilidad Ejecutiva
* **Mapas Coropléticos Avanzados con Deck.gl / PyDeck:** Visualización 3D en capas donde la elevación de las columnas representa el rendimiento promedio (ton/ha) y el mapa de calor de color indica la incidencia epidemiológica de roya o deficiencia nutricional.
* **Diagramas de Sankey para Trazabilidad del Grano:** Flujo analítico que ilustre el volumen municipal cosechado, clasificaciones de calidad física (factor de rendimiento en trilla) y su distribución final hacia consumo doméstico o exportación de cafés especiales.

---

### 3.2. CIENTÍFICOS DE DATOS (DATA SCIENTISTS)

#### A. Feature Engineering Avanzado
El bajo rendimiento predictivo previo en rendimiento agronómico ($R^2 = 0.067$) se resuelve dotando a los algoritmos de variables con fundamento agronómico y biometeorológico:

```
+----------------------------------------------------------------------------------------------------+
|                                MATRIZ DE INGENIERÍA DE CARACTERÍSTICAS                             |
+----------------------------------------------------------------------------------------------------+
  1. ÍNDICES BIOCLIMÁTICOS Y AGROMETEOROLÓGICOS CON RETARDOS (LAGS)
     * Grados Día de Desarrollo (GDD - Growing Degree Days):
       GDD_t = sum_{i=1}^N max(0, ((T_max + T_min)/2) - T_base),  con T_base = 10 °C
     * Déficit de Presión de Vapor (VPD - Vapor Pressure Deficit):
       Estimador del estrés hídrico que induce el cierre estomático y frena la fotosíntesis.
     * Ventanas Móviles de Precipitación acumulada:
       30 días previos a la antesis (inducción floral) y 90 días en fase de llenado de grano.

  2. CARACTERÍSTICAS EDAFOLÓGICAS Y TOPOGRÁFICAS
     * Índice de Radiación Solar Topográfica (TPI - Topographic Position Index) a partir del DEM.
     * Balance Catiónico del Suelo: Relación (Ca + Mg) / K y porcentaje de Saturación de Aluminio.

  3. VARIABLES MACROECONÓMICAS Y FINANCIERAS PARA SERIES DE TIEMPO
     * Diferencial del Café Colombiano (Prima sobre Contrato C en ICE Nueva York).
     * Volatilidad Implícita del Tipo de Cambio USD/COP (rolling standard deviation de 30 y 90 días).
     * Indicador ONI (Oceanic Niño Index): Variable continua que mide anomalías de SST en región Niño 3.4.
```

#### B. Validación Estadística Rigurosa y Prevención de Data Leakage
1. **Esquema de Validación Cruzada Temporal (TimeSeriesSplit / Purged Group TimeSeries Split):**
   * *Prohibición estricta de K-Fold tradicional:* En series financieras y rendimientos agronómicos históricos, el K-Fold aleatorio ocasiona fuga masiva del futuro hacia el pasado.
   * *Metodología:* Implementar *Expanding Window Backtesting* con periodo de purga (*Purging Window*) y embargo (*Embargoing Window*) de al menos 90 días para eliminar la autocorrelación residual:

```
[ Train: 1990 - 2015 ] -> [ Purge 90d ] -> [ Val: 2016 - 2018 ]
[ Train: 1990 - 2018 ] -> [ Purge 90d ] -> [ Val: 2019 - 2021 ]
[ Train: 1990 - 2021 ] -> [ Purge 90d ] -> [ Val: 2022 - 2024 ]
[ Train: 1990 - 2024 ] -> [ Purge 90d ] -> [ Test: 2025 - 2026 ]
```

2. **Validación Espacial Cruzada (Spatial Spatial Block K-Fold):**
   * En el modelo de rendimiento municipal, evitar que municipios colindantes del mismo departamento caigan simultáneamente en entrenamiento y prueba, ya que comparten el mismo régimen climático regional. Agrupar los folds por Unidades Edafológicas Homogéneas de Cenicafé o por cuencas hidrográficas.
3. **Pruebas de Hipótesis y Significancia Estadística:**
   * Evaluar si la superioridad del modelo Stacking o Transformer es estadísticamente significativa frente a modelos basales autorregresivos (ARIMA / SARIMAX) mediante la **Prueba de Diebold-Mariano**:
     $$DM = \frac{\bar{d}}{\sqrt{\hat{V}(\bar{d})}} \sim \mathcal{N}(0, 1), \quad d_t = e_{1,t}^2 - e_{2,t}^2$$
   * Contrastar la significancia de los coeficientes de Shapley (**SHAP values**) para confirmar que la precipitación y la altitud tengan un impacto físico congruente sobre las predicciones de rendimiento.

---

## 4. PROFESIONALES DE NEGOCIO

```
====================================================================================================
ÁREA: PROFESIONALES DE NEGOCIO
ROLES: BUSINESS ANALYSTS | ECONOMISTS | DOMAIN EXPERTS
====================================================================================================
```

### 4.1. ANALISTAS DE NEGOCIOS / BUSINESS ANALYSTS

#### A. Alineación Estratégica con los Objetivos del Gremio Cafetero
El desarrollo tecnológico de IA en el sector caficultor solo genera valor si responde a las decisiones que toman los actores clave de la cadena:
- **Comités Departamentales y Municipales de Cafeteros:** Planificación de compras de café de sustentación y asignación de créditos rotativos.
- **Cooperativas de Caficultores:** Gestión del riesgo de cobertura física en contratos a futuro frente a fluctuaciones en la Bolsa de Nueva York.
- **Extensionistas y Asistentes Técnicos:** Focalización geográfica de visitas agronómicas basadas en riesgo preventivo de plagas y estrés hídrico.

#### B. Análisis de Retorno de Inversión (ROI) y Matriz de Costo-Beneficio
Para un departamento con 50.000 hectáreas sembradas (ej. Huila, Antioquia o Valle del Cauca):

```
+----------------------------------------------------------------------------------------------------+
|                      CASO DE NEGOCIO: IMPACTO ECONÓMICO ANUALIZADO (SIMULACIÓN)                    |
+----------------------------------------------------------------------------------------------------+
  1. MITIGACIÓN DE DAÑOS POR ROYA Y PLAGAS (CV DIAGNÓSTICO TEMPRANO)
     * Incidencia promedio no tratada: Pérdida del 15% del volumen cosechado.
     * Con diagnóstico temprano (CV + RAG): Reducción del daño al 6% (ahorro de 9 puntos porcentuales).
     * Beneficio económico estimado:
       50.000 ha * 1.3 ton/ha = 65.000 ton de café pergamino seco.
       9% recuperado = 5.850 ton (aprox. 46.800 cargas de 125 kg).
       Valor de rescate (a $2.000.000 COP/carga) = $93.600.000.000 COP (~$23,4 M USD).

  2. GESTIÓN DE COBERTURA DE PRECIOS (TRANSFORMER + ANOMALY DETECTION)
     * Reducción del margen de error en ventas a futuro anticipando picos o colapsos.
     * Estimación de optimización en precio de venta: +2.5 centavos de dólar/lb.
     * Beneficio en un volumen exportable de 500.000 sacos (60 kg) = ~$1,65 M USD.

  3. COSTOS ESTIMADOS DE IMPLEMENTACIÓN Y OPERACIÓN TECNOLÓGICA (CLOUD + IA)
     * Infraestructura Cloud (PostgreSQL administrado + Servidores GPU Inferencia): $45.000 USD/año.
     * Mantenimiento, MLOps, licencias y conectividad rural: $120.000 USD/año.
     * Total OPEX tecnológico: $165.000 USD/año.
  
  4. RELACIÓN BENEFICIO / COSTO: > 50 : 1 en escenarios cooperativos consolidados.
```

#### C. Matriz de Riesgo Operativo y Mitigación
* **Riesgo de adopción tecnológica:** Brecha digital de pequeños productores (edad promedio > 55 años). *Mitigación:* Integrar el agente RAG no solo en web, sino a través de bots conversacionales accesibles por WhatsApp / SMS o audio.
* **Riesgo de falsos negativos en enfermedades:** Clasificar una hoja infectada con Roya como "Sana" retrasa la aplicación de fungicidas. *Mitigación:* Calibrar el umbral de decisión (*threshold tuning*) de la red convolucional para favorecer el *Recall* ($\ge 0.95$) a costa de una leve penalización en la precisión.

---

### 4.2. ECONOMISTAS / ANALISTAS ECONÓMICOS

#### A. Dinámica Estructural del Mercado del Café en Colombia
El precio pagado al caficultor por carga de 125 kg de café pergamino seco (precio interno FNC) responde a una ecuación fundamental de transmisión de precios:

$$P_{\text{interno}} = \left( \frac{(P_{\text{ICE\_C}} + \text{Diferencial}) \cdot \text{TRM} \cdot 125}{100} \right) \cdot \text{Factor Rendimiento} - \text{Costos de Transformación y Contribución}$$

donde:
- $P_{\text{ICE\_C}}$ es la cotización del Contrato «C» en la Bolsa Intercontinental de Nueva York (centavos de dólar por libra).
- $\text{Diferencial}$ es la prima de calidad por Café Colombiano Suave Lavado.
- $\text{TRM}$ es la Tasa de Cambio Representativa del Mercado (COP/USD).
- $\text{Factor Rendimiento}$ mide los kilos de café pergamino necesarios para obtener un saco de 70 kg de café excelso de exportación (estándar base: 92.8 kg).

#### B. Modelado Econométrico y Análisis de Cointegración
1. **Pruebas de Raíz Unitaria y Cointegración:**
   * Comprobar que las series de tiempo (Precio FNC, Cotización ICO, TRM) son $I(1)$ mediante las pruebas **Augmented Dickey-Fuller (ADF)** y **Kwiatkowski-Phillips-Schmidt-Shin (KPSS)**.
   * Realizar la **Prueba de Cointegración de Johansen** para identificar la existencia de relaciones de equilibrio de largo plazo entre el mercado local e internacional.
2. **Modelo de Corrección de Errores Vectorial (VECM) vs. Deep Learning:**
   * Contrastar las predicciones del modelo Transformer con un modelo VECM:
     $$\Delta Y_t = \Pi Y_{t-1} + \sum_{i=1}^{p-1} \Gamma_i \Delta Y_{t-i} + \Phi D_t + \varepsilon_t$$
     donde $\Pi = \alpha \beta'$ contiene el vector de cointegración $\beta$ y la velocidad de ajuste $\alpha$.
   * Utilizar la descomposición de varianza del error de pronóstico (FEVD) y funciones de impulso-respuesta (IRF) para cuantificar cuántos periodos tarda un shock de la tasa de cambio TRM en trasladarse completamente al precio interno de compra.

#### C. Impacto de Choques Climáticos Macroeconómicos (Fenómenos ENSO)
* Los ciclos de El Niño (déficit de precipitación y aumento de temperatura) incrementan la proliferación de plagas como la Broca (*Hypothenemus hampei*) y generan grano averanado (menor densidad, castigo en el factor de rendimiento).
* Los eventos de La Niña (exceso de lluvias y reducción de brillo solar) disminuyen la polinización y elevan la humedad relativa, detonando epidemias de Roya (*Hemileia vastatrix*).
* La inclusión del índice oceánico ONI en los modelos predictivos es fundamental para modelar los shocks de oferta global provenientes de Brasil y Vietnam, principales determinantes del precio de equilibrio global.

---

### 4.3. ESPECIALISTAS EN DOMINIO (INGENIEROS AGRÓNOMOS / EXTENSIONISTAS / CENICAFÉ)

#### A. Agrometeorología y Fisiología del Cafeto (*Coffea arabica*)
1. **Rango de Adaptación Ecológica:**
   * El cafeto arábico en Colombia prospera entre los 1.200 y 1.800 m.s.n.m. (con extensiones viables hasta los 2.100 m.s.n.m. debido al cambio climático).
   * Temperatura media óptima: 18 °C a 22 °C. Temperaturas superiores a 30 °C provocan estrés térmico y aborto floral.
   * Requerimiento hídrico: 1.500 a 2.500 mm anuales bien distribuidos, con una fase seca obligatoria de 4 a 6 semanas que estimule la inducción y reposo de las yemas florales.
2. **Propiedades Químicas y Edafológicas del Suelo:**
   * El modelo de machine learning debe considerar que el pH óptimo oscila entre 5.0 y 5.5 (suelos derivados de cenizas volcánicas / Andisoles).
   * Suelos con pH < 4.5 presentan toxicidad por aluminio libre ($Al^{3+}$), bloqueando la asimilación de fósforo ($P$) y limitando drásticamente el desarrollo radicular y el rendimiento por hectárea.

#### B. Patología Vegetal y Diagnóstico Computacional
Alineación técnica de las clases del modelo de visión por computador (`02_notebooks/NB08`) con la sintomatología real de campo:

```
+----------------------------------------------------------------------------------------------------+
|                            TAXONOMÍA DE ENFERMEDADES FOLIARES DEL CAFÉ                             |
+----------------------------------------------------------------------------------------------------+
  1. ROYA DEL CAFETO (Hemileia vastatrix)
     * Signos visuales: Pústulas cloróticas pulverulentas de color amarillo-naranja en el envés
       de la hoja. En fases avanzadas genera necrosis irregular y defoliación prematura severa.
     * Condición predisponente: Agua libre en la hoja y temperaturas de 21 °C a 25 °C.

  2. MANCHA DE HIERRO (Cercospora coffeicola)
     * Signos visuales: Manchas circulares pequeñas de color pardo o castaño, con halo amarillo
       periférico translúcido y centro blanco cenizo.
     * Indicador agronómico: Síntoma inequívoco de deficiencia de Nitrógeno o exceso de insolación.

  3. GOTERA U OJO DE GALLO (Mycena citricolor)
     * Signos visuales: Lesiones circulares u ovaladas bien delimitadas, color pardo claro a pajizo,
       donde la epidermis foliar termina perforándose o desprendiéndose.
     * Condición predisponente: Alta humedad relativa (> 90%), sombrío excesivo y drenaje deficiente.

  4. MUERTE DESCENDENTE / FOMA (Phoma costarricensis)
     * Signos visuales: Lesiones oscuras, necróticas y acuosas en los bordes apicales de la hoja
       que progresan hacia las nervaduras, secando el tejido tierno.
     * Condición predisponente: Vientos fríos de altura (> 1.800 m.s.n.m.) combinados con llovizna.

  5. MINADOR DE LA HOJA (Leucoptera coffeella)
     * Signos visuales: Galerías o minas irregulares de color café rojizo provocadas por la larva,
       ocasionando enrollamiento y pérdida de la capacidad fotosintética.
```

#### C. Validación de Grad-CAM para Evitar Sesgos Diagnósticos
Los agrónomos deben someter a prueba las explicaciones visuales generadas por Grad-CAM:
* Si la atención de la red neuronal se concentra en la nervadura central sana o en la punta de la hoja recortada, la inferencia debe ser rechazada como espuria (*Clever Hans effect*).
* El mapa de activación térmica debe concentrarse estrictamente en el área de la pústula o lesión necrótica activa.

---

## 5. PROFESIONALES DE SOPORTE

```
====================================================================================================
ÁREA: PROFESIONALES DE SOPORTE
ROLES: DEVOPS / MLOPS ENGINEERS | DATA VISUALIZATION & UX/UI DESIGNERS
====================================================================================================
```

### 5.1. INGENIEROS DEVOPS / MLOPS

#### A. Diagnóstico de la Infraestructura y Despliegue Actual
- **Estado de Docker:** El directorio `08_docker/` contiene un `Dockerfile` y un archivo `docker-compose.yml` que orquestan el contenedor web y la base de datos.
- **Vulnerabilidades y Oportunidades de Mejora:**
  1. *Tamaño de imagen:* El uso de imágenes base monolíticas de Python genera contenedores superiores a 4 GB al incluir bibliotecas pesadas de Deep Learning (`tensorflow`, `torch`, `transformers`).
  2. *Seguridad:* Ejecución de procesos bajo el usuario `root` dentro de los contenedores.
  3. *Inexistencia de Model Registry y Monitoreo MLOps:* No hay rastreo de experimentos ni versionamiento de modelos (.keras/.pkl están en el repositorio Git, violando las buenas prácticas de versionado de artefactos binarios pesados).

#### B. Endurecimiento de Contenedores (Dockerfile Multi-Stage Optimizado)
Refactorización para generar una imagen ligera, segura y no privilegiada:

```dockerfile
# ==============================================================================
# Multi-Stage Dockerfile para Café IA Web API / Streamlit
# ==============================================================================

# Etapa 1: Build y compilación de dependencias
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Etapa 2: Runtime de Producción
FROM python:3.11-slim-bookworm AS runner

WORKDIR /app
ENV PATH="/home/cafeapp/.local/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Instalar librerías de sistema mínimas para OpenCV y PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario sin privilegios
RUN useradd -m -u 10001 cafeapp && \
    chown -R cafeapp:cafeapp /app

COPY --from=builder --chown=cafeapp:cafeapp /root/.local /home/cafeapp/.local
COPY --chown=cafeapp:cafeapp . /app

USER 10001

EXPOSE 8501 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "07_app_web/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### C. Arquitectura MLOps: Registro, Versionado y Monitoreo Continuo
1. **Model Registry y Versionamiento con MLflow y DVC:**
   * Extraer los modelos binarios (`04_modelos_entrenados/*.pkl`, `*.keras`) del árbol de Git.
   * Integrar **Data Version Control (DVC)** apuntando a un bucket S3 para versionar datasets e imágenes foliares.
   * Utilizar **MLflow Tracking Server** para registrar hiperparámetros, pesos sinápticos, métricas y firmas de entrada/salida de cada ejecución de entrenamiento.
2. **Monitoreo de Data Drift y Concept Drift en Producción:**
   * Implementar **Evidently AI** o **Whylogs** para auditar el tráfico de inferencia en tiempo real.
   * *Data Drift:* Detectar si las distribuciones climáticas entrantes (precipitaciones extremas no vistas) difieren del histórico mediante la **Prueba de Kolmogorov-Smirnov** o la divergencia de Wasserstein.
   * *Concept Drift:* Monitorear la degradación de precisión en predicción de precios cuando cambian los regímenes de tasas de interés o estallan crisis geopolíticas mundiales.
   * Generar alertas automatizadas vía Slack / PagerDuty para reentrenamiento periódico programado (*Retraining Pipeline Trigger*).

---

### 5.2. ESPECIALISTAS EN VISUALIZACIÓN DE DATOS / DISEÑO UX-UI

#### A. Diagnóstico de la Experiencia de Usuario Actual
- La aplicación actual de Streamlit (`07_app_web/app.py`) agrupa todos los perfiles de usuario dentro de una misma interfaz jerárquica.
- La densidad de información es excesiva para un operario en campo y carece de opciones de visualización simplificadas para dispositivos móviles bajo condiciones de alto brillo solar en fincas cafeteras.
- El agente RAG carece de citas visuales claras y no ofrece un formato de respuesta estructurado para recomendaciones fitosanitarias de aplicación inmediata.

#### B. Arquitectura de Información y Rediseño Centrado en el Usuario (UCD)
Se propone dividir la experiencia en **tres vistas personalizadas según el rol del usuario**:

```
+----------------------------------------------------------------------------------------------------+
|                         MATRIZ UX/UI: PERFILES DE USUARIO Y EXPERIENCIAS                           |
+----------------------------------------------------------------------------------------------------+
  1. VISTA EXTENSIONISTA / PRODUCTOR (MOBILE-FIRST, BAJO CONSUMO DE DATOS)
     * Enfoque: Operativo, directo y de alta legibilidad en exteriores (alto contraste visual).
     * Módulos destacados:
       - Captura Rápida de Imagen: Carga de foto de hoja con retroalimentación inmediata del diagnóstico.
       - Semáforo de Riesgo Sanitario: Verde (Sano), Amarillo (Monitoreo), Rojo (Tratamiento Urgente).
       - Ficha Técnica de Tratamiento: Dosificación recomendada y productos autorizados por el ICA.
       - Asistente RAG con Notas de Voz: Interfaz de audio bidireccional (Whisper + TTS).

  2. VISTA COMERCIAL / COOPERATIVAS (DESKTOP ANALYTICS)
     * Enfoque: Análisis de mercado, pronóstico de precios y gestión de contratos de futuro.
     * Módulos destacados:
       - Simulador de Precio Interno: Modificación interactiva de TRM, ICE Contrato C y Factor de Rendimiento.
       - Monitor de Anomalías de Mercado con visualización de probabilidades del VAE.
       - Bandas de Confiabilidad Temporal: Visualización de conos de incertidumbre a 30, 60 y 90 días.

  3. VISTA GREMIAL / DIRECTIVA FNC (EXECUTIVE COCKPIT)
     * Enfoque: Macrotendencias, mapas de calor agregados y balance oferta-demanda nacional.
     * Módulos destacados:
       - Mapa Estratégico Municipal 3D: Cosecha estimada nacional en millones de sacos de 60 kg.
       - Alertas Tempranas Climáticas: Superposición de mapas de anomalías térmicas y de precipitación.
```

#### C. Principios de Diseño Visual y Accesibilidad
* **Paleta de Colores Agronómica Funcional:** 
  * Fondo Neutro: `#F8F9FA` (Modo Día) / `#121614` (Modo Noche).
  * Color Primario (Verde Follaje Saludable): `#2D6A4F`.
  * Color Secundario (Café Pergamino Maduro): `#8B4513` / `#A36638`.
  * Estados de Alerta: Éxito (`#38B000`), Advertencia/Cercospora (`#FFB703`), Peligro/Roya Crítica (`#D90429`).
* **Accesibilidad Web (Cumplimiento WCAG 2.1 Nivel AA):**
  * Contraste cromático mínimo de 4.5:1 en todos los textos e indicadores numéricos.
  * Compatibilidad con lectores de pantalla en gráficos vectoriales mediante atributos `aria-label` descriptivos.
  * Diseño táctil con áreas interactivas mínimas de $48 \times 48\text{ px}$ para uso con dedos enguantados o manchados en labores de cosecha.

---

## 6. SÍNTESIS DE LA MATRIZ DE TRANSFORMACIÓN Y ROADMAP DE IMPLEMENTACIÓN

Para garantizar una transición exitosa desde el repositorio actual hacia un entorno de producción de alta disponibilidad, se establece la siguiente matriz priorizada de intervenciones técnicas:

| Fase | Área / Rol | Intervención Clave | Métrica de Éxito / Entregable |
| :--- | :--- | :--- | :--- |
| **Fase 1** *(Corto Plazo: Mes 1)* | **ML / DS** | Corrección de fuga de datos en series de tiempo y entrenamiento de Stacking para rendimiento | $R^2 \ge 0.55$ en rendimiento; $R^2 \ge 0.60$ en precios sin autocorrelación trivial |
| **Fase 1** *(Corto Plazo: Mes 1)* | **Ing. Software** | Modularización de notebooks a paquete `cafe_ia` y creación de suite de tests en `pytest` | Cobertura de código $\ge 80\%$; pipeline CI/CD en GitHub Actions funcional |
| **Fase 2** *(Medio Plazo: Mes 2)* | **Ing. Datos** | Particionamiento en PostgreSQL 18, soporte PostGIS e ingesta asíncrona con validaciones | Carga idempotente de datos con Great Expectations; tiempos de consulta < 150 ms |
| **Fase 2** *(Medio Plazo: Mes 2)* | **DevOps / MLOps**| Implementación de Dockerfile multi-stage, integración con MLflow y DVC en almacenamiento S3 | Imagen Docker reducida a < 800 MB; trazabilidad del 100% de los modelos serializados |
| **Fase 3** *(Largo Plazo: Mes 3)* | **UX/UI & Negocio**| Despliegue de vistas diferenciadas en Streamlit/React, integración WhatsApp para el Agente RAG | Evaluación de usabilidad SUS > 85; adopción demostrada por comités departamentales |
| **Fase 3** *(Largo Plazo: Mes 3)* | **Economía & Dominio**| Incorporación formal de la fórmula de transmisión de precios FNC y validación fitosanitaria en campo | Validación agrometeorológica por Cenicafé; calibración del recall de roya al $98\%$ |

---

## 7. CONCLUSIÓN Y DICTAMEN TÉCNICO FINAL

El proyecto **«Sistema Integral de IA Agrícola — Café Colombia»** de Cárdenas y Díaz Urrego constituye un ejercicio académico y tecnológico de alto valor conceptual que integra con éxito las cuatro unidades formativas de Inteligencia Artificial (ML clásico, Redes Profundas, Visión Artificial, Modelos Secuenciales, Modelos Generativos y RAG).

Sin embargo, para superar el estado de prototipo de laboratorio y convertirse en un referente tecnológico para la agroindustria colombiana, debe **superar la fragmentación del código basada en notebooks, eliminar la trampa estadística de persistencia en las series temporales de precios, corregir el desacoplamiento biológico en la predicción del rendimiento e implementar una arquitectura de microservicios limpia, contenerizada y monitoreada continuamente**. 

La ejecución del plan de trabajo propuesto en este informe permitirá a las organizaciones cafeteras transformar estas herramientas analíticas en un escudo preventivo frente al cambio climático y en una palanca de rentabilidad directa para las más de 540.000 familias caficultoras del país.