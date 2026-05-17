# Agente RAG — Sistema IA Café

Cubre **Unidad IV — PLN/Transformers** del syllabus.

## Stack
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (multilingüe, gratis, local)
- **Vector store:** ChromaDB (persistencia local, sin servidor)
- **LLM:** Groq (gratis con API key) o Ollama local (sin internet)
- **Orquestación:** LangChain

## Instalación

```bash
pip install langchain langchain-community langchain-groq sentence-transformers langchain-text-splitters
pip install chromadb pypdf unstructured
```

### Configurar LLM

**Opción A — Groq (recomendada, gratis):**
1. Crear cuenta en https://console.groq.com
2. Generar API key
3. Exportar:
   ```bash
   export GROQ_API_KEY=gsk_xxxxx
   ```

**Opción B — Ollama local (sin internet, más lento):**
1. Instalar: https://ollama.com/download
2. Bajar modelo: `ollama pull llama3.1:8b`
3. (Opcional) `export OLLAMA_HOST=http://localhost:11434`

## Uso

### Vía CLI
```bash
# Primera vez — indexa documentos en documentos_fuente/
python rag_pipeline.py indexar

# Hacer una pregunta
python rag_pipeline.py preguntar -p "¿Qué efecto tiene El Niño sobre el café?"
python rag_pipeline.py preguntar -p "Qué R² alcanzó el BiGRU en pronóstico de precios"
python rag_pipeline.py preguntar -p "Cómo controlo la antracnosis en mi cafetal"
python rag_pipeline.py preguntar -p "Qué variedades sembrar en Rionegro Antioquia"
python rag_pipeline.py preguntar -p "Qué pasó con el café durante El Niño 2015"
python rag_pipeline.py preguntar -p "Necesito GPU para correr el sistema"

# Modo demo — 5 preguntas guionizadas
python rag_pipeline.py demo
```

### Vía Python
```python
from rag_pipeline import RAGAgent

agente = RAGAgent()
agente.indexar()  # primera vez
respuesta = agente.preguntar("¿Cuál variedad de café es resistente a la Roya?")
print(respuesta)
```

## Documentos a indexar

Coloca cualquiera de estos formatos en `documentos_fuente/`:
- PDFs de la 1ra y 2da entrega
- Documento académico final
- Papers de Cenicafé
- Boletines FNC
- CSVs con datos integrados (resumen anual)
- Notebook outputs en MD

Si la carpeta está vacía, el pipeline crea un archivo demo con conocimiento base.

## Preguntas de demostración (script presentación)

Para la presentación final, estas 5 preguntas funcionan bien:

1. *"¿Qué pasa con el rendimiento del café si hay El Niño en Huila?"*
2. *"¿Cuáles son las variedades de café resistentes a la Roya?"*
3. *"¿Por qué el precio del café subió tanto en 2024?"*
4. *"¿Cuál es el modelo que predice mejor el precio interno?"*
5. *"¿Qué métricas tuvo la CNN en la segunda entrega?"*

## Arquitectura RAG

```
Pregunta usuario
       ↓
Embedding (MiniLM)
       ↓
Búsqueda similitud en Chroma  ──→  Top-k chunks relevantes
       ↓
Prompt = pregunta + contexto
       ↓
LLM (Groq llama-3.1-70b)
       ↓
Respuesta con citas
```

## Cobertura del syllabus

- Embeddings: representación vectorial de palabras (Unidad IV — PLN)
- Transformers: el LLM Llama-3.1 internamente es un transformer
- RAG: arquitectura Retrieval Augmented Generation (estado del arte 2024)
- Aplicación: asistencia conversacional al MADR/FNC
