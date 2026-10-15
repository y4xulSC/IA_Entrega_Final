"""Proyección de rendimiento: línea base real, impacto de la roya y simulador.

Tres piezas, de la más sólida a la más débil:

1. ``linea_base``: último rendimiento que EVA reporta para el municipio. Es la
   cifra principal de la pantalla. En un corte temporal (entrenar hasta 2015,
   evaluar 2016–2018) ninguno de los modelos probados con EVA superó a esta referencia.
2. ``impacto_roya``: si la sesión tiene riesgo fitosanitario «Alto», descuenta
   del rendimiento el rango de pérdida documentado por Cenicafé y lo valora en
   pesos. Es un escenario «si no se controla», no un pronóstico.
3. ``simular_escenario``: el ``.pkl`` de NB09. Se entrenó con datos SIMULADOS
   (120 municipios ficticios generados con una fórmula), así que solo sirve
   para explorar escenarios y siempre se muestra rotulado como tal.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from cofitech import datos

RUTA_MODELO_SIMULADO: Path = datos.PROYECTO / "04_modelos_entrenados" / "ml_municipal_rendimiento.pkl"

# Pérdida de producción por roya sin control. Cenicafé no publica una curva
# incidencia -> pérdida, así que se usa el rango de sus experimentos y NO se
# gradúa por la confianza de la foto ni por la incidencia de la sesión.
PERDIDA_ROYA_SIN_CONTROL: tuple[float, float] = (0.23, 0.30)
FUENTE_PERDIDA_ROYA = (
    "Cenicafé, Boletín Técnico 36 (2011): pérdidas de hasta 23 % de la producción acumulada "
    "de cuatro cosechas y de 28 % a 30 % en experimentos más recientes."
)

KG_POR_CARGA = 125  # carga de café pergamino seco
ANIOS_VIGENCIA = 3   # antigüedad máxima del dato municipal frente al último año de EVA


# ───────────────────────────── Línea base EVA ───────────────────────────────
@dataclass(frozen=True)
class LineaBase:
    rendimiento_ton_ha: float
    anio: int
    nivel: str              # "municipio" | "departamento" | "nacional"
    etiqueta: str           # p. ej. "Pitalito, Huila"
    historial: pd.DataFrame  # columnas anio, rendimiento_ton_ha (últimos años)
    area_cosechada_ha: Optional[float]   # área cosechada del último año (None a nivel nacional)
    fuente: str


def linea_base(codigo_dane: Optional[str], departamento: Optional[str] = None) -> Optional[LineaBase]:
    """Último rendimiento reportado por EVA, del nivel más específico disponible.

    Busca primero el municipio; si EVA no lo reporta (o su dato está fuera del
    rango físico) usa el rendimiento ponderado del departamento, y en último
    caso el nacional. El nivel usado queda en ``LineaBase.nivel`` para que la
    pantalla lo diga.

    Args:
        codigo_dane: Código DANE de 5 dígitos, o ``None`` si no se conoce.
        departamento: Nombre del departamento (con o sin tildes).

    Returns:
        La línea base, o ``None`` si no hay datos EVA cargados.
    """
    eva = datos.produccion_municipal()
    if eva.empty:
        return None
    validos = eva[eva["en_rango"]]

    if codigo_dane:
        mun = validos[validos["codigo_dane"] == codigo_dane]
        # Un municipio que dejó de reportar hace años no describe la finca de hoy.
        if not mun.empty and mun["anio"].iloc[-1] >= eva["anio"].max() - ANIOS_VIGENCIA:
            ultimo = mun.iloc[-1]
            return LineaBase(
                rendimiento_ton_ha=float(ultimo["rendimiento_ton_ha"]), anio=int(ultimo["anio"]),
                nivel="municipio", etiqueta=f"{ultimo['municipio']}, {ultimo['departamento']}",
                historial=mun[["anio", "rendimiento_ton_ha"]].tail(8).reset_index(drop=True),
                area_cosechada_ha=float(ultimo["area_cosechada_ha"]), fuente=str(ultimo["fuente"]),
            )

    clave = datos.normalizar(departamento) if departamento else None
    if not clave and codigo_dane:
        clave = next(iter(eva.loc[eva["cod_dpto"] == codigo_dane[:2], "departamento"].map(datos.normalizar)), None)
    if clave:
        dep = validos[validos["departamento"].map(datos.normalizar) == clave]
        if not dep.empty:
            return _agregada(dep, "departamento", str(dep["departamento"].iloc[-1]))

    return _agregada(validos, "nacional", "Colombia")


def _agregada(df: pd.DataFrame, nivel: str, etiqueta: str) -> LineaBase:
    por_anio = (df.groupby("anio")
                .apply(datos.rendimiento_ponderado, include_groups=False)
                .rename("rendimiento_ton_ha").reset_index())
    anio = int(por_anio["anio"].iloc[-1])
    ultimo = df[df["anio"] == anio]
    return LineaBase(
        rendimiento_ton_ha=float(por_anio["rendimiento_ton_ha"].iloc[-1]), anio=anio, nivel=nivel,
        etiqueta=etiqueta, historial=por_anio.tail(8).reset_index(drop=True),
        area_cosechada_ha=float(ultimo["area_cosechada_ha"].sum()) if nivel == "departamento" else None,
        fuente=str(ultimo["fuente"].iloc[0]),
    )


@st.cache_data(show_spinner=False)
def banda_historica(anios: int = 5) -> Optional[tuple[float, float]]:
    """Qué tanto cambia el rendimiento municipal de un año al siguiente.

    Mide, en las últimas ``anios`` transiciones de EVA, el cambio relativo del
    rendimiento de cada municipio respecto al año anterior y devuelve los
    percentiles 10 y 90. Es la incertidumbre empírica de usar el último año
    como proyección (p. ej. ``(-0.25, 0.25)``: 8 de cada 10 municipios quedaron
    entre −25 % y +25 %).
    """
    eva = datos.produccion_municipal()
    if eva.empty:
        return None
    eva = eva[eva["en_rango"]].sort_values(["codigo_dane", "anio"])
    grupo = eva.groupby("codigo_dane")
    previo, anio_previo = grupo["rendimiento_ton_ha"].shift(1), grupo["anio"].shift(1)
    consecutivo = (anio_previo == eva["anio"] - 1) & (eva["anio"] > eva["anio"].max() - anios)
    cambio = ((eva["rendimiento_ton_ha"] - previo) / previo)[consecutivo].dropna()
    if len(cambio) < 100:
        return None
    return float(cambio.quantile(0.10)), float(cambio.quantile(0.90))


def ingreso_bruto_cop(rendimiento_ton_ha: float, area_ha: float, precio_cop_carga: float) -> float:
    """Ingreso bruto = toneladas × 1.000 kg / 125 kg por carga × precio por carga."""
    return rendimiento_ton_ha * area_ha * 1000 / KG_POR_CARGA * precio_cop_carga


# ─────────────────────────── Impacto de la roya ─────────────────────────────
@dataclass(frozen=True)
class ImpactoRoya:
    aplica: bool
    motivo: str                       # por qué se aplica o no (se muestra al usuario)
    perdida_min: float = 0.0          # fracción del rendimiento
    perdida_max: float = 0.0
    rendimiento_min_ton_ha: float = 0.0   # rendimiento si la pérdida es la máxima
    rendimiento_max_ton_ha: float = 0.0   # rendimiento si la pérdida es la mínima
    perdida_cop_min: float = 0.0
    perdida_cop_max: float = 0.0


def impacto_roya(
    riesgo: Optional[str],
    resistente_roya: Optional[bool],
    rendimiento_ton_ha: float,
    area_ha: float,
    precio_cop_carga: float,
) -> ImpactoRoya:
    """Convierte el riesgo fitosanitario de la sesión en un descuento del rendimiento.

    Solo penaliza cuando el riesgo es «Alto» (roya detectada con confianza alta)
    y la variedad no es resistente: las pérdidas de Cenicafé se midieron sin
    control químico en variedades que la roya sí afecta.

    Args:
        riesgo: ``"Alto"``, ``"Medio"``, ``"Bajo"`` o ``None`` (sin fotos).
        resistente_roya: ``True`` si la variedad de la finca es resistente.
        rendimiento_ton_ha: Rendimiento base, antes de descontar.
        area_ha: Área en café.
        precio_cop_carga: Precio interno por carga de 125 kg.

    Returns:
        El impacto, con ``aplica=False`` y el motivo cuando no se descuenta.
    """
    if riesgo != "Alto":
        motivos = {
            None: "Aún no hay fotos revisadas en esta sesión.",
            "Bajo": "Las hojas revisadas salieron sanas.",
            "Medio": "Hay una sospecha sin confirmar; repite la foto con buena luz antes de estimar pérdidas.",
        }
        return ImpactoRoya(False, motivos.get(riesgo, ""))
    if resistente_roya:
        return ImpactoRoya(False, "La variedad de la finca es resistente a la roya: no se descuenta "
                                  "rendimiento. Confirma el diagnóstico con tu extensionista.")

    minimo, maximo = PERDIDA_ROYA_SIN_CONTROL
    ingreso = ingreso_bruto_cop(rendimiento_ton_ha, area_ha, precio_cop_carga)
    return ImpactoRoya(
        aplica=True, motivo="Roya detectada con confianza alta.",
        perdida_min=minimo, perdida_max=maximo,
        rendimiento_min_ton_ha=rendimiento_ton_ha * (1 - maximo),
        rendimiento_max_ton_ha=rendimiento_ton_ha * (1 - minimo),
        perdida_cop_min=ingreso * minimo, perdida_cop_max=ingreso * maximo,
    )


# ───────────────────── Simulador (modelo de datos simulados) ────────────────
class ModeloIncompatibleError(RuntimeError):
    """El artefacto existe pero no se puede cargar con las librerías instaladas.

    Un ``.pkl`` de scikit-learn solo se lee con la versión que lo guardó: no es
    un fallo de la app sino del entorno. ``comando`` trae el ``pip install``
    que lo corrige cuando se pudo identificar la versión requerida.
    """

    def __init__(self, mensaje: str, comando: Optional[str] = None) -> None:
        super().__init__(mensaje)
        self.comando = comando


@st.cache_resource(show_spinner=False)
def _modelo_simulado():
    import warnings

    import joblib

    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        try:
            modelo = joblib.load(RUTA_MODELO_SIMULADO)
        except FileNotFoundError:
            raise
        except Exception as error:
            raise _error_de_carga(error, avisos) from error
    for aviso in avisos:        # la carga funcionó: los avisos siguen su curso normal
        warnings.warn_explicit(aviso.message, aviso.category, aviso.filename, aviso.lineno)
    return modelo


def _error_de_carga(error: Exception, avisos: list) -> ModeloIncompatibleError:
    """Traduce un fallo de deserialización a un mensaje que diga qué instalar."""
    import sklearn

    # scikit-learn avisa con qué versión se guardó cada estimador del pipeline.
    guardado = next((a.message.original_sklearn_version for a in avisos
                     if hasattr(a.message, "original_sklearn_version")), None)
    nombre = RUTA_MODELO_SIMULADO.name
    if guardado and guardado != sklearn.__version__:
        return ModeloIncompatibleError(
            f"`{nombre}` se guardó con scikit-learn {guardado} y este entorno tiene {sklearn.__version__}; "
            "un modelo de scikit-learn solo se carga con la versión que lo guardó. Instala la versión "
            "fijada en `requirements.txt` y reinicia la aplicación.",
            comando=f"python -m pip install scikit-learn=={guardado}",
        )
    return ModeloIncompatibleError(
        f"`{nombre}` no se pudo cargar con las librerías instaladas ({type(error).__name__}: {error}). "
        "Instala las versiones de `requirements.txt` y reinicia la aplicación.",
        comando="python -m pip install -r requirements.txt",
    )


def simulador_disponible() -> bool:
    return RUTA_MODELO_SIMULADO.exists()


def simular_escenario(
    altitud_msnm: float, temp_media_c: float, precip_mensual_mm: float, oni: float,
    precio_cop_carga: float, area_ha: float, departamento: str, anio: int, mes: int,
) -> float:
    """Evalúa el ``.pkl`` de NB09 y devuelve el resultado en ton/ha.

    El modelo se entrenó con datos simulados: su salida ilustra el flujo de un
    escenario, no estima el rendimiento real. Predice en kg/ha (así se generó
    su variable objetivo), por eso se divide entre 1.000. La precipitación que
    espera es mensual.

    Raises:
        FileNotFoundError: Si el artefacto no está en ``04_modelos_entrenados``.
        ModeloIncompatibleError: Si el artefacto no se puede cargar con las
            versiones instaladas (p. ej. otra versión de scikit-learn).
    """
    modelo = _modelo_simulado()
    categorias = modelo.named_steps["prep"].named_transformers_["cat"].named_steps["oh"].categories_[0]
    por_clave = {datos.normalizar(c): str(c) for c in categorias}
    por_clave.setdefault("VALLE DEL CAUCA", por_clave.get("VALLE", "Valle"))
    entrada = pd.DataFrame([{
        "altitud_msnm": altitud_msnm, "precip_mm": precip_mensual_mm, "temp_med_c": temp_media_c,
        "oni_index": oni, "precio_fnc_cop_carga": precio_cop_carga, "area_sembrada_ha": area_ha,
        "ano": anio, "mes": mes,
        "departamento": por_clave.get(datos.normalizar(departamento), departamento),
        "fase_enso": "Nino" if oni > 0.5 else ("Nina" if oni < -0.5 else "Neutro"),
    }])
    return float(modelo.predict(entrada)[0]) / 1000.0
