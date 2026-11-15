"""Aviso de privacidad y tratamiento de datos (Ley 1581 de 2012), para todos los roles."""
from __future__ import annotations

import streamlit as st

from cofitech import marca, privacidad

st.set_page_config(page_title="Aviso de privacidad", page_icon=marca.ICONO, layout="centered")
st.title("Aviso de privacidad")
st.caption("Tratamiento de datos personales · Ley 1581 de 2012")
privacidad.mostrar()
