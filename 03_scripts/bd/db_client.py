"""Cliente de base de datos en la nube (Supabase / PostgreSQL) para CofiTech.

Lo usan la app de Streamlit (diagnósticos, valoraciones y telemetría) y
cualquier script que necesite leer o escribir las tablas transaccionales del
esquema ``cafe`` creadas con ``03_supabase_schema.sql``.

Credenciales (la primera que exista):

1. ``.streamlit/secrets.toml``::

       [connections.postgresql]
       url = "postgresql://postgres.<ref>:<clave>@aws-<n>-<región>.pooler.supabase.com:5432/postgres"

   o con campos separados (``host``, ``port``, ``database``, ``username``,
   ``password``), el mismo formato de ``st.connection("postgresql", type="sql")``.
2. Variable de entorno o ``.env``: ``SUPABASE_DB_URL=postgresql://...``

Sin credenciales, ``disponible()`` devuelve ``False`` y la app sigue con sus
archivos locales: la nube es opcional. Las variables ``PG_*`` del ``.env``
(PostgreSQL local de Docker) no se usan aquí a propósito.

Supabase: usa la cadena del **pooler en modo sesión** (puerto 5432, usuario
``postgres.<ref>``). La conexión directa ``db.<ref>.supabase.co`` es solo IPv6
en el plan gratuito y no funciona desde redes IPv4 ni desde Streamlit Cloud.
Se exige SSL (``sslmode=require``) salvo en ``localhost``.

Prueba rápida::

    python 03_scripts/bd/db_client.py
"""
from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional
from urllib.parse import quote, urlsplit

PROYECTO: Path = Path(__file__).resolve().parents[2]
ESQUEMA = "cafe"
RUTA_SECRETS_APP: Path = PROYECTO / "07_app_web" / ".streamlit" / "secrets.toml"

_TIEMPO_CONEXION_S = 5          # sin red, no congelar la app más de 5 s
_PAUSA_TRAS_FALLO_S = 60        # tras un fallo, no reintentar en cada clic
_MAX_CONEXIONES = 3             # el pooler gratuito de Supabase admite pocas

_candado = threading.Lock()
_pool = None
_ultimo_fallo: float = 0.0
_ultimo_error: Optional[str] = None
_dotenv_leido = False


class BaseDatosNoDisponible(RuntimeError):
    """No hay credenciales, o la base no respondió."""


# ──────────────────────────────── Configuración ─────────────────────────────
def _dsn() -> Optional[str]:
    """Cadena de conexión desde ``st.secrets`` o ``SUPABASE_DB_URL``; ``None`` si no hay."""
    secreto = _desde_secrets()
    if secreto:
        return secreto
    _cargar_dotenv(PROYECTO / ".env")
    return os.environ.get("SUPABASE_DB_URL") or None


def _desde_secrets() -> Optional[str]:
    conf = None
    try:
        import streamlit as st

        conf = st.secrets.get("connections", {}).get("postgresql")
    except Exception:          # sin streamlit, sin secrets.toml o fuera de una app
        conf = None
    if not conf:
        # Streamlit busca secrets.toml junto a donde se lanzó; si se lanzó desde la
        # raíz del proyecto (o se usa este archivo por consola), se lee el de la app.
        conf = _leer_toml(RUTA_SECRETS_APP).get("connections", {}).get("postgresql")
    if not conf:
        return None
    if conf.get("url"):
        return str(conf["url"])
    try:
        usuario = quote(str(conf["username"]), safe="")
        clave = quote(str(conf["password"]), safe="")
        return (f"postgresql://{usuario}:{clave}@{conf['host']}:{conf.get('port', 5432)}/"
                f"{conf.get('database', 'postgres')}")
    except KeyError:
        return None


def _leer_toml(ruta: Path) -> dict[str, Any]:
    if not ruta.exists():
        return {}
    try:
        import tomllib

        with ruta.open("rb") as archivo:
            return tomllib.load(archivo)
    except Exception:          # TOML mal escrito: se trata como si no existiera
        return {}


def _cargar_dotenv(ruta: Path) -> None:
    """Lee SUPABASE_DB_URL del .env (una vez) sin pisar variables ya definidas."""
    global _dotenv_leido
    if _dotenv_leido or not ruta.exists():
        return
    _dotenv_leido = True
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        clave, sep, valor = linea.strip().partition("=")
        if sep and clave.strip() == "SUPABASE_DB_URL":
            os.environ.setdefault("SUPABASE_DB_URL", valor.strip().strip('"').strip("'"))


def _parametros(dsn: str) -> dict[str, Any]:
    host = urlsplit(dsn).hostname or ""
    local = host in ("localhost", "127.0.0.1", "::1") or host.startswith("/")
    params: dict[str, Any] = {
        "dsn": dsn,
        "connect_timeout": _TIEMPO_CONEXION_S,
        "application_name": "cofitech-streamlit",
        # Mantiene viva la conexión a través del pooler y detecta caídas.
        "keepalives": 1, "keepalives_idle": 30, "keepalives_interval": 10, "keepalives_count": 3,
    }
    if "sslmode=" not in dsn and not local:
        params["sslmode"] = "require"
    return params


def configurado() -> bool:
    """¿Hay credenciales? No intenta conectarse."""
    return _dsn() is not None


def disponible() -> bool:
    """¿Se puede usar la base ahora? Conecta si hace falta (máximo 5 s)."""
    try:
        with _conexion():
            return True
    except BaseDatosNoDisponible:
        return False


def estado() -> str:
    """Texto corto para mostrar en pantalla."""
    if not configurado():
        return "sin configurar"
    if _pool is not None:
        return "conectada"
    return f"no disponible ({_ultimo_error})" if _ultimo_error else "configurada"


# ─────────────────────────────── Conexiones ─────────────────────────────────
def _obtener_pool():
    global _pool, _ultimo_fallo, _ultimo_error
    if _pool is not None:
        return _pool
    with _candado:
        if _pool is not None:
            return _pool
        dsn = _dsn()
        if dsn is None:
            raise BaseDatosNoDisponible("sin credenciales (secrets.toml o SUPABASE_DB_URL)")
        if time.monotonic() - _ultimo_fallo < _PAUSA_TRAS_FALLO_S:
            raise BaseDatosNoDisponible(_ultimo_error or "falló hace poco")
        try:
            from psycopg2.pool import ThreadedConnectionPool

            _pool = ThreadedConnectionPool(1, _MAX_CONEXIONES, **_parametros(dsn))
            _ultimo_error = None
        except ImportError as error:
            raise BaseDatosNoDisponible("falta psycopg2: pip install psycopg2-binary") from error
        except Exception as error:
            _ultimo_fallo, _ultimo_error = time.monotonic(), _resumir(error)
            raise BaseDatosNoDisponible(_ultimo_error) from error
    return _pool


@contextmanager
def _conexion() -> Iterator[Any]:
    """Presta una conexión del pool; confirma al salir o revierte si hubo error."""
    global _pool, _ultimo_fallo, _ultimo_error
    pool = _obtener_pool()              # falla primero si no hay credenciales o psycopg2
    import psycopg2
    import psycopg2.pool

    try:
        conn = pool.getconn()
    except psycopg2.pool.PoolError as error:      # todas ocupadas
        raise BaseDatosNoDisponible("sin conexiones libres") from error
    roto = False
    try:
        yield conn
        conn.commit()
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as error:
        roto = True
        _ultimo_fallo, _ultimo_error = time.monotonic(), _resumir(error)
        raise BaseDatosNoDisponible(_ultimo_error) from error
    except Exception:
        if not conn.closed:
            conn.rollback()
        raise
    finally:
        pool.putconn(conn, close=roto or bool(conn.closed))
        if roto:                                   # la red cayó: rehacer el pool en el próximo uso
            with _candado:
                if _pool is pool:
                    _pool = None
                    pool.closeall()


def _resumir(error: Exception) -> str:
    return str(error).strip().splitlines()[0][:160] if str(error).strip() else type(error).__name__


# ─────────────────────────────── Escritura ──────────────────────────────────
def insertar_diagnostico(registro: dict[str, Any]) -> None:
    """Guarda un diagnóstico por foto en ``cafe.registro_diagnosticos``.

    Args:
        registro: Llaves ``id`` (uuid, hex de 32), ``fecha`` (ISO), ``municipio``,
            ``codigo_dane``, ``departamento``, ``altitud_msnm``, ``clase``
            (enfermedad), ``confianza`` (0–1), ``modelo``, ``rol_origen``,
            ``id_sesion``, ``es_demo``. Las que falten quedan en NULL.

    Raises:
        BaseDatosNoDisponible: Sin credenciales o sin conexión.
    """
    sql = f"""
        INSERT INTO {ESQUEMA}.registro_diagnosticos
            (id, fecha, municipio, codigo_dane, departamento, altitud_msnm,
             enfermedad_detectada, confianza, modelo, rol_origen, id_sesion, es_demo)
        VALUES (%(id)s, COALESCE(%(fecha)s::timestamptz, NOW()), %(municipio)s, %(codigo_dane)s,
                %(departamento)s, %(altitud_msnm)s, %(clase)s, %(confianza)s, %(modelo)s,
                %(rol_origen)s, %(id_sesion)s, %(es_demo)s)
        ON CONFLICT (id) DO NOTHING
    """
    valores = {k: registro.get(k) for k in ("id", "fecha", "municipio", "codigo_dane", "departamento",
                                            "altitud_msnm", "clase", "confianza", "modelo",
                                            "rol_origen", "id_sesion")}
    valores["es_demo"] = bool(registro.get("es_demo", False))
    with _conexion() as conn, conn.cursor() as cur:
        cur.execute(sql, valores)


def registrar_feedback_diagnostico(id_diagnostico: str, coincide: bool) -> bool:
    """Guarda la respuesta a «¿El diagnóstico coincide con lo que ves?».

    Returns:
        ``True`` si el diagnóstico existía y se actualizó.
    """
    sql = f"""
        UPDATE {ESQUEMA}.registro_diagnosticos
           SET feedback_usuario = %s, fecha_feedback = NOW()
         WHERE id = %s
    """
    with _conexion() as conn, conn.cursor() as cur:
        cur.execute(sql, (bool(coincide), id_diagnostico))
        return cur.rowcount == 1


def insertar_evento(evento: dict[str, Any]) -> None:
    """Guarda un evento de telemetría (incluye la calificación del asistente RAG)."""
    sql = f"""
        INSERT INTO {ESQUEMA}.registro_eventos_uso
            (fecha, id_sesion, usuario_rol, herramienta, accion, metadata)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
    """
    with _conexion() as conn, conn.cursor() as cur:
        cur.execute(sql, (evento.get("timestamp") or datetime.now().astimezone().isoformat(),
                          evento.get("id_sesion"), evento.get("usuario_rol"), evento["herramienta"],
                          evento["accion"], json.dumps(evento.get("metadata") or {}, ensure_ascii=False,
                                                       default=str)))


# ──────────────────────────────── Lectura ───────────────────────────────────
def resumen_roya_por_municipio(dias: int = 30, incluir_demo: bool = False):
    """Diagnósticos de los últimos ``dias`` agregados por municipio (para el mapa de calor).

    Las fotos que el caficultor marcó como «no coincide» no cuentan como roya:
    el usuario corrigió al modelo.

    Returns:
        ``pandas.DataFrame`` con ``codigo_dane``, ``municipio``, ``departamento``,
        ``fotos``, ``fotos_roya``, ``pct_fotos_roya``, ``ultimo_reporte``.
    """
    import pandas as pd

    sql = f"""
        SELECT codigo_dane,
               MAX(municipio)    AS municipio,
               MAX(departamento) AS departamento,
               COUNT(*)          AS fotos,
               COUNT(*) FILTER (WHERE enfermedad_detectada = 'Roya'
                                  AND feedback_usuario IS DISTINCT FROM false) AS fotos_roya,
               MAX(fecha)        AS ultimo_reporte
          FROM {ESQUEMA}.registro_diagnosticos
         WHERE fecha >= NOW() - make_interval(days => %s)
           AND (%s OR NOT es_demo)
         GROUP BY codigo_dane
    """
    with _conexion() as conn, conn.cursor() as cur:
        cur.execute(sql, (int(dias), bool(incluir_demo)))
        columnas = [c.name for c in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=columnas)
    if df.empty:
        return df.assign(pct_fotos_roya=pd.Series(dtype=float))
    df[["fotos", "fotos_roya"]] = df[["fotos", "fotos_roya"]].astype(int)
    df["pct_fotos_roya"] = (100 * df["fotos_roya"] / df["fotos"]).round(1)
    df["ultimo_reporte"] = pd.to_datetime(df["ultimo_reporte"], utc=True)
    return df.sort_values(["fotos_roya", "fotos"], ascending=False, ignore_index=True)


def leer_diagnosticos(limite: int = 5000):
    """Diagnósticos más recientes, con los nombres de columna que usa la app."""
    import pandas as pd

    sql = f"""
        SELECT id::text AS id, fecha, departamento, municipio, codigo_dane, altitud_msnm,
               enfermedad_detectada AS clase, confianza::float AS confianza, modelo, rol_origen,
               es_demo, feedback_usuario
          FROM {ESQUEMA}.registro_diagnosticos
         ORDER BY fecha DESC
         LIMIT %s
    """
    with _conexion() as conn, conn.cursor() as cur:
        cur.execute(sql, (int(limite),))
        df = pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])
    df["fecha"] = pd.to_datetime(df["fecha"], utc=True)
    return df


def kpis_consolidados():
    """KPIs por rol y total desde ``cafe.vw_kpis_consolidados`` (porcentajes entre 0 y 1).

    Columnas: rol, sesiones, eventos, valoraciones_rag, satisfaccion_rag,
    validaciones_vision, confianza_aceptada, confianza_media_modelo,
    sesiones_3_herramientas, ultimo_evento.
    """
    import pandas as pd

    sql = f"""
        SELECT rol, sesiones, eventos, valoraciones_rag, satisfaccion_rag::float,
               validaciones_vision, confianza_aceptada::float, confianza_media_modelo::float,
               sesiones_3_herramientas, ultimo_evento
          FROM {ESQUEMA}.vw_kpis_consolidados
         ORDER BY (rol = 'Total'), rol
    """
    with _conexion() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])


def leer_eventos(limite: int = 20000) -> list[dict[str, Any]]:
    """Eventos de telemetría en el mismo formato que los guarda la app."""
    sql = f"""
        SELECT fecha, id_sesion, usuario_rol, herramienta, accion, metadata
          FROM {ESQUEMA}.registro_eventos_uso
         ORDER BY fecha DESC
         LIMIT %s
    """
    with _conexion() as conn, conn.cursor() as cur:
        cur.execute(sql, (int(limite),))
        return [{"timestamp": f.isoformat(), "id_sesion": s, "usuario_rol": r,
                 "herramienta": h, "accion": a, "metadata": m}
                for f, s, r, h, a, m in cur.fetchall()]


def probar_conexion() -> str:
    """Versión del servidor y conteo de filas; lanza ``BaseDatosNoDisponible`` si falla."""
    with _conexion() as conn, conn.cursor() as cur:
        cur.execute("SHOW server_version")
        version = cur.fetchone()[0]
        cur.execute(f"SELECT (SELECT count(*) FROM {ESQUEMA}.registro_diagnosticos),"
                    f"       (SELECT count(*) FROM {ESQUEMA}.registro_eventos_uso)")
        diagnosticos, eventos = cur.fetchone()
    return f"PostgreSQL {version} · {diagnosticos} diagnósticos · {eventos} eventos"


if __name__ == "__main__":
    if not configurado():
        raise SystemExit("Sin credenciales: define SUPABASE_DB_URL en .env o "
                         "[connections.postgresql] en 07_app_web/.streamlit/secrets.toml")
    try:
        print("OK ·", probar_conexion())
    except BaseDatosNoDisponible as error:
        raise SystemExit(f"No se pudo conectar: {error}")
