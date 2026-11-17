"""Mantiene al día el código en memoria cuando Streamlit Cloud actualiza la app en caliente.

Al hacer ``git push``, Streamlit Community Cloud baja el código y muestra
«Updated app!» **sin reiniciar el proceso**. Las pantallas (``app.py``,
``pages/``, ``vistas/``) se leen del disco en cada ejecución, pero los módulos
importados se quedan en memoria:

* ``db_client`` (``03_scripts/bd``) y ``rag_pipeline`` (``06_agente_rag``) están
  fuera de la carpeta de la app y Streamlit nunca los recarga. Así apareció
  ``module 'db_client' has no attribute 'borrar_fotos_vencidas'``.
* Los de ``cofitech`` solo se recargan si había una sesión abierta que volvió a
  ejecutarse después del cambio. Si no, una pantalla nueva llama a un módulo
  viejo (``registrar_diagnostico() got an unexpected keyword argument``).

``app.py`` llama a ``actualizar_codigo()`` al empezar cada ejecución. Si algún
módulo del proyecto cambió en disco desde que se cargó, se sacan **todos** de
``sys.modules`` (igual que hace Streamlit con los suyos, para no mezclar
versiones), se cierra el pool de la base y ``app.py`` vuelve a ejecutarse con el
código nuevo.

Cómo se sabe si cambió: cada módulo tiene una firma (fecha en ns y tamaño del
archivo) tomada al cargarse: ``_FIRMA_ARCHIVO`` en ``db_client`` y
``rag_pipeline``, y ``cofitech._FIRMAS_AL_CARGAR`` para los de ``cofitech``. Se
compara por igualdad, no por «más nuevo», porque ``git`` y ``tar`` pueden dejar
fechas viejas. Un módulo sin firma (de una versión anterior a este archivo)
cuenta como cambiado una sola vez.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path
from types import ModuleType

log = logging.getLogger("cofitech.recarga")

PROYECTO: Path = Path(__file__).resolve().parents[2]
CARPETAS: tuple[Path, ...] = tuple(PROYECTO / c for c in ("07_app_web/cofitech", "03_scripts/bd", "06_agente_rag"))
_candado = threading.Lock()
# Firmas tomadas al sacar módulos sin firma propia. Vive en ``sys`` para
# sobrevivir a que este mismo módulo se saque de ``sys.modules``.
_SIN_FIRMA: dict[str, tuple[int, int]] = sys.__dict__.setdefault("_cofitech_firmas_sin_marca", {})


def firma(ruta: str | os.PathLike) -> tuple[int, int] | None:
    """(fecha de modificación en ns, tamaño) del archivo, o ``None`` si no existe."""
    try:
        estado = os.stat(ruta)
    except OSError:
        return None
    return estado.st_mtime_ns, estado.st_size


def _archivo(modulo: ModuleType) -> str | None:
    archivo = getattr(modulo, "__file__", None)
    return os.path.realpath(archivo) if archivo else None


def modulos_del_proyecto() -> dict[str, ModuleType]:
    """Módulos cargados cuyo archivo está en ``cofitech``, ``03_scripts/bd`` o ``06_agente_rag``."""
    carpetas = tuple(os.path.realpath(c) + os.sep for c in CARPETAS)
    return {nombre: m for nombre, m in list(sys.modules.items())
            if m is not None and (a := _archivo(m)) and a.startswith(carpetas)}


def _firma_al_cargar(modulo: ModuleType) -> tuple[int, int] | None:
    propia = getattr(modulo, "_FIRMA_ARCHIVO", None)
    if propia is not None:
        return tuple(propia)
    paquete = sys.modules.get("cofitech")
    firmas = getattr(paquete, "_FIRMAS_AL_CARGAR", {}) or {}
    archivo = _archivo(modulo)
    return firmas.get(archivo) or _SIN_FIRMA.get(archivo)


def modulos_desactualizados() -> list[str]:
    """Nombres de los módulos del proyecto cuyo archivo cambió desde que se cargaron."""
    viejos = []
    for nombre, modulo in modulos_del_proyecto().items():
        actual = firma(_archivo(modulo))
        if actual is not None and actual != _firma_al_cargar(modulo):
            viejos.append(nombre)
    return sorted(viejos)


def actualizar_codigo() -> list[str]:
    """Si algún módulo del proyecto cambió en disco, saca todos de ``sys.modules``.

    Returns:
        Los módulos que habían cambiado (lista vacía casi siempre). Si no está
        vacía, quien llama debe volver a ejecutar la app (``st.rerun()``).
    """
    with _candado:                 # varias sesiones pueden ejecutar app.py a la vez
        viejos = modulos_desactualizados()
        if not viejos:
            return []
        for nombre, modulo in modulos_del_proyecto().items():
            pool = getattr(modulo, "_pool", None)       # db_client: no dejar conexiones colgadas
            if pool is not None:
                try:
                    pool.closeall()
                except Exception:
                    pass
            archivo = _archivo(modulo)
            if getattr(modulo, "_FIRMA_ARCHIVO", None) is None and archivo:
                _SIN_FIRMA[archivo] = firma(archivo)     # para no repetir con módulos que nunca tendrán firma
            sys.modules.pop(nombre, None)
        log.warning("Código actualizado en caliente: se recargan %s", ", ".join(viejos))
        return viejos
