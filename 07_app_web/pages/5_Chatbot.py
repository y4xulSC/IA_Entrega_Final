"""Chatbot RAG — interfaz conversacional sobre el sistema IA Café."""
import streamlit as st
from pathlib import Path
import sys

st.set_page_config(page_title="Asistente IA Café", page_icon="🤖", layout="wide")
st.title("🤖 Asistente Conversacional — Sistema IA Café")

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "06_agente_rag"))

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

# Estado de la conversación
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content":
         "¡Hola! Soy el asistente del Sistema IA Café. Pregúntame sobre el proyecto, "
         "los modelos, los datos integrados o aspectos agronómicos del café colombiano. "
         "Por ejemplo: *¿Qué efecto tiene El Niño sobre el rendimiento?*"}
    ]

# Mostrar historia
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Input
if pregunta := st.chat_input("Escribe tu pregunta..."):
    st.session_state.messages.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Buscando contexto y generando respuesta..."):
            try:
                respuesta = agente.preguntar(pregunta)
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
            except Exception as e:
                st.error(f"Error: {e}")

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
        if st.button(s, key=f"sug_{i}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": s})
            try:
                resp = agente.preguntar(s)
                st.session_state.messages.append({"role": "assistant", "content": resp})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})
            st.rerun()
