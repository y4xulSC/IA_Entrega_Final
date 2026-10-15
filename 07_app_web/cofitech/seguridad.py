"""Acceso de administrador del sistema CofiTech.

El administrador es un permiso de la sesión, no un tercer rol: quien entra
como administrador sigue usando la app como Caficultor o como Agrónomo y,
además, ve la sección «Administración» (Telemetría y KPIs, Ficha técnica de
modelos) y el panel de depuración.

La contraseña no está en el código: se guarda solo su hash PBKDF2-SHA256 en
``COFITECH_ADMIN_HASH`` (``.streamlit/secrets.toml`` o ``.env``). Para
generarlo::

    python 07_app_web/cofitech/seguridad.py

Toda la app pregunta por ``es_admin()``. Para pasar a inicio de sesión con
Google (``st.login``) o Supabase Auth basta con cambiar esa función y
``iniciar_sesion``: las pantallas no se tocan.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

PROYECTO: Path = Path(__file__).resolve().parents[2]
RUTA_ACCESOS: Path = PROYECTO / "05_resultados" / "logs" / "accesos_admin.jsonl"
VARIABLE_HASH = "COFITECH_ADMIN_HASH"

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 600_000            # recomendación OWASP 2023 para PBKDF2-SHA256
LONGITUD_MINIMA = 10

# Límite de intentos: por sesión del navegador y, como recargar la página
# abre una sesión nueva, también para todo el servidor.
INTENTOS_POR_SESION = 5
INTENTOS_GLOBALES = 20
VENTANA_BLOQUEO_S = 60
VENTANA_GLOBAL_S = 300

_CLAVE_ADMIN = "cofitech_admin"
_CLAVE_FALLOS = "cofitech_admin_fallos"

log = logging.getLogger("cofitech.seguridad")
_candado = threading.Lock()
_fallos_globales: list[float] = []


# ─────────────────────────────── Hash ───────────────────────────────────────
def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


def _desde_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def generar_hash(contrasena: str, iteraciones: int = ITERACIONES) -> str:
    """``pbkdf2_sha256:<iteraciones>:<sal>:<hash>`` (sin ``$`` ni ``=``, seguro para ``.env``)."""
    sal = secrets.token_bytes(16)
    derivado = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), sal, iteraciones)
    return f"{ALGORITMO}:{iteraciones}:{_b64(sal)}:{_b64(derivado)}"


def verificar(contrasena: str, hash_guardado: str) -> bool:
    """Compara en tiempo constante. Un hash mal formado nunca da acceso."""
    try:
        algoritmo, iteraciones, sal, esperado = hash_guardado.strip().split(":")
        if algoritmo != ALGORITMO:
            return False
        derivado = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), _desde_b64(sal), int(iteraciones))
        return hmac.compare_digest(derivado, _desde_b64(esperado))
    except (ValueError, TypeError):
        return False


# ─────────────────────────── Configuración ──────────────────────────────────
def hash_configurado() -> Optional[str]:
    """El hash de ``secrets.toml``, de la variable de entorno o del ``.env``; ``None`` si no hay."""
    try:
        valor = st.secrets.get(VARIABLE_HASH)
        if valor:
            return str(valor)
    except Exception:          # sin secrets.toml
        pass
    if os.environ.get(VARIABLE_HASH):
        return os.environ[VARIABLE_HASH]
    ruta = PROYECTO / ".env"
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            clave, sep, valor = linea.strip().partition("=")
            if sep and clave.strip() == VARIABLE_HASH:
                return valor.strip().strip('"').strip("'") or None
    return None


def acceso_habilitado() -> bool:
    return hash_configurado() is not None


# ─────────────────────────────── Sesión ─────────────────────────────────────
def es_admin() -> bool:
    """¿La sesión actual tiene permiso de administrador? Único punto que consultan las pantallas."""
    return bool(st.session_state.get(_CLAVE_ADMIN, False))


def segundos_bloqueado() -> int:
    """Segundos que faltan para poder volver a intentar (0 = puede intentar)."""
    ahora = time.monotonic()
    fallos = [t for t in st.session_state.get(_CLAVE_FALLOS, []) if ahora - t < VENTANA_BLOQUEO_S]
    espera = 0.0
    if len(fallos) >= INTENTOS_POR_SESION:
        espera = VENTANA_BLOQUEO_S - (ahora - fallos[-INTENTOS_POR_SESION])
    with _candado:
        _fallos_globales[:] = [t for t in _fallos_globales if ahora - t < VENTANA_GLOBAL_S]
        if len(_fallos_globales) >= INTENTOS_GLOBALES:
            espera = max(espera, VENTANA_GLOBAL_S - (ahora - _fallos_globales[-INTENTOS_GLOBALES]))
    return max(0, int(espera + 0.999))


def iniciar_sesion(contrasena: str) -> tuple[bool, str]:
    """Valida la contraseña y activa el permiso de administrador en la sesión.

    Returns:
        ``(éxito, mensaje para mostrar)``. El mensaje nunca dice si falló por
        la contraseña o por la configuración, para no dar pistas.
    """
    hash_guardado = hash_configurado()
    if hash_guardado is None:
        return False, "El acceso de administrador no está configurado en este servidor."
    espera = segundos_bloqueado()
    if espera:
        return False, f"Demasiados intentos. Espera {espera} s."

    if verificar(contrasena, hash_guardado):
        st.session_state[_CLAVE_ADMIN] = True
        st.session_state[_CLAVE_FALLOS] = []
        _registrar("ingreso")
        return True, "Acceso de administrador activo."

    ahora = time.monotonic()
    st.session_state.setdefault(_CLAVE_FALLOS, []).append(ahora)
    with _candado:
        _fallos_globales.append(ahora)
    _registrar("intento_fallido")
    restantes = INTENTOS_POR_SESION - len(st.session_state[_CLAVE_FALLOS])
    if restantes <= 0:
        return False, f"Contraseña incorrecta. Espera {segundos_bloqueado()} s para volver a intentar."
    return False, f"Contraseña incorrecta. Te quedan {restantes} intento{'s' if restantes != 1 else ''}."


def cerrar_sesion() -> None:
    if es_admin():
        _registrar("salida")
    st.session_state[_CLAVE_ADMIN] = False


def exigir_admin() -> None:
    """Detiene la pantalla si la sesión no es de administrador (defensa adicional al menú)."""
    if not es_admin():
        st.error("Esta pantalla es solo para administradores del sistema.")
        st.stop()


def _registrar(evento: str) -> None:
    """Bitácora local de accesos (sin la contraseña ni datos personales)."""
    from cofitech import repositorio      # importación tardía: evita ciclos

    registro = {"timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
                "evento": evento, "id_sesion": repositorio.id_sesion()}
    (log.warning if evento == "intento_fallido" else log.info)("Acceso administrador: %s", registro)
    try:
        RUTA_ACCESOS.parent.mkdir(parents=True, exist_ok=True)
        with RUTA_ACCESOS.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ──────────────────────── Generar el hash (consola) ─────────────────────────
def _main() -> int:
    from getpass import getpass

    print("CofiTech · contraseña de administrador")
    print(f"Mínimo {LONGITUD_MINIMA} caracteres. No se muestra mientras escribes.\n")
    primera = getpass("Contraseña: ")
    if len(primera) < LONGITUD_MINIMA:
        print(f"✖ Muy corta: usa al menos {LONGITUD_MINIMA} caracteres.")
        return 1
    if getpass("Repítela:   ") != primera:
        print("✖ No coinciden.")
        return 1
    linea = generar_hash(primera)
    print("\nAgrega UNA de estas dos líneas (no ambas):\n")
    print(f"  En el archivo .env de la raíz del proyecto:\n    {VARIABLE_HASH}={linea}\n")
    print(f"  O en 07_app_web/.streamlit/secrets.toml (al inicio, antes de cualquier [sección]):\n"
          f'    {VARIABLE_HASH} = "{linea}"\n')
    print("Luego reinicia Streamlit. Para cambiar la contraseña, vuelve a ejecutar este script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
