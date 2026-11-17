"""Catálogo de variedades: Catimor / Costa Rica 95 y efecto en las recomendaciones.

    cd 07_app_web
    python -m pytest tests/test_variedades.py -q

Un usuario no encontró su variedad («catumorro» = Catimor). Lo crítico no es
la lista, sino qué decide la app con ella: una variedad marcada como resistente
recibe «no se recomienda control químico» y no se le descuenta la roya. El
Catimor que se siembra en Colombia no tiene resistencia suficiente (Cenicafé),
así que debe recorrer el camino de una variedad susceptible.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]
RAIZ = APP.parent
sys.path.insert(0, str(APP))

from cofitech import prescripcion  # noqa: E402
from cofitech import rendimiento as rend  # noqa: E402
from cofitech.contexto_finca import (  # noqa: E402
    VARIEDADES, ContextoFinca, Finca, Mercado, Rol, Zona, prefijo_rag,
)

CATIMOR = "Catimor / Costa Rica 95"


# ─────────────────────────────── Catálogo ───────────────────────────────────
def test_catimor_esta_y_es_susceptible():
    assert VARIEDADES[CATIMOR] is False
    assert Finca(variedad=CATIMOR).resistente_roya is False


def test_no_sabe_sigue_de_ultima_y_los_nombres_caben_en_la_base():
    nombres = list(VARIEDADES)
    assert nombres[-1] == "No sabe / Mezcla"            # es el valor por defecto del formulario
    assert all(len(n) <= 40 for n in nombres)             # mk_lote.variedad es VARCHAR(40)
    assert len(set(n.casefold() for n in nombres)) == len(nombres)


def test_resistentes_son_solo_las_de_cenicafe():
    """Marcar una variedad como resistente apaga el control químico: solo las de Cenicafé."""
    assert {n for n, r in VARIEDADES.items() if r} == {"Castillo", "Colombia", "Cenicafé 1", "Tabi"}


# ───────────────────────── Efecto en las decisiones ─────────────────────────
@pytest.mark.parametrize("incidencia, nivel", [(None, "sin_dato"), (3.0, "preventivo"), (8.0, "sistemico")])
def test_catimor_recibe_manejo_de_variedad_susceptible(incidencia, nivel):
    r = prescripcion.recomendacion_roya(incidencia, VARIEDADES[CATIMOR])
    assert r.nivel == nivel
    assert r.nivel != "resistente"


def test_catimor_si_descuenta_perdidas_por_roya():
    impacto = rend.impacto_roya("Alto", VARIEDADES[CATIMOR], 1.2, 3.0, 2_650_000)
    assert impacto.aplica and impacto.perdida_min > 0


def test_el_asistente_recibe_la_variedad_como_susceptible():
    ctx = ContextoFinca(
        rol=Rol.CAFICULTOR,
        finca=Finca(municipio="Pitalito", departamento="Huila", codigo_dane="41551", altitud_msnm=1500,
                    area_ha=2.0, variedad=CATIMOR),
        zona=Zona(departamentos=["Huila"]),
        mercado=Mercado(precio_fnc_cop_carga=2_650_000, fecha=date(2026, 9, 1)))
    assert f"Variedad: {CATIMOR} (susceptible a la roya)." in prefijo_rag(ctx, hoy=date(2026, 11, 17))


def test_formulario_de_ingreso_ofrece_catimor_con_ayuda(monkeypatch):
    monkeypatch.delenv("COFITECH_MERCADO_ACTIVO", raising=False)
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=120).run()
    caja = next(s for s in at.selectbox if s.label == "Variedad principal")
    assert CATIMOR in caja.options
    assert "Costa Rica" in (caja.help or "")
    caja.set_value(CATIMOR)
    assert caja.value == CATIMOR


# ───────────────────────────── Base y corpus ────────────────────────────────
def test_semilla_de_la_base_incluye_catimor():
    for archivo in ("01_ddl_schema.sql", "03_supabase_schema.sql", "07_variedad_catimor.sql"):
        texto = (RAIZ / "03_scripts" / "bd" / archivo).read_text(encoding="utf-8")
        assert f"'{CATIMOR}', 'Arábica', 'Baja'" in texto, archivo


def test_corpus_del_asistente_explica_el_catimor():
    texto = (RAIZ / "06_agente_rag" / "documentos_fuente" / "enfermedades_y_plagas.md").read_text(encoding="utf-8")
    assert "Catimor" in texto and "Costa Rica 95" in texto and "susceptible" in texto


# ───────────────────── Índice del asistente al día ──────────────────────────
@pytest.fixture
def rag_aislado(tmp_path, monkeypatch):
    """Agente con embeddings falsos y carpetas temporales: sin red ni modelo."""
    pytest.importorskip("langchain_chroma")
    from langchain_core.embeddings import DeterministicFakeEmbedding
    sys.path.insert(0, str(RAIZ / "06_agente_rag"))
    import rag_pipeline as rag
    docs, vec = tmp_path / "docs", tmp_path / "vec"
    docs.mkdir()
    vec.mkdir()
    (docs / "a.md").write_text("# Roya\n\n" + "La roya afecta al Caturra. " * 80, encoding="utf-8")
    monkeypatch.setattr(rag, "DOCS_DIR", docs)
    monkeypatch.setattr(rag, "VECTOR_DIR", vec)
    monkeypatch.setattr(rag, "ARCHIVO_HUELLA", vec / "huella_corpus.txt")
    agente = rag.RAGAgent(collection_name="prueba_variedades")
    monkeypatch.setattr(agente, "_get_embeddings", lambda: DeterministicFakeEmbedding(size=16))
    return rag, agente, docs


def test_indice_se_marca_desactualizado_al_cambiar_el_corpus(rag_aislado):
    rag, agente, docs = rag_aislado
    assert not agente.indice_al_dia()                     # vacío
    agente.indexar()
    assert agente.indice_al_dia()
    (docs / "b.md").write_text("El Catimor (Costa Rica 95) se maneja como susceptible.", encoding="utf-8")
    assert not agente.indice_al_dia()                     # documento nuevo → hay que reindexar


def test_reindexar_no_duplica_fragmentos(rag_aislado):
    rag, agente, docs = rag_aislado
    agente.indexar()
    n = agente._get_vectorstore()._collection.count()
    agente.indexar(force=True)
    agente.indexar(force=True)
    assert agente._get_vectorstore()._collection.count() == n
    assert agente.indice_al_dia()
