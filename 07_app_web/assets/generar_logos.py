"""Genera los recortes del logo oficial que usa la app.

Uso:
    python 07_app_web/assets/generar_logos.py

Lee ``00_documentos/logo_cofitech.jpeg`` (1254 × 1254 px, fondo crema) y escribe
en esta carpeta:

* ``emblema_cofitech.png``  solo el emblema, cuadrado y con fondo transparente
  (ícono de la pestaña del navegador y de la barra lateral colapsada).
* ``logo_horizontal.png``   emblema + palabra «CofiTech» del logo, en una línea
  (cabecera de la barra lateral con ``st.logo``).
* ``logo_completo.png``     el logo completo con el lema y fondo transparente (pantalla de ingreso).
* ``logo_cofitech.jpeg``    copia del original, por si se necesita con su fondo.

No redibuja nada: recorta el archivo oficial y vuelve transparente el fondo.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
from PIL import Image

AQUI = Path(__file__).resolve().parent
ORIGEN = AQUI.parents[1] / "00_documentos" / "logo_cofitech.jpeg"

# Cajas (izquierda, arriba, derecha, abajo) medidas sobre el JPEG oficial.
CAJA_EMBLEMA = (291, 199, 946, 723)
CAJA_PALABRA = (162, 749, 1103, 937)
UMBRAL_FONDO = 60          # distancia de color (suma RGB) a partir de la cual el píxel es logo


def _sin_fondo(imagen: Image.Image) -> Image.Image:
    """Fondo crema → transparente, con borde suave para que no quede un halo."""
    rgb = np.asarray(imagen.convert("RGB")).astype(np.int32)
    fondo = rgb[2, 2]
    distancia = np.abs(rgb - fondo).sum(axis=2)
    alfa = np.clip(distancia * 255 / UMBRAL_FONDO, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb.astype(np.uint8), alfa]), "RGBA")


def _cuadrado(imagen: Image.Image, margen: float = 0.06) -> Image.Image:
    lado = int(max(imagen.size) * (1 + 2 * margen))
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    lienzo.paste(imagen, ((lado - imagen.width) // 2, (lado - imagen.height) // 2), imagen)
    return lienzo


def main() -> None:
    logo = Image.open(ORIGEN)
    emblema = _sin_fondo(logo.crop(CAJA_EMBLEMA))
    palabra = _sin_fondo(logo.crop(CAJA_PALABRA))

    _cuadrado(emblema).resize((256, 256), Image.LANCZOS).save(AQUI / "emblema_cofitech.png", optimize=True)

    alto = 240
    em = emblema.resize((round(emblema.width * alto / emblema.height), alto), Image.LANCZOS)
    alto_palabra = round(alto * 0.56)
    pa = palabra.resize((round(palabra.width * alto_palabra / palabra.height), alto_palabra), Image.LANCZOS)
    separacion = 24
    horizontal = Image.new("RGBA", (em.width + separacion + pa.width, alto), (0, 0, 0, 0))
    horizontal.paste(em, (0, 0), em)
    horizontal.paste(pa, (em.width + separacion, (alto - alto_palabra) // 2 + 6), pa)
    horizontal.save(AQUI / "logo_horizontal.png", optimize=True)

    completo = _sin_fondo(logo.crop((120, 170, 1134, 1050)))
    completo.resize((completo.width // 2, completo.height // 2), Image.LANCZOS).save(AQUI / "logo_completo.png",
                                                                                       optimize=True)
    shutil.copyfile(ORIGEN, AQUI / "logo_cofitech.jpeg")
    print("Listo:", ", ".join(p.name for p in sorted(AQUI.glob("*.png"))), "+ logo_cofitech.jpeg")


if __name__ == "__main__":
    main()
