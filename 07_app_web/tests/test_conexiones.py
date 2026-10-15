"""Verificación rápida de la lógica que conecta las pantallas.

    cd 07_app_web
    python -m pytest tests -q -rs      # -rs muestra el motivo de las pruebas omitidas

Usa los datos reales de ``01_datos``; cada prueba se omite si falta su archivo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cofitech import anomalias, datos, rendimiento as rend  # noqa: E402

requiere_eva = pytest.mark.skipif(not datos.RUTA_EVA_VALIDADO.exists(), reason="falta produccion_validado.csv")


@requiere_eva
def test_produccion_coincide_con_la_fuente():
    """El cargador no altera las cifras: el total de un año es el del archivo validado."""
    eva = datos.produccion_municipal()
    fuente = pd.read_csv(datos.RUTA_EVA_VALIDADO)
    for anio in (2007, 2018):
        assert eva.loc[eva["anio"] == anio, "produccion_ton"].sum() == pytest.approx(
            fuente.loc[fuente["anio"] == anio, "produccion_ton"].sum())
    assert not eva.duplicated(["codigo_dane", "anio"]).any()


@requiere_eva
def test_catalogo_usa_el_codigo_dane_de_eva():
    """El catálogo geográfico trae Salento con el código de Quimbaya; manda el de EVA."""
    catalogo = datos.catalogo_municipios()
    assert not catalogo["codigo_dane"].duplicated().any()
    salento = catalogo[catalogo["municipio"] == "Salento"]
    assert salento["codigo_dane"].tolist() == ["63690"]


@requiere_eva
def test_linea_base_cae_al_departamento_y_luego_al_pais():
    eva = datos.produccion_municipal()
    codigo = eva.loc[eva["anio"] == eva["anio"].max(), "codigo_dane"].iloc[0]
    assert rend.linea_base(codigo).nivel == "municipio"
    assert rend.linea_base("99999", "Huila").nivel == "departamento"
    assert rend.linea_base(None, "Departamento Inexistente").nivel == "nacional"
    minimo, maximo = datos.RANGO_RENDIMIENTO_TON_HA
    assert minimo <= rend.linea_base(codigo).rendimiento_ton_ha <= maximo


def test_impacto_roya_solo_con_riesgo_alto_y_variedad_no_resistente():
    base, area, precio = 1.82, 3.5, 2_745_000
    ingreso = rend.ingreso_bruto_cop(base, area, precio)
    assert ingreso == pytest.approx(base * area * 1000 / 125 * precio)

    alto = rend.impacto_roya("Alto", False, base, area, precio)
    perdida_min, perdida_max = rend.PERDIDA_ROYA_SIN_CONTROL
    assert alto.aplica
    assert alto.rendimiento_min_ton_ha == pytest.approx(base * (1 - perdida_max))
    assert alto.rendimiento_max_ton_ha == pytest.approx(base * (1 - perdida_min))
    assert (alto.perdida_cop_min, alto.perdida_cop_max) == pytest.approx((ingreso * perdida_min, ingreso * perdida_max))

    for riesgo in (None, "Bajo", "Medio"):
        assert not rend.impacto_roya(riesgo, False, base, area, precio).aplica
    assert not rend.impacto_roya("Alto", True, base, area, precio).aplica      # variedad resistente


def test_anomalias_no_usan_el_futuro():
    """Truncar la serie no puede cambiar ninguna alerta ya emitida (sin fuga de información)."""
    rng = np.random.default_rng(42)
    fechas = pd.date_range("2000-01-01", periods=240, freq="MS")
    retornos = rng.normal(0, 0.04, 240)
    retornos[150:156] *= 5                      # episodio de alta volatilidad
    precios = pd.Series(100 * np.exp(np.cumsum(retornos)), index=fechas)

    completo = anomalias.analizar(precios)
    assert completo["volatilidad_inusual"].iloc[150:160].any(), "debe detectar el episodio sembrado"
    for corte in (120, 153, 200):
        parcial = anomalias.analizar(precios.iloc[:corte])
        for columna in ("volatilidad", "umbral", "z_retorno", "volatilidad_inusual", "salto_inusual"):
            np.testing.assert_allclose(parcial[columna].astype(float),
                                       completo[columna].iloc[:corte].astype(float), equal_nan=True)


@pytest.mark.skipif(not rend.simulador_disponible(), reason="falta ml_municipal_rendimiento.pkl")
def test_simulador_devuelve_toneladas_por_hectarea():
    """El .pkl predice en kg/ha; la pantalla debe recibir ton/ha (antes mostraba 1.419 «ton/ha»)."""
    pytest.importorskip("catboost")
    try:
        valor = rend.simular_escenario(1500, 21, 150, 0.0, 900_000, 1000, "Huila", 2024, 6)
    except rend.ModeloIncompatibleError as error:
        # El entorno no es el que guardó el .pkl: no es un fallo del código.
        pytest.skip(f"{error} -> {error.comando}")
    assert 0.5 < valor < 3.0


def test_modelo_que_no_carga_explica_que_instalar(monkeypatch):
    """Un .pkl ilegible no debe mostrar el error crudo de pickle, sino qué hacer."""
    import joblib

    def _falla(_ruta):
        raise AttributeError("Can't get attribute '_RemainderColsList'")

    monkeypatch.setattr(joblib, "load", _falla)
    rend._modelo_simulado.clear()
    with pytest.raises(rend.ModeloIncompatibleError) as info:
        rend._modelo_simulado()
    rend._modelo_simulado.clear()
    assert "requirements.txt" in str(info.value)
    assert info.value.comando.startswith("python -m pip install")
