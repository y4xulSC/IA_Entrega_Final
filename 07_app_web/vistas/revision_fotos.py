"""Revisión de diagnósticos (solo administradores).

1. **Diagnósticos dudosos:** los que salieron con certeza baja o con dos clases
   parecidas, a partir de las 7 probabilidades que se guardan desde la v1.7.
2. **Fotos donadas:** las que los usuarios donaron de forma voluntaria. El
   revisor ve la foto, lo que dijo el modelo y anota la clase real. Con eso se
   mide qué tanto acierta la CNN en fotos reales de campo.
3. **Borrado por código:** para atender a quien pida borrar su foto.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from cofitech import fotos, repositorio, seguridad
from cofitech.contexto_finca import NOMBRES_CLASE

seguridad.exigir_admin()
st.title("Revisión de diagnósticos")


def _nombre(clase: str | None) -> str:
    return NOMBRES_CLASE.get(clase, (clase or "—", ""))[0] if clase != "Indeterminada" else "No se puede saber"


borradas = fotos.limpiar_vencidas()
if borradas:
    st.caption(f"Se borraron {borradas} fotos vencidas ({fotos.DIAS_RETENCION} días).")

# ─────────────────────────── 1. Diagnósticos dudosos ─────────────────────────
st.subheader("Diagnósticos dudosos")
umbral = st.slider("Certeza por debajo de", 0.40, 0.95, fotos.UMBRAL_CERTEZA, 0.05, format="%.2f")
df = repositorio.leer_diagnosticos()
if "probabilidades" not in df:
    df["probabilidades"] = None
filas = []
for _, d in df.iterrows():
    segunda = fotos.segunda_opcion(d["probabilidades"] if isinstance(d["probabilidades"], dict) else None)
    if d["confianza"] < umbral or (segunda and segunda[2] < 0.20):
        filas.append({"Fecha": d["fecha"], "Municipio": d["municipio"], "Modelo dijo": _nombre(d["clase"]),
                      "Certeza": d["confianza"], "Segunda opción": _nombre(segunda[0]) if segunda else "—",
                      "Prob. segunda": segunda[1] if segunda else None,
                      "Usuario": {True: "👍", False: "👎"}.get(d["feedback_usuario"], "sin voto")})
if filas:
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch", column_config={
        "Fecha": st.column_config.DatetimeColumn(format="D MMM YYYY, HH:mm"),
        "Certeza": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "Prob. segunda": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})
    st.caption("La segunda opción solo aparece en diagnósticos hechos desde la v1.7 (antes no se guardaban las "
               "probabilidades). Margen < 20 puntos entre las dos primeras clases también cuenta como dudoso.")
else:
    st.info("No hay diagnósticos dudosos con ese umbral.")

# ───────────────────────────── 2. Fotos donadas ──────────────────────────────
st.subheader("Fotos donadas")
todas, fuente = fotos.listar(None)
revisadas = [f for f in todas if f.get("clase_revisada")]
validas = [f for f in revisadas if f["clase_revisada"] != "Indeterminada"]
aciertos = sum(f["clase_revisada"] == f["clase_modelo"] for f in validas)
c1, c2, c3 = st.columns(3)
c1.metric("Pendientes", len(todas) - len(revisadas))
c2.metric("Revisadas", len(revisadas))
c3.metric("Acierto del modelo en campo", f"{aciertos / len(validas):.0%}" if validas else "—",
          help="Fotos donadas en las que la clase del revisor coincide con la del modelo "
               "(sin contar «No se puede saber»).")
st.caption(f"Fuente: {fuente}. Las fotos se borran solas a los {fotos.DIAS_RETENCION} días.")

ver = st.radio("Mostrar", ["Pendientes", "Revisadas"], horizontal=True)
lista = [f for f in todas if bool(f.get("clase_revisada")) == (ver == "Revisadas")]
if not lista:
    st.info("No hay fotos en esta lista.")
for f in lista[:20]:
    with st.container(border=True):
        col_img, col_info = st.columns([1, 1.3])
        img = fotos.imagen(f, fuente)
        if img:
            col_img.image(img, caption=f"Código {f['codigo']}", width="stretch")
        with col_info:
            st.markdown(f"**El modelo dijo:** {_nombre(f['clase_modelo'])} ({float(f['confianza_modelo']):.0%})")
            probs = f.get("probabilidades") or {}
            if probs:
                top = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[:3]
                st.caption(" · ".join(f"{_nombre(c)} {p:.0%}" for c, p in top))
            st.caption(f"{f.get('municipio') or 'Municipio sin dato'} · {str(f.get('fecha'))[:16]}")
            actual = f.get("clase_revisada") or f["clase_modelo"]
            clase = st.selectbox("Clase real", fotos.CLASES_REVISION, key=f"rev_clase_{f['id']}",
                                 index=fotos.CLASES_REVISION.index(actual) if actual in fotos.CLASES_REVISION else 0,
                                 format_func=_nombre)
            notas = st.text_input("Notas (opcional)", value=f.get("notas_revision") or "", max_chars=500,
                                  key=f"rev_notas_{f['id']}")
            b1, b2 = st.columns(2)
            if b1.button("Guardar revisión", key=f"rev_ok_{f['id']}", type="primary", width="stretch"):
                fotos.revisar(f, fuente, clase, notas)
                st.rerun()
            if b2.button("Borrar foto", key=f"rev_borrar_{f['id']}", width="stretch"):
                fotos.borrar(f["id"] if fuente == "Supabase" else f["codigo"])
                st.rerun()

# ─────────────────────────── 3. Borrado por código ───────────────────────────
st.subheader("Borrar por código")
st.caption("Para atender a un usuario que pide borrar su foto (derecho de supresión, Ley 1581).")
codigo = st.text_input("Código de la foto", placeholder="K7Q2-M9XD", max_chars=9)
if st.button("Borrar", disabled=not codigo.strip()):
    if fotos.borrar(codigo):
        st.success(f"Foto {codigo.strip().upper()} borrada.")
    else:
        st.warning("No encontramos una foto con ese código (puede que ya se haya borrado).")
