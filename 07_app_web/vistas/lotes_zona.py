"""Oferta de café en mi zona: la venta directa vista desde la cooperativa (RF09, criterio C2).

Agrega por municipio los lotes que los caficultores publican en «Vender mi
café»: cuántas cargas hay, qué precio piden frente al FNC y cuántos lotes son
especiales. Es la misma red de datos de campo que alimenta las alertas de roya:
el valor B2B nace de lo que reportan los asociados.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from cofitech import marca, mercado
from cofitech.contexto_finca import obtener_contexto
from cofitech.datos import normalizar
from cofitech.mercado import cop
from cofitech.telemetria import registrar_una_vez

st.set_page_config(page_title="Oferta de café en mi zona", page_icon=marca.ICONO, layout="wide")

ctx = obtener_contexto()
st.title("Oferta de café en mi zona")
st.caption("Lotes publicados por los caficultores en «Vender mi café», por municipio")

incluir_demo = st.toggle("Incluir lotes de prueba", value=False,
                         help="Los lotes simulados desde el panel de depuración no cuentan por defecto.")
tabla, fuente = mercado.lotes_por_municipio(incluir_demo)
registrar_una_vez("lotes_zona", "Mercado", "consulta_oferta_zona", {"fuente": fuente})

if ctx.zona.departamentos and not tabla.empty:
    zona = {normalizar(d) for d in ctx.zona.departamentos}
    tabla = tabla[tabla["departamento"].map(normalizar).isin(zona)]

if tabla.empty:
    st.info("Todavía no hay lotes publicados en tu zona. Cuando los caficultores publiquen en «Vender mi café», "
            "aquí verás cuántas cargas hay por municipio y a qué precio las ofrecen.")
else:
    lotes, cargas = int(tabla["lotes"].sum()), float(tabla["cargas"].sum())
    pedido = (tabla["precio_esperado_medio"] * tabla["lotes"]).sum() / lotes
    fnc = (tabla["precio_fnc_medio"] * tabla["lotes"]).sum() / lotes
    especiales = int(tabla["lotes_especiales"].sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lotes en oferta", f"{lotes}")
    c2.metric("Cargas ofrecidas", f"{cargas:,.1f}".replace(",", "§").replace(".", ",").replace("§", "."))
    c3.metric("Precio pedido medio", cop(pedido), f"{marca.pct(100 * (pedido / fnc - 1))} vs. FNC"
              if fnc else None)
    c4.metric("Lotes de café especial", f"{especiales}")

    vista = tabla.assign(
        pct_sobre_fnc=(100 * (tabla["precio_esperado_medio"] / tabla["precio_fnc_medio"] - 1)).round(1),
        ultimo_lote=pd.to_datetime(tabla["ultimo_lote"], utc=True).dt.tz_convert("America/Bogota").dt.strftime("%d/%m/%Y"),
    ).sort_values("cargas", ascending=False)
    st.dataframe(
        vista[["municipio", "departamento", "lotes", "cargas", "precio_esperado_medio", "pct_sobre_fnc",
               "lotes_especiales", "ultimo_lote"]],
        hide_index=True, width="stretch",
        column_config={
            "municipio": "Municipio", "departamento": "Departamento", "lotes": "Lotes",
            "cargas": st.column_config.ProgressColumn("Cargas", format="%.1f", min_value=0,
                                                      max_value=float(vista["cargas"].max())),
            "precio_esperado_medio": st.column_config.NumberColumn("Precio pedido (COP/carga)", format="localized"),
            "pct_sobre_fnc": st.column_config.NumberColumn("% sobre FNC", format="%.1f %%"),
            "lotes_especiales": "Especiales", "ultimo_lote": "Último lote",
        })
st.caption(f"Fuente: {fuente} · lotes en estado publicado o en negociación. Los precios son los que piden los "
           "caficultores, no precios de cierre.")

with st.expander("Compradores registrados"):
    compradores = mercado.compradores()
    st.dataframe(pd.DataFrame([{"Comprador": c.nombre, "Tipo": c.tipo, "Municipio": c.municipio,
                                "Departamento": c.departamento, "Busca": c.busca,
                                "Prima (COP/carga)": c.prima_cop_carga, "Demostración": c.es_demo}
                               for c in compradores]), hide_index=True, width="stretch")
    if any(c.es_demo for c in compradores):
        st.caption(mercado.AVISO_DEMO)
