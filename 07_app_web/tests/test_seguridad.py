"""Acceso de administrador: hash de la contraseña y pantallas visibles por permiso.

    cd 07_app_web
    python -m pytest tests/test_seguridad.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from cofitech import seguridad  # noqa: E402
from cofitech.contexto_finca import Rol  # noqa: E402
from cofitech.navegacion import ADMINISTRACION, MENU  # noqa: E402

CONTRASENA = "cafe-de-prueba-2026"


@pytest.fixture(scope="module")
def hash_prueba() -> str:
    return seguridad.generar_hash(CONTRASENA, iteraciones=1_000)   # rápido para pruebas


def test_hash_verifica_solo_la_contrasena_correcta(hash_prueba):
    assert seguridad.verificar(CONTRASENA, hash_prueba)
    assert not seguridad.verificar(CONTRASENA + " ", hash_prueba)
    assert not seguridad.verificar("", hash_prueba)
    assert CONTRASENA not in hash_prueba
    assert "$" not in hash_prueba and "=" not in hash_prueba.split(":", 1)[1]   # seguro para .env


def test_misma_contrasena_da_hashes_distintos():
    assert seguridad.generar_hash(CONTRASENA, 1_000) != seguridad.generar_hash(CONTRASENA, 1_000)


@pytest.mark.parametrize("malo", ["", "texto", "md5:1:a:b", "pbkdf2_sha256:no-numero:a:b", "pbkdf2_sha256:1000:%%%:b"])
def test_hash_mal_formado_nunca_da_acceso(malo):
    assert not seguridad.verificar(CONTRASENA, malo)


def test_pantallas_de_administracion_no_estan_en_los_menus_de_rol():
    claves_admin = {p.clave for p in ADMINISTRACION}
    assert claves_admin == {"telemetria", "ficha"}
    for rol in (Rol.CAFICULTOR, Rol.AGRONOMO):
        assert not claves_admin & {p.clave for p in MENU[rol]}


# ─────────────────────────────── App completa ───────────────────────────────
def _agronomo(monkeypatch, hash_guardado: str | None) -> AppTest:
    monkeypatch.setattr(seguridad, "_fallos_globales", [])
    if hash_guardado:
        monkeypatch.setenv(seguridad.VARIABLE_HASH, hash_guardado)
    else:
        monkeypatch.delenv(seguridad.VARIABLE_HASH, raising=False)
        monkeypatch.setattr(seguridad, "PROYECTO", Path("/no/existe"))   # que no lea el .env real
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=120).run()
    at.radio[0].set_value("Soy agrónomo o trabajo en una cooperativa").run()
    at.multiselect[0].set_value(["Quindío"])
    at.button[0].click()
    return at.run()


def _es_admin(at: AppTest) -> bool:
    return "cofitech_admin" in at.session_state and bool(at.session_state["cofitech_admin"])


def _paginas(at: AppTest) -> list[str]:
    # AppTest no expone st.navigation: se infiere por el botón de salida y el panel de depuración.
    return [b.label for b in at.sidebar.button]


def test_usuario_comun_no_ve_administracion(monkeypatch, hash_prueba):
    at = _agronomo(monkeypatch, hash_prueba)
    assert not at.exception
    assert "Salir de administrador" not in _paginas(at)
    assert "Simular hoja con roya" not in _paginas(at)
    # La página ni siquiera se registra en st.navigation: no hay URL a la cual saltar.
    with pytest.raises(ValueError, match="Could not find a navigation page"):
        at.switch_page("vistas/telemetria.py")


def test_administrador_entra_con_la_contrasena_y_sale(monkeypatch, hash_prueba):
    at = _agronomo(monkeypatch, hash_prueba)
    at.switch_page("vistas/acceso.py").run()
    at.text_input[0].set_value("equivocada")
    at.button(key="FormSubmitter:form_admin-Entrar como administrador").click().run()
    assert any("Contraseña incorrecta" in e.value for e in at.error)
    assert not _es_admin(at)

    at.text_input[0].set_value(CONTRASENA)
    at.button(key="FormSubmitter:form_admin-Entrar como administrador").click().run()
    assert _es_admin(at)
    assert {"Salir de administrador", "Simular hoja con roya"} <= set(_paginas(at))
    at.switch_page("vistas/telemetria.py").run()
    assert not at.exception and not at.error
    assert at.title[0].value == "Telemetría y KPIs"

    next(b for b in at.sidebar.button if b.label == "Salir de administrador").click().run()
    assert not _es_admin(at)


def test_bloqueo_tras_cinco_intentos(monkeypatch, hash_prueba):
    at = _agronomo(monkeypatch, hash_prueba)
    at.switch_page("vistas/acceso.py").run()
    for _ in range(seguridad.INTENTOS_POR_SESION):
        at.text_input[0].set_value("equivocada")
        at.button(key="FormSubmitter:form_admin-Entrar como administrador").click().run()
    at.text_input[0].set_value(CONTRASENA)                 # ni la correcta entra durante el bloqueo
    at.button(key="FormSubmitter:form_admin-Entrar como administrador").click().run()
    assert any("Demasiados intentos" in e.value for e in at.error)
    assert not _es_admin(at)


def test_sin_hash_configurado_no_hay_acceso(monkeypatch):
    at = _agronomo(monkeypatch, None)
    at.switch_page("vistas/acceso.py").run()
    assert not at.text_input                               # ni siquiera aparece el campo
    assert any("no está configurado" in c.value for c in at.caption)


def test_pantalla_de_telemetria_se_protege_sola():
    """Defensa adicional: aunque alguien la ejecute directamente, sin permiso no muestra nada."""
    at = AppTest.from_file(str(APP / "vistas" / "telemetria.py"), default_timeout=60).run()
    assert any("solo para administradores" in e.value for e in at.error)
    assert not at.metric
