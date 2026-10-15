"""Detección de volatilidad inusual en series de precio (sin fuga de información).

Método
------
1. La serie de precios se pasa a retornos logarítmicos ``r_t = ln(P_t / P_{t-1})``:
   los precios nominales no son estacionarios y un umbral sobre el nivel solo
   detectaría la tendencia.
2. Volatilidad móvil = desviación estándar de los últimos ``ventana`` retornos.
3. El umbral de cada mes es el cuantil ``cuantil`` de la volatilidad observada
   HASTA EL MES ANTERIOR (ventana expansiva). Ningún mes se juzga con datos de
   su futuro, así que el historial de alertas es el que se habría visto en vivo.
4. Aparte, un retorno es un «salto» si su z robusto (mediana y MAD de los
   retornos previos) supera ``z_salto``.

No usa el autoencoder de NB12: ese modelo se ajustó sobre el NIVEL del precio
con un escalador calculado sobre toda la serie (incluido el futuro) y el
escalador no se guardó, así que no puede reproducirse en producción.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

VENTANA_MESES = 6          # meses de la volatilidad móvil
HISTORIA_MINIMA = 36       # meses de volatilidad previos exigidos para fijar un umbral
CUANTIL_ALERTA = 0.975     # por encima de este cuantil histórico se alerta
PERCENTIL_VIGILANCIA = 90  # desde este percentil se avisa «elevada» sin llegar a alerta
Z_SALTO = 3.0              # z robusto a partir del cual un retorno mensual es un salto


@dataclass(frozen=True)
class EstadoVolatilidad:
    """Lectura del último mes de la serie."""

    fecha: pd.Timestamp
    precio: float
    retorno: float                  # retorno logarítmico del último mes
    volatilidad: float              # desviación estándar móvil de los retornos
    umbral: Optional[float]         # None si aún no hay historia suficiente
    percentil: Optional[float]      # posición de la volatilidad actual en su historia (0–100)
    z_retorno: Optional[float]
    volatilidad_inusual: bool
    salto_inusual: bool
    meses_historia: int             # meses de volatilidad con los que se fijó el umbral

    @property
    def nivel(self) -> str:
        if self.umbral is None:
            return "Sin historia suficiente"
        if self.volatilidad_inusual:
            return "Volatilidad inusual"
        if self.salto_inusual:
            return "Movimiento brusco"
        if self.percentil is not None and self.percentil >= PERCENTIL_VIGILANCIA:
            return "Volatilidad elevada"
        return "Normal"


def analizar(
    precios: pd.Series,
    ventana: int = VENTANA_MESES,
    historia_minima: int = HISTORIA_MINIMA,
    cuantil: float = CUANTIL_ALERTA,
    z_salto: float = Z_SALTO,
) -> pd.DataFrame:
    """Calcula retornos, volatilidad móvil, umbral expansivo y alertas.

    Args:
        precios: Serie mensual de precios positivos indexada por fecha.
        ventana: Meses de la desviación estándar móvil.
        historia_minima: Meses de volatilidad previos necesarios para dar umbral.
        cuantil: Cuantil histórico que define «inusual».
        z_salto: Umbral del z robusto del retorno mensual.

    Returns:
        DataFrame por fecha con ``precio``, ``retorno``, ``volatilidad``,
        ``umbral``, ``percentil``, ``z_retorno``, ``volatilidad_inusual`` y
        ``salto_inusual``. Las columnas de umbral valen NaN mientras no haya
        historia suficiente.
    """
    precios = precios.dropna().astype(float).sort_index()
    if (precios <= 0).any():
        raise ValueError("La serie contiene precios no positivos; no admite retornos logarítmicos.")

    df = pd.DataFrame({"precio": precios})
    df["retorno"] = np.log(df["precio"]).diff()
    df["volatilidad"] = df["retorno"].rolling(ventana).std()

    # Todo lo que sigue usa SOLO el pasado: se desplaza un mes antes de acumular.
    vol_previa = df["volatilidad"].shift(1)
    df["umbral"] = vol_previa.expanding(min_periods=historia_minima).quantile(cuantil)
    df["meses_historia"] = vol_previa.expanding().count().astype(int)
    df["percentil"] = [
        _percentil(df["volatilidad"].iloc[:i].dropna().to_numpy(), v) if n >= historia_minima else np.nan
        for i, (v, n) in enumerate(zip(df["volatilidad"], df["meses_historia"]))
    ]

    ret_previo = df["retorno"].shift(1)
    mediana = ret_previo.expanding(min_periods=historia_minima).median()
    mad = (ret_previo - mediana).abs().expanding(min_periods=historia_minima).median()
    df["z_retorno"] = (df["retorno"] - mediana) / (1.4826 * mad)

    df["volatilidad_inusual"] = (df["volatilidad"] > df["umbral"]).fillna(False)
    df["salto_inusual"] = (df["z_retorno"].abs() > z_salto).fillna(False)
    return df


def estado_actual(analisis: pd.DataFrame) -> EstadoVolatilidad:
    """Resume el último mes del análisis."""
    ultimo = analisis.iloc[-1]

    def _opcional(valor: float) -> Optional[float]:
        return None if pd.isna(valor) else float(valor)

    return EstadoVolatilidad(
        fecha=analisis.index[-1],
        precio=float(ultimo["precio"]),
        retorno=float(ultimo["retorno"]),
        volatilidad=float(ultimo["volatilidad"]),
        umbral=_opcional(ultimo["umbral"]),
        percentil=_opcional(ultimo["percentil"]),
        z_retorno=_opcional(ultimo["z_retorno"]),
        volatilidad_inusual=bool(ultimo["volatilidad_inusual"]),
        salto_inusual=bool(ultimo["salto_inusual"]),
        meses_historia=int(ultimo["meses_historia"]),
    )


def _percentil(historia: np.ndarray, valor: float) -> float:
    """Porcentaje de meses previos con volatilidad menor o igual a ``valor``."""
    if np.isnan(valor) or historia.size == 0:
        return np.nan
    return float(100.0 * (historia <= valor).mean())
