"""Detector de enfermedades — sube imagen y la CNN clasifica."""
import streamlit as st
from pathlib import Path
import numpy as np
from PIL import Image
import io

st.set_page_config(page_title="Enfermedades", page_icon="📷", layout="wide")
st.title("📷 Detector de Enfermedades del Café")

PROJECT = Path(__file__).resolve().parents[2]
DIR_MOD = PROJECT / "04_modelos_entrenados"

st.markdown("""
Sube una foto de hoja o fruto de café y la CNN clasifica entre **Roya, Gotera,
Cercospora, Phoma, Miner, Sano**. La predicción incluye Grad-CAM para
explicabilidad visual.
""")

# ─── Cargar modelo ───
@st.cache_resource
def cargar_modelo():
    try:
        import tensorflow as tf
    except ImportError:
        return None, None

    candidatos = [
        DIR_MOD / "cnn_cafe_best.keras",
        DIR_MOD / "modelo_cnn_clasificacion_cafe.keras",
        PROJECT.parent / "IA_Segunda_Entrega" / "outputs" / "modelos" / "modelo_cnn_clasificacion_cafe.keras",
    ]
    for p in candidatos:
        if p.exists():
            try:
                m = tf.keras.models.load_model(p)
                return m, p.name
            except Exception:
                continue
    return None, None

modelo, nombre_modelo = cargar_modelo()

# ─── Upload ───
archivo = st.file_uploader("Selecciona una imagen", type=["jpg", "jpeg", "png"])

if archivo:
    img = Image.open(archivo).convert("RGB")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Imagen original")
        #st.image(img, use_column_width=True)
        st.image(img, use_container_width=True)

    with col2:
        st.subheader("Análisis del modelo")
        if modelo is not None:
            try:
                import tensorflow as tf
                # from tensorflow.keras.applications.efficientnet import preprocess_input
                target_size = (224, 224)
                img_r = img.resize(target_size)
                arr = np.array(img_r, dtype=np.float32)
                # arr = preprocess_input(arr)
                arr = arr / 255.0  # Normalización simple
                arr = np.expand_dims(arr, 0)

                # pred = modelo.predict(arr, verbose=0)[0]
                predicciones = modelo.predict(arr, verbose=0)
                # Como el modelo devuelve [Probabilidades_Clases, Severidad], tomamos [0][0]
                pred = predicciones[0][0]
                clases = ["Cercospora", "Gotera", "Miner", "Phoma", "Roya", "Sano", "SpiderMite"]
                # NOTA: La logica que adaptamos y esta en cnn_cafe_best.keras ya no predice la severidad confiable, solo la clase. 
                # Por eso se ignora el tema de las 4 clases de severidad y se asume que el modelo ya predice la clase final.
                # if len(pred) != len(clases):
                #     # Adaptar a la 2da entrega (4 clases severidad)
                #     clases = ["Sin enfermedad", "Bajo", "Medio", "Alto"][:len(pred)]
                idx = int(np.argmax(pred))
                conf = float(pred[idx])

                st.metric("Predicción", clases[idx], f"Confianza: {conf:.2%}")

                # Tabla de probabilidades
                import pandas as pd
                df_p = pd.DataFrame({"clase": clases, "prob": pred})\
                        .sort_values("prob", ascending=False)
                st.dataframe(df_p, hide_index=True, use_container_width=True)

                # Recomendación
                if "Roya" in clases[idx]:
                    st.error("⚠ Roya detectada — aplicar fungicida sistémico (triazoles) "
                              "y considerar variedades resistentes (Castillo, Colombia).")
                elif "Gotera" in clases[idx]:
                    st.error("⚠ Gotera detectada — controlar humedad excesiva, podar "
                              "para mejorar ventilación, aplicar cobre.")
                elif "Sano" in clases[idx] or "Sin" in clases[idx]:
                    st.success("✓ Hoja sana — mantener prácticas actuales de manejo.")
                else:
                    st.warning(f"Detectado: {clases[idx]} — consultar extensionista FNC.")

                st.caption(f"Modelo: `{nombre_modelo}`")
            except Exception as e:
                st.error(f"Error al procesar: {e}")
        else:
            st.warning("⚠ Modelo CNN no encontrado en `04_modelos_entrenados/`. "
                        "Ejecuta el notebook NB08 primero.")
            st.info("**Demo (sin modelo):**")
            st.metric("Predicción simulada", "Roya", "Confianza: 78%")
else:
    st.info("👆 Sube una imagen para empezar")

# ─── Galería de ejemplos ───
st.markdown("---")
st.subheader("📸 Ejemplos del dataset CALIBRO (2da entrega)")
ejemplos_dir = PROJECT.parent / "IA_Segunda_Entrega" / "datasets" / "calibro_imagenes"
if ejemplos_dir.exists():
    imgs = list(ejemplos_dir.glob("*.png"))[:6] + list(ejemplos_dir.glob("*.jpeg"))[:6]
    cols = st.columns(min(6, len(imgs)))
    for i, ej in enumerate(imgs[:6]):
        with cols[i]:
            try:
                st.image(str(ej), caption=ej.stem[:20], use_column_width=True)
            except Exception:
                pass
