"""Alertas fitosanitarias: mapa de calor de los reportes de roya en la zona del agrónomo.

Es la pantalla que prueba que las herramientas están conectadas: cada foto que
clasifica la CNN en el rol Caficultor llega a ``cafe.registro_diagnosticos``
(Supabase) y aparece aquí agregada por municipio, desde cualquier equipo.

* El panel se vuelve a leer solo cada 30 s (``st.fragment(run_every=...)``).
* No cuentan como roya los diagnósticos que el caficultor rechazó con 👎.
* Si Supabase no responde se muestra el archivo local de este equipo y se avisa.
"""
from __future__ import annotations

from datetime import datetime

import folium
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium

from cofitech import repositorio
from cofitech.contexto_finca import catalogo_municipios, obtener_contexto
from cofitech.datos import normalizar

CENTRO_COLOMBIA = (4.5, -74.0)
REFRESCO = "30s"
# Semáforo por % de fotos con roya (prioridad de visita, no incidencia del lote).
UMBRALES_COLOR: tuple[tuple[float, str], ...] = ((50, "#c0392b"), (20, "#e67e22"), (0, "#27ae60"))

ctx = obtener_contexto()
st.title("Alertas fitosanitarias")
st.caption("Dónde están reportando roya los caficultores de tu zona, a partir de las fotos de hojas.")

col_dias, col_demo, col_boton = st.columns([2, 2, 1], vertical_alignment="bottom")
dias = col_dias.select_slider("Periodo", options=[7, 15, 30, 90, 365], value=30,
                              format_func=lambda d: f"Últimos {d} días")
incluir_demo = col_demo.toggle("Incluir registros simulados", value=False,
                               help="Los del panel de depuración (botón «Simular hoja con roya»).")
if col_boton.button("Actualizar", icon=":material/refresh:", use_container_width=True):
    repositorio.refrescar()


def _color(pct: float) -> str:
    return next(color for umbral, color in UMBRALES_COLOR if pct >= umbral)


def _en_zona(resumen: pd.DataFrame) -> pd.DataFrame:
    if not ctx.zona.departamentos:
        return resumen
    zona = {normalizar(d) for d in ctx.zona.departamentos}
    return resumen[resumen["departamento"].map(normalizar).isin(zona)]


def _con_coordenadas(resumen: pd.DataFrame) -> pd.DataFrame:
    coords = catalogo_municipios()[["codigo_dane", "lat", "lon"]].dropna().drop_duplicates("codigo_dane")
    return resumen.merge(coords, on="codigo_dane", how="left")


def _mapa(puntos: pd.DataFrame) -> folium.Map:
    foco = puntos[puntos["codigo_dane"] == ctx.zona.municipio_foco]
    if not foco.empty:
        mapa = folium.Map(location=[foco["lat"].iloc[0], foco["lon"].iloc[0]], zoom_start=11, tiles="OpenStreetMap")
    else:
        mapa = folium.Map(location=CENTRO_COLOMBIA, zoom_start=6, tiles="OpenStreetMap")
        if len(puntos) > 1:
            mapa.fit_bounds([[puntos["lat"].min(), puntos["lon"].min()],
                             [puntos["lat"].max(), puntos["lon"].max()]], padding=(30, 30))
        elif len(puntos) == 1:
            mapa.location = [puntos["lat"].iloc[0], puntos["lon"].iloc[0]]
            mapa.options["zoom"] = 10

    con_roya = puntos[puntos["fotos_roya"] > 0]
    if not con_roya.empty:
        # leaflet.heat satura en 1.0: se normaliza contra el municipio con más reportes.
        maximo = float(con_roya["fotos_roya"].max())
        HeatMap(
            [[f.lat, f.lon, f.fotos_roya / maximo] for f in con_roya.itertuples()],
            name="Reportes de roya", radius=35, blur=25, min_opacity=0.35,
            # leaflet.heat atenúa los puntos cuando el zoom es menor que max_zoom;
            # con max_zoom=1 la intensidad no depende del zoom en el que se mire.
            max_zoom=1, gradient={0.2: "#f1c40f", 0.5: "#e67e22", 1.0: "#c0392b"},
        ).add_to(mapa)

    for f in puntos.itertuples():
        ultimo = pd.Timestamp(f.ultimo_reporte)
        ultimo = ultimo.tz_convert("America/Bogota") if ultimo.tzinfo else ultimo
        folium.CircleMarker(
            location=[f.lat, f.lon],
            radius=6 + min(int(f.fotos), 20),
            color=_color(f.pct_fotos_roya), fill=True, fill_opacity=0.55, weight=2,
            tooltip=f"{f.municipio}: {int(f.fotos_roya)} de {int(f.fotos)} fotos con roya",
            popup=folium.Popup(
                f"<b>{f.municipio}, {f.departamento}</b><br>"
                f"Fotos con roya: {int(f.fotos_roya)} de {int(f.fotos)} ({f.pct_fotos_roya:.0f} %)<br>"
                f"Último reporte: {ultimo:%d/%m/%Y %H:%M}", max_width=260),
        ).add_to(mapa)
    return mapa


@st.fragment(run_every=REFRESCO)
def panel_en_vivo(dias: int, incluir_demo: bool) -> None:
    resumen, fuente = repositorio.resumen_roya(dias, incluir_demo)
    resumen = _en_zona(resumen)
    hora = datetime.now().strftime("%H:%M:%S")

    if fuente == "Supabase":
        st.caption(f":material/cloud_done: Fuente: Supabase (`cafe.registro_diagnosticos`) · "
                   f"leído a las {hora} · se actualiza cada 30 s")
    elif repositorio.db_client.configurado():
        st.warning(f"Supabase no responde ({repositorio.db_client.estado()}). Se muestran solo los "
                   "reportes guardados en este equipo; se reintenta cada minuto.")
    else:
        st.caption(f":material/folder: Fuente: archivo local de este equipo · leído a las {hora}. "
                   "Configura Supabase para ver los reportes de todos los caficultores.")

    if resumen.empty:
        st.info(f"No hay reportes de campo en tu zona en los últimos {dias} días. Aparecen aquí "
                "cuando un caficultor de estos departamentos revisa una hoja con la cámara.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Fotos recibidas", int(resumen["fotos"].sum()))
    c2.metric("Fotos con roya", int(resumen["fotos_roya"].sum()))
    c3.metric("Municipios con roya", int((resumen["fotos_roya"] > 0).sum()),
              help=f"De {len(resumen)} municipios que enviaron fotos.")

    datos = _con_coordenadas(resumen)
    puntos = datos.dropna(subset=["lat", "lon"])
    if not puntos.empty:
        st_folium(_mapa(puntos), height=520, use_container_width=True,
                  returned_objects=[], key="mapa_alertas_roya")
    sin_mapa = datos[datos["lat"].isna()]
    if not sin_mapa.empty:
        st.caption(
            f"Sin coordenadas para ubicar en el mapa: {', '.join(sin_mapa['municipio'].fillna('sin municipio'))}. "
            "Ejecuta `python 03_scripts/descarga/08_descargar_divipola.py` para traer las de todos los municipios."
        )

    tabla = resumen.drop(columns="codigo_dane").assign(
        ultimo_reporte=pd.to_datetime(resumen["ultimo_reporte"], utc=True).dt.tz_convert("America/Bogota"))
    st.dataframe(
        tabla, hide_index=True, use_container_width=True,
        column_config={
            "departamento": "Departamento", "municipio": "Municipio",
            "fotos": "Fotos recibidas", "fotos_roya": "Con roya",
            "pct_fotos_roya": st.column_config.ProgressColumn(
                "% de fotos con roya", min_value=0, max_value=100, format="%.0f %%"),
            "ultimo_reporte": st.column_config.DatetimeColumn("Último reporte", format="D MMM YYYY, HH:mm"),
        },
    )


panel_en_vivo(dias, incluir_demo)

st.caption(
    "El porcentaje se calcula sobre las fotos enviadas, no sobre el cultivo: quien fotografía suele "
    "elegir hojas con síntomas. Sirve para priorizar visitas; la decisión de control se toma con el "
    "muestreo de incidencia en el lote (umbral del 5 %). No se cuentan como roya los diagnósticos que "
    "el caficultor marcó como incorrectos. (Fuente: Manual de Caficultura / Boletines Técnicos Cenicafé)"
)
