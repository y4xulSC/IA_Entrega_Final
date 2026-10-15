"""Escenarios de precio del café: simulador Ridge validado + modelos recurrentes en calibración.

* **Simulador Ridge** (``cofitech/precios_ridge.py``): precio interno FNC en
  función del arábica internacional y la TRM del mismo mes. Validado en los
  últimos 24 meses contra la referencia ingenua.
* **Modelos Experimentales de Alta Volatilidad (En calibración)**: BiGRU,
  LSTM y Transformer de NB10. No se ejecutan aquí porque sus escaladores y
  ventanas no se guardaron con los ``.keras``; se muestra su estado y una
  curva de tendencia reciente rotulada como referencia, no como pronóstico.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cofitech import precios_ridge
from cofitech.contexto_finca import mes_anio
from cofitech.telemetria import cronometro, registrar_evento_uso

st.set_page_config(page_title="Precios", page_icon="💰", layout="wide")
st.title("💰 Escenarios de precio del café")

PROJECT = Path(__file__).resolve().parents[2]
DIR_MOD = PROJECT / "04_modelos_entrenados"


def _cop(valor: float) -> str:
    return f"${valor:,.0f}".replace(",", ".")


def _mes(fecha) -> str:
    """``Timestamp('2025-12-01')`` -> ``'dic 2025'`` (en español, sin depender del locale)."""
    return mes_anio(pd.Timestamp(fecha).date())


def _pct(valor: float) -> str:
    return f"{valor:.1%}".replace(".", ",")


# ───────────────────────────── Histórico ────────────────────────────────────
@st.cache_data
def cargar_historico() -> pd.DataFrame | None:
    ruta = PROJECT / "01_datos" / "procesados" / "precios_validado.csv"
    if not ruta.exists():
        return None
    return pd.read_csv(ruta, parse_dates=["fecha"]).sort_values("fecha")


df = cargar_historico()
if df is None:
    st.error("Sin datos de precios (`01_datos/procesados/precios_validado.csv`).")
    st.stop()

fnc = df.dropna(subset=["precio_fnc_cop_kg"])
fig = go.Figure(go.Scatter(x=fnc["fecha"], y=fnc["precio_fnc_cop_kg"] * 125, name="Precio interno FNC",
                           line=dict(color="#3E2723")))
fig.update_layout(title="Precio interno de referencia FNC (COP por carga de 125 kg)", height=360,
                  xaxis_title=None, yaxis_title="COP por carga", margin=dict(t=50, b=20))
st.plotly_chart(fig, use_container_width=True)
st.caption(f"Fuente: FNC (precio interno), Banco de la República (TRM), ICO (arábica Brasil) · "
           f"{_mes(fnc['fecha'].min())} – {_mes(fnc['fecha'].max())}.")

tab_ridge, tab_rnn = st.tabs(["Simulador Ridge (validado)",
                              "Modelos Experimentales de Alta Volatilidad (En calibración)"])

# ───────────────────────────── Simulador Ridge ──────────────────────────────
with tab_ridge:
    sim = precios_ridge.simulador()
    if sim is None:
        st.warning("No hay suficientes meses con precio FNC, arábica y TRM para entrenar el simulador.")
    else:
        v = sim.validacion
        st.markdown(
            "**¿A cómo pagaría la FNC si cambian el precio internacional o el dólar?** El modelo Ridge relaciona "
            "el precio interno con el arábica (Brasil, USD/kg) y la TRM **del mismo mes**: sirve para simular "
            "escenarios, no para adivinar el precio del próximo mes."
        )
        ult = sim.ultimo
        col_a, col_t = st.columns(2)
        arabica = col_a.slider("Arábica Brasil (USD/kg)", 1.0, 12.0, float(round(ult["precio_arabica_brasil_usd_kg"], 2)),
                               0.05, help=f"Último dato: {ult['precio_arabica_brasil_usd_kg']:.2f} ({_mes(ult['fecha'])}).")
        trm = col_t.slider("TRM (COP por USD)", 3000, 5500, int(round(ult["trm_cop_usd"], -1)), 10,
                           help=f"Último dato: {ult['trm_cop_usd']:,.0f} ({_mes(ult['fecha'])}).".replace(",", "."))
        with cronometro() as tiempo:
            estimado, minimo, maximo = sim.precio_carga(arabica, trm)
        actual = float(ult[precios_ridge.OBJETIVO]) * precios_ridge.KG_POR_CARGA

        c1, c2, c3 = st.columns(3)
        c1.metric("Precio estimado por carga", _cop(estimado), f"{estimado / actual - 1:+.1%} vs. último real".replace(".", ","))
        c2.metric("Rango probable (90 %)", f"{_cop(minimo)} – {_cop(maximo)}")
        c3.metric(f"Último precio real ({_mes(ult['fecha'])})", _cop(actual))
        if st.session_state.get("_precios_ultimo_escenario") != (arabica, trm):
            st.session_state["_precios_ultimo_escenario"] = (arabica, trm)
            registrar_evento_uso("Predicción Precios", "simulacion_ridge", {
                "arabica_usd_kg": arabica, "trm": trm, "precio_carga": round(estimado), **tiempo})

        st.subheader("Validación en el tiempo")
        st.caption(f"Entrenado sin los últimos {precios_ridge.MESES_PRUEBA} meses y evaluado en ellos "
                   f"({_mes(v.desde)} – {_mes(v.hasta)}). Referencia ingenua: repetir el precio del mes anterior.")
        tabla = pd.DataFrame({
            "Modelo": ["Ridge (arábica + TRM)", "Referencia ingenua (mes anterior)"],
            "R²": [v.r2, v.r2_ingenuo],
            "Error medio (MAPE)": [v.mape, v.mape_ingenuo],
        })
        st.dataframe(tabla, hide_index=True, use_container_width=True, column_config={
            "R²": st.column_config.NumberColumn(format="%.3f"),
            "Error medio (MAPE)": st.column_config.NumberColumn(format="percent")})
        fig_v = go.Figure()
        for col, nombre, estilo in (("real", "Real", dict(color="#3E2723")),
                                    ("ridge", "Ridge", dict(color="#2E7D32", dash="dash")),
                                    ("ingenuo", "Mes anterior", dict(color="#9E9E9E", dash="dot"))):
            fig_v.add_trace(go.Scatter(x=v.tabla["fecha"], y=v.tabla[col], name=nombre, line=estilo))
        fig_v.update_layout(height=320, yaxis_title="COP por carga", margin=dict(t=20, b=20))
        st.plotly_chart(fig_v, use_container_width=True)
        efecto_arabica = f"{10 * sim.elasticidades['arábica']:.1f}".replace(".", ",")
        efecto_trm = f"{10 * sim.elasticidades['TRM']:.1f}".replace(".", ",")
        veredicto = "El Ridge supera" if v.supera_referencia else "El Ridge NO supera"
        st.caption(
            f"{veredicto} a la referencia ingenua en el periodo de prueba. Elasticidades: si el arábica sube "
            f"10 %, el precio interno sube ≈ {efecto_arabica} %; si la TRM sube 10 %, ≈ {efecto_trm} %. "
            f"Entrenado con {sim.meses_entrenamiento} meses."
        )

# ──────────────────── Modelos recurrentes (en calibración) ──────────────────
with tab_rnn:
    st.warning(
        "**Modelos Experimentales de Alta Volatilidad (En calibración).** Las redes recurrentes de NB10 no se "
        "usan para decidir: en la 2.ª entrega el BiGRU obtuvo R² = −2,12 (peor que repetir el último precio) y "
        "el alza de 2024–2025 quedó fuera del rango de entrenamiento. Además, sus escaladores y ventanas de "
        "entrada no se guardaron junto a los archivos `.keras`, así que no se pueden ejecutar de forma confiable aquí."
    )
    modelos = [("BiGRU", "rnn_bigru.keras"), ("LSTM apilada", "rnn_lstm_apilada.keras"),
               ("LSTM + atención", "rnn_lstm_atención.keras"), ("Transformer", "rnn_transformer.keras")]
    st.dataframe(pd.DataFrame({
        "Modelo": [m for m, _ in modelos],
        "Archivo": [a for _, a in modelos],
        "Disponible": ["Sí" if (DIR_MOD / a).exists() else "No" for _, a in modelos],
        "Estado": ["En calibración: falta guardar escalador y ventana; validar contra la referencia ingenua"] * len(modelos),
    }), hide_index=True, use_container_width=True)

    st.markdown("**Referencia visual: tendencia reciente amortiguada** (no es un modelo entrenado)")
    horizonte = st.slider("Meses hacia adelante", 1, 12, 3)
    serie = fnc.set_index("fecha")["precio_fnc_cop_kg"] * 125
    tendencia = serie.diff().tail(3).mean()
    volatilidad = float(serie.diff().tail(12).std())
    fechas = pd.date_range(serie.index[-1] + pd.DateOffset(months=1), periods=horizonte, freq="MS")
    curva = serie.iloc[-1] + np.cumsum([tendencia * 0.8 ** i for i in range(horizonte)])
    banda = 1.645 * volatilidad * np.sqrt(np.arange(1, horizonte + 1))
    fig_t = go.Figure([
        go.Scatter(x=serie.index[-36:], y=serie.iloc[-36:], name="Histórico", line=dict(color="#3E2723")),
        go.Scatter(x=fechas, y=curva, name="Tendencia amortiguada", line=dict(color="#D84315", dash="dash")),
        go.Scatter(x=list(fechas) + list(fechas[::-1]), y=list(curva + banda) + list((curva - banda)[::-1]),
                   fill="toself", fillcolor="rgba(216,67,21,0.15)", line=dict(width=0), name="Banda de volatilidad"),
    ])
    fig_t.update_layout(height=360, yaxis_title="COP por carga", margin=dict(t=20, b=20))
    st.plotly_chart(fig_t, use_container_width=True)

st.divider()
st.caption("Los escenarios son estimaciones, no garantías de precio. El alza de 2024–2025 mostró que los eventos "
           "atípicos pueden salirse del rango histórico de cualquier modelo.")
