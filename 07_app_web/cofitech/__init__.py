"""CofiTech · núcleo compartido de la app web (estado, navegación y repositorio).

Al importarse (``app.py`` lo hace antes que cualquier modelo) prepara el proceso
para correr TensorFlow y PyTorch juntos en un servidor pequeño, como el plan
gratis de Streamlit Community Cloud (2 núcleos, 2,7 GB):

1. ``faulthandler``: si una librería en C falla (``Segmentation fault``), la pila
   de Python queda en los logs y se sabe en qué línea pasó.
2. Hilos de TensorFlow, oneDNN y PyTorch limitados a los núcleos que el
   contenedor puede usar de verdad (no a los del servidor físico).
3. Triton antes que TensorFlow (ver ``_cargar_triton_antes_que_tensorflow``).

Todo se puede cambiar con variables de entorno o con claves de primer nivel en
los *Secrets* de Streamlit, sin tocar código.
"""
from __future__ import annotations

import faulthandler
import importlib.util
import math
import os
import sys


def _activar_faulthandler() -> None:
    try:
        if not faulthandler.is_enabled():
            faulthandler.enable(all_threads=True)
    except Exception:              # stderr no disponible: seguir sin esto
        pass


def _nucleos_disponibles() -> int:
    """Núcleos que el contenedor puede usar: afinidad y cuota de cgroup (v2 o v1)."""
    try:
        nucleos = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        nucleos = os.cpu_count() or 1
    cuota = None
    try:
        with open("/sys/fs/cgroup/cpu.max", encoding="ascii") as f:          # cgroup v2: "200000 100000"
            limite, periodo = f.read().split()[:2]
            if limite != "max":
                cuota = int(limite) / int(periodo)
    except (OSError, ValueError):
        try:
            with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us", encoding="ascii") as f:   # cgroup v1
                limite = int(f.read())
            with open("/sys/fs/cgroup/cpu/cpu.cfs_period_us", encoding="ascii") as f:
                periodo = int(f.read())
            if limite > 0:
                cuota = limite / periodo
        except (OSError, ValueError):
            pass
    if cuota:
        nucleos = min(nucleos, max(1, math.ceil(cuota)))
    return max(1, nucleos)


def _limitar_hilos() -> None:
    """Evita que TensorFlow cree un hilo por cada núcleo del servidor físico.

    En un contenedor, ``os.cpu_count()`` devuelve los núcleos de la máquina
    entera (decenas) aunque la cuota sea de 2. TensorFlow y oneDNN dimensionan
    sus grupos de hilos con ese número; en el plan gratis eso multiplica la
    memoria de trabajo y puede tumbar el proceso. ``setdefault``: si la variable
    ya existe, manda la del entorno.
    """
    if not sys.platform.startswith("linux"):
        return
    n = str(min(_nucleos_disponibles(), 4))
    for variable in ("TF_NUM_INTRAOP_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(variable, n)
    os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")
    # oneDNN es la fuente más común de fallos en C de TensorFlow en CPU ajenas.
    # Sin él los resultados son los mismos (diferencias de redondeo) y la CNN
    # sigue por debajo de 1 s por foto. COFITECH_ONEDNN=1 lo vuelve a activar.
    if os.environ.get("COFITECH_ONEDNN", "0") != "1":
        os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")


def _cargar_triton_antes_que_tensorflow() -> None:
    """Evita que el servidor se caiga en Linux (Streamlit Community Cloud).

    En Linux, PyTorch (que usa el asistente RAG a través de sentence-transformers)
    trae Triton. Triton y TensorFlow registran las mismas opciones de LLVM: si
    TensorFlow se carga primero (al abrir «Revisar una hoja») y Triton después
    (al abrir el asistente), el proceso aborta con
    ``LLVM ERROR: inconsistency in registered CommandLine options`` y la app se
    cae para todos los usuarios. Cargando Triton primero no pasa. En Windows y
    macOS PyTorch no trae Triton y esto no hace nada. ``COFITECH_CARGAR_TRITON=0``
    lo desactiva (para diagnosticar).
    """
    if not sys.platform.startswith("linux") or "tensorflow" in sys.modules:
        return
    if os.environ.get("COFITECH_CARGAR_TRITON", "1") == "0":
        return
    if importlib.util.find_spec("triton") is None:
        return
    try:
        import triton  # noqa: F401
    except Exception:              # nunca impedir que la app arranque por esto
        pass


_activar_faulthandler()
_limitar_hilos()
_cargar_triton_antes_que_tensorflow()
