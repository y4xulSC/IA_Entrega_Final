"""Telemetría y KPIs: lo que prometimos medir en la entrega de Data Thinking.

Lee todos los eventos guardados (todas las sesiones) y calcula los KPIs que
la telemetría puede medir. KR1 (registros) y la retención semanal necesitan
inicio de sesión de usuarios y aquí no se miden.
"""
from __future__ import annotations

import streamlit as st

from cofitech import seguridad
from cofitech import telemetria as tel

seguridad.exigir_admin()
st.title("Telemetría y KPIs")

df = tel.leer_eventos()
kpis = tel.calcular_kpis(df)


def _pct(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:.0%}".replace(".", ",")


c1, c2, c3, c4 = st.columns(4)
c1.metric("Nivel de confianza aceptada", _pct(kpis["confianza_aceptada"]),
          help=f"Diagnósticos por foto que el usuario validó con 👍 ({kpis['validaciones']} valoraciones).")
c2.metric("Tasa de resolución del RAG", _pct(kpis["resolucion_rag"]),
          help=f"Respuestas del asistente marcadas como útiles ({kpis['valoraciones_rag']} valoraciones).")
c3.metric("KR3 · sesiones con las 3 herramientas", f"{kpis['sesiones_3_herramientas']} de 10",
          help="Sesiones que usaron Visión, Predicción (rendimiento o precios) y el asistente RAG. Meta: 10.")
c4.metric("Sesiones que valoraron", _pct(kpis["sesiones_con_valoracion"]),
          help="Proxy de KR2 (meta 70 %): sesiones con al menos un 👍/👎. KR2 pide encuestas de usabilidad; "
               "los votos son una señal parcial.")
st.caption(f"{kpis['eventos']} eventos de {kpis['sesiones']} sesiones · Supabase: {tel.db_client.estado()} "
           f"(si no responde se lee `{tel.RUTA_EVENTOS.name}`). "
           "Una sesión es un navegador, no una persona: sin inicio de sesión no se pueden contar usuarios.")



# ───────────────────── KPIs consolidados en vivo (por rol) ──────────────────
@st.fragment(run_every="30s")
def kpis_en_vivo() -> None:
    st.subheader("KPIs consolidados en vivo")
    tabla, fuente = None, "archivo local"
    if tel.db_client.configurado():
        try:
            tabla, fuente = tel.db_client.kpis_consolidados(), "Supabase (`cafe.vw_kpis_consolidados`)"
        except tel.db_client.BaseDatosNoDisponible:
            tabla = None
    if tabla is None:
        tabla = tel.kpis_por_rol(tel.leer_eventos())
    if tabla.empty or not tabla["eventos"].fillna(0).astype(int).any():   # la vista devuelve una fila «Total» en 0
        st.info("Aún no hay eventos. Se registran al usar Visión, Rendimiento, Precios y el asistente.")
        return
    st.dataframe(
        tabla, hide_index=True, use_container_width=True,
        column_config={
            "rol": "Rol", "sesiones": "Sesiones", "eventos": "Eventos",
            "valoraciones_rag": "Votos RAG",
            "satisfaccion_rag": st.column_config.ProgressColumn(
                "Satisfacción RAG", format="percent", min_value=0, max_value=1,
                help="Respuestas del asistente marcadas 👍 / respuestas calificadas."),
            "validaciones_vision": "Votos Visión",
            "confianza_aceptada": st.column_config.ProgressColumn(
                "Confianza aceptada", format="percent", min_value=0, max_value=1,
                help="Diagnósticos por foto que el usuario confirmó con 👍 / diagnósticos calificados."),
            "confianza_media_modelo": st.column_config.NumberColumn(
                "Certeza media CNN", format="percent",
                help="Promedio de la probabilidad que dio la CNN a la clase elegida."),
            "sesiones_3_herramientas": st.column_config.NumberColumn("KR3 (sesiones)", help="Meta: 10."),
            "ultimo_evento": st.column_config.DatetimeColumn("Último evento", format="D MMM YYYY, HH:mm"),
        },
    )
    st.caption(f"Fuente: {fuente} · se actualiza cada 30 s.")


kpis_en_vivo()

if df.empty:
    st.stop()

st.subheader("Uso por herramienta")
uso = (df.groupby(["herramienta", "accion"]).size().rename("eventos").reset_index()
       .sort_values(["herramienta", "eventos"], ascending=[True, False]))
st.dataframe(uso, hide_index=True, use_container_width=True)

st.subheader("Últimos eventos")
columnas = [c for c in ("timestamp", "usuario_rol", "herramienta", "accion", "md_municipio", "md_modelo",
                        "md_tiempo_respuesta_s", "md_confianza_aceptada", "md_util") if c in df]
st.dataframe(df.sort_values("timestamp", ascending=False)[columnas].head(50), hide_index=True,
             use_container_width=True)

st.download_button("Descargar eventos (CSV)", df.to_csv(index=False).encode("utf-8"),
                   file_name="eventos_uso_cofitech.csv", mime="text/csv")
