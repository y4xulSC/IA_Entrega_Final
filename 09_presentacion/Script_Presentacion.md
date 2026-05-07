# Script de presentación — Entrega Final
## 15 minutos · 14 slides · ~1 min por slide promedio

---

### Slide 1 — Portada (0:30)
"Buenos días/tardes. Somos Yáxul Cárdenas y Yesenia Díaz. Hoy presentamos
la entrega final del proyecto de Inteligencia Artificial: el Sistema
Integral de IA Agrícola para Colombia, módulo café."

### Slide 2 — Recap dónde estábamos (1:00)
"En la segunda entrega entregamos un prototipo funcional con seis módulos.
El modelo de precio interno con Ridge alcanzó R² de 0.945 — excelente.
Pero teníamos tres limitaciones serias: el modelo de rendimiento daba
R² de apenas 0.067, las redes recurrentes daban R² negativo por el
surge 2024-2025, y la CNN tenía solo 47 imágenes con accuracy del 48.9%.
Nuestra hipótesis fue: el problema es falta de datos, no metodología."

### Slide 3 — Qué hicimos (1:00)
"En la entrega final nos enfocamos en resolver eso. Pasamos de 47 a casi
diez mil imágenes de café usando datasets públicos (RoCoLe, BRACOL,
JMuBEN). Extendimos los precios de seis a treinta y seis años usando FRED
y World Bank. Bajamos a granularidad municipal. Integramos clima
satelital, suelos y altitudes. Y empaquetamos todo en una app web
desplegable con base de datos y agente conversacional."

### Slide 4 — Unidad I (0:45)
"La Unidad I la cubrimos en el documento académico: definición de IA,
historia desde AlexNet 2012 hasta el RAG actual, y un análisis específico
de riesgos y oportunidades para el café colombiano. Mencionamos sesgo
geográfico, brecha digital rural, y la oportunidad para 800 mil familias
cafeteras."

### Slide 5 — Unidad II (1:00)
"Unidad II: regresión, clasificación, agrupamiento y sesgos. Tenemos
nueve modelos de regresión comparados, clasificación binaria de riesgo,
clustering con K-Means, DBSCAN y Hierarchical, y análisis de sesgos con
Fairlearn por departamento y por clase de la CNN."

### Slide 6 — Unidad III (1:30)
"La Unidad III es nueva en esta entrega. El notebook NB07 implementa
progresivamente: el perceptrón simple — una sola neurona — luego una red
superficial con una capa oculta de 32 neuronas, y finalmente una red
profunda de cinco capas con BatchNorm, Dropout 0.3 y regularización L2.
Comparamos la convergencia bajo Adam, SGD con momentum y RMSprop, y
evaluamos contra XGBoost en el mismo split temporal."

### Slide 7 — CNN (1:30)
"Para la Unidad IV de CNN, comparamos tres arquitecturas representativas
de la historia del deep learning en visión: EfficientNetB0, ResNet50 y
MobileNetV2. Usamos transfer learning en dos fases: primero extracción
con la base congelada y learning rate 1e-3, luego fine-tuning de las
últimas capas con LR 1e-5. Aumentamos los datos por factor cinco. Para
explicabilidad usamos Grad-CAM y para incertidumbre MC-Dropout."

### Slide 8 — Series y Transformers (1:30)
"Para series de tiempo, ampliamos a cuatro arquitecturas. LSTM apilada,
BiGRU bidireccional, LSTM con atención Bahdanau implementada manualmente,
y un Transformer simplificado tipo Temporal Fusion Transformer. Lo
crítico: pasamos de 60 observaciones a 432 — esto resuelve el problema
del R² negativo de la segunda entrega."

### Slide 9 — Generativas y RAG (1:30)
"Para redes generativas, autoencoder convencional y VAE detectan
anomalías en la serie de precio — el surge 2024-2025 sale como anomalía
estadística. Mencionamos GANs y modelos de difusión conceptualmente.
Para Transformers en PLN, construimos un RAG completo con embeddings
multilingües, vector store ChromaDB y LLM Llama-3.1 vía Groq gratis."

### Slide 10 — Sesgos (1:00)
"Con Fairlearn calculamos error MAE por departamento. Encontramos que
Nariño tiene peores predicciones porque está subrepresentado.
Implementamos tres estrategias de mitigación: ampliar datos donde falta,
reweighing por clase en la CNN, y augmentation diferencial sobre clases
minoritarias."

### Slide 11 — Sistema desplegable (1:00)
"Todo se integra en una app Streamlit multipágina con seis vistas:
dashboard, predicción de rendimiento, forecasting de precios, detector
de enfermedades por upload de imagen, chatbot RAG y mapa cafetero. El
backend es PostgreSQL 18 con un esquema en estrella. Está
contenedorizado en Docker y se puede desplegar gratis en HuggingFace
Spaces o Streamlit Cloud."

### Slide 12 — Resultados (1:00)
"Los resultados esperados con los datos ampliados: mantener el 0.945 en
precio, subir el rendimiento de 0.067 a más de 0.5, llevar la CNN del
49% al 85%+, y resolver el subajuste de las recurrentes. El RAG responde
correctamente a las cinco preguntas demo del script."

### Slide 13 — Limitaciones honestas (1:00)
"Somos honestos sobre limitaciones: los datasets de imágenes son
foráneos, la resolución municipal sigue siendo limitada en municipios
chicos, y los modelos no extrapolan eventos atípicos. El trabajo futuro
prioriza captura propia de imágenes colombianas, Temporal Fusion
Transformer completo, versión móvil offline y validación operacional con
el MADR."

### Slide 14 — Cierre (0:30)
"Para cerrar: el sistema cubre las cuatro unidades del syllabus de
manera explícita y desplegable, resuelve los limitantes identificados
en la segunda entrega, y entrega valor tangible. Gracias al equipo, al
docente y a las fuentes públicas. Quedamos atentos a sus preguntas."

---

## Q&A anticipado

**¿Por qué Streamlit y no FastAPI + frontend?**
Streamlit nos permite ML-friendly demos en horas. FastAPI requeriría
frontend separado y más tiempo. Para entrega es óptimo.

**¿Cómo manejan el surge 2024-2025?**
Lo detectamos como anomalía con el VAE. Los modelos de pronóstico no
pretenden extrapolarlo — entregamos intervalos de confianza amplios y
señalamos la limitación.

**¿Las imágenes RoCoLe/BRACOL son representativas de Colombia?**
Parcialmente. Las enfermedades del café son similares en la región
andina. Pero validar con captura propia es trabajo futuro prioritario.

**¿Por qué bajaron a municipal?**
Porque el R² departamental era 0.067 — la varianza intra-departamento
no se capturaba. Municipal nos da más observaciones (1000+ vs 14) y
captura altitud, suelos, variedad por finca.

**¿Tienen modelo desplegado en producción?**
Tenemos el sistema funcionando localmente con Docker. El paso a
producción real es trabajo futuro — requiere validación operativa
con el MADR.

**¿Cómo integran ENSO?**
Como variable exógena. NB04 ya lo tenía como `es_El_Nino`,
`es_La_Nina` y ONI continuo. El test de Kruskal-Wallis confirma que
es estadísticamente significativo (p < 0.05).
