"""
Modulo comun: carga .env, configura logging a archivo + consola,
expone PG_CONFIG y rutas absolutas. Reutilizado por 02_carga_inicial.py
y validar_pre_carga.py.
"""
from __future__ import annotations
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve()
PROJECT = HERE.parents[2]

# Carga .env si existe (sin requerir python-dotenv)
def _cargar_dotenv(env_path: Path):
    if not env_path.exists():
        return
    for linea in env_path.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, _, v = linea.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        # No sobrescribir si ya esta en el entorno (precedencia: env real > .env)
        os.environ.setdefault(k, v)

_cargar_dotenv(PROJECT / ".env")

# PostgreSQL
PG_CONFIG = {
    "host":     os.environ.get("PG_HOST", "localhost"),
    "port":     int(os.environ.get("PG_PORT", "5432")),
    "user":     os.environ.get("PG_USER", "postgres"),
    "password": os.environ.get("PG_PASSWORD", "root"),
    "dbname":   os.environ.get("PG_DB", "cafe_ia"),
}

# Rutas
DIR_DATOS = PROJECT / "01_datos"
DIR_PROC = DIR_DATOS / "procesados"
DIR_ENRIQ = DIR_DATOS / "enriquecidos"
DIR_LOGS = PROJECT / os.environ.get("LOG_DIR", "05_resultados/logs")
DIR_LOGS.mkdir(parents=True, exist_ok=True)


# Logger configurado: consola + archivo
def get_logger(nombre: str) -> logging.Logger:
    """
    Logger que escribe a consola Y a un archivo
    05_resultados/logs/<nombre>_<YYYYMMDD_HHMMSS>.log
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = DIR_LOGS / f"{nombre}_{timestamp}.log"

    logger = logging.getLogger(nombre)
    logger.setLevel(log_level)
    logger.handlers.clear()  # idempotente

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(message)s",
        datefmt="%H:%M:%S")

    # Consola
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Archivo
    try:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.info(f"Log file: {log_path.relative_to(PROJECT)}")
    except Exception as e:
        logger.warning(f"No se pudo crear log file: {e}")

    return logger


# Helper de conexion
def conectar():
    """Devuelve conexion psycopg2; lanza ConnectionError descriptivo si falla."""
    try:
        import psycopg2
    except ImportError:
        raise ImportError("Falta psycopg2: pip install psycopg2-binary")

    try:
        conn = psycopg2.connect(**PG_CONFIG)
        return conn
    except Exception as e:
        raise ConnectionError(
            f"No se pudo conectar a {PG_CONFIG['user']}@{PG_CONFIG['host']}:"
            f"{PG_CONFIG['port']}/{PG_CONFIG['dbname']}: {e}\n"
            f"  Verifica que PostgreSQL este corriendo y que .env tenga las "
            f"credenciales correctas (copia .env.example a .env)."
        ) from e
