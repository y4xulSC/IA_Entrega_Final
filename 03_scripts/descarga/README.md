# Scripts de descarga — Entrega Final

Scripts para enriquecer el dataset de la 2da entrega con fuentes adicionales que **resuelven las limitaciones identificadas**.

## Resumen de fuentes

| Script | Fuente | Resuelve | Tamaño aprox | Tiempo |
|--------|--------|----------|--------------|--------|
| `01_descargar_imagenes_cafe.py` | RoCoLe + BRACOL + JMuBEN + CoLeaf | CNN solo 47 imgs → ~10000 imgs | ~5 GB | 20-60 min |
| `02_descargar_precios_extendidos.py` | FRED + World Bank + IMF + ICO | Surge 2024-2025 fuera de distribución | ~10 MB | ~3 min |
| `03_descargar_clima_satelital.py` | CHIRPS + ERA5-Land + NDVI MODIS | Huecos de cobertura IDEAM | ~500 MB | 1-3 h |
| `04_descargar_eva_municipal.py` | DANE EVA municipal extendido | 14 obs → 1000+ obs municipales | ~20 MB | 5 min |
| `05_descargar_dem_suelos.py` | SRTM DEM + SoilGrids | Variables agronómicas faltantes | ~200 MB | 30 min |
| `06_consolidar_imagenes.py` | Local | Unifica RoCoLe+BRACOL+JMuBEN+CALIBRO en estructura común | — | 5 min |
| `00_ejecutar_todo.py` | — | Orquesta todos en orden | — | varias horas |

## Uso

```bash
cd IA_Entrega_Final/03_scripts/descarga
pip install -r requirements_descarga.txt

# Todo (recomendado primera vez, ~3 horas)
python 00_ejecutar_todo.py

# Solo lo más rápido y de mayor impacto inmediato
python 00_ejecutar_todo.py --solo precios eva consolidar

# Saltar imágenes si tienes poco espacio
python 00_ejecutar_todo.py --skip imagenes
```

## Requisitos previos

| Recurso | Necesario para | Cómo obtenerlo |
|---------|---------------|----------------|
| Cuenta Kaggle | RoCoLe, BRACOL, Coffee Leaf Diseases | https://www.kaggle.com/settings → Create API Token → guardar en `~/.kaggle/kaggle.json` |
| Cuenta NASA Earthdata | SRTM DEM | https://urs.earthdata.nasa.gov/ |
| Cuenta Copernicus CDS (opcional) | ERA5-Land | https://cds.climate.copernicus.eu/api-how-to |
| Espacio disco | Imágenes café | ~10 GB libres |

## Salidas esperadas

Después de ejecutar todo, en `01_datos/enriquecidos/` y `01_datos/imagenes_cafe/`:

```
01_datos/
├── enriquecidos/
│   ├── precios/
│   │   ├── fred_coffee_brazil.csv
│   │   ├── fred_coffee_robusta.csv
│   │   ├── world_bank_coffee.csv
│   │   ├── imf_coffee.csv
│   │   └── ico_composite_extended.csv
│   ├── clima/
│   │   ├── chirps_municipal_mensual.csv
│   │   ├── era5_land_dptos.csv
│   │   └── modis_ndvi_municipal.csv
│   ├── produccion/
│   │   └── eva_municipal_2007_2024.csv
│   ├── geografia/
│   │   ├── dem_municipal_altitud.csv
│   │   └── soilgrids_municipal.csv
│   └── eventos/
│       └── enso_eventos_historicos.csv
└── imagenes_cafe/
    ├── train/{Roya, Gotera, Cercospora, Phoma, Miner, Sano}/
    ├── val/{...}/
    ├── test/{...}/
    └── manifest_consolidado.csv
```

## Validación post-descarga

Ejecutar `python 99_validar_descargas.py` — verifica integridad y reporta huecos.
