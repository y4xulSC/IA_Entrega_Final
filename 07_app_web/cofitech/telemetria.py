"""Telemetría de uso y captura de KPIs de producto (KR2, KR3 y KPIs de la entrega de Data Thinking).

Cada evento se guarda en dos lugares:

* ``st.session_state["log_eventos"]``: la lista de la sesión, para mostrarla
  en pantalla en el momento.
* ``05_resultados/logs/eventos_uso.jsonl``: un archivo que acumula todas las
  sesiones. Sin él los KPIs no se pueden medir, porque ``session_state``
  desaparece al recargar la página. La ruta se cambia con la variable de
  entorno ``COFITECH_RUTA_EVENTOS`` (las pruebas la usan).
* ``cafe.registro_eventos_uso`` en Supabase, si hay credenciales: así los KPIs
  sobreviven a un despliegue en la nube, donde el archivo local se pierde.

Privacidad: no se guarda el texto de las preguntas ni nada que identifique a
la persona. ``id_sesion`` es un identificador aleatorio por sesión del
navegador, no un usuario: KR1 (registros) y la retención semanal necesitan
inicio de sesión y no se pueden medir con esto.

Uso::

    from cofitech.telemetria import cronometro, registrar_evento_uso

    with cronometro() as t:
        resultado = modelo.predict(x)
    registrar_evento_uso("Visión", "diagnostico_ejecutado",
                         {"modelo": "cnn_cafe_best.keras", **t})
"""
from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

import pandas as pd
import streamlit as st

from cofitech import repositorio
from cofitech.repositorio import db_client
from cofitech.contexto_finca import Rol, municipio_activo, obtener_contexto

PROYECTO: Path = Path(__file__).resolve().parents[2]
RUTA_EVENTOS: Path = Path(os.environ.get(
    "COFITECH_RUTA_EVENTOS", PROYECTO / "05_resultados" / "logs" / "eventos_uso.jsonl"))

CLAVE_LOG = "log_eventos"
_CLAVE_VOTOS = "cofitech_votos"
_CLAVE_UNICOS = "cofitech_eventos_unicos"

HERRAMIENTAS: tuple[str, ...] = ("Visión", "Predicción Rendimiento", "Predicción Precios", "RAG")
ETIQUETA_ROL: dict[Rol, str] = {Rol.CAFICULTOR: "Caficultor", Rol.AGRONOMO: "Agrónomo/Cooperativa"}
GRACIAS = "Gracias por ayudarnos a calibrar los modelos para el campo colombiano"

_candado = threading.Lock()   # varias sesiones de Streamlit escriben el mismo archivo


# ─────────────────────────────── Registro ───────────────────────────────────
def registrar_evento_uso(herramienta: str, accion: str, metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Registra un evento de uso de una de las tres herramientas núcleo.

    Args:
        herramienta: Una de ``HERRAMIENTAS``.
        accion: Verbo del evento, p. ej. ``"diagnostico_ejecutado"``,
            ``"calculo_rendimiento"``, ``"pregunta_enviada"``.
        metadata: Datos de contexto (modelo, tiempo de respuesta...). Si no
            trae ``municipio``, se toma el de la sesión.

    Returns:
        El evento registrado.

    Raises:
        ValueError: Si ``herramienta`` no es una de las cuatro esperadas (un
            nombre mal escrito partiría los KPIs en dos grupos).
    """
    if herramienta not in HERRAMIENTAS:
        raise ValueError(f"Herramienta desconocida: {herramienta!r}. Usa una de {HERRAMIENTAS}.")
    ctx = obtener_contexto()
    datos = dict(metadata or {})
    for clave, valor in _municipio_de_sesion(ctx).items():
        datos.setdefault(clave, valor)

    evento = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "id_sesion": repositorio.id_sesion(),
        "usuario_rol": ETIQUETA_ROL.get(ctx.rol, "Sin rol"),
        "herramienta": herramienta,
        "accion": accion,
        "metadata": datos,
    }
    st.session_state.setdefault(CLAVE_LOG, []).append(evento)
    _persistir(evento)
    return evento


def registrar_una_vez(clave: str, herramienta: str, accion: str,
                      metadata: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    """Como ``registrar_evento_uso``, pero una sola vez por ``clave`` y sesión.

    Para cálculos que se ejecutan solos al abrir una pantalla: Streamlit
    re-ejecuta la página en cada clic y sin esto cada clic contaría como uso.
    """
    vistos: set[str] = st.session_state.setdefault(_CLAVE_UNICOS, set())
    if clave in vistos:
        return None
    vistos.add(clave)
    return registrar_evento_uso(herramienta, accion, metadata)


@contextmanager
def cronometro() -> Iterator[dict[str, float]]:
    """Mide el bloque y deja ``{"tiempo_respuesta_s": ...}`` en el diccionario que entrega."""
    medida: dict[str, float] = {}
    inicio = time.perf_counter()
    try:
        yield medida
    finally:
        medida["tiempo_respuesta_s"] = round(time.perf_counter() - inicio, 3)


def eventos_de_sesion() -> list[dict[str, Any]]:
    return list(st.session_state.get(CLAVE_LOG, []))


def leer_eventos() -> pd.DataFrame:
    """Todos los eventos guardados (todas las sesiones), con ``metadata`` expandida en columnas ``md_*``.

    Lee de Supabase si responde; si no, del archivo local.
    """
    filas: list[dict[str, Any]] = []
    if db_client.configurado():
        try:
            filas = db_client.leer_eventos()
        except db_client.BaseDatosNoDisponible:
            filas = []
    if not filas and RUTA_EVENTOS.exists():
        with RUTA_EVENTOS.open(encoding="utf-8") as archivo:
            for linea in archivo:
                try:
                    filas.append(json.loads(linea))
                except json.JSONDecodeError:
                    continue
    if not filas:
        filas = eventos_de_sesion()      # disco no escribible: al menos la sesión actual
    if not filas:
        return pd.DataFrame(columns=["timestamp", "id_sesion", "usuario_rol", "herramienta", "accion"])
    df = pd.json_normalize(filas, sep="_")
    df.columns = [c.replace("metadata_", "md_", 1) for c in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    return df


# ─────────────────────────────── KPIs ───────────────────────────────────────
def calcular_kpis(df: pd.DataFrame) -> dict[str, Any]:
    """KPIs de la entrega de Data Thinking que la telemetría puede medir.

    * Nivel de confianza aceptada: % de diagnósticos que el usuario validó con 👍.
    * Tasa de resolución del RAG: % de respuestas marcadas como útiles.
    * KR3: sesiones que usaron Visión, Predicción (rendimiento o precios) y RAG.
    * Proxy de KR2: % de sesiones que dejaron al menos una valoración. KR2 pide
      encuestas de usabilidad; los votos son una señal parcial.
    """
    def _tasa(serie: pd.Series) -> Optional[float]:
        serie = serie.dropna().astype(bool)
        return float(serie.mean()) if len(serie) else None

    if df.empty:
        return {"sesiones": 0, "eventos": 0, "confianza_aceptada": None, "validaciones": 0, "resolucion_rag": None,
                "valoraciones_rag": 0, "sesiones_3_herramientas": 0, "sesiones_con_valoracion": None}

    validaciones = df.loc[df["accion"] == "validacion_diagnostico", "md_confianza_aceptada"] \
        if "md_confianza_aceptada" in df else pd.Series(dtype=bool)
    utiles = df.loc[df["accion"] == "feedback_respuesta", "md_util"] if "md_util" in df else pd.Series(dtype=bool)

    herramientas = df.groupby("id_sesion")["herramienta"].agg(set)
    tres = herramientas.map(lambda h: "Visión" in h and "RAG" in h
                            and bool(h & {"Predicción Rendimiento", "Predicción Precios"}))
    votaron = df[df["accion"].isin(["validacion_diagnostico", "feedback_respuesta"])]["id_sesion"].nunique()

    return {
        "sesiones": int(df["id_sesion"].nunique()),
        "eventos": int(len(df)),
        "confianza_aceptada": _tasa(validaciones),
        "validaciones": int(validaciones.notna().sum()),
        "resolucion_rag": _tasa(utiles),
        "valoraciones_rag": int(utiles.notna().sum()),
        "sesiones_3_herramientas": int(tres.sum()),
        "sesiones_con_valoracion": votaron / df["id_sesion"].nunique(),
    }


COLUMNAS_KPI_ROL: list[str] = [
    "rol", "sesiones", "eventos", "valoraciones_rag", "satisfaccion_rag", "validaciones_vision",
    "confianza_aceptada", "confianza_media_modelo", "sesiones_3_herramientas", "ultimo_evento",
]


def kpis_por_rol(df: pd.DataFrame) -> pd.DataFrame:
    """Los KPIs de ``calcular_kpis`` por rol y en total, con las columnas de ``cafe.vw_kpis_consolidados``.

    Respaldo local de la vista de Supabase: si la base no responde, la tabla
    del administrador se calcula igual desde el archivo de eventos.
    """
    if df.empty:
        return pd.DataFrame(columns=COLUMNAS_KPI_ROL)

    def _fila(rol: str, parte: pd.DataFrame) -> dict[str, Any]:
        k = calcular_kpis(parte)
        diagnosticos = parte.loc[parte["accion"] == "diagnostico_ejecutado", "md_confianza"] \
            if "md_confianza" in parte else pd.Series(dtype=float)
        confianza = pd.to_numeric(diagnosticos, errors="coerce").dropna()
        return {"rol": rol, "sesiones": k["sesiones"], "eventos": k["eventos"],
                "valoraciones_rag": k["valoraciones_rag"], "satisfaccion_rag": k["resolucion_rag"],
                "validaciones_vision": k["validaciones"], "confianza_aceptada": k["confianza_aceptada"],
                "confianza_media_modelo": float(confianza.mean()) if len(confianza) else None,
                "sesiones_3_herramientas": k["sesiones_3_herramientas"],
                "ultimo_evento": parte["timestamp"].max()}

    filas = [_fila(str(rol), parte) for rol, parte in df.groupby(df["usuario_rol"].fillna("Sin rol"))]
    filas.append(_fila("Total", df))
    return pd.DataFrame(filas, columns=COLUMNAS_KPI_ROL)


# ───────────────────────────── Componente UI ────────────────────────────────
def barra_valoracion(
    clave: str,
    pregunta: str,
    herramienta: str,
    accion: str,
    campo: str,
    metadata: Optional[dict[str, Any]] = None,
    etiqueta_si: str = "👍 Sí",
    etiqueta_no: str = "👎 No",
    al_votar: Optional[Callable[[bool], Any]] = None,
) -> Optional[bool]:
    """Pregunta de sí/no que registra el voto una sola vez.

    Tras votar, los botones quedan desactivados y aparece el agradecimiento.
    El voto se registra en el ``on_click`` (antes de la re-ejecución), así un
    doble clic no alcanza a contar dos veces.

    Args:
        clave: Identificador único de lo que se valora (id del diagnóstico o de la respuesta).
        pregunta: Texto que ve el usuario.
        herramienta, accion: Clasificación del evento de telemetría.
        campo: Nombre del dato en ``metadata`` (``"confianza_aceptada"``, ``"util"``).
        metadata: Datos adicionales del evento.
        al_votar: Función opcional que recibe el voto (p. ej. guardarlo en Supabase).

    Returns:
        El voto (``True``/``False``) o ``None`` si aún no se ha votado.
    """
    votos: dict[str, bool] = st.session_state.setdefault(_CLAVE_VOTOS, {})

    def _votar(valor: bool) -> None:
        if clave in votos:
            return
        votos[clave] = valor
        registrar_evento_uso(herramienta, accion, {**(metadata or {}), campo: valor})
        if al_votar is not None:
            al_votar(valor)

    votado = clave in votos
    with st.container():
        st.caption(pregunta)
        col_si, col_no = st.columns(2)
        col_si.button(etiqueta_si, key=f"voto_si_{clave}", on_click=_votar, args=(True,), disabled=votado)
        col_no.button(etiqueta_no, key=f"voto_no_{clave}", on_click=_votar, args=(False,), disabled=votado)
        if votado:
            st.caption(f"{GRACIAS} · Tu respuesta: {'sí' if votos[clave] else 'no'}")
    return votos.get(clave)


# ─────────────────────────────── Internos ───────────────────────────────────
def _municipio_de_sesion(ctx) -> dict[str, Optional[str]]:
    """Nombre y código DANE del municipio de la finca o del foco del agrónomo (``None`` si no hay)."""
    activo = municipio_activo(ctx)
    if not activo:
        return {"municipio": None, "codigo_dane": None}
    return {"municipio": activo.get("municipio"), "codigo_dane": activo.get("codigo_dane")}


def _persistir(evento: dict[str, Any]) -> bool:
    """Archivo local siempre; Supabase si hay credenciales. Devuelve si quedó en la nube."""
    linea = json.dumps(evento, ensure_ascii=False, default=str) + "\n"
    try:
        with _candado:
            RUTA_EVENTOS.parent.mkdir(parents=True, exist_ok=True)
            with RUTA_EVENTOS.open("a", encoding="utf-8") as archivo:
                archivo.write(linea)
    except OSError:
        pass                # sin disco escribible el evento sigue en la sesión
    return bool(repositorio._en_nube(db_client.insertar_evento, evento))
