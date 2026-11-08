"""Identidad visual de CofiTech: logo oficial y piezas del MockUp ganador.

* ``ICONO``: emblema del logo para la pestaña del navegador (``page_icon``).
* ``aplicar()``: logo en la barra lateral (``st.logo``) y estilos de las
  tarjetas. Lo llama el enrutador (``app.py``) en cada ejecución.
* ``tarjeta_*``: tarjetas HTML con el sistema de diseño de la lámina de Sofía
  (``00_documentos/CofiTech_mockup_sofia.png``).

Los colores son los tokens de ``00_documentos/mockups_src/sistema.py``; el
tema general de Streamlit está en ``.streamlit/config.toml``.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st
from PIL import Image

ASSETS: Path = Path(__file__).resolve().parents[1] / "assets"
RUTA_EMBLEMA: Path = ASSETS / "emblema_cofitech.png"
RUTA_HORIZONTAL: Path = ASSETS / "logo_horizontal.png"
RUTA_LOGO: Path = ASSETS / "logo_completo.png"

LEMA = "Datos que impulsan el futuro del café"

COLORES = {
    "lienzo": "#F3EFE6", "tinta": "#2C1A11", "cafe": "#6B4A35", "suave": "#7A685B", "linea": "#E6DCCF",
    "crema": "#F1EBE1", "verde": "#2E6F40", "verde_s": "#E4F1E8", "verde_b": "#B8DEC6", "oro": "#E5A93B",
    "rojo": "#B5462F", "rojo_s": "#F8E3DD", "ambar": "#B7790F", "ambar_s": "#FBEFD3",
}


def _icono() -> Image.Image | str:
    try:
        return Image.open(RUTA_EMBLEMA)
    except OSError:          # sin el archivo la app sigue con un emoji
        return "☕"


ICONO = _icono()

_CSS = f"""
<style>
.ct-tarjeta{{background:#fff;border:1px solid {COLORES['linea']};border-radius:16px;padding:14px 16px;margin-bottom:10px}}
.ct-tarjeta .et{{font-size:.82rem;color:{COLORES['suave']};line-height:1.3}}
.ct-tarjeta .v{{font-size:1.25rem;font-weight:800;letter-spacing:-.01em;line-height:1.2;margin-top:2px}}
.ct-tarjeta .s{{font-size:.82rem;color:{COLORES['suave']};margin-top:2px}}
.ct-precio{{background:{COLORES['cafe']};color:#fff;border-radius:18px;padding:16px 18px;margin-bottom:10px}}
.ct-precio .et{{font-size:.85rem;color:#E8D9CC;display:flex;justify-content:space-between;align-items:center;gap:8px}}
.ct-precio .v{{font-size:2rem;font-weight:800;letter-spacing:-.02em;line-height:1.1;margin:4px 0 2px}}
.ct-precio .s{{font-size:.82rem;color:#E8D9CC}}
.ct-chip{{display:inline-block;border-radius:999px;padding:2px 10px;font-size:.76rem;font-weight:700;white-space:nowrap;
         background:{COLORES['crema']};color:{COLORES['cafe']}}}
.ct-precio .ct-chip{{background:rgba(255,255,255,.16);color:#fff}}
.ct-chip.verde{{background:{COLORES['verde_s']};color:{COLORES['verde']}}}
.ct-chip.rojo{{background:{COLORES['rojo_s']};color:{COLORES['rojo']}}}
.ct-chip.ambar{{background:{COLORES['ambar_s']};color:{COLORES['ambar']}}}
.ct-chip.demo{{background:#FDF6E2;color:#8A6510;border:1px solid #EED690}}
.ct-banner{{background:{COLORES['verde_s']};border:1px solid {COLORES['verde_b']};border-radius:16px;padding:12px 16px;
           color:{COLORES['verde']};margin-bottom:6px}}
.ct-banner b{{font-size:1rem}}
.ct-banner .s{{color:{COLORES['suave']};font-size:.82rem}}
.ct-comprador{{display:flex;gap:12px;align-items:center}}
.ct-avatar{{width:44px;height:44px;border-radius:12px;display:grid;place-items:center;color:#fff;font-weight:800;flex:none}}
.ct-comprador .n{{font-weight:800;font-size:1rem;line-height:1.2}}
.ct-comprador .s{{font-size:.8rem;color:{COLORES['suave']}}}
.ct-oferta{{border:2px solid {COLORES['verde']};border-radius:16px;padding:12px 14px;background:#fff;margin:6px 0}}
.ct-oferta .fila{{display:flex;justify-content:space-between;font-size:.9rem;margin-top:3px}}
.ct-oferta .fila b{{font-variant-numeric:tabular-nums}}
.ct-burbuja{{border-radius:14px;padding:8px 12px;margin:4px 0;max-width:88%;font-size:.92rem;line-height:1.4}}
.ct-burbuja.yo{{margin-left:auto;background:{COLORES['cafe']};color:#fff;border-bottom-right-radius:4px}}
.ct-burbuja.ellos{{background:#fff;border:1px solid {COLORES['linea']};border-bottom-left-radius:4px}}
.ct-burbuja.sistema{{margin:6px auto;background:{COLORES['crema']};color:{COLORES['cafe']};font-size:.82rem;text-align:center}}
.ct-burbuja .meta{{display:block;font-size:.7rem;opacity:.7;margin-top:2px}}
</style>
"""


def aplicar() -> None:
    """Logo en la barra lateral y estilos de las tarjetas (una vez por ejecución)."""
    if RUTA_HORIZONTAL.exists() and RUTA_EMBLEMA.exists():
        st.logo(str(RUTA_HORIZONTAL), icon_image=str(RUTA_EMBLEMA), size="large")
    st.markdown(_CSS, unsafe_allow_html=True)


def pct(valor: float, signo: bool = True) -> str:
    """Porcentaje con coma decimal: ``+5,7 %``."""
    return (f"{valor:+.1f}" if signo else f"{valor:.1f}").replace(".", ",") + " %"


def _e(texto: object) -> str:
    return escape(str(texto))


def tarjeta_precio(etiqueta: str, valor: str, detalle: str, chip: str = "") -> str:
    chip_html = f'<span class="ct-chip">{_e(chip)}</span>' if chip else ""
    return (f'<div class="ct-precio"><div class="et"><span>{_e(etiqueta)}</span>{chip_html}</div>'
            f'<div class="v">{_e(valor)}</div><div class="s">{_e(detalle)}</div></div>')


def tarjeta(etiqueta: str, valor: str, detalle: str = "", color: str = "") -> str:
    estilo = f' style="color:{COLORES[color]}"' if color in COLORES else ""
    return (f'<div class="ct-tarjeta"><div class="et">{_e(etiqueta)}</div><div class="v"{estilo}>{_e(valor)}</div>'
            + (f'<div class="s">{_e(detalle)}</div>' if detalle else "") + "</div>")


def banner(titulo: str, detalle: str) -> str:
    return f'<div class="ct-banner"><b>{_e(titulo)}</b><div class="s">{_e(detalle)}</div></div>'


def chip(texto: str, tono: str = "") -> str:
    return f'<span class="ct-chip {_e(tono)}">{_e(texto)}</span>'


def avatar(iniciales: str, color: str) -> str:
    return f'<div class="ct-avatar" style="background:{_e(color)}">{_e(iniciales)}</div>'


def burbuja(texto: str, quien: str, meta: str = "") -> str:
    """Mensaje del chat: ``quien`` = ``"yo"`` | ``"ellos"`` | ``"sistema"``."""
    meta_html = f'<span class="meta">{_e(meta)}</span>' if meta else ""
    return f'<div class="ct-burbuja {_e(quien)}">{_e(texto)}{meta_html}</div>'
