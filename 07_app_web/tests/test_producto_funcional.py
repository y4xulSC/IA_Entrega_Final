"""Grad-CAM, orientación de manejo de roya y simulador Ridge.

    cd 07_app_web
    python -m pytest tests/test_producto_funcional.py -q -rs
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from cofitech import precios_ridge, prescripcion, vision  # noqa: E402

# ───────────────────────────── Prescripción ─────────────────────────────────
@pytest.mark.parametrize("incidencia, resistente, nivel", [
    (None, False, "sin_dato"),
    (0.0, False, "preventivo"),
    (4.9, None, "preventivo"),
    (5.0, False, "sistemico"),
    (32.0, False, "sistemico"),
    (32.0, True, "resistente"),
])
def test_nivel_segun_incidencia_y_variedad(incidencia, resistente, nivel):
    r = prescripcion.recomendacion_roya(incidencia, resistente)
    assert r.nivel == nivel
    assert r.fuente.endswith("Boletines Técnicos Cenicafé)")


def test_preventivo_es_cobre_y_sistemico_es_triazol_con_carencia_y_epp():
    preventivo = prescripcion.recomendacion_roya(2.0, False)
    sistemico = prescripcion.recomendacion_roya(12.0, False)
    assert any("oxicloruro de cobre" in a for a in preventivo.acciones)
    assert any("triazoles" in a for a in sistemico.acciones)
    for r in (preventivo, sistemico):
        texto = " ".join(r.advertencias)
        assert "carencia" in texto and "ICA" in texto and "Protección personal" in texto


def test_incidencia_fuera_de_rango():
    with pytest.raises(ValueError):
        prescripcion.recomendacion_roya(120.0)


# Cifra + unidad de dosis o de carencia: «2 cc/L», «500 g por hectárea», «30 días de carencia»...
_DOSIS = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:cc|ml|mL|g|gr|gramos|kg|l|L|litros?)\s*(?:/|por)\s*\w+"
                    r"|\b\d+\s*d[ií]as\s+(?:de\s+)?carencia|carencia\s+(?:de\s+)?\d+\s*d[ií]as", re.I)


@pytest.mark.parametrize("ruta", [
    APP / "cofitech" / "prescripcion.py", APP / "cofitech" / "calendario.py",
    APP / "pages" / "4_Enfermedades.py", APP / "pages" / "8_Asesor_Caficultor.py",
])
def test_sin_dosis_ni_carencias_quemadas_en_el_codigo(ruta):
    assert not _DOSIS.findall(ruta.read_text(encoding="utf-8"))


# ─────────────────────────────── Grad-CAM ───────────────────────────────────
def _modelo_como_nb08(tf, anidado: bool = True):
    """Réplica pequeña de la arquitectura de NB08 (base convolucional anidada + dos salidas)."""
    layers = tf.keras.layers
    entrada_base = layers.Input((224, 224, 3))
    x = layers.Conv2D(8, 3, strides=4, activation="relu")(entrada_base)
    x = layers.Conv2D(16, 3, strides=4, activation="relu", name="ultima_conv")(x)
    entrada = layers.Input((224, 224, 3))
    if anidado:
        mapa = tf.keras.Model(entrada_base, x, name="base_cnn")(entrada)
    else:
        mapa = layers.Conv2D(16, 3, strides=16, activation="relu")(entrada)
    y = layers.GlobalAveragePooling2D()(mapa)
    y = layers.Dense(8, activation="relu")(y)
    clase = layers.Dense(len(vision.CLASES), activation="softmax", name="clase")(y)
    severidad = layers.Dense(1, activation="sigmoid", name="severidad")(y)
    return tf.keras.Model(entrada, [clase, severidad])


@pytest.mark.parametrize("anidado", [True, False])
def test_gradcam_da_un_mapa_normalizado_del_tamano_de_la_entrada(anidado):
    tf = pytest.importorskip("tensorflow")
    tf.keras.utils.set_random_seed(0)
    modelo = _modelo_como_nb08(tf, anidado)
    foto = Image.fromarray((np.random.default_rng(0).random((300, 400, 3)) * 255).astype("uint8"))
    r = vision.diagnosticar(modelo, foto)
    assert r.clase in vision.CLASES
    assert sum(r.probabilidades.values()) == pytest.approx(1.0, abs=1e-4)
    assert r.mapa.shape == (224, 224)
    assert 0.0 <= r.mapa.min() and r.mapa.max() <= 1.0 + 1e-6
    assert r.superpuesta.size == foto.size


def test_modelo_con_otro_numero_de_clases_se_rechaza():
    tf = pytest.importorskip("tensorflow")
    entrada = tf.keras.layers.Input((224, 224, 3))
    salida = tf.keras.layers.Dense(4, activation="softmax")(tf.keras.layers.GlobalAveragePooling2D()(entrada))
    with pytest.raises(ValueError, match="clases"):
        vision.diagnosticar(tf.keras.Model(entrada, salida), Image.new("RGB", (50, 50)), con_gradcam=False)


# ─────────────────────────────── Ridge ──────────────────────────────────────
requiere_precios = pytest.mark.skipif(not precios_ridge.RUTA_PRECIOS.exists(), reason="falta precios_validado.csv")


@requiere_precios
def test_ridge_validado_en_el_tiempo_supera_la_referencia_ingenua():
    sim = precios_ridge.entrenar(precios_ridge._datos())
    v = sim.validacion
    assert len(v.tabla) == precios_ridge.MESES_PRUEBA
    assert v.tabla["fecha"].min() == v.desde                 # la prueba es el tramo final de la serie
    assert v.supera_referencia and v.r2 > 0.8


@requiere_precios
def test_ridge_responde_en_la_direccion_esperada():
    sim = precios_ridge.entrenar(precios_ridge._datos())
    base, minimo, maximo = sim.precio_carga(5.0, 4000)
    assert minimo < base < maximo
    assert sim.precio_carga(6.0, 4000)[0] > base             # arábica más caro → precio interno más alto
    assert sim.precio_carga(5.0, 4500)[0] > base             # dólar más caro → precio interno más alto


def test_ridge_exige_historia_suficiente():
    import pandas as pd
    corto = pd.DataFrame({"fecha": pd.date_range("2020-01-01", periods=30, freq="MS"),
                          "precio_fnc_cop_kg": 1e4, "precio_arabica_brasil_usd_kg": 4.0, "trm_cop_usd": 4000.0})
    with pytest.raises(ValueError, match="meses"):
        precios_ridge.entrenar(corto)
