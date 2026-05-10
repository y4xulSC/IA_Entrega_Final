# RESUMEN ETL · 2026-05-09T07:24:13

| Categoria | Estado | n_in | n_out | Errores | Warnings |
|---|---|---|---|---|---|
| precios | OK | 6 | 444 | 0 | 0 |
| clima | OK | 6928 | 6928 | 0 | 0 |
| enso | OK | 915 | 915 | 0 | 0 |
| produccion | OK | 7263 | 7263 | 0 | 3 |
| geografia | OK | 42 | 21 | 0 | 0 |
| imagenes | OK | 65775 | 10846 | 0 | 2 |

## precios
**Archivo:** `01_datos\procesados\precios_validado.csv`

**Metricas:**
- `fred_brazil_meses`: 411
- `fred_brazil_unidad_origen`: cents/lb -> USD/kg
- `fred_robusta_meses`: 411
- `fred_robusta_unidad_origen`: cents/lb -> USD/kg
- `wb_meses`: 780
- `trm_meses`: 272
- `fnc_meses`: 96
- `meses_con_surge_>25%`: 6

## clima
**Archivo:** `01_datos\procesados\clima_validado.csv`

**Metricas:**
- `filas_temp_inconsistente`: 0
- `huecos_temporales_municipales`: 0
- `municipios_distintos`: 16
- `rango_fechas`: 1990-01-01|2026-01-01
- `anios_distintos`: 37

## enso
**Archivo:** `01_datos\procesados\enso_validado.csv`

**Metricas:**
- `oni_no_nulos`: 915
- `rango_fechas`: 1950-01-01|2026-03-01
- `conteo_fases`: {'Neutro': 418, 'Nina': 252, 'Nino': 245}

## produccion
**Archivo:** `01_datos\procesados\produccion_validado.csv`

**Warnings:**
- codigo_dane derivado directamente de 'c_d_mun' (longitud tipica=5, zfill a 5)
- 1 filas con rendimiento incoherente (>0.5 ton/ha de error)
- rendimiento fuera [0.1, 5] ton/ha en 13 filas

**Metricas:**
- `filas_rendimiento_incoherente`: 1
- `municipios_distintos`: 657
- `filas_post_filtros`: 7263
- `rango_anios`: 2007|2018
- `municipios_x_anio`: {2007: 593, 2008: 598, 2009: 614, 2010: 620, 2011: 627, 2012: 625, 2013: 597, 2014: 595, 2015: 595, 2016: 598, 2017: 600, 2018: 601}

## geografia
**Archivo:** `01_datos\procesados\geografia_validado.csv`

**Metricas:**
- `municipios`: 21

## imagenes
**Archivo:** `01_datos\procesados\imagenes_validado.csv`

**Warnings:**
- 2375 imagenes <100px (se mantienen)
- 54929 duplicados byte-exactos detectados (SE ELIMINAN del manifest validado; original conservada)

**Metricas:**
- `archivos_faltantes`: 0
- `archivos_corruptos`: 0
- `archivos_resolucion<100px`: 2375
- `duplicados_byte_exactos`: 54929
- `duplicados_ejemplos`: [{'original': 'train\\Cercospora\\jmuben_9 (1776).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (1812).jpg'}, {'original': 'train\\Cercospora\\jmuben_7 (356).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (458).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (3464).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (3432).jpg'}, {'original': 'train\\Cercospora\\jmuben_7 (163).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (142).jpg'}, {'original': 'train\\Cercospora\\jmuben_8 (210).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (1440).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (2775).jpg', 'duplicada': 'train\\Cercospora\\jmuben_4 (1001).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (1143).jpg', 'duplicada': 'train\\Cercospora\\jmuben_8 (867).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (564).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (548).jpg'}, {'original': 'train\\Cercospora\\jmuben_7 (602).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (596).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (345).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (455).jpg'}, {'original': 'train\\Cercospora\\jmuben_8 (517).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (1763).jpg'}, {'original': 'train\\Cercospora\\jmuben_7 (163).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (165).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (3102).jpg', 'duplicada': 'train\\Cercospora\\jmuben_6 (540).jpg'}, {'original': 'train\\Cercospora\\jmuben_6 (506).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (3098).jpg'}, {'original': 'train\\Cercospora\\jmuben_6 (902).jpg', 'duplicada': 'train\\Cercospora\\jmuben_6 (909).jpg'}, {'original': 'train\\Cercospora\\jmuben_7 (347).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (360).jpg'}, {'original': 'train\\Cercospora\\jmuben_7 (933).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (845).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (1143).jpg', 'duplicada': 'train\\Cercospora\\jmuben_8 (947).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (3464).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (3460).jpg'}, {'original': 'train\\Cercospora\\jmuben_6 (292).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (2917).jpg'}, {'original': 'train\\Cercospora\\jmuben_4 (712).jpg', 'duplicada': 'train\\Cercospora\\jmuben_4 (737).jpg'}, {'original': 'train\\Cercospora\\jmuben_6 (552).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (3114).jpg'}, {'original': 'train\\Cercospora\\jmuben_7 (933).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (925).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (3830).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (3746).jpg'}, {'original': 'train\\Cercospora\\jmuben_4 (1057).jpg', 'duplicada': 'train\\Cercospora\\jmuben_4 (1129).jpg'}, {'original': 'train\\Cercospora\\jmuben_8 (209).jpg', 'duplicada': 'train\\Cercospora\\jmuben_8 (195).jpg'}, {'original': 'train\\Cercospora\\jmuben_8 (689).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (982).jpg'}, {'original': 'train\\Cercospora\\jmuben_4 (1090).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (2828).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (3202).jpg', 'duplicada': 'train\\Cercospora\\jmuben_6 (596).jpg'}, {'original': 'train\\Cercospora\\jmuben_6 (385).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (3003).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (800).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (802).jpg'}, {'original': 'train\\Cercospora\\jmuben_6 (724).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (3211).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (2449).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (2455).jpg'}, {'original': 'train\\Cercospora\\jmuben_7 (409).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (413).jpg'}, {'original': 'train\\Cercospora\\jmuben_8 (26).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (1362).jpg'}, {'original': 'train\\Cercospora\\jmuben_7 (821).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (859).jpg'}, {'original': 'train\\Cercospora\\jmuben_8 (192).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (1430).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (1765).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (1747).jpg'}, {'original': 'train\\Cercospora\\jmuben_8 (297).jpg', 'duplicada': 'train\\Cercospora\\jmuben_8 (388).jpg'}, {'original': 'train\\Cercospora\\jmuben_6 (451).jpg', 'duplicada': 'train\\Cercospora\\jmuben_6 (525).jpg'}, {'original': 'train\\Cercospora\\jmuben_7 (179).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (195).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (2378).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (2344).jpg'}, {'original': 'train\\Cercospora\\jmuben_4 (473).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (2357).jpg'}, {'original': 'train\\Cercospora\\jmuben_8 (517).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (1760).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (216).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (374).jpg'}, {'original': 'train\\Cercospora\\jmuben_8 (689).jpg', 'duplicada': 'train\\Cercospora\\jmuben_8 (714).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (2502).jpg', 'duplicada': 'train\\Cercospora\\jmuben_4 (636).jpg'}, {'original': 'train\\Cercospora\\jmuben_7 (514).jpg', 'duplicada': 'train\\Cercospora\\jmuben_7 (520).jpg'}, {'original': 'train\\Cercospora\\jmuben_4 (79).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (2017).jpg'}, {'original': 'train\\Cercospora\\jmuben_9 (1143).jpg', 'duplicada': 'train\\Cercospora\\jmuben_9 (1139).jpg'}]
- `dim_min`: 64x64
- `dim_max`: 4128x4000
- `dim_mediana`: 128x128
- `balance_split_clase_input`: {'Cercospora': {'test': 1178, 'train': 5495, 'val': 1177}, 'Gotera': {'test': 6, 'train': 22, 'val': 4}, 'Miner': {'test': 2597, 'train': 12115, 'val': 2596}, 'Phoma': {'test': 1179, 'train': 5499, 'val': 1178}, 'Roya': {'test': 1738, 'train': 8105, 'val': 1736}, 'Sano': {'test': 3085, 'train': 14391, 'val': 3083}, 'SpiderMite': {'test': 90, 'train': 413, 'val': 88}}
- `eliminadas_faltantes`: 0
- `eliminadas_corruptas`: 0
- `eliminadas_duplicadas`: 54929
- `conservadas_unicas`: 10846
- `balance_split_clase_final`: {'Cercospora': {'test': 24, 'train': 447, 'val': 20}, 'Gotera': {'test': 6, 'train': 22, 'val': 4}, 'Miner': {'test': 43, 'train': 1874, 'val': 52}, 'Phoma': {'test': 189, 'train': 1600, 'val': 187}, 'Roya': {'test': 483, 'train': 3310, 'val': 441}, 'Sano': {'test': 199, 'train': 1148, 'val': 224}, 'SpiderMite': {'test': 89, 'train': 399, 'val': 85}}
