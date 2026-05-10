"""
═══════════════════════════════════════════════════════════════════════════════
 _config.py — carga credenciales desde .env y expone constantes comunes
═══════════════════════════════════════════════════════════════════════════════
 Uso desde cualquier script de la carpeta:
    from _config import FRED_API_KEY, SOCRATA_APP_TOKEN, KAGGLE_API_TOKEN, UA
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations
from pathlib import Path
import os

HERE = Path(__file__).resolve().parent

# ── Cargar .env si existe ───────────────────────────────────────────────────
def _load_env(path: Path) -> None:
    """Mini-loader para .env sin requerir python-dotenv (compat máxima)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        # No sobrescribir variables ya seteadas en el sistema
        if key and key not in os.environ:
            os.environ[key] = val


_load_env(HERE / ".env")

# Si el usuario tiene python-dotenv, también úsalo (cubre casos como
# variables con caracteres especiales que el mini-loader no parsea).
try:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env", override=False)
except ImportError:
    pass


# ── Credenciales públicas via os.getenv ─────────────────────────────────────
FRED_API_KEY        = os.getenv("FRED_API_KEY", "")
SOCRATA_APP_TOKEN   = os.getenv("SOCRATA_APP_TOKEN", "")
SOCRATA_APP_SECRET  = os.getenv("SOCRATA_APP_SECRET", "")
KAGGLE_API_TOKEN    = os.getenv("KAGGLE_API_TOKEN", "")
KAGGLE_USERNAME     = os.getenv("KAGGLE_USERNAME", "")
KAGGLE_KEY          = os.getenv("KAGGLE_KEY", "")


# ── User-Agent común ────────────────────────────────────────────────────────
UA = {
    "User-Agent": "Mozilla/5.0 (UAO IA Cafe Project; +https://uao.edu.co)",
    "Accept": "*/*",
}


# ── Headers para datos.gov.co (Socrata) ─────────────────────────────────────
def socrata_headers() -> dict:
    h = dict(UA)
    if SOCRATA_APP_TOKEN:
        h["X-App-Token"] = SOCRATA_APP_TOKEN
    return h


# ── Configurar Kaggle CLI desde env (autocrea ~/.kaggle/kaggle.json si toca) ─
def setup_kaggle() -> bool:
    """
    Asegura que la librería kaggle pueda autenticar. Soporta:
      1. KAGGLE_API_TOKEN (formato nuevo KGAT_*) → ~/.kaggle/access_token
      2. KAGGLE_USERNAME + KAGGLE_KEY            → ~/.kaggle/kaggle.json
      3. ~/.kaggle/kaggle.json ya presente       → no toca
    Devuelve True si hay alguna credencial disponible.
    """
    home = Path.home()
    kdir = home / ".kaggle"
    kdir.mkdir(exist_ok=True)
    kjson = kdir / "kaggle.json"
    ktoken = kdir / "access_token"
    found = False

    # 1. Token nuevo (KGAT_*)
    if KAGGLE_API_TOKEN and KAGGLE_API_TOKEN.startswith("KGAT_"):
        try:
            ktoken.write_text(KAGGLE_API_TOKEN, encoding="utf-8")
            try:
                ktoken.chmod(0o600)
            except Exception:
                pass  # Windows
            os.environ["KAGGLE_API_TOKEN"] = KAGGLE_API_TOKEN
            found = True
        except Exception as e:
            print(f"   ⚠  no pude escribir {ktoken}: {e}")

    # 2. Formato clásico
    if KAGGLE_USERNAME and KAGGLE_KEY:
        import json as _json
        kjson.write_text(_json.dumps(
            {"username": KAGGLE_USERNAME, "key": KAGGLE_KEY}), encoding="utf-8")
        try:
            kjson.chmod(0o600)
        except Exception:
            pass
        os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME
        os.environ["KAGGLE_KEY"] = KAGGLE_KEY
        found = True

    # 3. Ya existe alguno
    if kjson.exists() or ktoken.exists():
        found = True

    return found


# ── Logging consistente ─────────────────────────────────────────────────────
def log_status() -> None:
    print(f"   FRED key       : {'sí' if FRED_API_KEY else '(no)'}")
    print(f"   Socrata token  : {'sí' if SOCRATA_APP_TOKEN else '(no)'}")
    print(f"   Kaggle token   : {'sí' if (KAGGLE_API_TOKEN or KAGGLE_USERNAME) else '(no)'}")


if __name__ == "__main__":
    log_status()
    setup_kaggle()
