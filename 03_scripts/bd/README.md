# Base de datos PostgreSQL — Sistema IA Café

## Configuración esperada

Se lee desde `.env` en la raíz del proyecto:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `PG_HOST` | localhost | |
| `PG_PORT` | 5432 | |
| `PG_USER` | postgres | |
| `PG_PASSWORD` | root | |
| `PG_DB` | cafe_ia | |
| `LOG_LEVEL` | INFO | DEBUG/INFO/WARNING/ERROR |
| `LOG_DIR` | 05_resultados/logs | Logs auto-generados |

## Archivos

| Archivo | Función |
|---------|---------|
| `01_ddl_schema.sql` | DDL completo: tablas, vistas, triggers, datos semilla |
| `_config_bd.py` | Módulo común: lee `.env`, configura logging, abre conexión |
| `validar_pre_carga.py` | Reporte calidad de los `*_validado.csv` antes de cargar |
| `02_carga_inicial.py` | Carga los validados a la BD (idempotente, con UPSERTs) |
| `03_supabase_schema.sql` | Versión del DDL para el SQL Editor de Supabase + tablas de la app (ver sección Supabase) |
| `db_client.py` | Cliente de la app Streamlit para Supabase |
| `04_vistas_kpis.sql` | Solo las vistas de KPIs (`telemetria_kpis`, `vw_kpis_consolidados`), para bases que ya tenían el esquema v1.3 |

## Flujo recomendado

### Paso 1 — Configurar `.env`
```bash
archivo .env
# Editar .env si tus credenciales son diferentes:
# ─── PostgreSQL ──────────────────────────────────────────────────────────
PG_HOST=[host]
PG_PORT=[puerto]
PG_USER=[usuario_postgres]
PG_PASSWORD=[contraseña]
PG_DB=cafe_ia # Importante mantener el nombre de la base de datos
# ─── Configuracion de logging ────────────────────────────────────────────
# DEBUG | INFO | WARNING | ERROR
LOG_LEVEL=INFO
LOG_DIR=05_resultados/logs
```

### Paso 2 — Crear la BD (una sola vez)
```bash
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE cafe_ia;"
psql -U postgres -h localhost -p 5432 -d cafe_ia -f 03_scripts/bd/01_ddl_schema.sql
```

### Paso 3 — Validar los CSVs antes de cargar
```bash
python 03_scripts/bd/validar_pre_carga.py
```

Output: tabla con shape, nulos PK, duplicados, outliers físicos por tabla. Si todo OK,
genera reporte MD en `05_resultados/reportes/pre_carga_<timestamp>.md`.

### Paso 4 — Cargar
```bash
python 03_scripts/bd/02_carga_inicial.py
```

Carga en orden: `dim_periodo → ONI → dim_municipio → fact_clima → fact_precio → fact_produccion → fact_imagen_enfermedad → vista materializada`. Usa UPSERTs por PK natural (idempotente: puedes correrlo 2 veces sin duplicar).

Logs: `05_resultados/logs/carga_inicial_<timestamp>.log` y consola.

### Paso 5 — Verificar
```sql
SELECT 'dim_periodo' AS t,         count(*) FROM cafe.dim_periodo
UNION ALL SELECT 'dim_municipio',     count(*) FROM cafe.dim_municipio
UNION ALL SELECT 'fact_clima',        count(*) FROM cafe.fact_clima
UNION ALL SELECT 'fact_precio',       count(*) FROM cafe.fact_precio
UNION ALL SELECT 'fact_produccion',   count(*) FROM cafe.fact_produccion
UNION ALL SELECT 'fact_imagen_enfermedad', count(*) FROM cafe.fact_imagen_enfermedad;

SELECT * FROM cafe.vw_master_municipal_mensual LIMIT 5;
```

## Supabase (nube, sin Docker)

La app guarda en Supabase cada foto diagnosticada (`cafe.registro_diagnosticos`), el 👍/👎 del caficultor y la telemetría con las calificaciones del chat (`cafe.registro_eventos_uso`, vista `cafe.vw_feedback_rag`). El mapa de **Alertas fitosanitarias** (rol Agrónomo / Cooperativa) lee de ahí y se refresca cada 30 s. Si la base no responde, la app sigue con los archivos locales de `05_resultados/logs/` y lo avisa en pantalla.

| Archivo | Función |
|---------|---------|
| `03_supabase_schema.sql` | Esquema en estrella + tablas transaccionales, listo para el SQL Editor de Supabase. Idempotente: se puede volver a ejecutar sin borrar datos |
| `db_client.py` | Cliente de la app (psycopg2 con pool, reintento en pausa de 60 s, `connect_timeout` de 5 s) |

### Paso 1 — Crear las tablas
Supabase → **SQL Editor** → **New query** → pegar todo `03_supabase_schema.sql` → **Run**. La última fila dice `OK · esquema cafe con 14 tablas…`.

Seguridad: el esquema `cafe` no se publica en la Data API, tiene RLS activado sin políticas y se le retiran los permisos a `anon` y `authenticated`. La llave pública (`anon key`) de Supabase no puede leerlo; solo la app con la contraseña de la base.

### Paso 2 — Credenciales
Supabase → **Connect** → **Session pooler** (puerto 5432, funciona por IPv4; la *Direct connection* solo por IPv6). Copiar la cadena y reemplazar `[YOUR-PASSWORD]`.

Opción A — `07_app_web/.streamlit/secrets.toml` (no se sube a git; plantilla en `secrets.toml.example`):
```toml
[connections.postgresql]
url = "postgresql://postgres.<PROJECT_REF>:<CONTRASEÑA>@aws-0-<REGION>.pooler.supabase.com:5432/postgres"
```
Opción B — `.env` en la raíz: `SUPABASE_DB_URL=postgresql://...`

En Streamlit Community Cloud el contenido de `secrets.toml` va en **Settings → Secrets**.

### Paso 3 — Probar
```bash
python 03_scripts/bd/db_client.py      # OK · PostgreSQL 17.x · N diagnósticos · M eventos
```
Reiniciar Streamlit. En el panel lateral **Depuración** aparece `Supabase: conectada`.

### Paso 4 (opcional) — Coordenadas de todos los municipios
```bash
python 03_scripts/descarga/08_descargar_divipola.py
```
Sin este archivo el mapa de alertas solo ubica las 21 cabeceras de `geografia_validado.csv`; los demás municipios aparecen listados debajo del mapa.

### Paso 5 (opcional) — Cargar el esquema en estrella con los datos históricos
`02_carga_inicial.py` funciona contra Supabase si el `.env` apunta al pooler: `PG_HOST=aws-0-<REGION>.pooler.supabase.com`, `PG_PORT=5432`, `PG_USER=postgres.<PROJECT_REF>`, `PG_DB=postgres`, `PG_PASSWORD=<contraseña>` y `PGSSLMODE=require`.

### Pruebas
```bash
cd 07_app_web
python -m pytest tests/test_persistencia.py -q -rs
# con una base de PRUEBAS (nunca la de producción):
COFITECH_TEST_DB_URL=postgresql://... python -m pytest tests/test_persistencia.py -q
```

## Cambios en el DDL respecto a versión 1.0

- `fact_clima`: agregadas `viento_max_kmh`, `radiacion_mj_m2`. Tipos numéricos ampliados (NUMERIC(5,2) para temperatura).
- `fact_precio`: schema canónico en USD/kg y COP/kg (antes USD/lb y COP/125kg). Agregada `surge_flag`. Agregada `precio_arabica_brasil_cop_kg` (derivada).
- Vista materializada: actualizada para los nuevos nombres.

## Modos de carga

```bash
# Solo algunos pasos
python 02_carga_inicial.py --solo periodos oni clima

# Saltar pasos (ej. imágenes que son las más pesadas)
python 02_carga_inicial.py --skip imagenes

# Refrescar solo la vista
python 02_carga_inicial.py --refresh-vistas
```

## Backup y restore

```bash
pg_dump -U postgres -h localhost -d cafe_ia -n cafe -F c -f cafe_ia_backup.dump
pg_restore -U postgres -h localhost -d cafe_ia -c cafe_ia_backup.dump
```

## Versionado

| Versión | Fecha | Cambio |
|---------|-------|--------|
| 1.0 | 2026-05 | Esquema inicial |
| 1.1 | 2026-05 | Alineado con `*_validado.csv` (USD/kg, viento, radiación, surge_flag); carga lee de `procesados/`; `.env` + logging real |
