"""Ilustraciones SVG de las láminas: hoja con roya, Grad-CAM, líneas, mapa de calor y mapa de zona."""
from __future__ import annotations


def hoja(ancho: int = 268, alto: int = 150, roya: bool = True, gradcam: bool = False, uid: str = "h") -> str:
    """Hoja de café estilizada; con manchas de roya y, si se pide, el mapa de atención encima."""
    manchas = ""
    if roya:
        puntos = [(118, 62, 9), (150, 78, 7), (96, 84, 6), (176, 58, 6), (138, 98, 8), (188, 90, 5), (110, 44, 5),
                  (162, 104, 5), (82, 66, 4), (204, 72, 4)]
        manchas = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#roya{uid})"/>' for x, y, r in puntos)
    calor = ""
    if gradcam:
        calor = (f'<g clip-path="url(#clip{uid})" opacity=".78"><rect width="268" height="150" fill="#2B3FA8"/>'
                 f'<ellipse cx="140" cy="76" rx="92" ry="44" fill="url(#cam1{uid})"/>'
                 f'<ellipse cx="124" cy="70" rx="44" ry="26" fill="url(#cam2{uid})"/></g>')
    return f'''<svg width="{ancho}" height="{alto}" viewBox="0 0 268 150" style="display:block">
<defs>
 <linearGradient id="lam{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7FA255"/><stop offset=".55" stop-color="#5C8A3E"/><stop offset="1" stop-color="#3F6B2E"/></linearGradient>
 <radialGradient id="roya{uid}"><stop offset="0" stop-color="#E9862B"/><stop offset=".6" stop-color="#E7A93C"/><stop offset="1" stop-color="#C9C25A" stop-opacity="0"/></radialGradient>
 <radialGradient id="cam1{uid}"><stop offset="0" stop-color="#F2E14A"/><stop offset=".45" stop-color="#4FC98F"/><stop offset="1" stop-color="#2B3FA8" stop-opacity="0"/></radialGradient>
 <radialGradient id="cam2{uid}"><stop offset="0" stop-color="#E5352B"/><stop offset=".55" stop-color="#F29A2E"/><stop offset="1" stop-color="#F2E14A" stop-opacity="0"/></radialGradient>
 <clipPath id="clip{uid}"><path d="M14 80 C 50 18, 170 8, 254 70 C 180 128, 70 138, 14 80 Z"/></clipPath>
</defs>
<path d="M14 80 C 50 18, 170 8, 254 70 C 180 128, 70 138, 14 80 Z" fill="url(#lam{uid})"/>
<path d="M14 80 C 90 74, 170 72, 254 70" stroke="#C9DDA0" stroke-width="2" fill="none"/>
<g stroke="#9CC07A" stroke-width="1.2" fill="none" opacity=".8">
 <path d="M60 78 C 70 60, 85 48, 100 40"/><path d="M100 76 C 112 56, 126 44, 140 34"/><path d="M140 74 C 152 56, 166 46, 182 40"/>
 <path d="M60 79 C 72 96, 86 106, 100 112"/><path d="M100 77 C 114 96, 128 106, 146 112"/><path d="M146 74 C 160 92, 172 100, 190 104"/>
</g>
{manchas}{calor}
</svg>'''


def linea(series: list[tuple[list[float], str, bool]], ancho: int, alto: int, etiquetas: list[str],
          minimo: float, maximo: float, paso_y: float, formato=lambda v: f"{v:.1f}".replace(".", ",")) -> str:
    """Gráfico de líneas simple. ``series`` = [(valores, color, punteada)]."""
    izq, der, arr, aba = 30, 14, 6, 16
    w, h = ancho - izq - der, alto - arr - aba
    n = len(etiquetas)

    def x(i): return izq + w * i / (n - 1)
    def y(v): return arr + h * (1 - (v - minimo) / (maximo - minimo))

    rejilla, v = [], minimo
    while v <= maximo + 1e-9:
        rejilla.append(f'<line x1="{izq}" x2="{ancho - der}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#EFE7DC"/>'
                       f'<text x="{izq - 5}" y="{y(v) + 3:.1f}" text-anchor="end" font-size="8" fill="#9B8B7D">{formato(v)}</text>')
        v += paso_y
    ejes = "".join(f'<text x="{x(i):.1f}" y="{alto - 3}" text-anchor="middle" font-size="8" fill="#9B8B7D">{e}</text>'
                   for i, e in enumerate(etiquetas) if e)
    trazos = []
    for valores, color, punteada in series:
        d = " ".join(f"{'M' if i == 0 else 'L'}{x(i):.1f} {y(val):.1f}" for i, val in enumerate(valores) if val is not None)
        guiones = 'stroke-dasharray="4 3"' if punteada else ""
        trazos.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" '
                      f'stroke-linecap="round" {guiones}/>')
    return (f'<svg width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" style="display:block">'
            f'{"".join(rejilla)}{ejes}{"".join(trazos)}</svg>')


def mapa_calor(ancho: int, alto: int, puntos: list[tuple[str, float, float, float]], uid: str = "m") -> str:
    """Mapa estilizado de la zona (no cartográfico) con calor por municipio: (nombre, x, y, intensidad 0-1)."""
    capas, marcas = [], []
    for nombre, x, y, k in puntos:
        r = 18 + 30 * k
        capas.append(f'<circle cx="{x}" cy="{y}" r="{r:.0f}" fill="url(#calor{uid})" opacity="{0.35 + 0.6 * k:.2f}"/>')
        color = "#B5462F" if k >= .6 else ("#D98A1E" if k >= .3 else "#2E6F40")
        marcas.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{color}" stroke="#fff" stroke-width="1.5"/>'
                      f'<text x="{x + 7}" y="{y + 3.5}" font-size="9" font-weight="700" fill="#2C1A11" '
                      f'paint-order="stroke" stroke="#F6F1E6" stroke-width="3">{nombre}</text>')
    return f'''<svg width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" style="display:block;border-radius:10px">
<defs><radialGradient id="calor{uid}"><stop offset="0" stop-color="#D9381E"/><stop offset=".45" stop-color="#F0A23A" stop-opacity=".8"/><stop offset="1" stop-color="#F5D35A" stop-opacity="0"/></radialGradient></defs>
<rect width="{ancho}" height="{alto}" fill="#EEF0E2"/>
<g fill="none" stroke="#D7DCC2" stroke-width="1.2">
 <path d="M0 {alto * .30:.0f} C {ancho * .25:.0f} {alto * .18:.0f}, {ancho * .55:.0f} {alto * .42:.0f}, {ancho} {alto * .28:.0f}"/>
 <path d="M0 {alto * .55:.0f} C {ancho * .3:.0f} {alto * .44:.0f}, {ancho * .6:.0f} {alto * .70:.0f}, {ancho} {alto * .52:.0f}"/>
 <path d="M0 {alto * .80:.0f} C {ancho * .35:.0f} {alto * .68:.0f}, {ancho * .65:.0f} {alto * .92:.0f}, {ancho} {alto * .76:.0f}"/>
</g>
<path d="M{ancho * .08:.0f} 0 C {ancho * .2:.0f} {alto * .35:.0f}, {ancho * .12:.0f} {alto * .7:.0f}, {ancho * .24:.0f} {alto}" stroke="#B9D3E3" stroke-width="3" fill="none"/>
<path d="M{ancho * .5:.0f} {alto * .05:.0f} L{ancho * .93:.0f} {alto * .12:.0f} L{ancho * .9:.0f} {alto * .9:.0f} L{ancho * .42:.0f} {alto * .95:.0f} L{ancho * .3:.0f} {alto * .5:.0f} Z" fill="none" stroke="#9FAF86" stroke-width="1.3" stroke-dasharray="5 4"/>
{"".join(capas)}{"".join(marcas)}
</svg>'''
