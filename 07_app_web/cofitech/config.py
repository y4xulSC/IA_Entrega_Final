"""Ajustes de despliegue de CofiTech, leídos sin tocar el código.

Orden de búsqueda de cada ajuste (gana el primero que exista):

1. ``st.secrets`` (``07_app_web/.streamlit/secrets.toml`` o *Settings → Secrets*
   en Streamlit Community Cloud), como clave de primer nivel.
2. Variable de entorno.
3. Archivo ``.env`` de la raíz del proyecto.

Ajustes disponibles:

=========================== ============================================================
``COFITECH_MERCADO_ACTIVO``  ``1`` activa «Vender mi café» y «Oferta de café en mi zona».
                             Por defecto ``0``: en la Beta la venta directa está inactiva.
``COFITECH_CONTACTO_DATOS``  Correo o enlace para ejercer los derechos de la Ley 1581
                             (aviso de privacidad). Por defecto, el tablero de *issues*
                             del repositorio.
=========================== ============================================================
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import streamlit as st

PROYECTO: Path = Path(__file__).resolve().parents[2]

VERSION = "0.9.0"
ETAPA = "Beta"
REPOSITORIO = "https://github.com/y4xulSC/IA_Entrega_Final"
CONTACTO_POR_DEFECTO = f"{REPOSITORIO}/issues"

_VERDADERO = {"1", "true", "si", "sí", "yes", "on", "activo"}


def ajuste(nombre: str, defecto: Optional[str] = None) -> Optional[str]:
    """Valor de un ajuste según el orden del módulo; ``defecto`` si no está en ningún lado."""
    try:
        valor = st.secrets.get(nombre)
        if valor not in (None, ""):
            return str(valor)
    except Exception:            # sin secrets.toml
        pass
    if os.environ.get(nombre):
        return os.environ[nombre]
    ruta = PROYECTO / ".env"
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            clave, sep, valor = linea.strip().partition("=")
            if sep and clave.strip() == nombre:
                return valor.strip().strip('"').strip("'") or defecto
    return defecto


def ajuste_bool(nombre: str, defecto: bool = False) -> bool:
    valor = ajuste(nombre)
    return defecto if valor is None else valor.strip().lower() in _VERDADERO


def mercado_activo() -> bool:
    """¿Está habilitada la venta directa (RF09)? En la Beta, no."""
    return ajuste_bool("COFITECH_MERCADO_ACTIVO", False)


def contacto_datos() -> str:
    return ajuste("COFITECH_CONTACTO_DATOS", CONTACTO_POR_DEFECTO) or CONTACTO_POR_DEFECTO
