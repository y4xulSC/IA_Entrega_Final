# Guía de instalación

Pasos para dejar CofiTech (versión **Beta 0.9.0**) funcionando después de clonar el repositorio: app, asistente RAG y base de datos con los datos históricos cargados. Los comandos están para **Windows PowerShell**; la versión Linux/Mac va al lado cuando cambia. Todos se ejecutan desde la raíz del repositorio, salvo que el paso diga otra cosa.

| Ruta | Pasos | Tiempo aproximado |
|---|---|---|
| Solo ver la app (sin base de datos) | 1, 2, 3, 5, 7 | 10 min |
| **Instalación completa** (app + base cargada) | 1 a 8 | 20–30 min |
| Publicar la Beta en internet | 1 a 6 y «Producción» | 30–45 min |
| Regenerar datos y modelos desde cero | Anexo A | varias horas |

---

## Requisitos

| Componente | Versión | Notas |
|------------|---------|-------|
| Python | **3.11** | Es la versión con la que se probaron las versiones fijadas de `requirements.txt` |
| PostgreSQL | 13 o superior (probado en 16 y 18) | Local con pgAdmin, o un proyecto gratis de [Supabase](https://supabase.com) |
| Git | cualquiera | |
| RAM | 8 GB | La app con todos los modelos cargados usa ~1,6 GB |
| Internet | la primera vez | Instalar paquetes y descargar el modelo de embeddings del asistente |

Cuentas opcionales: [Groq](https://console.groq.com) (gratis) para que el asistente responda; Supabase para la base en la nube.

---

## Paso 1 · Clonar

```powershell
git clone https://github.com/y4xulSC/IA_Entrega_Final.git
cd IA_Entrega_Final
```

Si el repositorio es privado, el dueño debe dar acceso en GitHub primero.

Qué trae el clon y qué no:

| Viene en el repositorio | No viene (se crea en esta guía) |
|---|---|
| Datos procesados `01_datos/procesados/*.csv` | `.env` y `07_app_web/.streamlit/secrets.toml` (secretos) |
| Modelos `04_modelos_entrenados/*.keras` y `*.pkl` | Índice del asistente `06_agente_rag/vectorstore/` |
| Scripts SQL `03_scripts/bd/` | Base de datos con los datos cargados |
| Logo, letra y tema de la app | Imágenes de entrenamiento y datos crudos (Anexo A) |

---

## Paso 2 · Entorno de Python

```powershell
py -3.11 -m venv .venv                 # Linux/Mac: python3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1           # Linux/Mac: source .venv/bin/activate
python --version                       # debe decir 3.11.x
python -m pip install --upgrade pip
pip install -r 07_app_web/requirements.txt
```

Usa el Python 3.11 de [python.org](https://www.python.org/downloads/) (o `winget install Python.Python.3.11`), no el de Microsoft Store, y trabaja siempre con el `.venv` activado: con el Python global quedan versiones mezcladas (por ejemplo `pyarrow` 24, que no funciona con NumPy 1.x) y las pruebas fallan.

Las versiones están fijadas porque son las probadas: `scikit-learn` 1.6.1 y `catboost` 1.2.10 son las únicas con las que carga el modelo de rendimiento (`.pkl`), NumPy se queda en 1.x porque así se entrenaron los modelos, y `pyarrow` en 19 porque las versiones nuevas exigen NumPy 2. En Linux se instala `tensorflow-cpu` (más liviano); en Windows y macOS, `tensorflow`.

Este archivo solo trae lo que usa la app. Para **reentrenar** (notebooks y scripts, con XGBoost, LightGBM, SHAP, seaborn, Jupyter…) usa en su lugar `pip install -r 02_notebooks/requirements_notebooks.txt`, que incluye el de la app.

---

## Paso 3 · Archivo `.env`

Crea un archivo llamado `.env` **en la raíz del repositorio** (al lado de este archivo). Está en `.gitignore`: nunca se sube. Plantilla:

```dotenv
# ── Asistente RAG (sin esta clave la app abre, pero el asistente no responde)
GROQ_API_KEY=<tu clave de https://console.groq.com>
# GROQ_MODEL=openai/gpt-oss-20b        # opcional; este es el valor por defecto

# ── Base de datos para cargar el esquema en estrella (paso 4)
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=<tu contraseña de PostgreSQL>
PG_DB=cafe_ia
# PGSSLMODE=require                     # solo si cargas en Supabase

# ── Base de datos donde la app guarda diagnósticos, telemetría y ventas (paso 4.5)
# SUPABASE_DB_URL=postgresql://postgres:<contraseña>@localhost:5432/cafe_ia

# ── Contraseña de administrador (paso 6): se pega el HASH, nunca la contraseña
# COFITECH_ADMIN_HASH=pbkdf2_sha256:600000:...

# ── Beta: venta directa inactiva (0). Pon 1 solo para probar el mercado en local.
# COFITECH_MERCADO_ACTIVO=0
# ── Correo o enlace para los derechos de la Ley 1581 (aviso de privacidad)
# COFITECH_CONTACTO_DATOS=cofitech@<dominio>

LOG_LEVEL=INFO
LOG_DIR=05_resultados/logs
```

Si `PG_PASSWORD` no se define, los scripts usan `root`.

---

## Paso 4 · Base de datos: crear y cargar

La app funciona sin base de datos (guarda en archivos locales), pero la entrega incluye el **esquema en estrella con los datos históricos** y las **tablas de la app**. No hay que descargar nada: la carga lee los `*_validado.csv` que ya trae el repositorio.

Elige **una** de las dos opciones.

### Opción A · PostgreSQL local (pgAdmin)

**4.1 Crear la base y el esquema.** En pgAdmin: clic derecho en *Databases* → *Create* → nombre `cafe_ia`. Luego, con `cafe_ia` seleccionada, abre el *Query Tool* y ejecuta, en este orden, el contenido completo de:

1. `03_scripts/bd/01_ddl_schema.sql`: esquema en estrella (dimensiones, hechos y vista materializada).
2. `03_scripts/bd/03_supabase_schema.sql`: tablas de la app (diagnósticos, telemetría, venta directa) y seguridad. Está hecho para ejecutarse encima del anterior.

Con `psql` es lo mismo:

```powershell
psql -U postgres -c "CREATE DATABASE cafe_ia;"
psql -U postgres -d cafe_ia -f 03_scripts/bd/01_ddl_schema.sql
psql -U postgres -d cafe_ia -f 03_scripts/bd/03_supabase_schema.sql
```

La última fila debe decir `OK (v1.6) · esquema cafe con 18 tablas…; 5 compradores`.

### Opción B · Supabase

**4.1 Crear el esquema.** En Supabase: *SQL Editor* → *New query* → pegar todo `03_scripts/bd/03_supabase_schema.sql` → *Run*. Este archivo ya incluye el esquema en estrella; no hace falta el `01`.

Para los pasos siguientes, cambia en el `.env` los datos de conexión por los del **Session pooler** (Supabase → *Connect* → *Session pooler*, puerto 5432, IPv4):

```dotenv
PG_HOST=aws-0-<región>.pooler.supabase.com
PG_PORT=5432
PG_USER=postgres.<project_ref>
PG_PASSWORD=<contraseña de la base>
PG_DB=postgres
PGSSLMODE=require
```

### Para las dos opciones

**4.2 Validar los CSV antes de cargar**

```powershell
python 03_scripts/bd/validar_pre_carga.py
```

Debe terminar en `Total OK: 6/6`. El reporte queda en `05_resultados/reportes/`.

**4.3 Cargar los datos**

```powershell
python 03_scripts/bd/02_carga_inicial.py
```

Carga, en orden: periodos, ONI, municipios, clima, precios, producción, imágenes y la vista materializada. Tarda segundos. Se puede repetir sin duplicar filas: los UPSERT y el reemplazo de producción e imágenes lo garantizan. Para cargar solo una parte: `--solo precios clima` o `--skip imagenes`.

**4.4 Verificar** (en pgAdmin o en el SQL Editor):

```sql
SELECT 'dim_periodo' AS tabla, count(*) FROM cafe.dim_periodo
UNION ALL SELECT 'dim_municipio',          count(*) FROM cafe.dim_municipio
UNION ALL SELECT 'fact_clima',             count(*) FROM cafe.fact_clima
UNION ALL SELECT 'fact_precio',            count(*) FROM cafe.fact_precio
UNION ALL SELECT 'fact_produccion',        count(*) FROM cafe.fact_produccion
UNION ALL SELECT 'fact_imagen_enfermedad', count(*) FROM cafe.fact_imagen_enfermedad;
```

Valores esperados con los CSV actuales:

| Tabla | Filas |
|---|---:|
| dim_periodo | 492 |
| dim_municipio | 659 |
| fact_clima | 6.928 |
| fact_precio | 444 |
| fact_produccion | 7.263 |
| fact_imagen_enfermedad | 10.846 |

**4.5 Conectar la app a la misma base.** La app escribe con su propia conexión. Configúrala de **una** de estas dos formas:

- En el `.env`: `SUPABASE_DB_URL=postgresql://postgres:<contraseña>@localhost:5432/cafe_ia` (local) o la cadena del pooler (Supabase).
- O copia `07_app_web/.streamlit/secrets.toml.example` como `07_app_web/.streamlit/secrets.toml` y pon la cadena en `[connections.postgresql] url`. Es la forma que usa Streamlit Community Cloud.

Probar:

```powershell
python 03_scripts/bd/db_client.py
```

Debe decir `OK · PostgreSQL … · tablas de venta directa listas · KPI de interés en la venta directa listo`.

> **¿Ya tenías la base de una versión anterior?** v1.5: ejecuta `03_scripts/bd/06_kpi_interes_mercado.sql` (KPI de interés en la venta directa; solo vistas). v1.4: `05_marketplace.sql` y luego `06_kpi_interes_mercado.sql`. Ninguno borra datos. Detalle en `03_scripts/bd/README.md`.

---

## Paso 5 · Índice del asistente RAG

El índice de ChromaDB no está en git. **La app lo crea sola** la primera vez que alguien abre «¿Qué hago?» (tarda unos segundos y descarga el modelo de embeddings `all-MiniLM-L6-v2`, necesita internet). Si prefieres crearlo antes:

```powershell
python 06_agente_rag/rag_pipeline.py indexar
```

Para probarlo sin abrir la app: `python 06_agente_rag/rag_pipeline.py demo` (requiere `GROQ_API_KEY` u Ollama). Si la indexación automática falla, la pantalla del asistente muestra el error y el botón «Reintentar indexación».

Sin clave de Groq se puede usar Ollama local: ver `06_agente_rag/README.md`.

---

## Paso 6 · Acceso de administrador (opcional)

Telemetría y KPIs, Ficha técnica de modelos y el panel de depuración solo se ven con contraseña de administrador.

```powershell
python 07_app_web/cofitech/seguridad.py
```

Pide la contraseña dos veces (mínimo 10 caracteres) e imprime una línea `COFITECH_ADMIN_HASH=…`. Pégala en el `.env` **o** al inicio de `secrets.toml`, no en los dos. Lo que se guarda es el hash, no la contraseña. En la app se entra por «Acceso administrador», en la pantalla de ingreso.

---

## Paso 7 · Lanzar la app

```powershell
cd 07_app_web
python -m streamlit run app.py
```

Abre http://localhost:8501. Lánzala **desde `07_app_web`**: así Streamlit lee `.streamlit/config.toml` (tema, logo y letra). Si la app ya estaba abierta y cambiaste código o el `.env`, deténla con Ctrl+C y vuelve a lanzarla.

Recorrido para comprobar que todo funciona:

1. **Ingreso:** arriba aparece la franja **BETA**. Elige «Soy caficultor» y un municipio, marca la casilla de autorización de datos (sin ella no deja entrar) y entra.
2. **Hoy en mi finca:** precio FNC, clima, tareas del mes y la invitación «¿Viste manchas en las hojas?».
3. **Revisar una hoja:** sube una foto de una hoja; aparece el diagnóstico con Grad-CAM.
4. **¿Qué hago?:** pregunta al asistente (la primera vez crea el índice; necesita `GROQ_API_KEY`).
5. **Vender mi café · Inactivo:** aviso «Inactivo en la Beta» y el **simulador de venta**: «Ver ofertas simuladas», negociar con un comprador de demostración y cerrar la venta de práctica. Abajo, vota 👍/👎 en «¿Te gustaría vender tu café desde CofiTech?»: como administrador, el voto aparece en «Telemetría y KPIs» → *Interés en la venta directa*.
6. **Aviso de privacidad** (sección «Más»): el texto de la Ley 1581.
7. **Cambiar de rol** → «Agrónomo / Cooperativa»: alertas fitosanitarias, indicadores y escenarios de precio.

Para probar la venta directa en local, pon `COFITECH_MERCADO_ACTIVO=1` en el `.env` y relanza: publica un lote y en «Mis lotes y mensajes» llega una oferta de un comprador de demostración.

En el panel lateral de depuración (solo administradores) debe aparecer `Supabase: conectada` si hiciste el paso 4.5.

---

## Paso 8 · Pruebas

```powershell
pip install pytest
cd 07_app_web
python -m pytest tests -q
```

Las pruebas que escriben en una base solo se ejecutan si defines `COFITECH_TEST_DB_URL` con una **base de pruebas** creada con `03_supabase_schema.sql`. Nunca uses la base real: esas pruebas borran registros.

```powershell
$env:COFITECH_TEST_DB_URL = "postgresql://postgres:<clave>@localhost:5432/cafe_pruebas"
python -m pytest tests -q -rs
```

Resultado esperado con las versiones de `requirements.txt`: **91 pasan y 6 se omiten** sin base de pruebas; **97 pasan** con ella (la base de pruebas debe estar en v1.6). `tests/test_produccion.py` cubre lo propio de la Beta: franja, mercado inactivo, autorización de datos y que TensorFlow y el asistente convivan en Linux.

---

## Producción (Beta) en Streamlit Community Cloud

Todo gratis: la app en **Streamlit Community Cloud** y la base en **Supabase** (paso 4, opción B). Lo que corre en la nube son los mismos modelos `.keras` y `.pkl` del repositorio y el mismo modelo de embeddings: no hay versión recortada.

**1. Antes de publicar**

- Base de Supabase creada y cargada (paso 4, opción B) y `db_client.py` en OK.
- Hash de administrador generado (paso 6).
- Repositorio en GitHub **sin** `.env` ni `secrets.toml` (ya están en `.gitignore`). Revisa con `git status` antes de cada `git push`.

**2. Crear la app** en https://share.streamlit.io → *Create app* → *Deploy a public app from GitHub*:

| Campo | Valor |
|---|---|
| Repository | `y4xulSC/IA_Entrega_Final` |
| Branch | `main` |
| Main file path | `07_app_web/app.py` |
| App URL | `cofitech` → `https://cofitech.streamlit.app` (si el nombre está tomado, usa otro, p. ej. `cofitech-uao`) |
| Advanced settings → Python version | **3.11** |
| Advanced settings → Secrets | el bloque de abajo |

```toml
GROQ_API_KEY = "<tu clave de Groq>"
COFITECH_ADMIN_HASH = "pbkdf2_sha256:600000:..."
COFITECH_MERCADO_ACTIVO = "0"
# COFITECH_CONTACTO_DATOS = "cofitech@<dominio>"

[connections.postgresql]
url = "postgresql://postgres.<PROJECT_REF>:<CONTRASEÑA>@aws-0-<REGION>.pooler.supabase.com:5432/postgres"
```

Las claves sueltas van **antes** de `[connections.postgresql]`. Streamlit lee `07_app_web/requirements.txt` porque está junto al archivo principal. La primera instalación tarda varios minutos (TensorFlow y PyTorch).

**3. Primera prueba en la nube:** haz el recorrido del paso 7 en la dirección pública, incluido «¿Qué hago?» (crea el índice del asistente la primera vez). Como administrador, el panel de depuración debe decir `Supabase: conectada`.

**4. Mantener la base despierta.** Supabase pausa los proyectos gratis tras unos 7 días sin actividad. El flujo `.github/workflows/supabase_keepalive.yml` hace una consulta de solo lectura cada 3 días. Actívalo una vez: GitHub → *Settings* → *Secrets and variables* → *Actions* → *New repository secret* → nombre `SUPABASE_DB_URL`, valor la misma cadena del pooler. Pruébalo en *Actions* → *Supabase keep-alive* → *Run workflow*.

**Límites del plan gratis que hay que conocer**

| Límite | Efecto en CofiTech |
|---|---|
| ~2,7 GB de memoria | La app completa usa ~1,6 GB medidos con todos los modelos cargados |
| La app se duerme tras 12 h sin visitas | El primer visitante ve «This app has gone to sleep» y la despierta con un clic (~1 min) |
| Solo subdominios `*.streamlit.app` | Un dominio propio (cofitech.co) no se puede apuntar directo |
| Supabase pausa la base sin actividad | Lo evita el keep-alive del punto 4 |

**Ajustes de la Beta**

- `COFITECH_MERCADO_ACTIVO = "0"` deja «Vender mi café» y «Oferta de café en mi zona» en el menú, marcadas como *Inactivo*, fuera del recorrido del caficultor y sin escribir en las tablas `mk_*`. Con `"1"` vuelven a funcionar sin cambiar código.
- La franja **BETA** y la versión (`0.9.0`) salen de `07_app_web/cofitech/config.py`.
- El aviso de privacidad está en `07_app_web/cofitech/privacidad.py`. Si cambia lo que la app guarda, actualiza el texto y su `VERSION_AVISO`.

El despliegue oficial no usa Docker. `08_docker/` es una configuración heredada. Hugging Face Spaces dejó de ser alternativa gratis para apps nuevas con Docker/Gradio en CPU.

---

## Anexo A · Regenerar datos y modelos desde cero

Solo hace falta para actualizar las fuentes o reentrenar. Toma varias horas.

```powershell
# 1. Descargar fuentes (necesita token de Kaggle en ~/.kaggle/kaggle.json)
pip install -r 03_scripts/descarga/requirements_descarga.txt
python 03_scripts/descarga/00_ejecutar_todo.py

# 2. Limpiar y validar → 01_datos/procesados/*_validado.csv
python 03_scripts/etl/etl_pipeline.py

# 3. Dataset maestro municipal (lo usan los notebooks)
python 03_scripts/utilidades/construir_master_municipal.py

# 4. Volver a cargar la base: paso 4.2 y 4.3

# 5. Entrenar en 02_notebooks/: NB07, NB09, NB10, NB11, NB12 y NB08 (CNN, mejor con GPU o Colab)
pip install -r 02_notebooks/requirements_notebooks.txt
```

`run_all.bat` y `run_all.sh` ejecutan este flujo completo con las descargas. No son necesarios para usar la app y solo crean el esquema `01`: si los usas, ejecuta después `03_supabase_schema.sql`.

---

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| PowerShell no deja activar el entorno («la ejecución de scripts está deshabilitada») | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` y vuelve a activar |
| `psycopg2` no instala | `pip install psycopg2-binary` |
| `password authentication failed` al cargar | Revisa `PG_USER` y `PG_PASSWORD` en el `.env` de la raíz |
| Supabase: `connection refused` o `timeout` | Usa la cadena del **Session pooler** (IPv4), no la *Direct connection*, y `PGSSLMODE=require` |
| `there is no unique or exclusion constraint matching the ON CONFLICT` | Estás usando un script viejo: descarga la versión actual de `03_supabase_schema.sql` |
| `db_client.py` dice «faltan las tablas de venta directa» | Ejecuta `03_scripts/bd/05_marketplace.sql` |
| `db_client.py` dice «falta el KPI de interés en la venta directa» | Ejecuta `03_scripts/bd/06_kpi_interes_mercado.sql` |
| `dim_variedad_cafe` tiene 9 filas y no aparece «Catimor / Costa Rica 95» | Base creada antes de nov-2026: ejecuta `03_scripts/bd/07_variedad_catimor.sql` (la app no depende de esa tabla) |
| El asistente no conoce un documento nuevo de `documentos_fuente/` | Se reindexa solo al abrir «¿Qué hago?» cuando cambia el corpus. A mano: `python 06_agente_rag/rag_pipeline.py indexar --force` |
| El modelo de rendimiento no carga | `pip install scikit-learn==1.6.1` |
| «No se pudo cargar el agente RAG» o el asistente no responde | Falta `GROQ_API_KEY` en el `.env` (o en los Secrets de la nube), o no se hizo el paso 5 |
| La app no cambia después de editar código | Detén Streamlit (Ctrl+C) y vuelve a lanzarlo |
| Pytest: `PermissionError: [WinError 5] Acceso denegado: '...\\Temp\\pytest-of-<usuario>'` | Pasa con el Python de Microsoft Store. Usa un entorno `.venv` con Python 3.11 de python.org (paso 2). Mientras tanto: `python -m pytest tests -q --basetemp=%USERPROFILE%\\pytest_cofitech` |
| Pytest: fallan 4 pruebas de `test_seguridad.py` («DID NOT RAISE», `IndexError`) | El entorno tiene otra versión de Streamlit: instala las fijadas con `pip install -r 07_app_web/requirements.txt` dentro del `.venv` |
| En la nube la app se reinicia con `LLVM ERROR: inconsistency in registered CommandLine options` | Choque entre TensorFlow y Triton (PyTorch) en Linux; lo evita `cofitech/__init__.py`. No quites ese archivo ni importes TensorFlow antes de `cofitech` |
| `A module that was compiled using NumPy 1.x cannot be run in NumPy 2` o error en `st.dataframe` | Se instaló otra versión de `pyarrow` o `numpy`: reinstala con `pip install -r 07_app_web/requirements.txt` |
| La app en la nube dice que la base no responde después de unos días | Supabase pausó el proyecto: reanúdalo en su panel y activa el keep-alive (Producción, punto 4) |
| No puedo entrar: «necesitamos tu autorización» | Marca la casilla del aviso de privacidad en la pantalla de ingreso |
| No aparecen las páginas de administración | Paso 6 y entra por «Acceso administrador» |

---

## Lista de verificación

- [ ] Entorno creado y `pip install -r 07_app_web/requirements.txt` sin errores
- [ ] `.env` en la raíz con `GROQ_API_KEY` y los datos `PG_*`
- [ ] Base creada (`01` + `03` en local, o `03` en Supabase) con la fila `OK (v1.6)`
- [ ] `validar_pre_carga.py` con `Total OK: 6/6`
- [ ] `02_carga_inicial.py` con «CARGA INICIAL COMPLETADA» y los conteos del paso 4.4
- [ ] `db_client.py` con «tablas de venta directa listas»
- [ ] Índice del asistente creado
- [ ] App en http://localhost:8501 con el recorrido del paso 7 completo (franja BETA, casilla de autorización, venta inactiva)
- [ ] Pruebas en verde
- [ ] (Producción) App en Streamlit Community Cloud con Python 3.11 y los Secrets
- [ ] (Producción) Secreto `SUPABASE_DB_URL` en GitHub y el flujo *Supabase keep-alive* en verde
