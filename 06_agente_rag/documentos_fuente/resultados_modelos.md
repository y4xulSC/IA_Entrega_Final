# Resultados cuantitativos de los modelos del Sistema IA Café

Este documento resume los resultados obtenidos en los notebooks NB07-NB12
de la entrega final, con métricas exactas reproducibles.

## NB07 — Redes Neuronales Profundas (Unidad III)

Predicción de rendimiento del café (ton/ha) con escala municipal.

| Modelo | R² test | RMSE | MAE | MAPE |
|---|---|---|---|---|
| XGBoost (baseline) | 0.873 | 0.113 | 0.077 | 6.95% |
| Red superficial (1 capa, 32 neuronas) | 0.324 | 0.261 | 0.208 | 20.76% |
| MLP profundo (5 capas, BatchNorm + Dropout + L2) | 0.287 | 0.268 | 0.208 | 19.52% |
| Perceptrón simple (1 neurona) | −0.170 | 0.344 | 0.264 | 23.58% |

**Conclusión:** XGBoost supera al MLP profundo porque con dataset tabular
pequeño los modelos basados en árboles son más eficientes en muestra.
El MLP cumple su propósito didáctico de cubrir la Unidad III.

## NB08 — Detección de Enfermedades con CNN (Unidad IV)

Modelo entrenado sobre ~10000 imágenes únicas combinadas de RoCoLe, BRACOL,
JMuBEN, Coffee Leaf y CALIBRO. Comparación de 3 arquitecturas con transfer
learning en 2 fases (feature extraction + fine-tuning).

Clases detectables: Roya, Gotera, Cercospora, Phoma, Miner, Sano, SpiderMite.

Técnicas aplicadas:
- Data augmentation: rotación ±30°, zoom 20%, flip horizontal, brillo ±30%
- Class weights por desbalance
- Grad-CAM para explicabilidad
- MC-Dropout 100 pasadas para cuantificar incertidumbre

## NB09 — Machine Learning Municipal (Unidad II refinada)

Mejora del modelo de rendimiento al pasar de granularidad departamental
(14 obs test) a municipal (~7263 filas EVA).

| Modelo | R² test | Δ vs baseline 2da entrega |
|---|---|---|
| CatBoost | 0.818 | +0.751 |
| Lasso | 0.818 | +0.751 |
| Linear | 0.818 | +0.751 |
| Stacking | 0.816 | +0.749 |

**Logro principal:** mejora de R²=0.067 a R²=0.818 (+0.75 puntos).

Análisis SHAP confirmó que altitud y temperatura media son los predictores
dominantes, consistente con conocimiento agronómico (zona óptima 1200-2000
msnm, 18-22°C). Error MAE mayor en Nariño por sub-representación.

## NB10 — Forecasting de Precios con RNN (Unidad IV)

Pronóstico de precio FNC mensual con 444 observaciones (1990-2026).

| Modelo | RMSE | MAE | R² |
|---|---|---|---|
| BiGRU (mejor) | 0.694 | 0.477 | 0.472 |
| LSTM apilada | 0.702 | 0.576 | 0.460 |
| LSTM + Atención Bahdanau | 1.683 | 1.409 | −2.105 |
| Transformer simplificado | 1.700 | 1.458 | −2.168 |
| Naive (random walk) | 2.259 | 1.653 | −4.592 |

**Logro principal:** mejora de R²=−2.12 a R²=0.472 (+2.59 puntos) con BiGRU.
Supera al baseline Naive en +5.06 puntos, demostrando que el modelo
aprende patrones temporales reales y no solo replica último valor.

**Hallazgo:** modelos sofisticados (Transformer, atención) sobreajustan
con 444 obs; el BiGRU bidireccional simple es la zona óptima.

## NB11 — Clustering y Análisis de Sesgos (Unidad II)

5 clústeres agroclimáticos identificados sobre 21 municipios cafeteros:

| Cluster | Temp media | Altitud | Precip mensual | Perfil |
|---|---|---|---|---|
| 0 | 26.6°C | 125 msnm | 136 mm | Caliente bajo (Caribe) |
| 1 | 17.3°C | 1605 msnm | 485 mm | Eje Cafetero clásico |
| 2 | 22.1°C | 874 msnm | 242 mm | Templado-caliente medio |
| 3 | 16.1°C | 1795 msnm | 1068 mm | Frío alto húmedo |
| 4 | 13.0°C | 2622 msnm | 173 mm | Muy frío páramo (Nariño) |

Análisis Fairlearn detectó sesgo geográfico: Nariño sub-representado y
con mayor MAE en el modelo de rendimiento. Mitigación aplicada con
reweighing por clase.

## NB12 — Autoencoder y VAE (Unidad IV — Generativas)

Detección de anomalías en serie de precio mensual.

| Método | Anomalías detectadas | % del total |
|---|---|---|
| Autoencoder convencional | 8 | 9.4% |
| Variational Autoencoder (VAE) | 12 | 14.1% |
| Isolation Forest (baseline) | 19 | 22.4% |

**El surge de precio 2024-2025 fue detectado por los 3 métodos** —
validación cuantitativa de la hipótesis que explica el R²<0 del LSTM
de la 2da entrega: ese surge es out-of-distribution.

## Resumen de logros por unidad del syllabus

| Unidad | Notebooks | Estado |
|---|---|---|
| I — Introducción IA | Documento académico | Cubierto |
| II — ML clásico | NB09 (R²=0.82), NB11 (clustering + sesgos) | Excelente |
| III — Redes neuronales | NB07 (perceptrón → MLP profundo) | Cubierto didácticamente |
| IV — CNN | NB08 (EfficientNet + ResNet + MobileNet) | Cubierto |
| IV — RNN/Transformer | NB10 (R²=0.47 BiGRU) | Excelente |
| IV — Generativas | NB12 (AE + VAE) | Cubierto |
| IV — PLN/Transformers | Módulo RAG (06_agente_rag) | Funcional |

## Modelo de precio interno (2da entrega, preservado)

Ridge regression con feature engineering integrado:
- R² = 0.945
- MAPE = 4.3%
- Este modelo se mantiene como el mejor para precio interno FNC.

## Hallazgos clave para la presentación

1. El efecto del fenómeno El Niño reduce el rendimiento del café en
   aproximadamente 24% respecto a la fase Neutro (test Kruskal-Wallis
   significativo p < 0.05).
2. La altitud y temperatura media son los predictores agronómicos más
   importantes, validado con SHAP.
3. El surge de precio 2024-2025 es un evento out-of-distribution
   detectado por 3 métodos independientes.
4. La escala municipal mejora el R² del modelo de rendimiento en 0.75
   puntos respecto a la escala departamental.
