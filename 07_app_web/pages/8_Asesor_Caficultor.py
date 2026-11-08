"""Hoy en mi finca: paso 1 del MockUp ganador (lámina de Sofía).

Una pantalla de decisiones para el celular: precio FNC del día, clima y
último diagnóstico, tareas del mes y aviso de compradores que llevan a Vender.
Todo sale del contexto compartido (``cofitech/contexto_finca.py``): esta
pantalla ya no pide municipio, altitud ni área (RF01).

Para el agrónomo la misma pantalla es «Calendario del caficultor».
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from cofitech import marca, mercado
from cofitech.calendario import CALENDARIO, MESES, estado_fenologico
from cofitech.contexto_finca import Rol, mes_anio, obtener_contexto
from cofitech.datos import series_precios

st.set_page_config(page_title="Hoy en mi finca", page_icon=marca.ICONO, layout="wide")

ctx = obtener_contexto()
finca, clima, precio = ctx.finca, ctx.clima, ctx.mercado
hoy = date.today()

CONSEJO_ENSO = {
    "Nina": ("Más lluvia: vigila la roya", "ambar"),
    "Nino": ("Menos lluvia: cuida el sombrío", "rojo"),
    "Neutro": ("Año típico", "verde"),
}


@st.cache_data(ttl=3600, show_spinner=False)
def _variacion_fnc() -> tuple[float | None, float | None]:
    """Cambio del precio FNC frente al mes anterior y frente al promedio de 12 meses."""
    serie = series_precios().get("fnc")
    if serie is None or len(serie) < 13:
        return None, None
    ultimo, anterior = float(serie.iloc[-1]), float(serie.iloc[-2])
    media = float(serie.tail(12).mean())
    return 100 * (ultimo / anterior - 1), 100 * (ultimo / media - 1)


def _num(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


# ── Encabezado ──────────────────────────────────────────────────────────────
if ctx.rol == Rol.AGRONOMO:
    st.title("Calendario del caficultor")
    st.caption("Lo que ven tus asociados en su pantalla de inicio")
else:
    st.title("Hoy en mi finca")
    st.caption("Esto es lo que pasa hoy en tu finca")

col_izq, col_der = st.columns([1, 1], gap="large")

with col_izq:
    # ── Precio FNC (tarjeta café) ──
    cambio_mes, sobre_media = _variacion_fnc()
    if precio.precio_fnc_cop_carga:
        chip = (f"{'↑' if cambio_mes >= 0 else '↓'} {marca.pct(abs(cambio_mes), signo=False)} vs. mes anterior"
                if cambio_mes is not None else "")
        st.markdown(marca.tarjeta_precio(
            "Precio interno FNC", f"${_num(precio.precio_fnc_cop_carga)}",
            f"por carga de 125 kg · pergamino seco · dato de {mes_anio(precio.fecha)}", chip), unsafe_allow_html=True)
    else:
        st.markdown(marca.tarjeta("Precio interno FNC", "Sin dato", "Ejecuta el ETL de precios"), unsafe_allow_html=True)

    # ── Clima y última hoja ──
    c1, c2 = st.columns(2)
    with c1:
        consejo, tono = CONSEJO_ENSO.get(clima.fase_enso or "", ("Sin dato reciente", ""))
        st.markdown(marca.tarjeta("Clima (ENSO)", clima.fase_legible, consejo, tono),
                    unsafe_allow_html=True)
    with c2:
        d, m = ctx.diagnostico, ctx.muestreo
        if d is None:
            st.markdown(marca.tarjeta("Última hoja", "Sin revisar", "Toma una foto en «Revisar una hoja»"),
                        unsafe_allow_html=True)
        else:
            color = "rojo" if d.clase == "Roya" else ("verde" if d.clase == "Sano" else "ambar")
            riesgo = f"Riesgo {m.riesgo.lower()}" if m.riesgo else ""
            st.markdown(marca.tarjeta("Última hoja", f"{d.clase} {d.confianza:.0%}", riesgo, color),
                        unsafe_allow_html=True)

    # ── Compradores (lleva a Vender) ──
    lista = mercado.compradores()
    de_zona = mercado.compradores_de_zona(lista, finca.departamento) if finca.departamento else []
    if de_zona:
        n = len(de_zona)
        titulo = f"{n} comprador{'es' if n != 1 else ''} busca{'n' if n != 1 else ''} café de tu zona"
    else:
        titulo = f"{len(lista)} compradores reciben ofertas en CofiTech"
    st.markdown(marca.banner(titulo, "Contacto directo, sin intermediarios"
                             + (" · compradores de demostración" if all(c.es_demo for c in lista) else "")),
                unsafe_allow_html=True)
    if ctx.rol == Rol.CAFICULTOR:
        st.page_link("vistas/vender.py", label="Ir a Vender mi café", icon=":material/storefront:")

with col_der:
    # ── Tareas del mes ──
    info = CALENDARIO.get(hoy.month, {})
    with st.container(border=True):
        st.markdown(f"**Tareas de {MESES[hoy.month - 1]}** · {info.get('actividad', '—').lower()}")
        for i, tarea in enumerate(info.get("tareas", [])):
            st.checkbox(tarea, key=f"tarea_{hoy.year}_{hoy.month}_{i}")
        if hoy.month in (2, 5, 8, 11):
            st.warning("Este es mes de fertilización: la fórmula y la cantidad salen del análisis de suelos.")
        st.caption("Calendario de referencia de la zona andina; cambia por región y altitud. "
                   + estado_fenologico(hoy, finca.fecha_floracion_principal).capitalize() + ".")

    # ── Detalle (sin saturar la pantalla del celular) ──
    with st.expander("Clima y precio en detalle"):
        if clima.fase_enso == "Nino":
            st.error("**El Niño activo.** Reforzar el sombrío, vigilar el estrés hídrico y la roya por estrés.")
        elif clima.fase_enso == "Nina":
            st.warning("**La Niña activa.** Revisar drenajes, podas sanitarias para airear y vigilar gotera y roya.")
        elif clima.fase_enso:
            st.success("Condiciones ENSO neutras: año típico esperado.")
        if clima.oni is not None:
            st.caption(f"ONI {clima.oni:+.2f} ({mes_anio(clima.fecha_enso)}) · fuente: NOAA".replace(".", ",", 1))
        if sobre_media is not None:
            if sobre_media > 10:
                st.success(f"El precio está {sobre_media:.0f} % sobre el promedio de 12 meses: buen momento para vender.")
            elif sobre_media < -10:
                st.warning(f"El precio está {abs(sobre_media):.0f} % bajo el promedio de 12 meses: si puedes, espera.")
            else:
                st.info("El precio está en su rango normal de los últimos 12 meses.")

    with st.expander("Recomendaciones para tu finca"):
        altitud = finca.altitud_msnm or 0
        if altitud >= 1800:
            st.markdown(f"**{_num(altitud)} msnm: café de altura.** La maduración lenta favorece el café especial. "
                        "Cuida la cosecha selectiva y el beneficio; vigila gotera por humedad.")
        elif altitud >= 1200:
            st.markdown(f"**{_num(altitud)} msnm: zona cafetera óptima.** Variedades resistentes a roya "
                        "(Castillo, Cenicafé 1) y fertilización oportuna según el análisis de suelos.")
        elif altitud:
            st.markdown(f"**{_num(altitud)} msnm: zona baja.** Mayor presión de broca y minador: "
                        "control fitosanitario constante.")
        st.caption("Recomendaciones de referencia. Para un diagnóstico específico consulta al extensionista "
                   "del Comité de Cafeteros o de tu cooperativa.")
