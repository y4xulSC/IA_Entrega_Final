"""Vender mi café: pasos 5–7 del MockUp ganador (lámina de Sofía, RF09).

5. Compradores  · quién compra en la zona y qué paga sobre el precio FNC.
6. Publicar lote · el caficultor describe su lote en pocos toques; los datos
   de la finca y el último diagnóstico se adjuntan solos (RF01).
7. Mis lotes y mensajes · oferta formal con total calculado; aceptar,
   contraofertar o rechazar sin salir del chat.

Reglas del prototipo: los compradores son de demostración y la pantalla lo
dice; no se guardan nombre, teléfono ni documento del caficultor.

Las acciones van en callbacks (``on_click``): corren antes de dibujar la
pantalla, así pueden cambiar de sección sin ``st.rerun()``.
"""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from cofitech import marca, mercado
from cofitech.contexto_finca import VARIEDADES, mes_anio, obtener_contexto
from cofitech.mercado import cop
from cofitech.telemetria import registrar_evento_uso

st.set_page_config(page_title="Vender mi café", page_icon=marca.ICONO, layout="centered")

SECCIONES = ["Compradores", "Publicar mi lote", "Mis lotes y mensajes"]
_SECCION = "vender_seccion"
_LOTE = "vender_lote"
_CONVERSACION = "vender_conversacion"
_AVISO = "vender_aviso"
_ERRORES = "vender_errores"
COLOR_TIPO = {"Tostador": "#6B4A35", "Cooperativa": "#2E6F40", "Exportador": "#B7790F"}
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
    st.selectbox("Variedad", variedades, key="lote_variedad",
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
