"""Asesor del Caficultor — recordatorios mensuales, alertas y buenas prácticas.
Pensado para asociaciones de pequeños caficultores (caso Rionegro, Antioquia).
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, date

st.set_page_config(page_title="Asesor del Caficultor", page_icon="🌱", layout="wide")
st.title("🌱 Asesor del Caficultor")
st.caption("Recordatorios mensuales · Alertas climáticas y de precio · Buenas prácticas")

PROJECT = Path(__file__).resolve().parents[2]
DIR_PROC = PROJECT / "01_datos" / "procesados"

# Calendario agronómico mes-a-mes
CALENDARIO = {
    1:  {"actividad": "Manejo de arvenses y planeación",
         "tareas": ["Plato limpio alrededor del tronco (40 cm radio)",
                    "Revisar plan de fertilización del año",
                    "Limpiar herramientas (machete, tijeras de poda)"]},
    2:  {"actividad": "PRIMERA FERTILIZACIÓN del año",
         "tareas": ["Aplicar NPK 17-6-18-2 (200-300 g por planta)",
                    "Mojar bien antes de abonar si está seco",
                    "Hacer deshije: dejar 2-3 chupones por tronco"]},
    3:  {"actividad": "Inicio cosecha mitaca (Antioquia, Tolima, Valle)",
         "tareas": ["Recolección selectiva: SOLO cereza roja madura",
                    "Beneficio: lavar bien, secar lento (6-12 días)",
                    "Monitorear roya en hojas jóvenes"]},
    4:  {"actividad": "Cosecha mitaca + control roya",
         "tareas": ["Continuar cosecha selectiva",
                    "Si hay >10% incidencia roya: aplicar triazol",
                    "Revisar trampas de broca"]},
    5:  {"actividad": "SEGUNDA FERTILIZACIÓN (poscosecha mitaca)",
         "tareas": ["Aplicar NPK con énfasis en potasio",
                    "Foliar con boro + magnesio si hojas amarillas",
                    "Podas selectivas de ramas improductivas"]},
    6:  {"actividad": "Final mitaca, secado, mantenimiento",
         "tareas": ["Terminar de secar el café (humedad 10-12%)",
                    "Almacenar en pergamino, lugar seco",
                    "Sembrar nuevas chapolas si renovó zoca"]},
    7:  {"actividad": "Floración principal (depende del clima)",
         "tareas": ["NO regar fuerte durante floración",
                    "Vigilar broca: muestreo semanal",
                    "Revisar sombrío: ralear si está muy denso"]},
    8:  {"actividad": "TERCERA FERTILIZACIÓN + control plagas",
         "tareas": ["Aplicar NPK balanceado",
                    "Control de broca con trampas + buenas prácticas",
                    "Control de minador si infestación >30%"]},
    9:  {"actividad": "Inicio cosecha principal (zona andina)",
         "tareas": ["Recolección selectiva diaria",
                    "Beneficio inmediato (máx 6h después de recoger)",
                    "Monitorear gotera con humedad alta"]},
    10: {"actividad": "Pico de cosecha principal",
         "tareas": ["Maximizar mano de obra de recolección",
                    "Asegurar capacidad de fermentadores y patios",
                    "Revisar puntaje SCA con muestras a tostadora"]},
    11: {"actividad": "CUARTA FERTILIZACIÓN + cosecha",
         "tareas": ["Aplicar NPK final del año",
                    "Continuar recolección selectiva",
                    "Si viene El Niño anticipado: reforzar sombrío"]},
    12: {"actividad": "Final cosecha + planeación próximo año",
         "tareas": ["Cierre de cosecha y secado final",
                    "Mantenimiento de equipos (despulpadora)",
                    "Decidir qué lotes vender por SCA y cuáles por FNC"]},
}

# Sidebar: datos del usuario
with st.sidebar:
    st.header("Tu finca")
    municipio = st.text_input("Municipio", value="Rionegro")
    departamento = st.selectbox("Departamento",
        ["Antioquia", "Huila", "Nariño", "Caldas", "Tolima",
         "Quindío", "Risaralda", "Cauca", "Valle del Cauca",
         "Santander", "Cundinamarca", "Otro"])
    altitud = st.number_input("Altitud finca (msnm)", 500, 3000, 2100, 50,
                                help="Rionegro Antioquia ≈ 2100 msnm")
    area_ha = st.number_input("Hectáreas de café", 0.1, 100.0, 2.0, 0.1)

# 1. Recordatorios del mes
mes_actual = datetime.now().month
st.subheader(f"📅 Tareas de este mes ({datetime.now().strftime('%B %Y')})")
info = CALENDARIO.get(mes_actual, {})
st.markdown(f"### {info.get('actividad', '—')}")
for t in info.get("tareas", []):
    st.markdown(f"- {t}")

if mes_actual in (2, 5, 8, 11):
    st.warning(f"⚠ **Este es mes de fertilización.** Si no abonas ahora, "
                f"perderás producción y aumentarás riesgo de enfermedades.")

# 2. Alerta climática y ENSO
st.markdown("---")
st.subheader("🌦 Alerta climática")

@st.cache_data
def cargar_enso():
    p = DIR_PROC / "enso_validado.csv"
    if not p.exists():
        p = PROJECT / "01_datos" / "enriquecidos" / "clima" / "enso_oni_extendido.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    return df.dropna(subset=["fecha"]).sort_values("fecha")

enso = cargar_enso()
if enso is not None and len(enso):
    ult = enso.iloc[-1]
    oni = float(ult.get("oni", 0))
    fase = ult.get("fase_enso", "Neutro")

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Índice ONI actual", f"{oni:+.2f}")
    with c2: st.metric("Fase ENSO", fase)
    with c3: st.metric("Última actualización", ult.fecha.strftime("%b %Y"))

    if fase == "Nino":
        st.error("☀ **El Niño activo.** Reducción esperada de rendimiento ~24%.\n\n"
                  "**Qué hacer:**\n"
                  "- Reforzar sombrío para reducir estrés térmico\n"
                  "- Fertilización foliar para soportar al cafetal\n"
                  "- Riego si tienes posibilidad\n"
                  "- Vigilar roya intensificada por estrés")
    elif fase == "Nina":
        st.warning("🌧 **La Niña activa.** Reducción esperada ~12% por exceso de lluvia.\n\n"
                    "**Qué hacer:**\n"
                    "- Revisar drenajes\n"
                    "- Podas sanitarias para mejorar aireación\n"
                    "- Fungicidas cúpricos preventivos contra gotera y antracnosis")
    else:
        st.success("✓ **Condiciones ENSO neutras.** Año típico esperado.")
else:
    st.info("Sin datos ENSO recientes. Ejecuta el pipeline ETL para actualizarlos.")

# 3. Alerta de precio
st.markdown("---")
st.subheader("💰 Alerta de precio FNC")

@st.cache_data
def cargar_precios():
    p = DIR_PROC / "precios_validado.csv"
    if not p.exists(): return None
    df = pd.read_csv(p)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    return df.dropna(subset=["fecha"]).sort_values("fecha")

precios = cargar_precios()
if precios is not None and "precio_fnc_cop_kg" in precios.columns:
    serie = precios[["fecha","precio_fnc_cop_kg"]].dropna()
    if len(serie) >= 2:
        ult = float(serie["precio_fnc_cop_kg"].iloc[-1])
        ant = float(serie["precio_fnc_cop_kg"].iloc[-2])
        cambio = (ult / ant - 1) * 100
        media_12m = float(serie["precio_fnc_cop_kg"].tail(12).mean())

        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Precio FNC último", f"${ult:,.0f}/kg", f"{cambio:+.1f}%")
        with c2: st.metric("Promedio 12 meses", f"${media_12m:,.0f}/kg")
        with c3: st.metric("Carga 125kg", f"${ult*125:,.0f} COP")

        if ult > media_12m * 1.1:
            st.success("📈 **Precio ALTO** (>10% sobre promedio 12 meses). "
                        "Buen momento para vender tu inventario disponible.")
        elif ult < media_12m * 0.9:
            st.warning("📉 **Precio BAJO** (<10% debajo del promedio). "
                        "Si puedes esperar, vale la pena retener.")
        else:
            st.info("↔ Precio en rango normal. Vende según tu flujo de caja.")
else:
    st.info("Sin datos de precio cargados.")

# 4. Buenas prácticas según altitud
st.markdown("---")
st.subheader("📚 Recomendaciones para tu finca")

if altitud >= 1800:
    st.markdown(f"""
**Tu finca está a {altitud:,.0f} msnm — zona de café de altura.** ✨

- **Ventaja:** la maduración lenta concentra azúcares → potencial de café especial (>85 SCA).
- **Variedades recomendadas:** Castillo, Caturra, Geisha (si la tasa el mercado).
- **Riesgos:** heladas en madrugadas claras, gotera por humedad.
- **Inversión que más rinde aquí:** cosecha selectiva + beneficio cuidadoso.
- **Mercado objetivo:** tostadoras especializadas, exportación café especial.
""")
elif altitud >= 1200:
    st.markdown(f"""
**Tu finca está a {altitud:,.0f} msnm — zona cafetera óptima clásica.**

- **Ventaja:** condiciones ideales para arábica de buena calidad.
- **Variedades recomendadas:** Castillo, Colombia, Cenicafé 1 (resistentes a roya).
- **Riesgos:** roya, broca.
- **Inversión que más rinde:** fertilización oportuna + variedades resistentes.
""")
else:
    st.markdown(f"""
**Tu finca está a {altitud:,.0f} msnm — zona baja.**

- **Limitación:** mayor riesgo de plagas (broca, minador) y menor calidad SCA.
- **Variedades recomendadas:** Castillo resistente, considerar robusta si <800 msnm.
- **Inversión que más rinde:** control fitosanitario constante.
""")

st.caption("ℹ Estas recomendaciones son referenciales. Consulta con extensionistas "
            "de la FNC o tu cooperativa para diagnóstico específico.")
