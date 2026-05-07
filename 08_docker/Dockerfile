# ════════════════════════════════════════════════════════════════════════════
# Sistema IA Café — Streamlit App
# Multi-stage build para reducir tamaño final
# ════════════════════════════════════════════════════════════════════════════

# ───── Stage 1: builder con dependencias ─────
FROM python:3.10-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY 07_app_web/requirements.txt /build/requirements.txt

RUN pip install --no-cache-dir --upgrade pip wheel \
 && pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# ───── Stage 2: runtime ─────
FROM python:3.10-slim

WORKDIR /app

# Dependencias mínimas runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Wheels precompiladas
COPY --from=builder /wheels /wheels
COPY 07_app_web/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# App + modelos + datos minimos
COPY 07_app_web/        /app/07_app_web/
COPY 06_agente_rag/     /app/06_agente_rag/
COPY 04_modelos_entrenados/ /app/04_modelos_entrenados/
COPY 05_resultados/     /app/05_resultados/
COPY 01_datos/procesados/   /app/01_datos/procesados/
# Datos originales (subset, no las imágenes)
COPY 01_datos/originales/ /app/01_datos/originales/

# Streamlit healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl --silent --fail http://localhost:8501/_stcore/health || exit 1

EXPOSE 8501

# Configuración Streamlit
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    PYTHONUNBUFFERED=1

CMD ["streamlit", "run", "/app/07_app_web/app.py"]
