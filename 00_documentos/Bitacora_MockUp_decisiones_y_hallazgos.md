# CofiTech · Bitácora del MockUp: decisiones y hallazgos

Actualizado: 2026-10-15. Código en `IA_Entrega_Final/07_app_web/`, `06_agente_rag/` y `03_scripts/bd/`.

## Decisiones tomadas

| Tema | Decisión |
|---|---|
| Roles | Dos perfiles: Caficultor (simple, móvil) y Agrónomo / Cooperativa (técnico, escritorio). Las 9 pantallas originales se conservan. |
| Administrador | Permiso de sesión, no un tercer rol: el administrador usa la app como Caficultor o Agrónomo y además ve la sección «Administración» (Telemetría y KPIs, Ficha técnica de modelos) y el panel de depuración. Contraseña única; se guarda solo su hash PBKDF2-SHA256 en `COFITECH_ADMIN_HASH` (`.env` o `secrets.toml`), generado con `python 07_app_web/cofitech/seguridad.py`. Bloqueo de 60 s tras 5 intentos por sesión y de 5 min tras 20 fallos en el servidor. Bitácora en `05_resultados/logs/accesos_admin.jsonl`. Toda la app consulta `seguridad.es_admin()`: para pasar a `st.login` (Google) o Supabase Auth se cambia solo esa función. |
| Punto de entrada | `app.py` es el enrutador por roles (`streamlit run app.py`); `app_mockup.py` quedó como alias. La portada anterior pasó a `vistas/ficha_tecnica.py` (solo administradores), con la tabla de estado de modelos corregida. Requiere Streamlit ≥ 1.49. |
| Estado compartido | `cofitech/contexto_finca.py`: finca, zona y municipio en foco, clima, precio, diagnóstico, muestreo (incluida la incidencia medida en el lote), predicción. El riesgo también va en `st.session_state["riesgo_fitosanitario"]`. |
| Rendimiento | Cifra principal = último rendimiento EVA del municipio (dato real). El `.pkl` de NB09 queda solo para el Agrónomo como simulador rotulado «datos simulados». |
| Riesgo fitosanitario | Roya con probabilidad ≥ 80 % en alguna hoja del muestreo ⇒ «Alto». Manda la peor hoja de la sesión, no la última. |
| Descuento por roya | 23 %–30 % del rendimiento, sin graduar por severidad. Solo en proyecciones de finca y en variedades no resistentes. |
| Anomalías de precio | Retornos logarítmicos, volatilidad móvil de 6 meses y umbral = percentil 97,5 de la historia previa (sin datos futuros). No usa el autoencoder de NB12. |
| Precios | Simulador Ridge log-log en `cofitech/precios_ridge.py`: precio FNC ~ arábica Brasil (USD/kg) + TRM del mismo mes, entrenado al vuelo (sin `.pkl`). Validación en los últimos 24 meses (2024–2025): R² 0,989 y MAPE 2,5 %, frente a R² 0,89 y MAPE 6,1 % de repetir el mes anterior. Elasticidades ≈ 1,05 (arábica) y 0,59 (TRM). Las redes recurrentes quedan en la pestaña «Modelos Experimentales de Alta Volatilidad (En calibración)»: no se ejecutan porque sus escaladores no se guardaron. |
| Grad-CAM | `cofitech/vision.py`, en dos tramos: el MobileNetV2 va anidado como submodelo, así que se aplica la base y luego la cabeza dentro de `GradientTape`. Con el modelo real, en CPU de 2 núcleos: p50 0,56 s y p95 0,65 s por foto (clasificación + Grad-CAM); 33 de 35 aciertos en una muestra del test. |
| LLM del asistente | Groq con `openai/gpt-oss-20b` por defecto; se cambia con la variable `GROQ_MODEL`. Si el modelo configurado fue retirado, el agente prueba `openai/gpt-oss-120b`. |
| Contexto al RAG | `prefijo_rag` antepone a cada pregunta: municipio y altitud, diagnóstico y certeza, estado fenológico, variedad, ENSO e incidencia medida en el lote. La búsqueda en ChromaDB recibe solo la pregunta + la enfermedad. Botón «¿Qué hago con este resultado?» en Visión. |
| Prescripción (RAG) | Dosis, concentraciones y carencias solo de documentos en `06_agente_rag/documentos_fuente/cenicafe/`. Reglas en el system prompt y verificadas en código (`aplicar_salvaguardas`). La cita «(Fuente: Manual de Caficultura / Boletines Técnicos Cenicafé)» solo se agrega si se recuperó un documento validado. |
| Manejo de roya en pantalla | `cofitech/prescripcion.py`, según la **incidencia medida en el lote** (no la confianza de la foto): variedad resistente → sin control químico; < 5 % → preventivo con oxicloruro de cobre; ≥ 5 % → triazol sistémico con registro ICA. Siempre con periodo de carencia según la etiqueta ICA, EPP y fuente Cenicafé; sin dosis en el código. |
| Dosis fijas en pantallas | Retiradas de Enfermedades y del calendario del Asesor (ahora en `cofitech/calendario.py`). Una prueba automática busca cifras de dosis o de carencia en esos archivos. |
| Telemetría | `registrar_evento_uso(herramienta, accion, metadata)` en `cofitech/telemetria.py`: sesión + `05_resultados/logs/eventos_uso.jsonl` + Supabase (`cafe.registro_eventos_uso`). No guarda el texto de las preguntas. Cada evento guarda nombre y código DANE del municipio. Pantalla «Telemetría y KPIs» solo para administradores. |
| KPIs en la base | `cafe.telemetria_kpis` es una **vista** (no una tabla aparte) sobre `registro_eventos_uso`, con rol, herramienta, calificación 👍/👎, confianza del modelo y municipio; `cafe.vw_kpis_consolidados` agrega satisfacción RAG, confianza aceptada, certeza media de la CNN y KR3 por rol y en total. Ambas con `security_invoker`. La pantalla de administración la lee cada 30 s (`db_client.kpis_consolidados()`); si la base no responde, calcula lo mismo desde el archivo local (`telemetria.kpis_por_rol`), y una prueba verifica que los dos cálculos coinciden. |
| KPIs medidos | Nivel de confianza aceptada (👍/👎 en Visión), tasa de resolución del RAG (👍/👎 por respuesta), KR3 (sesiones con Visión + Predicción + RAG), proxy de KR2 (sesiones que valoraron). KR1 y retención semanal requieren inicio de sesión: no se miden. |
| Persistencia en la nube | Supabase (PostgreSQL), sin Docker. `03_scripts/bd/03_supabase_schema.sql` (v1.4: esquema en estrella + `registro_diagnosticos` + `registro_eventos_uso` + vistas `vw_feedback_rag`, `telemetria_kpis` y `vw_kpis_consolidados`), idempotente; semillas con `WHERE NOT EXISTS` para correr encima de un esquema creado con `01_ddl_schema.sql`. Probado en PostgreSQL 16 y 18. Cliente `03_scripts/bd/db_client.py` con psycopg2: pool de 3 conexiones, `connect_timeout` 5 s, pausa de 60 s tras un fallo. Credenciales en `07_app_web/.streamlit/secrets.toml` (`[connections.postgresql] url`) o `SUPABASE_DB_URL` en `.env` (sirve también para un PostgreSQL local); en Supabase, conexión por el *Session pooler* (IPv4). |
| Seguridad de la base | Esquema `cafe` fuera de la Data API, RLS activado sin políticas y permisos retirados a `anon`/`authenticated` (incluye las vistas): la llave pública de Supabase no lee nada. `secrets.toml` en `.gitignore`. |
| Respaldo sin nube | Todo se guarda también en `05_resultados/logs/` (diagnósticos, votos, eventos). Si Supabase no responde, las pantallas leen los archivos locales y lo avisan. |
| Mapa de alertas (Agrónomo) | `vistas/alertas_fitosanitarias.py`: mapa de calor folium de fotos con roya por municipio, semáforo por % de fotos con roya, periodo seleccionable, se relee cada 30 s (`st.fragment(run_every)`). No cuenta los diagnósticos rechazados con 👎 ni los simulados (opcional). La barra superior usa el mismo conteo (30 días). |
| Coordenadas municipales | Las 21 cabeceras de `geografia_validado.csv`; el resto, de DIVIPOLA (DANE) con `03_scripts/descarga/08_descargar_divipola.py` → `01_datos/procesados/divipola_municipios.csv`. |

## Hallazgos de auditoría que afectan la sustentación

1. **NB09 se entrenó con datos simulados.** El cuaderno busca `master_municipal_mensual.csv`, que no existe (el real es `master_cafe_municipal_mensual.csv`), y usa su rama de respaldo: 120 municipios ficticios generados con una fórmula. El R² = 0,818 mide esa fórmula, no el rendimiento del café.
2. **Con datos reales no hay modelo que supere la referencia simple.** EVA 2007–2018, entrenando hasta 2015 y evaluando 2016–2018: repetir el año anterior da R² 0,60; el mejor modelo probado (Ridge con rezagos, ONI y departamento), 0,28.
3. **La pantalla de Rendimiento mostraba kg/ha rotulados como ton/ha.** Corregido.
4. **`produccion_validado.csv` termina en 2018.** Los años 2019–2024 están en `01_datos/originales/produccion/EVA_cafe_2019_2024.csv`, que el ETL no incorpora y git ignora. La app los une si el archivo está presente.
5. **Dos códigos DANE errados en el catálogo geográfico:** Salento figura con 63594 (es Quimbaya; el correcto es 63690) y Marsella con 17442 (es Marmato; el correcto es 66440).
6. **El efecto ENSO de −24 % / −12 % no se reproduce con EVA anual 2007–2024:** 1,02 ton/ha en años La Niña, 1,04 en neutros y 1,10 en El Niño.
7. **El Ridge de precios no pronostica:** usa el precio internacional del mismo mes; sirve como simulador de escenarios (validado frente a la referencia ingenua).
8. **Cenicafé no publica una curva incidencia → pérdida.** El Boletín Técnico 36 (2011) reporta hasta 23 % de la producción acumulada de cuatro cosechas y 28 %–30 % en experimentos más recientes. Tampoco trae periodos de carencia, que dependen del producto comercial.
9. **El corpus del RAG no contiene documentos de Cenicafé:** son 10 archivos escritos por el equipo. Mientras `documentos_fuente/cenicafe/` esté vacío, el asistente responde con el mensaje de respaldo a toda pregunta de dosis.
10. **Datos desactualizados:** precio FNC a diciembre de 2025, ENSO a marzo de 2026, clima municipal solo para 16 cabeceras.
11. **Groq retiró los modelos Llama del asistente el 16 de agosto de 2026.** Corregido en `rag_pipeline.py` y en la ficha técnica. `documentos_fuente/arquitectura_sistema.md` todavía dice «Llama 3.1».
12. **El `.pkl` de rendimiento solo carga con scikit-learn 1.6.1.**
13. **Grad-CAM a veces mira fuera de la lesión:** en una hoja con Cercospora bien clasificada, la atención cayó sobre la nervadura y el fondo. Puede indicar que el modelo aprendió rasgos de la fuente de las imágenes (JMuBEN, BRACOL) y no solo de la enfermedad; conviene mostrarlo como limitación.
14. **Corregido:** la pantalla de Precios mostraba una tendencia amortiguada rotulada como si fuera el modelo elegido.
15. **El mapa de alertas mide % de fotos con roya, no incidencia en el lote:** quien fotografía elige hojas con síntomas. Sirve para priorizar visitas; la decisión de control sigue siendo el muestreo con umbral del 5 %.
16. **La persistencia se probó contra PostgreSQL 16 y 18 locales con los roles de Supabase, no contra un proyecto Supabase real.** Falta la prueba con la cadena del pooler del equipo.
17. **Los roles Caficultor y Agrónomo no tienen autenticación:** cualquiera puede elegir «Agrónomo» y ver los reportes de todos los caficultores. Solo la administración está protegida. Se resuelve con usuarios en base de datos (Supabase Auth) o `st.login`.

## Pendiente

- Generar la contraseña de administrador (`python 07_app_web/cofitech/seguridad.py`) y poner el hash en `.env`.
- Crear el proyecto Supabase, ejecutar `03_supabase_schema.sql` (v1.4), poner la cadena del pooler en `secrets.toml` y probar con `python 03_scripts/bd/db_client.py`.
- Ejecutar `08_descargar_divipola.py` (datos.gov.co) para ubicar todos los municipios en el mapa.
- Decidir cómo se presenta NB09 y su R² en la ficha técnica, el RAG y la presentación.
- Copiar PDF de Cenicafé a `documentos_fuente/cenicafe/` y reindexar.
- Incluir EVA 2019–2024 y corregir los dos códigos DANE en el ETL.
- Actualizar el nombre del LLM en el corpus del RAG (y reindexar).
- Guardar escaladores y ventanas de las redes recurrentes de NB10 para poder ejecutarlas y validarlas contra la referencia ingenua.
- Medir el tiempo de Grad-CAM en Streamlit Cloud.
