"""Proyección de rendimiento (ton/ha), producción e ingreso.

Flujo de datos (nada se vuelve a pedir si ya está en el contexto):
  finca o municipio en foco ──► línea base EVA del municipio (dato real)
  área + precio FNC          ──► producción e ingreso
  riesgo fitosanitario       ──► descuento por roya sin tratar e impacto en pesos
El ``.pkl`` de NB09 se entrenó con datos simulados: queda como simulador de
escenarios para el agrónomo, siempre rotulado, y no alimenta la cifra principal.
"""
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from cofitech import datos, rendimiento as rend
from cofitech.telemetria import cronometro, registrar_evento_uso, registrar_una_vez
from cofitech.contexto_finca import (
    Rol, mes_anio, municipio_activo, obtener_contexto, registrar_prediccion, riesgo_fitosanitario,
)

st.set_page_config(page_title="Rendimiento", page_icon="🌱", layout="wide")
st.title("🌱 Predicción de Rendimiento del Café")

ctx = obtener_contexto()
es_caficultor = ctx.rol == Rol.CAFICULTOR
activo = municipio_activo(ctx)            # finca del caficultor o municipio en foco del agrónomo
eva = datos.produccion_municipal()

st.markdown("""
Proyecta el rendimiento (ton/ha) con el último dato que EVA reporta para el
municipio y lo convierte en producción e ingreso con el área y el precio FNC.
Si en esta sesión se detectó roya, descuenta la pérdida esperada de no tratarla.
""")


def pesos(valor: float) -> str:
    """Pesos para texto con formato (avisos, notas): el signo va escapado.

    Dos «$» en un mismo texto Markdown se interpretan como una fórmula.
    """
    return "\\$" + datos.miles(valor)


def pesos_indicador(minimo: float, maximo: float | None = None) -> str:
    """Pesos para ``st.metric``: un solo «$» y sin escape.

    Según la versión de Streamlit el valor del indicador se procesa o no como
    Markdown; con un único «$» sin barra se ve bien en ambos casos.
    """
    if maximo is None:
        return f"${datos.miles(minimo)} COP" if minimo < 1e9 else f"${datos.miles(minimo / 1e6)} millones"
    if maximo < 1e6:
        return f"${datos.miles(minimo)} – {datos.miles(maximo)}"
    return f"${datos.miles(minimo / 1e6, 1)} – {datos.miles(maximo / 1e6, 1)} millones"


def _acotar(valor, minimo, maximo, defecto):
    """Valor por defecto de un control: el del contexto si existe, dentro de sus límites."""
    return float(min(max(valor if valor is not None else defecto, minimo), maximo))


# ─── Entradas: se prellenan desde el contexto compartido ─────────────────────
with st.sidebar:
    st.header("Variables de entrada")

    if activo and activo["codigo_dane"]:
        codigo, dpto = activo["codigo_dane"], activo["departamento"]
    else:
        codigo = None
        deptos = sorted(eva["departamento"].dropna().unique()) or ["Huila"]
        sugerido = (activo or {}).get("departamento") or (ctx.zona.departamentos or ["Huila"])[0]
        coincidencias = [d for d in deptos if datos.normalizar(d) == datos.normalizar(sugerido)]
        dpto = st.selectbox("Departamento", deptos,
                            index=deptos.index(coincidencias[0]) if coincidencias else 0)

    base = rend.linea_base(codigo, dpto)

    area_defecto = ctx.finca.area_ha if es_caficultor else (base.area_cosechada_ha if base else None)
    area = st.number_input("Área cosechada (ha)", 0.1, 500000.0,
                           _acotar(area_defecto, 0.1, 500000.0, 100.0), step=0.5)
    precio_fnc = st.number_input(
        "Precio FNC actual (COP/125kg)", 500_000, 6_000_000,
        int(_acotar(ctx.mercado.precio_fnc_cop_carga, 500_000, 6_000_000, 2_000_000) // 1000 * 1000),
        step=50_000, help=f"Último precio cargado: {mes_anio(ctx.mercado.fecha)}.")

    if not es_caficultor:
        st.subheader("Simulador de escenarios")
        st.caption("Estas variables solo alimentan el simulador (modelo de datos simulados).")
        clima = ctx.clima
        temp_media = st.slider("Temperatura media (°C)", 14.0, 28.0,
                               _acotar(clima.temp_media_12m_c, 14.0, 28.0, 21.0), 0.5)
        precip = st.slider("Precipitación total semestre (mm)", 0, 5000,
                           int(_acotar((clima.precip_12m_mm or 3000.0) / 2, 0, 5000, 1500) // 50 * 50), 50)
        altitud = st.slider("Altitud (msnm)", 500, 2500,
                            int(_acotar((activo or {}).get("altitud_msnm"), 500, 2500, 1500) // 50 * 50), 50)
        oni = st.slider("Índice ONI (ENSO)", -2.5, 2.5, _acotar(clima.oni, -2.5, 2.5, 0.0), 0.1,
                        help=">+0.5 = El Niño, <-0.5 = La Niña")

if base is None:
    st.error("No hay datos de producción EVA cargados; ejecuta el ETL para proyectar el rendimiento.")
    st.stop()

# ─── Proyección: línea base real + riesgo fitosanitario ──────────────────────
# El riesgo sale de fotos de UNA finca: se descuenta en la proyección de esa finca,
# no en la de todo un municipio o departamento (vista del agrónomo).
riesgo_sesion = riesgo_fitosanitario()
riesgo = None if ctx.rol == Rol.AGRONOMO else riesgo_sesion
impacto = rend.impacto_roya(riesgo, ctx.finca.resistente_roya if es_caficultor else None,
                            base.rendimiento_ton_ha, area, precio_fnc)
produccion = base.rendimiento_ton_ha * area
ingreso = rend.ingreso_bruto_cop(base.rendimiento_ton_ha, area, precio_fnc)

col1, col2, col3 = st.columns(3)
if impacto.aplica:
    descuento = (f"-{datos.porcentaje(impacto.perdida_min)} a -{datos.porcentaje(impacto.perdida_max)} "
                 "por roya sin tratar")
    with col1:
        st.metric("Rendimiento predicho",
                  f"{datos.miles(impacto.rendimiento_min_ton_ha, 2)} – "
                  f"{datos.miles(impacto.rendimiento_max_ton_ha, 2)} ton/ha", descuento)
    with col2:
        st.metric("Producción esperada",
                  f"{datos.miles(impacto.rendimiento_min_ton_ha * area, 1)} – "
                  f"{datos.miles(impacto.rendimiento_max_ton_ha * area, 1)} ton")
    with col3:
        st.metric("Ingreso bruto estimado",
                  pesos_indicador(ingreso - impacto.perdida_cop_max, ingreso - impacto.perdida_cop_min))
    st.error(
        f"⚠ **Riesgo fitosanitario alto: roya detectada en esta sesión.** Sin roya, la proyección es "
        f"{datos.miles(base.rendimiento_ton_ha, 2)} ton/ha e ingreso bruto de {pesos(ingreso)}. "
        f"**No tratarla costaría entre {pesos(impacto.perdida_cop_min)} y "
        f"{pesos(impacto.perdida_cop_max)}** en {datos.miles(area, 1)} ha."
    )
    st.caption(f"Rango de pérdida: {rend.FUENTE_PERDIDA_ROYA} Es un escenario sin control, no un "
               "pronóstico; el diagnóstico por foto debe confirmarse con un muestreo del lote.")
else:
    with col1:
        st.metric("Rendimiento predicho", f"{datos.miles(base.rendimiento_ton_ha, 2)} ton/ha")
    with col2:
        st.metric("Producción esperada", f"{datos.miles(produccion, 1)} ton")
    with col3:
        st.metric("Ingreso bruto estimado", pesos_indicador(ingreso))
    if riesgo:
        st.info(f"Riesgo fitosanitario de la sesión: **{riesgo}**. {impacto.motivo}")
    elif riesgo_sesion == "Alto":
        st.info("Esta sesión tiene un diagnóstico de roya con riesgo alto. El descuento por roya se "
                "calcula para una finca (rol Caficultor), no para el total del municipio.")

ambito = {"municipio": "", "departamento": " (promedio del departamento: EVA no reporta el municipio)",
          "nacional": " (promedio nacional: no hay municipio ni departamento con datos)"}[base.nivel]
detalle = f"Base: rendimiento EVA {base.anio} de **{base.etiqueta}**{ambito}."
banda = rend.banda_historica()
if banda and base.nivel == "municipio":
    detalle += (f" De un año al siguiente, 8 de cada 10 municipios quedaron entre "
                f"{datos.porcentaje(banda[0], signo=True)} y {datos.porcentaje(banda[1], signo=True)} "
                "del valor anterior.")
st.caption(detalle)

if es_caficultor:
    registrar_prediccion(base.rendimiento_ton_ha, modelo=f"EVA {base.anio} · {base.etiqueta}")

# La proyección se calcula sola al abrir la pantalla: se registra una vez por
# combinación de entradas, no en cada re-ejecución de Streamlit.
registrar_una_vez(
    f"rendimiento|{ctx.rol}|{codigo or dpto}|{area}|{precio_fnc}|{riesgo}",
    "Predicción Rendimiento", "calculo_rendimiento",
    {"modelo": f"EVA {base.anio} (último dato reportado)", "nivel": base.nivel, "municipio": base.etiqueta,
     "rendimiento_ton_ha": round(base.rendimiento_ton_ha, 3), "area_ha": area,
     "penalizado_roya": impacto.aplica})

with st.expander("Ver historial EVA"):
    fig = px.line(base.historial, x="anio", y="rendimiento_ton_ha", markers=True,
                  labels={"anio": "Año", "rendimiento_ton_ha": "Rendimiento (ton/ha)"},
                  title=f"Rendimiento reportado por EVA · {base.etiqueta}",
                  color_discrete_sequence=["#6F4E37"])
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True)

# ─── ENSO ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Impacto del ENSO actual")
clima = ctx.clima
if clima.oni is not None:
    st.markdown(f"Fase vigente: **{clima.fase_legible}** (ONI {datos.miles(clima.oni, 2)}, "
                f"dato de {mes_anio(clima.fecha_enso)}).")
por_fase = (eva.groupby("anio").apply(datos.rendimiento_ponderado, include_groups=False)
            .rename("rend").reset_index().merge(datos.enso_anual(), on="anio")
            .groupby("fase")["rend"].agg(["mean", "count"]))
if not por_fase.empty:
    partes = [f"{datos.miles(por_fase.loc[f, 'mean'], 2)} ton/ha en años {f} ({int(por_fase.loc[f, 'count'])})"
              for f in ("La Niña", "Neutro", "El Niño") if f in por_fase.index]
    st.info("Rendimiento nacional EVA según la fase del año: " + ", ".join(partes) +
            ". Las diferencias son pequeñas frente a la variación entre años, así que la "
            "proyección no se ajusta por ENSO.")

# ─── Recomendaciones ─────────────────────────────────────────────────────────
st.subheader("📋 Recomendaciones agronómicas")
if impacto.aplica:
    st.write("- Roya con riesgo alto: confirma con un muestreo del lote y consulta el manejo en el asistente.")
if not es_caficultor and precip < 1000:
    st.write("- Escenario con precipitación baja — considerar riego suplementario.")
if not es_caficultor and temp_media > 24:
    st.write("- Escenario con temperatura alta — sombrar el cafetal con árboles.")
if precio_fnc > 2_500_000:
    st.write("- Precio favorable — aprovechar para vender stock.")

# ─── Simulador (solo vista técnica) ──────────────────────────────────────────
if not es_caficultor:
    st.markdown("---")
    with st.expander("🧪 Simulador de escenarios · modelo entrenado con datos simulados"):
        st.warning(
            "`ml_municipal_rendimiento.pkl` (NB09) se entrenó con 120 municipios generados por una "
            "fórmula, no con EVA. Muestra cómo respondería un modelo a un escenario; **su resultado "
            "no es una estimación del rendimiento real**."
        )
        if not rend.simulador_disponible():
            st.info(f"No se encontró el modelo en `{rend.RUTA_MODELO_SIMULADO.name}`.")
        elif st.button("🔮 Predecir rendimiento", type="primary"):
            try:
                hoy = date.today()
                with cronometro() as tiempo:
                    simulado = rend.simular_escenario(
                        altitud_msnm=altitud, temp_media_c=temp_media, precip_mensual_mm=precip / 6,
                        oni=oni, precio_cop_carga=precio_fnc, area_ha=area, departamento=dpto,
                        anio=hoy.year, mes=hoy.month)
                registrar_evento_uso("Predicción Rendimiento", "simulacion_ejecutada", {
                    "modelo": rend.RUTA_MODELO_SIMULADO.name, "datos_entrenamiento": "simulados",
                    "resultado_ton_ha": round(simulado, 3), **tiempo})
                st.metric("Escenario simulado", f"{datos.miles(simulado, 2)} ton/ha",
                          help="Salida del modelo en kg/ha convertida a ton/ha.")
                st.caption(f"Modelo usado: `{rend.RUTA_MODELO_SIMULADO.name}` · precipitación mensual "
                           f"equivalente: {precip / 6:.0f} mm.")
            except rend.ModeloIncompatibleError as error:   # entorno distinto al que guardó el .pkl
                st.error(f"El simulador no puede ejecutarse en este entorno. {error}")
                if error.comando:
                    st.code(error.comando, language="bash")
            except Exception as error:
                st.error(f"El modelo no pudo evaluarse: {error}")

st.markdown("---")
st.caption("⚠ Este es un sistema de apoyo a la decisión. La proyección repite el último dato "
           "reportado y puede desviarse — consultar el extensionista FNC.")
