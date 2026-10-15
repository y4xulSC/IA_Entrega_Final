"""Acceso a datos compartido por las pantallas (una sola forma de leer cada fuente).

Antes cada pantalla abría sus CSV y adivinaba columnas por nombre; por eso el
Dashboard terminó sumando la producción NACIONAL de la FNC repetida en cada
fila municipal. Aquí cada fuente tiene un cargador con contrato explícito:

* ``produccion_municipal``  EVA municipal real (producción, área, rendimiento).
* ``catalogo_municipios``   municipios cafeteros con código DANE verificado.
* ``enso_anual``            ONI medio y fase por año.
* ``series_precios``        precio interno FNC, ICO compuesto y referencias largas.

No depende de ``contexto_finca`` (evita importaciones circulares).
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

PROYECTO: Path = Path(__file__).resolve().parents[2]
DIR_DATOS: Path = PROYECTO / "01_datos"

# Rango físico admitido para el rendimiento del café (regla de calidad del proyecto).
RANGO_RENDIMIENTO_TON_HA: tuple[float, float] = (0.2, 5.5)

RUTA_EVA_VALIDADO: Path = DIR_DATOS / "procesados" / "produccion_validado.csv"
RUTA_EVA_RECIENTE: Path = DIR_DATOS / "originales" / "produccion" / "EVA_cafe_2019_2024.csv"

_MINUSCULAS = {"De", "Del", "La", "Las", "Los", "El", "Y"}
# El catálogo geográfico abrevia departamentos; EVA usa el nombre oficial.
_ALIAS_DEPARTAMENTO = {"VALLE": "VALLE DEL CAUCA", "N. SANTANDER": "NORTE DE SANTANDER", "GUAJIRA": "LA GUAJIRA"}


def normalizar(texto: object) -> str:
    """Clave de comparación: mayúsculas, sin tildes ni espacios dobles (``Nariño`` -> ``NARINO``)."""
    plano = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return " ".join(plano.upper().split())


def miles(valor: float, decimales: int = 0) -> str:
    """Formato colombiano: ``1234567.8`` -> ``'1.234.568'`` (punto de miles, coma decimal)."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def porcentaje(fraccion: float, decimales: int = 0, signo: bool = False) -> str:
    """``0.098`` -> ``'9,8 %'`` (con ``decimales=1``). ``signo=True`` antepone + o −."""
    texto = miles(abs(fraccion) * 100, decimales) + " %"
    if signo or fraccion < 0:
        texto = ("−" if fraccion < 0 else "+") + texto
    return texto


def nombre_legible(texto: object) -> str:
    """``'VALLE DEL CAUCA'`` -> ``'Valle del Cauca'``. Respeta los nombres que ya traen minúsculas."""
    texto = " ".join(str(texto).split())
    if not texto.isupper():
        return texto
    palabras = texto.title().split()
    return " ".join(p.lower() if i and p in _MINUSCULAS else p for i, p in enumerate(palabras))


# ───────────────────────────── Producción EVA ───────────────────────────────
@st.cache_data(show_spinner=False)
def produccion_municipal() -> pd.DataFrame:
    """Producción de café por municipio y año (EVA, Ministerio de Agricultura).

    Une ``produccion_validado.csv`` (2007–2018) con ``EVA_cafe_2019_2024.csv``
    cuando está disponible: el archivo validado termina en 2018 aunque el ETL
    lo nombra «2007_2024». La corrección de fondo es incluir 2019–2024 en el ETL.

    Returns:
        Una fila por municipio y año con: ``codigo_dane`` (5 dígitos),
        ``cod_dpto``, ``departamento``, ``municipio``, ``anio``,
        ``area_sembrada_ha``, ``area_cosechada_ha``, ``produccion_ton``,
        ``rendimiento_ton_ha``, ``fuente`` y ``en_rango`` (rendimiento dentro
        del rango físico). Vacío si no hay archivos.
    """
    columnas = ["codigo_dane", "departamento", "municipio", "anio", "area_sembrada_ha",
                "area_cosechada_ha", "produccion_ton", "rendimiento_ton_ha"]
    partes: list[pd.DataFrame] = []

    if RUTA_EVA_VALIDADO.exists():
        validado = pd.read_csv(RUTA_EVA_VALIDADO, dtype={"codigo_dane": str})
        validado["codigo_dane"] = validado["codigo_dane"].str.zfill(5)
        partes.append(validado[columnas].assign(fuente="EVA 2007–2018 (validado)"))

    if RUTA_EVA_RECIENTE.exists():
        reciente = pd.read_csv(RUTA_EVA_RECIENTE, encoding="utf-8-sig").rename(columns={
            "Departamento": "departamento", "Municipio": "municipio", "Anio": "anio",
            "Area_sembrada": "area_sembrada_ha", "Area_cosechada": "area_cosechada_ha",
            "Produccion": "produccion_ton", "Rendimiento": "rendimiento_ton_ha",
        })
        reciente["codigo_dane"] = reciente["Cod_Mpio"].astype(int).astype(str).str.zfill(5)
        partes.append(reciente[columnas].assign(fuente="EVA 2019–2024"))

    if not partes:
        return pd.DataFrame(columns=columnas + ["cod_dpto", "fuente", "en_rango"]).astype({"en_rango": bool})

    df = pd.concat(partes, ignore_index=True)
    df["anio"] = df["anio"].astype(int)
    # Si un municipio-año viniera en ambas fuentes, manda la más reciente.
    df = df.drop_duplicates(["codigo_dane", "anio"], keep="last")
    df["cod_dpto"] = df["codigo_dane"].str[:2]

    # Un solo nombre por código: el del registro más reciente (trae tildes).
    por_anio = df.sort_values("anio")
    nombres_mun = por_anio.groupby("codigo_dane")["municipio"].last().map(nombre_legible)
    nombres_dep = por_anio.groupby("cod_dpto")["departamento"].last().map(nombre_legible)
    df["municipio"] = df["codigo_dane"].map(nombres_mun)
    df["departamento"] = df["cod_dpto"].map(nombres_dep)

    df["en_rango"] = df["rendimiento_ton_ha"].between(*RANGO_RENDIMIENTO_TON_HA)
    return df.sort_values(["codigo_dane", "anio"], ignore_index=True)


def rendimiento_ponderado(df: pd.DataFrame) -> float:
    """Rendimiento agregado correcto: producción total / área cosechada total.

    Promediar los rendimientos municipales daría el mismo peso a un municipio
    de 50 ha que a uno de 18.000 ha.
    """
    area = df["area_cosechada_ha"].sum()
    return float(df["produccion_ton"].sum() / area) if area else float("nan")


# ─────────────────────────── Catálogo de municipios ─────────────────────────
@st.cache_data(show_spinner=False)
def catalogo_municipios() -> pd.DataFrame:
    """Municipios cafeteros con código DANE verificado contra EVA.

    El catálogo geográfico del proyecto trae coordenadas y altitud de 21
    cabeceras, pero dos códigos están mal (``63594`` es Quimbaya, no Salento;
    ``17442`` es Marmato, no Marsella). Por eso las coordenadas se cruzan por
    NOMBRE de municipio y departamento, y el código que vale es el de EVA.

    Los municipios sin cabecera en ese catálogo toman las coordenadas de
    DIVIPOLA (DANE) por código, si se descargó con
    ``03_scripts/descarga/08_descargar_divipola.py``. Sin eso el mapa de
    alertas solo puede ubicar las 21 cabeceras.

    Returns:
        ``codigo_dane``, ``municipio``, ``departamento``, ``cod_dpto``, ``lat``,
        ``lon``, ``altitud_msnm`` (NaN si no hay dato), ``tiene_eva`` y
        ``fuente_coordenadas`` (``"cabecera validada"``, ``"DIVIPOLA"`` o vacío).
    """
    eva = produccion_municipal()
    base = (eva.sort_values("anio").groupby("codigo_dane").tail(1)
            [["codigo_dane", "municipio", "departamento", "cod_dpto"]].assign(tiene_eva=True))
    base["clave"] = base["municipio"].map(normalizar) + "|" + base["departamento"].map(normalizar)

    base[["lat", "lon", "altitud_msnm"]] = np.nan
    oficial_dpto = {normalizar(d): d for d in base["departamento"].unique()}
    geo = _catalogo_geografico()
    sobrantes: list[dict] = []
    for fila in geo.to_dict("records"):
        nombre = normalizar(fila["municipio"])
        departamento = normalizar(fila["departamento"])
        clave = f"{nombre}|{_ALIAS_DEPARTAMENTO.get(departamento, departamento)}"
        destino = base["clave"] == clave
        if not destino.any():
            # Mismo código y nombre contenido en el oficial («Cali» en «Santiago de Cali»).
            destino = (base["codigo_dane"] == fila["codigo_dane"]) & base["municipio"].map(
                lambda oficial: nombre in normalizar(oficial))
        if destino.any():
            base.loc[destino, ["lat", "lon", "altitud_msnm"]] = [fila["lat"], fila["lon"], fila["altitud_msnm"]]
        elif not (base["codigo_dane"] == fila["codigo_dane"]).any():
            # Municipio con coordenadas que EVA no reporta: se conserva con su código.
            oficial = oficial_dpto.get(_ALIAS_DEPARTAMENTO.get(departamento, departamento), fila["departamento"])
            sobrantes.append({**fila, "departamento": oficial, "cod_dpto": fila["codigo_dane"][:2],
                              "tiene_eva": False, "clave": clave})
    if sobrantes:
        base = pd.concat([base, pd.DataFrame(sobrantes)[base.columns]], ignore_index=True)

    base["fuente_coordenadas"] = np.where(base["lat"].notna(), "cabecera validada", None)
    divipola = _coordenadas_divipola()
    if not divipola.empty:
        faltan = base["lat"].isna() & base["codigo_dane"].isin(divipola.index)
        codigos = base.loc[faltan, "codigo_dane"]
        base.loc[faltan, "lat"] = codigos.map(divipola["lat"]).to_numpy()
        base.loc[faltan, "lon"] = codigos.map(divipola["lon"]).to_numpy()
        base.loc[faltan, "fuente_coordenadas"] = "DIVIPOLA"

    return base.drop(columns="clave").sort_values(["departamento", "municipio"], ignore_index=True)


RUTA_DIVIPOLA: Path = DIR_DATOS / "procesados" / "divipola_municipios.csv"


def _coordenadas_divipola() -> pd.DataFrame:
    """Centroide de la cabecera de cada municipio (DANE), indexado por código."""
    if not RUTA_DIVIPOLA.exists():
        return pd.DataFrame(columns=["lat", "lon"])
    df = pd.read_csv(RUTA_DIVIPOLA, dtype={"codigo_dane": str}, usecols=["codigo_dane", "lat", "lon"])
    df = df.dropna().drop_duplicates("codigo_dane")
    return df.set_index("codigo_dane")[["lat", "lon"]]


def _catalogo_geografico() -> pd.DataFrame:
    columnas = ["codigo_dane", "municipio", "departamento", "lat", "lon", "altitud_msnm"]
    for ruta in (DIR_DATOS / "procesados" / "geografia_validado.csv",
                 DIR_DATOS / "enriquecidos" / "geografia" / "dem_municipal_altitud.csv"):
        if ruta.exists():
            df = pd.read_csv(ruta, dtype={"codigo_dane": str}, usecols=lambda c: c in columnas)
            if set(columnas) <= set(df.columns):
                return df
    return pd.DataFrame(columns=columnas)


# ──────────────────────────────── ENSO ──────────────────────────────────────
@st.cache_data(show_spinner=False)
def enso_anual() -> pd.DataFrame:
    """ONI medio y fase por año (``El Niño`` > +0,5 · ``La Niña`` < −0,5 · ``Neutro``)."""
    ruta = DIR_DATOS / "procesados" / "enso_validado.csv"
    if not ruta.exists():
        return pd.DataFrame(columns=["anio", "oni", "fase"])
    df = pd.read_csv(ruta, parse_dates=["fecha"]).dropna(subset=["oni"])
    anual = df.groupby(df["fecha"].dt.year)["oni"].agg(oni="mean", meses="count").reset_index(names="anio")
    anual = anual[anual["meses"] >= 6]          # un año con pocos meses no define fase
    anual["fase"] = pd.cut(anual["oni"], [-np.inf, -0.5, 0.5, np.inf],
                           labels=["La Niña", "Neutro", "El Niño"]).astype(str)
    return anual[["anio", "oni", "fase"]]


# ─────────────────────────────── Precios ────────────────────────────────────
SERIES_PRECIO: dict[str, dict[str, str]] = {
    "fnc": {"nombre": "Precio interno FNC", "unidad": "COP por carga de 125 kg"},
    "ico": {"nombre": "Indicador compuesto ICO", "unidad": "centavos de dólar por libra"},
    "arabica_bm": {"nombre": "Arábica · Banco Mundial (referencia larga)", "unidad": "USD por kg"},
}


@st.cache_data(show_spinner=False)
def series_precios() -> dict[str, pd.Series]:
    """Series mensuales de precio, indexadas por fecha y sin huecos al final.

    El precio FNC y el arábica del Banco Mundial salen de ``precios_validado.csv``.
    El compuesto ICO solo existe en los archivos enriquecidos u originales; si
    no están (p. ej. en un despliegue desde git) la clave ``ico`` no se devuelve.
    """
    series: dict[str, pd.Series] = {}

    ruta = DIR_DATOS / "procesados" / "precios_validado.csv"
    if ruta.exists():
        df = pd.read_csv(ruta, parse_dates=["fecha"]).set_index("fecha").sort_index()
        if "precio_fnc_cop_kg" in df:
            series["fnc"] = (df["precio_fnc_cop_kg"] * 125).dropna()
        if "precio_arabica_wb_usd_kg" in df:
            series["arabica_bm"] = df["precio_arabica_wb_usd_kg"].dropna()

    candidatos = [
        (DIR_DATOS / "enriquecidos" / "precios" / "precios_consolidados_mensual.csv",
         "orig_precio_oic_compuesto_cusd_libra__fnc_cafe_mensual"),
        (DIR_DATOS / "originales" / "precios" / "fnc_cafe_mensual.csv", "precio_oic_compuesto_cusd_libra"),
    ]
    for ruta, columna in candidatos:
        if ruta.exists():
            df = pd.read_csv(ruta, encoding="utf-8-sig", parse_dates=["fecha"])
            if columna in df:
                series["ico"] = df.set_index("fecha")[columna].sort_index().dropna()
                break

    return {clave: s.rename(SERIES_PRECIO[clave]["nombre"]) for clave, s in series.items() if len(s)}
