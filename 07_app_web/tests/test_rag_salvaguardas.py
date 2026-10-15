"""Reglas de prescripción del agente RAG verificadas en código (sin LLM ni red).

    cd 07_app_web
    python -m pytest tests -q -rs
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "06_agente_rag"))
pytest.importorskip("dotenv")
import rag_pipeline as rag  # noqa: E402


@pytest.mark.parametrize("texto", [
    "Aplique ciproconazol 250 cc/ha.",
    "Use 1 L por hectárea de oxicloruro de cobre.",
    "Abone con 200-300 g por planta.",
    "Dosis típica 800-1200 kg NPK 17-6-18-2 por hectárea/año.",
    "Mezcle 3 cc por litro de agua.",
    "La dosis recomendada es de 2,5 kg del producto.",
    "Tiene un periodo de carencia de 21 días.",
    "Espere 30 días de carencia antes de cosechar.",
])
def test_detecta_dosis_y_carencias(texto):
    assert rag.contiene_dosis(texto)


@pytest.mark.parametrize("texto", [
    "Si más del 5 % de las hojas tiene roya, consulte al extensionista.",
    "Muestree 60 árboles por lote.",
    "Su finca está a 1.500 msnm y tiene 2 ha de café.",
    "Aplique entre los 60 y 150 días después de la floración.",
    "La variedad Castillo es resistente.",
])
def test_no_confunde_umbrales_ni_datos_de_la_finca_con_dosis(texto):
    assert not rag.contiene_dosis(texto)


def test_sin_fuente_validada_retira_la_dosis_y_responde_con_el_respaldo():
    respuesta = ("Para la roya realice podas sanitarias [enfermedades_y_plagas.md]. "
                 "Aplique ciproconazol 250 cc/ha cada 60 días.\n- Renueve con variedad Castillo.")
    texto, aplicadas = rag.aplicar_salvaguardas(respuesta, hay_fuente_validada=False)
    assert "250 cc" not in texto
    assert "podas sanitarias" in texto and "Castillo" in texto
    assert rag.FALLBACK_DOSIS in texto
    assert "dosis_retirada" in aplicadas
    # La única frase con el fungicida se retiró: no queda producto que advertir.
    assert aplicadas == ["dosis_retirada"]


def test_con_fuente_validada_conserva_la_dosis_pero_exige_carencia_y_epp():
    texto, aplicadas = rag.aplicar_salvaguardas("Ciproconazol 250 cc/ha [cenicafe/bot036.pdf].", True)
    assert "250 cc/ha" in texto and rag.ADVERTENCIA_QUIMICOS in texto
    assert aplicadas == ["advertencia_quimicos"]


def test_no_duplica_advertencias_que_ya_estan():
    respuesta = ("Use oxicloruro de cobre según la etiqueta; respete el periodo de carencia y use EPP. "
                 "Fertilice según el análisis de suelos.")
    texto, aplicadas = rag.aplicar_salvaguardas(respuesta, False)
    assert texto == respuesta and aplicadas == []


def test_fertilizacion_sin_analisis_de_suelos_agrega_la_nota():
    texto, aplicadas = rag.aplicar_salvaguardas("Fertilice con potasio después de la cosecha.", False)
    assert rag.NOTA_SUELOS in texto and aplicadas == ["nota_analisis_suelos"]


def test_respaldo_no_se_repite_si_el_modelo_ya_lo_escribio():
    texto, _ = rag.aplicar_salvaguardas(f"{rag.FALLBACK_DOSIS} Use 1 L/ha.", False)
    assert texto.count(rag.FALLBACK_DOSIS) == 1


def test_fuentes_validadas_por_carpeta():
    assert rag.es_fuente_validada("cenicafe/bot036.pdf")
    assert rag.es_fuente_validada("cenicafe\\avance_586.pdf")          # ruta de Windows
    assert not rag.es_fuente_validada("buenas_practicas_cafe.md")


def test_cita_cenicafe_solo_con_documento_validado():
    sin = rag.citar_fuentes("Respuesta", ["enfermedades_y_plagas.md"], [])
    con = rag.citar_fuentes("Respuesta", ["cenicafe/bot036.pdf", "glosario.md"], ["cenicafe/bot036.pdf"])
    assert rag.CITA_CENICAFE not in sin and "no validado por Cenicafé" in sin
    assert rag.CITA_CENICAFE in con and "glosario.md" in con
