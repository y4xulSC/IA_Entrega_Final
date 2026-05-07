"""Dashboard agroclimático — vista general del sistema café."""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard Agroclimático del Café Colombia")

PROJECT = Path(__file__).resolve().parents[2]
DIR_DATOS = PROJECT / "01_datos"

# ──────── Carga de datos ────────
@st.cache_data
def cargar_master():
    """Intenta leer master_cafe_*.csv en orden de preferencia."""
    candidatos = [
        DIR_DATOS / "procesados" / "master_cafe_municipal_mensual.csv",
        DIR_DATOS / "procesados" / "master_cafe_mensual.csv",
        PROJECT.parent / "IA_Segunda_Entrega" / "datasets" / "master_cafe_mensual.csv",
        PROJECT.parent / "IA_Segunda_Entrega" / "datasets" / "master_cafe_semestral.csv",
    ]
    for p in candidatos:
        if p.exists():
            df = pd.read_csv(p)
            return df, p
    return None, None

df, fuente = cargar_master()
if df is None:
    st.warning("⚠ Sin dataset maestro disponible. Ejecuta primero los scripts de descarga "
               "y carga de la BD, o el notebook NB04 de la 2da entrega.")
    st.stop()

st.caption(f"Fuente: `{fuente.name}` · {len(df)} registros")

# ──────── Filtros ────────
with st.sidebar:
    st.header("Filtros")
    if "anio" in df.columns:
        anio_min, anio_max = int(df["anio"].min()), int(df["anio"].max())
        rango = st.slider("Rango de años", anio_min, anio_max,
                          (max(anio_min, 2019), anio_max))
        df = df[(df["anio"] >= rango[0]) & (df["anio"] <= rango[1])]

    if "departamento" in df.columns:
        deptos = sorted(df["departamento"].dropna().unique())
        sel_dpto = st.multiselect("Departamentos", deptos,
                                   default=[d for d in deptos[:5]])
        df = df[df["departamento"].isin(sel_dpto)]
    elif "Dpto" in df.columns:
        df = df.rename(columns={"Dpto": "departamento"})

# ──────── KPIs ────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    if "produccion_ton" in df.columns:
        st.metric("Producción total", f"{df['produccion_ton'].sum():,.0f} ton")
with c2:
    if "rendimiento_ton_ha" in df.columns:
        st.metric("Rendimiento promedio", f"{df['rendimiento_ton_ha'].mean():.3f} ton/ha")
with c3:
    if "precio_interno_cop_125kg" in df.columns:
        st.metric("Precio interno medio", f"${df['precio_interno_cop_125kg'].mean():,.0f}")
    elif "precio_fnc_cop_125kg" in df.columns:
        st.metric("Precio FNC medio", f"${df['precio_fnc_cop_125kg'].mean():,.0f}")
with c4:
    if "fase_enso" in df.columns or "es_El_Nino" in df.columns:
        col = "fase_enso" if "fase_enso" in df.columns else None
        st.metric("Eventos ENSO", df[col].nunique() if col else "—")

st.markdown("---")

# ──────── Gráficos ────────
tab1, tab2, tab3, tab4 = st.tabs(["📈 Evolución", "🌡️ Clima", "💰 Precios", "🌎 Geografía"])

with tab1:
    if "produccion_ton" in df.columns and "anio" in df.columns:
        df_evo = df.groupby("anio")["produccion_ton"].sum().reset_index()
        fig = px.line(df_evo, x="anio", y="produccion_ton",
                      title="Producción nacional de café por año",
                      markers=True)
        st.plotly_chart(fig, use_container_width=True)

    if "rendimiento_ton_ha" in df.columns:
        col_dpto = "departamento" if "departamento" in df.columns else None
        if col_dpto:
            fig2 = px.box(df, x=col_dpto, y="rendimiento_ton_ha",
                          title="Distribución de rendimiento por departamento")
            st.plotly_chart(fig2, use_container_width=True)

with tab2:
    cols_clima = [c for c in df.columns if any(s in c.lower()
                  for s in ["temp", "precip", "et0", "ndvi"])]
    if cols_clima:
        col_sel = st.selectbox("Variable climática", cols_clima)
        if "anio" in df.columns:
            df_c = df.groupby("anio")[col_sel].mean().reset_index()
            fig = px.line(df_c, x="anio", y=col_sel,
                          title=f"Evolución de {col_sel}", markers=True)
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    cols_precio = [c for c in df.columns if "precio" in c.lower()]
    if cols_precio and "anio" in df.columns:
        col_p = st.selectbox("Variable de precio", cols_precio)
        df_p = df.groupby("anio")[col_p].mean().reset_index()
        fig = px.line(df_p, x="anio", y=col_p,
                      title=f"Evolución de {col_p}", markers=True)
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    if "departamento" in df.columns and "produccion_ton" in df.columns:
        df_geo = df.groupby("departamento")["produccion_ton"].sum().reset_index()
        df_geo = df_geo.sort_values("produccion_ton", ascending=True).tail(15)
        fig = px.bar(df_geo, y="departamento", x="produccion_ton",
                     orientation="h", title="Top 15 departamentos productores")
        st.plotly_chart(fig, use_container_width=True)

# ──────── Análisis ENSO ────────
st.markdown("---")
st.subheader("🌊 Impacto de ENSO en el rendimiento")

if "fase_enso" in df.columns and "rendimiento_ton_ha" in df.columns:
    df_enso = df.groupby("fase_enso")["rendimiento_ton_ha"].agg(["mean", "std", "count"]).reset_index()
    fig_enso = px.bar(df_enso, x="fase_enso", y="mean",
                       error_y="std",
                       title="Rendimiento promedio por fase ENSO")
    st.plotly_chart(fig_enso, use_container_width=True)
    st.dataframe(df_enso, hide_index=True)
elif "es_El_Nino" in df.columns:
    df["fase_calc"] = df.apply(lambda r:
        "Nino" if r.get("es_El_Nino", 0) else
        "Nina" if r.get("es_La_Nina", 0) else "Neutro", axis=1)
    df_enso = df.groupby("fase_calc")["rendimiento_ton_ha"].mean().reset_index()
    fig_enso = px.bar(df_enso, x="fase_calc", y="rendimiento_ton_ha",
                       title="Rendimiento por fase ENSO")
    st.plotly_chart(fig_enso, use_container_width=True)
