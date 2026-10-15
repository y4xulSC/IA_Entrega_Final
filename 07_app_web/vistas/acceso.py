"""Ingreso: se elige el rol y se entregan los datos de la finca o de la zona UNA vez.

La misma vista sirve después como «Datos de mi finca» / «Mi zona de trabajo»
para corregirlos. Ninguna otra pantalla debe volver a pedir estos datos.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from cofitech import seguridad
from cofitech.contexto_finca import (
    RANGO_ALTITUD_MSNM, RANGO_AREA_HA, VARIEDADES, Rol,
    actualizar_finca, actualizar_zona, catalogo_municipios, definir_rol, obtener_contexto,
)

OTRO = "Otro municipio"
ROLES = {"Soy caficultor": Rol.CAFICULTOR, "Soy agrónomo o trabajo en una cooperativa": Rol.AGRONOMO}

st.set_page_config(layout="centered")  # un formulario se lee mejor angosto

ctx = obtener_contexto()
catalogo = catalogo_municipios()

if ctx.rol is None:
    st.title("CofiTech")
    st.caption("Datos que impulsan el futuro del café")
    eleccion = st.radio("¿Cómo vas a usar CofiTech?", list(ROLES), horizontal=True)
    rol = ROLES[eleccion]
else:
    rol = ctx.rol
    st.title("Datos de mi finca" if rol == Rol.CAFICULTOR else "Mi zona de trabajo")

if rol == Rol.CAFICULTOR:
    finca = ctx.finca
    opciones = [f"{m}, {d}" for m, d in zip(catalogo["municipio"], catalogo["departamento"])] + [OTRO]
    actual = f"{finca.municipio}, {finca.departamento}"
    indice = opciones.index(actual) if actual in opciones else (len(opciones) - 1 if finca.municipio else 0)
    # Fuera del formulario: al cambiar de municipio se actualiza la altitud sugerida.
    seleccion = st.selectbox("¿En qué municipio está tu finca?", opciones, index=indice)

    if seleccion == OTRO:
        col_m, col_d = st.columns(2)
        municipio = col_m.text_input("Municipio", value=finca.municipio)
        departamento = col_d.text_input("Departamento", value=finca.departamento)
        codigo_dane, altitud_sugerida = None, 1500.0
    else:
        fila = catalogo.iloc[opciones.index(seleccion)]
        municipio, departamento = str(fila["municipio"]), str(fila["departamento"])
        codigo_dane = str(fila["codigo_dane"])
        # Solo 21 cabeceras tienen altitud en el catálogo; para el resto se parte de 1.500 msnm.
        altitud_sugerida = float(fila["altitud_msnm"]) if pd.notna(fila["altitud_msnm"]) else 1500.0

    if finca.altitud_msnm and municipio == finca.municipio:
        altitud_sugerida = finca.altitud_msnm
    altitud_sugerida = min(max(altitud_sugerida, RANGO_ALTITUD_MSNM[0]), RANGO_ALTITUD_MSNM[1])
    variedades = list(VARIEDADES)

    with st.form("form_finca"):
        altitud = st.number_input(
            "Altitud de la finca (msnm)", *RANGO_ALTITUD_MSNM, value=altitud_sugerida, step=50.0,
            help="Si el catálogo tiene la altitud del casco urbano la sugerimos; ajústala a la de tu finca.",
        )
        area = st.number_input("Hectáreas sembradas en café", *RANGO_AREA_HA, value=finca.area_ha or 2.0, step=0.5)
        variedad = st.selectbox(
            "Variedad principal", variedades,
            index=variedades.index(finca.variedad) if finca.variedad in variedades else len(variedades) - 1,
        )
        floracion = st.date_input(
            "Fecha de la floración principal (opcional)", value=finca.fecha_floracion_principal,
            help="Con esta fecha se decide si un control de roya está a tiempo.",
        )
        enviar = st.form_submit_button("Guardar y entrar" if ctx.rol is None else "Guardar", type="primary")

    if enviar:
        errores = actualizar_finca(
            municipio=municipio.strip(), departamento=departamento.strip(), codigo_dane=codigo_dane,
            altitud_msnm=altitud, area_ha=area, variedad=variedad, fecha_floracion_principal=floracion,
        )
        if errores:
            for error in errores:
                st.error(error)
        else:
            definir_rol(Rol.CAFICULTOR)
            st.rerun()

else:
    departamentos = sorted(catalogo["departamento"].dropna().unique())
    with st.form("form_zona"):
        zona = st.multiselect(
            "¿Qué departamentos atiendes?", departamentos,
            default=[d for d in ctx.zona.departamentos if d in departamentos],
        )
        enviar = st.form_submit_button("Guardar y entrar" if ctx.rol is None else "Guardar", type="primary")

    if enviar:
        if not zona:
            st.error("Elige al menos un departamento.")
        else:
            actualizar_zona(zona)
            definir_rol(Rol.AGRONOMO)
            st.rerun()


# ─────────────────────── Acceso de administrador ────────────────────────────
st.divider()
with st.expander("Acceso administrador", icon=":material/lock:", expanded=seguridad.es_admin()):
    if seguridad.es_admin():
        st.success("Acceso de administrador activo: verás la sección «Administración» en el menú.")
        if st.button("Salir de administrador", icon=":material/logout:"):
            seguridad.cerrar_sesion()
            st.rerun()
    elif not seguridad.acceso_habilitado():
        st.caption("El acceso de administrador no está configurado en este servidor.")
    else:
        with st.form("form_admin", clear_on_submit=True):
            contrasena = st.text_input("Contraseña de administrador", type="password")
            entrar = st.form_submit_button("Entrar como administrador")
        if entrar:
            ok, mensaje = seguridad.iniciar_sesion(contrasena)
            if ok:
                st.rerun()
            st.error(mensaje)
