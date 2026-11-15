"""CofiTech · núcleo compartido de la app web (estado, navegación y repositorio)."""
from __future__ import annotations

import importlib.util
import sys


def _cargar_triton_antes_que_tensorflow() -> None:
    """Evita que el servidor se caiga en Linux (Streamlit Community Cloud).

    En Linux, PyTorch (que usa el asistente RAG a través de sentence-transformers)
    trae Triton. Triton y TensorFlow registran las mismas opciones de LLVM: si
    TensorFlow se carga primero (al abrir «Revisar una hoja») y Triton después
    (al abrir el asistente), el proceso aborta con
    ``LLVM ERROR: inconsistency in registered CommandLine options`` y la app se
    cae para todos los usuarios. Cargando Triton primero no pasa. En Windows y
    macOS PyTorch no trae Triton y esto no hace nada.
    """
    if not sys.platform.startswith("linux") or "tensorflow" in sys.modules:
        return
    if importlib.util.find_spec("triton") is None:
        return
    try:
        import triton  # noqa: F401
    except Exception:              # nunca impedir que la app arranque por esto
        pass


_cargar_triton_antes_que_tensorflow()
