# ETL Pipeline por categoría

## Qué es esto

Pipeline que toma los **datos ya descargados** en `01_datos/enriquecidos/`
y, por cada categoría de fuente, aplica:

1. **Validación específica del dominio** (rangos físicos, coherencia, cobertura)
2. **Consolidación canónica** (renombre a esquema único, cruce intra-categoría)
3. **Reporte de calidad** (JSON por categoría + resumen MD)

La descarga de la data se hizo con los scripts de `03_scripts/descarga/`.

## Categorías y reglas aplicadas

| Categoría | Fuentes que consolida | Reglas clave |
|-----------|------------------------|---------------|
| **precios** | FRED Brasil + FRED Robusta + WB + IMF + ICO + BanRep TRM + FNC 2da entrega | Normaliza USD/lb → USD/kg, COP/125kg → COP/kg; rangos USD/kg ∈ [0.5,30], TRM ∈ [1500,6000]; surge MoM > 25%; cobertura ≥ 60 meses |
| **clima** | Open-Meteo mensual | T en [-5,45]°C, precip ≥ 0, Tmin ≤ Tmedia ≤ Tmax; continuidad mensual por municipio; deduplicación |
| **enso** | NOAA ONI | rango ONI ∈ [-3,3]; recálculo coherente de fase (Niño/Niña/Neutro); deduplicación |
| **produccion** | EVA municipal Socrata | código DANE 5 dígitos; solo café (descarta tostado/soluble/extracto); rendimiento = producción/área (tolerancia 0.5 ton/ha); rendimiento ∈ [0.1,5] ton/ha; dedup por (DANE, año, cultivo) |
| **geografia** | DEM altitudes + SoilGrids suelos | altitud ∈ [0,4500] msnm; pH ajustado por d_factor (∈ [3,9]); SOC plausible; merge por código DANE |
| **imagenes** | manifest_consolidado.csv | integridad de archivos (existe + abre con PIL); resolución mínima 100×100 (solo reporta, no descarta); SHA1 del archivo completo para detectar duplicados byte-exactos; balance por (clase, split) |

### Por qué cada parámetro de imágenes

**Resolución mínima 100×100** — solo se reporta, no se descarta.
EfficientNetB0/ResNet50 esperan 224×224. Una imagen de 60×60 escalada a
224×224 produce pixelado que la CNN no aprende. Pero **eliminar imágenes
pequeñas automáticamente puede borrar información útil** (fotos de hojas
recortadas que aún tienen las lesiones visibles), por eso se reporta la
cuenta y se deja al usuario decidir si filtra en el `flow_from_directory`.

**Hash SHA1 del archivo COMPLETO** — antes usaba MD5 de los primeros 64KB
y eso reportaba falsos duplicados masivamente: JPGs del mismo dataset
comparten header EXIF y tablas de cuantización, así que el primer 64KB
suele ser idéntico aunque la imagen sea distinta. Hash del archivo
completo es 100% exacto byte-a-byte.

**Eliminación**: del manifest validado se sacan las imágenes que
(a) no existen en disco, (b) PIL no las abre, **(c) son duplicados
byte-exactos** (se conserva la primera ocurrencia). Las imágenes
pequeñas (<100×100) se mantienen — el notebook NB08 puede filtrarlas
en el `flow_from_directory` si lo desea.

**Razón para eliminar duplicados**: si un archivo es **byte por byte
idéntico** a otro, no aporta información al entrenamiento — solo
infla los conteos y sesga el split (la misma imagen puede caer en
train y val a la vez). Es común que pase con datasets RoCoLe + BRACOL +
JMuBEN/JMuBEN2 + Coffee Leaf de Kaggle porque hay re-mirrors entre
ellos. El reporte JSON incluye `eliminadas_duplicadas` y
`balance_split_clase_final` para que veas el dataset efectivo de
training.

## Salidas

```
01_datos/procesados/
├── precios_validado.csv          # canónico mensual: USD/kg + COP/kg + TRM + flags
├── clima_validado.csv            # canónico mensual por municipio
├── enso_validado.csv             # canónico mensual con fase coherente
├── produccion_validado.csv       # EVA municipal limpio (solo café)
├── geografia_validado.csv        # DEM + suelos por municipio
├── imagenes_validado.csv         # manifest depurado (solo archivos vivos)
└── etl_reportes/
    ├── precios.json
    ├── clima.json
    ├── enso.json
    ├── produccion.json
    ├── geografia.json
    ├── imagenes.json
    └── RESUMEN.md                # tabla consolidada + warnings/errores
```

## Uso

```powershell
# Todo el pipeline
python 03_scripts/etl/etl_pipeline.py

# Solo algunas categorías
python 03_scripts/etl/etl_pipeline.py --solo precios clima enso

# Ver qué pasaría sin escribir archivos
python 03_scripts/etl/etl_pipeline.py --dry-run

# Hacer fallar la sesión si hay errores (útil en CI)
python 03_scripts/etl/etl_pipeline.py --strict
```

## Output esperado en consola (resumen)

```
======================================================================
 ETL Pipeline por categoria
======================================================================
Categorias    : ['precios','clima','enso','produccion','geografia','imagenes']
Dry run       : False
Salida CSV    : 01_datos\procesados
Reportes JSON : 01_datos\procesados\etl_reportes

----------------------------------------------------------------------
[precios] iniciando ...
  -> OK  in=8  out=444  err=0  warn=2
     WARN precio_robusta_wb_usd_kg con cobertura debil: 48 meses
     WARN precio_arabica_brasil_usd_kg: 3 valores fuera [0.5,30]
[clima] iniciando ...
  -> OK  in=6928  out=6912  err=0  warn=1
     WARN clima con 16 huecos mensuales acumulados entre municipios
[enso] iniciando ...
  -> OK  in=915  out=912  err=0  warn=1
[produccion] iniciando ...
  -> OK  in=7263  out=2841  err=0  warn=2
     WARN filtrado cultivo: 7263 -> 2841 filas
[geografia] iniciando ...
  -> OK  in=42  out=21  err=0  warn=0
[imagenes] iniciando ...
  -> OK  in=10145  out=10142  err=0  warn=1
     WARN 3 posibles duplicados por hash

Resumen MD: 01_datos\procesados\etl_reportes\RESUMEN.md

======================================================================
  OK   : 6/6 categorias
  FAIL : 0/6
======================================================================
```

## Después del pipeline

Los `*_validado.csv` son los que debes cargar a PostgreSQL.
Cuando ejecutes `02_carga_inicial.py`, ya puedes apuntarlo a esos
archivos (o lo ajustamos en un siguiente paso para que prefiera
`01_datos/procesados/<x>_validado.csv` antes que el raw enriquecido).

También `construir_master_municipal.py` puede leer estos validados
como fuente preferida — así tu master parte de datos limpios.
