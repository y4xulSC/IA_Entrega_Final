"""Mapa cafetero interactivo + clústeres agroclimáticos.

El mapa se centra solo: en la finca del caficultor o en el municipio en foco
que el agrónomo elige en la barra global. Sin municipio concreto, encuadra la
zona de trabajo.
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import folium
from streamlit_folium import st_folium

from cofitech.contexto_finca import Rol, catalogo_municipios, municipio_activo, obtener_contexto

st.set_page_config(page_title="Mapa", page_icon="🗺️", layout="wide")
st.title("🗺️ Mapa Cafetero de Colombia")

PROJECT = Path(__file__).resolve().parents[2]

# Centro Colombia
CENTRO = [4.5, -74.0]

# Municipios con coordenadas: catálogo con código DANE verificado contra EVA
@st.cache_data
def cargar_municipios():
    catalogo = catalogo_municipios()
    columnas = ["codigo_dane", "municipio", "departamento", "lat", "lon", "altitud_msnm"]
    return catalogo.loc[catalogo["lat"].notna() & catalogo["lon"].notna(), columnas].reset_index(drop=True)

df = cargar_municipios()
if df.empty:
    st.warning("⚠ Sin catálogo geográfico. Ejecuta el script de descarga 05 (DEM y suelos).")
    st.stop()

ctx = obtener_contexto()
activo = municipio_activo(ctx)                       # finca o municipio en foco
foco = df[df["codigo_dane"] == activo["codigo_dane"]] if activo and activo["codigo_dane"] else df.iloc[0:0]

st.markdown(f"**Municipios cafeteros mapeados:** {len(df)}")

# Sidebar
with st.sidebar:
    st.header("Filtros del mapa")
    deptos = sorted(df["departamento"].dropna().unique())
    zona = [d for d in ctx.zona.departamentos if d in deptos] if ctx.rol == Rol.AGRONOMO else []
    sel = st.multiselect("Departamentos", deptos, default=zona or deptos)
    df = df[df["departamento"].isin(sel)]
    alt_lo = int(df["altitud_msnm"].min()) if df["altitud_msnm"].notna().any() else 0
    alt_hi = int(df["altitud_msnm"].max()) if df["altitud_msnm"].notna().any() else 3000
    if alt_lo < alt_hi:
        # El rango por defecto (1000–2200) se ajusta a los límites de la selección:
        # con pocos departamentos quedaba fuera de rango y el control fallaba.
        defecto = (min(max(1000, alt_lo), alt_hi), max(min(2200, alt_hi), alt_lo))
        altitud_min, altitud_max = st.slider("Altitud (msnm)", alt_lo, alt_hi, defecto)
        # Sin altitud (coordenadas DIVIPOLA) no se puede filtrar: se muestran.
        df = df[df["altitud_msnm"].between(altitud_min, altitud_max) | df["altitud_msnm"].isna()]

# El municipio activo nunca se oculta por los filtros.
if not foco.empty:
    df = pd.concat([df, foco]).drop_duplicates("codigo_dane")
    CENTRO, ZOOM = [float(foco["lat"].iloc[0]), float(foco["lon"].iloc[0])], 11
    st.caption(f"Centrado en **{foco['municipio'].iloc[0]}, {foco['departamento'].iloc[0]}**.")
else:
    ZOOM = 6
    if activo:
        st.caption(f"{activo['municipio']} no tiene coordenadas en el catálogo; se muestra el mapa general.")

# Construir mapa
m = folium.Map(location=CENTRO, zoom_start=ZOOM, tiles="OpenStreetMap")
if foco.empty and len(df) and zona:
    # Sin municipio concreto: encuadrar la zona de trabajo del agrónomo.
    m.fit_bounds([[float(df["lat"].min()), float(df["lon"].min())],
                  [float(df["lat"].max()), float(df["lon"].max())]], max_zoom=9)

for _, r in df.iterrows():
    # Color según altitud (zonas cafeteras prefieren 1200-2000 msnm)
    alt = r.get("altitud_msnm", 1500) or 1500
    es_foco = not foco.empty and r["codigo_dane"] == foco["codigo_dane"].iloc[0]
    if es_foco:
        color = "darkblue"; icono = "star"
    elif 1200 <= alt <= 2000:
        color = "green"; icono = "leaf"
    elif alt < 1200:
        color = "orange"; icono = "info-sign"
    else:
        color = "red"; icono = "exclamation-sign"

    folium.Marker(
        location=[r["lat"], r["lon"]],
        popup=folium.Popup(
            f"<b>{r['municipio']}</b>{' · municipio en foco' if es_foco else ''}<br/>"
            f"Departamento: {r['departamento']}<br/>"
            f"Altitud: {alt:.0f} msnm<br/>"
            f"Código DANE: {r['codigo_dane']}",
            max_width=250),
        tooltip=r["municipio"],
        icon=folium.Icon(color=color, icon=icono, prefix="glyphicon"),
    ).add_to(m)

# Leyenda
legend = """
<div style='position: fixed; bottom: 50px; left: 50px; z-index: 1000;
    background: white; padding: 10px; border: 1px solid grey;'>
<b>Aptitud para café</b><br/>
<i style='color:green'>●</i> Óptima (1200-2000 msnm)<br/>
<i style='color:orange'>●</i> Subóptima (&lt;1200)<br/>
<i style='color:red'>●</i> Subóptima (&gt;2000)<br/>
<i style='color:darkblue'>★</i> Municipio en foco
</div>
"""
m.get_root().html.add_child(folium.Element(legend))

st_folium(m, height=600, use_container_width=True, returned_objects=[])

st.markdown("---")
st.subheader("📊 Tabla de municipios")
st.dataframe(df, use_container_width=True, hide_index=True)
