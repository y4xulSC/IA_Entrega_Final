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

# Carga de datos
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

# Filtros
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

# KPIs
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

# Gráficos
tab1, tab2, tab3 = st.tabs(["📈 Evolución", "🌡️ Clima", "💰 Precios"])

if "anio" not in df.columns and "ano" not in df.columns:
    for f_col in ["fecha", "Fecha", "date", "Date"]:
        if f_col in df.columns:
            df["anio"] = pd.to_datetime(df[f_col], errors="coerce").dt.year
            break
col_anio = "anio" if "anio" in df.columns else ("ano" if "ano" in df.columns else None)
col_rend = next((c for c in df.columns if "rendimiento" in c.lower()), None)
col_prod = next((c for c in df.columns if "produccion" in c.lower() or "prod" in c.lower()), None)
col_enso = next((c for c in df.columns if "enso" in c.lower() or "nino" in c.lower() or "nina" in c.lower()), None)

with tab1:
    col_prod = next((c for c in df.columns if "produccion" in c.lower() or "prod" in c.lower()), None)
    if col_prod and col_anio:
        df_evo = df.groupby(col_anio)[col_prod].sum().reset_index()
        fig = px.line(df_evo, x=col_anio, y=col_prod,
                      title="Producción de café por año",
                      markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No se encontró columna de 'producción' o 'año' en el dataset.")

    col_rend = next((c for c in df.columns if "rendimiento" in c.lower()), None)
    col_dpto = next((c for c in df.columns if "departamento" in c.lower() or "dpto" in c.lower()), None)
    if col_rend and col_dpto:
        fig2 = px.box(df, x=col_dpto, y=col_rend,
                      title="Distribución de rendimiento por departamento")
        st.plotly_chart(fig2, use_container_width=True)
        
    col_dpto = next((c for c in df.columns if "departamento" in c.lower() or "dpto" in c.lower()), None)
    metrica_box = col_rend if col_rend else col_prod
    
    if metrica_box and col_dpto:
        fig2 = px.box(df, x=col_dpto, y=metrica_box,
                      title=f"Distribución de {metrica_box} por departamento")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Faltan datos de departamento o métrica agrícola para la distribución.")

with tab2:
    cols_clima = [c for c in df.columns if any(s in c.lower() for s in ["temp", "precip", "et0", "ndvi"])]
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

# Análisis ENSO
st.markdown("---")
st.subheader("🌊 Impacto de ENSO en el rendimiento")

if col_enso:
    metrica_enso = col_rend if col_rend else col_prod
    
    if metrica_enso:
        df_enso = df.groupby(col_enso)[metrica_enso].mean().reset_index()
        fig_enso = px.bar(df_enso, x=col_enso, y=metrica_enso,
                          title=f"Promedio de {metrica_enso} por fase climática (ENSO)")
        st.plotly_chart(fig_enso, use_container_width=True)
    else:
        st.info("No se encontró variable de producción o rendimiento para comparar con ENSO.")
else:
    st.info("No se encontró información sobre el fenómeno ENSO en este dataset.")
