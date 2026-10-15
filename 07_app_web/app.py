"""CofiTech · Plataforma Dual Adaptativa por Roles (MockUp final, Opción 3 del AHP).

Ejecutar:
    cd 07_app_web
    python -m streamlit run app.py

Este archivo es el enrutador: decide qué pantallas ve cada rol
(``cofitech/navegacion.py``), dibuja la barra de contexto compartido arriba de
todas y el enlace «siguiente paso» al final. Las 9 pantallas de la app
anterior se conservan: las 8 de ``pages/`` se agrupan por rol y la portada
antigua quedó como «Ficha técnica de modelos» (``vistas/ficha_tecnica.py``),
visible solo para administradores.

Utilidades:
    cofitech/contexto_finca.py  estado compartido (finca, zona, diagnóstico, riesgo, precio)
    cofitech/vision.py          CNN + Grad-CAM
    cofitech/prescripcion.py    manejo de roya por incidencia (sin dosis en el código)
    cofitech/precios_ridge.py   simulador Ridge de precio interno
    cofitech/telemetria.py      registrar_evento_uso y botones 👍/👎 (KPIs)
    cofitech/repositorio.py     persistencia (Supabase + archivo local)
    cofitech/seguridad.py       acceso de administrador
"""
from __future__ import annotations

import json
from dataclasses import asdict

import streamlit as st

from cofitech import repositorio, seguridad

from cofitech import navegacion as nav
from cofitech.contexto_finca import obtener_contexto, registrar_diagnostico, reiniciar_muestreo

# 1.46: st.set_page_config puede llamarse en el enrutador y en cada pantalla.
# 1.49: st.dataframe(width="stretch"), que usa pages/4_Enfermedades.py.
VERSION_MINIMA: tuple[int, int] = (1, 49)

# Panel de depuración: muestra el estado compartido y permite simular un
# diagnóstico sin subir una foto (útil para ensayar la sustentación sin el
# modelo CNN). Solo lo ven los administradores; en False no lo ve nadie.
MODO_ESQUELETO: bool = True


def _version_streamlit() -> tuple[int, int]:
    mayor, menor, *_ = st.__version__.split(".")
    return int(mayor), int(menor)


def _panel_esqueleto() -> None:
    with st.sidebar.expander("Depuración · estado compartido"):
        st.caption(f"Supabase: {repositorio.db_client.estado()}")
        if st.button("Simular hoja con roya", use_container_width=True):
            registrar_diagnostico("Roya", 0.87, "simulado", es_demo=True)
            st.rerun()
        if st.button("Simular hoja sana", use_container_width=True):
            registrar_diagnostico("Sano", 0.93, "simulado", es_demo=True)
            st.rerun()
        if st.button("Reiniciar muestreo", use_container_width=True):
            reiniciar_muestreo()
            st.rerun()
        st.json(json.loads(json.dumps(asdict(obtener_contexto()), default=str)), expanded=1)


st.set_page_config(page_title="CofiTech", page_icon="☕", layout="wide")

if _version_streamlit() < VERSION_MINIMA:
    st.error(
        f"CofiTech necesita Streamlit {VERSION_MINIMA[0]}.{VERSION_MINIMA[1]} o superior "
        f"(instalado: {st.__version__}). Ejecuta: pip install -U streamlit"
    )
    st.stop()

ctx = obtener_contexto()

if not ctx.listo:
    # Sin rol o sin datos mínimos: la única pantalla posible es el ingreso.
    st.navigation([st.Page("vistas/acceso.py", title="Ingreso")], position="hidden").run()
    st.stop()

secciones, indice = nav.construir_paginas(ctx.rol, admin=seguridad.es_admin())
pagina = st.navigation(secciones, expanded=True)   # con más de 10 páginas Streamlit oculta el resto

nav.pie_lateral(ctx)
if MODO_ESQUELETO and seguridad.es_admin():
    _panel_esqueleto()

nav.barra_contexto(ctx)                      # arriba de TODAS las pantallas
try:
    pagina.run()                             # la pantalla elegida (original o nueva)
finally:
    # También cuando la pantalla termina con st.stop() (p. ej. por falta de datos).
    nav.siguiente_paso(ctx, pagina, indice)  # hacia dónde sigue el recorrido
