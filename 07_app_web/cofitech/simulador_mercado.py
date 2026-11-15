"""Simulador de venta de café (Beta): cómo funcionaría «Vender mi café» sin publicar nada.

Mientras la venta directa está inactiva (``config.mercado_activo``), el
caficultor puede describir un lote y ver qué le ofrecerían los compradores de
demostración, negociar y "cerrar" una venta de práctica. Usa las mismas reglas
de negocio del mercado real (``mercado.le_interesa``, ``precio_ofrecido``,
``respuesta_a_contraoferta``) para que lo que se ve en la simulación sea lo que
haría la herramienta al activarse.

Reglas:

* Solo participan los compradores de demostración (``mercado.COMPRADORES_DEMO``),
  nunca compradores reales de la base, y la pantalla lo dice.
* No escribe en las tablas ``mk_*`` ni en ``05_resultados/marketplace/``: el lote
  y la negociación viven solo en la sesión. La telemetría registra que se usó
  (tipo de café, cargas, número de ofertas), sin texto.
* Los totales son brutos: no descuentan transporte, trilla ni impuestos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cofitech import mercado
from cofitech.mercado import COMPRADORES_DEMO, Comprador, Lote, cop

AVISO = ("Simulación: los compradores son de demostración y sus ofertas las calcula la app con reglas fijas. "
         "No se publica ni se guarda tu lote.")
NOTA_TOTALES = "Totales brutos: no descuentan transporte, trilla ni impuestos."


@dataclass(frozen=True)
class OfertaSimulada:
    comprador: Comprador
    precio_cop_carga: int
    cantidad_cargas: float
    recoge_en_finca: bool
    pct_vs_fnc: Optional[float]

    @property
    def total_cop(self) -> int:
        return round(self.precio_cop_carga * self.cantidad_cargas)


@dataclass(frozen=True)
class Resultado:
    lote: Lote
    ofertas: list[OfertaSimulada]                       # de mayor a menor precio
    sin_oferta: list[tuple[Comprador, str]]             # comprador y por qué no ofertó

    @property
    def mejor(self) -> Optional[OfertaSimulada]:
        return self.ofertas[0] if self.ofertas else None

    @property
    def total_fnc(self) -> Optional[int]:
        ref = self.lote.precio_fnc_ref_cop_carga
        return round(ref * self.lote.cantidad_cargas) if ref else None

    @property
    def ganancia_vs_fnc(self) -> Optional[int]:
        """Cuánto más recibiría con la mejor oferta que vendiendo todo al precio FNC."""
        if self.mejor is None or self.total_fnc is None:
            return None
        return self.mejor.total_cop - self.total_fnc


@dataclass
class Negociacion:
    """Estado de la negociación de práctica con un comprador."""
    id_comprador: str
    vigente: int                                        # último precio del comprador
    historial: list[tuple[str, str]] = field(default_factory=list)   # (quien, texto)
    cerrada: bool = False


def _pct(precio: float, ref: Optional[float]) -> Optional[float]:
    return round(100 * (precio / ref - 1), 1) if ref else None


def motivo_sin_oferta(c: Comprador, lote: Lote) -> str:
    """En palabras del caficultor, por qué un comprador no le haría oferta."""
    if lote.tipo_cafe == "Cereza" and c.tipo != "Cooperativa":
        return "La cereza solo la compran las cooperativas o el beneficio de la zona."
    if c.puntaje_min is not None and lote.puntaje_sca is None:
        return f"Pide puntaje de catación de {c.puntaje_min} o más y tu lote no tiene puntaje."
    if c.puntaje_min is not None and lote.puntaje_sca is not None and lote.puntaje_sca < c.puntaje_min:
        return f"Pide {c.puntaje_min} puntos SCA o más; tu lote tiene {lote.puntaje_sca}."
    if lote.cantidad_cargas < c.cargas_min:
        return f"Compra lotes de {c.cargas_min:g} cargas o más."
    return "No busca este tipo de lote."


def simular(lote: Lote, compradores: tuple[Comprador, ...] = COMPRADORES_DEMO) -> Resultado:
    """Ofertas que harían los compradores de demostración por ``lote`` (no guarda nada)."""
    ref = lote.precio_fnc_ref_cop_carga
    ofertas: list[OfertaSimulada] = []
    sin_oferta: list[tuple[Comprador, str]] = []
    for c in compradores:
        if not c.es_demo:               # el simulador nunca muestra compradores reales
            continue
        precio = mercado.precio_ofrecido(c, lote) if mercado.le_interesa(c, lote) else None
        if precio is None:
            sin_oferta.append((c, motivo_sin_oferta(c, lote)))
            continue
        recoge = c.tipo == "Cooperativa" or lote.cantidad_cargas >= 10     # misma regla que publicar_lote
        ofertas.append(OfertaSimulada(c, precio, lote.cantidad_cargas, recoge, _pct(precio, ref)))
    ofertas.sort(key=lambda o: o.precio_cop_carga, reverse=True)
    return Resultado(lote, ofertas, sin_oferta)


def iniciar_negociacion(oferta: OfertaSimulada) -> Negociacion:
    texto = (f"Hola. Por su lote de {oferta.cantidad_cargas:g} cargas le ofrecemos {cop(oferta.precio_cop_carga)} "
             "por carga" + (" y lo recogemos en la finca." if oferta.recoge_en_finca else "."))
    return Negociacion(oferta.comprador.id, oferta.precio_cop_carga, [("ellos", texto)])


def contraofertar(neg: Negociacion, lote: Lote, pedido: int) -> str:
    """Aplica la contraoferta del caficultor. Devuelve ``"acepta"`` o ``"contraoferta"``."""
    comprador = next(c for c in COMPRADORES_DEMO if c.id == neg.id_comprador)
    pedido = mercado.redondear(pedido)
    neg.historial.append(("yo", f"¿Me lo pagan a {cop(pedido)} por carga?"))
    resultado, precio = mercado.respuesta_a_contraoferta(comprador, lote, neg.vigente, pedido)
    neg.vigente = precio
    if resultado == "acepta":
        neg.historial.append(("ellos", f"Trato hecho: {cop(precio)} por carga."))
    else:
        neg.historial.append(("ellos", f"No llegamos a tanto. Le podemos pagar {cop(precio)} por carga."))
    return resultado


def cerrar(neg: Negociacion, lote: Lote) -> dict[str, Optional[float]]:
    """Cierra la venta de práctica al precio vigente y resume lo que recibiría."""
    neg.cerrada = True
    total = round(neg.vigente * lote.cantidad_cargas)
    ref = lote.precio_fnc_ref_cop_carga
    total_fnc = round(ref * lote.cantidad_cargas) if ref else None
    neg.historial.append(("sistema", f"Venta simulada cerrada: {lote.cantidad_cargas:g} cargas a "
                                     f"{cop(neg.vigente)} = {cop(total)}."))
    return {"precio": neg.vigente, "total": total, "pct_vs_fnc": _pct(neg.vigente, ref),
            "diferencia_vs_fnc": total - total_fnc if total_fnc is not None else None}


def consejos(resultado: Resultado) -> list[str]:
    """Qué cambiar en el lote para recibir más o mejores ofertas."""
    lote = resultado.lote
    tips: list[str] = []
    if lote.puntaje_sca is None and lote.tipo_cafe != "Cereza":
        tips.append("Con una catación de 84 puntos o más te buscarían los tostadores, que pagan las primas más altas "
                    "(revisa «Calidad y primas (SCA)»).")
    if lote.tipo_cafe == "Cereza":
        tips.append("Vender pergamino seco abre la puerta a tostadores y exportadores.")
    if any("cargas o más" in motivo for _, motivo in resultado.sin_oferta):
        tips.append("Juntar cosecha con vecinos para llegar a 50 cargas interesa a los exportadores.")
    mejor = resultado.mejor
    if mejor and mejor.precio_cop_carga >= lote.precio_esperado_cop_carga:
        tips.append("La mejor oferta ya iguala lo que pides: podrías pedir un poco más y negociar.")
    return tips
