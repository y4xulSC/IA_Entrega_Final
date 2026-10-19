# Láminas de MockUp de CofiTech

Generador de las láminas PNG de `00_documentos/` con el mismo sistema de diseño de
`CofiTech_mockup_sofia.png`: lienzo pergamino, pasos numerados, marcos de teléfono
(Caficultor) y de navegador (Agrónomo / Cooperativa), badges dorados de trazabilidad,
flechas verdes de transición y tarjetas de COMENTARIOS ligadas a los RF.

| Archivo | Qué contiene |
|---|---|
| `sistema.py` | Tokens de diseño, marcos, badges, flechas, tarjetas y logo embebido en base64 |
| `graficos.py` | Ilustraciones SVG: hoja con roya, Grad-CAM, líneas, mapa de calor |
| `laminas.py` | Contenido de cada lámina (MockUp A, MockUp B y vista web B2B del MockUp C) |
| `generar_mockups.py` | Escribe el HTML de cada lámina aquí y el PNG en `00_documentos/` a 2× |
| `tablero_ahp.py` | Tablero `CofiTech_AHP_Seleccion_Mockup.png`: miniaturas de las láminas, síntesis AHP, aportes por criterio y trazabilidad RF/RNF. Las cifras salen de `03_scripts/ahp/ahp_cofitech.py` |
| `fonts/` | Inter (SIL Open Font License), embebida para que el render sea igual en cualquier equipo |

## Uso

```bash
pip install playwright
python -m playwright install chromium
python 00_documentos/mockups_src/generar_mockups.py
pip install pillow numpy   # además, para el tablero AHP
python 00_documentos/mockups_src/tablero_ahp.py
```

El script revisa que ningún texto se salga de su pantalla ni quede recortado y
termina con error si encuentra alguno. Para cambiar textos o pantallas, edite
`laminas.py`; los colores y medidas están en `CSS` dentro de `sistema.py`.
