"""
═══════════════════════════════════════════════════════════════════════════════
 app.py · Sistema IA Café Colombia — App Web (Streamlit)
═══════════════════════════════════════════════════════════════════════════════
 Punto de entrada multipágina. Usa la convención `pages/` de Streamlit.

 Ejecutar:
   cd 07_app_web
   python -m streamlit run app.py
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Sistema IA Café Colombia",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS personalizado
CSS = """
<style>
.big-metric {font-size: 2.5em; color: #2E7D32; font-weight: 700;}
.module-card {background: #f6f6f4; padding: 1.2em; border-radius: 12px;
              border-left: 4px solid #6F4E37; margin-bottom: 1em;}
h1 {color: #3E2723;}
h2 {color: #4E342E;}
.success {background: #e8f5e9; padding: 0.8em; border-radius: 8px;}
.warning {background: #fff8e1; padding: 0.8em; border-radius: 8px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Header
col1, col2 = st.columns([1, 4])
with col1:
    st.markdown("# ☕")
with col2:
    st.title("Sistema Integral de IA Agrícola — Café Colombia")
    st.markdown(
        "**Universidad Autónoma de Occidente · Ingeniería de Datos e IA · 2026-1**  \n"
        "Yáxul Santiago Cárdenas · Yesenia Díaz Urrego — *Entrega Final*"
    )

st.markdown("---")

# Hero / pitch
st.markdown(
    """
    Este sistema integra **datos abiertos del agro colombiano** con **modelos
    de IA** para apoyar decisiones del Ministerio de Agricultura (MADR) y la
    Federación Nacional de Cafeteros (FNC).
    """
)

# Métricas top
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Datasets integrados", "11", help="EVA, FNC, ICO, NOAA, IDEAM, Open-Meteo, FRED, World Bank, CALIBRO+RoCoLe+BRACOL+JMuBEN, SoilGrids, SRTM")
with c2:
    st.metric("Modelos entrenados", "13+", help="ML clásico, MLP profundo, CNN x3, RNN x4, AE+VAE")
with c3:
    st.metric("Imágenes café", "~10K", help="vs 47 en la 2da entrega")
with c4:
    st.metric("Cobertura syllabus", "U.I-IV ✓", help="Las 4 unidades del curso cubiertas")

st.markdown("---")

# Módulos del sistema
st.subheader("🧩 Módulos disponibles")

mods = [
    ("📊 Dashboard agroclimático", "Visualiza indicadores del café por departamento y año (rendimiento, precio, ENSO).", "1_📊_Dashboard"),
    ("🌱 Predicción de rendimiento", "Predice rendimiento (ton/ha) según condiciones climáticas (MLP profundo + Stacking).", "2_🌱_Rendimiento"),
    ("💰 Forecasting de precios", "Pronóstico de precio FNC e ICO (LSTM, BiGRU, Transformer).", "3_💰_Precios"),
    ("📷 Detector de enfermedades", "Sube foto de hoja → CNN clasifica Roya, Gotera, Cercospora, Phoma, Miner, Sano.", "4_📷_Enfermedades"),
    ("🤖 Asistente conversacional", "Chatbot RAG con contexto del proyecto, datos integrados y conocimiento agronómico.", "5_🤖_Chatbot"),
    ("🗺️ Mapa cafetero", "Mapa interactivo de municipios cafeteros + clústeres agroclimáticos.", "6_🗺️_Mapa"),
]

cols = st.columns(2)
for i, (titulo, desc, page) in enumerate(mods):
    with cols[i % 2]:
        st.markdown(
            f"<div class='module-card'><b>{titulo}</b><br/>{desc}</div>",
            unsafe_allow_html=True,
        )

st.markdown("---")

# Cobertura del syllabus
st.subheader("📚 Cobertura del syllabus")
syllabus = {
    "Unidad I — Introducción a la IA": "Documento académico (Cap. 1) — riesgos y oportunidades para café colombiano",
    "Unidad II — ML": "Regresión (NB02, NB05, NB09), Clasificación (NB11), Agrupamiento (NB11), Sesgos (Fairlearn en NB11)",
    "Unidad III — Redes Neuronales": "NB07: perceptrón → red superficial → MLP profundo. Comparación Adam/SGD/RMSprop.",
    "Unidad IV — Deep Learning": "CNN (NB08), LSTM/Transformer (NB10), VAE generativa (NB12), RAG/Transformers (06_agente_rag)",
}
for k, v in syllabus.items():
    st.markdown(f"**{k}**  \n{v}")

st.markdown("---")

# Estado de los modelos
st.subheader("🎯 Estado de los modelos")

models_status = {
    "Modelo": ["ML Precio (Ridge)", "ML Rendimiento (Stacking)", "MLP Profundo",
               "BiGRU Series Tiempo", "Transformer", "CNN MobileNetV2",
               "Autoencoder Anomalías", "Agente RAG (Groq+Llama3.1)"],
    "Estado 2da entrega": ["R²=0.945", "R²=0.067", "—",
                            "R²=−2.12", "—", "Acc=48.9%",
                            "—", "—"],
    "Estado entrega final": ["R²=0.945+", "R²>0.5 esperado", "Implementado",
                              "R²>0.5 esperado", "Implementado", "Acc=81.9%, F1=82.7%",
                              "Implementado", "Funcional y Rápido"],
}
import pandas as pd
df_status = pd.DataFrame(models_status)
st.dataframe(df_status, use_container_width=True, hide_index=True)

st.markdown("---")

# Footer
st.markdown(
    """
    <div style='text-align: center; color: #888; padding: 1em;'>
    Universidad Autónoma de Occidente · Ingeniería de Datos e IA · Mayo 2026<br/>
    Yáxul Santiago Cárdenas · Yesenia Díaz Urrego
    </div>
    """,
    unsafe_allow_html=True,
)
