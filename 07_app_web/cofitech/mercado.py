"""Venta directa de café (RF09): pasos 5–7 del MockUp ganador («Vender»).

El caficultor publica un lote, los compradores interesados le hacen una oferta
formal y negocian por chat sin intermediarios. La cooperativa ve en su consola
cuánto café se está ofreciendo en cada municipio de su zona.

Dónde se guarda (igual que los diagnósticos, ver ``repositorio.py``):

* Supabase: ``cafe.mk_comprador``, ``cafe.mk_lote``, ``cafe.mk_oferta`` y
  ``cafe.mk_mensaje`` (``03_scripts/bd/05_marketplace.sql``).
* Archivos locales en ``05_resultados/marketplace/`` como respaldo: la app
  nunca se detiene por la base. Cada cambio de estado se anexa como una línea
  nueva y al leer manda la última.

Compradores de demostración
---------------------------
El prototipo no tiene compradores reales. Los de ``COMPRADORES_DEMO`` son
ficticios (``es_demo``) y la app responde por ellos con reglas simples
(``es_simulada`` / ``es_simulado``); la pantalla lo dice siempre. Cuando un
comprador real se registre en ``cafe.mk_comprador`` con ``es_demo = false``,
sus respuestas dejan de simularse.

Privacidad (Ley 1581 de 2012): el lote no guarda nombre, teléfono ni documento
del caficultor; se liga a un ``id_sesion`` aleatorio.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import pandas as pd
import streamlit as st

from cofitech import repositorio
from cofitech.repositorio import db_client

log = logging.getLogger("cofitech.mercado")

PROYECTO: Path = Path(__file__).resolve().parents[2]
DIR_LOCAL: Path = Path(os.environ.get("COFITECH_DIR_MERCADO", PROYECTO / "05_resultados" / "marketplace"))

TIPOS_CAFE: tuple[str, ...] = ("Pergamino seco", "Cereza", "Especial")
TIPOS_COMPRADOR: tuple[str, ...] = ("Cooperativa", "Tostador", "Exportador")
CANALES: dict[str, str] = {"chat": "Chat en la app", "whatsapp": "WhatsApp", "llamada": "Llamada"}
ESTADOS_LOTE: tuple[str, ...] = ("publicado", "negociando", "vendido", "retirado")
MAX_TEXTO = 500                 # mismo límite que cafe.mk_mensaje.texto
REDONDEO_COP = 1_000            # los precios por carga se redondean a miles
MARGEN_NEGOCIACION = 1.25       # el comprador acepta hasta FNC + 1,25 × su prima

AVISO_DEMO = ("Comprador de demostración: es ficticio y sus respuestas las genera la app. "
              "Sirve para probar el flujo de venta del prototipo.")
AVISO_PRIVACIDAD = ("No escribas tu nombre, teléfono ni número de documento: CofiTech no los guarda "
                    "y el comprador los pedirá por un canal oficial cuando cierren el trato.")


# ─────────────────────────────── Modelo ─────────────────────────────────────
@dataclass(frozen=True)
class Comprador:
    id: str
    nombre: str
    tipo: str
    municipio: str
    departamento: str
    codigo_dane: str
    busca: str
    prima_cop_carga: int
    puntaje_min: Optional[int] = None
    cargas_min: float = 1.0
    es_demo: bool = True
    activo: bool = True

    @property
    def iniciales(self) -> str:
        palabras = [p for p in self.nombre.replace("(demo)", "").split() if p[0].isupper()]
        return "".join(p[0] for p in palabras[:2]) or self.nombre[:2].upper()

    @property
    def precio_maximo_extra(self) -> int:
        """Lo máximo que paga sobre el precio FNC en una negociación."""
        return int(round(self.prima_cop_carga * MARGEN_NEGOCIACION))


# Igual a la semilla de 05_marketplace.sql (lo verifica tests/test_mercado.py).
COMPRADORES_DEMO: tuple[Comprador, ...] = (
    Comprador("demo-tostadora-montana", "Tostadora La Montaña (demo)", "Tostador", "Cali", "Valle del Cauca",
              "76001", "Café especial de 84 puntos o más", 180_000, 84, 1.0),
    Comprador("demo-cafes-altos-valle", "Cafés Altos del Valle (demo)", "Cooperativa", "Sevilla", "Valle del Cauca",
              "76736", "Pergamino seco · precio FNC más bono", 40_000, None, 1.0),
    Comprador("demo-exportadora-andina", "Exportadora Andina (demo)", "Exportador", "Armenia", "Quindío",
              "63001", "Lotes de 50 cargas o más, 82 puntos o más", 90_000, 82, 50.0),
    Comprador("demo-cooperativa-suroeste", "Cooperativa del Suroeste (demo)", "Cooperativa", "Andes", "Antioquia",
              "05034", "Pergamino seco · precio FNC más bono", 35_000, None, 1.0),
    Comprador("demo-tostadora-sur-huila", "Tostadora Sur del Huila (demo)", "Tostador", "Pitalito", "Huila",
              "41551", "Café especial de 85 puntos o más", 200_000, 85, 1.0),
)


@dataclass
class Lote:
    tipo_cafe: str
    cantidad_cargas: float
    precio_esperado_cop_carga: int
    precio_fnc_ref_cop_carga: Optional[int]
    municipio: str = ""
    departamento: str = ""
    codigo_dane: Optional[str] = None
    altitud_msnm: Optional[float] = None
    variedad: Optional[str] = None
    disponible_desde: date = field(default_factory=date.today)
    puntaje_sca: Optional[int] = None
    ultimo_diagnostico: Optional[str] = None
    riesgo_fitosanitario: Optional[str] = None
    canales: list[str] = field(default_factory=lambda: ["chat"])
    estado: str = "publicado"
    es_demo: bool = False
    id: str = field(default_factory=lambda: uuid4().hex)
    fecha: str = field(default_factory=lambda: _ahora())
    id_sesion: Optional[str] = None

    def validar(self) -> list[str]:
        errores: list[str] = []
        if self.tipo_cafe not in TIPOS_CAFE:
            errores.append("Elige el tipo de café.")
        if not 0 < self.cantidad_cargas <= 10_000:
            errores.append("La cantidad debe estar entre 0,5 y 10.000 cargas.")
        if self.precio_esperado_cop_carga <= 0:
            errores.append("Escribe el precio que esperas por carga.")
        if self.puntaje_sca is not None and not 60 <= self.puntaje_sca <= 100:
            errores.append("El puntaje SCA va de 60 a 100.")
        if self.tipo_cafe == "Especial" and self.puntaje_sca is None:
            errores.append("Para vender como café especial indica el puntaje SCA de la catación.")
        if not self.canales:
            errores.append("Elige al menos un canal de contacto.")
        return errores

    @property
    def pct_sobre_fnc(self) -> Optional[float]:
        if not self.precio_fnc_ref_cop_carga:
            return None
        return 100.0 * (self.precio_esperado_cop_carga / self.precio_fnc_ref_cop_carga - 1)


@dataclass
class Oferta:
    id_lote: str
    id_comprador: str
    origen: str                       # "comprador" | "caficultor"
    precio_cop_carga: int
    cantidad_cargas: float
    recoge_en_finca: bool = False
    estado: str = "pendiente"         # pendiente | aceptada | rechazada | contraofertada
    es_simulada: bool = False
    id: str = field(default_factory=lambda: uuid4().hex)
    fecha: str = field(default_factory=lambda: _ahora())

    @property
    def total_cop(self) -> float:
        return self.precio_cop_carga * self.cantidad_cargas


@dataclass
class Mensaje:
    id_lote: str
    id_comprador: str
    autor: str                        # "caficultor" | "comprador" | "sistema"
    texto: str
    es_simulado: bool = False
    fecha: str = field(default_factory=lambda: _ahora())


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def redondear(valor: float) -> int:
    return int(round(valor / REDONDEO_COP) * REDONDEO_COP)


def cop(valor: Optional[float]) -> str:
    """Pesos con punto de miles: 2.830.000."""
    if valor is None:
        return "—"
    return f"${valor:,.0f}".replace(",", ".")


# ───────────────────────────── Reglas de negocio ────────────────────────────
def le_interesa(comprador: Comprador, lote: Lote) -> bool:
    """¿El lote cumple lo que busca el comprador?"""
    if not comprador.activo:
        return False
    if lote.cantidad_cargas < comprador.cargas_min:
        return False
    if comprador.puntaje_min is not None and (lote.puntaje_sca is None or lote.puntaje_sca < comprador.puntaje_min):
        return False
    if lote.tipo_cafe == "Cereza" and comprador.tipo != "Cooperativa":
        return False          # la cereza se vende a la cooperativa o al beneficio de la zona
    return True


def precio_ofrecido(comprador: Comprador, lote: Lote) -> Optional[int]:
    """Primera oferta: precio FNC + prima del comprador, sin pasar del precio que pidió el caficultor."""
    if not lote.precio_fnc_ref_cop_carga:
        return None
    return min(redondear(lote.precio_fnc_ref_cop_carga + comprador.prima_cop_carga), lote.precio_esperado_cop_carga)


def precio_maximo(comprador: Comprador, lote: Lote) -> Optional[int]:
    if not lote.precio_fnc_ref_cop_carga:
        return None
    return redondear(lote.precio_fnc_ref_cop_carga + comprador.precio_maximo_extra)


def respuesta_a_contraoferta(comprador: Comprador, lote: Lote, anterior: int, pedido: int) -> tuple[str, int]:
    """Cómo responde un comprador de demostración a una contraoferta del caficultor.

    Returns:
        ``("acepta", pedido)`` si el precio pedido cabe en su margen, o
        ``("contraoferta", precio)`` con el punto medio entre su oferta anterior
        y lo pedido, sin pasar de su máximo.
    """
    maximo = precio_maximo(comprador, lote) or anterior
    if pedido <= maximo:
        return "acepta", pedido
    return "contraoferta", min(maximo, max(anterior, redondear((anterior + pedido) / 2)))


def compradores_de_zona(compradores: list[Comprador], departamento: str) -> list[Comprador]:
    return [c for c in compradores if c.departamento == departamento]


def resumen_por_municipio(lotes: list[Lote], incluir_demo: bool = False) -> pd.DataFrame:
    """Oferta publicada por municipio (misma lógica que ``cafe.vw_lotes_zona``)."""
    columnas = ["codigo_dane", "municipio", "departamento", "lotes", "cargas", "precio_esperado_medio",
                "precio_fnc_medio", "lotes_especiales", "ultimo_lote"]
    activos = [l for l in lotes if l.estado in ("publicado", "negociando") and (incluir_demo or not l.es_demo)]
    if not activos:
        return pd.DataFrame(columns=columnas)
    df = pd.DataFrame([asdict(l) for l in activos])
    df["especial"] = (df["tipo_cafe"] == "Especial").astype(int)
    resumen = df.groupby("codigo_dane", dropna=False).agg(
        municipio=("municipio", "max"), departamento=("departamento", "max"), lotes=("id", "count"),
        cargas=("cantidad_cargas", "sum"), precio_esperado_medio=("precio_esperado_cop_carga", "mean"),
        precio_fnc_medio=("precio_fnc_ref_cop_carga", "mean"), lotes_especiales=("especial", "sum"),
        ultimo_lote=("fecha", "max")).reset_index()
    return resumen[columnas]


# ─────────────────────────────── Persistencia ───────────────────────────────
def _ruta(nombre: str) -> Path:
    return DIR_LOCAL / f"{nombre}.jsonl"


def _local(nombre: str, registro: dict[str, Any]) -> None:
    repositorio._anexar(_ruta(nombre), registro)


def _ultimos(nombre: str) -> list[dict[str, Any]]:
    """Registros locales; una línea posterior con el mismo id actualiza la anterior."""
    por_id: dict[str, dict[str, Any]] = {}
    for fila in repositorio._leer_jsonl(_ruta(nombre)):
        if "id" in fila:
            por_id[fila["id"]] = {**por_id.get(fila["id"], {}), **fila}
    return list(por_id.values())


def _nube(funcion, *args) -> Any:
    return repositorio._en_nube(funcion, *args)


def _desde_nube(funcion, *args) -> Optional[Any]:
    """Lectura en Supabase; ``None`` si no hay base o falla (entonces se lee el archivo local)."""
    if not db_client.configurado():
        return None
    try:
        return funcion(*args)
    except db_client.BaseDatosNoDisponible:
        return None
    except Exception as error:      # p. ej. faltan las tablas: no se ejecutó 05_marketplace.sql
        log.error("Lectura de venta directa en Supabase falló: %s", error)
        return None


def _a_lote(fila: dict[str, Any]) -> Lote:
    campos = {k: fila.get(k) for k in Lote.__dataclass_fields__ if k in fila}
    if isinstance(campos.get("disponible_desde"), str):
        campos["disponible_desde"] = date.fromisoformat(campos["disponible_desde"][:10])
    if isinstance(campos.get("fecha"), datetime):
        campos["fecha"] = campos["fecha"].isoformat()
    campos["id"] = str(campos.get("id", "")).replace("-", "")
    for k in ("precio_esperado_cop_carga", "precio_fnc_ref_cop_carga", "puntaje_sca"):
        if campos.get(k) is not None:
            campos[k] = int(campos[k])
    campos["canales"] = list(campos.get("canales") or ["chat"])
    return Lote(**campos)


def _a_oferta(fila: dict[str, Any]) -> Oferta:
    campos = {k: fila.get(k) for k in Oferta.__dataclass_fields__ if k in fila}
    for k in ("id", "id_lote"):
        campos[k] = str(campos[k]).replace("-", "")
    if isinstance(campos.get("fecha"), datetime):
        campos["fecha"] = campos["fecha"].isoformat()
    campos["precio_cop_carga"] = int(campos["precio_cop_carga"])
    return Oferta(**campos)


def _a_mensaje(fila: dict[str, Any]) -> Mensaje:
    campos = {k: fila.get(k) for k in Mensaje.__dataclass_fields__ if k in fila}
    campos["id_lote"] = str(campos["id_lote"]).replace("-", "")
    if isinstance(campos.get("fecha"), datetime):
        campos["fecha"] = campos["fecha"].isoformat()
    return Mensaje(**campos)


def compradores() -> list[Comprador]:
    """Compradores activos: de Supabase si responde; si no, los de demostración."""
    filas = _desde_nube(db_client.listar_compradores)
    if not filas:
        return list(COMPRADORES_DEMO)
    lista = []
    for f in filas:
        lista.append(Comprador(
            id=f["id"], nombre=f["nombre"], tipo=f["tipo"], municipio=f.get("municipio") or "",
            departamento=f.get("departamento") or "", codigo_dane=f.get("codigo_dane") or "",
            busca=f.get("busca") or "", prima_cop_carga=int(f.get("prima_cop_carga") or 0),
            puntaje_min=f.get("puntaje_min"), cargas_min=float(f.get("cargas_min") or 1),
            es_demo=bool(f.get("es_demo", True)), activo=bool(f.get("activo", True))))
    return lista


def comprador(id_comprador: str) -> Optional[Comprador]:
    return next((c for c in compradores() if c.id == id_comprador), None)


def _registro_lote(lote: Lote) -> dict[str, Any]:
    registro = asdict(lote)
    registro["disponible_desde"] = lote.disponible_desde.isoformat()
    return registro


def publicar_lote(lote: Lote) -> tuple[Lote, list[Oferta]]:
    """Guarda el lote y, por cada comprador de demostración interesado, su primera oferta simulada.

    Raises:
        ValueError: Si el lote no pasa ``Lote.validar``.
    """
    errores = lote.validar()
    if errores:
        raise ValueError(" ".join(errores))
    lote.id_sesion = lote.id_sesion or repositorio.id_sesion()
    registro = _registro_lote(lote)
    _local("lotes", registro)
    _nube(db_client.insertar_lote, registro)

    ofertas: list[Oferta] = []
    for c in compradores():
        if not (c.es_demo and le_interesa(c, lote)):
            continue
        precio = precio_ofrecido(c, lote)
        if precio is None:
            continue
        recoge = c.tipo == "Cooperativa" or lote.cantidad_cargas >= 10
        oferta = Oferta(lote.id, c.id, "comprador", precio, lote.cantidad_cargas, recoge, es_simulada=True)
        texto = (f"Hola. Vimos su lote de {lote.municipio or 'su finca'}: {lote.cantidad_cargas:g} cargas de "
                 f"{lote.tipo_cafe.lower()}. ¿Nos puede enviar una muestra de 500 g? Mientras tanto le "
                 f"dejamos una oferta formal de {cop(precio)} por carga.")
        _guardar_oferta(oferta)
        _guardar_mensaje(Mensaje(lote.id, c.id, "comprador", texto, es_simulado=True))
        ofertas.append(oferta)
    if ofertas:
        cambiar_estado_lote(lote, "negociando")
    return lote, ofertas


def cambiar_estado_lote(lote: Lote, estado: str) -> None:
    if estado not in ESTADOS_LOTE:
        raise ValueError(f"Estado de lote desconocido: {estado}")
    lote.estado = estado
    _local("lotes", {"id": lote.id, "estado": estado, "actualizado": _ahora()})
    _nube(db_client.actualizar_estado_lote, lote.id, estado)


def _guardar_oferta(oferta: Oferta) -> None:
    registro = asdict(oferta)
    _local("ofertas", registro)
    _nube(db_client.insertar_oferta, registro)


def _cambiar_estado_oferta(oferta: Oferta, estado: str) -> None:
    oferta.estado = estado
    _local("ofertas", {"id": oferta.id, "estado": estado})
    _nube(db_client.actualizar_estado_oferta, oferta.id, estado)


def _guardar_mensaje(mensaje: Mensaje) -> None:
    registro = asdict(mensaje)
    _local("mensajes", {"id": uuid4().hex, **registro})
    _nube(db_client.insertar_mensaje, registro)


def _ts(valor: Any) -> pd.Timestamp:
    return pd.Timestamp(valor).tz_convert("UTC") if pd.Timestamp(valor).tzinfo else pd.Timestamp(valor, tz="UTC")


def _fusionar(nube: Optional[list[dict[str, Any]]], locales: list[dict[str, Any]], clave) -> list[dict[str, Any]]:
    """Supabase manda; se agregan los registros locales que no llegaron a la nube (p. ej. sin red)."""
    if nube is None:
        return locales
    vistos = {clave(f) for f in nube}
    return list(nube) + [f for f in locales if clave(f) not in vistos]


def _id(fila: dict[str, Any]) -> str:
    return str(fila.get("id", "")).replace("-", "")


def _clave_mensaje(fila: dict[str, Any]) -> tuple:
    return (_ts(fila["fecha"]).floor("s"), fila.get("autor"), fila.get("texto"))


def mis_lotes() -> list[Lote]:
    """Lotes publicados en esta sesión, del más reciente al más antiguo."""
    sesion = repositorio.id_sesion()
    locales = [f for f in _ultimos("lotes") if f.get("id_sesion") == sesion and "tipo_cafe" in f]
    filas = _fusionar(_desde_nube(db_client.leer_lotes, sesion), locales, _id)
    return sorted((_a_lote(f) for f in filas), key=lambda l: _ts(l.fecha), reverse=True)


def todos_los_lotes() -> list[Lote]:
    locales = [f for f in _ultimos("lotes") if "tipo_cafe" in f]
    filas = _fusionar(_desde_nube(db_client.leer_lotes, None, 2000), locales, _id)
    return [_a_lote(f) for f in filas]


def ofertas_de(id_lote: str) -> list[Oferta]:
    locales = [f for f in _ultimos("ofertas") if f.get("id_lote") == id_lote and "origen" in f]
    filas = _fusionar(_desde_nube(db_client.leer_ofertas, id_lote), locales, _id)
    return sorted((_a_oferta(f) for f in filas), key=lambda o: _ts(o.fecha))


def mensajes_de(id_lote: str, id_comprador: Optional[str] = None) -> list[Mensaje]:
    locales = [f for f in _ultimos("mensajes") if f.get("id_lote") == id_lote]
    filas = _fusionar(_desde_nube(db_client.leer_mensajes, id_lote), locales, _clave_mensaje)
    mensajes = [_a_mensaje(f) for f in filas]
    if id_comprador:
        mensajes = [m for m in mensajes if m.id_comprador == id_comprador]
    return sorted(mensajes, key=lambda m: _ts(m.fecha))


def oferta_vigente(ofertas: list[Oferta], id_comprador: str) -> Optional[Oferta]:
    """La última oferta de esa conversación (la que se puede aceptar o contraofertar)."""
    de_comprador = [o for o in ofertas if o.id_comprador == id_comprador]
    return de_comprador[-1] if de_comprador else None


def enviar_mensaje(lote: Lote, id_comprador: str, texto: str) -> Mensaje:
    texto = texto.strip()[:MAX_TEXTO]
    if not texto:
        raise ValueError("El mensaje está vacío.")
    mensaje = Mensaje(lote.id, id_comprador, "caficultor", texto)
    _guardar_mensaje(mensaje)
    c = comprador(id_comprador)
    if c and c.es_demo:
        _guardar_mensaje(Mensaje(lote.id, id_comprador, "comprador",
                                 "Recibido, gracias. Revisamos la muestra y le confirmamos por aquí.",
                                 es_simulado=True))
    return mensaje


def aceptar(lote: Lote, oferta: Oferta) -> None:
    """El caficultor acepta la oferta vigente: lote vendido."""
    if oferta.estado != "pendiente" or oferta.origen != "comprador":
        raise ValueError("Solo se puede aceptar una oferta pendiente del comprador.")
    _cambiar_estado_oferta(oferta, "aceptada")
    _guardar_mensaje(Mensaje(lote.id, oferta.id_comprador, "sistema",
                             f"Oferta aceptada: {oferta.cantidad_cargas:g} cargas a {cop(oferta.precio_cop_carga)} "
                             f"(total {cop(oferta.total_cop)}). Acuerden la entrega y el pago con el comprador."))
    cambiar_estado_lote(lote, "vendido")


def rechazar(lote: Lote, oferta: Oferta) -> None:
    if oferta.estado != "pendiente":
        raise ValueError("Esa oferta ya no está pendiente.")
    _cambiar_estado_oferta(oferta, "rechazada")
    _guardar_mensaje(Mensaje(lote.id, oferta.id_comprador, "sistema", "Oferta rechazada por el caficultor."))


def contraofertar(lote: Lote, oferta: Oferta, precio: int) -> Oferta:
    """El caficultor propone otro precio. Un comprador de demostración responde de inmediato.

    Returns:
        La oferta que queda vigente (aceptada por el comprador o su nueva contraoferta).
    """
    if oferta.estado != "pendiente" or oferta.origen != "comprador":
        raise ValueError("Solo se puede contraofertar una oferta pendiente del comprador.")
    precio = redondear(precio)
    if precio <= 0:
        raise ValueError("Escribe un precio por carga.")
    _cambiar_estado_oferta(oferta, "contraofertada")
    mia = Oferta(lote.id, oferta.id_comprador, "caficultor", precio, oferta.cantidad_cargas, oferta.recoge_en_finca)
    _guardar_oferta(mia)
    _guardar_mensaje(Mensaje(lote.id, oferta.id_comprador, "caficultor",
                             f"Le propongo {cop(precio)} por carga."))
    c = comprador(oferta.id_comprador)
    if not (c and c.es_demo):
        return mia                                      # un comprador real responde por su cuenta
    decision, valor = respuesta_a_contraoferta(c, lote, oferta.precio_cop_carga, precio)
    if decision == "acepta":
        _cambiar_estado_oferta(mia, "aceptada")
        _guardar_mensaje(Mensaje(lote.id, c.id, "comprador",
                                 f"Trato hecho: {cop(precio)} por carga. Coordinemos la entrega.", es_simulado=True))
        cambiar_estado_lote(lote, "vendido")
        return mia
    _cambiar_estado_oferta(mia, "contraofertada")
    nueva = Oferta(lote.id, c.id, "comprador", valor, oferta.cantidad_cargas, oferta.recoge_en_finca, es_simulada=True)
    _guardar_oferta(nueva)
    _guardar_mensaje(Mensaje(lote.id, c.id, "comprador",
                             f"Podemos llegar a {cop(valor)} por carga si la taza confirma el puntaje.",
                             es_simulado=True))
    return nueva


# ──────────────────────────── Para la cooperativa ───────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def _resumen_nube(incluir_demo: bool) -> Optional[pd.DataFrame]:
    return _desde_nube(db_client.lotes_por_municipio, incluir_demo)


def lotes_por_municipio(incluir_demo: bool = False) -> tuple[pd.DataFrame, str]:
    """Oferta publicada por municipio para la consola de la cooperativa: ``(tabla, fuente)``."""
    df = _resumen_nube(incluir_demo)
    if df is not None:
        return df, "Supabase"
    return resumen_por_municipio(todos_los_lotes(), incluir_demo), "archivo local"


def refrescar() -> None:
    _resumen_nube.clear()


def a_json(objeto: Any) -> str:
    return json.dumps(asdict(objeto), ensure_ascii=False, default=str)
