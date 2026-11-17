"""Vender mi café: pasos 5–7 del MockUp ganador (lámina de Sofía, RF09).

5. Compradores  · quién compra en la zona y qué paga sobre el precio FNC.
6. Publicar lote · el caficultor describe su lote en pocos toques; los datos
   de la finca y el último diagnóstico se adjuntan solos (RF01).
7. Mis lotes y mensajes · oferta formal con total calculado; aceptar,
   contraofertar o rechazar sin salir del chat.

Reglas del prototipo: los compradores son de demostración y la pantalla lo
dice; no se guardan nombre, teléfono ni documento del caficultor.

En la versión Beta la venta real está **inactiva** (``config.mercado_activo``):
la pantalla muestra el aviso, un **simulador de venta** con los compradores de
demostración (``cofitech/simulador_mercado.py``, no guarda el lote) y la
pregunta «¿Te gustaría vender tu café desde CofiTech?», cuyo 👍/👎 es el KPI
«Interés en la venta directa» (``cafe.vw_kpis_consolidados``). Todo el flujo
real sigue en el código y en las pruebas; se enciende con
``COFITECH_MERCADO_ACTIVO=1``.

Las acciones van en callbacks (``on_click``): corren antes de dibujar la
pantalla, así pueden cambiar de sección sin ``st.rerun()``.
"""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from cofitech import config, marca, mercado
from cofitech import simulador_mercado as simulador
from cofitech.contexto_finca import AYUDA_VARIEDAD, VARIEDADES, mes_anio, obtener_contexto
from cofitech.mercado import cop
from cofitech.telemetria import barra_valoracion, registrar_evento_uso, registrar_una_vez

st.set_page_config(page_title="Vender mi café", page_icon=marca.ICONO, layout="centered")

_SIM, _SIM_NEG, _SIM_CIERRE = "sim_resultado", "sim_negociacion", "sim_cierre"
_SIM_USO, _SIM_GLOBOS = "sim_usado", "sim_globos"

COLOR_TIPO = {"Tostador": "#6B4A35", "Cooperativa": "#2E6F40", "Exportador": "#B7790F"}


def _beta_simulador() -> None:
    """Beta: venta directa inactiva + simulador de venta + voto de interés (KPI)."""
    ctx = obtener_contexto()
    finca = ctx.finca
    precio_fnc = round(ctx.mercado.precio_fnc_cop_carga) if ctx.mercado.precio_fnc_cop_carga else None
    e = st.session_state

    # ── Acciones (callbacks: corren antes de dibujar)
    def simular(ref: int) -> None:
        puntaje = e.get("sim_puntaje") if e.get("sim_con_puntaje") else None
        lote = mercado.Lote(
            tipo_cafe=e["sim_tipo"], cantidad_cargas=float(e["sim_cargas"]),
            precio_esperado_cop_carga=int(e["sim_precio"]), precio_fnc_ref_cop_carga=ref,
            municipio=finca.municipio, departamento=finca.departamento, codigo_dane=finca.codigo_dane,
            altitud_msnm=finca.altitud_msnm, variedad=finca.variedad, puntaje_sca=puntaje)
        resultado = simulador.simular(lote)
        e.update({_SIM: resultado, _SIM_NEG: None, _SIM_CIERRE: None, _SIM_USO: True})
        registrar_evento_uso("Mercado", "simulacion_venta", {
            "tipo_cafe": lote.tipo_cafe, "cargas": lote.cantidad_cargas, "con_puntaje": puntaje is not None,
            "ofertas": len(resultado.ofertas),
            "pct_mejor_vs_fnc": resultado.mejor.pct_vs_fnc if resultado.mejor else None})

    def negociar(oferta: simulador.OfertaSimulada) -> None:
        e.update({_SIM_NEG: simulador.iniciar_negociacion(oferta), _SIM_CIERRE: None})

    def contraofertar(clave: str) -> None:
        respuesta = simulador.contraofertar(e[_SIM_NEG], e[_SIM].lote, int(e[clave]))
        registrar_evento_uso("Mercado", "simulacion_contraoferta", {"resultado": respuesta})

    def cerrar() -> None:
        cierre = simulador.cerrar(e[_SIM_NEG], e[_SIM].lote)
        e.update({_SIM_CIERRE: cierre, _SIM_GLOBOS: True})
        registrar_evento_uso("Mercado", "simulacion_cierre", {"pct_vs_fnc": cierre["pct_vs_fnc"]})

    def reiniciar() -> None:
        for clave in (_SIM, _SIM_NEG, _SIM_CIERRE):
            e.pop(clave, None)

    # ── Encabezado
    st.title("Vender mi café")
    st.markdown(marca.tarjeta_inactiva(
        "La venta real está desactivada en esta versión",
        "CofiTech Beta se concentra en sus herramientas de inteligencia artificial. La venta directa se activará "
        "cuando haya compradores reales verificados. Mientras tanto, prueba cómo funcionaría con el simulador: "
        "nada se publica ni se comparte."), unsafe_allow_html=True)
    registrar_una_vez("mercado_inactivo_venta", "Mercado", "vista_inactiva", {"pantalla": "vender"})

    st.markdown(marca.cabecera_simulador(
        "Simulador de venta",
        "Describe un lote y mira qué te ofrecerían cinco compradores de demostración (cooperativas, tostadores y "
        "exportadores). Puedes negociar y cerrar una venta de práctica."), unsafe_allow_html=True)

    # ── 1 · Tu lote
    st.markdown(marca.paso(1, "Tu lote"), unsafe_allow_html=True)
    if precio_fnc:
        ref = precio_fnc
        st.caption(f"Precio de referencia FNC: {cop(ref)} por carga ({mes_anio(ctx.mercado.fecha)}).")
    else:
        ref = int(st.number_input("Precio de referencia FNC (COP por carga)", min_value=500_000,
                                  max_value=10_000_000, value=2_500_000, step=10_000, key="sim_ref"))
    tipo = st.radio("Tipo de café", list(mercado.TIPOS_CAFE), horizontal=True, key="sim_tipo")
    c1, c2 = st.columns(2)
    c1.number_input("Cantidad (cargas de 125 kg)", min_value=0.5, max_value=10_000.0, value=20.0, step=0.5,
                    key="sim_cargas")
    precio = c2.number_input("Precio que pides (COP por carga)", min_value=100_000, max_value=20_000_000,
                             value=mercado.redondear(ref * 1.05), step=10_000, key="sim_precio")
    if st.toggle("Tengo puntaje de catación (SCA)", value=tipo == "Especial", key="sim_con_puntaje"):
        st.slider("Puntaje SCA", 60, 100, 84, key="sim_puntaje")
    dif = round(100 * (precio / ref - 1), 1)
    st.markdown(marca.chip(f"Pides {marca.pct(dif)} frente al precio FNC", "verde" if dif >= 0 else "rojo"),
                unsafe_allow_html=True)
    st.button("Ver ofertas simuladas", type="primary", icon=":material/play_arrow:", use_container_width=True,
              on_click=simular, args=(ref,))

    resultado: simulador.Resultado | None = e.get(_SIM)
    if resultado is not None:
        _ofertas(resultado, negociar)
        if e.get(_SIM_NEG) is not None:
            _negociacion(resultado, e[_SIM_NEG], e.get(_SIM_CIERRE), contraofertar, cerrar)
        st.button("Probar con otro lote", icon=":material/restart_alt:", on_click=reiniciar)

    # ── KPI: ¿le gustaría la herramienta?
    st.divider()
    with st.container(border=True):
        st.markdown("#### ¿Te gustaría vender tu café desde CofiTech?")
        barra_valoracion(
            clave="interes_venta_directa",
            pregunta="Tu voto decide si activamos la venta directa con compradores reales. Es anónimo: "
                     "solo se cuenta el 👍 o el 👎.",
            herramienta="Mercado", accion="interes_venta_directa", campo="le_gustaria",
            metadata={"uso_simulador": bool(e.get(_SIM_USO))},
            etiqueta_si="👍 Sí, me gustaría", etiqueta_no="👎 No la usaría",
            agradecimiento="¡Gracias! Tu voto nos ayuda a decidir qué construir")

    st.markdown("**Mientras tanto, estas herramientas de IA están activas:**")
    marca.enlace("pages/4_Enfermedades.py", "Revisar una hoja · CNN con Grad-CAM",
                 ":material/photo_camera:")
    marca.enlace("pages/5_Chatbot.py", "¿Qué hago? · asistente RAG con fuentes", ":material/forum:")
    marca.enlace("pages/2_Rendimiento.py", "Mi cosecha e ingreso · proyección",
                 ":material/agriculture:")
    marca.enlace("pages/7_Calidad_SCA.py", "Calidad y primas (SCA)",
                 ":material/sell:")
    if e.pop(_SIM_GLOBOS, False):
        st.balloons()


def _cabecera_comprador(c: mercado.Comprador) -> str:
    return (f'<div class="ct-comprador">{marca.avatar(c.iniciales, COLOR_TIPO.get(c.tipo, "#6B4A35"))}'
            f'<div><div class="n">{marca._e(c.nombre)}</div>'
            f'<div class="s">{marca._e(c.tipo)} · {marca._e(c.municipio)}, {marca._e(c.departamento)}</div>'
            f'</div></div>')


def _ofertas(resultado: simulador.Resultado, negociar) -> None:
    lote = resultado.lote
    st.markdown(marca.paso(2, "Ofertas que recibirías"), unsafe_allow_html=True)
    st.caption(f"Simulado con {lote.cantidad_cargas:g} cargas de {lote.tipo_cafe.lower()}"
               + (f" · {lote.puntaje_sca} puntos SCA" if lote.puntaje_sca else " · sin puntaje")
               + f" · pides {cop(lote.precio_esperado_cop_carga)} por carga.")
    mejor = resultado.mejor
    if mejor is None:
        st.info("Con este lote ningún comprador de demostración haría una oferta. Mira abajo por qué.")
    else:
        vs = f"{marca.pct(mejor.pct_vs_fnc)} vs. FNC" if mejor.pct_vs_fnc is not None else ""
        st.markdown(marca.tarjeta_precio(
            "Mejor oferta simulada", f"{cop(mejor.precio_cop_carga)} / carga",
            f"{mejor.comprador.nombre} · total {cop(mejor.total_cop)} por {lote.cantidad_cargas:g} cargas", vs),
            unsafe_allow_html=True)
        if resultado.ganancia_vs_fnc is not None:
            ganancia = resultado.ganancia_vs_fnc
            st.markdown(marca.tarjeta(
                "Frente a vender todo al precio FNC", ("+" if ganancia >= 0 else "−") + cop(abs(ganancia)),
                f"Al precio FNC recibirías {cop(resultado.total_fnc)}", "verde" if ganancia >= 0 else "rojo"),
                unsafe_allow_html=True)
        negociando = st.session_state.get(_SIM_NEG)
        for i, o in enumerate(resultado.ofertas):
            with st.container(border=True):
                st.markdown(_cabecera_comprador(o.comprador), unsafe_allow_html=True)
                chips = ([marca.chip("Mejor oferta", "verde")] if i == 0 else [])
                if o.pct_vs_fnc is not None:
                    chips.append(marca.chip(f"{marca.pct(o.pct_vs_fnc)} vs. FNC", "verde" if o.pct_vs_fnc >= 0 else "rojo"))
                if o.recoge_en_finca:
                    chips.append(marca.chip("Recoge en la finca"))
                chips.append(marca.chip("Demostración", "demo"))
                st.markdown(" ".join(chips), unsafe_allow_html=True)
                st.markdown(
                    f'<div class="ct-oferta {"" if i == 0 else "normal"}">'
                    f'<div class="fila"><span>Precio por carga</span><b>{cop(o.precio_cop_carga)}</b></div>'
                    f'<div class="fila"><span>Total ({o.cantidad_cargas:g} cargas)</span><b>{cop(o.total_cop)}</b></div>'
                    "</div>", unsafe_allow_html=True)
                activo = negociando is not None and negociando.id_comprador == o.comprador.id
                st.button("Negociando…" if activo else "Negociar con este comprador", key=f"sim_neg_{o.comprador.id}",
                          icon=":material/handshake:", use_container_width=True, disabled=activo,
                          on_click=negociar, args=(o,))
    for consejo in simulador.consejos(resultado):
        st.markdown(f":material/lightbulb: {consejo}")
    if resultado.sin_oferta:
        n = len(resultado.sin_oferta)
        with st.expander(f"Por qué {n} comprador{'es' if n != 1 else ''} no ofert{'aron' if n != 1 else 'ó'}"):
            for c, motivo in resultado.sin_oferta:
                st.markdown(f"**{c.nombre}** · {motivo}")
    st.caption(":material/info: " + simulador.AVISO + " " + simulador.NOTA_TOTALES)


def _negociacion(resultado: simulador.Resultado, neg: simulador.Negociacion, cierre, contraofertar, cerrar) -> None:
    lote = resultado.lote
    comprador = next(c for c in mercado.COMPRADORES_DEMO if c.id == neg.id_comprador)
    st.markdown(marca.paso(3, "Negocia (práctica)"), unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(_cabecera_comprador(comprador), unsafe_allow_html=True)
        for quien, texto in neg.historial:
            st.markdown(marca.burbuja(texto, quien, "respuesta simulada" if quien == "ellos" else ""),
                        unsafe_allow_html=True)
        if not neg.cerrada:
            clave = f"sim_contra_{neg.id_comprador}_{len(neg.historial)}"   # un campo nuevo por ronda
            st.number_input("Tu contraoferta (COP por carga)", min_value=neg.vigente, max_value=20_000_000,
                            value=max(neg.vigente, lote.precio_esperado_cop_carga), step=10_000, key=clave)
            col_a, col_b = st.columns(2)
            col_a.button("Enviar contraoferta", icon=":material/send:", use_container_width=True,
                         key=f"enviar_{clave}", on_click=contraofertar, args=(clave,))
            col_b.button(f"Aceptar {cop(neg.vigente)}", type="primary", icon=":material/check:",
                         use_container_width=True, key=f"aceptar_{clave}", on_click=cerrar)
        elif cierre:
            diferencia = cierre.get("diferencia_vs_fnc")
            extra = (f" Son {cop(abs(diferencia))} {'más' if diferencia >= 0 else 'menos'} que al precio FNC."
                     if diferencia is not None else "")
            st.success(f"Venta de práctica cerrada: {lote.cantidad_cargas:g} cargas a {cop(cierre['precio'])} = "
                       f"{cop(cierre['total'])}.{extra} Así funcionaría la venta directa cuando se active.")


if not config.mercado_activo():
    # Beta: la venta directa real está apagada hasta tener compradores reales
    # verificados (COFITECH_MERCADO_ACTIVO=1 la enciende). En su lugar, simulador.
    _beta_simulador()
    st.stop()

SECCIONES = ["Compradores", "Publicar mi lote", "Mis lotes y mensajes"]
_SECCION = "vender_seccion"
_LOTE = "vender_lote"
_CONVERSACION = "vender_conversacion"
_AVISO = "vender_aviso"
_ERRORES = "vender_errores"
ESTADO_LEGIBLE = {"publicado": ("Publicado", ""), "negociando": ("En negociación", "ambar"),
                  "vendido": ("Vendido", "verde"), "retirado": ("Retirado", "rojo")}

ctx = obtener_contexto()
finca = ctx.finca
precio_fnc = round(ctx.mercado.precio_fnc_cop_carga) if ctx.mercado.precio_fnc_cop_carga else None


def _pct_fnc(precio: float) -> float | None:
    return round(100 * (precio / precio_fnc - 1), 1) if precio_fnc else None


# ────────────────────────────── Acciones ────────────────────────────────────
def ir_a(seccion: str) -> None:
    st.session_state[_SECCION] = seccion


def publicar() -> None:
    e = st.session_state
    puntaje = e.get("lote_puntaje") if e.get("lote_con_puntaje") else None
    d = ctx.diagnostico
    lote = mercado.Lote(
        tipo_cafe=e["lote_tipo"], cantidad_cargas=float(e["lote_cantidad"]),
        precio_esperado_cop_carga=int(e["lote_precio"]), precio_fnc_ref_cop_carga=precio_fnc,
        municipio=finca.municipio, departamento=finca.departamento, codigo_dane=finca.codigo_dane,
        altitud_msnm=finca.altitud_msnm, variedad=e["lote_variedad"], disponible_desde=e["lote_disponible"],
        puntaje_sca=puntaje, ultimo_diagnostico=d.clase if d else None, riesgo_fitosanitario=ctx.muestreo.riesgo,
        canales=list(e.get("lote_canales") or []))
    errores = lote.validar()
    if errores:
        e[_ERRORES] = errores
        return
    lote, ofertas = mercado.publicar_lote(lote)
    registrar_evento_uso("Mercado", "lote_publicado", {
        "tipo_cafe": lote.tipo_cafe, "cargas": lote.cantidad_cargas, "ofertas_recibidas": len(ofertas),
        "pct_sobre_fnc": _pct_fnc(lote.precio_esperado_cop_carga)})
    n = len(ofertas)
    e[_AVISO] = (f"Lote publicado. {n} comprador{'es' if n != 1 else ''} ya te "
                 f"hici{'eron' if n != 1 else 'o'} una oferta." if n else
                 "Lote publicado. Todavía ningún comprador busca un lote así; te avisaremos aquí.")
    e.update({_LOTE: lote.id, _CONVERSACION: None, _SECCION: "Mis lotes y mensajes"})


def aceptar(lote: mercado.Lote, oferta: mercado.Oferta) -> None:
    mercado.aceptar(lote, oferta)
    registrar_evento_uso("Mercado", "oferta_aceptada", {"pct_sobre_fnc": _pct_fnc(oferta.precio_cop_carga),
                                                        "simulada": oferta.es_simulada})


def rechazar(lote: mercado.Lote, oferta: mercado.Oferta) -> None:
    mercado.rechazar(lote, oferta)
    registrar_evento_uso("Mercado", "oferta_rechazada", {"simulada": oferta.es_simulada})


def contraofertar(lote: mercado.Lote, oferta: mercado.Oferta) -> None:
    vigente = mercado.contraofertar(lote, oferta, int(st.session_state[f"precio_{oferta.id}"]))
    registrar_evento_uso("Mercado", "contraoferta", {"resultado": vigente.estado, "simulada": oferta.es_simulada})


def retirar(lote: mercado.Lote) -> None:
    mercado.cambiar_estado_lote(lote, "retirado")
    registrar_evento_uso("Mercado", "lote_retirado", {"tipo_cafe": lote.tipo_cafe})


def enviar(lote: mercado.Lote, id_comprador: str, clave: str) -> None:
    texto = (st.session_state.get(clave) or "").strip()
    if texto:
        mercado.enviar_mensaje(lote, id_comprador, texto)
        registrar_evento_uso("Mercado", "mensaje_enviado", {"caracteres": len(texto)})   # nunca el texto
        st.session_state[clave] = ""


# ────────────────────────────── Encabezado ──────────────────────────────────
st.title("Vender mi café")
st.caption("Contacta compradores directamente, sin intermediarios")

if precio_fnc:
    st.markdown(marca.tarjeta("Precio de referencia FNC · úsalo para comparar ofertas",
                              f"{cop(precio_fnc)} / carga",
                              f"Precio interno de {mes_anio(ctx.mercado.fecha)} · carga de 125 kg de pergamino seco"),
                unsafe_allow_html=True)
else:
    st.warning("No hay precio FNC cargado: las ofertas no se pueden comparar. Ejecuta el ETL de precios.")

if st.session_state.get(_SECCION) not in SECCIONES:
    st.session_state[_SECCION] = SECCIONES[0]
# st.radio y no st.segmented_control: el probador de Streamlit (AppTest) no maneja este último.
seccion = st.radio("Sección", SECCIONES, key=_SECCION, horizontal=True, label_visibility="collapsed")
compradores = mercado.compradores()


# ───────────────────────────── 5 · Compradores ──────────────────────────────
def vista_compradores() -> None:
    filtro = st.radio("Tipo de comprador", ["Todos", "Cooperativas", "Tostadores", "Exportadores"],
                      horizontal=True, label_visibility="collapsed", key="vender_filtro")
    tipo = {"Cooperativas": "Cooperativa", "Tostadores": "Tostador", "Exportadores": "Exportador"}.get(filtro)
    lista = sorted((c for c in compradores if tipo is None or c.tipo == tipo),
                   key=lambda c: (c.departamento != finca.departamento, c.tipo, c.nombre))   # primero los de la zona
    if any(c.es_demo for c in lista):
        st.caption(":material/info: " + mercado.AVISO_DEMO)
    for c in lista:
        with st.container(border=True):
            zona = " · en tu departamento" if c.departamento == finca.departamento else ""
            st.markdown(
                f'<div class="ct-comprador">{marca.avatar(c.iniciales, COLOR_TIPO.get(c.tipo, "#6B4A35"))}'
                f'<div><div class="n">{marca._e(c.nombre)}</div>'
                f'<div class="s">{marca._e(c.tipo)} · {marca._e(c.municipio)}, {marca._e(c.departamento)}{zona}</div>'
                f'</div></div>', unsafe_allow_html=True)
            chips = [marca.chip(f"Paga +{cop(c.prima_cop_carga)}/carga" if c.prima_cop_carga else "Precio FNC", "verde"),
                     marca.chip(c.busca)]
            if c.es_demo:
                chips.append(marca.chip("Demostración", "demo"))
            st.markdown(" ".join(chips), unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            col_a.button("Ofrecerle mi café", key=f"ofrecer_{c.id}", icon=":material/storefront:", type="primary",
                         use_container_width=True, on_click=ir_a, args=("Publicar mi lote",))
            col_b.button("WhatsApp", key=f"wa_{c.id}", icon=":material/chat:", disabled=True,
                         use_container_width=True,
                         help="Disponible cuando el comprador registre su número. Mientras tanto, negocia en el chat de la app.")


# ─────────────────────────── 6 · Publicar mi lote ───────────────────────────
def vista_publicar() -> None:
    st.markdown("**Publicar mi lote** · los compradores te escriben a ti")
    for error in st.session_state.pop(_ERRORES, []):
        st.error(error)
    tipo = st.radio("Tipo de café", list(mercado.TIPOS_CAFE), horizontal=True, key="lote_tipo")
    c1, c2 = st.columns(2)
    c1.number_input("Cantidad (cargas de 125 kg)", min_value=0.5, max_value=10_000.0, value=20.0, step=0.5,
                    key="lote_cantidad", help="Para cereza, escribe las cargas equivalentes de pergamino seco.")
    c2.date_input("Disponible desde", value=date.today() + timedelta(days=7), min_value=date.today(),
                  format="DD/MM/YYYY", key="lote_disponible")
    variedades = list(VARIEDADES)
    st.selectbox("Variedad", variedades, key="lote_variedad", help=AYUDA_VARIEDAD,
                 index=variedades.index(finca.variedad) if finca.variedad in variedades else len(variedades) - 1)
    con_puntaje = st.toggle("Tengo puntaje de catación (SCA)", value=tipo == "Especial", key="lote_con_puntaje")
    puntaje = st.slider("Puntaje SCA", 60, 100, 84, key="lote_puntaje") if con_puntaje else None

    sugerido = mercado.redondear(precio_fnc * 1.05) if precio_fnc else 2_500_000
    precio = st.number_input("Precio que esperas (COP por carga)", min_value=100_000, max_value=20_000_000,
                             value=sugerido, step=10_000, key="lote_precio")
    if precio_fnc:
        dif = _pct_fnc(precio)
        st.markdown(marca.chip(f"{marca.pct(dif)} vs. precio FNC", "verde" if dif >= 0 else "rojo"),
                    unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("**Datos que verá el comprador** · " + marca.chip("Automático"), unsafe_allow_html=True)
        d = ctx.diagnostico
        lugar = f"{finca.municipio}, {finca.departamento}"
        datos = [f"{finca.altitud_msnm:,.0f} msnm · {lugar}".replace(",", ".", 1) if finca.altitud_msnm else lugar,
                 f"Último diagnóstico de la finca: {d.clase} ({d.confianza:.0%})" if d else "Sin diagnóstico por foto aún",
                 f"Puntaje SCA: {puntaje}" if puntaje else "Sin puntaje de catación"]
        for dato in datos:
            st.markdown(f":material/check: {dato}")
        st.caption("No se comparte tu nombre, teléfono ni documento.")

    st.pills("¿Cómo te contactan?", list(mercado.CANALES), selection_mode="multi", default=["chat"],
             format_func=mercado.CANALES.get, key="lote_canales")
    st.button("Publicar lote", type="primary", use_container_width=True, icon=":material/publish:", on_click=publicar)


# ───────────────────────── 7 · Mis lotes y mensajes ─────────────────────────
def _etiqueta_lote(l: mercado.Lote) -> str:
    estado = ESTADO_LEGIBLE.get(l.estado, (l.estado, ""))[0]
    return f"{l.cantidad_cargas:g} cargas · {l.tipo_cafe} · {l.disponible_desde:%d/%m} · {estado}"


def vista_mis_lotes() -> None:
    if aviso := st.session_state.pop(_AVISO, None):
        st.success(aviso)
    lotes = mercado.mis_lotes()
    if not lotes:
        st.info("Aún no has publicado lotes. Publica uno y los compradores te escriben.")
        st.button("Publicar mi lote", type="primary", on_click=ir_a, args=("Publicar mi lote",))
        return

    ids = [l.id for l in lotes]
    indice = ids.index(st.session_state[_LOTE]) if st.session_state.get(_LOTE) in ids else 0
    id_lote = st.selectbox("Lote", ids, index=indice, format_func=lambda i: _etiqueta_lote(lotes[ids.index(i)]))
    st.session_state[_LOTE] = id_lote
    lote = lotes[ids.index(id_lote)]

    ofertas = mercado.ofertas_de(lote.id)
    mensajes = mercado.mensajes_de(lote.id)
    conversaciones = list(dict.fromkeys([o.id_comprador for o in ofertas] + [m.id_comprador for m in mensajes]))
    texto_estado, tono = ESTADO_LEGIBLE.get(lote.estado, (lote.estado, ""))
    st.markdown(marca.chip(texto_estado, tono) + " " + marca.chip(f"Pides {cop(lote.precio_esperado_cop_carga)}/carga"),
                unsafe_allow_html=True)
    if lote.estado in ("publicado", "negociando"):
        st.button("Retirar lote", icon=":material/close:", on_click=retirar, args=(lote,), key=f"retirar_{lote.id}")
    if not conversaciones:
        st.info("Ningún comprador ha escrito sobre este lote todavía.")
        return

    por_id = {c.id: c for c in compradores}
    actual = st.session_state.get(_CONVERSACION)
    id_comprador = st.radio("Conversación", conversaciones, horizontal=True,
                            index=conversaciones.index(actual) if actual in conversaciones else 0,
                            format_func=lambda i: por_id[i].nombre if i in por_id else i)
    st.session_state[_CONVERSACION] = id_comprador
    chat(lote, por_id.get(id_comprador), id_comprador, [m for m in mensajes if m.id_comprador == id_comprador], ofertas)


def chat(lote: mercado.Lote, c: mercado.Comprador | None, id_comprador: str, mensajes, ofertas) -> None:
    with st.container(border=True):
        color = COLOR_TIPO.get(c.tipo, "#6B4A35") if c else "#6B4A35"
        st.markdown(
            f'<div class="ct-comprador">{marca.avatar(c.iniciales if c else "?", color)}'
            f'<div><div class="n">{marca._e(c.nombre if c else id_comprador)}</div>'
            f'<div class="s">{marca._e(f"{c.tipo} · {c.municipio}" if c else "")}</div></div></div>',
            unsafe_allow_html=True)
        if c and c.es_demo:
            st.caption(":material/info: " + mercado.AVISO_DEMO)
        st.markdown(marca.tarjeta("Sobre tu lote", f"{lote.cantidad_cargas:g} cargas · {lote.tipo_cafe}",
                                  (lote.variedad or "Variedad sin dato")
                                  + (f" · {lote.puntaje_sca} pts" if lote.puntaje_sca else "")),
                    unsafe_allow_html=True)
        for m in mensajes:
            quien = {"caficultor": "yo", "comprador": "ellos"}.get(m.autor, "sistema")
            st.markdown(marca.burbuja(m.texto, quien, "respuesta simulada" if m.es_simulado else ""),
                        unsafe_allow_html=True)

        vigente = mercado.oferta_vigente(ofertas, id_comprador)
        if vigente:
            tarjeta_oferta(lote, vigente)

        if lote.estado not in ("vendido", "retirado"):
            clave = f"msg_{lote.id}_{id_comprador}"
            col_t, col_b = st.columns([4, 1], vertical_alignment="bottom")
            col_t.text_input("Escribe un mensaje", max_chars=mercado.MAX_TEXTO, placeholder="Escribe un mensaje...",
                             label_visibility="collapsed", key=clave)
            col_b.button("Enviar", icon=":material/send:", key=f"enviar_{clave}", on_click=enviar,
                         args=(lote, id_comprador, clave), use_container_width=True)
            st.caption(mercado.AVISO_PRIVACIDAD)


def tarjeta_oferta(lote: mercado.Lote, oferta: mercado.Oferta) -> None:
    pct = _pct_fnc(oferta.precio_cop_carga)
    vs = f"{marca.pct(pct)} vs. FNC" if pct is not None else ""
    estado = {"pendiente": "Oferta formal" if oferta.origen == "comprador" else "Tu contraoferta",
              "aceptada": "Oferta aceptada", "rechazada": "Oferta rechazada",
              "contraofertada": "Contraofertada"}[oferta.estado]
    st.markdown(
        f'<div class="ct-oferta"><div class="fila"><b>{marca._e(estado)}</b>{marca.chip(vs, "verde") if vs else ""}</div>'
        f'<div class="fila"><span>Precio por carga</span><b>{cop(oferta.precio_cop_carga)}</b></div>'
        f'<div class="fila"><span>Total ({oferta.cantidad_cargas:g} cargas)</span><b>{cop(oferta.total_cop)}</b></div>'
        + ('<div class="fila"><span>Recogen el café en la finca</span></div>' if oferta.recoge_en_finca else "")
        + "</div>", unsafe_allow_html=True)
    if oferta.estado != "pendiente" or oferta.origen != "comprador" or lote.estado in ("vendido", "retirado"):
        return
    col_a, col_b = st.columns(2)
    col_a.button("Aceptar", type="primary", use_container_width=True, key=f"aceptar_{oferta.id}",
                 on_click=aceptar, args=(lote, oferta))
    col_b.button("Rechazar", use_container_width=True, key=f"rechazar_{oferta.id}",
                 on_click=rechazar, args=(lote, oferta))
    with st.expander("Contraofertar"):
        st.number_input("Tu precio por carga (COP)", min_value=100_000, max_value=20_000_000,
                        value=max(oferta.precio_cop_carga, lote.precio_esperado_cop_carga), step=10_000,
                        key=f"precio_{oferta.id}")
        st.button("Enviar contraoferta", key=f"contra_{oferta.id}", on_click=contraofertar, args=(lote, oferta))


{"Compradores": vista_compradores, "Publicar mi lote": vista_publicar,
 "Mis lotes y mensajes": vista_mis_lotes}[seccion]()
