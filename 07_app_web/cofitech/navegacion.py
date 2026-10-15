"""Arquitectura de navegación por rol.

Tres piezas hacen que las pantallas se lean como un solo producto:

1. ``MENU``: qué pantallas ve cada rol y en qué sección. Las 9 pantallas
   originales siguen existiendo; aquí solo se decide dónde aparecen.
2. ``barra_contexto``: franja fija arriba de TODAS las pantallas con la finca
   (o zona), el clima, el precio y el último diagnóstico.
3. ``siguiente_paso``: enlace al final de cada pantalla hacia el paso que
   sigue en el recorrido del rol, con el contexto ya cargado.

El enrutador (``app.py``) dibuja 2 y 3 alrededor de la pantalla, así
que una pantalla nueva las hereda sin escribir una línea.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import streamlit as st

from cofitech import repositorio, seguridad
from cofitech.datos import normalizar
from cofitech.contexto_finca import (
    ContextoFinca, Rol, actualizar_foco, catalogo_municipios, definir_rol, mes_anio,
)

if TYPE_CHECKING:
    from streamlit.navigation.page import StreamlitPage


@dataclass(frozen=True)
class Pantalla:
    clave: str        # identificador estable; también es la ruta en la URL
    archivo: str      # relativo a 07_app_web/
    titulo: str
    icono: str
    seccion: str
    inicio: bool = False


# ───────────────────── Qué ve cada rol (y en qué orden) ─────────────────────
MENU: dict[Rol, list[Pantalla]] = {
    Rol.CAFICULTOR: [
        Pantalla("inicio", "pages/8_Asesor_Caficultor.py", "Hoy en mi finca", ":material/home:", "Mi finca", inicio=True),
        Pantalla("diagnostico", "pages/4_Enfermedades.py", "Revisar una hoja", ":material/photo_camera:", "Mi finca"),
        Pantalla("que_hago", "pages/5_Chatbot.py", "¿Qué hago?", ":material/forum:", "Mi finca"),
        Pantalla("cosecha", "pages/2_Rendimiento.py", "Mi cosecha e ingreso", ":material/agriculture:", "Mi finca"),
        Pantalla("venta", "pages/7_Calidad_SCA.py", "¿A cómo vendo?", ":material/sell:", "Mi finca"),
        Pantalla("mapa", "pages/6_Mapa.py", "Mi zona en el mapa", ":material/map:", "Más"),
        Pantalla("perfil", "vistas/acceso.py", "Datos de mi finca", ":material/edit:", "Más"),
    ],
    Rol.AGRONOMO: [
        Pantalla("mapa", "pages/6_Mapa.py", "Mapa cafetero", ":material/map:", "Panorama regional", inicio=True),
        Pantalla("dashboard", "pages/1_Dashboard.py", "Indicadores municipales", ":material/monitoring:", "Panorama regional"),
        Pantalla("alertas", "vistas/alertas_fitosanitarias.py", "Alertas fitosanitarias", ":material/warning:", "Sanidad"),
        Pantalla("diagnostico", "pages/4_Enfermedades.py", "Diagnóstico por imagen", ":material/photo_camera:", "Sanidad"),
        Pantalla("rendimiento", "pages/2_Rendimiento.py", "Rendimiento municipal", ":material/agriculture:", "Modelos"),
        Pantalla("precios", "pages/3_Precios.py", "Escenarios de precios", ":material/show_chart:", "Modelos"),
        Pantalla("anomalias", "vistas/anomalias_precios.py", "Detección de anomalías", ":material/troubleshoot:", "Modelos"),
        Pantalla("sca", "pages/7_Calidad_SCA.py", "Primas por calidad (SCA)", ":material/sell:", "Modelos"),
        Pantalla("rag", "pages/5_Chatbot.py", "Consola técnica (RAG)", ":material/forum:", "Consulta"),
        Pantalla("calendario", "pages/8_Asesor_Caficultor.py", "Calendario del caficultor", ":material/calendar_month:", "Consulta"),
        Pantalla("perfil", "vistas/acceso.py", "Mi zona de trabajo", ":material/edit:", "Mi cuenta"),
    ],
}

# Solo para administradores del sistema (``seguridad.es_admin()``), con cualquiera
# de los dos roles. Si no se agregan a ``st.navigation`` tampoco se puede llegar
# a ellas escribiendo la URL.
ADMINISTRACION: list[Pantalla] = [
    Pantalla("telemetria", "vistas/telemetria.py", "Telemetría y KPIs", ":material/analytics:", "Administración"),
    Pantalla("ficha", "vistas/ficha_tecnica.py", "Ficha técnica de modelos", ":material/info:", "Administración"),
]

# Recorrido principal de cada rol: de cada pantalla sale un enlace a la siguiente.
FLUJO: dict[Rol, list[str]] = {
    Rol.CAFICULTOR: ["inicio", "diagnostico", "que_hago", "cosecha", "venta"],
    Rol.AGRONOMO: ["mapa", "dashboard", "alertas", "rendimiento", "precios", "anomalias", "rag"],
}

ETIQUETA_ROL: dict[Rol, str] = {
    Rol.CAFICULTOR: "Caficultor",
    Rol.AGRONOMO: "Agrónomo / Cooperativa",
}


def construir_paginas(rol: Rol, admin: bool = False) -> tuple[dict[str, list["StreamlitPage"]], dict[str, "StreamlitPage"]]:
    """Crea las páginas del rol (más las de ``ADMINISTRACION`` si ``admin``).

    Returns:
        ``(secciones, indice)``: ``secciones`` va directo a ``st.navigation``;
        ``indice`` permite enlazar por clave (``indice["que_hago"]``).
    """
    secciones: dict[str, list["StreamlitPage"]] = {}
    indice: dict[str, "StreamlitPage"] = {}
    for p in MENU[rol] + (ADMINISTRACION if admin else []):
        pagina = st.Page(p.archivo, title=p.titulo, icon=p.icono, url_path=p.clave, default=p.inicio)
        secciones.setdefault(p.seccion, []).append(pagina)
        indice[p.clave] = pagina
    return secciones, indice


def clave_de(pagina: "StreamlitPage", indice: dict[str, "StreamlitPage"]) -> str | None:
    """Clave de la pantalla que se está mostrando."""
    for clave, candidata in indice.items():
        if candidata is pagina or candidata.title == pagina.title:
            return clave
    return None


# ───────────────────────── Barra de contexto ────────────────────────────────
def barra_contexto(ctx: ContextoFinca) -> None:
    """Franja fija con lo que el usuario ya entregó y lo que el sistema ya sabe.

    Caficultor: dos renglones, para que en el celular no ocupe la pantalla.
    Agrónomo: cuatro columnas, pensada para escritorio.
    """
    c, m = ctx.clima, ctx.mercado
    enso = f"ENSO {c.fase_legible}" + (f" (ONI {c.oni:+.2f}, {mes_anio(c.fecha_enso)})" if c.oni is not None else "")
    precio = (f"\\${_num(m.precio_fnc_cop_carga)} por carga ({mes_anio(m.fecha)})"
              if m.precio_fnc_cop_carga else "sin dato")

    with st.container(border=True):
        if ctx.rol == Rol.CAFICULTOR:
            f = ctx.finca
            finca = f"**{f.municipio}, {f.departamento}** · {_num(f.altitud_msnm)} msnm · {_num(f.area_ha, 1)} ha"
            if f.variedad:
                finca += f" · {f.variedad}"
            st.markdown(finca)
            st.caption(f"{enso} · Precio FNC {precio} · Última hoja: {_texto_diagnostico(ctx)}")
            return

        col_zona, col_clima, col_precio, col_sanidad = st.columns([3, 2, 2, 3])
        with col_zona:
            st.caption("Mi zona de trabajo · " + ", ".join(ctx.zona.departamentos))
            _selector_foco(ctx)
        with col_clima:
            st.caption("Clima")
            st.markdown(enso)
        with col_precio:
            st.caption("Precio FNC")
            st.markdown(precio)
        with col_sanidad:
            st.caption("Reportes de campo en mi zona")
            st.markdown(_texto_alertas(ctx))


_TODA_LA_ZONA = "Toda la zona"
_CLAVE_FOCO = "cofitech_selector_foco"


def _selector_foco(ctx: ContextoFinca) -> None:
    """Municipio en foco del agrónomo: lo leen Mapa, Indicadores y Rendimiento.

    El valor se guarda en el contexto (no en la clave del widget) para que
    sobreviva aunque la barra deje de dibujarse.
    """
    catalogo = catalogo_municipios()
    zona = catalogo[catalogo["departamento"].isin(ctx.zona.departamentos)]
    etiquetas = {fila.codigo_dane: f"{fila.municipio}, {fila.departamento}" for fila in zona.itertuples()}
    if ctx.zona.municipio_foco not in etiquetas:
        actualizar_foco(None)

    def _guardar() -> None:
        elegido = st.session_state[_CLAVE_FOCO]
        actualizar_foco(None if elegido == _TODA_LA_ZONA else elegido)

    st.session_state[_CLAVE_FOCO] = ctx.zona.municipio_foco or _TODA_LA_ZONA
    st.selectbox("Municipio en foco", [_TODA_LA_ZONA, *etiquetas], key=_CLAVE_FOCO, on_change=_guardar,
                 format_func=lambda c: etiquetas.get(c, _TODA_LA_ZONA), label_visibility="collapsed",
                 help="Municipio en foco para Mapa, Indicadores y Rendimiento.")


def _texto_diagnostico(ctx: ContextoFinca) -> str:
    d = ctx.diagnostico
    if d is None:
        return "aún no has revisado ninguna"
    texto = f"**{d.clase}**, confianza {d.confianza:.0%}"
    m = ctx.muestreo
    if m.hojas_evaluadas > 1:
        texto += f" ({m.hojas_con_roya} de {m.hojas_evaluadas} hojas con roya)"
    if m.riesgo:
        texto += f" · riesgo {m.riesgo.lower()}"
    if d.es_demo:
        texto += " (simulado)"
    return texto


def _texto_alertas(ctx: ContextoFinca) -> str:
    """Mismo conteo que el mapa de alertas: últimos 30 días, sin simulados ni diagnósticos rechazados."""
    resumen, _ = repositorio.resumen_roya(dias=30)
    if ctx.zona.departamentos:
        zona = {normalizar(d) for d in ctx.zona.departamentos}
        resumen = resumen[resumen["departamento"].map(normalizar).isin(zona)]
    if resumen.empty:
        return "Sin reportes en 30 días"
    fotos, municipios = int(resumen["fotos"].sum()), len(resumen)
    con_roya = int(resumen["fotos_roya"].sum())
    return (f"**{fotos} foto{'s' if fotos != 1 else ''}** de {municipios} "
            f"municipio{'s' if municipios != 1 else ''} · {con_roya} con roya (30 días)")


# ─────────────────────────── Siguiente paso ─────────────────────────────────
def siguiente_paso(ctx: ContextoFinca, pagina: "StreamlitPage", indice: dict[str, "StreamlitPage"]) -> None:
    """Enlace al paso que sigue en el recorrido del rol, con texto según el contexto."""
    flujo = FLUJO[ctx.rol]
    actual = clave_de(pagina, indice)
    if actual not in flujo or flujo.index(actual) + 1 >= len(flujo):
        return
    destino = flujo[flujo.index(actual) + 1]
    st.divider()
    st.page_link(indice[destino], label=_etiqueta_siguiente(ctx, actual, indice[destino].title),
                 icon=":material/arrow_forward:")


def _etiqueta_siguiente(ctx: ContextoFinca, actual: str, titulo_destino: str) -> str:
    if ctx.rol == Rol.CAFICULTOR:
        if actual == "inicio":
            return "Siguiente: revisar una hoja con la cámara"
        if actual == "diagnostico":
            d = ctx.diagnostico
            if d is None:
                return "Siguiente: ¿qué hago? (primero revisa una hoja)"
            return f"Siguiente: ¿qué hago con este resultado? ({d.clase}, {d.confianza:.0%})"
        if actual == "que_hago":
            return "Siguiente: ¿cuánto afecta esto mi cosecha y mi ingreso?"
        if actual == "cosecha":
            return "Siguiente: ¿a cómo puedo vender?"
    return f"Siguiente: {titulo_destino}"


# ───────────────────────────── Barra lateral ────────────────────────────────
def pie_lateral(ctx: ContextoFinca) -> None:
    """Rol activo y cambio de rol (útil en la sustentación para mostrar ambos)."""
    with st.sidebar:
        st.caption(f"Sesión como **{ETIQUETA_ROL[ctx.rol]}**")
        if seguridad.es_admin():
            st.caption(":material/admin_panel_settings: **Administrador del sistema**")
        if st.button("Cambiar de rol", use_container_width=True):
            definir_rol(None)
            st.rerun()
        if seguridad.es_admin() and st.button("Salir de administrador", icon=":material/logout:",
                                              use_container_width=True):
            seguridad.cerrar_sesion()
            st.rerun()


def _num(valor: float | None, decimales: int = 0) -> str:
    """Formato colombiano: punto de miles y coma decimal."""
    if valor is None:
        return "—"
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")
