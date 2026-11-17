"""Donación voluntaria de fotos y revisión experta de los diagnósticos de la CNN.

Por defecto CofiTech **no guarda la foto**: la procesa en memoria y la descarta.
Este módulo solo actúa cuando el usuario marca, para esa foto, la casilla de
donación (desmarcada por defecto). Entonces:

* La foto se **reduce** (lado mayor de ``LADO_MAX_PX``) y se vuelve a codificar
  como JPEG **sin metadatos EXIF** (GPS, cámara, fecha).
* Se guarda en ``cafe.registro_fotos_donadas`` (Supabase) con el diagnóstico,
  las 7 probabilidades, el municipio y la versión del aviso de privacidad que
  estaba vigente. Si la base no responde, en ``05_resultados/fotos_donadas/``.
* Vence a los ``DIAS_RETENCION`` días y se borra sola.
* El usuario recibe un **código** (p. ej. ``K7Q2-M9XD``) para pedir el borrado
  antes de tiempo (derecho de supresión, Ley 1581).

Los administradores revisan las fotos en «Revisión de diagnósticos»
(``vistas/revision_fotos.py``) y anotan la clase real.
"""
from __future__ import annotations

import io
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import streamlit as st
from PIL import Image, ImageOps

from cofitech import privacidad, repositorio
from cofitech.repositorio import db_client

log = logging.getLogger("cofitech.fotos")

LADO_MAX_PX = 1024
CALIDAD_JPEG = 85
DIAS_RETENCION = 180
UMBRAL_CERTEZA = 0.80           # por debajo, la pantalla muestra la segunda opción del modelo
MAX_FOTOS = 2000                 # tope para no llenar los 500 MB del plan gratis de Supabase
DIR_LOCAL: Path = repositorio.PROYECTO / "05_resultados" / "fotos_donadas"
CLASES_REVISION: tuple[str, ...] = ("Cercospora", "Gotera", "Miner", "Phoma", "Roya", "Sano", "SpiderMite",
                                    "Indeterminada")
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"     # sin 0/O ni 1/I para dictarlo por teléfono


@dataclass(frozen=True)
class FotoPreparada:
    jpeg: bytes
    ancho_px: int
    alto_px: int


def preparar(contenido: bytes) -> FotoPreparada:
    """Endereza, reduce y vuelve a codificar la foto como JPEG sin EXIF."""
    with Image.open(io.BytesIO(contenido)) as original:
        imagen = ImageOps.exif_transpose(original)          # respeta la orientación del celular
        imagen = imagen.convert("RGB")                      # quita transparencia y perfiles raros
    imagen.thumbnail((LADO_MAX_PX, LADO_MAX_PX))
    limpia = Image.new("RGB", imagen.size)                  # imagen nueva: no hereda ningún metadato
    limpia.paste(imagen)
    salida = io.BytesIO()
    limpia.save(salida, format="JPEG", quality=CALIDAD_JPEG, optimize=True)
    return FotoPreparada(salida.getvalue(), limpia.width, limpia.height)


def nuevo_codigo() -> str:
    letras = "".join(secrets.choice(_ALFABETO) for _ in range(8))
    return f"{letras[:4]}-{letras[4:]}"


def donar(contenido: bytes, *, id_diagnostico: str, clase: str, confianza: float,
          probabilidades: Optional[dict[str, float]], modelo: str, municipio: Optional[str],
          departamento: Optional[str], codigo_dane: Optional[str], es_demo: bool = False) -> tuple[str, bool]:
    """Guarda una foto donada.

    Returns:
        ``(codigo, en_nube)``: el código para pedir el borrado y si quedó en Supabase.

    Raises:
        RuntimeError: si ya se alcanzó ``MAX_FOTOS``.
    """
    foto = preparar(contenido)
    ahora = datetime.now(timezone.utc)
    registro: dict[str, Any] = {
        "codigo": nuevo_codigo(), "id_diagnostico": id_diagnostico, "id_sesion": repositorio.id_sesion(),
        "imagen": foto.jpeg, "mime": "image/jpeg", "ancho_px": foto.ancho_px, "alto_px": foto.alto_px,
        "bytes": len(foto.jpeg), "clase_modelo": clase, "confianza_modelo": round(float(confianza), 4),
        "probabilidades": {c: round(float(p), 4) for c, p in (probabilidades or {}).items()} or None,
        "modelo": modelo, "municipio": municipio or None, "departamento": departamento or None,
        "codigo_dane": codigo_dane, "version_aviso": privacidad.VERSION_AVISO,
        "borrar_despues": ahora + timedelta(days=DIAS_RETENCION), "es_demo": es_demo,
    }
    if db_client.configurado():
        try:
            limpiar_vencidas()
            if db_client.contar_fotos_donadas() >= MAX_FOTOS:
                raise RuntimeError("Por ahora no recibimos más fotos: ya tenemos las que podemos revisar. ¡Gracias!")
            db_client.insertar_foto_donada(registro)
            return registro["codigo"], True
        except db_client.BaseDatosNoDisponible as error:
            log.warning("Supabase no disponible, la foto queda en el respaldo local: %s", error)
    _guardar_local(registro)
    return registro["codigo"], False


# ─────────────────────────── Respaldo local ─────────────────────────────────
def _indice_local() -> Path:
    return DIR_LOCAL / "indice.jsonl"


def _guardar_local(registro: dict[str, Any]) -> None:
    DIR_LOCAL.mkdir(parents=True, exist_ok=True)
    (DIR_LOCAL / f"{registro['codigo']}.jpg").write_bytes(registro["imagen"])
    meta = {k: v for k, v in registro.items() if k != "imagen"}
    meta.update(id=registro["codigo"], fecha=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                borrar_despues=registro["borrar_despues"].isoformat(timespec="seconds"))
    with _indice_local().open("a", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False, default=str) + "\n")


def _leer_local() -> list[dict[str, Any]]:
    """Última versión de cada foto local (las revisiones y borrados se anexan al índice)."""
    fotos: dict[str, dict[str, Any]] = {}
    if _indice_local().exists():
        for linea in _indice_local().read_text(encoding="utf-8").splitlines():
            try:
                fila = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if fila.get("borrada"):
                fotos.pop(fila["id"], None)
            else:
                fotos[fila["id"]] = {**fotos.get(fila["id"], {}), **fila}
    return [f for f in fotos.values() if (DIR_LOCAL / f"{f['id']}.jpg").exists()]


def _anexar_local(fila: dict[str, Any]) -> None:
    DIR_LOCAL.mkdir(parents=True, exist_ok=True)
    with _indice_local().open("a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False, default=str) + "\n")


# ─────────────────────────── Revisión (admin) ───────────────────────────────
def listar(pendientes: Optional[bool] = None) -> tuple[list[dict[str, Any]], str]:
    """Fotos donadas sin la imagen. Returns ``(fotos, fuente)``."""
    if db_client.configurado():
        try:
            return db_client.listar_fotos_donadas(pendientes), "Supabase"
        except db_client.BaseDatosNoDisponible:
            pass
    fotos = sorted(_leer_local(), key=lambda f: f.get("fecha", ""), reverse=True)
    if pendientes is not None:
        fotos = [f for f in fotos if (f.get("clase_revisada") is None) == pendientes]
    return fotos, "archivo local"


def imagen(foto: dict[str, Any], fuente: str) -> Optional[bytes]:
    if fuente == "Supabase":
        return db_client.leer_imagen_foto(foto["id"])
    ruta = DIR_LOCAL / f"{foto['id']}.jpg"
    return ruta.read_bytes() if ruta.exists() else None


def revisar(foto: dict[str, Any], fuente: str, clase_revisada: str, notas: str = "") -> bool:
    if clase_revisada not in CLASES_REVISION:
        raise ValueError(f"Clase no válida: {clase_revisada}")
    if fuente == "Supabase":
        return db_client.revisar_foto(foto["id"], clase_revisada, notas)
    _anexar_local({"id": foto["id"], "clase_revisada": clase_revisada, "notas_revision": notas[:500] or None,
                   "revisada_en": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return True


def borrar(id_o_codigo: str) -> bool:
    """Borra por id o por código (en Supabase y en el respaldo local)."""
    codigo = id_o_codigo.strip().upper()
    borrada = False
    if db_client.configurado():
        try:
            borrada = db_client.borrar_foto(id_o_codigo)
        except db_client.BaseDatosNoDisponible:
            pass
    ruta = DIR_LOCAL / f"{codigo}.jpg"
    if ruta.exists():
        ruta.unlink()
        _anexar_local({"id": codigo, "borrada": True})
        borrada = True
    return borrada


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def limpiar_vencidas() -> int:
    """Borra las fotos que pasaron su plazo (como mucho cada 6 h por proceso)."""
    borradas = 0
    if db_client.configurado():
        try:
            borradas += db_client.borrar_fotos_vencidas()
        except db_client.BaseDatosNoDisponible:
            pass
    ahora = datetime.now(timezone.utc)
    for f in _leer_local():
        try:
            vence = datetime.fromisoformat(str(f["borrar_despues"]))
        except (KeyError, ValueError):
            continue
        if vence.tzinfo is None:
            vence = vence.replace(tzinfo=timezone.utc)
        if vence < ahora and borrar(f["id"]):
            borradas += 1
    return borradas


def segunda_opcion(probabilidades: Optional[dict[str, float]]) -> Optional[tuple[str, float, float]]:
    """``(clase, probabilidad, margen)`` de la segunda clase más probable, o ``None``."""
    if not probabilidades or len(probabilidades) < 2:
        return None
    (c1, p1), (c2, p2) = sorted(probabilidades.items(), key=lambda kv: kv[1], reverse=True)[:2]
    return c2, float(p2), float(p1) - float(p2)
