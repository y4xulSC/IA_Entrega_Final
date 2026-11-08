# Guía de instalación

Pasos para dejar CofiTech funcionando después de clonar el repositorio: app, asistente RAG y base de datos con los datos históricos cargados. Los comandos están para **Windows PowerShell**; la versión Linux/Mac va al lado cuando cambia. Todos se ejecutan desde la raíz del repositorio, salvo que el paso diga otra cosa.

| Ruta | Pasos | Tiempo aproximado |
|---|---|---|
| Solo ver la app (sin base de datos) | 1, 2, 3, 5, 7 | 10 min |
| **Instalación completa** (app + base cargada) | 1 a 8 | 20–30 min |
| Regenerar datos y modelos desde cero | Anexo A | varias horas |

---

## Requisitos

| Componente | Versión | Notas |
|------------|---------|-------|
| Python | **3.11** (3.10–3.12) | TensorFlow y `numpy<2` no instalan bien en versiones más nuevas |
| PostgreSQL | 13 o superior (probado en 16 y 18) | Local con pgAdmin, o un proyecto gratis de [Supabase](https://supabase.com) |
| Git | cualquiera | |
| RAM | 8 GB | La app carga la CNN y el modelo de embeddings |
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
python -m venv .venv
.\.venv\Scripts\Activate.ps1           # Linux/Mac: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r 07_app_web/requirements.txt
```

`scikit-learn` está fijado en 1.6.1 porque el modelo de rendimiento (`.pkl`) solo carga con esa versión. La app necesita Streamlit 1.49 o superior.

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

La última fila debe decir `OK (v1.5) · esquema cafe con 18 tablas…; 5 compradores`.

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

Debe decir `OK · PostgreSQL … · tablas de venta directa listas`.

> **¿Ya tenías la base de una versión anterior (v1.4)?** Ejecuta solo `03_scripts/bd/05_marketplace.sql`: agrega las tablas de venta directa sin tocar lo demás. Detalle en `03_scripts/bd/README.md`.

---

## Paso 5 · Índice del asistente RAG

El índice de ChromaDB no está en git. Créalo una vez (la primera vez descarga el modelo de embeddings `all-MiniLM-L6-v2`, necesita internet):

```powershell
python 06_agente_rag/rag_pipeline.py indexar
```

Para probarlo sin abrir la app: `python 06_agente_rag/rag_pipeline.py demo` (requiere `GROQ_API_KEY` u Ollama). También se puede indexar desde la app, con el botón «Indexar documentos demo» de la pantalla del asistente.

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

1. **Ingreso:** elige «Soy caficultor», un municipio, y entra.
2. **Hoy en mi finca:** precio FNC, clima, tareas del mes y aviso de compradores.
3. **Revisar una hoja:** sube una foto de una hoja; aparece el diagnóstico con Grad-CAM.
4. **¿Qué hago?:** pregunta al asistente (necesita el paso 5).
5. **Vender mi café:** publica un lote; en «Mis lotes y mensajes» llega una oferta de un comprador de demostración.
6. **Cambiar de rol** → «Agrónomo / Cooperativa»: alertas fitosanitarias, indicadores y «Oferta de café en mi zona».

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

Con Streamlit 1.49 fallan 4 pruebas de `test_seguridad.py` porque esa versión del probador (`AppTest`) no lanza error al abrir una página no registrada; con versiones más nuevas pasan todas.

---

## Despliegue en Streamlit Community Cloud

1. Sube el repositorio a GitHub (sin `.env` ni `secrets.toml`: ya están en `.gitignore`).
2. En https://share.streamlit.io → *Create app* → repositorio, rama y archivo principal `07_app_web/app.py`.
3. En *Advanced settings* → *Python version* elige 3.11.
4. En *Settings* → *Secrets* pega el contenido de tu `secrets.toml`: `GROQ_API_KEY`, `COFITECH_ADMIN_HASH` (al inicio, antes de cualquier sección) y `[connections.postgresql] url` con la cadena del pooler de Supabase.
5. El índice del asistente no existe en la nube la primera vez: créalo con el botón «Indexar documentos demo» de la pantalla del asistente.

El despliegue oficial del proyecto no usa Docker. `08_docker/` es una configuración heredada.

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
| El modelo de rendimiento no carga | `pip install scikit-learn==1.6.1` |
| «No se pudo cargar el agente RAG» o el asistente no responde | Falta `GROQ_API_KEY` en el `.env` (o en los Secrets de la nube), o no se hizo el paso 5 |
| La app no cambia después de editar código | Detén Streamlit (Ctrl+C) y vuelve a lanzarlo |
| No aparecen las páginas de administración | Paso 6 y entra por «Acceso administrador» |

---

## Lista de verificación

- [ ] Entorno creado y `pip install -r 07_app_web/requirements.txt` sin errores
- [ ] `.env` en la raíz con `GROQ_API_KEY` y los datos `PG_*`
- [ ] Base creada (`01` + `03` en local, o `03` en Supabase) con la fila `OK (v1.5)`
- [ ] `validar_pre_carga.py` con `Total OK: 6/6`
- [ ] `02_carga_inicial.py` con «CARGA INICIAL COMPLETADA» y los conteos del paso 4.4
- [ ] `db_client.py` con «tablas de venta directa listas»
- [ ] Índice del asistente creado
- [ ] App en http://localhost:8501 con el recorrido del paso 7 completo
- [ ] Pruebas en verde
