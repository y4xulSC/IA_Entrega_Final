"""Revisión de diagnósticos: probabilidades guardadas y donación voluntaria de fotos.

    cd 07_app_web
    python -m pytest tests/test_revision_fotos.py -q -rs

Las pruebas de base de datos solo corren con ``COFITECH_TEST_DB_URL`` (base de
pruebas con ``03_supabase_schema.sql`` v1.7 o ``08_revision_diagnosticos.sql``).
"""
from __future__ import annotations

import io
import os
import re
import sys
import uuid
from pathlib import Path

import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from cofitech import fotos, privacidad, repositorio, seguridad  # noqa: E402
from cofitech.repositorio import db_client  # noqa: E402

URL_PRUEBAS = os.environ.get("COFITECH_TEST_DB_URL")
requiere_bd = pytest.mark.skipif(not URL_PRUEBAS, reason="define COFITECH_TEST_DB_URL con una base de pruebas")
PROBS = {"Cercospora": 0.02, "Gotera": 0.03, "Miner": 0.05, "Phoma": 0.01, "Roya": 0.12, "Sano": 0.0353,
         "SpiderMite": 0.7447}


def _foto_con_gps(ancho=3000, alto=2000, orientacion=None) -> bytes:
    """JPEG grande con EXIF de GPS y cámara, como sale de un celular."""
    imagen = Image.new("RGB", (ancho, alto), (40, 120, 40))
    exif = Image.Exif()
    exif[0x010F] = "MarcaCelular"                     # Make
    exif[0x8825] = {1: "N", 2: (4.0, 35.0, 0.0)}       # GPSInfo
    if orientacion:
        exif[0x0112] = orientacion
    salida = io.BytesIO()
    imagen.save(salida, format="JPEG", exif=exif)
    return salida.getvalue()


@pytest.fixture
def local(tmp_path, monkeypatch):
    """Sin base de datos y con el respaldo local en una carpeta temporal."""
    monkeypatch.setattr(db_client, "_dsn", lambda: None)
    monkeypatch.setattr(fotos, "DIR_LOCAL", tmp_path / "fotos")
    fotos.limpiar_vencidas.clear()
    return tmp_path / "fotos"


def _donar(**cambios) -> tuple[str, bool]:
    datos = dict(id_diagnostico=uuid.uuid4().hex, clase="SpiderMite", confianza=0.7447, probabilidades=PROBS,
                 modelo="cnn_cafe_best.keras", municipio="Pitalito", departamento="Huila", codigo_dane="41551")
    datos.update(cambios)
    return fotos.donar(_foto_con_gps(), **datos)


# ───────────────────────────── Preparación ──────────────────────────────────
def test_foto_se_reduce_y_pierde_el_exif():
    preparada = fotos.preparar(_foto_con_gps())
    imagen = Image.open(io.BytesIO(preparada.jpeg))
    assert max(imagen.size) == fotos.LADO_MAX_PX
    assert (preparada.ancho_px, preparada.alto_px) == imagen.size == (1024, 683)
    assert len(imagen.getexif()) == 0                  # ni GPS ni cámara
    assert b"MarcaCelular" not in preparada.jpeg


def test_foto_respeta_la_orientacion_del_celular():
    preparada = fotos.preparar(_foto_con_gps(orientacion=6))   # tomada en vertical
    assert preparada.alto_px > preparada.ancho_px


def test_codigo_facil_de_dictar():
    for _ in range(50):
        codigo = fotos.nuevo_codigo()
        assert re.fullmatch(r"[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}", codigo)


def test_segunda_opcion():
    assert fotos.segunda_opcion(PROBS) == ("Roya", 0.12, pytest.approx(0.6247))
    assert fotos.segunda_opcion(None) is None


def test_aviso_de_privacidad_explica_la_donacion():
    texto = privacidad.texto_aviso()
    assert "salvo que decidas donarla" in texto
    assert f"{fotos.DIAS_RETENCION} días" in texto
    assert "sin los datos" in texto and "ubicación" in texto
    assert privacidad.VERSION_AVISO == "2026-11-17"


# ─────────────────────────── Respaldo local ─────────────────────────────────
def test_donar_revisar_y_borrar_sin_base(local):
    codigo, en_nube = _donar()
    assert not en_nube and (local / f"{codigo}.jpg").exists()
    pendientes, fuente = fotos.listar(True)
    assert fuente == "archivo local" and [f["codigo"] for f in pendientes] == [codigo]
    assert Image.open(io.BytesIO(fotos.imagen(pendientes[0], fuente))).size == (1024, 683)
    assert fotos.revisar(pendientes[0], fuente, "Roya", "Pústulas naranja en el envés")
    revisadas, _ = fotos.listar(False)
    assert revisadas[0]["clase_revisada"] == "Roya"
    assert fotos.borrar(codigo.lower())                  # el usuario lo puede escribir en minúsculas
    assert fotos.listar(None)[0] == [] and not (local / f"{codigo}.jpg").exists()


def test_fotos_vencidas_se_borran(local, monkeypatch):
    monkeypatch.setattr(fotos, "DIAS_RETENCION", -1)
    _donar()
    assert fotos.limpiar_vencidas() == 1
    assert fotos.listar(None)[0] == []


def test_revision_con_clase_invalida(local):
    _donar()
    foto = fotos.listar(True)[0][0]
    with pytest.raises(ValueError):
        fotos.revisar(foto, "archivo local", "Hongo raro")


def test_pantalla_de_revision_para_administradores(local, tmp_path, monkeypatch):
    monkeypatch.setattr(repositorio, "RUTA_DIAGNOSTICOS", tmp_path / "diag.jsonl")
    monkeypatch.setattr(repositorio, "RUTA_FEEDBACK", tmp_path / "feedback.jsonl")
    repositorio._anexar(repositorio.RUTA_DIAGNOSTICOS, {
        "id": "x1", "fecha": "2026-11-17T08:00:00+00:00", "municipio": "Pitalito", "clase": "SpiderMite",
        "confianza": 0.7447, "probabilidades": PROBS})
    _donar()
    at = AppTest.from_file(str(APP / "vistas/revision_fotos.py"), default_timeout=120)
    at.session_state[seguridad._CLAVE_ADMIN] = True
    at.run()
    assert not at.exception
    assert next(m for m in at.metric if m.label == "Pendientes").value == "1"
    assert at.dataframe                                   # el diagnóstico dudoso aparece en la tabla
    at.selectbox[0].set_value("Roya")
    next(b for b in at.button if b.label == "Guardar revisión").click().run()
    assert not at.exception
    assert next(m for m in at.metric if m.label == "Revisadas").value == "1"
    assert next(m for m in at.metric if m.label == "Acierto del modelo en campo").value == "0%"


def test_pantalla_de_revision_exige_administrador(local):
    at = AppTest.from_file(str(APP / "vistas/revision_fotos.py"), default_timeout=120).run()
    assert not at.metric                                  # se detiene antes de mostrar nada


# ──────────────────────────────── Supabase ──────────────────────────────────
@pytest.fixture
def bd(monkeypatch, tmp_path):
    monkeypatch.setattr(db_client, "_dsn", lambda: URL_PRUEBAS)
    monkeypatch.setattr(db_client, "_pool", None)
    monkeypatch.setattr(db_client, "_ultimo_fallo", 0.0)
    monkeypatch.setattr(db_client, "_CACHE_COLUMNAS", {})
    monkeypatch.setattr(fotos, "DIR_LOCAL", tmp_path / "fotos")
    monkeypatch.setattr(repositorio, "RUTA_DIAGNOSTICOS", tmp_path / "diag.jsonl")
    fotos.limpiar_vencidas.clear()
    yield
    with db_client._conexion() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM cafe.registro_fotos_donadas WHERE municipio = 'Pytest'")
        cur.execute("DELETE FROM cafe.registro_diagnosticos WHERE municipio = 'Pytest'")


@requiere_bd
def test_probabilidades_llegan_a_la_base(bd):
    ident = uuid.uuid4().hex
    db_client.insertar_diagnostico({"id": ident, "municipio": "Pytest", "clase": "SpiderMite",
                                    "confianza": 0.7447, "probabilidades": PROBS, "es_demo": True})
    df = db_client.leer_diagnosticos()
    fila = df[df["id"] == str(uuid.UUID(ident))].iloc[0]
    assert fila["probabilidades"]["SpiderMite"] == pytest.approx(0.7447)


@requiere_bd
def test_foto_donada_en_la_base(bd):
    codigo, en_nube = _donar(municipio="Pytest", es_demo=True)
    assert en_nube
    assert not fotos.DIR_LOCAL.exists() or not list(fotos.DIR_LOCAL.glob("*.jpg"))   # no quedó copia local
    pendientes, fuente = fotos.listar(True)
    foto = next(f for f in pendientes if f["codigo"] == codigo)
    assert fuente == "Supabase" and foto["probabilidades"]["Roya"] == pytest.approx(0.12)
    jpeg = fotos.imagen(foto, fuente)
    assert jpeg[:2] == b"\xff\xd8" and len(Image.open(io.BytesIO(jpeg)).getexif()) == 0
    assert fotos.revisar(foto, fuente, "SpiderMite", "Telarañas en el envés")
    assert any(f["codigo"] == codigo and f["clase_revisada"] == "SpiderMite" for f in fotos.listar(False)[0])
    assert fotos.borrar(codigo)
    assert not any(f["codigo"] == codigo for f in fotos.listar(None)[0])


@requiere_bd
def test_vencidas_se_borran_en_la_base(bd, monkeypatch):
    monkeypatch.setattr(fotos, "DIAS_RETENCION", -1)
    codigo, _ = _donar(municipio="Pytest", es_demo=True)
    fotos.limpiar_vencidas.clear()                    # donar() ya la llamó (antes de insertar)
    assert fotos.limpiar_vencidas() >= 1
    assert not any(f["codigo"] == codigo for f in fotos.listar(None)[0])
