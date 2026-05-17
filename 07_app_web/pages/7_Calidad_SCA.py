"""Calculadora SCA → precio estimado por kilo de café pergamino seco."""
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Calidad SCA", page_icon="☕", layout="wide")
st.title("☕ Calculadora SCA → Precio del Café")

st.markdown("""
Estima el precio que podrías recibir por tu café según el **puntaje SCA**
(Specialty Coffee Association). Útil para que el caficultor evalúe si
invertir en mejorar calidad vale la pena económicamente.
""")

# Categorías SCA
CATEGORIAS = [
    {"min": 0,  "max": 70, "nombre": "Comercial",    "factor": 0.95,
     "mercado": "Industria, café soluble, mezclas estándar",
     "color": "#9E9E9E"},
    {"min": 70, "max": 80, "nombre": "Consumo",      "factor": 1.00,
     "mercado": "Café molido nacional, supermercados",
     "color": "#8D6E63"},
    {"min": 80, "max": 85, "nombre": "Premium",      "factor": 1.20,
     "mercado": "Tostadoras nacionales especializadas",
     "color": "#FFA726"},
    {"min": 85, "max": 90, "nombre": "Especial",     "factor": 1.65,
     "mercado": "Exportación café especial",
     "color": "#43A047"},
    {"min": 90, "max": 100, "nombre": "Excepcional", "factor": 3.00,
     "mercado": "Microlotes, subastas internacionales",
     "color": "#1B5E20"},
]


def categorizar(sca: float) -> dict:
    for c in CATEGORIAS:
        if c["min"] <= sca < c["max"]:
            return c
    return CATEGORIAS[-1]


# Inputs
col1, col2 = st.columns(2)

with col1:
    sca = st.slider("Puntaje SCA de tu café",
                     min_value=60, max_value=100, value=82, step=1,
                     help="Si no lo conoces, una tostadora local puede taxearlo")
    cantidad_kg = st.number_input("Cantidad a vender (kg pergamino seco)",
                                     min_value=1, max_value=100000,
                                     value=125, step=1,
                                     help="125 kg = 1 carga estándar")

with col2:
    precio_base_carga = st.number_input(
        "Precio FNC base actual (COP / carga 125kg)",
        min_value=500_000, max_value=5_000_000,
        value=2_800_000, step=50_000,
        help="Consulta el precio de hoy en federaciondecafeteros.org")
    precio_base_kg = precio_base_carga / 125

# Cálculo
cat = categorizar(sca)
precio_kg = precio_base_kg * cat["factor"]
total = precio_kg * cantidad_kg
diferencia_vs_comercial = total - (precio_base_kg * 0.95 * cantidad_kg)

# Resultado
st.markdown("---")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Categoría", cat["nombre"])
with c2:
    st.metric("Precio estimado", f"${precio_kg:,.0f}/kg",
               delta=f"{(cat['factor']-1)*100:+.0f}% vs base")
with c3:
    st.metric("Total venta", f"${total:,.0f} COP")

st.markdown(
    f"<div style='background:{cat['color']};color:white;padding:1em;"
    f"border-radius:8px;margin:1em 0;'>"
    f"<b>Mercado objetivo:</b> {cat['mercado']}</div>",
    unsafe_allow_html=True)

if sca >= 80:
    st.success(f"💰 **Vale la pena vender este café como diferenciado.** "
                f"Estás ganando ${diferencia_vs_comercial:,.0f} COP más vs "
                f"venderlo como comercial.")
else:
    st.info("Para subir el puntaje SCA: cosecha selectiva (solo cereza roja), "
             "fermentación controlada, secado lento y limpio.")

# Tabla comparativa
st.markdown("---")
st.subheader("Comparativa de categorías SCA")
df = pd.DataFrame(CATEGORIAS)
df["rango_sca"] = df.apply(lambda r: f"{r['min']}-{r['max']}", axis=1)
df["precio_kg_estimado"] = (df["factor"] * precio_base_kg).round(0).astype(int)
df["sobreprecio"] = ((df["factor"] - 1) * 100).round(0).astype(int).astype(str) + "%"
st.dataframe(
    df[["rango_sca", "nombre", "precio_kg_estimado", "sobreprecio", "mercado"]]
    .rename(columns={
        "rango_sca": "Puntaje SCA", "nombre": "Categoría",
        "precio_kg_estimado": "COP/kg estimado", "sobreprecio": "vs base",
        "mercado": "Mercado típico"}),
    hide_index=True, use_container_width=True)

st.caption("⚠ Los factores de precio son referenciales basados en datos públicos "
            "de mercado. El precio final depende de demanda, certificaciones "
            "(orgánico, rainforest), y relación con el comprador.")
