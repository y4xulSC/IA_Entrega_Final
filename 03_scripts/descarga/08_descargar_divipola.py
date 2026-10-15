"""
===============================================================================
 08_descargar_divipola.py
===============================================================================
 Descarga DIVIPOLA (DANE): código, nombre y coordenadas de la cabecera de los
 1.122 municipios de Colombia.

 Para qué: el catálogo geográfico del proyecto solo trae coordenadas de 21
 cabeceras. El mapa de calor de alertas de roya (vista del Agrónomo) necesita
 ubicar cualquier municipio desde el que un caficultor envíe una foto.

 Fuente: datos.gov.co (Socrata), dataset gdxc-w37w
   "DIVIPOLA - Códigos municipios" (DANE)

 Output:
   01_datos/procesados/divipola_municipios.csv
     codigo_dane (5 dígitos), municipio, departamento, lat, lon

 Uso:
   python 03_scripts/descarga/08_descargar_divipola.py
===============================================================================
"""
from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from _config import socrata_headers

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
SALIDA = PROJECT_ROOT / "01_datos" / "procesados" / "divipola_municipios.csv"
REFERENCIA = PROJECT_ROOT / "01_datos" / "procesados" / "geografia_validado.csv"

DATASET = "gdxc-w37w"
URL_JSON = f"https://www.datos.gov.co/resource/{DATASET}.json?$limit=5000"
URL_CSV = f"https://www.datos.gov.co/api/views/{DATASET}/rows.csv?accessType=DOWNLOAD"

# Caja de Colombia continental + San Andrés (lat −4,3 a 13,5; lon −82 a −66,8).
RANGO_LAT = (-4.3, 13.5)
RANGO_LON = (-82.0, -66.8)
TOLERANCIA_GRADOS = 0.25   # diferencia admitida contra las 21 cabeceras validadas

# Nombres posibles de cada campo (el portal los ha cambiado entre versiones).
CANDIDATOS = {
    "cod_dpto": ["cod_dpto", "codigo_departamento", "cod_depto", "código_departamento"],
    "dpto": ["dpto", "departamento", "nom_dpto", "nombre_departamento"],
    "cod_mpio": ["cod_mpio", "codigo_municipio", "cod_municipio", "código_municipio"],
    "nom_mpio": ["nom_mpio", "municipio", "nombre_municipio"],
    "latitud": ["latitud", "lat", "latitude"],
    "longitud": ["longitud", "lon", "long", "longitude"],
}


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    plano = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    df = df.rename(columns=plano)
    renombre: dict[str, str] = {}
    for destino, opciones in CANDIDATOS.items():
        encontrada = next((c for c in opciones if c in df.columns), None)
        if encontrada is None:
            raise KeyError(f"No encuentro la columna {destino!r}. Columnas: {list(df.columns)}")
        renombre[encontrada] = destino
    return df.rename(columns=renombre)[list(CANDIDATOS)]


def _numero(serie: pd.Series) -> pd.Series:
    """El portal publica las coordenadas como texto con coma decimal (``-75,581775``)."""
    texto = serie.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(texto, errors="coerce")


def limpiar(crudo: pd.DataFrame) -> pd.DataFrame:
    """Convierte la tabla del portal en ``codigo_dane, municipio, departamento, lat, lon``.

    Raises:
        ValueError: si quedan menos de 1.000 municipios válidos (descarga incompleta).
    """
    df = _normalizar_columnas(crudo)
    cod_dpto = df["cod_dpto"].astype(str).str.extract(r"(\d+)")[0].str.zfill(2)
    cod_mpio = df["cod_mpio"].astype(str).str.extract(r"(\d+)")[0]
    # Algunas versiones traen el código completo (05001) y otras solo el municipal (001).
    codigo = cod_mpio.where(cod_mpio.str.len() > 3, cod_dpto + cod_mpio.str.zfill(3)).str.zfill(5)

    limpio = pd.DataFrame({
        "codigo_dane": codigo,
        "municipio": df["nom_mpio"].astype(str).str.strip().str.title(),
        "departamento": df["dpto"].astype(str).str.strip().str.title(),
        "lat": _numero(df["latitud"]),
        "lon": _numero(df["longitud"]),
    })
    validos = (limpio["codigo_dane"].str.fullmatch(r"\d{5}")
               & limpio["lat"].between(*RANGO_LAT) & limpio["lon"].between(*RANGO_LON))
    descartados = limpio[~validos]
    if len(descartados):
        print(f"  ⚠ {len(descartados)} filas sin código o con coordenadas fuera de Colombia (se descartan)")
    limpio = limpio[validos].drop_duplicates("codigo_dane").sort_values("codigo_dane", ignore_index=True)
    if len(limpio) < 1000:
        raise ValueError(f"Solo {len(limpio)} municipios válidos: la descarga parece incompleta.")
    return limpio


def comparar_con_referencia(limpio: pd.DataFrame, referencia: Path = REFERENCIA) -> pd.DataFrame:
    """Diferencias contra las cabeceras ya validadas del proyecto (por código DANE)."""
    if not referencia.exists():
        return pd.DataFrame()
    ref = pd.read_csv(referencia, dtype={"codigo_dane": str}, usecols=["codigo_dane", "municipio", "lat", "lon"])
    cruce = ref.merge(limpio, on="codigo_dane", suffixes=("_ref", "_dane"))
    cruce["diferencia_grados"] = ((cruce["lat_ref"] - cruce["lat_dane"]).abs()
                                  + (cruce["lon_ref"] - cruce["lon_dane"]).abs())
    return cruce[cruce["diferencia_grados"] > TOLERANCIA_GRADOS]


def descargar() -> pd.DataFrame:
    errores: list[str] = []
    try:
        r = requests.get(URL_JSON, headers=socrata_headers(), timeout=60)
        r.raise_for_status()
        return pd.DataFrame(r.json())
    except (requests.RequestException, ValueError) as e:
        errores.append(f"JSON: {e}")
    try:
        r = requests.get(URL_CSV, headers=socrata_headers(), timeout=60)
        r.raise_for_status()
        return pd.read_csv(StringIO(r.text), dtype=str)
    except (requests.RequestException, ValueError) as e:
        errores.append(f"CSV: {e}")
    raise RuntimeError("No se pudo descargar DIVIPOLA:\n  " + "\n  ".join(errores))


def main() -> int:
    print(f"Descargando DIVIPOLA ({DATASET}) de datos.gov.co…")
    try:
        crudo = descargar()
        limpio = limpiar(crudo)
    except (RuntimeError, KeyError, ValueError) as e:
        print(f"✖ {e}")
        return 1

    diferencias = comparar_con_referencia(limpio)
    if len(diferencias):
        print(f"  ⚠ {len(diferencias)} cabeceras difieren más de {TOLERANCIA_GRADOS}° de geografia_validado.csv "
              "(el catálogo de la app conserva las validadas):")
        print(diferencias[["codigo_dane", "municipio_ref", "municipio_dane", "diferencia_grados"]]
              .to_string(index=False))

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    limpio.to_csv(SALIDA, index=False, encoding="utf-8")
    print(f"✔ {len(limpio)} municipios → {SALIDA.relative_to(PROJECT_ROOT)}")
    print("  Reinicia Streamlit para que el mapa de alertas use las nuevas coordenadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
