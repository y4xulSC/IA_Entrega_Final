# Guion — Presentación Final · Sistema Integral de IA Agrícola — Café Colombia

**Equipo:** Yáxul Santiago Cárdenas · Yesenia Díaz Urrego
**Curso:** Inteligencia Artificial · Universidad Autónoma de Occidente · 2026-1
**Archivo de diapositivas:** `Presentacion Final IA - MEJORADA.pptx` (13 diapositivas)
**Duración objetivo:** 16–18 minutos (≈ 9 min de diapositivas + 5–6 min de demo en vivo + cierre)

---

## Antes de empezar (checklist de 5 minutos)

1. Abrir la app **antes** de entrar al salón: `cd 07_app_web` → `python -m streamlit run app.py`. Dejarla corriendo en el navegador, en la pestaña **Inicio**.
2. Tener el **chatbot RAG ya indexado** (`python 06_agente_rag/rag_pipeline.py indexar --force`) y verificado con `demo`.
3. Tener lista **una imagen de hoja de café** descargada para el detector de enfermedades (carpeta `01_datos/imagenes_cafe`).
4. Abrir la presentación en modo presentador. Tener este guion impreso o en el celular.
5. Acordar quién narra cada bloque (sugerencia abajo: alternar por unidad temática).

> **Regla de oro:** las diapositivas acompañan, no se leen. Mira al jurado, no a la pantalla.

---

## PARTE 1 — Diapositivas (≈ 9 minutos)

### Diapositiva 1 — Portada · *(0:30)* — Narra: Yáxul

> "Buenas tardes. Somos Yáxul Cárdenas y Yesenia Díaz, de Ingeniería de Datos e IA. Presentamos la entrega final del proyecto: el **Sistema Integral de Inteligencia Artificial Agrícola para Colombia, módulo café**. En los próximos minutos verán cómo, partiendo de datos públicos, construimos un sistema que predice, diagnostica y aconseja, y lo van a ver funcionando en vivo."

### Diapositiva 2 — Problema · *(0:45)* — Yáxul

> "El café colombiano sostiene a unas 800.000 familias, pero el caficultor decide casi a ciegas: no sabe si viene un El Niño, si su lote rinde poco por clima o por enfermedad, ni cuándo conviene vender. Nuestro objetivo fue construir una **plataforma de IA de apoyo a la decisión** que convierta datos dispersos en respuestas accionables."

### Diapositiva 3 — Objetivo General · *(0:45)* — Yesenia

> "El objetivo: una plataforma integral que **integre datos climáticos, productivos, económicos e imágenes**, y que sobre ellos genere predicciones y herramientas concretas. No un modelo aislado, sino un sistema completo: datos, modelos, base de datos y aplicación."

### Diapositiva 4 — Arquitectura del Sistema · *(1:15)* — Yesenia

> "Esta es la arquitectura de extremo a extremo. A la izquierda, las fuentes de datos. Luego la ingeniería de datos: descarga, limpieza, integración y un dataset maestro. En el centro, los modelos de IA. A la derecha, las salidas, y todo se sirve en una aplicación web."
>
> "El proyecto se organiza en seis notebooks: **NB07**, redes neuronales profundas; **NB08**, la CNN de enfermedades; **NB09**, machine learning de rendimiento municipal; **NB10**, series temporales; **NB11**, clustering y análisis de sesgos; y **NB12**, modelos generativos. Cada uno cubre una parte del temario del curso."

### Diapositiva 5 — Fuentes de Datos · *(0:50)* — Yesenia

> "Integramos **11 fuentes públicas**: clima del IDEAM y Open-Meteo, precios de la FNC e ICO, producción de las Evaluaciones Agropecuarias, el índice ENSO de la NOAA, suelos, altitudes, y datasets de imágenes de enfermedades — RoCoLe, BRACOL y JMuBEN. Todo dato abierto y reproducible."

### Diapositiva 6 — Feature Engineering · *(0:50)* — Yáxul

> "Los datos crudos no se modelan directamente. Construimos variables derivadas: **rezagos climáticos**, **estrés hídrico** — evapotranspiración menos precipitación —, variables de fase ENSO y variables de precio. El resultado es un dataset maestro municipal mensual: más de un millón de registros, 1990–2026, con 95% de completitud."

### Diapositiva 7 — Modelos de Machine Learning · *(0:55)* — Yáxul

> "Para las tareas tabulares comparamos nueve algoritmos: regresión regularizada — Ridge, Lasso, ElasticNet —, ensambles de árboles — Random Forest, XGBoost, LightGBM — y Stacking. La evaluación es estricta: **partición temporal**, sin fuga de información, con R², MAE, RMSE y MAPE. Ganan los modelos lineales regularizados y de boosting."

### Diapositiva 8 — Resultados ML · *(1:10)* — Yáxul  ⭐ *diapositiva clave*

> "Estos son los resultados reales del sistema:"
>
> - **Precio interno FNC: R² = 0.945** con Ridge, error porcentual de apenas 4.3%.
> - **Rendimiento municipal: R² = 0.818** con CatBoost. Y aquí está el avance más importante: en la segunda entrega este modelo daba **R² de 0.067**. Al bajar de escala departamental a municipal y ampliar los datos, pasó de 0.07 a 0.82.
> - **Detección de enfermedades: 82% de accuracy** con la CNN MobileNetV2.
> - **Pronóstico de precio futuro: R² = 0.47** con una red recurrente BiGRU — recordando que en la segunda entrega las recurrentes daban R² negativo.

> *Pausa breve aquí. Es el momento de mayor impacto: el sistema mejoró de verdad.*

### Diapositiva 9 — Deep Learning · *(1:10)* — Yesenia

> "Para la Unidad de Deep Learning trabajamos tres frentes. **Visión por computador:** una CNN con transfer learning clasifica siete clases de enfermedad en hoja de café, con Grad-CAM para explicar visualmente la predicción. **Series temporales:** LSTM, BiGRU y un Transformer para el precio. Y **transfer learning y atención** como técnicas transversales. Lo decisivo fue ampliar el dataset de imágenes de 47 a casi diez mil."

### Diapositiva 10 — Interpretabilidad · *(0:50)* — Yesenia

> "Un modelo que no se explica no se adopta. Usamos **SHAP** en los modelos tabulares: las variables que más pesan son temperatura, ENSO y estrés hídrico. Y **Grad-CAM** en la CNN, que muestra qué zona de la hoja activó la decisión. Esto le da confianza al técnico que use el sistema."

### Diapositiva 11 — App Web y RAG · *(0:50)* — Yáxul  → *enlaza con la demo*

> "Todo esto se integra en una **aplicación web en Streamlit**, con base de datos PostgreSQL y un chatbot RAG que responde preguntas sobre café en lenguaje natural. Está contenedorizada con Docker. Y en lugar de describirla… se las vamos a mostrar funcionando."

> **→ Cambiar a la ventana del navegador con la app. Iniciar PARTE 2.**

---

## PARTE 2 — Demostración en vivo de la aplicación (≈ 5–6 minutos) — Narra: Yáxul, apoya: Yesenia

> Mostrar 5 páginas, no las 8. Elegir las de mayor impacto. Si el tiempo aprieta, recortar Dashboard y Mapa.

### Demo 1 — Inicio + Dashboard *(0:50)*
- Señalar la barra lateral: "ocho módulos, uno por cada capacidad del sistema".
- Entrar a **📊 Dashboard**. Mover el *slider* de años.
- Decir: "Aquí el caficultor ve de un vistazo producción, rendimiento y precios. Abajo, el impacto medido de ENSO: **El Niño reduce el rendimiento cerca de un 24%**, validado con un test estadístico."

### Demo 2 — Predicción de Rendimiento *(0:55)*
- Entrar a **🌱 Rendimiento**. Ajustar los *sliders*: temperatura 21°, altitud 1.500 msnm, ONI en 0.
- Pulsar **🔮 Predecir rendimiento**.
- Decir: "El modelo CatBoost — el de R² 0.818 — devuelve el rendimiento esperado, la producción y el ingreso bruto estimado. Ahora subo el ONI a +2 para simular El Niño…" → volver a predecir → "y se ve caer el rendimiento."

### Demo 3 — Detector de Enfermedades (CNN) *(1:10)* — *el momento más visual*
- Entrar a **📷 Enfermedades**. Subir la imagen de hoja preparada.
- Decir: "El modelo es la CNN MobileNetV2. Clasifica entre roya, gotera, cercospora, phoma, minador, ácaro y hoja sana, y entrega la **confianza** de la predicción."
- Señalar el resultado: clase + porcentaje de confianza.

### Demo 4 — Calculadora SCA → Precio *(0:55)* — *herramienta nacida de la reunión con la asociación*
- Entrar a **☕ Calidad SCA**. Mover el *slider* de puntaje SCA hasta ~85.
- Decir: "Esta calculadora la diseñamos tras reunirnos con una asociación cafetera de Rionegro, Antioquia. Traduce el **puntaje de calidad SCA en precio por kilo**: muestra cuánto más vale un café de 85 puntos frente al precio base. Es el argumento para que el pequeño productor invierta en calidad."

### Demo 5 — Asesor del Caficultor + Chatbot RAG *(1:00)*
- Entrar a **🌱 Asesor del Caficultor**. Elegir un departamento.
- Decir: "Recomienda las **tareas agronómicas del mes**, da una **alerta climática** según el ONI actual y una **alerta de precio** cuando conviene vender."
- Entrar a **🤖 Chatbot**. Escribir o pulsar una pregunta sugerida, p. ej. *"¿Qué hago si viene El Niño?"*
- Decir: "El chatbot usa RAG: busca en nuestra base de conocimiento y responde con un modelo de lenguaje, citando el contexto. Es la parte de Transformers y PLN del curso, aplicada."

> **→ Volver a la presentación. Diapositiva 12.**

---

## PARTE 3 — Cierre (≈ 2 minutos)

### Diapositiva 12 — Limitaciones · *(0:55)* — Yesenia

> "Somos honestos sobre los límites. Los datasets de imágenes son **foráneos** — de Brasil, Ecuador, Kenia — y requieren validación con cafetales colombianos. Faltan variables agronómicas locales de finca. Y los modelos de pronóstico **no extrapolan eventos atípicos**, como el alza de precios de 2024–2025, que de hecho nuestro modelo generativo VAE detecta como anomalía. Es un prototipo académico funcional, no un producto certificado."

### Diapositiva 13 — Conclusiones · *(1:00)* — Yáxul

> "Para cerrar, cuatro ideas. Primera: **ampliar los datos resolvió el cuello de botella** — el rendimiento pasó de R² 0.07 a 0.82. Segunda: el precio interno se predice con R² 0.945 y las enfermedades con 82% de acierto. Tercera: un solo sistema integra regresión, redes profundas, CNN, series temporales, modelos generativos y un agente RAG — las cuatro unidades del curso. Y cuarta: no quedó en notebooks, es una **plataforma web funcional y desplegable**, con herramientas pensadas para el caficultor real. Gracias — quedamos atentos a sus preguntas."

---

## Reparto sugerido

| Bloque | Narra |
|---|---|
| Diapositivas 1, 2, 6, 7, 8, 11, 13 | Yáxul |
| Diapositivas 3, 4, 5, 9, 10, 12 | Yesenia |
| Demo en vivo de la app | Yáxul narra · Yesenia opera el equipo / pasa imágenes |

---

## Preguntas frecuentes anticipadas (Q&A)

**¿Por qué el rendimiento mejoró tanto, de 0.07 a 0.82?**
No fue cambiar de algoritmo, fue cambiar la **escala y la cantidad de datos**. Pasamos de resolución departamental (14 unidades) a municipal (600+), lo que multiplicó las observaciones y permitió capturar altitud, suelo y variedad. El modelo siempre fue capaz; antes no tenía con qué aprender.

**En la diapositiva 8, ¿el pronóstico de precio con R² 0.47 no es bajo?**
Es honesto. Predecir precio **futuro** de un commodity es intrínsecamente difícil. Lo relevante es el contexto: en la segunda entrega ese modelo daba R² negativo —peor que adivinar la media—. Pasar a 0.47 con la red BiGRU es el resultado de tener 432 observaciones en lugar de 60. El precio **actual** sí lo predecimos muy bien: R² 0.945.

**¿La CNN está entrenada con café colombiano?**
No directamente. Los datasets públicos vienen de Brasil, Ecuador y Kenia. Las enfermedades son las mismas en la región andina, pero la validación con imágenes colombianas es trabajo futuro prioritario. Lo declaramos abiertamente en limitaciones.

**¿Por qué Streamlit y no un framework web completo?**
Streamlit permite construir demos centradas en ML en horas, no semanas. Para un prototipo académico que debe ser reproducible y desplegable gratis, es la elección óptima. Una API con frontend separado sería el paso a producción.

**¿Cómo manejan el alza de precios 2024–2025?**
No pretendemos extrapolarla. Nuestro autoencoder y VAE la **detectan como anomalía estadística**, que es la respuesta correcta: el sistema avisa "esto es atípico" en vez de fingir que lo predijo.

**¿XGBoost le ganó a la red neuronal profunda en el NB07?**
Sí, y lo reportamos tal cual. En datos tabulares con pocas muestras, los modelos de boosting suelen superar a las redes profundas. El NB07 cumple su propósito didáctico —construir el perceptrón, la red superficial y la profunda, y comparar optimizadores— y además deja una lección metodológica real: la arquitectura más compleja no siempre gana.

**¿El sistema está en producción?**
Funciona localmente y está contenedorizado con Docker. El despliegue del entrenamiento de la CNN en Docker tuvo incompatibilidades de versiones entre Keras y TensorFlow; el resto de la plataforma corre sin problemas. El paso a producción real requiere validación operativa con la FNC o el MADR.

**¿Cómo integran el ENSO en los modelos?**
Como variable exógena: fase de El Niño / La Niña y el índice ONI continuo. Un test de Kruskal-Wallis confirma que el efecto es estadísticamente significativo (p < 0.05): El Niño reduce el rendimiento ~24% y La Niña ~12%.

---

## Consejos de entrega

- **Ritmo:** si vas retrasado, recorta la demo (omite Dashboard y Asesor), nunca las conclusiones.
- **Plan B de la demo:** si la app falla, ten capturas de pantalla de las 5 páginas en una carpeta. "Por estabilidad lo muestro en capturas" suena profesional.
- **La diapositiva 8 es el corazón:** baja el ritmo, deja respirar el contraste 0.07 → 0.82.
- **Cierra mirando al jurado**, sin leer. La última frase apréndela de memoria.
