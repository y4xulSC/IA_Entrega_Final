"""
═══════════════════════════════════════════════════════════════════════════════
 rag_pipeline.py · Agente RAG sobre el sistema IA Café
═══════════════════════════════════════════════════════════════════════════════
 Cubre Unidad IV — PLN/Transformers:
   - Embeddings (representación vectorial de palabras/documentos)
   - Recuperación con vector store (ChromaDB)
   - Generación con LLM (Groq gratis o Ollama local)
   - Re-ranking opcional con cross-encoder

 Dependencias:
   pip install langchain langchain-community langchain-groq sentence-transformers
   pip install chromadb pypdf unstructured

 Variables de entorno:
   GROQ_API_KEY  (opcional, gratis en https://console.groq.com)
   OLLAMA_HOST   (opcional, default http://localhost:11434 si Ollama corre local)

 Uso programático:
   from rag_pipeline import RAGAgent
   agente = RAGAgent()
   agente.indexar()                       # primera vez
   resp = agente.preguntar('Qué pasa con el rendimiento si hay El Niño en Huila?')
   print(resp)
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# rutas
HERE = Path(__file__).resolve()
PROJECT = HERE.parents[1]
DOCS_DIR = HERE.parent / "documentos_fuente"
VECTOR_DIR = HERE.parent / "vectorstore"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

class RAGAgent:
    """Agente RAG con backend local (sentence-transformers + ChromaDB) y LLM remoto/local."""

    def __init__(self,
                embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                llm_provider: str = "groq",
                # llm_model: str = "llama-3.3-70b-versatile", # Modelo grande
                llm_model: str = "llama-3.1-8b-instant", # Modelo recomendado para pruebas locales (Ollama) o Groq gratis
                collection_name: str = "cafe_ia"):
        self.embedding_model_name = embedding_model
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.collection_name = collection_name
        self._vectorstore = None
        self._llm = None

    # embeddings
    def _get_embeddings(self):
        #from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name=self.embedding_model_name,
            model_kwargs={"device": "cpu"},
        )

    # vector store
    def _get_vectorstore(self):
        if self._vectorstore is not None:
            return self._vectorstore
        #from langchain_community.vectorstores import Chroma
        from langchain_chroma import Chroma
        self._vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self._get_embeddings(),
            persist_directory=str(VECTOR_DIR),
        )
        return self._vectorstore

    # LLM
    def _get_llm(self):
        if self._llm is not None:
            return self._llm
        if self.llm_provider == "groq":
            try:
                from langchain_groq import ChatGroq
                key = os.environ.get("GROQ_API_KEY")
                if not key:
                    print("[!] GROQ_API_KEY no definida — usando Ollama local")
                    return self._get_llm_ollama()
                print(f"[LLM] Conectando a Groq (Modelo: {self.llm_model})...")
                self._llm = ChatGroq(
                    api_key=key,
                    model_name=self.llm_model,
                    temperature=0.3, max_tokens=1024,
                )
                return self._llm
            except ImportError:
                print("pip install langchain-groq")
                return self._get_llm_ollama()
        return self._get_llm_ollama()

    def _get_llm_ollama(self):
        try:
            from langchain_community.llms import Ollama
            host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            print(f"[LLM] Conectando a Ollama local en {host}...")
            self._llm = Ollama(base_url=host, model="llama3.1:8b", temperature=0.3)
            return self._llm
        except Exception as e:
            print(f"[!] Ollama no disponible: {e}")
            return None

    # indexación
    def indexar(self, force: bool = False):
        """Indexa todos los documentos en documentos_fuente/."""
        from langchain_community.document_loaders import (
            PyPDFLoader, TextLoader, CSVLoader
        )
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        vs = self._get_vectorstore()
        count = vs._collection.count()
        if not force and count > 0:
            print(f"[indexar] Ya hay {count} chunks indexados en ChromaDB.")
            print("           Usa force=True para reindexar.")
            return

        documentos = []
        for archivo in DOCS_DIR.rglob("*"):
            if not archivo.is_file():
                continue
            suf = archivo.suffix.lower()
            try:
                if suf == ".pdf":
                    docs = PyPDFLoader(str(archivo)).load()
                elif suf in (".md", ".markdown", ".txt", ""):
                    docs = TextLoader(str(archivo), encoding="utf-8").load()
                elif suf == ".csv":
                    docs = CSVLoader(str(archivo)).load()
                else:
                    continue
                for d in docs:
                    d.metadata["origen"] = str(archivo.relative_to(DOCS_DIR))
                documentos.extend(docs)
                print(f"   [OK] {archivo.name}: {len(docs)} chunks")
            except Exception as e:
                print(f"   [FAIL] {archivo.name}: {e}")

        if not documentos:
            print("\n[!] Sin documentos. Coloca PDFs/MD/TXT en documentos_fuente/")
            self._cargar_documentos_demo()
            return

        # Chunking
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=120,
            separators=["\n\n", "\n", ". ", " "],
        )
        chunks = splitter.split_documents(documentos)
        print(f"\n   total chunks: {len(chunks)}")

        vs.add_documents(chunks)
        print(f"  [OK] {len(chunks)} chunks indexados en {VECTOR_DIR}")

    def _cargar_documentos_demo(self):
        """Crea documentos de demo si no hay nada en documentos_fuente."""
        demo_path = DOCS_DIR / "conocimiento_cafe_demo.md"
        demo_path.write_text(_TEXTO_DEMO, encoding="utf-8")
        print(f"   → Demo creado: {demo_path}")
        self.indexar(force=True)

    # consulta
    def preguntar(self, pregunta: str, k: int = 4) -> str:
        # from langchain.prompts import PromptTemplate
        # from langchain.prompts import ChatPromptTemplate
        # from langchain.schema.runnable import RunnablePassthrough
        # from langchain.schema.output_parser import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.runnables import RunnablePassthrough
        from langchain_core.output_parsers import StrOutputParser

        vs = self._get_vectorstore()
        llm = self._get_llm()

        docs = vs.similarity_search(pregunta, k=k)
        contexto = "\n\n".join([f"[{d.metadata.get('origen','?')}]\n{d.page_content}"
                                for d in docs])
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Eres un asistente experto en café colombiano. Responde EN ESPAÑOL "
                       "de forma concisa y técnica. "
                       "Utiliza ÚNICAMENTE el contexto proporcionado para responder. "
                       "Si la respuesta no está en el contexto, di que no tienes información suficiente. "
                       "Siempre menciona la [Fuente] al final de tu respuesta basándote en el contexto.\n\n"
                       "CONTEXTO RECUPERADO:\n{contexto}"),
            ("human", "{pregunta}")
        ])
        if llm is None:
            # Fallback: solo recuperación
            return ("[Sin LLM disponible — solo retrieval]\n" +
                    f"\nFragmentos relevantes:\n\n{contexto[:2000]}")

        chain = ({"contexto": lambda x: contexto, "pregunta": RunnablePassthrough()} | prompt | llm | StrOutputParser())
        try:
            respuesta = chain.invoke(pregunta)
            return respuesta
        except Exception as e:
            return f"Error: {e}"


# texto demo
_TEXTO_DEMO = """# Conocimiento base · Sistema IA Café Colombia

## El Niño y rendimiento

En el contexto del análisis realizado en la 2da entrega del proyecto,
se observó que el fenómeno El Niño reduce el rendimiento del café en
aproximadamente **24%** respecto a la fase Neutro (de 1.037 ton/ha a
0.788 ton/ha), con diferencias estadísticamente significativas según
el test de Kruskal-Wallis (p < 0.05).

La Niña tiene un efecto menor: reduce el rendimiento en aproximadamente
12% (a 0.910 ton/ha).

Esto se debe a que El Niño causa déficit hídrico y aumento de
temperatura — condiciones desfavorables para el café arábica que prefiere
1500-2000 mm de precipitación anual y temperaturas entre 18-22°C.

## Roya del café

La Roya (Hemileia vastatrix) es la enfermedad más importante del café
en Colombia. Síntomas:
- Manchas amarillentas en envés de hojas
- Polvillo color naranja-amarillo
- Caída prematura de hojas

Variedades resistentes a la roya en Colombia: Castillo, Colombia,
Cenicafé 1, Tabi. Variedades susceptibles: Caturra, Bourbon, Típica.

Sin manejo, la roya puede causar pérdidas del 40% de la producción.

## Departamentos cafeteros principales

1. **Huila** — productor #1 desde 2010 (~150K ton/año)
2. **Antioquia** — segundo productor (~110K ton/año)
3. **Nariño** — café especial alta altitud (~70K ton/año)
4. **Tolima**, **Caldas**, **Quindío**, **Risaralda**, **Cauca** —
   forman el Eje Cafetero clásico.

## Precio interno (FNC) y precio externo (ICO)

El precio FNC para carga de 125 kg sigue de cerca al precio ICO Composite
en USD/lb con correlación r=0.97 (modelado en NB05 con Ridge regression
que alcanza R²=0.945, MAPE=4.3%).

El surge 2024-2025 (precio interno superando 3,200,000 COP) se explica por:
1. Sequía en Brasil (super productor mundial) durante 2024
2. Devaluación del peso colombiano (TRM superando 4,200 COP/USD)
3. Aumento de la demanda mundial post-pandemia

## Modelos del sistema

Notebook | Modelo | Métrica | Estado
--- | --- | --- | ---
NB02 | Stacking RF+XGB+LGB | R²=0.067 (departamental) | mejorado en NB09
NB05 | Ridge precio | R²=0.945 | excelente
NB06 | BiGRU forecasting | R²=−2.12 | mejorado en NB10
NB03 | EfficientNetB0 CNN | Acc=48.9% | mejorado en NB08

NB07-NB12 son la entrega final con datos ampliados.
"""


# CLI
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("comando", choices=["indexar", "preguntar", "demo"])
    parser.add_argument("--pregunta", "-p", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    agent = RAGAgent()

    if args.comando == "indexar":
        agent.indexar(force=args.force)
    elif args.comando == "preguntar":
        if not args.pregunta:
            print("Falta --pregunta")
            return
        print(agent.preguntar(args.pregunta))
    elif args.comando == "demo":
        agent.indexar()
        preguntas_demo = [
            "¿Qué efecto tiene El Niño sobre el rendimiento del café?",
            "¿Cuáles son las variedades resistentes a la Roya en Colombia?",
            "¿Por qué el precio del café subió tanto en 2024?",
            "¿Cuál es el departamento con mayor producción de café en Colombia?",
            "¿Qué modelo predice mejor el precio interno?",
        ]
        for q in preguntas_demo:
            print("\n" + "─"*70)
            print(f"Q: {q}")
            print("─"*70)
            try:
                print(agent.preguntar(q))
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    main()
