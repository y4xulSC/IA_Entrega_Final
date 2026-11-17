"""Aviso de privacidad y autorización de tratamiento de datos (Ley 1581 de 2012).

Lo muestran la pantalla de ingreso (con la casilla de autorización, obligatoria
para entrar la primera vez) y la página «Aviso de privacidad» de cada rol.

El texto describe lo que la app hace hoy; si cambia lo que se guarda
(``contexto_finca.registrar_diagnostico``, ``telemetria``, ``mercado``), hay que
actualizarlo y subir ``VERSION_AVISO``. No es una asesoría jurídica: antes de
abrir la app a usuarios reales conviene que lo revise la oficina jurídica de la
universidad.
"""
from __future__ import annotations

import streamlit as st

from cofitech import config

VERSION_AVISO = "2026-11-17"
_CLAVE_ACEPTO = "cofitech_acepto_aviso"

TEXTO_CASILLA = ("Leí el aviso de privacidad y autorizo el tratamiento de los datos de mi finca o de mi zona "
                 "para los fines que allí se describen.")


def texto_aviso() -> str:
    mercado = ("- **Venta directa (inactiva en la Beta):** el simulador de venta no guarda tu lote; solo se cuenta "
               "que lo usaste (tipo de café, cargas y número de ofertas) y tu voto 👍/👎 sobre si te gustaría la "
               "herramienta. Si se activa la venta real, se guardarán los datos del lote (cantidad, tipo de café, "
               "precio esperado) y los mensajes que escribas a los compradores.\n"
               if not config.mercado_activo() else
               "- **Venta directa:** los datos del lote (cantidad, tipo de café, precio esperado) y los mensajes "
               "que escribas a los compradores. No escribas en el chat tu nombre, teléfono ni documento.\n")
    return f"""
**Responsable.** Equipo CofiTech, proyecto académico de Ingeniería de Datos e Inteligencia Artificial de la
Universidad Autónoma de Occidente (Cali). CofiTech está en versión **{config.ETAPA}**.

**Qué datos se tratan**

- **Datos de la finca o de la zona:** municipio, departamento, altitud, hectáreas, variedad y fecha de floración
  (caficultor), o departamentos atendidos (agrónomo o cooperativa).
- **Diagnósticos por foto:** la enfermedad detectada, la confianza del modelo (incluida la probabilidad de cada
  enfermedad), el municipio y la fecha. **La foto no se guarda**, salvo que decidas donarla.
- **Fotos donadas (opcional):** solo si marcas la casilla de donación de esa foto. Se guarda reducida y sin los datos
  de ubicación ni de la cámara, junto con el diagnóstico y el municipio, para que el equipo revise si el diagnóstico
  fue correcto y para mejorar el modelo. Se borra sola a los 180 días; puedes pedir que se borre antes con el código
  que te mostramos al donarla.
- **Preguntas al asistente:** se envían, junto con los datos de la finca, a un proveedor de modelos de lenguaje
  (Groq, con servidores en Estados Unidos) para generar la respuesta. CofiTech no guarda el texto de las preguntas.
- **Uso de la app:** qué herramienta se usó, cuánto tardó y si la respuesta te sirvió (votos 👍/👎), sin texto.
{mercado}
CofiTech **no pide nombre, cédula, teléfono ni correo**: todo se asocia a un identificador aleatorio de la sesión.

**Para qué**

1. Darte recomendaciones para tu finca (diagnóstico, manejo, cosecha, precios).
2. Mostrar a agrónomos y cooperativas alertas de roya **agregadas por municipio**, sin datos que identifiquen a nadie.
3. Medir y mejorar los modelos de la app.

**Dónde se guardan.** En una base de datos PostgreSQL administrada por Supabase, con servidores fuera de Colombia
(transferencia internacional de datos), y en copias de respaldo en el servidor de la app.

**Tus derechos (artículo 8 de la Ley 1581).** Conocer, actualizar y rectificar tus datos; pedir prueba de esta
autorización; saber cómo se usan; revocar la autorización y pedir que se borren; y presentar quejas ante la
Superintendencia de Industria y Comercio. Como CofiTech no conoce tu identidad, al escribir indica el municipio y
la fecha aproximada de uso.

**Contacto:** {config.contacto_datos()}

*Versión del aviso: {VERSION_AVISO}.*
"""


def mostrar() -> None:
    st.markdown(texto_aviso())


def acepto() -> bool:
    return bool(st.session_state.get(_CLAVE_ACEPTO))


def registrar_aceptacion() -> None:
    st.session_state[_CLAVE_ACEPTO] = VERSION_AVISO
