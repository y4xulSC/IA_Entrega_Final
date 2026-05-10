# Utilidades — ETL y herramientas comunes

## `construir_master_municipal.py` ⭐ IMPORTANTE

Este script construye el archivo `01_datos/procesados/master_cafe_municipal_mensual.csv`
que **todos los notebooks NB07-NB12 esperan encontrar**.

### Cuándo ejecutarlo

Después de:
1. Haber descargado los nuevos datos (`03_scripts/descarga/00_ejecutar_todo.py`)
2. Opcionalmente, haber cargado los datos en PostgreSQL

### Cómo ejecutarlo

```bash
cd 03_scripts/utilidades
python construir_master_municipal.py
```

### Qué hace internamente

Tiene dos modos automáticos:

**Modo A — BD (preferido):** si PostgreSQL `cafe_ia` está cargado, lee directamente
de la vista materializada `cafe.vw_master_municipal_mensual` que ya tiene el cruce
hecho por las foreign keys.

**Modo B — CSVs (fallback):** si no hay BD, lee y cruza directamente los CSVs
en `01_datos/enriquecidos/`:
- `precios/precios_consolidados_mensual.csv`
- `clima/openmeteo_municipios_mensual.csv`
- `clima/enso_oni_extendido.csv`
- `produccion/eva_cafe_municipal_2007_2024.csv`
- `geografia/dem_municipal_altitud.csv`
- `geografia/soilgrids_municipal.csv`

Luego aplica feature engineering:
- Lags 1, 3, 6, 12 meses para temperatura, precipitación, ONI, precios
- Rolling means 3, 6, 12 meses
- Estrés hídrico (ET0 − precipitación)
- Amplitud térmica (Tmax − Tmin)
- Dummies de fase ENSO (`es_nino`, `es_nina`)
- Intensidad ENSO continua

### Salida

Dos archivos en `01_datos/procesados/`:
- `master_cafe_municipal_mensual.csv` — granularidad municipio × mes
- `master_cafe_municipal_anual.csv` — agregado anual (útil para modelos de rendimiento)

### Opciones

```bash
# Forzar modo BD (falla si no hay BD)
python construir_master_municipal.py --modo bd

# Forzar modo CSV (saltar BD aunque exista)
python construir_master_municipal.py --modo csv

# Filtrar solo a departamentos cafeteros
python construir_master_municipal.py --solo-cafeteros
```

### Variables de entorno (modo BD)

```bash
export PG_HOST=localhost
export PG_PORT=5432
export PG_USER=postgres
export PG_PASSWORD=root
export PG_DB=cafe_ia
```
