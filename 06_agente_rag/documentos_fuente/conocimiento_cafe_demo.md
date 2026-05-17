# Conocimiento base · Sistema IA Café Colombia

## El Niño y rendimiento

En el contexto del análisis realizado en la 2da entrega del proyecto,
se observó que el fenómeno El Niño reduce el rendimiento del café en
aproximadamente **24%** respecto a la fase Neutro (de 1.037 ton/ha a
0.788 ton/ha), con diferencias estadísticamente significativas según
el test de Kruskal-Wallis (p < 0.05).

La Niña tiene un efecto menor: reduce el rendimiento en aproximadamente
12% (a 0.910 ton/ha).

Esto se debe a que El Niño causa déficit hídrico y aumento de
temperatura — condiciones desfavorables para el café arábica que prefiere
1500-2000 mm de precipitación anual y temperaturas entre 18-22°C.

## Roya del café

La Roya (Hemileia vastatrix) es la enfermedad más importante del café
en Colombia. Síntomas:
- Manchas amarillentas en envés de hojas
- Polvillo color naranja-amarillo
- Caída prematura de hojas

Variedades resistentes a la roya en Colombia: Castillo, Colombia,
Cenicafé 1, Tabi. Variedades susceptibles: Caturra, Bourbon, Típica.

Sin manejo, la roya puede causar pérdidas del 40% de la producción.

## Departamentos cafeteros principales

1. **Huila** — productor #1 desde 2010 (~150K ton/año)
2. **Antioquia** — segundo productor (~110K ton/año)
3. **Nariño** — café especial alta altitud (~70K ton/año)
4. **Tolima**, **Caldas**, **Quindío**, **Risaralda**, **Cauca** —
   forman el Eje Cafetero clásico.

## Precio interno (FNC) y precio externo (ICO)

El precio FNC para carga de 125 kg sigue de cerca al precio ICO Composite
en USD/lb con correlación r=0.97 (modelado en NB05 con Ridge regression
que alcanza R²=0.945, MAPE=4.3%).

El surge 2024-2025 (precio interno superando 3,200,000 COP) se explica por:
1. Sequía en Brasil (super productor mundial) durante 2024
2. Devaluación del peso colombiano (TRM superando 4,200 COP/USD)
3. Aumento de la demanda mundial post-pandemia

## Modelos del sistema

Notebook | Modelo | Métrica | Estado
--- | --- | --- | ---
NB02 | Stacking RF+XGB+LGB | R²=0.067 (departamental) | mejorado en NB09
NB05 | Ridge precio | R²=0.945 | excelente
NB06 | BiGRU forecasting | R²=−2.12 | mejorado en NB10
NB03 | EfficientNetB0 CNN | Acc=48.9% | mejorado en NB08

NB07-NB12 son la entrega final con datos ampliados.
