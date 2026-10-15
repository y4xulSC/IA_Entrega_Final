"""Simulador Ridge del precio interno FNC a partir del precio internacional y la TRM.

Modelo (log-log, por eso los coeficientes se leen como elasticidades)::

    log(precio FNC COP/kg) = b0 + b1·log(arábica Brasil USD/kg) + b2·log(TRM COP/USD)

* Es un **simulador de escenarios**, no un pronóstico: usa el precio
  internacional y la TRM del mismo mes. Responde «si el arábica estuviera en X
  y el dólar en Y, ¿a cómo pagaría la FNC?».
* Se valida en el tiempo: se entrena con todos los meses menos los últimos 24
  y se evalúa en esos 24 (sin mezclar futuro y pasado), comparando con la
  referencia ingenua «el precio del mes anterior».
* Se entrena al vuelo (96 meses, milisegundos), así que no hay ``.pkl`` que
  dependa de la versión de scikit-learn instalada.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

PROYECTO: Path = Path(__file__).resolve().parents[2]
RUTA_PRECIOS: Path = PROYECTO / "01_datos" / "procesados" / "precios_validado.csv"

OBJETIVO = "precio_fnc_cop_kg"
VARIABLES = ("precio_arabica_brasil_usd_kg", "trm_cop_usd")
MESES_PRUEBA = 24
ALFA = 1.0
KG_POR_CARGA = 125


@dataclass(frozen=True)
class Validacion:
    desde: pd.Timestamp
    hasta: pd.Timestamp
    r2: float
    mape: float
    r2_ingenuo: float
    mape_ingenuo: float
    tabla: pd.DataFrame              # fecha, real, ridge, ingenuo (COP/carga)

    @property
    def supera_referencia(self) -> bool:
        return self.mape < self.mape_ingenuo


@dataclass(frozen=True)
class Simulador:
    modelo: object                   # sklearn Ridge
    validacion: Validacion
    elasticidades: dict[str, float]
    error_relativo_std: float        # desviación del error en escala log (para el rango)
    ultimo: pd.Series                # última fila con datos completos
    meses_entrenamiento: int

    def precio_carga(self, arabica_usd_kg: float, trm: float) -> tuple[float, float, float]:
        """``(estimado, mínimo, máximo)`` en COP por carga de 125 kg; rango ≈ 90 %."""
        x = np.log([[arabica_usd_kg, trm]])
        centro = float(self.modelo.predict(x)[0])
        margen = 1.645 * self.error_relativo_std
        return tuple(float(np.exp(v)) * KG_POR_CARGA for v in (centro, centro - margen, centro + margen))


def _datos(ruta: Path = RUTA_PRECIOS) -> pd.DataFrame:
    df = pd.read_csv(ruta, parse_dates=["fecha"])
    df = df.dropna(subset=[OBJETIVO, *VARIABLES]).sort_values("fecha").reset_index(drop=True)
    return df[(df[[OBJETIVO, *VARIABLES]] > 0).all(axis=1)]


def entrenar(df: pd.DataFrame, meses_prueba: int = MESES_PRUEBA, alfa: float = ALFA) -> Simulador:
    """Valida con los últimos ``meses_prueba`` y reentrena con toda la serie para simular."""
    from sklearn.linear_model import Ridge
    from sklearn.metrics import mean_absolute_percentage_error, r2_score

    if len(df) < meses_prueba + 24:
        raise ValueError(f"Hacen falta al menos {meses_prueba + 24} meses con datos completos; hay {len(df)}.")
    X = np.log(df[list(VARIABLES)].to_numpy())
    y = np.log(df[OBJETIVO].to_numpy())
    corte = len(df) - meses_prueba

    modelo_val = Ridge(alpha=alfa).fit(X[:corte], y[:corte])
    real = df[OBJETIVO].to_numpy()[corte:]
    ridge = np.exp(modelo_val.predict(X[corte:]))
    ingenuo = df[OBJETIVO].shift(1).to_numpy()[corte:]
    validacion = Validacion(
        desde=df["fecha"].iloc[corte], hasta=df["fecha"].iloc[-1],
        r2=float(r2_score(real, ridge)), mape=float(mean_absolute_percentage_error(real, ridge)),
        r2_ingenuo=float(r2_score(real, ingenuo)), mape_ingenuo=float(mean_absolute_percentage_error(real, ingenuo)),
        tabla=pd.DataFrame({"fecha": df["fecha"].iloc[corte:].to_numpy(), "real": real * KG_POR_CARGA,
                            "ridge": ridge * KG_POR_CARGA, "ingenuo": ingenuo * KG_POR_CARGA}),
    )
    errores_log = y[corte:] - modelo_val.predict(X[corte:])

    modelo = Ridge(alpha=alfa).fit(X, y)
    return Simulador(
        modelo=modelo, validacion=validacion,
        elasticidades={"arábica": float(modelo.coef_[0]), "TRM": float(modelo.coef_[1])},
        error_relativo_std=float(np.std(errores_log, ddof=1)),
        ultimo=df.iloc[-1], meses_entrenamiento=len(df),
    )


@st.cache_resource(show_spinner=False)
def simulador() -> Simulador | None:
    """Simulador entrenado con ``precios_validado.csv``; ``None`` si no hay datos suficientes."""
    if not RUTA_PRECIOS.exists():
        return None
    try:
        return entrenar(_datos())
    except ValueError:
        return None
