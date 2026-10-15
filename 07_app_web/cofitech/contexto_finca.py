"""Estado compartido de CofiTech: una sola fuente de verdad por sesión.

Por qué existe
--------------
Streamlit borra de ``st.session_state`` las claves de los *widgets* cuando la
pantalla que los dibuja deja de mostrarse. Si cada pantalla guarda municipio,
altitud o área en sus propios sliders, el dato se pierde al navegar y hay que
volver a pedirlo: ese es el origen de la queja «las herramientas se ven
desconectadas». Aquí el contexto vive en UNA clave que no pertenece a ningún
widget y las pantallas lo leen y lo actualizan solo con las funciones de este
módulo.

Uso desde cualquier pantalla::

    from cofitech.contexto_finca import obtener_contexto, registrar_diagnostico

    ctx = obtener_contexto()
    altitud = ctx.finca.altitud_msnm                    # leer
    registrar_diagnostico("Roya", 0.87, "cnn_cafe_best.keras", huella=sha1)  # escribir

Qué viaja
---------
``rol`` · ``finca`` (municipio, altitud, área, variedad, floración) · ``zona``
(agrónomo, con su municipio en foco) · ``clima`` (ENSO + clima municipal) ·
``mercado`` (precio FNC) · ``diagnostico`` (última foto) · ``muestreo``
(incidencia y riesgo) · ``prediccion``.

El riesgo fitosanitario además se publica en
``st.session_state["riesgo_fitosanitario"]`` (``"Alto"`` / ``"Medio"`` /
``"Bajo"``) para las pantallas que solo necesitan ese dato.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import pandas as pd
import streamlit as st

from cofitech import repositorio
from cofitech.datos import catalogo_municipios  # noqa: F401  (se reexporta para las vistas)

PROYECTO: Path = Path(__file__).resolve().parents[2]
DIR_DATOS: Path = PROYECTO / "01_datos"

_CLAVE = "cofitech_ctx"   # clave de session_state que NO pertenece a ningún widget
_ESQUEMA = 3              # súbelo al cambiar los dataclasses: invalida contextos viejos

# Rangos físicos admitidos (regla de calidad de datos del proyecto).
RANGO_ALTITUD_MSNM: tuple[float, float] = (500.0, 3000.0)
RANGO_AREA_HA: tuple[float, float] = (0.1, 5000.0)

CLASE_ROYA = "Roya"
CLASE_SANO = "Sano"

# Etiquetas de la CNN -> (nombre que ve el caficultor, términos para buscar en el corpus).
NOMBRES_CLASE: dict[str, tuple[str, str]] = {
    "Roya": ("roya", "roya Hemileia vastatrix"),
    "Gotera": ("gotera u ojo de gallo", "gotera ojo de gallo Mycena citricolor"),
    "Cercospora": ("mancha de hierro (Cercospora)", "mancha de hierro Cercospora coffeicola"),
    "Phoma": ("Phoma (muerte descendente)", "Phoma costarricensis muerte descendente"),
    "Miner": ("minador de la hoja", "minador de la hoja Leucoptera coffeella"),
    "SpiderMite": ("araña roja", "araña roja ácaro Tetranychus"),
    "Sano": ("hoja sana", ""),
}

# Riesgo fitosanitario de la sesión. Regla del producto: roya detectada con
# probabilidad >= 80 % en alguna hoja del muestreo => riesgo "Alto".
CLAVE_RIESGO = "riesgo_fitosanitario"
UMBRAL_ROYA_ALTO: float = 0.80

# Variedad -> ¿resistente a roya? (None = desconocido). Fuente: listado del
# formulario de caracterización y de la base de conocimiento del agente RAG.
VARIEDADES: dict[str, Optional[bool]] = {
    "Castillo": True,
    "Colombia": True,
    "Cenicafé 1": True,
    "Tabi": True,
    "Caturra": False,
    "Borbón / Típica": False,
    "Geisha": False,
    "No sabe / Mezcla": None,
}

_FASES_ENSO = {"Nino": "El Niño", "Nina": "La Niña", "Neutro": "Neutro"}
_MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


class Rol(str, Enum):
    """Perfil operativo. Hereda de ``str`` para compararse con texto plano."""

    CAFICULTOR = "caficultor"
    AGRONOMO = "agronomo"


# ─────────────────────────── Modelo de datos ────────────────────────────────
@dataclass
class Finca:
    """Datos que el caficultor entrega UNA vez y que usan todas las pantallas."""

    municipio: str = ""
    departamento: str = ""
    codigo_dane: Optional[str] = None            # None si el municipio no está en el catálogo
    altitud_msnm: Optional[float] = None
    area_ha: Optional[float] = None
    variedad: Optional[str] = None
    fecha_floracion_principal: Optional[date] = None   # la pide la prescripción de roya

    @property
    def completa(self) -> bool:
        return bool(self.municipio and self.altitud_msnm and self.area_ha)

    @property
    def resistente_roya(self) -> Optional[bool]:
        return VARIEDADES.get(self.variedad or "")

    def validar(self) -> list[str]:
        """Devuelve los errores de rango físico (lista vacía = válida)."""
        errores: list[str] = []
        if not self.municipio.strip():
            errores.append("Falta el municipio.")
        if self.altitud_msnm is None or not RANGO_ALTITUD_MSNM[0] <= self.altitud_msnm <= RANGO_ALTITUD_MSNM[1]:
            errores.append(f"La altitud debe estar entre {RANGO_ALTITUD_MSNM[0]:.0f} y {RANGO_ALTITUD_MSNM[1]:.0f} msnm.")
        if self.area_ha is None or not RANGO_AREA_HA[0] <= self.area_ha <= RANGO_AREA_HA[1]:
            errores.append(f"El área debe estar entre {RANGO_AREA_HA[0]} y {RANGO_AREA_HA[1]:.0f} ha.")
        return errores


@dataclass
class Zona:
    """Ámbito de trabajo del agrónomo / cooperativa."""

    departamentos: list[str] = field(default_factory=list)
    municipio_foco: Optional[str] = None     # código DANE elegido en la barra global (None = toda la zona)


@dataclass
class Clima:
    """Clima que se muestra y que alimenta modelos y RAG. Siempre con su fecha."""

    oni: Optional[float] = None
    fase_enso: Optional[str] = None              # "Nino" | "Nina" | "Neutro" (como en enso_validado.csv)
    fecha_enso: Optional[date] = None
    temp_media_12m_c: Optional[float] = None     # media de los últimos 12 meses completos
    precip_12m_mm: Optional[float] = None        # acumulado de los últimos 12 meses completos
    fecha_clima: Optional[date] = None           # último mes incluido

    @property
    def fase_legible(self) -> str:
        return _FASES_ENSO.get(self.fase_enso or "", "sin dato")


@dataclass
class Mercado:
    precio_fnc_cop_carga: Optional[float] = None  # COP por carga de 125 kg de pergamino seco
    fecha: Optional[date] = None


@dataclass
class Diagnostico:
    """Resultado de UNA foto clasificada por la CNN."""

    id: str
    clase: str
    confianza: float          # 0–1
    modelo: str
    fecha: datetime
    es_demo: bool = False


@dataclass
class Muestreo:
    """Conteo de hojas revisadas en la sesión.

    Una foto es una hoja, no una incidencia. El criterio de Cenicafé se aplica
    sobre el % de hojas con roya de un muestreo del lote, así que la
    prescripción debe leer ``incidencia_pct`` y nunca la confianza de una foto.
    """

    hojas_evaluadas: int = 0
    hojas_con_roya: int = 0
    hojas_otra_enfermedad: int = 0
    confianza_max_roya: float = 0.0     # mayor probabilidad de roya vista en el muestreo
    incidencia_lote_pct: Optional[float] = None   # % de hojas con roya que el caficultor midió en el lote

    @property
    def incidencia_pct(self) -> Optional[float]:
        if self.hojas_evaluadas == 0:
            return None
        return 100.0 * self.hojas_con_roya / self.hojas_evaluadas

    @property
    def riesgo(self) -> Optional[str]:
        """Riesgo del muestreo: manda la peor hoja, no la última.

        Si el riesgo siguiera a la última foto, revisar una hoja sana después
        de una con roya borraría la alerta.
        """
        if self.hojas_evaluadas == 0:
            return None
        if self.confianza_max_roya >= UMBRAL_ROYA_ALTO:
            return "Alto"
        if self.hojas_con_roya or self.hojas_otra_enfermedad:
            return "Medio"
        return "Bajo"


@dataclass
class Prediccion:
    rendimiento_ton_ha: float
    produccion_ton: float
    ingreso_bruto_cop: float
    modelo: str
    fecha: datetime
    es_heuristica: bool = False   # True si la cifra no viene de datos observados ni de un modelo validado


@dataclass
class ContextoFinca:
    """Todo lo que debe sobrevivir al cambio de pantalla."""

    esquema: int = _ESQUEMA
    rol: Optional[Rol] = None
    finca: Finca = field(default_factory=Finca)
    zona: Zona = field(default_factory=Zona)
    clima: Clima = field(default_factory=Clima)
    mercado: Mercado = field(default_factory=Mercado)
    diagnostico: Optional[Diagnostico] = None
    muestreo: Muestreo = field(default_factory=Muestreo)
    prediccion: Optional[Prediccion] = None
    huellas_registradas: list[str] = field(default_factory=list)

    @property
    def codigo_activo(self) -> Optional[str]:
        """Código DANE del municipio sobre el que trabaja la sesión.

        Caficultor: el de su finca. Agrónomo: el municipio en foco de la barra
        global. ``None`` si no hay municipio concreto.
        """
        if self.rol == Rol.AGRONOMO:
            return self.zona.municipio_foco
        return self.finca.codigo_dane

    @property
    def listo(self) -> bool:
        """¿Hay rol y datos mínimos para entrar a la app?"""
        if self.rol == Rol.CAFICULTOR:
            return self.finca.completa
        if self.rol == Rol.AGRONOMO:
            return bool(self.zona.departamentos)
        return False


# ───────────────────────────── API pública ──────────────────────────────────
def obtener_contexto() -> ContextoFinca:
    """Devuelve el contexto de la sesión; lo crea la primera vez."""
    ctx = st.session_state.get(_CLAVE)
    if ctx is None or getattr(ctx, "esquema", None) != _ESQUEMA:
        ctx = ContextoFinca()
        _refrescar_entorno(ctx)
        st.session_state[_CLAVE] = ctx
    return ctx


def reiniciar_contexto() -> None:
    """Borra todo (cerrar sesión)."""
    st.session_state.pop(_CLAVE, None)
    st.session_state.pop(CLAVE_RIESGO, None)


def definir_rol(rol: Optional[Rol]) -> None:
    """Fija el rol. ``None`` vuelve a la pantalla de ingreso sin borrar la finca."""
    obtener_contexto().rol = rol


def actualizar_finca(**campos: Any) -> list[str]:
    """Actualiza la finca con validación de rangos.

    Args:
        **campos: Atributos de ``Finca`` (``municipio``, ``altitud_msnm``, ...).

    Returns:
        Lista de errores. Si no está vacía, el contexto NO se modifica.
    """
    ctx = obtener_contexto()
    candidata = Finca(**{**asdict(ctx.finca), **campos})
    errores = candidata.validar()
    if errores:
        return errores
    ctx.finca = candidata
    _refrescar_entorno(ctx)
    return []


def actualizar_zona(departamentos: list[str]) -> None:
    ctx = obtener_contexto()
    ctx.zona = Zona(departamentos=sorted(departamentos))
    _refrescar_entorno(ctx)


def actualizar_foco(codigo_dane: Optional[str]) -> None:
    """Fija el municipio en foco del agrónomo (``None`` = toda la zona)."""
    ctx = obtener_contexto()
    ctx.zona.municipio_foco = codigo_dane
    _refrescar_entorno(ctx)


def municipio_activo(ctx: Optional[ContextoFinca] = None) -> Optional[dict[str, Any]]:
    """Fila del catálogo del municipio activo, con coordenadas si existen.

    Returns:
        Diccionario con ``codigo_dane``, ``municipio``, ``departamento``,
        ``lat``, ``lon`` y ``altitud_msnm`` (``None`` donde no hay dato), o
        ``None`` si la sesión no tiene un municipio concreto.
    """
    ctx = ctx or obtener_contexto()
    codigo = ctx.codigo_activo
    if codigo:
        catalogo = catalogo_municipios()
        fila = catalogo[catalogo["codigo_dane"] == codigo]
        if not fila.empty:
            return {k: (None if pd.isna(v) else v) for k, v in fila.iloc[0].to_dict().items()}
    if ctx.rol != Rol.AGRONOMO and ctx.finca.municipio:
        return {"codigo_dane": None, "municipio": ctx.finca.municipio, "departamento": ctx.finca.departamento,
                "lat": None, "lon": None, "altitud_msnm": ctx.finca.altitud_msnm}
    return None


def riesgo_fitosanitario() -> Optional[str]:
    """Riesgo vigente: ``"Alto"``, ``"Medio"``, ``"Bajo"`` o ``None`` (sin fotos)."""
    return st.session_state.get(CLAVE_RIESGO)


def registrar_diagnostico(
    clase: str,
    confianza: float,
    modelo: str,
    huella: Optional[str] = None,
    es_demo: bool = False,
) -> Diagnostico:
    """Guarda el diagnóstico de una foto en el contexto y en el repositorio.

    Args:
        clase: Etiqueta que devolvió la CNN (``"Roya"``, ``"Sano"``, ...).
        confianza: Probabilidad de la clase, entre 0 y 1.
        modelo: Nombre del artefacto que predijo.
        huella: Hash de la imagen. Streamlit re-ejecuta la pantalla en cada
            interacción; con la huella la misma foto se registra una sola vez.
        es_demo: Marca los registros simulados para excluirlos de los KPIs.

    Returns:
        El diagnóstico vigente (el nuevo, o el anterior si la foto se repite).
    """
    if not 0.0 <= confianza <= 1.0:
        raise ValueError(f"confianza fuera de [0, 1]: {confianza}")
    ctx = obtener_contexto()
    if huella and huella in ctx.huellas_registradas and ctx.diagnostico is not None:
        return ctx.diagnostico

    diag = Diagnostico(
        id=uuid4().hex, clase=clase, confianza=float(confianza),
        modelo=modelo, fecha=datetime.now(), es_demo=es_demo,
    )
    ctx.diagnostico = diag
    ctx.muestreo.hojas_evaluadas += 1
    if clase == CLASE_ROYA:
        ctx.muestreo.hojas_con_roya += 1
        ctx.muestreo.confianza_max_roya = max(ctx.muestreo.confianza_max_roya, float(confianza))
    elif clase != CLASE_SANO:
        ctx.muestreo.hojas_otra_enfermedad += 1
    if huella:
        ctx.huellas_registradas.append(huella)
    st.session_state[CLAVE_RIESGO] = ctx.muestreo.riesgo

    repositorio.guardar_diagnostico({
        "id": diag.id, "fecha": diag.fecha.isoformat(timespec="seconds"),
        "departamento": ctx.finca.departamento or None,
        "municipio": ctx.finca.municipio or None,
        "codigo_dane": ctx.finca.codigo_dane,
        "altitud_msnm": ctx.finca.altitud_msnm,
        "clase": clase, "confianza": round(float(confianza), 4), "modelo": modelo,
        "rol_origen": ctx.rol.value if ctx.rol else None, "es_demo": es_demo,
        "id_sesion": repositorio.id_sesion(),
    })
    return diag


def registrar_incidencia_lote(pct: Optional[float]) -> None:
    """Guarda la incidencia de roya medida en el lote (0–100) o la borra con ``None``.

    Es la cifra con la que se decide el manejo (``cofitech.prescripcion``); la
    leen la pantalla de diagnóstico y el contexto que recibe el asistente.
    """
    if pct is not None and not 0 <= pct <= 100:
        raise ValueError(f"La incidencia debe estar entre 0 y 100 %, no {pct}.")
    obtener_contexto().muestreo.incidencia_lote_pct = pct


def reiniciar_muestreo() -> None:
    """Empieza un muestreo nuevo (otro lote u otra fecha)."""
    ctx = obtener_contexto()
    ctx.muestreo = Muestreo()
    ctx.huellas_registradas = []
    ctx.diagnostico = None
    st.session_state.pop(CLAVE_RIESGO, None)


def registrar_prediccion(
    rendimiento_ton_ha: float, modelo: str, es_heuristica: bool = False,
) -> Optional[Prediccion]:
    """Guarda la predicción de rendimiento y deriva producción e ingreso.

    Producción = rendimiento × área de la finca. Ingreso bruto = producción en
    kg × precio FNC por kg. Devuelve ``None`` si faltan área o precio.
    """
    ctx = obtener_contexto()
    if not ctx.finca.area_ha or not ctx.mercado.precio_fnc_cop_carga:
        return None
    produccion = rendimiento_ton_ha * ctx.finca.area_ha
    ingreso = produccion * 1000 * ctx.mercado.precio_fnc_cop_carga / 125
    ctx.prediccion = Prediccion(
        rendimiento_ton_ha=rendimiento_ton_ha, produccion_ton=produccion,
        ingreso_bruto_cop=ingreso, modelo=modelo,
        fecha=datetime.now(), es_heuristica=es_heuristica,
    )
    return ctx.prediccion


def prefijo_rag(ctx: Optional[ContextoFinca] = None, hoy: Optional[date] = None) -> str:
    """Contexto del usuario que se antepone a la pregunta enviada al agente RAG.

    Empieza con el prefijo acordado para el caficultor::

        El usuario tiene un cultivo en Pitalito, Huila a 1.500 msnm. El modelo de
        visión diagnosticó roya con 87% de certeza. Estado fenológico actual
        estimado según el mes: octubre — pico de cosecha principal ...

    y sigue con los datos que cambian la recomendación (variedad, ENSO, hojas
    revisadas). Cada frase aparece solo si el dato existe: nunca rellena.
    """
    from cofitech.calendario import estado_fenologico
    from cofitech.datos import miles

    ctx = ctx or obtener_contexto()
    frases: list[str] = []
    extras: list[str] = []

    if ctx.rol == Rol.AGRONOMO:
        extras.append("Perfil: agrónomo o técnico de cooperativa; responde con detalle técnico.")
        if ctx.zona.departamentos:
            extras.append("Zona de trabajo: " + ", ".join(ctx.zona.departamentos) + ".")
        activo = municipio_activo(ctx)
        if activo:
            frases.append(f"El usuario consulta por el municipio de {activo['municipio']}, {activo['departamento']}.")
    else:
        f = ctx.finca
        if f.municipio:
            lugar = f"{f.municipio}, {f.departamento}".strip(", ")
            frases.append(f"El usuario tiene un cultivo en {lugar}"
                          + (f" a {miles(f.altitud_msnm)} msnm." if f.altitud_msnm else "."))
        if ctx.diagnostico and ctx.diagnostico.clase != CLASE_SANO:
            d = ctx.diagnostico
            nombre = NOMBRES_CLASE.get(d.clase, (d.clase, ""))[0]
            frases.append(f"El modelo de visión diagnosticó {nombre} con {d.confianza * 100:.0f}% de certeza.")
        elif ctx.diagnostico:
            frases.append(f"El modelo de visión clasificó la hoja como sana "
                          f"({ctx.diagnostico.confianza * 100:.0f}% de certeza).")
        if f.variedad:
            resistencia = {True: "resistente a la roya", False: "susceptible a la roya"}.get(f.resistente_roya)
            extras.append(f"Variedad: {f.variedad}" + (f" ({resistencia})." if resistencia else "."))
        if f.area_ha:
            extras.append(f"Área en café: {miles(f.area_ha, 1)} ha.")
        extras.append("Perfil: caficultor; responde en lenguaje sencillo y con pasos concretos.")

    floracion = ctx.finca.fecha_floracion_principal if ctx.rol != Rol.AGRONOMO else None
    frases.append(f"Estado fenológico actual estimado según el mes: {estado_fenologico(hoy, floracion)}.")

    c = ctx.clima
    if c.oni is not None:
        extras.append(f"ENSO: {c.fase_legible} (ONI {c.oni:+.2f}, dato de {mes_anio(c.fecha_enso)}).")
    m = ctx.muestreo
    if m.incidencia_lote_pct is not None:
        extras.append(f"Incidencia de roya medida en el lote por el usuario: {m.incidencia_lote_pct:.1f} %.")
    if ctx.rol != Rol.AGRONOMO and m.hojas_evaluadas:
        extras.append(f"Hojas fotografiadas en la sesión: {m.hojas_evaluadas}, con roya {m.hojas_con_roya}. "
                      "Esto no es la incidencia del lote.")

    texto = " ".join(frases)
    if extras:
        texto += "\nDatos adicionales: " + " ".join(extras)
    return texto


def mes_anio(fecha: Optional[date]) -> str:
    """``date(2025, 12, 1)`` -> ``'dic 2025'``. Sin dato -> ``'sin fecha'``."""
    if fecha is None:
        return "sin fecha"
    return f"{_MESES[fecha.month - 1]} {fecha.year}"


# ──────────────────── Carga del entorno (clima y mercado) ───────────────────
@st.cache_data(show_spinner=False)
def _ultimo_enso() -> dict[str, Any]:
    ruta = DIR_DATOS / "procesados" / "enso_validado.csv"
    if not ruta.exists():
        return {}
    df = pd.read_csv(ruta, parse_dates=["fecha"]).dropna(subset=["oni"]).sort_values("fecha")
    if df.empty:
        return {}
    ultimo = df.iloc[-1]
    return {"oni": float(ultimo["oni"]), "fase_enso": str(ultimo["fase_enso"]),
            "fecha_enso": ultimo["fecha"].date()}


@st.cache_data(show_spinner=False)
def _ultimo_precio_fnc() -> dict[str, Any]:
    ruta = DIR_DATOS / "procesados" / "precios_validado.csv"
    if not ruta.exists():
        return {}
    df = pd.read_csv(ruta, parse_dates=["fecha"]).dropna(subset=["precio_fnc_cop_kg"]).sort_values("fecha")
    if df.empty:
        return {}
    ultimo = df.iloc[-1]
    return {"precio_fnc_cop_carga": float(ultimo["precio_fnc_cop_kg"]) * 125,
            "fecha": ultimo["fecha"].date()}


@st.cache_data(show_spinner=False)
def _clima_municipal(codigo_dane: str) -> dict[str, Any]:
    """Media de temperatura y lluvia acumulada de los últimos 12 meses completos.

    El último mes del maestro se descarta: la descarga lo deja a medio llenar
    (enero de 2026 trae 1–23 mm en todos los municipios) y sesgaría el acumulado.
    """
    ruta = DIR_DATOS / "procesados" / "master_cafe_municipal_mensual.csv"
    if not ruta.exists():
        return {}
    df = pd.read_csv(
        ruta, usecols=["codigo_dane", "fecha", "temp_media_c", "precipitacion_mm"],
        dtype={"codigo_dane": str}, parse_dates=["fecha"],
    )
    df["codigo_dane"] = df["codigo_dane"].str.zfill(5)
    df = df[df["fecha"] < df["fecha"].max()]
    serie = df[df["codigo_dane"] == codigo_dane].sort_values("fecha").tail(12)
    if len(serie) < 12:
        return {}
    return {"temp_media_12m_c": float(serie["temp_media_c"].mean()),
            "precip_12m_mm": float(serie["precipitacion_mm"].sum()),
            "fecha_clima": serie["fecha"].iloc[-1].date()}


def _refrescar_entorno(ctx: ContextoFinca) -> None:
    """Rellena ``clima`` y ``mercado`` desde los datos validados del proyecto."""
    clima = dict(_ultimo_enso())
    if ctx.codigo_activo:
        clima.update(_clima_municipal(ctx.codigo_activo))
    ctx.clima = Clima(**clima)
    ctx.mercado = Mercado(**_ultimo_precio_fnc())
