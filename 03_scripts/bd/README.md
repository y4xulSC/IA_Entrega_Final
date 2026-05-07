# Base de datos PostgreSQL — Sistema IA Café

## Configuración esperada (la del usuario)

| Parámetro | Valor |
|-----------|-------|
| Versión | PostgreSQL 18.3 |
| Driver | psqlODBC 64bit v13.02.0000-1 |
| Host | localhost |
| Puerto | 5432 |
| Usuario | postgres |
| Contraseña | root |
| Base de datos | `cafe_ia` (a crear) |

## Pasos de instalación

### 1. Crear la base
```bash
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE cafe_ia;"
```

### 2. Cargar el esquema (DDL)
```bash
psql -U postgres -h localhost -p 5432 -d cafe_ia -f 01_ddl_schema.sql
```

Esto crea:
- 7 tablas dimensionales/auxiliares
- 5 tablas de hechos
- 1 vista materializada (`vw_master_municipal_mensual`)
- Triggers de calidad de datos
- Datos semilla (33 departamentos, 9 variedades, 6 enfermedades, 6 eventos ENSO)

### 3. Cargar datos iniciales (Python)
```bash
cd 03_scripts/bd
pip install psycopg2-binary pandas
python 02_carga_inicial.py
```

Carga en orden:
1. `dim_periodo` — calendario 1990-2030
2. ONI/ENSO actualizado
3. `dim_municipio` — desde DEM + suelos
4. `fact_produccion` — EVA 2da entrega + EVA municipal extendido
5. `fact_precio` — FNC + precios consolidados
6. `fact_imagen_enfermedad` — manifest consolidado
7. Refresh vista materializada

### 4. Verificar
```sql
-- Tablas creadas
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'cafe' ORDER BY table_name;

-- Conteos
SELECT 'dim_departamento' AS tabla, count(*) FROM cafe.dim_departamento
UNION ALL SELECT 'dim_municipio',     count(*) FROM cafe.dim_municipio
UNION ALL SELECT 'dim_periodo',       count(*) FROM cafe.dim_periodo
UNION ALL SELECT 'dim_enfermedad',    count(*) FROM cafe.dim_enfermedad
UNION ALL SELECT 'dim_variedad_cafe', count(*) FROM cafe.dim_variedad_cafe
UNION ALL SELECT 'fact_produccion',   count(*) FROM cafe.fact_produccion
UNION ALL SELECT 'fact_clima',        count(*) FROM cafe.fact_clima
UNION ALL SELECT 'fact_precio',       count(*) FROM cafe.fact_precio
UNION ALL SELECT 'fact_imagen_enfermedad', count(*) FROM cafe.fact_imagen_enfermedad;

-- Tablón maestro
SELECT * FROM cafe.vw_master_municipal_mensual LIMIT 5;
```

## Diccionario de datos

Ver `10_diccionario_datos/DICCIONARIO_DATOS.md` en la raíz del proyecto.

Para auto-documentación viva, consultar `cafe.aux_diccionario_columnas`.

## Backup y restore

```bash
# Backup
pg_dump -U postgres -h localhost -d cafe_ia -n cafe -F c -f cafe_ia_backup.dump

# Restore
pg_restore -U postgres -h localhost -d cafe_ia -c cafe_ia_backup.dump
```

## Reglas de calidad implementadas

- `CHECK` sobre rangos válidos (temperatura, severidad, áreas)
- Trigger auto-cálculo de `rendimiento_ton_ha` si falta
- `UNIQUE` constraints en `(id_municipio, id_periodo, fuente)` clima
- Foreign keys con cascade adecuado
- Índices en campos de filtro frecuente (anio, fuente, dataset)

## Cambios futuros (versionado)

| Versión | Fecha | Cambio |
|---------|-------|--------|
| 1.0 | 2026-05 | Esquema inicial entrega final |
