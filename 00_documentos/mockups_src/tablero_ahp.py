"""Tablero AHP + MockUps: conecta el resultado del AHP con las láminas PNG de 00_documentos.

Uso (desde cualquier carpeta):
    pip install playwright pillow numpy && python -m playwright install chromium
    python 00_documentos/mockups_src/tablero_ahp.py

Lee los juicios y calcula el AHP con ``03_scripts/ahp/ahp_cofitech.py`` (vector
propio principal), arma el HTML con el sistema de diseño de las láminas
(``sistema.py``) y guarda ``00_documentos/CofiTech_AHP_Seleccion_Mockup.png`` a 2×.
Las cifras del tablero salen siempre del script: si cambian los juicios, basta
con volver a ejecutar este archivo.
"""
from __future__ import annotations

import base64
import io
import math
import sys
from html import escape
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC.parents[1] / "03_scripts" / "ahp"))

import ahp_cofitech as ahp  # noqa: E402
from sistema import CSS, DOCS, _fuentes, _logo_b64, emblema  # noqa: E402

ARCHIVO = "CofiTech_AHP_Seleccion_Mockup.png"
ESCALA = 2

COLOR_C = {"C1": "#3D2314", "C2": "#E5A93B", "C3": "#2E6F40", "C4": "#A9B98E"}
COLOR_OP = {"Op1": "#8C6B55", "Op2": "#4A7FA8", "Op3": "#2E6F40"}
CORTO_C = {"C1": "Usabilidad y Adopción Rural", "C2": "Valor B2B", "C3": "Integración Sistémica",
           "C4": "Factibilidad y Conectividad"}
CORTO_OP = {"Op1": "Op1 · Monolítico web", "Op2": "Op2 · Móvil asistencial", "Op3": "Op3 · Dual por roles"}

# Láminas de cada alternativa: (archivo, rótulo, ancho en px CSS del tablero).
LAMINAS = {
    "Op1": [("CofiTech_mockup_A_dashboard_monolitico.png", "Lámina A · 9 pestañas técnicas en silos", 828)],
    "Op2": [("CofiTech_mockup_B_movil_asistencial.png", "Lámina B · foto + chat básico, sin finca ni cooperativa", 828)],
    "Op3": [("CofiTech_mockup_sofia.png", "Vista Caficultor · móvil (lámina de Sofía Gómez)", 1214),
            ("CofiTech_mockup_dual_b2b_agronomo.png", "Vista Agrónomo / Cooperativa · web B2B", 1214)],
}

REQUERIMIENTOS = [
    ("RF01", "Ingesta única"), ("RF02", "Diagnóstico visual"), ("RF03", "Prescripción con fuente"),
    ("RF04", "Rendimiento e ingreso"), ("RF05", "Alertas territoriales"),
    ("RNF01", "Inferencia ≤ 3 s"), ("RNF02", "Usabilidad móvil"), ("RNF03", "Degradación controlada"),
]

# Trazabilidad: ● la pantalla implementa el requerimiento (o es donde se verifica);
# ○ usa el resultado de ese requerimiento. Pasos tomados de las láminas.
TRAZA_MOVIL = [
    (1, "Hoy en mi finca", {"RF01": "●", "RF04": "●", "RNF02": "●"},
     "Finca fija arriba (municipio, altitud, área) y precio FNC del día."),
    (2, "Revisar una hoja", {"RF02": "●", "RF01": "○", "RNF01": "●", "RNF02": "●"},
     "Grad-CAM, confianza y muestreo de la finca; p95 = 0,65 s en CPU."),
    (3, "¿Qué hago?", {"RF03": "●", "RF01": "○", "RNF02": "●", "RNF03": "●"},
     "RAG con la incidencia del muestreo, fuente Cenicafé y votos Sí/No."),
    (4, "Mi cosecha e ingreso", {"RF04": "●", "RF02": "○", "RF01": "○", "RNF02": "●"},
     "Rendimiento EVA e ingreso con y sin control de la roya."),
    (5, "Vender · Compradores", {"RF04": "○"}, "Backlog (marketplace): usa el precio FNC de referencia."),
    (6, "Vender · Publicar lote", {"RF01": "○", "RF02": "○", "RF04": "○"},
     "Backlog: adjunta solos los datos de la finca y el diagnóstico."),
    (7, "Vender · Chat comprador", {}, "Backlog: negociación directa, fuera del Producto Funcional."),
]
TRAZA_WEB = [
    (1, "Mi zona de trabajo", {"RF01": "●", "RF05": "○"},
     "Barra de contexto fija; zona única; municipios con DIVIPOLA."),
    (2, "Alertas fitosanitarias", {"RF05": "●", "RF02": "○", "RNF03": "●"},
     "Mapa de calor de las fotos de campo; en vivo cada 30 s con respaldo local."),
    (3, "Indicadores municipales", {"RF04": "●", "RF02": "○", "RNF03": "●"},
     "Serie EVA con fuente y año; impacto de la roya según Cenicafé."),
    (4, "Escenarios de precio", {"RF04": "●", "RNF03": "○"},
     "Simulador Ridge validado (MAPE 2,5 %) con rango probable."),
    (5, "Consola técnica (RAG)", {"RF03": "●", "RF01": "○", "RNF03": "●"},
     "Zona e incidencia viajan a la pregunta; umbral 5 %, sin dosis."),
    (6, "Alerta epidemiológica", {"RF05": "●", "RF03": "○"},
     "Municipios priorizados y acciones de campo sin prescripción química."),
]

CSS_TABLERO = """
.tablero{width:2240px;padding:48px 48px 70px;background:var(--lienzo);display:flex;flex-direction:column;gap:36px;position:relative}
.cab{display:flex;align-items:center;gap:28px}
.cab .marca-g{display:flex;align-items:center;gap:12px;font-weight:800;font-size:26px;letter-spacing:-.02em}
.cab .titulo{flex:1}
.cab h1{margin:0;font-size:38px;font-weight:800;letter-spacing:-.025em;line-height:1.1}
.cab .bajada{margin-top:8px;font-size:16px;color:var(--suave);line-height:1.4}
.ganador{width:560px;flex:none;background:var(--cafe);color:#fff;border-radius:22px;padding:20px 24px;box-shadow:0 22px 44px -22px rgba(61,35,20,.55)}
.ganador .k{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#E8D9CC}
.ganador .n{display:flex;align-items:baseline;gap:12px;margin-top:6px}
.ganador .n b{font-size:46px;font-weight:800;letter-spacing:-.03em;line-height:1}
.ganador .n span{font-size:16px;font-weight:600;color:#F3E6D8}
.prog{height:16px;border-radius:8px;background:rgba(255,255,255,.18);overflow:hidden;margin-top:12px}
.prog>i{display:block;height:100%;border-radius:8px;background:linear-gradient(90deg,#E5A93B,#F2C66B)}
.ganador .pie-g{display:flex;justify-content:space-between;margin-top:9px;font-size:13px;color:#F3E6D8}
.seccion{display:flex;flex-direction:column;gap:18px}
.seccion>.paso{font-size:22px;height:auto}
.seccion>.paso .n{width:34px;height:34px;font-size:17px}
.seccion>.paso small{font-size:15px;font-weight:500;color:var(--suave);margin-left:4px}
.fila-alt{display:grid;grid-template-columns:1250px 1fr;gap:36px;align-items:stretch}
.col-alt{display:flex;flex-direction:column;gap:36px}
.alt{background:#fff;border:1px solid var(--linea);border-radius:20px;padding:16px 16px 18px;display:flex;flex-direction:column;gap:12px;position:relative}
.alt.win{border:2.5px solid var(--verde);box-shadow:0 26px 50px -30px rgba(46,111,64,.55)}
.alt .top{display:flex;align-items:center;gap:12px}
.alt .nom{font-size:20px;font-weight:800;letter-spacing:-.015em}
.alt .desc{font-size:13.5px;color:var(--suave);margin-top:2px}
.alt .score{margin-left:auto;text-align:right}
.alt .score b{font-size:30px;font-weight:800;letter-spacing:-.02em;display:block;line-height:1}
.alt .score span{font-size:12px;color:var(--suave);font-weight:600}
.alt .bar{height:10px;border-radius:5px;background:var(--crema);overflow:hidden}
.alt .bar>i{display:block;height:100%;border-radius:5px}
.mini{display:flex;flex-direction:column;gap:6px}
.mini .rot{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;color:var(--cafe)}
.mini img{display:block;width:100%;border-radius:12px;border:1px solid var(--linea);background:var(--lienzo)}
.nota-alt{font-size:13.5px;line-height:1.45;color:var(--tinta)}
.nota-alt b{font-weight:700}
.chip.pf{background:var(--verde);color:#fff;font-size:12px;padding:5px 11px}
.fila-sin{display:grid;grid-template-columns:1180px 1fr;gap:36px;align-items:stretch}
.tarjeta{background:#fff;border:1px solid var(--linea);border-radius:20px;padding:20px 22px;display:flex;flex-direction:column;gap:14px}
.tarjeta h3{margin:0;font-size:17px;font-weight:800;letter-spacing:-.01em}
.tarjeta .sub{font-size:13px;margin-top:0}
.ts{width:100%;border-collapse:collapse;font-size:15px;font-variant-numeric:tabular-nums}
.ts th{font-size:12px;font-weight:700;color:var(--suave);text-align:right;padding:8px 10px;border-bottom:1.5px solid var(--linea);white-space:nowrap}
.ts th:first-child,.ts td:first-child{text-align:left}
.ts td{padding:9px 10px;border-bottom:1px solid #F0E9DF;text-align:right;white-space:nowrap}
.ts td.crit{display:flex;align-items:center;gap:9px;font-weight:700}
.ts .sw{width:12px;height:12px;border-radius:3px;flex:none}
.ts .wbar{display:inline-flex;align-items:center;gap:8px;justify-content:flex-end}
.ts .wbar i{display:block;height:8px;border-radius:4px;background:var(--cafe)}
.ts tr.glob td{font-weight:800;font-size:17px;border-bottom:none;padding-top:12px}
.ts td.op3{color:var(--verde);font-weight:700}
.ts tr.glob td.op3{font-size:20px}
.ts .cr{font-size:12.5px;color:var(--verde);font-weight:700}
.meta{display:flex;flex-direction:column;gap:8px;background:var(--verde-s);border:1px solid var(--verde-b);border-radius:14px;padding:12px 14px}
.meta .fila{justify-content:space-between;font-size:14px}
.meta .prog{background:#fff;height:18px;margin-top:0;border:1px solid var(--verde-b)}
.meta .prog>i{background:linear-gradient(90deg,#2E6F40,#4E9A62)}
.ley{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;font-weight:600;color:var(--suave)}
.ley span{display:inline-flex;align-items:center;gap:6px}
.ley i{width:12px;height:12px;border-radius:3px;display:inline-block}
.dos{display:grid;grid-template-columns:300px 1fr;gap:18px;align-items:start}
.tc{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}
.tc th{font-size:11.5px;color:var(--suave);font-weight:700;text-align:right;padding:6px 8px;border-bottom:1.5px solid var(--linea)}
.tc th:first-child,.tc td:first-child{text-align:left}
.tc td{padding:6px 8px;border-bottom:1px solid #F0E9DF;text-align:right;white-space:nowrap}
.fila-tr{display:grid;grid-template-columns:1fr 1fr;gap:36px}
.tt{width:100%;border-collapse:separate;border-spacing:0;font-size:13px}
.tt th{font-size:11px;font-weight:800;color:var(--cafe);padding:6px 3px 8px;border-bottom:1.5px solid var(--linea);vertical-align:bottom;text-align:center;line-height:1.2}
.tt th small{display:block;font-weight:600;color:var(--suave);font-size:9.5px;margin-top:2px}
.tt th.izq{text-align:left}
.tt td{padding:7px 3px;border-bottom:1px solid #F0E9DF;text-align:center;vertical-align:middle}
.tt td.paso-t{text-align:left;white-space:nowrap;font-weight:700;font-size:13.5px}
.tt td.paso-t .n{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--paso);color:#fff;font-size:11px;margin-right:7px;vertical-align:1px}
.tt td.ev{text-align:left;font-size:12px;color:var(--suave);line-height:1.35}
.tt tr.backlog td{background:#FBF8F2}
.tt tr.backlog td.paso-t{color:var(--suave)}
.tt tr.cob td{border-bottom:none;font-weight:800;font-size:12px;color:var(--verde);padding-top:9px}
.tt th.rnf,.tt td.rnf{background:rgba(234,244,238,.55)}
.tt tr.backlog td.rnf{background:#F3F1E8}
.lleno{display:inline-block;width:14px;height:14px;border-radius:50%;background:var(--verde)}
.vacio{display:inline-block;width:14px;height:14px;border-radius:50%;border:2px solid var(--oro);box-sizing:border-box}
.pie-t{position:absolute;left:48px;bottom:24px;right:48px;display:flex;justify-content:space-between;font-size:12.5px;color:#9B8B7D;font-weight:500}
"""


def _f(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _miniatura(nombre: str, ancho_css: int) -> str:
    """PNG de 00_documentos reducido a 2× el ancho mostrado, incrustado como JPEG en base64."""
    from PIL import Image

    ruta = DOCS / nombre
    if not ruta.exists():
        raise FileNotFoundError(f"Falta la lámina {ruta}")
    with Image.open(ruta) as im:
        im = im.convert("RGB")
        ancho = ancho_css * ESCALA
        alto = round(im.height * ancho / im.width)
        im = im.resize((ancho, alto), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=90, optimize=True)
    return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


def _barras_apiladas(r: dict, ancho: int = 806) -> str:
    """Aporte w_j · p_ij de cada criterio al puntaje global de cada alternativa."""
    izq, der, alto_barra, sep = 168, 64, 44, 22
    escala = (ancho - izq - der) / 0.65
    filas = []
    for k, op in enumerate(r["ranking"]):
        y = 24 + k * (alto_barra + sep)
        x = izq
        segs = []
        for c, v in r["aportes"][op].items():
            w = v * escala
            segs.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{alto_barra}" fill="{COLOR_C[c]}"/>')
            if w >= 46:
                color = "#fff" if c in ("C1", "C3") else "#2C1A11"
                segs.append(f'<text x="{x + w / 2:.1f}" y="{y + alto_barra / 2 + 4.5}" text-anchor="middle" '
                            f'font-size="13" font-weight="700" fill="{color}">{_f(v)}</text>')
            x += w
        total = r["global"][op]
        filas.append(
            f'<text x="0" y="{y + alto_barra / 2 + 5}" font-size="15" font-weight="800" fill="#2C1A11">{escape(CORTO_OP[op])}</text>'
            f'<g clip-path="url(#redondeo{k})">{"".join(segs)}</g>'
            f'<clipPath id="redondeo{k}"><rect x="{izq}" y="{y}" width="{total * escala:.1f}" height="{alto_barra}" rx="9"/></clipPath>'
            f'<text x="{izq + total * escala + 10:.1f}" y="{y + alto_barra / 2 + 6}" font-size="18" font-weight="800" '
            f'fill="{COLOR_OP[op]}">{_f(total)}</text>')
    alto = 24 + 3 * (alto_barra + sep) + 14
    eje = []
    for t in (0, .1, .2, .3, .4, .5, .6):
        x = izq + t * escala
        eje.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="14" y2="{alto - 22}" stroke="#EFE7DC"/>'
                   f'<text x="{x:.1f}" y="{alto - 6}" text-anchor="middle" font-size="11" fill="#9B8B7D">{_f(t, 1)}</text>')
    return (f'<svg width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" style="display:block">'
            f'{"".join(eje)}{"".join(filas)}</svg>')


def _radar(r: dict, lado: int = 300) -> str:
    """Prioridad local de cada alternativa en cada criterio (0 a 0,8)."""
    cx = cy = lado / 2
    radio, maximo = lado / 2 - 46, 0.8
    criterios = list(ahp.NOMBRES_CRITERIOS)
    angulos = [-math.pi / 2 + i * 2 * math.pi / len(criterios) for i in range(len(criterios))]

    def punto(a, v):
        return cx + radio * v / maximo * math.cos(a), cy + radio * v / maximo * math.sin(a)

    anillos = "".join(
        f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in (punto(a, v) for a in angulos))}" fill="none" stroke="#EFE7DC"/>'
        for v in (.2, .4, .6, .8))
    ejes = "".join(f'<line x1="{cx}" y1="{cy}" x2="{punto(a, maximo)[0]:.1f}" y2="{punto(a, maximo)[1]:.1f}" stroke="#E6DCCF"/>'
                   for a in angulos)
    etiquetas = []
    for c, a in zip(criterios, angulos):
        x, y = punto(a, maximo * 1.17)
        ancla = "middle" if abs(math.cos(a)) < .3 else ("start" if math.cos(a) > 0 else "end")
        etiquetas.append(f'<text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="{ancla}" font-size="14" font-weight="800" fill="{COLOR_C[c]}" '
                         f'paint-order="stroke" stroke="#fff" stroke-width="3">{c}</text>')
    poligonos = []
    for i, op in enumerate(ahp.NOMBRES_ALTERNATIVAS):
        pts = [punto(a, r["alternativas"][c]["vector"][i]) for c, a in zip(criterios, angulos)]
        trazo = 'stroke-dasharray="5 4"' if op == "Op1" else ""
        poligonos.append(
            f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="{COLOR_OP[op]}" fill-opacity="{.22 if op == "Op3" else .10}" '
            f'stroke="{COLOR_OP[op]}" stroke-width="{3 if op == "Op3" else 2}" {trazo}/>'
            + "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{COLOR_OP[op]}"/>' for x, y in pts))
    return (f'<svg width="{lado}" height="{lado}" viewBox="0 0 {lado} {lado}" style="display:block">'
            f'{anillos}{ejes}{"".join(poligonos)}{"".join(etiquetas)}</svg>')


def _tabla_sintesis(r: dict) -> str:
    pesos = r["criterios"]["vector"]
    filas = []
    for j, c in enumerate(ahp.NOMBRES_CRITERIOS):
        p = r["alternativas"][c]
        celdas = "".join(f'<td class="{"op3" if i == 2 else ""}">{_f(v)}</td>' for i, v in enumerate(p["vector"]))
        filas.append(
            f'<tr><td class="crit"><span class="sw" style="background:{COLOR_C[c]}"></span>{c} · {escape(CORTO_C[c])}</td>'
            f'<td><span class="wbar"><i style="width:{pesos[j] * 240:.0f}px;background:{COLOR_C[c]}"></i><b>{_f(pesos[j])}</b></span></td>'
            f'<td><span class="cr">{_f(p["cr"])}</span></td>{celdas}</tr>')
    g = r["global"]
    filas.append('<tr class="glob"><td>Puntaje global Σ w<sub>j</sub>·p<sub>ij</sub></td><td>1,000</td><td></td>'
                 + "".join(f'<td class="{"op3" if op == "Op3" else ""}">{_f(g[op])}</td>' for op in ahp.NOMBRES_ALTERNATIVAS)
                 + "</tr>")
    cab = ('<tr><th>Criterio</th><th>Peso w<sub>j</sub> (vector propio)</th><th>CR matriz</th>'
           + "".join(f'<th style="color:{COLOR_OP[op]}">{escape(CORTO_OP[op])}</th>' for op in ahp.NOMBRES_ALTERNATIVAS)
           + "</tr>")
    return f'<table class="ts">{cab}{"".join(filas)}</table>'


def _tabla_consistencia(r: dict) -> str:
    filas = [("Criterios (4×4)", r["criterios"])] + [(f"{c} (3×3)", r["alternativas"][c]) for c in ahp.NOMBRES_CRITERIOS]
    cuerpo = "".join(
        f'<tr><td><b>{n}</b></td><td>{_f(p["lambda_max"], 4)}</td><td>{_f(p["ci"], 4)}</td><td>{_f(p["ri"], 2)}</td>'
        f'<td class="verde-t b7">{_f(p["cr"], 4)} ✓</td></tr>' for n, p in filas)
    return ('<table class="tc"><tr><th>Matriz</th><th>λmax</th><th>CI</th><th>RI</th><th>CR &lt; 0,10</th></tr>'
            f'{cuerpo}</table>')


def _tabla_escenarios(r: dict) -> str:
    filas = "".join(
        f'<tr><td><b>{escape(e["escenario"])}</b></td>'
        + "".join(f'<td class="{"verde-t b7" if a == e["ganador"] else ""}">{_f(v)}</td>' for a, v in e["global"].items())
        + f'<td style="color:{COLOR_OP[e["ganador"]]};font-weight:800">{e["ganador"]}</td></tr>'
        for e in r["escenarios"])
    return ('<table class="tc"><tr><th>Escenario de pesos</th>'
            + "".join(f"<th>{a}</th>" for a in ahp.NOMBRES_ALTERNATIVAS) + f"<th>Gana</th></tr>{filas}</table>")


def _tabla_traza(titulo: str, sub: str, pasos: list) -> str:
    cab = ('<tr><th class="izq">Paso del MockUp</th>'
           + "".join(f'<th class="{"rnf" if c.startswith("RNF") else ""}">{c}<small>{escape(n)}</small></th>' for c, n in REQUERIMIENTOS)
           + '<th class="izq" style="padding-left:10px">Evidencia en la pantalla</th></tr>')
    filas, cobertura = [], {c: 0 for c, _ in REQUERIMIENTOS}
    for n, nombre, marcas, evidencia in pasos:
        backlog = evidencia.startswith("Backlog")
        celdas = []
        for c, _ in REQUERIMIENTOS:
            m = marcas.get(c, "")
            if m == "●":
                cobertura[c] += 1
            simbolo = '<span class="lleno"></span>' if m == "●" else ('<span class="vacio"></span>' if m == "○" else "")
            celdas.append(f'<td class="{"rnf" if c.startswith("RNF") else ""}">{simbolo}</td>')
        filas.append(f'<tr class="{"backlog" if backlog else ""}"><td class="paso-t"><span class="n">{n}</span>{escape(nombre)}</td>'
                     f'{"".join(celdas)}<td class="ev" style="padding-left:10px">{escape(evidencia)}</td></tr>')
    pie = ('<tr class="cob"><td class="paso-t" style="color:var(--verde)">Pasos que lo implementan</td>'
           + "".join(f'<td class="{"rnf" if c.startswith("RNF") else ""}">{cobertura[c] or "—"}</td>' for c, _ in REQUERIMIENTOS)
           + "<td></td></tr>")
    return (f'<div class="tarjeta"><div><h3>{escape(titulo)}</h3><div class="sub">{escape(sub)}</div></div>'
            f'<table class="tt">{cab}{"".join(filas)}{pie}</table></div>'), cobertura


def construir() -> str:
    r = ahp.calcular()
    g = r["global"]
    ganador = r["ranking"][0]
    pct = 100 * g[ganador]
    cr_max = max([r["criterios"]["cr"]] + [r["alternativas"][c]["cr"] for c in ahp.NOMBRES_CRITERIOS])
    locales = {op: [r["alternativas"][c]["vector"][i] for c in ahp.NOMBRES_CRITERIOS]
               for i, op in enumerate(ahp.NOMBRES_ALTERNATIVAS)}

    def tarjeta(op: str, nota: str) -> str:
        minis = "".join(
            f'<div class="mini"><div class="rot">{escape(rot)}</div><img src="{_miniatura(arch, ancho)}" alt="{escape(rot)}"></div>'
            for arch, rot, ancho in LAMINAS[op])
        chip = '<span class="chip pf">✓ Producto Funcional ganador</span>' if op == ganador else ""
        return (f'<div class="alt{" win" if op == ganador else ""}"><div class="top"><div><div class="fila" style="gap:10px">'
                f'<span class="nom" style="color:{COLOR_OP[op]}">{escape(op)}</span><span class="nom">{escape(ahp.NOMBRES_ALTERNATIVAS[op])}</span>{chip}</div>'
                f'<div class="desc">{escape(nota)}</div></div>'
                f'<div class="score"><b style="color:{COLOR_OP[op]}">{_f(g[op])}</b><span>{r["ranking"].index(op) + 1}.º · {_f(100 * g[op], 1)} %</span></div></div>'
                f'<div class="bar"><i style="width:{100 * g[op]:.1f}%;background:{COLOR_OP[op]}"></i></div>{minis}</div>')

    op1 = tarjeta("Op1", f"Gana en ningún criterio · mejor en C2 ({_f(locales['Op1'][1])}) por la analítica, pero en silos")
    op2 = tarjeta("Op2", f"Gana en C4 Factibilidad ({_f(locales['Op2'][3])}) · sin Predicción ni vista para cooperativas")
    op3 = tarjeta("Op3", f"Gana en C1 ({_f(locales['Op3'][0])}), C2 ({_f(locales['Op3'][1])}) y C3 ({_f(locales['Op3'][2])}) · "
                         "una sola finca compartida por Visión, Clima, Precios y RAG")

    t_movil, cob_m = _tabla_traza("Vista Caficultor · móvil (7 pasos, lámina de Sofía Gómez)",
                                  "Pasos 5–7 (Vender) son backlog: no están en RF01–RF05 y no forman parte del Producto Funcional.",
                                  TRAZA_MOVIL)
    t_web, cob_w = _tabla_traza("Vista Agrónomo / Cooperativa · web B2B (6 pasos)",
                                "Consume los diagnósticos que envían los caficultores: aquí nace el valor B2B (C2).",
                                TRAZA_WEB)
    sin_cubrir = [c for c, _ in REQUERIMIENTOS if not (cob_m[c] + cob_w[c])]
    cobertura_txt = ("Los 8 requerimientos tienen al menos una pantalla que los implementa."
                     if not sin_cubrir else f"Sin pantalla que lo implemente: {', '.join(sin_cubrir)}.")

    sens = r["sensibilidad"]["C4"]["cambios_de_ganador"]
    sens_txt = (f"Op3 solo perdería si C4 pesara ≥ {_f(sens[0]['peso'], 2)} (hoy {_f(r['criterios']['vector'][3], 2)})"
                if sens else "Op3 gana con cualquier peso de C4")

    cuerpo = f"""
<div class="tablero" id="lienzo">
 <div class="cab">
  <div class="marca-g">{emblema(64)}CofiTech</div>
  <div class="titulo"><h1>Selección del MockUp final · AHP de Saaty</h1>
   <div class="bajada">3 alternativas × 4 criterios · vector propio principal (w<sub>j</sub>), CI = (λmax − n)/(n − 1) y CR = CI/RI &lt; 0,10 en las 5 matrices (CR máx. {_f(cr_max)}).<br>
   Cada alternativa está representada por sus láminas de MockUp en <b>00_documentos/</b>.</div></div>
  <div class="ganador"><div class="k">Producto Funcional ganador</div>
   <div class="n"><b>{_f(g[ganador])}</b><span>Op3 · Plataforma Dual Adaptativa por Roles</span></div>
   <div class="prog"><i style="width:{pct:.1f}%"></i></div>
   <div class="pie-g"><span><b>{_f(pct, 1)} %</b> del puntaje total</span><span>{_f(r["ventaja_ganador"], 2)}× la Op2 · {_f(g[ganador] / g[r["ranking"][-1]], 1)}× la Op1</span></div></div>
 </div>

 <div class="seccion"><div class="paso"><span class="n">1</span>Alternativas evaluadas <small>MockUps de 00_documentos/</small></div>
  <div class="fila-alt">{op3}<div class="col-alt">{op1}{op2}</div></div>
 </div>

 <div class="seccion"><div class="paso"><span class="n">2</span>Síntesis AHP <small>puntaje<sub>i</sub> = Σ<sub>j</sub> w<sub>j</sub> · p<sub>ij</sub> (los puntajes suman 1)</small></div>
  <div class="fila-sin">
   <div class="tarjeta"><div><h3>Pesos, prioridades locales normalizadas y puntaje global</h3>
     <div class="sub">Cada columna de prioridades es el vector propio de la matriz 3×3 de ese criterio (suma 1).</div></div>
    {_tabla_sintesis(r)}
    <div class="meta"><div class="fila"><b class="verde-t">Op3 · Plataforma Dual Adaptativa por Roles</b><b class="verde-t">{_f(pct, 1)} %</b></div>
     <div class="prog"><i style="width:{pct:.1f}%"></i></div>
     <div class="fila t mut" style="font-size:13px"><span>Op2 {_f(100 * g["Op2"], 1)} % · Op1 {_f(100 * g["Op1"], 1)} %</span><span>{escape(sens_txt)}</span></div></div>
    <div><h3 style="margin-bottom:4px">Análisis de sensibilidad</h3>
     <div class="sub" style="margin-bottom:6px">Se fija el peso de un criterio y el resto se reparte en la misma proporción. La Op3 gana en todos los escenarios.</div>
     {_tabla_escenarios(r)}</div>
   </div>
   <div class="tarjeta"><div><h3>Aporte de cada criterio al puntaje de cada alternativa (w<sub>j</sub> · p<sub>ij</sub>)</h3>
     <div class="ley">{"".join(f'<span><i style="background:{COLOR_C[c]}"></i>{c} {escape(CORTO_C[c])}</span>' for c in ahp.NOMBRES_CRITERIOS)}</div></div>
    {_barras_apiladas(r)}
    <div class="sep"></div>
    <div class="dos"><div>{_radar(r)}<div class="ley" style="justify-content:center">{"".join(f'<span><i style="background:{COLOR_OP[op]}"></i>{op}</span>' for op in ahp.NOMBRES_ALTERNATIVAS)}</div></div>
     <div><h3 style="margin-bottom:6px">Consistencia de las 5 matrices</h3>{_tabla_consistencia(r)}
      <div class="t mut" style="margin-top:10px;font-size:12.5px;line-height:1.45">Radar: prioridad local p<sub>ij</sub> de cada alternativa. La Op3 domina en C1, C2 y C3; la Op2 solo en C4, el criterio de menor peso.</div></div></div>
   </div>
  </div>
 </div>

 <div class="seccion"><div class="paso"><span class="n">3</span>Trazabilidad del MockUp ganador → requerimientos <small><span class="lleno" style="width:11px;height:11px;vertical-align:-1px"></span> implementa o se verifica en esa pantalla · <span class="vacio" style="width:11px;height:11px;vertical-align:-1px"></span> usa el resultado de ese requerimiento</small></div>
  <div class="fila-tr">{t_movil}{t_web}</div>
  <div class="t b7 verde-t" style="font-size:14px">{escape(cobertura_txt)} RF01–RF05 y RNF01–RNF03 según Especificacion_sistema_CofiTech.md.</div>
 </div>

 <div class="pie-t"><span>Cálculo: 03_scripts/ahp/ahp_cofitech.py (vector propio principal, juicios v2 del equipo CofiTech) · detalle en AHP_seleccion_mockup.md</span><span>Generado con 00_documentos/mockups_src/tablero_ahp.py</span></div>
</div>"""
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>CofiTech · AHP y MockUps</title>'
            f'<style>{_fuentes()}\n{CSS}\n{CSS_TABLERO}</style></head><body>{cuerpo}</body></html>').replace("{LOGO}", _logo_b64())


VERIFICAR = """
() => {
  const problemas = [];
  const lienzo = document.querySelector('#lienzo').getBoundingClientRect();
  document.querySelectorAll('#lienzo *').forEach(el => {
    if (el.closest('svg') && el.tagName.toLowerCase() !== 'svg') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    if (r.right > lienzo.right - 47 && !el.classList.contains('tablero'))
      problemas.push(`«${(el.textContent || el.tagName).trim().slice(0, 50)}» invade el margen derecho`);
    if (el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflow !== 'visible')
      problemas.push(`texto recortado en «${(el.textContent || '').trim().slice(0, 50)}»`);
  });
  document.querySelectorAll('img').forEach(img => { if (!img.naturalWidth) problemas.push('miniatura sin cargar'); });
  document.querySelectorAll('.tarjeta, .alt').forEach(c => {
    if (c.scrollWidth > c.clientWidth + 1) problemas.push(`tarjeta desbordada: «${c.textContent.trim().slice(0, 40)}»`);
  });
  return problemas;
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    fuente = SRC / ARCHIVO.replace(".png", ".html")
    fuente.write_text(construir(), encoding="utf-8")
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": 2240, "height": 1200}, device_scale_factor=ESCALA)
        pagina.goto(fuente.as_uri())
        pagina.evaluate("document.fonts.ready")
        pagina.wait_for_timeout(300)
        problemas = pagina.evaluate(VERIFICAR)
        salida = DOCS / ARCHIVO
        pagina.locator("#lienzo").screenshot(path=str(salida))
        navegador.close()
    print(f"{'OK' if not problemas else f'{len(problemas)} PROBLEMAS':>12}  {salida.name}")
    for problema in problemas:
        print("              ·", problema)
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
