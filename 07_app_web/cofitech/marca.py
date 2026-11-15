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

from cofitech import config

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
    """Emblema ya decodificado en memoria.

    ``Image.open`` es perezoso: deja el archivo abierto y lo lee al primer uso.
    ``ICONO`` lo comparten todas las sesiones, y en Streamlit Community Cloud
    varias ejecutan ``st.set_page_config`` a la vez: leer el mismo archivo desde
    varios hilos rompe la lectura (``OSError: image file is truncated``) y la app
    no abre. Con ``load()`` + ``copy()`` la imagen queda en memoria, sin archivo.
    """
    try:
        with Image.open(RUTA_EMBLEMA) as imagen:
            imagen.load()
            return imagen.copy()
    except OSError:          # sin el archivo (o dañado) la app sigue con un emoji
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
.ct-beta{{display:flex;gap:10px;align-items:flex-start;background:#FDF6E2;border:1px solid #EED690;border-radius:12px;
         padding:8px 12px;margin-bottom:10px;font-size:.84rem;color:#5A4410;line-height:1.4}}
.ct-beta b.et{{flex:none;background:{COLORES['oro']};color:#2C1A11;border-radius:999px;padding:1px 9px;font-size:.72rem;
              letter-spacing:.06em;margin-top:1px}}
.ct-inactivo{{background:#fff;border:1px dashed {COLORES['suave']};border-radius:16px;padding:16px 18px;margin:6px 0 12px}}
.ct-inactivo .et{{display:inline-block;background:{COLORES['crema']};color:{COLORES['suave']};border-radius:999px;
                 padding:2px 10px;font-size:.74rem;font-weight:800;letter-spacing:.05em;text-transform:uppercase}}
.ct-inactivo .v{{font-size:1.1rem;font-weight:800;margin:8px 0 4px}}
.ct-inactivo .s{{font-size:.88rem;color:{COLORES['suave']};line-height:1.45}}
.ct-sim{{background:linear-gradient(135deg,#fff 0%,{COLORES['crema']} 100%);border:1px solid {COLORES['linea']};
  border-radius:18px;padding:16px 18px;margin:14px 0 6px}}
.ct-sim .t{{display:flex;justify-content:space-between;align-items:center;gap:8px;font-weight:800;font-size:1.15rem}}
.ct-sim .s{{font-size:.88rem;color:{COLORES['suave']};margin-top:4px;line-height:1.45}}
.ct-paso{{display:flex;align-items:center;gap:8px;font-weight:800;font-size:1rem;margin:16px 0 6px}}
.ct-paso b{{display:grid;place-items:center;width:26px;height:26px;border-radius:999px;background:{COLORES['cafe']};
  color:#fff;font-size:.8rem;flex:none}}
.ct-oferta.normal{{border:1px solid {COLORES['linea']}}}
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


def aviso_beta() -> None:
    """Franja «Beta» arriba de todas las pantallas (la dibuja el enrutador)."""
    st.markdown(
        f'<div class="ct-beta"><b class="et">{_e(config.ETAPA.upper())}</b><span>CofiTech {_e(config.VERSION)} está '
        "en fase de prueba. Los diagnósticos, proyecciones y respuestas del asistente son apoyo a la decisión: "
        "no reemplazan la visita del extensionista ni la etiqueta del producto.</span></div>",
        unsafe_allow_html=True)


def enlace(ruta: str, etiqueta: str, icono: str | None = None) -> None:
    """``st.page_link`` que no rompe la pantalla si la página no está en el menú de este rol."""
    try:
        st.page_link(ruta, label=etiqueta, icon=icono)
    except Exception:          # StreamlitAPIException: página no registrada en st.navigation
        st.markdown(f"- {etiqueta}")


def tarjeta_inactiva(titulo: str, detalle: str, etiqueta: str = "Inactivo en la Beta") -> str:
    return (f'<div class="ct-inactivo"><span class="et">{_e(etiqueta)}</span>'
            f'<div class="v">{_e(titulo)}</div><div class="s">{_e(detalle)}</div></div>')


def cabecera_simulador(titulo: str, detalle: str, etiqueta: str = "Simulación") -> str:
    return (f'<div class="ct-sim"><div class="t"><span>{_e(titulo)}</span>'
            f'<span class="ct-chip demo">{_e(etiqueta)}</span></div><div class="s">{_e(detalle)}</div></div>')


def paso(numero: int, titulo: str) -> str:
    return f'<div class="ct-paso"><b>{numero}</b><span>{_e(titulo)}</span></div>'


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
