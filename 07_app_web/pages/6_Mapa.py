"""Mapa cafetero interactivo + clústeres agroclimáticos."""
import streamlit as st
import pandas as pd
from pathlib import Path
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Mapa", page_icon="🗺️", layout="wide")
st.title("🗺️ Mapa Cafetero de Colombia")

PROJECT = Path(__file__).resolve().parents[2]

# Centro Colombia
CENTRO = [4.5, -74.0]

# ─── Datos de municipios cafeteros (con coords del script descarga 05) ───
@st.cache_data
def cargar_municipios():
    p1 = PROJECT / "01_datos" / "enriquecidos" / "geografia" / "dem_municipal_altitud.csv"
    if p1.exists():
        return pd.read_csv(p1)
    # Fallback: lista hardcoded del script
    data = [
        ("41001","Neiva","Huila",2.9389,-75.2819,442),
        ("05001","Medellin","Antioquia",6.2442,-75.5812,1495),
        ("52001","Pasto","Nariño",1.2136,-77.2811,2527),
        ("17001","Manizales","Caldas",5.0703,-75.5138,2160),
        ("63001","Armenia","Quindio",4.5340,-75.6811,1483),
        ("66001","Pereira","Risaralda",4.8133,-75.6961,1411),
        ("73001","Ibague","Tolima",4.4389,-75.2322,1285),
        ("76001","Cali","Valle",3.4516,-76.5320,995),
        ("19001","Popayan","Cauca",2.4448,-76.6147,1738),
    ]
    return pd.DataFrame(data, columns=["codigo_dane","municipio","departamento","lat","lon","altitud_msnm"])

df = cargar_municipios()

st.markdown(f"**Municipios cafeteros mapeados:** {len(df)}")

# ─── Sidebar ───
with st.sidebar:
    st.header("Filtros del mapa")
    deptos = sorted(df["departamento"].dropna().unique())
    sel = st.multiselect("Departamentos", deptos, default=deptos)
    df = df[df["departamento"].isin(sel)]
    altitud_min, altitud_max = st.slider("Altitud (msnm)",
        int(df["altitud_msnm"].min()) if len(df) else 0,
        int(df["altitud_msnm"].max()) if len(df) else 3000,
        (1000, 2200))
    df = df[(df["altitud_msnm"] >= altitud_min) & (df["altitud_msnm"] <= altitud_max)]

# ─── Construir mapa ───
m = folium.Map(location=CENTRO, zoom_start=6, tiles="OpenStreetMap")

for _, r in df.iterrows():
    # Color según altitud (zonas cafeteras prefieren 1200-2000 msnm)
    alt = r.get("altitud_msnm", 1500) or 1500
    if 1200 <= alt <= 2000:
        color = "green"; icono = "leaf"
    elif alt < 1200:
        color = "orange"; icono = "info-sign"
    else:
        color = "red"; icono = "exclamation-sign"

    folium.Marker(
        location=[r["lat"], r["lon"]],
        popup=folium.Popup(
            f"<b>{r['municipio']}</b><br/>"
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
<i style='color:red'>●</i> Subóptima (&gt;2000)
</div>
"""
m.get_root().html.add_child(folium.Element(legend))

st_folium(m, height=600, use_container_width=True)

st.markdown("---")
st.subheader("📊 Tabla de municipios")
st.dataframe(df, use_container_width=True, hide_index=True)
