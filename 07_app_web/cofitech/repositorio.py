"""Repositorio de diagnósticos de campo: el puente entre los dos roles.

Cada diagnóstico se guarda en dos lugares:

* **Supabase** (``cafe.registro_diagnosticos``), si hay credenciales: es lo
  que hace que el agrónomo vea en su mapa los reportes de todos los
  caficultores, desde cualquier equipo. Cliente en ``03_scripts/bd/db_client.py``.
* **Archivo local** ``05_resultados/logs/diagnosticos_campo.jsonl``: respaldo
  cuando no hay nube o la conexión falla. La app nunca se detiene por la base.

Las lecturas usan Supabase si responde y, si no, el archivo local.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import streamlit as st

PROYECTO: Path = Path(__file__).resolve().parents[2]
RUTA_DIAGNOSTICOS: Path = PROYECTO / "05_resultados" / "logs" / "diagnosticos_campo.jsonl"
RUTA_FEEDBACK: Path = PROYECTO / "05_resultados" / "logs" / "diagnosticos_feedback.jsonl"

sys.path.insert(0, str(PROYECTO / "03_scripts" / "bd"))
import db_client  # noqa: E402

log = logging.getLogger("cofitech.repositorio")

COLUMNAS: list[str] = [
    "id", "fecha", "departamento", "municipio", "codigo_dane", "altitud_msnm",
    "clase", "confianza", "modelo", "rol_origen", "es_demo", "feedback_usuario",
]
COLUMNAS_RESUMEN: list[str] = ["codigo_dane", "departamento", "municipio", "fotos", "fotos_roya",
                               "pct_fotos_roya", "ultimo_reporte"]
_CLAVE_SESION = "cofitech_id_sesion"
_SEGUNDOS_CACHE = 30          # el mapa de calor y la barra global se refrescan cada 30 s


def id_sesion() -> str:
    """Identificador aleatorio de la sesión del navegador (no identifica a la persona)."""
    if _CLAVE_SESION not in st.session_state:
        st.session_state[_CLAVE_SESION] = uuid4().hex[:12]
    return st.session_state[_CLAVE_SESION]


# ─────────────────────────────── Escritura ──────────────────────────────────
def guardar_diagnostico(registro: dict[str, Any]) -> bool:
    """Guarda un diagnóstico en Supabase (si hay) y en el archivo local.

    Args:
        registro: Diccionario con las llaves de ``COLUMNAS``.

    Returns:
        ``True`` si quedó en la nube; ``False`` si solo quedó en el archivo local.
    """
    registro = {**registro, "id_sesion": registro.get("id_sesion") or id_sesion()}
    _guardar_local(registro)
    en_nube = _en_nube(db_client.insertar_diagnostico, registro)
    if en_nube:
        refrescar()
    return en_nube


def registrar_feedback(id_diagnostico: str, coincide: bool) -> bool:
    """Guarda si el caficultor confirmó (👍) o rechazó (👎) el diagnóstico (Supabase y archivo local)."""
    _anexar(RUTA_FEEDBACK, {"id": id_diagnostico, "feedback_usuario": bool(coincide)})
    actualizado = _en_nube(db_client.registrar_feedback_diagnostico, id_diagnostico, coincide)
    if actualizado:
        refrescar()
    return bool(actualizado)


def _guardar_local(registro: dict[str, Any]) -> bool:
    return _anexar(RUTA_DIAGNOSTICOS, registro)


def _anexar(ruta: Path, registro: dict[str, Any]) -> bool:
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
        return True
    except OSError:
        return False


def _leer_jsonl(ruta: Path) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    if not ruta.exists():
        return filas
    with ruta.open(encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea:
                continue
            try:
                filas.append(json.loads(linea))
            except json.JSONDecodeError:
                continue  # una línea dañada no debe tumbar el tablero
    return filas


def _en_nube(funcion, *args) -> Any:
    """Ejecuta una operación en Supabase sin dejar que un fallo detenga la app."""
    if not db_client.configurado():
        return False
    try:
        resultado = funcion(*args)
        return True if resultado is None else resultado
    except db_client.BaseDatosNoDisponible as error:
        log.warning("Supabase no disponible: %s", error)
    except Exception as error:      # p. ej. una restricción CHECK que rechaza el registro
        log.error("Supabase rechazó la operación %s: %s", funcion.__name__, error)
    return False


# ──────────────────────────────── Lectura ───────────────────────────────────
def leer_diagnosticos() -> pd.DataFrame:
    """Todos los diagnósticos: de Supabase si responde, si no del archivo local."""
    if db_client.configurado():
        try:
            return _leer_nube()
        except db_client.BaseDatosNoDisponible:
            pass
    return _leer_local()


def resumen_roya(dias: int = 30, incluir_demo: bool = False) -> tuple[pd.DataFrame, str]:
    """Reportes por municipio de los últimos ``dias`` para el mapa de calor.

    Returns:
        ``(tabla, fuente)``: la tabla tiene ``codigo_dane``, ``municipio``,
        ``departamento``, ``fotos``, ``fotos_roya``, ``pct_fotos_roya`` y
        ``ultimo_reporte``; ``fuente`` es ``"Supabase"`` o ``"archivo local"``.
    """
    if db_client.configurado():
        try:
            return _resumen_nube(dias, incluir_demo)[COLUMNAS_RESUMEN], "Supabase"
        except db_client.BaseDatosNoDisponible:
            pass
    df = _leer_local()
    if not df.empty:
        df = df[df["fecha"] >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=dias)]
        if not incluir_demo:
            df = df[~df["es_demo"].fillna(False).astype(bool)]
    return alertas_por_municipio(df), "archivo local"


def refrescar() -> None:
    """Olvida las lecturas en caché para traer lo último de Supabase."""
    _leer_nube.clear()
    _resumen_nube.clear()


@st.cache_data(ttl=_SEGUNDOS_CACHE, show_spinner=False)
def _leer_nube() -> pd.DataFrame:
    return db_client.leer_diagnosticos()


@st.cache_data(ttl=_SEGUNDOS_CACHE, show_spinner=False)
def _resumen_nube(dias: int, incluir_demo: bool) -> pd.DataFrame:
    return db_client.resumen_roya_por_municipio(dias, incluir_demo)


def _leer_local() -> pd.DataFrame:
    df = pd.DataFrame(_leer_jsonl(RUTA_DIAGNOSTICOS), columns=COLUMNAS)
    votos = {f["id"]: f["feedback_usuario"] for f in _leer_jsonl(RUTA_FEEDBACK) if "id" in f}
    df["feedback_usuario"] = df["id"].map(votos)     # el último voto manda
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", utc=True)
    return df


def alertas_por_municipio(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega los diagnósticos por municipio.

    ``pct_fotos_roya`` es el porcentaje de FOTOS clasificadas como roya, no la
    incidencia del cultivo: quien toma la foto elige hojas sospechosas, así
    que el valor sobreestima. Sirve para priorizar visitas, no para prescribir.
    Igual que en Supabase, no cuenta como roya lo que el caficultor rechazó (👎).
    """
    columnas = COLUMNAS_RESUMEN
    if df.empty:
        return pd.DataFrame(columns=columnas)
    rechazada = df.get("feedback_usuario", pd.Series(None, index=df.index, dtype=object)).eq(False)
    df = df.assign(es_roya=((df["clase"] == "Roya") & ~rechazada).astype(int))
    resumen = df.groupby(["codigo_dane", "departamento", "municipio"], dropna=False).agg(
        fotos=("id", "count"),
        fotos_roya=("es_roya", "sum"),
        ultimo_reporte=("fecha", "max"),
    ).reset_index()
    resumen["pct_fotos_roya"] = (100 * resumen["fotos_roya"] / resumen["fotos"]).round(1)
    return resumen[columnas].sort_values(["fotos_roya", "fotos"], ascending=False, ignore_index=True)
