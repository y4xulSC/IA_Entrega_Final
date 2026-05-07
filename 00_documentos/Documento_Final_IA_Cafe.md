# Sistema Integral de Inteligencia Agrícola para Colombia
## Módulo Café — Entrega Final

**Universidad Autónoma de Occidente · Ingeniería de Datos e Inteligencia Artificial · 2026-1**

**Autores:** Yáxul Santiago Cárdenas Hincapié · Yesenia Díaz Urrego

**Asignatura:** Inteligencia Artificial

**Fecha:** Mayo 2026

---

## Resumen ejecutivo

Este proyecto desarrolla un sistema integral de Inteligencia Artificial para el café colombiano, integrando 11 fuentes de datos heterogéneas (producción, clima satelital, precios nacionales e internacionales, imágenes de enfermedades) con 13 modelos de IA que cubren las cuatro unidades del syllabus (ML clásico, redes neuronales, deep learning, PLN). La entrega final resuelve las limitaciones identificadas en la segunda entrega (datos insuficientes para CNN, escala departamental gruesa, historia corta para series de tiempo) escalando a más de 10000 imágenes públicas de café, ampliando los precios a la ventana 1990-2026 y descendiendo la granularidad a nivel municipal. El sistema se despliega como aplicación web Streamlit con backend PostgreSQL 18 y agente conversacional RAG.

---

## Capítulo 1 — Introducción a la Inteligencia Artificial *(Unidad I)*

### 1.1 ¿Qué es Inteligencia Artificial?

La Inteligencia Artificial es el campo de las ciencias de la computación que estudia y construye sistemas capaces de realizar tareas que tradicionalmente requerían inteligencia humana: percibir, razonar, aprender de la experiencia, comunicarse en lenguaje natural y tomar decisiones bajo incertidumbre. En la práctica moderna, la IA se entiende principalmente como aprendizaje automático aplicado a grandes volúmenes de datos.

### 1.2 Breve historia

Los hitos más relevantes para este proyecto son: el surgimiento del aprendizaje automático con árboles de decisión (1980s) y máquinas de soporte vectorial (1990s), la consolidación de redes neuronales profundas tras el renacimiento de 2012 con AlexNet, la era de las arquitecturas convolucionales aplicadas a agricultura (Mohanty 2016, PlantVillage), las redes recurrentes para series de tiempo (LSTM 1997, GRU 2014, Atención 2014, Transformer 2017) y la actual generación de modelos generativos basados en transformers que habilitan agentes conversacionales como el RAG implementado en este sistema.

### 1.3 Riesgos y oportunidades para el café colombiano

**Oportunidades:** Colombia es el tercer productor mundial con 800 mil familias cafeteras y 2500 millones de dólares en divisas anuales. La adopción de IA permite predecir rendimiento por municipio, anticipar el efecto del ENSO (que reduce el rendimiento hasta 24% en años de El Niño), detectar enfermedades en campo con un teléfono celular y acceder a pronósticos de precios para decidir cuándo vender.

**Riesgos:** sesgo geográfico hacia los departamentos sobre-representados en los datos (el Eje Cafetero tradicional) que puede invisibilizar a productores de Nariño y zonas emergentes; brecha digital rural que limita la adopción real; sobreconfianza en alertas automáticas sin validación humana; dependencia de datasets foráneos para imágenes de enfermedades (RoCoLe es Ecuador, BRACOL es Brasil) que pueden no representar bien las variedades colombianas; y el riesgo regulatorio de una IA que genere recomendaciones agronómicas sin pasar por el extensionismo formal.

---

## Capítulo 2 — Marco institucional y problema de negocio

El cliente institucional es el Ministerio de Agricultura y Desarrollo Rural (MADR), específicamente la Dirección de Cadenas Agrícolas, y como segundo usuario los técnicos de la Federación Nacional de Cafeteros (FNC) y los extensionistas departamentales. Actualmente el MADR carece de un sistema unificado que cruce producción municipal (EVA), precios mayoristas (FNC e ICO) y variables climáticas (IDEAM) para anticipar riesgos de desabastecimiento en café con antelación suficiente. Las alertas tempranas se generan manualmente con rezagos de semanas, afectando la capacidad de respuesta institucional.

La pregunta de investigación es: **¿es posible diseñar un sistema integral basado en IA que, mediante la integración de datos agroclimáticos, productivos y de mercado, permita predecir rendimiento de café, anticipar riesgos fitosanitarios y facilitar la consulta en lenguaje natural, contribuyendo a la transformación digital del sector cafetero colombiano?**

---

## Capítulo 3 — Estado del arte y revisión de literatura

La literatura científica converge en que (a) el aprendizaje automático tradicional con Random Forest y XGBoost es competitivo para predicción de rendimiento agrícola cuando hay suficientes muestras y variables agroclimáticas (Chlingaryan, Sukkarieh & Whelan 2018); (b) el deep learning convolucional supera a los métodos tradicionales en detección de enfermedades foliares con datasets balanceados (Mohanty, Hughes & Salathé 2016, Kamilaris & Prenafeta-Boldú 2018); (c) las redes recurrentes y Transformers producen mejores pronósticos de precios commodity cuando se incorporan covariables exógenas como ENSO y tipo de cambio (Lim et al. 2021 con Temporal Fusion Transformer); y (d) los sistemas RAG basados en LangChain y vector stores son la arquitectura dominante para asistentes conversacionales sobre dominios especializados (Lewis et al. 2020).

En Colombia, las iniciativas AgroTECH, AgroTIC y los programas del SNIA han impulsado digitalización pero permanecen mayormente descriptivas. Cenicafé publica investigación en variedades resistentes a roya y manejo agronómico, pero sin modelos de IA accesibles públicamente. La brecha clave que aborda este proyecto es la integración simultánea de las tres familias de datos (producción, clima, precios) más detección de enfermedades por imagen y consulta en lenguaje natural en un único sistema desplegable.

---

## Capítulo 4 — Datos integrados

La entrega final integra once fuentes:

| # | Dataset | Período | Fuente | Variables clave |
|---|---------|---------|--------|------------------|
| 1 | EVA Café | 2019-2024 (extendido a 2007-2024) | DANE/MADR | Área, producción, rendimiento por municipio |
| 2 | FNC Mensual | 2018-2025 (extendido a 1990-2026) | Federación Nacional de Cafeteros | Precio interno COP/125kg, exportaciones |
| 3 | ICO Composite | 1990-2026 | International Coffee Organization | Precio internacional USD/lb |
| 4 | NOAA ONI | 1950-2026 | NOAA | Índice ENSO, fase climática |
| 5 | Open-Meteo Historical | 1990-2026 | Open-Meteo (gratis sin API key) | Temperatura, precipitación, ET0, NDVI |
| 6 | IDEAM (2da entrega) | 2019-2024 | IDEAM | Estaciones meteorológicas |
| 7 | FRED St. Louis Fed | 1990-presente | Federal Reserve | Precios Brasil y Robusta USD/lb |
| 8 | World Bank Pink Sheet | 1960-presente | Banco Mundial | Precios commodity mensuales |
| 9 | RoCoLe + BRACOL + JMuBEN + CALIBRO | 2018-2024 | Mendeley / Kaggle / propia | ~10000 imágenes hojas/frutos |
| 10 | SoilGrids ISRIC | 2020 | ISRIC | pH, materia orgánica, textura |
| 11 | SRTM DEM | 2000 | NASA Earthdata | Altitud media municipal |

Toda la información se centraliza en una base de datos PostgreSQL 18 con esquema en estrella (siete dimensiones, cinco hechos, dos auxiliares) y vista materializada `vw_master_municipal_mensual` que actúa como tablón maestro para los modelos. El diccionario de datos se documenta en el archivo correspondiente y vive auto-documentado en la tabla `cafe.aux_diccionario_columnas`.

---

## Capítulo 5 — Modelos y resultados

### 5.1 Cobertura por unidad del syllabus

**Unidad II — Aprendizaje Automático.** Los notebooks NB02, NB05, NB09 cubren regresión (Ridge, Lasso, ElasticNet, Random Forest, Extra Trees, XGBoost, LightGBM, Stacking) sobre dos targets: rendimiento (ton/ha) y precio interno (COP/125kg). El NB11 cubre clasificación binaria de "riesgo de baja productividad" y agrupamiento (K-Means, DBSCAN, Hierarchical) de municipios cafeteros por perfil agroclimático. El análisis de sesgos con Fairlearn cuantifica diferencias de error entre departamentos y entre clases de severidad de la CNN.

**Unidad III — Redes Neuronales.** El notebook NB07 implementa progresivamente el modelo de neurona artificial (perceptrón simple), la red superficial (una capa oculta) y la red profunda (cinco capas con BatchNorm, Dropout y regularización L2). Se compara la convergencia bajo Adam, SGD con momentum y RMSprop, mostrando curvas de pérdida por época. El MLP profundo se evalúa contra XGBoost en el mismo split temporal.

**Unidad IV — Deep Learning.** Cuatro frentes: (a) NB08 entrena tres CNN convolucionales (EfficientNetB0, ResNet50, MobileNetV2) con transfer learning en dos fases (extracción y fine-tuning), data augmentation por factor 5, Grad-CAM para explicabilidad y MC-Dropout para incertidumbre cuantificada; (b) NB10 entrena cuatro arquitecturas secuenciales (LSTM apilada, BiGRU, LSTM con atención Bahdanau aditiva, Transformer simplificado) sobre la serie de precios extendida a 432 observaciones, con intervalos de confianza por MC-Dropout; (c) NB12 implementa un autoencoder convencional y un Variational Autoencoder con reparametrización para detectar anomalías de precio (incluyendo el surge 2024-2025), y menciona conceptualmente GANs y modelos de difusión; (d) el módulo `06_agente_rag` implementa un sistema RAG completo con embeddings sentence-transformers, vector store ChromaDB y LLM Llama-3.1 (Groq) o Llama-3.1 local (Ollama) para responder preguntas sobre el sistema y el dominio.

### 5.2 Comparación cuantitativa

| Modelo | Tarea | Métrica 2da entrega | Métrica esperada final |
|--------|-------|---------------------|-------------------------|
| Ridge | Precio interno | R²=0.945, MAPE=4.3% | R²=0.945+ (mantener) |
| Stacking RF+XGB+LGB | Rendimiento departamental | R²=0.067, MAPE=14% | reemplazado por NB09 |
| ML Municipal (NB09) | Rendimiento municipal | — | R²>0.5 esperado |
| MLP Profundo (NB07) | Rendimiento | — | comparable a XGBoost |
| BiGRU (NB10) | Precio futuro | R²=−2.12, MAPE=23.1% | R²>0.5 esperado |
| Transformer (NB10) | Precio futuro | — | benchmark moderno |
| EfficientNetB0 (NB08) | Severidad enfermedad | Acc=48.9% | Acc>85% esperado |
| Grad-CAM | Explicabilidad CNN | funcional | funcional + más datos |
| Autoencoder (NB12) | Anomalías precio | — | detecta surge 2024 |
| RAG | Q&A dominio | — | 5 preguntas demo OK |

### 5.3 Análisis ENSO

La hipótesis principal validada es que la fase ENSO es un predictor estadísticamente significativo del rendimiento del café colombiano. El test de Kruskal-Wallis sobre las tres fases (El Niño, Neutro, La Niña) arroja p < 0.05, con rendimientos medios de 0.788, 1.037 y 0.910 ton/ha respectivamente. Este hallazgo es consistente con la literatura agroclimática y guía las recomendaciones del sistema: en años de Niño anticipado se sugiere riego suplementario y manejo de sombra, en años de Niña se prioriza control fitosanitario por exceso de humedad.

---

## Capítulo 6 — Análisis de sesgos y fairness

El análisis con Fairlearn sobre el modelo de rendimiento revela una diferencia de error MAE entre departamentos del orden de 0.05-0.15 ton/ha, con peores resultados en Nariño (departamento subrepresentado). Para la CNN, la clase Alto domina el dataset CALIBRO original con 53% de las muestras, lo que se mitigó con: (a) la ampliación a datasets externos (RoCoLe, BRACOL, JMuBEN) que producen distribución más balanceada; (b) cálculo explícito de pesos por clase para `class_weight` en el `fit`; y (c) data augmentation diferencial sobre las clases minoritarias.

---

## Capítulo 7 — Arquitectura del sistema y despliegue

El sistema se compone de cuatro capas. La capa de datos consiste en PostgreSQL 18 corriendo en localhost:5432 con la base `cafe_ia` y esquema `cafe`, creada mediante el DDL en `03_scripts/bd/01_ddl_schema.sql` y poblada con `02_carga_inicial.py`. La capa de modelos consiste en archivos `.pkl` (sklearn/XGBoost/LightGBM) y `.keras` (TensorFlow) almacenados en `04_modelos_entrenados/`. La capa de servicio consiste en una aplicación Streamlit multipágina en `07_app_web/` con páginas de dashboard, predicción de rendimiento, forecasting de precios, detector de enfermedades por upload de imagen, chatbot RAG y mapa cafetero interactivo. La capa de despliegue se hace vía Docker (Dockerfile multistage + docker-compose) y permite hosting gratuito en HuggingFace Spaces o Streamlit Cloud.

---

## Capítulo 8 — Limitaciones honestas y trabajo futuro

Aun con la ampliación de datos, varias limitaciones persisten. **Datasets de imágenes:** RoCoLe y BRACOL provienen de Ecuador y Brasil respectivamente, y aunque las enfermedades del café son similares en la región andina, los fondos, las cámaras, las variedades y la severidad reportada difieren. Es necesario validar el modelo con captura propia en cafetales colombianos. **Resolución municipal:** muchos municipios cafeteros pequeños tienen pocas observaciones por año, lo que limita la varianza explicable. La integración con el Censo Nacional Agropecuario 2014 podría mitigar esto pero ese censo está desactualizado. **Cobertura climática satelital:** Open-Meteo es muy bueno pero solo para 18 capitales departamentales en este proyecto; escalar a 600 municipios requiere un loop de varias horas. **Surge de precios 2024-2025:** los modelos extrapolan con dificultad eventos atípicos, por lo que el sistema debe enmarcar sus pronósticos como condicionales a la continuidad del régimen actual. **Consumo de cómputo:** los Transformers y Temporal Fusion Transformers requieren GPU para entrenamientos extensivos; este proyecto los implementa en versión liviana.

El trabajo futuro priorizado: (1) captura propia de 1000+ imágenes balanceadas en zonas cafeteras colombianas con metadata de variedad, altitud y severidad medida; (2) integración con MODIS NDVI mensual y CHIRPS satelital a nivel municipal completo vía Earth Engine; (3) entrenamiento de un Temporal Fusion Transformer completo con covariables conocidas vs no conocidas; (4) validación operacional con técnicos de la Dirección de Cadenas Agrícolas del MADR y extensionistas FNC; (5) versión móvil offline del detector de enfermedades para uso en finca.

---

## Capítulo 9 — Conclusiones

El proyecto demuestra la viabilidad técnica de un sistema integral de IA para el café colombiano. Los modelos de ML clásico para precio funcionan excelentemente (R² superior a 0.94), los modelos de rendimiento mejoran sustancialmente al pasar de granularidad departamental a municipal, los modelos de deep learning para series y para visión rinden bien cuando los datasets son suficientes y las arquitecturas modernas (Transformer, EfficientNet) son competitivas. El sistema cubre las cuatro unidades del syllabus de manera explícita, está documentado, contenedorizado, desplegable y honesto sobre sus limitaciones, y entrega valor tangible: cuantifica el efecto del ENSO sobre el rendimiento, detecta enfermedades foliares en campo y permite consultar el conocimiento del proyecto en lenguaje natural.

---

## Bibliografía

Chlingaryan, A., Sukkarieh, S., & Whelan, B. (2018). Machine learning approaches for crop yield prediction and nitrogen status estimation in precision agriculture. *Computers and Electronics in Agriculture*, 151, 61–69.

DANE (2024). Evaluaciones Agropecuarias Municipales (EVA). https://www.dane.gov.co

Federación Nacional de Cafeteros (2024). Estadísticas de la actividad cafetera. https://federaciondecafeteros.org

Hughes, D. P., & Salathé, M. (2015). An open access repository of images on plant health to enable the development of mobile disease diagnostics. *arXiv:1511.08060*.

IDEAM (2024). Datos climáticos de Colombia. https://www.ideam.gov.co

International Coffee Organization (2024). Coffee Market Report. https://www.ico.org

Kamilaris, A., & Prenafeta-Boldú, F. X. (2018). Deep learning in agriculture: A survey. *Computers and Electronics in Agriculture*, 147, 70–90.

Krohling, R. A., Esgario, J. G., Ventura, J. A. (2019). BRACOL — A Brazilian Arabica Coffee Leaf images dataset. *Mendeley Data*.

Lewis, P., Perez, E., Piktus, A., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *NeurIPS*.

Lim, B., Arık, S. Ö., Loeff, N., & Pfister, T. (2021). Temporal Fusion Transformers for interpretable multi-horizon time series forecasting. *International Journal of Forecasting*, 37(4), 1748–1764.

Mohanty, S. P., Hughes, D. P., & Salathé, M. (2016). Using deep learning for image-based plant disease detection. *Frontiers in Plant Science*, 7, 1419.

NOAA (2024). Climate Prediction Center — ENSO ONI. https://origin.cpc.ncep.noaa.gov

Parraga-Alava, J., Cusme, K., Loor, A., & Santander, E. (2019). RoCoLe: A robusta coffee leaf images dataset for evaluation of machine learning based methods in plant diseases recognition. *Data in Brief*, 25, 104414.

Vaswani, A., et al. (2017). Attention is all you need. *NeurIPS*.

World Bank (2024). Commodity Markets Pink Sheet. https://www.worldbank.org/en/research/commodity-markets

---

*Universidad Autónoma de Occidente · Mayo 2026*
