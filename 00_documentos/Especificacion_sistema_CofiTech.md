# Especificación del sistema CofiTech · MockUp final (Opción 3: Plataforma Dual Adaptativa por Roles)

*Anexo técnico de la entrega final · Data Thinking · Universidad Autónoma de Occidente · Octubre de 2026*

La alternativa seleccionada mediante AHP (puntaje global 0,5839) es una aplicación web única con dos vistas que comparten estado: una vista móvil para el **Caficultor** y una consola analítica para el **Agrónomo / Cooperativa**, más un permiso de **Administrador** del sistema. Esta especificación define qué debe hacer el sistema, con qué calidad y bajo qué restricciones, y registra el estado real de cada requerimiento en el prototipo.

**Convenciones**

- **Prioridad (MoSCoW):** *Debe* (indispensable para la entrega), *Debería* (importante, no bloqueante), *Podría* (deseable).
- **Estado en el prototipo:** ✅ Implementado y probado · 🟡 Parcial · ⏳ Pendiente.
- Las rutas de código son relativas a `IA_Entrega_Final/`.

---

## 1. Requerimientos funcionales (RF)

### RF01 · Ingesta única y estado compartido

| Campo | Especificación |
|---|---|
| **Descripción** | El sistema debe capturar una sola vez los datos de la finca (municipio, código DANE, departamento, altitud, área sembrada, variedad y fecha de floración principal) o la zona de trabajo del agrónomo (departamentos y municipio en foco), y mantenerlos en la sesión (`st.session_state`) para que todos los módulos los usen sin volver a pedirlos. |
| **Entradas** | Formulario de ingreso por rol; catálogo de municipios con código DANE verificado contra EVA. |
| **Procesamiento** | Validación de rangos físicos (altitud y área) antes de guardar. El contexto viaja también con el último diagnóstico, el riesgo fitosanitario de la sesión, el clima (ONI/fase ENSO) y el precio FNC vigentes. |
| **Salidas** | Barra de contexto fija en todas las pantallas; datos precargados en Visión, Rendimiento, Precios y el asistente RAG. |
| **Criterio de aceptación** | Ninguna pantalla posterior al ingreso pide de nuevo municipio, altitud, área o variedad. Un diagnóstico de roya ≥ 80 % cambia el riesgo de la sesión a «Alto» y se refleja en Rendimiento y en el contexto del RAG sin acción del usuario. |
| **Prioridad / Estado** | Debe · ✅ |
| **Trazabilidad** | Retroalimentación del profesor («herramientas desconectadas»); criterio AHP C3. Código: `07_app_web/cofitech/contexto_finca.py`, `cofitech/navegacion.py`. |

### RF02 · Diagnóstico visual asistido

| Campo | Especificación |
|---|---|
| **Descripción** | El sistema debe clasificar fotografías de hojas de café tomadas con el celular y mostrar la clase, la probabilidad y el riesgo fitosanitario resultante, junto con un mapa de atención Grad-CAM que señale la zona de la hoja que motivó la predicción. |
| **Clases del modelo** | 7 clases: 4 enfermedades fúngicas —**roya** (*Hemileia vastatrix*), **gotera u ojo de gallo** (*Mycena citricolor*), **mancha de hierro** (*Cercospora coffeicola*), ***Phoma*** (*Phoma costarricensis*)—, 2 plagas —**minador de la hoja** (*Leucoptera coffeella*, insecto) y **araña roja** (*Tetranychus* spp., ácaro)— y **hoja sana**. |
| **Entradas** | Imagen JPG/PNG de una hoja. La imagen se procesa en memoria y **no se almacena**. |
| **Procesamiento** | CNN (`04_modelos_entrenados/cnn_cafe_best.keras`, NB08). Regla de producto: roya con probabilidad ≥ 80 % en cualquier hoja del muestreo ⇒ riesgo «Alto». El muestreo acumula las hojas revisadas en la sesión. |
| **Salidas** | Clase, probabilidad, riesgo de la sesión, Grad-CAM; registro del diagnóstico (sin imagen) en `cafe.registro_diagnosticos`. |
| **Criterio de aceptación** | Para cada foto se muestran clase y probabilidad; el registro aparece en la base y en el mapa de alertas del agrónomo en menos de 30 s. |
| **Prioridad / Estado** | Debe · ✅ Clasificación, Grad-CAM (`cofitech/vision.py`), muestreo, riesgo y registro implementados. Verificado con el modelo real sobre 35 imágenes del conjunto de prueba (33 aciertos). |
| **Trazabilidad** | KR3 (módulo Visión); KPI Nivel de Confianza Aceptada. Código: `07_app_web/pages/4_Enfermedades.py`. |

> **Ajuste respecto al borrador:** el borrador hablaba de «5 patologías». El modelo distingue 6 problemas sanitarios más la clase sana, y 2 de ellos (minador y araña roja) son plagas, no enfermedades. Conviene nombrarlos así ante evaluadores con formación agronómica.

### RF03 · Prescripción con fuente y telemetría de valor

| Campo | Especificación |
|---|---|
| **Descripción** | El sistema debe responder consultas técnicas con un agente RAG que use el contexto de la finca y del último diagnóstico, y que cite la literatura técnica de Cenicafé cuando la use. Cada diagnóstico y cada respuesta deben poder calificarse con 👍/👎. |
| **Reglas de prescripción** | (1) Dosis, concentraciones y periodos de carencia **solo** si provienen de un documento validado de Cenicafé recuperado en la consulta; si no, el sistema responde: «No cuento con la dosificación exacta validada por Cenicafé para este caso específico; consulte al extensionista del Comité de Cafeteros de su municipio.» (2) Control químico de roya sujeto al umbral de incidencia del 5 % del muestreo en lote. (3) Toda mención de fungicida incluye equipo de protección personal y periodo de carencia. (4) Toda recomendación de fertilización remite al análisis de suelos. (5) La cita «(Fuente: Manual de Caficultura / Boletines Técnicos Cenicafé)» solo se agrega si se recuperó un documento validado. Las reglas están en el *prompt* y además se verifican en código antes de mostrar la respuesta. |
| **Telemetría** | Evento por uso de cada herramienta (`registrar_evento_uso(herramienta, accion, metadata)`) con tiempo de respuesta, rol y municipio; sin texto de las preguntas ni datos personales. |
| **Salidas / KPI** | **Tasa de Resolución del RAG** = respuestas 👍 / respuestas calificadas. **Nivel de Confianza Aceptada** = diagnósticos 👍 / diagnósticos calificados. **KR3** = sesiones que usaron Visión, Predicción y RAG. Visibles en «Telemetría y KPIs» (solo administradores). |
| **Criterio de aceptación** | Una respuesta sin documento validado nunca contiene dosis. Cada voto se registra una sola vez y queda en `cafe.registro_eventos_uso`. |
| **Prioridad / Estado** | Debe · 🟡 Agente, salvaguardas, votos y KPIs implementados y probados. **El corpus aún no contiene documentos de Cenicafé** (`06_agente_rag/documentos_fuente/cenicafe/` vacío): hoy toda pregunta de dosis recibe el mensaje de respaldo. |
| **Trazabilidad** | KPI de Negocio y KPI de Modelo de la 1.ª entrega; KR2 (proxy) y KR3. Código: `06_agente_rag/rag_pipeline.py`, `07_app_web/cofitech/telemetria.py`. |

### RF04 · Proyección de rendimiento e ingreso

| Campo | Especificación |
|---|---|
| **Descripción** | El sistema debe estimar el rendimiento esperado (ton/ha) del municipio de la finca y el ingreso aproximado, ajustado por el riesgo fitosanitario de la sesión y por escenarios de precio. |
| **Componentes** | (a) **Línea base de rendimiento:** último rendimiento municipal reportado por las Evaluaciones Agropecuarias Municipales (EVA, MADR/UPRA), con caída al promedio departamental o nacional si el municipio no reporta. (b) **Ajuste fitosanitario:** reducción del 23 % al 30 % si el riesgo de roya es «Alto» y la variedad no es resistente (rango reportado por Cenicafé, Boletín Técnico 36). (c) **Precios:** precio interno FNC vigente y simulador Ridge «precio ICO → precio interno» para escenarios. (d) **Simulador agroclimático** (altitud, temperatura, precipitación, ONI) solo para el Agrónomo, rotulado como experimental. |
| **Criterio de aceptación** | Toda cifra muestra su fuente y su fecha. Ningún valor de modelo se presenta como pronóstico si no superó la referencia ingenua en validación temporal. |
| **Prioridad / Estado** | Debe · ✅ Línea base EVA, ajuste por roya, precio FNC y simulador Ridge (`cofitech/precios_ridge.py`) implementados. El Ridge, validado en 2024–2025, obtiene R² = 0,989 y MAPE = 2,5 %, frente a R² = 0,89 y MAPE = 6,1 % de repetir el precio del mes anterior. |
| **Trazabilidad** | KR3 (módulo Predicción). Código: `07_app_web/cofitech/rendimiento.py`, `pages/2_Rendimiento.py`, `pages/3_Precios.py`. |

> **Ajuste respecto al borrador:** el borrador decía «modelo Ridge validado que integra variables del IDEAM para el rendimiento». Eso no corresponde al proyecto y no resistiría una pregunta del evaluador. Primero, el Ridge es el modelo de **precios**, y funciona como simulador, no como pronóstico: usa el precio ICO del mismo mes (R² = 0,945). Segundo, para el **rendimiento**, con datos EVA reales y validación temporal (entrenamiento hasta 2015, prueba 2016–2018), repetir el valor del año anterior obtuvo R² = 0,60, y el mejor modelo con clima y ENSO obtuvo 0,28. Tercero, el R² = 0,818 de NB09 se calculó sobre datos simulados. Por eso la cifra principal es el dato EVA y el modelo agroclimático queda como simulador experimental.

### Requerimientos funcionales complementarios (ya implementados)

| ID | Requerimiento | Prioridad / Estado |
|---|---|---|
| **RF05** | **Alertas fitosanitarias territoriales.** La consola del Agrónomo muestra un mapa de calor de los reportes de roya por municipio, con datos de `cafe.registro_diagnosticos`. Se actualiza cada 30 s, excluye los diagnósticos que el caficultor rechazó con 👎 y los registros simulados, y permite filtrar por periodo (7 a 365 días). El indicador es «% de fotos con roya»: sirve para priorizar visitas, no reemplaza el muestreo de incidencia en lote. | Debe · ✅ |
| **RF06** | **Persistencia con respaldo.** Diagnósticos, votos y eventos se guardan en PostgreSQL (Supabase) y en archivos locales. Si la base no responde, la app sigue funcionando con los archivos y lo avisa en pantalla. | Debe · ✅ |
| **RF07** | **Control de acceso administrativo.** Telemetría, Ficha técnica de modelos y el panel de depuración solo son visibles con contraseña de administrador. La contraseña se guarda como *hash* PBKDF2-SHA256, con bloqueo tras 5 intentos fallidos y bitácora de accesos. | Debe · ✅ |
| **RF08** | **Detección de anomalías de precio.** Alerta de meses con variación atípica del precio interno e ICO (volatilidad móvil de 6 meses, umbral en el percentil 97,5 de la historia previa, sin usar datos futuros). | Debería · ✅ |

---

## 2. Requerimientos no funcionales (RNF)

| ID | Atributo | Requerimiento medible | Método de verificación | Estado |
|---|---|---|---|---|
| **RNF01** | Rendimiento | Percentil 95 del tiempo de inferencia (clasificación + Grad-CAM) **≤ 3 s en CPU** por imagen, con el modelo ya cargado en memoria. La primera carga del modelo se mide aparte y se mitiga con caché (`st.cache_resource`). | Campo `tiempo_respuesta_s` de la telemetría (evento `diagnostico_ejecutado`) en el entorno de despliegue, con al menos 30 inferencias. | 🟡 Medido en CPU de 2 núcleos con el modelo real: p50 = 0,56 s y p95 = 0,65 s (clasificación + Grad-CAM, 35 imágenes). **Falta medirlo en Streamlit Cloud.** |
| **RNF02** | Usabilidad móvil | La vista del Caficultor se usa en celular con una mano: tarjetas de decisión con una acción principal por pantalla; texto base ≥ 16 px; botones ≥ 44 × 44 px; sin tablas anchas ni desplazamiento horizontal a 360 px de ancho; lenguaje sin jerga estadística. | Revisión a 360 × 800 px; prueba con al menos 3 caficultores (tarea: revisar una hoja y llegar a «¿Qué hago?» sin ayuda), registrada como insumo de KR2. | 🟡 Navegación por rol, barra de contexto en 2 renglones y flujo «siguiente paso» listos; **falta la prueba con usuarios** en campo. |
| **RNF03** | Disponibilidad y tolerancia a fallos | **Degradación controlada:** ninguna falla de un servicio externo detiene la app. Base de datos: tiempo máximo de conexión de 5 s, pausa de 60 s antes de reintentar y respaldo en archivos locales. LLM: modelo alterno si el configurado fue retirado; mensaje claro si no hay servicio. Datos: toda cifra muestra fecha de corte. | Pruebas automáticas con la base caída (`tests/test_persistencia.py`) y con fallos simulados del LLM. | ✅ Mecanismos implementados y probados. |
| **RNF04** | Seguridad | Secretos fuera del código (`.env` / `secrets.toml`, excluidos de git). El esquema `cafe` no es accesible con la llave pública de Supabase (RLS activo sin políticas; permisos retirados a `anon` y `authenticated`). Contraseña de administrador solo como *hash*. | Pruebas de permisos con los roles de Supabase; `tests/test_seguridad.py`. | ✅ |
| **RNF05** | Trazabilidad de fuentes | Toda cifra y toda recomendación indican su fuente (EVA, FNC, ICO, IDEAM/NOAA, Cenicafé) y su fecha. | Revisión de pantallas; prueba de que la cita de Cenicafé solo aparece con documento recuperado. | ✅ |

> **Ajuste respecto al borrador de RNF03:** «disponibilidad garantizada» no se puede prometer con presupuesto cero, porque los planes gratuitos no tienen acuerdo de nivel de servicio:
> - Streamlit Community Cloud suspende las apps tras **12 horas sin tráfico**.
> - Supabase pausa los proyectos gratuitos tras **7 días de baja actividad**; se reactivan desde el panel sin perder datos.
>
> Por eso el requerimiento se redactó como degradación controlada. Para la sustentación basta con abrir la app y la base unas horas antes.

---

## 3. Restricciones del proyecto

| Tipo | Restricción | Implicación de diseño / mitigación |
|---|---|---|
| **Tecnológica** | Sin Docker en el despliegue. Streamlit Community Cloud como servidor y PostgreSQL administrado en Supabase. | Cliente propio `03_scripts/bd/db_client.py` (psycopg2 con *pool*), esquema idempotente `03_supabase_schema.sql` y conexión por el *Session pooler* (IPv4). **Riesgo:** Streamlit Community Cloud ofrece hasta **2,7 GB de RAM**, y TensorFlow, *sentence-transformers*, ChromaDB y los modelos de *boosting* juntos pueden acercarse a ese límite. Mitigación: cargar los modelos solo en la pantalla que los usa (`st.cache_resource`) y, si hace falta, convertir la CNN a TensorFlow Lite. |
| **Legal y regulatoria** | Ley Estatutaria 1581 de 2012 (protección de datos personales) y Decreto 1377 de 2013, compilado en el Decreto 1074 de 2015. Derechos de autor: Ley 23 de 1982 y Decisión Andina 351 de 1993. | **Hoy no se recolectan datos personales:** el registro guarda municipio, clase, probabilidad, rol y un identificador aleatorio de sesión; no guarda nombres, teléfonos, coordenadas de la finca, fotos ni el texto de las preguntas. Si se habilita el registro de usuarios (necesario para medir KR1 y la retención), antes debe existir autorización previa, expresa e informada del titular (art. 9), aviso de privacidad y una política de tratamiento. Contenido de Cenicafé: se cita la publicación de origen en cada respuesta que lo use, y se verifican las condiciones de uso de cada documento antes de incorporarlo al corpus. |
| **Operacional y de conectividad** | Zonas cafeteras con cobertura 3G/4G intermitente. | El diagnóstico envía una sola imagen. Las pantallas del caficultor no cargan mapas ni tablas pesadas, y el estado se conserva entre pantallas. **Proyección:** una PWA con captura sin conexión y envío diferido, y un canal de WhatsApp (foto → diagnóstico → recomendación) para quien no instala aplicaciones. Ninguna de las dos está en el alcance del prototipo. |
| **Recursos** | Presupuesto de infraestructura igual a cero durante el prototipo académico. | Planes gratuitos de Streamlit Community Cloud, Supabase y Groq (LLM por API). Consecuencias asumidas: suspensión por inactividad (ver RNF03), límites de uso del LLM y sin respaldo automático de la base: se hace con `pg_dump` manual antes de la entrega. |

---

## 4. Matriz estratégica y grado de innovación

### 4.1 Marco de análisis

La matriz de innovación cruza dos ejes (Davila, Epstein y Shelton, 2006):

- **Eje tecnológico:** cuánto cambia la tecnología con la que se entrega la solución.
- **Eje de modelo de negocio:** cuánto cambia la forma de crear, entregar y capturar valor.

Las combinaciones dan cuatro grados:

| | **Modelo de negocio: cambio incremental** | **Modelo de negocio: cambio radical** |
|---|---|---|
| **Tecnología: cambio radical** | Semirradical (impulsada por tecnología) | **Radical** |
| **Tecnología: cambio incremental** | Incremental | Semirradical (impulsada por el modelo de negocio) |

### 4.2 Eje tecnológico: radical para el usuario y el sector

Frente a la práctica actual del caficultor (diagnóstico a ojo o espera del extensionista, información de clima, producción y precios dispersa en fuentes oficiales separadas), CofiTech introduce un cambio de naturaleza, no de grado:

1. **IA multimodal integrada.** Tres familias de modelos sobre tipos de dato distintos —visión por computador sobre imágenes de hojas, modelos sobre series municipales de producción, clima y precios, y un agente RAG sobre texto técnico— operan como un solo sistema. El diagnóstico visual modifica el riesgo que usa la proyección de rendimiento y se inyecta como contexto en la consulta al RAG.
2. **Datos de campo generados por el propio usuario.** Cada foto diagnosticada se convierte en un dato georreferenciado a nivel de municipio. Con eso se construye vigilancia fitosanitaria casi en tiempo real, que hoy no existe en las fuentes abiertas: las EVA son anuales y los reportes sanitarios no tienen resolución municipal pública.
3. **IA con salvaguardas verificables.** La prescripción química está restringida en código a fuentes validadas, con mensaje de respaldo cuando no hay fuente. Esto aborda el principal riesgo de los asistentes generativos en agronomía.

**Matiz para la defensa:** cada componente por separado es una técnica conocida (CNN, regresión, RAG). Lo radical es su **integración** y su **aplicación** al pequeño caficultor colombiano y a sus organizaciones, no la invención de un algoritmo. Si el evaluador sostiene que la tecnología es incremental, la posición defendible es que CofiTech es **como mínimo semirradical impulsada por tecnología**, con un camino claro hacia lo radical a medida que crezca la red de datos de campo (punto 2).

### 4.3 Eje de modelo de negocio: de incremental a radical

| Etapa | Modelo | Grado | Por qué |
|---|---|---|---|
| **Hoy (Canvas de la 1.ª entrega)** | Freemium B2C: herramientas gratuitas para el caficultor y suscripción para agrónomos y analistas. | Incremental | Replica el esquema de las aplicaciones agrícolas existentes; cambia el canal, no la lógica de captura de valor. |
| **Con la Opción 3 (este MockUp)** | **B2B2C:** la cooperativa o el Comité de Cafeteros paga la consola analítica (alertas territoriales, panorama regional, priorización de visitas) y ofrece la app sin costo a sus asociados. | Radical | Quien paga deja de ser el caficultor. El activo que se vende es la **red de datos de campo** que generan los asociados, no la herramienta. Cada nuevo caficultor activo mejora el producto de la cooperativa (efecto de red). La consola de alertas (RF05) es la primera versión funcional de ese producto. |

### 4.4 Ubicación en la matriz

| | **Modelo de negocio incremental (Freemium B2C)** | **Modelo de negocio radical (B2B2C con cooperativas)** |
|---|---|---|
| **Tecnología radical (IA multimodal integrada + datos de campo)** | CofiTech según el Canvas de la 1.ª entrega → *semirradical impulsada por tecnología* | **CofiTech con la Plataforma Dual (meta)** → ***radical*** |
| **Tecnología incremental** | Apps de consulta y boletines digitales existentes | — |

**Conclusión.** CofiTech se ubica hoy como **innovación semirradical impulsada por tecnología** y avanza hacia el cuadrante **radical** al adoptar el modelo B2B2C que habilita la Opción 3. El desplazamiento depende de una hipótesis que el piloto debe validar: que una cooperativa esté dispuesta a pagar por las alertas territoriales. La validación se mide con la adopción de caficultores (KR1, KR3) y con al menos una carta de intención o entrevista de disposición a pagar de una cooperativa o Comité.

---

## 5. Matriz de trazabilidad

| Requerimiento | OKR / KPI | Criterio AHP | Módulo principal |
|---|---|---|---|
| RF01 | KR3 | C1, C3 | `cofitech/contexto_finca.py` |
| RF02 | KR3 · Confianza Aceptada | C1, C3 | `pages/4_Enfermedades.py` |
| RF03 | KR2 (proxy), KR3 · Resolución RAG | C1, C3 | `06_agente_rag/rag_pipeline.py`, `cofitech/telemetria.py` |
| RF04 | KR3 | C2, C3 | `cofitech/rendimiento.py`, `pages/2_Rendimiento.py`, `pages/3_Precios.py` |
| RF05 | Hipótesis B2B2C | C2, C3 | `vistas/alertas_fitosanitarias.py` |
| RF06 / RNF03 | Medición de todos los KPI | C4 | `03_scripts/bd/db_client.py`, `cofitech/repositorio.py` |
| RF07 / RNF04 | — | C4 | `cofitech/seguridad.py` |
| RNF01 | Confianza Aceptada | C4 | `cofitech/telemetria.py` (`tiempo_respuesta_s`) |
| RNF02 | KR2 | C1 | `cofitech/navegacion.py`, vistas del Caficultor |

## 6. Pendientes para cumplir la especificación completa

1. Medir RNF01 en el entorno de despliegue (Streamlit Cloud).
2. Incorporar documentos de Cenicafé validados al corpus del RAG y reindexar.
3. Prueba de usabilidad con caficultores en celular (RNF02, KR2).
4. Habilitar el registro de usuarios con autorización de tratamiento de datos (Ley 1581) para medir KR1 y la retención.

## Referencias

- Davila, T., Epstein, M. J. y Shelton, R. (2006). *Making Innovation Work: How to Manage It, Measure It, and Profit from It*. Wharton School Publishing.
- Congreso de Colombia. Ley Estatutaria 1581 de 2012, por la cual se dictan disposiciones generales para la protección de datos personales.
- Presidencia de la República de Colombia. Decreto 1377 de 2013 (compilado en el Decreto Único Reglamentario 1074 de 2015).
- Congreso de Colombia. Ley 23 de 1982, sobre derechos de autor; Comunidad Andina, Decisión 351 de 1993.
- Rivillas O., C. A., Serna G., C. A., Cristancho A., M. A. y Gaitán B., A. L. (2011). *La roya del cafeto en Colombia: impacto, manejo y costos del control*. Boletín Técnico n.º 36. Manizales: Cenicafé. https://biblioteca.cenicafe.org/handle/10778/594
- Streamlit. *Manage your app* (hibernación y límites de recursos de Community Cloud). https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app
- Supabase. *Project Pausing*. https://supabase.com/docs/guides/platform/free-project-pausing
