# Eventos ENSO históricos y su impacto en el café colombiano

Cronología de los principales eventos El Niño y La Niña desde 1980 con
su efecto documentado en la caficultura colombiana.

## El Niño Muy Fuerte 1982-1983

- ONI pico: +2.2
- Duración: abril 1982 - junio 1983
- Efecto Colombia: sequía prolongada, defoliación severa, caída de
  producción nacional ~30%.
- Lección: el primer evento moderno bien documentado.

## La Niña Fuerte 1988-1989

- ONI pico: −1.9
- Duración: mayo 1988 - mayo 1989
- Efecto: lluvias extremas, brotes de gotera y antracnosis,
  pérdida de calidad de taza por hongos.

## El Niño Muy Fuerte 1997-1998

- ONI pico: +2.4
- Duración: mayo 1997 - mayo 1998
- Efecto Colombia: sequía severa, incendios en zonas cafeteras,
  reducción de producción ~25%. Precios internacionales aumentaron
  por menor oferta global.

## La Niña Fuerte 2010-2011

- ONI pico: −1.7
- Duración: junio 2010 - abril 2011
- Efecto Colombia: olas invernales, inundaciones, brote masivo de roya
  conocido como "epidemia de roya 2008-2011" que devastó variedades
  susceptibles (Caturra, Bourbon). Llevó a renovación masiva con
  Castillo.

## El Niño Muy Fuerte 2015-2016

- ONI pico: +2.6 (uno de los más fuertes del registro)
- Duración: abril 2015 - mayo 2016
- Efecto Colombia: sequía intensa, estrés hídrico generalizado,
  reducción de rendimiento ~20-25%, brotes de roya por estrés del
  cafetal. Precios FNC subieron significativamente por menor oferta.

## La Niña Triple-Dip 2020-2023

- Duración: agosto 2020 - febrero 2023
- ONI pico: −1.4
- Característica: tres temporadas consecutivas de La Niña, evento
  inusual en el registro climático.
- Efecto Colombia: lluvias persistentes, alta incidencia de gotera y
  antracnosis, problemas de secado, defoliación. Impacto significativo
  en calidad y volumen.

## El Niño Fuerte 2023-2024

- ONI pico: +2.0
- Duración: abril 2023 - mayo 2024
- Efecto Colombia: sequía moderada, contribuyó al **surge de precio
  2024-2025** detectado por el modelo VAE del proyecto. Combinado con
  sequía en Brasil y devaluación COP/USD, llevó el precio interno FNC
  a niveles históricos (>3.2 millones COP/carga).

## Patrones observados

**Frecuencia:** un evento ENSO importante ocurre cada 3-7 años.
**Predictibilidad:** NOAA tiene buena capacidad de pronóstico 3-6
meses adelante. Pronósticos a 12 meses tienen mayor incertidumbre.

**Impacto cuantificado en el sistema:**
- El Niño reduce rendimiento del café colombiano ~24% (test Kruskal-Wallis
  significativo p < 0.05, datos 1990-2024).
- La Niña reduce rendimiento ~12% (por enfermedades, no por estrés
  hídrico).

## Cómo aprovechar la información ENSO

**Si NOAA pronostica El Niño en los próximos 6-12 meses:**
1. Reforzar sombrío para reducir estrés térmico del cafetal
2. Fertilización foliar para reforzar resistencia
3. Si tiene posibilidad de riego, prepararlo
4. Vigilar roya intensificada por estrés
5. Considerar adelantar parte de la cosecha
6. Anticipar que el precio FNC tenderá a subir → buena posición vendedora

**Si NOAA pronostica La Niña:**
1. Revisar y mejorar drenajes
2. Podas sanitarias para mejorar aireación del cafetal
3. Aplicar fungicidas cúpricos preventivos (gotera, antracnosis)
4. Construir o reparar marquesinas de secado
5. Anticipar problemas de calidad por humedad excesiva
6. Diversificar momentos de cosecha para evitar pérdidas masivas

## Fuente de datos

Datos del índice ONI: NOAA Climate Prediction Center
https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php

Catálogo de eventos: tabla `cafe.aux_evento_climatico` en la BD del
sistema, alimentada desde `enso_validado.csv`.
