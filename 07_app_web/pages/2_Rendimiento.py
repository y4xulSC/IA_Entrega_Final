"""Predicción de rendimiento (ton/ha) — usa el mejor modelo disponible."""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import joblib

st.set_page_config(page_title="Rendimiento", page_icon="🌱", layout="wide")
st.title("🌱 Predicción de Rendimiento del Café")

PROJECT = Path(__file__).resolve().parents[2]
DIR_MOD = PROJECT / "04_modelos_entrenados"

st.markdown("""
Predice el rendimiento (ton/ha) según condiciones climáticas y de mercado.
El modelo se entrenó con datos de 8 departamentos cafeteros 2019–2024 y se
mejora en la entrega final con datos municipales.
""")

# Inputs
with st.sidebar:
    st.header("Variables de entrada")
    temp_media = st.slider("Temperatura media (°C)", 14.0, 28.0, 21.0, 0.5)
    temp_min = st.slider("Temperatura mínima (°C)", 8.0, 22.0, 16.0, 0.5)
    temp_max = st.slider("Temperatura máxima (°C)", 22.0, 35.0, 27.0, 0.5)
    precip = st.slider("Precipitación total semestre (mm)", 0, 5000, 1500, 50)
    altitud = st.slider("Altitud (msnm)", 500, 2500, 1500, 50)
    oni = st.slider("Índice ONI (ENSO)", -2.5, 2.5, 0.0, 0.1,
                     help=">+0.5 = El Niño, <-0.5 = La Niña")
    area = st.number_input("Área cosechada (ha)", 1, 100000, 100)
    precio_fnc = st.number_input("Precio FNC actual (COP/125kg)", 1_000_000, 5_000_000, 2_000_000, 50_000)
    dpto = st.selectbox("Departamento", ["Huila", "Antioquia", "Nariño",
        "Caldas", "Tolima", "Quindio", "Risaralda", "Santander", "Cauca"])

# Cargar modelo
@st.cache_resource
def cargar_modelo():
    modelo_path = DIR_MOD / "ml_municipal_rendimiento.pkl"
    if modelo_path.exists():
        try:
            return joblib.load(modelo_path), modelo_path.name
        except Exception as e:
            st.error(f" [WARNING] El archivo existe, pero falló al cargar: {e}")
            return None, None
    st.error(f" [WARNING] No se encontró el modelo entrenado en: {modelo_path}")
    return None, None

modelo, nombre = cargar_modelo()

# Predicción
if st.button("🔮 Predecir rendimiento", type="primary"):
    # Vector de features simplificado (en producción ajustar al pipeline real)
    enso_int = abs(oni) if oni > 0.5 or oni < -0.5 else 0
    es_nino = int(oni > 0.5); es_nina = int(oni < -0.5)
    estres_hidrico = max(0, 1 - precip / 1500)
    amplitud_term = temp_max - temp_min

    if modelo is not None:
        try:
            # Feature vector — el shape exacto depende del modelo entrenado
            mes_actual = pd.Timestamp.now().month
            X = pd.DataFrame([{
                "mes": mes_actual,
                "ano": 2026,
                "departamento": dpto,
                "altitud_msnm": altitud,
                "fase_enso": "El Nino" if es_nino else ("La Nina" if es_nina else "Neutro"),
                "temp_med_c": temp_media,
                "precip_mm": precip,
                "area_sembrada_ha": area,
                "precio_fnc_cop_carga": precio_fnc,
                "oni_index": oni,
                "Area_sembrada": area,
                "Area_cosechada": area*0.95,
                "Produccion_ton": area*1.0,
                "Temp_media_sem": temp_media,
                "Temp_min_sem": temp_min,
                "Temp_max_sem": temp_max,
                "Precip_total_sem": precip,
                "ONI_media": oni,
                "ENSO_intensidad": enso_int,
                "es_El_Nino": es_nino,
                "es_La_Nina": es_nina,
                "Estres_hidrico": estres_hidrico,
                "Amplitud_termica": amplitud_term,
                "Precio_interno_cop": precio_fnc,
                "Precio_interno_cop_lag1": precio_fnc,
            }])
            pred = float(modelo.predict(X)[0]) if hasattr(modelo, "predict") else None
        except Exception as e:
            # Fallback heurístico
            pred = None
            st.warning(f"Modelo cargado pero predicción falló: {e}. Usando heurística.")

        if pred is None:
            # Heurística simple
            base = 1.0
            base *= (1 - 0.24 * es_nino)  # El Niño reduce 24%
            base *= (1 - 0.12 * es_nina)  # La Niña reduce 12%
            base *= 1 + 0.05 * (temp_media - 21) / 21  # T cerca de óptima
            base *= 1 + 0.10 * min(0, (precip - 1500) / 1500)  # déficit hídrico
            pred = max(0.1, base)
    else:
        st.warning(" Sin modelo entrenado disponible — usando heurística")
        pred = 1.0 * (1 - 0.24 * es_nino) * (1 - 0.12 * es_nina)

    # Mostrar resultado
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rendimiento predicho", f"{pred:.3f} ton/ha")
    with col2:
        produccion = pred * area
        st.metric("Producción esperada", f"{produccion:,.1f} ton")
    with col3:
        ingreso = produccion * 1000 * (precio_fnc / 125)
        st.metric("Ingreso bruto estimado", f"${ingreso:,.0f} COP")

    if modelo is not None:
        st.caption(f"Modelo usado: `{nombre}`")

    # Análisis ENSO
    st.markdown("---")
    st.subheader("Impacto del ENSO actual")
    if es_nino:
        st.error(f"⚠ **El Niño activo** (ONI={oni}). El rendimiento esperado es ~24% menor que en condiciones neutras.")
    elif es_nina:
        st.warning(f"⚠ **La Niña activa** (ONI={oni}). Rendimiento esperado ~12% menor que en condiciones neutras.")
    else:
        st.success(f"✓ **Condiciones ENSO neutras** (ONI={oni}). Rendimiento esperado en rango óptimo.")

    # Recomendaciones
    st.subheader("📋 Recomendaciones agronómicas")
    if precip < 1000:
        st.write("- Considerar riego suplementario — precipitación insuficiente.")
    if temp_media > 24:
        st.write("- Temperatura alta — sombrar el cafetal con árboles.")
    if precio_fnc > 2_500_000:
        st.write("- Precio favorable — aprovechar para vender stock.")

st.markdown("---")
st.caption("⚠ Este es un sistema de apoyo a la decisión. Las predicciones tienen "
           "intervalos de confianza considerables — consultar el extensionista FNC.")
