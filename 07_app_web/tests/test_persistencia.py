"""Persistencia de diagnósticos y votos: archivo local y Supabase.

    cd 07_app_web
    python -m pytest tests/test_persistencia.py -q -rs

Las pruebas de base de datos NO usan la Supabase de producción: solo corren si
se define ``COFITECH_TEST_DB_URL`` con una base de pruebas (con el SQL de
``03_scripts/bd/03_supabase_schema.sql`` aplicado). Escriben filas con
``es_demo = true`` y las borran al terminar.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cofitech import repositorio  # noqa: E402
from cofitech.repositorio import db_client  # noqa: E402

URL_PRUEBAS = os.environ.get("COFITECH_TEST_DB_URL")
requiere_bd = pytest.mark.skipif(not URL_PRUEBAS, reason="define COFITECH_TEST_DB_URL con una base de pruebas")


def _diagnosticos(**cambios) -> pd.DataFrame:
    base = pd.DataFrame({
        "id": ["a", "b", "c", "d"],
        "fecha": pd.to_datetime(["2026-10-01"] * 4, utc=True),
        "codigo_dane": ["63690", "63690", "63690", "66440"],
        "departamento": ["Quindío", "Quindío", "Quindío", "Risaralda"],
        "municipio": ["Salento", "Salento", "Salento", "Marsella"],
        "clase": ["Roya", "Roya", "Sano", "Roya"],
        "feedback_usuario": [None, False, None, True],
    })
    return base.assign(**cambios)


def test_roya_rechazada_por_el_caficultor_no_cuenta():
    """Igual que en SQL: un 👎 saca la foto del conteo de roya, pero no del total de fotos."""
    resumen = repositorio.alertas_por_municipio(_diagnosticos()).set_index("municipio")
    assert resumen.loc["Salento", "fotos"] == 3
    assert resumen.loc["Salento", "fotos_roya"] == 1
    assert resumen.loc["Salento", "pct_fotos_roya"] == pytest.approx(33.3)
    assert resumen.loc["Marsella", "fotos_roya"] == 1
    assert list(repositorio.alertas_por_municipio(_diagnosticos()).columns) == repositorio.COLUMNAS_RESUMEN


def test_resumen_sin_columna_de_feedback():
    resumen = repositorio.alertas_por_municipio(_diagnosticos().drop(columns="feedback_usuario"))
    assert resumen["fotos_roya"].sum() == 3


def test_sin_credenciales_no_intenta_conectarse(monkeypatch):
    monkeypatch.setattr(db_client, "_dsn", lambda: None)
    assert not db_client.configurado()
    assert db_client.estado() == "sin configurar"
    assert repositorio._en_nube(db_client.insertar_diagnostico, {}) is False


def test_base_caida_no_detiene_la_app(monkeypatch):
    """Host inalcanzable: falla en segundos, queda en pausa y la app sigue con el archivo local."""
    monkeypatch.setattr(db_client, "_dsn", lambda: "postgresql://u:p@127.0.0.1:1/x")
    monkeypatch.setattr(db_client, "_pool", None)
    monkeypatch.setattr(db_client, "_ultimo_fallo", 0.0)
    assert db_client.disponible() is False
    assert "no disponible" in db_client.estado()
    with pytest.raises(db_client.BaseDatosNoDisponible):      # pausa: ni siquiera reintenta
        db_client.resumen_roya_por_municipio(30)


# ───────────────────────── Con base de datos de pruebas ─────────────────────
@pytest.fixture
def bd(monkeypatch):
    monkeypatch.setattr(db_client, "_dsn", lambda: URL_PRUEBAS)
    monkeypatch.setattr(db_client, "_pool", None)
    monkeypatch.setattr(db_client, "_ultimo_fallo", 0.0)
    creados: list[str] = []
    yield creados
    with db_client._conexion() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM cafe.registro_diagnosticos WHERE id = ANY(%s::uuid[])", (creados,))
        cur.execute("DELETE FROM cafe.registro_eventos_uso WHERE id_sesion = 'pytest'")


@requiere_bd
def test_diagnostico_y_feedback_llegan_a_la_base(bd):
    ident = uuid.uuid4().hex
    bd.append(ident)
    db_client.insertar_diagnostico({
        "id": ident, "fecha": "2026-10-14T10:00:00-05:00", "municipio": "Salento", "codigo_dane": "63690",
        "departamento": "Quindío", "altitud_msnm": 1990, "clase": "Roya", "confianza": 0.91,
        "modelo": "pytest", "rol_origen": "caficultor", "id_sesion": "pytest", "es_demo": True,
    })
    resumen = db_client.resumen_roya_por_municipio(dias=3650, incluir_demo=True).set_index("codigo_dane")
    antes = int(resumen.loc["63690", "fotos_roya"])
    assert db_client.registrar_feedback_diagnostico(ident, False) is True
    despues = db_client.resumen_roya_por_municipio(dias=3650, incluir_demo=True).set_index("codigo_dane")
    assert int(despues.loc["63690", "fotos_roya"]) == antes - 1


@requiere_bd
def test_calificacion_del_chat_queda_en_la_vista_de_feedback(bd):
    db_client.insertar_evento({
        "timestamp": "2026-10-14T10:00:00-05:00", "id_sesion": "pytest", "usuario_rol": "Caficultor",
        "herramienta": "RAG", "accion": "feedback_respuesta",
        "metadata": {"util": True, "modelo": "pytest", "id_respuesta": "r1", "municipio": "Salento"},
    })
    with db_client._conexion() as conn, conn.cursor() as cur:
        cur.execute("SELECT util, municipio FROM cafe.vw_feedback_rag WHERE id_sesion = 'pytest'")
        assert cur.fetchall() == [(True, "Salento")]


# ───────────────────────────── KPIs consolidados ────────────────────────────
def _eventos_kpi():
    from cofitech import telemetria as tel
    filas = [
        ("s1", "Caficultor", "Visión", "diagnostico_ejecutado", {"confianza": 0.9}),
        ("s1", "Caficultor", "Visión", "validacion_diagnostico", {"confianza_aceptada": True}),
        ("s1", "Caficultor", "Predicción Rendimiento", "calculo_rendimiento", {}),
        ("s1", "Caficultor", "RAG", "feedback_respuesta", {"util": True}),
        ("s2", "Agrónomo/Cooperativa", "RAG", "feedback_respuesta", {"util": False}),
    ]
    eventos = [{"timestamp": "2026-10-15T08:00:00-05:00", "id_sesion": s, "usuario_rol": r, "herramienta": h,
                "accion": a, "metadata": md} for s, r, h, a, md in filas]
    df = pd.json_normalize(eventos, sep="_").rename(columns=lambda c: c.replace("metadata_", "md_", 1))
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return tel, eventos, df


def test_kpis_por_rol_local():
    tel, _, df = _eventos_kpi()
    tabla = tel.kpis_por_rol(df).set_index("rol")
    assert list(tabla.reset_index().columns) == tel.COLUMNAS_KPI_ROL
    assert tabla.loc["Total", "satisfaccion_rag"] == pytest.approx(0.5)
    assert tabla.loc["Caficultor", "confianza_aceptada"] == pytest.approx(1.0)
    assert tabla.loc["Caficultor", "sesiones_3_herramientas"] == 1
    assert tabla.loc["Agrónomo/Cooperativa", "valoraciones_rag"] == 1


@requiere_bd
def test_vista_de_kpis_coincide_con_el_calculo_local(bd):
    tel, eventos, df = _eventos_kpi()
    with db_client._conexion() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM cafe.registro_eventos_uso")      # base de PRUEBAS: se parte de cero
    for evento in eventos:
        db_client.insertar_evento(evento)
    nube = db_client.kpis_consolidados().set_index("rol")
    local = tel.kpis_por_rol(df).set_index("rol")
    for rol in local.index:
        for col in ("sesiones", "eventos", "valoraciones_rag", "validaciones_vision", "sesiones_3_herramientas"):
            assert nube.loc[rol, col] == local.loc[rol, col], (rol, col)
        for col in ("satisfaccion_rag", "confianza_aceptada", "confianza_media_modelo"):
            assert nube.loc[rol, col] == pytest.approx(local.loc[rol, col], nan_ok=True), (rol, col)
    with db_client._conexion() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM cafe.registro_eventos_uso WHERE id_sesion IN ('s1', 's2')")
