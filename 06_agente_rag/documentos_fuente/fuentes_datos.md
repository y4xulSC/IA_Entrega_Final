# Fuentes de datos integradas en el Sistema IA Café

El sistema consolida 11 fuentes públicas en una base de datos PostgreSQL
con esquema en estrella. Todas son reproducibles desde los scripts
de descarga en `03_scripts/descarga/`.

## EVA Café (Evaluaciones Agropecuarias Municipales)

- **Fuente:** Ministerio de Agricultura y Desarrollo Rural (MADR) /
  datos.gov.co vía API Socrata.
- **Período:** 2007-2024.
- **Granularidad:** municipal × año × cultivo.
- **Variables:** área sembrada (ha), área cosechada (ha), producción
  (toneladas), rendimiento (ton/ha), estado físico, ciclo de cultivo,
  variedad cuando reportada.
- **Filas en el sistema:** 7263 registros filtrados a café.
- **Resuelve:** la limitación de la 2da entrega de tener solo 14
  observaciones de test a nivel departamental.

## FNC Mensual (Federación Nacional de Cafeteros)

- **Fuente:** publicaciones públicas de FNC.
- **Período:** 2018-2025.
- **Variables:** precio interno COP/125 kg, producción mensual en sacos
  60 kg, exportaciones mensuales.
- **Filas:** ~84 meses iniciales, ampliados.

## ICO Composite (International Coffee Organization)

- **Fuente:** ICO publicaciones mensuales.
- **Período:** 1990-2026 (ampliado en la entrega final).
- **Variables:** precio compuesto USD/libra de los 4 grupos de café
  (Colombian Milds, Other Milds, Brasilian Naturals, Robustas).

## NOAA ONI (Oceanic Niño Index)

- **Fuente:** NOAA Climate Prediction Center.
- **Período:** 1950-2026.
- **Variables:** índice ONI mensual, fase ENSO derivada (Niño / Niña /
  Neutro). Umbrales: Niño si ONI ≥ +0.5, Niña si ONI ≤ −0.5.
- **Filas:** 915 meses.
- **Uso:** variable exógena en modelos de rendimiento y precio.

## Open-Meteo Historical (clima por municipio)

- **Fuente:** Open-Meteo API (gratis, sin API key).
- **Período:** 1990-2026.
- **Variables:** temperatura media/mínima/máxima diaria, precipitación
  diaria, ET0 evapotranspiración, viento máximo, radiación solar.
- **Granularidad:** municipal (21 municipios cafeteros principales),
  agregado a frecuencia mensual.
- **Filas:** 6928 registros municipio-mes.
- **Resuelve:** la limitación de cobertura IDEAM (estaciones no llegan
  a todos los municipios).

## FRED St. Louis Fed (precios commodity)

- **Fuente:** Federal Reserve Bank of St. Louis (FRED).
- **Período:** 1990-presente.
- **Variables:** precio Café Brasil (PCOFFOTMUSDM) y Café Robusta
  (PCOFFROBUSDM), en USD/kg tras conversión de cents/lb.
- **Uso:** baseline internacional para LSTM y validación cruzada con FNC.

## World Bank Pink Sheet

- **Fuente:** Banco Mundial Commodity Markets Pink Sheet.
- **Período:** 1960-presente.
- **Variables:** precio Arabica y Robusta en USD/kg.
- **Uso:** segunda fuente de validación para precios internacionales.

## BanRep TRM

- **Fuente:** Banco de la República Colombia.
- **Período:** 1990-presente.
- **Variables:** Tasa Representativa del Mercado (USD/COP).
- **Uso:** conversión de precios USD a COP, variable exógena en LSTM.

## SoilGrids ISRIC (suelos)

- **Fuente:** ISRIC SoilGrids 250m API REST.
- **Período:** snapshot 2020.
- **Variables:** pH H2O (phh2o_0_30cm), carbono orgánico (soc), arcilla,
  arena, capacidad intercambio catiónico (CEC), por profundidad.
- **Granularidad:** municipal (21 municipios cafeteros).
- **Uso:** features agronómicas en modelo de rendimiento (NB09).

## SRTM DEM (altitudes)

- **Fuente:** NASA Earthdata SRTM 30m vía Open-Elevation API.
- **Variables:** altitud media municipal en msnm.
- **Granularidad:** municipal.
- **Uso:** feature crítico para predicción de calidad y rendimiento de café.

## CALIBRO + datasets de imágenes

- **Fuentes:** CALIBRO (47 imágenes Colombia, 2da entrega) + RoCoLe
  (1560 imgs Ecuador) + BRACOL (4707 imgs Brasil con crops) + JMuBEN
  (58549 imgs Kenia, mayoría duplicados) + Coffee Leaf Kaggle (2081 imgs).
- **Total único tras dedup byte-exacto:** ~10846 imágenes.
- **Clases:** Roya, Gotera, Cercospora, Phoma, Miner, Sano, SpiderMite.
- **Uso:** entrenamiento del CNN (NB08).

## Esquema de la base de datos PostgreSQL

| Tabla | Filas aprox |
|---|---|
| dim_departamento | 33 |
| dim_municipio | 600+ municipios cafeteros |
| dim_periodo | 444 meses (1990-2026) |
| dim_enfermedad | 6 enfermedades catalogadas |
| dim_variedad_cafe | 9 variedades |
| fact_produccion | ~7263 |
| fact_clima | ~6928 |
| fact_precio | ~444 |
| fact_imagen_enfermedad | ~10846 |
| aux_evento_climatico | eventos ENSO catalogados |

Vista materializada `vw_master_municipal_mensual` consolida todo a nivel
municipio-mes para consumo de los notebooks.
