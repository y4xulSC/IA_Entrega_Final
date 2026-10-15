"""Chatbot RAG — interfaz conversacional sobre el sistema IA Café.

Conectado con el resto de la app:
  · Cada pregunta lleva el contexto de la sesión (finca, diagnóstico, estado
    fenológico) generado por ``prefijo_rag``; la búsqueda en ChromaDB recibe
    además el nombre de la enfermedad diagnosticada.
  · El botón «¿Qué hago con este resultado?» de Visión deja una pregunta
    pendiente que se responde apenas se abre esta pantalla.
  · Cada respuesta se registra en la telemetría y trae la valoración 👍/👎
    (KPI «Tasa de resolución del agente RAG»).
"""
import streamlit as st
from pathlib import Path
from uuid import uuid4
import sys

from cofitech.contexto_finca import CLASE_SANO, NOMBRES_CLASE, obtener_contexto, prefijo_rag
from cofitech.telemetria import barra_valoracion, cronometro, registrar_evento_uso

st.set_page_config(page_title="Asistente IA Café", page_icon="🤖", layout="wide")
st.title("🤖 Asistente Conversacional — Sistema IA Café")

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "06_agente_rag"))

CLAVE_PENDIENTE = "rag_pregunta_pendiente"     # la deja pages/4_Enfermedades.py

st.markdown("""
Pregunta al sistema sobre clima, precios, enfermedades, modelos, datos integrados, etc.
El asistente usa **RAG (Retrieval Augmented Generation)** con embeddings locales y un LLM gratis.
""")

# Cargar agente
@st.cache_resource
def cargar_agente():
    try:
        from rag_pipeline import RAGAgent
        agente = RAGAgent()
        return agente, None
    except Exception as e:
        return None, str(e)

agente, err = cargar_agente()

if err:
    st.error(f"⚠ No se pudo cargar el agente RAG: {err}")
    st.markdown("""
    **Para activar el chatbot:**
    ```bash
    pip install langchain langchain-community langchain-groq sentence-transformers chromadb
    export GROQ_API_KEY=gsk_xxxx  # https://console.groq.com (gratis)
    cd 06_agente_rag
    python rag_pipeline.py indexar
    ```
    """)
    st.stop()

# Verificar índice
try:
    vs = agente._get_vectorstore()
    n_docs = vs._collection.count()
    st.caption(f"Índice: {n_docs} chunks vectorizados")
    if n_docs == 0:
        if st.button("📥 Indexar documentos demo"):
            with st.spinner("Indexando..."):
                agente.indexar()
            st.rerun()
        st.stop()
except Exception as e:
    st.warning(f"No se pudo verificar el índice: {e}")

ctx = obtener_contexto()
contexto_usuario = prefijo_rag(ctx)
with st.expander("Lo que el asistente sabe de tu caso"):
    st.text(contexto_usuario)


def responder(pregunta: str, origen: str) -> None:
    """Consulta al agente con el contexto de la sesión y registra la telemetría."""
    diag = ctx.diagnostico
    termino = NOMBRES_CLASE.get(diag.clase, ("", ""))[1] if diag and diag.clase != CLASE_SANO else None
    st.session_state.messages.append({"role": "user", "content": pregunta})
    with cronometro() as tiempo:
        try:
            r = agente.consultar(pregunta, contexto_usuario=contexto_usuario, termino_busqueda=termino)
            texto = r.texto
            meta = {"modelo": r.modelo, "n_fuentes": len(r.fuentes), "fuentes_validadas": len(r.fuentes_validadas),
                    "salvaguardas": r.salvaguardas, "error": r.error}
        except Exception as e:
            texto, meta = f"Error: {e}", {"modelo": getattr(agente, "llm_model", None), "error": True}
    id_respuesta = uuid4().hex[:12]
    st.session_state.messages.append({"role": "assistant", "content": texto, "id": id_respuesta, "meta": meta})
    registrar_evento_uso("RAG", "pregunta_enviada", {
        **meta, **tiempo, "origen": origen, "id_respuesta": id_respuesta,
        "con_diagnostico": diag is not None, "enfermedad": diag.clase if diag else None})


# Estado de la conversación
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content":
         "¡Hola! Soy el asistente del Sistema IA Café. Pregúntame sobre el proyecto, "
         "los modelos, los datos integrados o aspectos agronómicos del café colombiano. "
         "Por ejemplo: *¿Qué efecto tiene El Niño sobre el rendimiento?*"}
    ]

# Pregunta nueva: la escrita en el chat, la que dejó Visión o una sugerida.
nueva = st.chat_input("Escribe tu pregunta...")
pendiente = st.session_state.pop(CLAVE_PENDIENTE, None)
if nueva:
    pendiente = {"pregunta": nueva, "origen": "chat"}
if pendiente:
    with st.spinner("Buscando contexto y generando respuesta..."):
        responder(pendiente["pregunta"], pendiente["origen"])

# Mostrar historia, con la valoración bajo cada respuesta
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant" and m.get("id") and not m.get("meta", {}).get("error"):
            barra_valoracion(
                clave=m["id"], pregunta="¿Te fue útil esta recomendación?",
                herramienta="RAG", accion="feedback_respuesta", campo="util",
                metadata={"id_respuesta": m["id"], "modelo": m["meta"].get("modelo"),
                          "salvaguardas": m["meta"].get("salvaguardas", [])},
                etiqueta_si="👍", etiqueta_no="👎")


def _sugerir(texto: str) -> None:
    st.session_state[CLAVE_PENDIENTE] = {"pregunta": texto, "origen": "sugerida"}


# Sugerencias
st.markdown("---")
st.subheader("💡 Preguntas sugeridas")
sugerencias = [
    "¿Qué efecto tiene El Niño sobre el rendimiento del café?",
    "¿Cuáles son las variedades de café resistentes a la Roya?",
    "¿Por qué el precio del café subió tanto en 2024?",
    "¿Cuál modelo predice mejor el precio interno?",
    "¿Qué es Grad-CAM y por qué es útil?",
    "¿Qué métricas tuvo la CNN en la segunda entrega?",
]
cols = st.columns(2)
for i, s in enumerate(sugerencias):
    with cols[i % 2]:
        st.button(s, key=f"sug_{i}", use_container_width=True, on_click=_sugerir, args=(s,))
