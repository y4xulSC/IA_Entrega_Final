"""Detección de anomalías: ¿el precio está en una zona de volatilidad inusual?

Consume las series mensuales de precio (interno FNC, compuesto ICO y una
referencia larga del Banco Mundial) y aplica ``cofitech.anomalias``: retornos
logarítmicos, volatilidad móvil y un umbral que cada mes se calcula solo con
la historia anterior.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from cofitech import anomalias, datos

COLOR_SERIE = "#6F4E37"     # color primario de la app
COLOR_ALERTA = "#C62828"    # estado crítico (siempre acompañado de etiqueta)
COLOR_UMBRAL = "#757575"

st.title("Detección de anomalías de precio")

series = datos.series_precios()
if not series:
    st.warning("Sin series de precio. Ejecuta el ETL para generar `precios_validado.csv`.")
    st.stop()

clave = st.radio("Serie", list(series), horizontal=True,
                 format_func=lambda k: datos.SERIES_PRECIO[k]["nombre"])
precio, unidad = series[clave], datos.SERIES_PRECIO[clave]["unidad"]

analisis = anomalias.analizar(precio)
estado = anomalias.estado_actual(analisis)
fecha = f"{estado.fecha:%m/%Y}"

# ─── Lectura del último mes ──────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Precio · {fecha}", datos.miles(estado.precio, 0 if estado.precio > 1000 else 2), help=unidad)
c2.metric("Variación del mes", datos.porcentaje(estado.retorno, 1, signo=True), help="Retorno logarítmico frente al mes anterior.")
c3.metric(f"Volatilidad · {anomalias.VENTANA_MESES} meses", datos.porcentaje(estado.volatilidad, 1),
          help="Desviación estándar de los retornos mensuales de la ventana.")
c4.metric("Posición en su historia", "—" if estado.percentil is None else f"percentil {estado.percentil:.0f}",
          help="Porcentaje de meses anteriores con volatilidad menor o igual a la actual.")

mensajes = {
    "Volatilidad inusual": (st.error, "🔴 **Volatilidad inusual.** La volatilidad actual supera el percentil "
                                      f"{datos.porcentaje(anomalias.CUANTIL_ALERTA, 1)} de toda su historia previa."),
    "Movimiento brusco": (st.error, "🔴 **Movimiento brusco.** La variación del último mes es atípica frente "
                                    "a las variaciones mensuales anteriores."),
    "Volatilidad elevada": (st.warning, "🟠 **Volatilidad elevada.** Está por encima del percentil "
                                        f"{anomalias.PERCENTIL_VIGILANCIA} de su historia, sin llegar al umbral de alerta."),
    "Normal": (st.success, "🟢 **Normal.** La volatilidad está dentro de lo observado históricamente."),
    "Sin historia suficiente": (st.info, f"La serie aún no tiene {anomalias.HISTORIA_MINIMA} meses de "
                                         "volatilidad previa para fijar un umbral."),
}
avisar, texto = mensajes[estado.nivel]
avisar(f"{texto} Último dato: {fecha}.")

# ─── Precio con los meses en alerta ──────────────────────────────────────────
alertas = analisis[analisis["volatilidad_inusual"] | analisis["salto_inusual"]]
fig = go.Figure()
fig.add_trace(go.Scatter(x=analisis.index, y=analisis["precio"], name="Precio", mode="lines",
                         line=dict(color=COLOR_SERIE, width=2)))
fig.add_trace(go.Scatter(x=alertas.index, y=alertas["precio"], name="Mes en alerta", mode="markers",
                         marker=dict(color=COLOR_ALERTA, size=9, line=dict(color="white", width=2))))
fig.update_layout(title=datos.SERIES_PRECIO[clave]["nombre"], yaxis_title=unidad, height=380,
                  hovermode="x unified", legend=dict(orientation="h", y=1.12, x=0))
st.plotly_chart(fig, use_container_width=True)

# ─── Volatilidad frente a su umbral (gráfico aparte: otra escala) ────────────
fig_v = go.Figure()
fig_v.add_trace(go.Scatter(x=analisis.index, y=analisis["volatilidad"], name="Volatilidad móvil",
                           mode="lines", line=dict(color=COLOR_SERIE, width=2)))
fig_v.add_trace(go.Scatter(x=analisis.index, y=analisis["umbral"], mode="lines",
                           name=f"Umbral (percentil {datos.porcentaje(anomalias.CUANTIL_ALERTA, 1)} de la historia previa)",
                           line=dict(color=COLOR_UMBRAL, width=1.5, dash="dash")))
fig_v.update_layout(title=f"Volatilidad de {anomalias.VENTANA_MESES} meses", height=320,
                    yaxis=dict(title="Desv. estándar de retornos mensuales", tickformat=".0%", rangemode="tozero"),
                    hovermode="x unified", legend=dict(orientation="h", y=1.15, x=0))
st.plotly_chart(fig_v, use_container_width=True)

with st.expander(f"Meses en alerta ({len(alertas)})"):
    if alertas.empty:
        st.write("Ningún mes de esta serie ha superado los umbrales.")
    else:
        tabla = alertas[["precio", "retorno", "volatilidad", "umbral", "z_retorno"]].copy()
        tabla.insert(0, "mes", alertas.index.strftime("%Y-%m"))
        tabla["motivo"] = [
            " + ".join(m for m, activo in (("volatilidad", v), ("salto", s)) if activo)
            for v, s in zip(alertas["volatilidad_inusual"], alertas["salto_inusual"])
        ]
        st.dataframe(tabla.iloc[::-1], hide_index=True, use_container_width=True, column_config={
            "mes": "Mes", "precio": st.column_config.NumberColumn("Precio", format="%.2f"),
            "retorno": st.column_config.NumberColumn("Variación", format="percent"),
            "volatilidad": st.column_config.NumberColumn("Volatilidad", format="percent"),
            "umbral": st.column_config.NumberColumn("Umbral", format="percent"),
            "z_retorno": st.column_config.NumberColumn("z robusto", format="%.1f"),
            "motivo": "Motivo",
        })

st.caption(
    f"Método: retornos logarítmicos mensuales, desviación estándar móvil de {anomalias.VENTANA_MESES} meses y "
    f"umbral igual al percentil {datos.porcentaje(anomalias.CUANTIL_ALERTA, 1)} de la volatilidad observada hasta el mes anterior "
    f"(sin usar datos futuros). El umbral actual se apoya en {estado.meses_historia} meses de historia"
    + ("; con menos de 10 años las alertas son poco estables." if estado.meses_historia < 120 else ".")
)
