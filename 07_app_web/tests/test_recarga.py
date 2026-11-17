"""Código al día tras una actualización en caliente (Streamlit Community Cloud).

    cd 07_app_web
    python -m pytest tests/test_recarga.py -q
"""
from __future__ import annotations

import importlib
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cofitech import recarga  # noqa: E402

CON_FIRMA = ("import os\n_FIRMA_ARCHIVO = (os.stat(__file__).st_mtime_ns, os.stat(__file__).st_size)\n"
             "_pool = None\ndef a():\n    return 'a'\n")
SIN_FIRMA = "def a():\n    return 'a'\n"


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    """Una carpeta «del proyecto» con módulos importados, como db_client antes de un git pull."""
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(recarga, "CARPETAS", (tmp_path,))
    nombres = []

    def importar(nombre: str, texto: str):
        (tmp_path / f"{nombre}.py").write_text(texto, encoding="utf-8")
        sys.modules.pop(nombre, None)
        importlib.invalidate_caches()
        nombres.append(nombre)
        return importlib.import_module(nombre)

    yield tmp_path, importar
    for nombre in nombres:
        sys.modules.pop(nombre, None)


def _cambiar(ruta: Path, texto: str, fecha: float) -> None:
    ruta.write_text(texto, encoding="utf-8")
    os.utime(ruta, (fecha, fecha))


def test_sin_cambios_no_hace_nada(carpeta):
    _, importar = carpeta
    importar("mod_a", CON_FIRMA)
    assert recarga.actualizar_codigo() == []
    assert "mod_a" in sys.modules


def test_archivo_cambiado_saca_todos_los_modulos_del_proyecto(carpeta):
    ruta, importar = carpeta
    importar("mod_a", CON_FIRMA)
    importar("mod_b", CON_FIRMA)
    _cambiar(ruta / "mod_a.py", CON_FIRMA + "def b():\n    return 'b'\n", time.time() + 5)
    assert recarga.actualizar_codigo() == ["mod_a"]
    assert "mod_a" not in sys.modules and "mod_b" not in sys.modules    # no se mezclan versiones
    assert importlib.import_module("mod_a").b() == "b"                   # la próxima importación es la nueva
    assert recarga.actualizar_codigo() == []


def test_archivo_con_fecha_vieja_tambien_cuenta(carpeta):
    """git archive / tar dejan la fecha del commit, más vieja que la carga."""
    ruta, importar = carpeta
    importar("mod_a", CON_FIRMA)
    _cambiar(ruta / "mod_a.py", CON_FIRMA + "\n# cambio\n", time.time() - 86400)
    assert recarga.actualizar_codigo() == ["mod_a"]


def test_modulo_viejo_sin_firma_se_recarga_una_sola_vez(carpeta):
    _, importar = carpeta
    importar("mod_viejo", SIN_FIRMA)                 # como el db_client de antes de este arreglo
    assert recarga.actualizar_codigo() == ["mod_viejo"]
    importlib.import_module("mod_viejo")             # sigue sin firma propia
    assert recarga.actualizar_codigo() == []         # no entra en un ciclo de recargas


def test_cierra_el_pool_de_la_base(carpeta):
    ruta, importar = carpeta
    mod = importar("mod_a", CON_FIRMA)
    cerrado = []
    mod._pool = type("Pool", (), {"closeall": lambda self: cerrado.append(True)})()
    _cambiar(ruta / "mod_a.py", CON_FIRMA + "\n# cambio\n", time.time() + 5)
    recarga.actualizar_codigo()
    assert cerrado == [True]


def test_modulos_de_otras_carpetas_no_se_tocan(carpeta):
    assert "json" not in recarga.modulos_del_proyecto()


def test_el_proyecto_real_tiene_firmas_y_esta_al_dia():
    import cofitech
    from cofitech.repositorio import db_client
    assert db_client._FIRMA_ARCHIVO == recarga.firma(db_client.__file__)
    assert os.path.realpath(recarga.__file__) in cofitech._FIRMAS_AL_CARGAR
    texto = (recarga.PROYECTO / "06_agente_rag" / "rag_pipeline.py").read_text(encoding="utf-8")
    assert "_FIRMA_ARCHIVO = (os.stat(__file__).st_mtime_ns" in texto
    assert recarga.modulos_desactualizados() == []
