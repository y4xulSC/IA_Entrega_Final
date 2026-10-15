"""Dashboard agroclimático — vista general del sistema café.

Fuentes (cada indicador lee la suya; ya no se adivinan columnas por nombre):
  · Producción, área y rendimiento: EVA municipal real (``cofitech.datos.produccion_municipal``).
  · Clima: maestro municipal mensual (Open-Meteo), solo donde hay cobertura.
  · Precios: series nacionales FNC / ICO / Banco Mundial.
  · ENSO: ONI medio anual.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from cofitech import datos
from cofitech.contexto_finca import obtener_contexto

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard Agroclimático del Café Colombia")

COLOR_SERIE = "#6F4E37"   # color primario de la app; una sola serie por gráfico
ctx = obtener_contexto()

eva = datos.produccion_municipal()
if eva.empty:
    st.warning("⚠ Sin datos de producción. Ejecuta el ETL para generar "
               "`01_datos/procesados/produccion_validado.csv`.")
    st.stop()

fuentes = " + ".join(sorted(eva["fuente"].unique()))
st.caption(f"Fuente: {fuentes} · {datos.miles(len(eva))} registros municipio-año · "
           f"{eva['codigo_dane'].nunique()} municipios")

# ─── Filtros ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")
    anio_min, anio_max = int(eva["anio"].min()), int(eva["anio"].max())
    rango = st.slider("Rango de años", anio_min, anio_max, (max(anio_min, 2019), anio_max))

    deptos = sorted(eva["departamento"].dropna().unique())
    # Por defecto: la zona del agrónomo; si no hay, los 5 departamentos que más producen.
    zona = [d for d in ctx.zona.departamentos if d in deptos]
    top5 = eva.groupby("departamento")["produccion_ton"].sum().nlargest(5).index.tolist()
    sel_dpto = st.multiselect("Departamentos", deptos, default=zona or sorted(top5))

df = eva[eva["anio"].between(*rango) & eva["departamento"].isin(sel_dpto)]
if df.empty:
    st.info("No hay registros para los filtros elegidos.")
    st.stop()
cod_dptos = set(df["cod_dpto"])
enso = datos.enso_anual()
enso_rango = enso[enso["anio"].between(*rango)]
precios = datos.series_precios()

# ─── KPIs ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Producción total", f"{datos.miles(df['produccion_ton'].sum())} ton",
              help="Suma de la producción municipal EVA en el rango y los departamentos elegidos.")
with c2:
    st.metric("Rendimiento promedio", f"{datos.miles(datos.rendimiento_ponderado(df), 2)} ton/ha",
              help="Producción total / área cosechada total (ponderado por área).")
with c3:
    fnc = precios.get("fnc")
    fnc_rango = fnc[(fnc.index.year >= rango[0]) & (fnc.index.year <= rango[1])] if fnc is not None else None
    if fnc_rango is not None and len(fnc_rango):
        st.metric("Precio interno medio", f"${datos.miles(fnc_rango.mean())}",
                  help=f"Precio FNC por carga de 125 kg, {fnc_rango.index.min():%Y-%m} a {fnc_rango.index.max():%Y-%m}.")
    else:
        st.metric("Precio interno medio", "—", help="La serie FNC cargada empieza en 2018.")
with c4:
    ninos = int((enso_rango["fase"] == "El Niño").sum())
    ninas = int((enso_rango["fase"] == "La Niña").sum())
    st.metric("Eventos ENSO", f"{ninos + ninas} de {len(enso_rango)} años",
              help=f"{ninos} año(s) El Niño (ONI medio mayor que +0,5) y {ninas} La Niña (menor que −0,5) en el rango.")

st.markdown("---")

# ─── Gráficos ───────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 Evolución", "🌡️ Clima", "💰 Precios"])

with tab1:
    df_evo = df.groupby("anio", as_index=False)["produccion_ton"].sum()
    fig = px.line(df_evo, x="anio", y="produccion_ton", markers=True,
                  title="Producción de café por año",
                  labels={"anio": "Año", "produccion_ton": "Producción (ton)"},
                  color_discrete_sequence=[COLOR_SERIE])
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)
    if rango[0] <= 2018 < rango[1]:
        st.caption("EVA cambia la etiqueta del estado físico entre 2018 («café verde equivalente») "
                   "y 2019 («pergamino seco»); las dos series se muestran como las publica la fuente.")

    en_rango = df[df["en_rango"]]
    fig2 = px.box(en_rango, x="departamento", y="rendimiento_ton_ha",
                  title="Distribución de rendimiento por departamento",
                  labels={"departamento": "Departamento", "rendimiento_ton_ha": "Rendimiento municipal (ton/ha)"},
                  hover_data=["municipio", "anio"], color_discrete_sequence=[COLOR_SERIE])
    st.plotly_chart(fig2, use_container_width=True)
    descartados = len(df) - len(en_rango)
    if descartados:
        st.caption(f"Se excluyen {descartados} registros con rendimiento fuera del rango físico "
                   f"{datos.RANGO_RENDIMIENTO_TON_HA[0]}–{datos.RANGO_RENDIMIENTO_TON_HA[1]} ton/ha.")

    # Municipio en foco (barra global del agrónomo) frente a su departamento.
    foco = ctx.codigo_activo
    serie_foco = eva[(eva["codigo_dane"] == foco) & eva["en_rango"] & eva["anio"].between(*rango)] if foco else eva.iloc[0:0]
    if not serie_foco.empty:
        nombre, dpto = serie_foco["municipio"].iloc[-1], serie_foco["departamento"].iloc[-1]
        del_dpto = eva[(eva["departamento"] == dpto) & eva["anio"].between(*rango)]
        comparacion = pd.concat([
            serie_foco[["anio", "rendimiento_ton_ha"]].assign(serie=nombre),
            del_dpto.groupby("anio").apply(datos.rendimiento_ponderado, include_groups=False)
                    .rename("rendimiento_ton_ha").reset_index().assign(serie=f"{dpto} (departamento)"),
        ])
        fig3 = px.line(comparacion, x="anio", y="rendimiento_ton_ha", color="serie", markers=True,
                       title=f"Rendimiento de {nombre} frente a su departamento",
                       labels={"anio": "Año", "rendimiento_ton_ha": "Rendimiento (ton/ha)", "serie": ""},
                       color_discrete_sequence=[COLOR_SERIE, "#9E9E9E"])
        fig3.update_xaxes(dtick=1)
        st.plotly_chart(fig3, use_container_width=True)


@st.cache_data(show_spinner=False)
def cargar_clima() -> pd.DataFrame:
    """Clima mensual por municipio, sin el último mes (queda a medio descargar)."""
    ruta = datos.DIR_DATOS / "procesados" / "master_cafe_municipal_mensual.csv"
    if not ruta.exists():
        return pd.DataFrame()
    clima = pd.read_csv(ruta, dtype={"codigo_dane": str}, parse_dates=["fecha"],
                        usecols=lambda c: c in {"codigo_dane", "fecha", "temp_media_c", "temp_min_c",
                                                "temp_max_c", "precipitacion_mm", "et0_mm"})
    clima["codigo_dane"] = clima["codigo_dane"].str.zfill(5)
    clima = clima[clima["fecha"] < clima["fecha"].max()]
    clima["anio"] = clima["fecha"].dt.year
    return clima


with tab2:
    clima = cargar_clima()
    if not clima.empty:
        clima = clima[clima["codigo_dane"].str[:2].isin(cod_dptos) & clima["anio"].between(*rango)]
    if clima.empty:
        st.info("No hay municipios con clima cargado en los departamentos elegidos.")
    else:
        cols_clima = [c for c in clima.columns if c not in ("codigo_dane", "fecha", "anio")]
        col_sel = st.selectbox("Variable climática", cols_clima)
        acumulable = col_sel in ("precipitacion_mm", "et0_mm")
        # Lluvia y ET0 se acumulan por municipio y año; la temperatura se promedia.
        por_mun = clima.groupby(["codigo_dane", "anio"])[col_sel].agg("sum" if acumulable else "mean")
        df_c = por_mun.groupby("anio").mean().reset_index()
        fig = px.line(df_c, x="anio", y=col_sel, markers=True,
                      title=f"Evolución de {col_sel} ({'acumulado anual' if acumulable else 'media anual'})",
                      labels={"anio": "Año"}, color_discrete_sequence=[COLOR_SERIE])
        fig.update_xaxes(dtick=1)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Promedio de {clima['codigo_dane'].nunique()} municipio(s) con clima cargado "
                   "(cabeceras municipales, Open-Meteo); no cubre todos los municipios de EVA.")

with tab3:
    if not precios:
        st.info("Sin series de precio cargadas.")
    else:
        clave = st.selectbox("Variable de precio", list(precios),
                             format_func=lambda k: datos.SERIES_PRECIO[k]["nombre"])
        serie = precios[clave]
        serie = serie[(serie.index.year >= rango[0]) & (serie.index.year <= rango[1])]
        if serie.empty:
            st.info(f"La serie cargada no tiene datos entre {rango[0]} y {rango[1]}.")
        else:
            df_p = serie.groupby(serie.index.year).mean().rename("precio").rename_axis("anio").reset_index()
            fig = px.line(df_p, x="anio", y="precio", markers=True,
                          title=f"Evolución de {datos.SERIES_PRECIO[clave]['nombre']} (media anual)",
                          labels={"anio": "Año", "precio": datos.SERIES_PRECIO[clave]["unidad"]},
                          color_discrete_sequence=[COLOR_SERIE])
            fig.update_xaxes(dtick=1)
            st.plotly_chart(fig, use_container_width=True)

# ─── Análisis ENSO ──────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🌊 Impacto de ENSO en el rendimiento")

por_anio = (df.groupby("anio").apply(datos.rendimiento_ponderado, include_groups=False)
            .rename("rendimiento_ton_ha").reset_index().merge(enso, on="anio"))
if por_anio.empty:
    st.info("No hay años con ONI y producción en el rango elegido.")
else:
    df_enso = (por_anio.groupby("fase")
               .agg(rendimiento_ton_ha=("rendimiento_ton_ha", "mean"), anios=("anio", "count"))
               .reindex(["La Niña", "Neutro", "El Niño"]).dropna().reset_index())
    df_enso["etiqueta"] = df_enso.apply(
        lambda f: f"{datos.miles(f['rendimiento_ton_ha'], 2)} ton/ha · {int(f['anios'])} año(s)", axis=1)
    fig_enso = px.bar(df_enso, x="fase", y="rendimiento_ton_ha", text="etiqueta",
                      title="Rendimiento medio según la fase ENSO del año",
                      labels={"fase": "Fase ENSO", "rendimiento_ton_ha": "Rendimiento (ton/ha)"},
                      color_discrete_sequence=[COLOR_SERIE])
    fig_enso.update_traces(width=0.45, textposition="outside", cliponaxis=False)
    st.plotly_chart(fig_enso, use_container_width=True)
    st.caption("Rendimiento ponderado por área de cada año, promediado por fase. Con pocos años por "
               "fase las diferencias no son concluyentes.")
