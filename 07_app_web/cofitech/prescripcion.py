"""Orientación de manejo de la roya según la incidencia medida en el lote.

Regla de producto (alineada con Cenicafé):

* La decisión se toma con la **incidencia** del lote (% de hojas con roya en
  un muestreo del lote), no con la confianza de una foto: una foto es una
  hoja, y quien fotografía elige las hojas enfermas.
* Variedad resistente (Castillo, Colombia, Cenicafé 1, Tabi): no se recomienda
  control químico; se vigila.
* Incidencia < 5 %: manejo **preventivo** con protector cúprico (oxicloruro de cobre).
* Incidencia ≥ 5 %: control con fungicida **sistémico** del grupo de los
  triazoles con registro ICA para roya del cafeto.

Este módulo NO contiene dosis, concentraciones ni días de carencia: dependen
del producto comercial y de su etiqueta registrada ante el ICA. Esas cifras
solo las da el asistente cuando las encuentra en un documento validado de
Cenicafé (ver ``06_agente_rag/rag_pipeline.py``). Una prueba automática
verifica que aquí no aparezca ninguna cifra de dosis ni de carencia.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

UMBRAL_INCIDENCIA_PCT: float = 5.0
FUENTE = "(Fuente: Manual de Caficultura / Boletines Técnicos Cenicafé)"

CARENCIA = ("**Periodo de carencia:** respete los días entre la última aplicación y la cosecha que indica "
            "la etiqueta del producto registrado ante el ICA. Si faltan menos días para recoger, no aplique.")
EPP = ("**Protección personal:** guantes, careta o gafas, mascarilla para plaguicidas, overol y botas; "
       "no coma ni fume mientras aplica y lávese al terminar.")
RESPALDO_DOSIS = ("No cuento con la dosificación exacta validada por Cenicafé para este caso específico; "
                  "consulte al extensionista del Comité de Cafeteros de su municipio.")


@dataclass(frozen=True)
class Recomendacion:
    nivel: str                       # "sin_dato" | "resistente" | "preventivo" | "sistemico"
    titulo: str
    acciones: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    fuente: str = FUENTE

    @property
    def es_quimica(self) -> bool:
        return self.nivel in ("preventivo", "sistemico")


def _pct(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def recomendacion_roya(incidencia_pct: Optional[float], variedad_resistente: Optional[bool] = None) -> Recomendacion:
    """Orientación para la roya del cafeto.

    Args:
        incidencia_pct: % de hojas con roya medido en el lote (0–100); ``None`` si no se ha medido.
        variedad_resistente: ``True`` (Castillo, Colombia, Cenicafé 1, Tabi), ``False``
            (Caturra, Típica, Borbón…) o ``None`` si no se conoce.

    Raises:
        ValueError: si la incidencia está fuera de 0–100.
    """
    if incidencia_pct is not None and not 0 <= incidencia_pct <= 100:
        raise ValueError(f"La incidencia debe estar entre 0 y 100 %, no {incidencia_pct}.")

    if variedad_resistente:
        return Recomendacion(
            nivel="resistente",
            titulo="Variedad resistente: no se recomienda control químico",
            acciones=[
                "Siga revisando el lote: la resistencia reduce mucho el riesgo, pero no lo elimina.",
                "Mantenga la fertilización según el análisis de suelos: una planta bien nutrida resiste mejor.",
                "Si ve muchas hojas con roya, mida la incidencia y consulte al extensionista: "
                "podría tratarse de una variante del hongo que afecta su variedad.",
            ],
        )

    if incidencia_pct is None:
        return Recomendacion(
            nivel="sin_dato",
            titulo="Mida la incidencia en el lote antes de decidir",
            acciones=[
                "La foto confirma que hay roya en esa hoja, pero no dice cuánta hay en el lote.",
                "Recorra el lote en zigzag, revise ramas del tercio medio de árboles escogidos al azar y cuente "
                "cuántas hojas tienen roya de cada 100 revisadas. El extensionista le indica cuántos árboles revisar.",
                f"Con ese porcentaje: por debajo de {UMBRAL_INCIDENCIA_PCT:.0f} % se hace manejo preventivo; "
                f"desde {UMBRAL_INCIDENCIA_PCT:.0f} % se considera un fungicida sistémico.",
            ],
        )

    advertencias = [CARENCIA, EPP,
                    "**Dosis:** la indica la etiqueta registrada ante el ICA o el extensionista. " + RESPALDO_DOSIS]
    if incidencia_pct < UMBRAL_INCIDENCIA_PCT:
        return Recomendacion(
            nivel="preventivo",
            titulo=f"Incidencia {_pct(incidencia_pct)} % (menor a {UMBRAL_INCIDENCIA_PCT:.0f} %): manejo preventivo",
            acciones=[
                "Protector cúprico (oxicloruro de cobre) para proteger el follaje nuevo, aplicado antes de "
                "que la enfermedad avance, de acuerdo con el calendario de floración.",
                "Regule la sombra y haga desyerbas y podas que mejoren la aireación del cafetal.",
                "Vuelva a medir la incidencia en 30 días.",
            ],
            advertencias=advertencias,
        )
    return Recomendacion(
        nivel="sistemico",
        titulo=f"Incidencia {_pct(incidencia_pct)} % (desde {UMBRAL_INCIDENCIA_PCT:.0f} %): control con fungicida sistémico",
        acciones=[
            "Fungicida sistémico del grupo de los triazoles con registro ICA para roya del cafeto.",
            "Alterne grupos químicos entre aplicaciones para evitar que el hongo se vuelva resistente.",
            "Vuelva a medir la incidencia después de la aplicación para confirmar que bajó.",
            "Si la variedad es susceptible, considere la renovación con una variedad resistente (Castillo, "
            "Cenicafé 1, Tabi) en el próximo ciclo.",
        ],
        advertencias=advertencias,
    )


def mostrar(recomendacion: Recomendacion) -> None:
    """Tarjeta de decisión para Streamlit (vista móvil del caficultor)."""
    import streamlit as st

    estilo = {"sistemico": st.error, "preventivo": st.warning, "sin_dato": st.info, "resistente": st.success}
    with st.container(border=True):
        estilo[recomendacion.nivel](f"**{recomendacion.titulo}**")
        for accion in recomendacion.acciones:
            st.markdown(f"- {accion}")
        for advertencia in recomendacion.advertencias:
            st.caption(advertencia)
        st.caption(recomendacion.fuente)
