# Glosario de términos del Sistema IA Café

## Términos de café

**Arábica (Coffea arabica):** especie principal cultivada en Colombia.
Mejor calidad, requiere altitudes 1200-2000 msnm, temperaturas 18-22°C.
Representa ~95% del café colombiano.

**Robusta (Coffea canephora):** segunda especie más cultivada
mundialmente. Mayor contenido de cafeína, sabor más áspero. En
Colombia cultivada en zonas bajas (<900 msnm), principalmente
Caquetá, Putumayo.

**Pergamino seco:** café procesado con humedad entre 10-12%, listo para
trillado. Es la unidad estándar de comercialización al productor.
Una carga = 125 kg de pergamino seco.

**Café cereza:** fruto del café recién cosechado, sin procesar.
Conversión: ~5 kg de cereza producen 1 kg de pergamino seco.

**Beneficio:** proceso de transformación de cereza a pergamino.
Incluye despulpado, fermentación, lavado y secado.

**Beneficio húmedo tradicional:** despulpa + fermenta 16-24h + lava +
seca. Estándar colombiano.

**Beneficio honey/miel:** despulpa + seca sin fermentar (con mucílago).
Da notas dulces al café. Tendencia en cafés especiales.

**Cosecha selectiva:** recolectar solo cereza 100% madura (roja).
Imprescindible para café especial (>80 SCA).

**Mitaca:** cosecha secundaria, entre marzo-junio en Antioquia y otras
zonas. La cosecha principal es septiembre-noviembre.

## Calidad SCA

**SCA:** Specialty Coffee Association. Define el estándar de calidad
mundial de café especial.

**Puntaje SCA:** evaluación sensorial de 0-100 puntos por catador
certificado (Q-Grader). Tiene 10 atributos: fragancia/aroma, sabor,
sabor residual, acidez, cuerpo, balance, uniformidad, taza limpia,
dulzor, evaluación general.

**Categorías SCA:**
- 0-70: comercial
- 70-80: consumo (mainstream)
- 80-85: premium
- 85-90: especial
- 90-100: excepcional

**Catación / cupping:** evaluación sensorial de café siguiendo
protocolo SCA estándar.

**Q-Grader:** catador certificado por el Coffee Quality Institute.
La autoridad para evaluar puntajes SCA.

## Variedades de café en Colombia

**Caturra:** mutación del Bourbon, porte bajo, alta productividad.
Susceptible a roya. Era la más cultivada hasta los 90s.

**Castillo:** variedad mejorada por Cenicafé, resistente a roya y CBD.
Combina genes de Caturra + Híbrido de Timor. La más sembrada hoy.

**Variedad Colombia:** primera resistente a roya desarrollada por
Cenicafé (1980s). Reemplazada gradualmente por Castillo.

**Cenicafé 1:** variedad reciente (2016), porte bajo, resistente a
roya y CBD, alta productividad.

**Tabi:** variedad de porte alto, resistente a roya. Café de buena
calidad de taza.

**Borbón / Típica:** variedades tradicionales, calidad excelente,
susceptibles a roya. Cultivadas en cafés especiales boutique.

**Geisha:** variedad africana, calidad excepcional, vendida en
subastas internacionales. Cultivo difícil, requiere altitud >1500 msnm.

## Términos climáticos

**ENSO:** El Niño-Oscilación del Sur. Patrón climático del Pacífico
ecuatorial con tres fases: El Niño, La Niña, Neutro.

**ONI (Oceanic Niño Index):** indicador oficial NOAA para clasificar
fases ENSO. Anomalía de temperatura superficial del mar en región
Niño 3.4, promedio móvil 3 meses.
- ONI ≥ +0.5 → El Niño
- ONI ≤ −0.5 → La Niña
- En medio → Neutro

**El Niño:** fase cálida del ENSO. En Colombia reduce precipitación
30-40% y aumenta temperatura. **Reduce rendimiento del café ~24%.**

**La Niña:** fase fría del ENSO. En Colombia aumenta precipitación.
Reduce rendimiento café ~12% por exceso humedad y enfermedades.

**Cosecha bimodal:** patrón colombiano con dos cosechas al año
(mitaca + principal). Característico de zona andina.

**Estrés hídrico:** déficit de agua que afecta producción y calidad.
Se calcula como ET0 − precipitación.

**ET0 (evapotranspiración de referencia):** mm de agua que un cultivo
de referencia evapora por día. Indicador de demanda hídrica.

## Términos de IA y modelos

**R² (coeficiente de determinación):** mide qué tan bien el modelo
explica la varianza de la variable objetivo. Rango: −∞ a 1. R²=1 es
perfecto, R²=0 es como predecir la media, R²<0 es peor que la media.

**RMSE (Root Mean Squared Error):** raíz del error cuadrático medio.
En las mismas unidades que la variable objetivo.

**MAE (Mean Absolute Error):** error absoluto medio. Más robusto a
outliers que RMSE.

**MAPE (Mean Absolute Percentage Error):** error porcentual medio.
Útil para interpretación intuitiva (X% de error).

**Transfer Learning:** técnica de DL donde un modelo pre-entrenado en
una tarea grande (ImageNet) se ajusta a una tarea específica con
menos datos.

**EfficientNet, ResNet, MobileNet:** arquitecturas CNN representativas.
EfficientNetB0 es el más eficiente en parámetros/precisión.

**LSTM (Long Short-Term Memory):** red recurrente con compuertas que
captura dependencias temporales largas.

**GRU (Gated Recurrent Unit):** simplificación de LSTM, menos parámetros,
similar desempeño.

**BiGRU (Bidirectional GRU):** procesa la secuencia en ambas direcciones.
El mejor modelo en NB10 (R²=0.47).

**Atención Bahdanau:** mecanismo de atención aditiva. Aprende pesos
para enfocar partes relevantes de la secuencia.

**Transformer:** arquitectura basada solo en atención. Estado del arte
en PLN. Requiere muchos datos para superar a RNN.

**Autoencoder:** red que aprende a reconstruir la entrada pasando por
un cuello de botella (espacio latente). Útil para detección de
anomalías y reducción de dimensión.

**VAE (Variational Autoencoder):** autoencoder probabilístico. El
espacio latente sigue distribución gaussiana, permitiendo generación
de muestras nuevas.

**Grad-CAM:** técnica de visualización que muestra qué regiones de
una imagen activan más al CNN para una predicción específica.

**MC-Dropout:** técnica para cuantificar incertidumbre en redes
neuronales. Mantiene dropout activo en inferencia y promedia múltiples
predicciones.

**SHAP:** SHapley Additive exPlanations. Mide la contribución de cada
feature a una predicción individual. Basado en teoría de juegos.

**Fairlearn:** librería de Microsoft para medir y mitigar sesgos en
modelos ML. Métricas como demographic parity, equalized odds.

**RAG (Retrieval Augmented Generation):** arquitectura que combina
búsqueda en vector store con generación de LLM. Permite responder
sobre dominios específicos sin reentrenar el LLM.

**Embeddings:** representación vectorial densa de texto. Vectores con
similitud semántica preservada.

**Vector store:** base de datos especializada en búsqueda por
similitud vectorial. ChromaDB es local y persistente.

## Términos institucionales

**MADR:** Ministerio de Agricultura y Desarrollo Rural de Colombia.

**FNC:** Federación Nacional de Cafeteros de Colombia. Gremio privado
fundado en 1927.

**Cenicafé:** Centro Nacional de Investigaciones de Café. Brazo
investigativo de la FNC.

**DANE:** Departamento Administrativo Nacional de Estadística. Maneja
EVA, SIPSA, censos.

**UPRA:** Unidad de Planificación Rural Agropecuaria. Maneja datos de
planificación territorial.

**IDEAM:** Instituto de Hidrología, Meteorología y Estudios Ambientales.
Datos climáticos oficiales.

**SNIA:** Sistema Nacional de Innovación Agropecuaria. Marco de política
de innovación.

**NOAA:** National Oceanic and Atmospheric Administration (EE.UU.).
Publica el índice ONI oficial mundialmente.

**ICO:** International Coffee Organization. Organización intergubernamental
de países productores y consumidores.
