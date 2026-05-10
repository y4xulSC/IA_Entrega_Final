# 01_datos/originales/

Datos descargados **manualmente** o que vienen de **entregas previas / fuentes únicas**.

## Convención

Esta carpeta es para datos **estables y persistentes** que no se regeneran por scripts.
Si un archivo aquí tiene una contraparte automática en `enriquecidos/`, prevalece el de `originales/` para auditoría.

## Estructura espejo de `enriquecidos/`

```
originales/
├── precios/         # ICO histórico, archivos manuales de FRED/WB/IMF
├── clima/           # series climáticas IDEAM, archivos manuales
├── produccion/      # CSV de FNC, EVA descargada manualmente
├── geografia/       # shapefiles DIVIPOLA, rasters DEM locales
└── otros/           # cualquier otra fuente confiable
```

## Reglas

1. **Nunca borrar** archivos aquí — son la fuente de verdad estable.
2. **Documentar la fuente** de cada archivo en `MANIFEST.md` (autor, fecha, URL).
3. **Naming convention**: usar el mismo nombre que el script automático produciría
   en `enriquecidos/` para que el consolidador los recoja sin cambios.

## Ejemplo

| Archivo en originales/ | Equivalente en enriquecidos/ | Fuente |
|---|---|---|
| `precios/ico_composite_extended.csv` | (no se genera por API ahora) | descarga manual ICO 2024 |
| `produccion/eva_2007_2018_manual.csv` | `produccion/eva_cafe_municipal_2007_2024.csv` | base 2da entrega |

## Cómo se usa

El consolidador de precios (`02_descargar_precios_extendidos.py → consolidar()`) lee
de **ambas** carpetas (`originales/precios/` + `enriquecidos/precios/`) y deduplica
por fecha. Esto permite que tus archivos manuales entren al `precios_consolidados_mensual.csv`.
