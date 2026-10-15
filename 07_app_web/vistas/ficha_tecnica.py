"""Ficha técnica de modelos (antes ``app.py``, la portada de la app anterior).

Desde la refactorización del MockUp final, ``app.py`` es el enrutador por
roles y esta portada vive aquí, en la sección «Administración». El contenido
se conserva; la tabla de estado de los modelos se actualizó con las cifras
reales (ver ``claude/Bitacora_MockUp_decisiones_y_hallazgos.md``).
"""

import streamlit as st

from cofitech import precios_ridge, seguridad

seguridad.exigir_admin()

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
    ("🌱 Rendimiento e ingreso", "Línea base EVA del municipio ajustada por el riesgo de roya; simulador agroclimático experimental para el agrónomo.", "2_🌱_Rendimiento"),
    ("💰 Escenarios de precio", "Simulador Ridge validado (arábica + TRM → precio interno FNC); redes recurrentes en calibración.", "3_💰_Precios"),
    ("📷 Detector de enfermedades", "Foto de hoja → CNN (7 clases) + Grad-CAM; orientación de manejo de roya según la incidencia del lote.", "4_📷_Enfermedades"),
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

sim = precios_ridge.simulador()
ridge = (f"Simulador validado {sim.validacion.desde:%Y-%m}–{sim.validacion.hasta:%Y-%m}: "
         f"R²={sim.validacion.r2:.3f}, MAPE={sim.validacion.mape:.1%} "
         f"(mes anterior: R²={sim.validacion.r2_ingenuo:.3f})") if sim else "Sin datos para validar"
models_status = {
    "Modelo": ["ML Precio (Ridge: arábica + TRM)", "ML Rendimiento (NB09)", "MLP Profundo (NB07)",
               "BiGRU / LSTM / Transformer (NB10)", "CNN MobileNetV2 (NB08)",
               "Autoencoder Anomalías (NB12)", "Agente RAG"],
    "Estado 2da entrega": ["R²=0.945", "R²=0.067", "—", "R²=−2.12 (BiGRU)", "Acc=48.9%", "—", "—"],
    "Estado entrega final": [
        ridge,
        "R²=0.818 medido sobre datos simulados; con EVA real (prueba 2016–2018): 0.28 vs. 0.60 de repetir "
        "el año anterior → la app usa la línea base EVA",
        "Implementado (NB07); no se usa en la app",
        "En calibración (Modelos Experimentales de Alta Volatilidad)",
        "Acc=81.9%, F1=82.7% (test NB08) + Grad-CAM en la app",
        "Implementado (NB12); la app usa volatilidad móvil con percentil 97.5",
        "Groq openai/gpt-oss-20b + ChromaDB, con salvaguardas de dosis verificadas en código",
    ],
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
