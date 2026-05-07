# Docker · Sistema IA Café

## Estructura

```
08_docker/
├── Dockerfile                # Imagen Streamlit + modelos
├── docker-compose.yml        # Orquesta DB + App
├── .dockerignore             # Excluye imágenes pesadas
└── README.md                 # Este archivo
```

## Levantar todo el sistema (recomendado)

```bash
cd IA_Entrega_Final/08_docker

# Opcional: configurar API key del LLM
echo "GROQ_API_KEY=gsk_xxx" > .env

# Build + up
docker compose up -d --build

# Ver logs
docker compose logs -f app

# Detener
docker compose down

# Detener y eliminar volúmenes (perder datos)
docker compose down -v
```

Acceder: http://localhost:8501

## Solo la app (sin Postgres en Docker, conexión a Postgres del host)

```bash
docker build -f Dockerfile -t cafe-ia ..
docker run -p 8501:8501 \
    -e PG_HOST=host.docker.internal \
    -e PG_USER=postgres \
    -e PG_PASSWORD=root \
    -e PG_DB=cafe_ia \
    cafe-ia
```

## Deploy gratis en HuggingFace Spaces

1. Crear Space tipo "Docker": https://huggingface.co/new-space
2. Subir el código de `IA_Entrega_Final/`
3. Crear `Dockerfile` en raíz que apunte a `07_app_web/app.py`
4. Variables secretas: `GROQ_API_KEY` en Settings → Secrets
5. Build automático

## Deploy gratis en Streamlit Cloud

1. Subir repo a GitHub
2. https://streamlit.io/cloud → New App
3. Path: `07_app_web/app.py`
4. Requirements: `07_app_web/requirements.txt`
5. Secrets en `[secrets]` Settings:
   ```toml
   GROQ_API_KEY = "gsk_xxx"
   PG_HOST = "..."  # opcional
   ```

## Tamaño esperado de imagen

- Sin TensorFlow: ~600MB
- Con TensorFlow CPU: ~1.8GB
- Con TensorFlow + CUDA: ~4GB+ (no recomendado para deploy gratis)

Para reducir: comentar TensorFlow en `requirements.txt` y servir solo
los .pkl (sklearn). Las predicciones de CNN se pueden cargar como ONNX
en runtime ligero.
