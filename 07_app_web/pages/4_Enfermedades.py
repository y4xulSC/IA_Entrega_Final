"""Detector de enfermedades — sube imagen y la CNN clasifica.

El resultado no se queda en esta pantalla: ``registrar_diagnostico`` lo guarda
en el contexto compartido, actualiza ``st.session_state["riesgo_fitosanitario"]``
y lo envía al repositorio que alimenta las alertas del agrónomo. El botón
«¿Qué hago con este resultado?» lleva el diagnóstico al asistente RAG, y la
barra 👍/👎 mide el KPI «Nivel de confianza aceptada».

Grad-CAM (``cofitech/vision.py``) muestra en qué zona de la hoja se fijó la
CNN. Para la roya, la orientación de manejo depende de la incidencia medida en
el lote (``cofitech/prescripcion.py``): nunca de la confianza de una foto y
nunca con dosis escritas en el código.
"""
import hashlib
import pandas as pd
import streamlit as st
from pathlib import Path
from PIL import Image
import io

from cofitech.contexto_finca import (
    CLASE_SANO, NOMBRES_CLASE, UMBRAL_ROYA_ALTO, obtener_contexto, registrar_diagnostico,
    registrar_incidencia_lote, riesgo_fitosanitario,
)
from cofitech import prescripcion, repositorio, vision
from cofitech.telemetria import barra_valoracion, cronometro, registrar_evento_uso

CLAVE_PREGUNTA_PENDIENTE = "rag_pregunta_pendiente"   # la lee pages/5_Chatbot.py

st.set_page_config(page_title="Enfermedades", page_icon="📷", layout="wide")
st.title("📷 Detector de Enfermedades del Café")

PROJECT = Path(__file__).resolve().parents[2]
DIR_MOD = PROJECT / "04_modelos_entrenados"

st.markdown("""
Toma o sube una foto de una hoja de café. La CNN distingue **roya, gotera,
mancha de hierro (Cercospora), Phoma, minador, araña roja y hoja sana**, y el
mapa Grad-CAM muestra en qué parte de la hoja se fijó para decidir.
""")

# Cargar modelo
@st.cache_resource
def cargar_modelo():
    try:
        import tensorflow as tf
    except ImportError:
        st.error(" [ERROR] TensorFlow no está instalado en este entorno.")
        return None, None

    modelo_path = DIR_MOD / "cnn_cafe_best.keras"
    if not modelo_path.exists():
        st.error(f"  [ERROR] Modelo no encontrado en `{modelo_path}`.")
        return None, None
    
    try:
        m = tf.keras.models.load_model(modelo_path, compile=False)
        return m, modelo_path.name
    except Exception as e:
        st.error(f"  [ERROR] Error al cargar el modelo: {e}")
        return None, None

modelo, nombre_modelo = cargar_modelo()

# Upload
_CLAVE_RESULTADOS = "cofitech_resultados_vision"   # huella de la foto -> Resultado (evita recalcular)


def _diagnosticar(contenido: bytes, huella: str) -> tuple[vision.Resultado, dict[str, float]]:
    cache: dict = st.session_state.setdefault(_CLAVE_RESULTADOS, {})
    if huella not in cache:
        with cronometro() as tiempo:
            resultado = vision.diagnosticar(modelo, Image.open(io.BytesIO(contenido)))
        cache.clear()                                   # solo se guarda la foto actual
        cache[huella] = (resultado, tiempo)
    return cache[huella]


archivo = st.file_uploader("Selecciona o toma una foto de la hoja", type=["jpg", "jpeg", "png"])

if archivo and modelo is None:
    st.warning("⚠ Modelo CNN no encontrado en `04_modelos_entrenados/`. Ejecuta el notebook NB08 primero.")
elif archivo:
    contenido = archivo.getvalue()
    huella = hashlib.sha1(contenido).hexdigest()
    try:
        resultado, tiempo = _diagnosticar(contenido, huella)
    except Exception as e:                              # imagen dañada o modelo incompatible
        st.error(f"No se pudo analizar la imagen: {e}")
        st.stop()

    clase, conf = resultado.clase, resultado.confianza
    nombre_comun = NOMBRES_CLASE.get(clase, (clase, ""))[0]

    # Conexión con el resto de la app (barra global, riesgo, alertas del agrónomo).
    previo = obtener_contexto().diagnostico
    actual = registrar_diagnostico(clase=clase, confianza=min(max(conf, 0.0), 1.0), modelo=nombre_modelo, huella=huella)
    if actual is not previo:
        registrar_evento_uso("Visión", "diagnostico_ejecutado", {
            "modelo": nombre_modelo, "enfermedad": clase, "confianza": round(conf, 4),
            "gradcam": resultado.mapa is not None, **tiempo})
        st.rerun()      # foto nueva: refresca la barra global con el diagnóstico
    riesgo = riesgo_fitosanitario()

    # Tarjeta de resultado
    with st.container(border=True):
        st.subheader(nombre_comun.capitalize(), anchor=False)
        st.caption(f"Certeza del modelo: {conf:.0%}")
        col_foto, col_mapa = st.columns(2)
        col_foto.image(Image.open(io.BytesIO(contenido)), caption="Tu foto", use_container_width=True)
        if resultado.superpuesta is not None:
            col_mapa.image(resultado.superpuesta, caption="Dónde se fijó el modelo (rojo = más atención)",
                           use_container_width=True)
        segundos = f"{tiempo['tiempo_respuesta_s']:.1f}".replace(".", ",")
        st.caption(f"Modelo `{nombre_modelo}` · análisis en {segundos} s. "
                   "Si el rojo cae fuera de la mancha, toma otra foto más cerca y con buena luz.")
        with st.expander("Probabilidad de cada clase"):
            df_p = pd.DataFrame({"Clase": [NOMBRES_CLASE.get(c, (c, ""))[0] for c in resultado.probabilidades],
                                 "Probabilidad": list(resultado.probabilidades.values())}
                                ).sort_values("Probabilidad", ascending=False)
            st.dataframe(df_p, hide_index=True, width="stretch",
                         column_config={"Probabilidad": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})

    # KPI de modelo: ¿el caficultor acepta el diagnóstico?
    barra_valoracion(
        clave=actual.id,
        pregunta="¿El diagnóstico coincide con lo que ves en tu cultivo?",
        herramienta="Visión", accion="validacion_diagnostico", campo="confianza_aceptada",
        metadata={"enfermedad": clase, "confianza": round(conf, 4), "modelo": nombre_modelo},
        al_votar=lambda coincide, ident=actual.id: repositorio.registrar_feedback(ident, coincide))

    if riesgo == "Alto":
        st.error(f"Riesgo fitosanitario de la sesión: **Alto** (roya con certeza de {UMBRAL_ROYA_ALTO:.0%} o más "
                 "en alguna hoja). La proyección de cosecha e ingreso ya lo tiene en cuenta.")
    elif riesgo:
        st.info(f"Riesgo fitosanitario de la sesión: **{riesgo}**.")

    # Orientación de manejo
    if clase == "Roya":
        st.subheader("¿Qué hago con la roya?")
        ctx = obtener_contexto()
        sin_medir = st.toggle("Todavía no he medido la incidencia en el lote",
                              value=ctx.muestreo.incidencia_lote_pct is None)
        if sin_medir:
            registrar_incidencia_lote(None)
        else:
            pct = st.number_input("De cada 100 hojas revisadas en el lote, ¿cuántas tienen roya? (%)",
                                  min_value=0.0, max_value=100.0, step=0.5,
                                  value=float(ctx.muestreo.incidencia_lote_pct or 0.0))
            registrar_incidencia_lote(pct)
        prescripcion.mostrar(prescripcion.recomendacion_roya(
            obtener_contexto().muestreo.incidencia_lote_pct, ctx.finca.resistente_roya))
    elif clase == CLASE_SANO:
        st.success("✓ Hoja sana: mantén las prácticas de manejo y sigue revisando el lote.")
    elif clase == "Gotera":
        st.warning("Posible gotera: favorecen la humedad y la poca aireación. Regula la sombra y poda para "
                   "ventilar; pregúntale al asistente por el manejo. " + prescripcion.FUENTE)
    else:
        st.warning(f"Posible {nombre_comun}: consulta el manejo con el asistente o con el extensionista del "
                   "Comité de Cafeteros.")

    if clase != CLASE_SANO and st.button("¿Qué hago con este resultado?", type="primary", icon=":material/forum:"):
        st.session_state[CLAVE_PREGUNTA_PENDIENTE] = {
            "pregunta": f"Mi hoja salió con {nombre_comun}. ¿Qué hago?", "origen": "boton_que_hago"}
        st.switch_page("pages/5_Chatbot.py")
else:
    st.info("👆 Sube una imagen para empezar")

# Galería de ejemplos
st.markdown("---")
st.subheader("📸 Ejemplos del dataset CALIBRO (2da entrega)")
ejemplos_dir = PROJECT / "01_datos" / "imagenes_cafe" / "val" / "Gotera"
if ejemplos_dir.exists():
    imgs = list(ejemplos_dir.glob("*.png"))[:6] + list(ejemplos_dir.glob("*.jpeg"))[:6]
    cols = st.columns(min(6, len(imgs)))
    for i, ej in enumerate(imgs[:6]):
        with cols[i]:
            try:
                # st.image(str(ej), caption=ej.stem[:20], use_column_width=True)
                st.image(str(ej), caption=ej.stem[:20], use_container_width=True)
            except Exception:
                pass
