"""
===============================================================================
 04_descargar_eva_municipal.py
===============================================================================
 Descarga EVA (Evaluaciones Agropecuarias Municipales) extendido:
   - Periodo completo 2007-2024
   - Granularidad municipal (NO departamental)
   - Filtrado a cafe Arabica + Robusta + Pergamino + Verde

 Fuente: datos.gov.co (Socrata API)
   Datasets vigentes (mayo 2026):
     2pnw-mmge   EVA Municipales (canonico)
     uejq-wxrr   EVA Base Agricola 2019-2024
     fp29-z39g   Vista EVA (resumen)

 v2 (2026-05-07): App Token en header X-App-Token, descubrimiento dinamico
                  de columna 'cultivo', fallback a IDs alternativos,
                  exit(1) si todos los IDs fallan.

 Output:
   01_datos/enriquecidos/produccion/
     eva_cafe_municipal_2007_2024.csv
     eva_cafe_resumen_anual.csv
===============================================================================
"""
from __future__ import annotations
from io import StringIO
from pathlib import Path
import sys
import time

import requests
import pandas as pd

from _config import socrata_headers, SOCRATA_APP_TOKEN

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
OUT_DIR = PROJECT_ROOT / "01_datos" / "enriquecidos" / "produccion"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DATASETS_EVA = [
    ("2pnw-mmge", "EVA Municipales (canonico)"),
    ("uejq-wxrr", "EVA Base Agricola 2019-2024"),
    ("fp29-z39g", "Vista EVA (resumen)"),
]


def _socrata_columns(socrata_id):
    """Lee 1 fila para detectar el nombre real de las columnas."""
    URL = "https://www.datos.gov.co/resource/" + socrata_id + ".json"
    try:
        r = requests.get(URL, params={"$limit": 1},
                         headers=socrata_headers(), timeout=30)
        r.raise_for_status()
        data = r.json()
        if data:
            return list(data[0].keys())
    except Exception as e:
        print("   WARN no pude leer schema de " + socrata_id + ": " + str(e))
    return []


def _build_where(columns):
    """WHERE robusto basado en las columnas reales."""
    posibles = ["cultivo", "nombre_cultivo", "cul", "producto", "nom_cultivo"]
    col_match = next((c for c in posibles if c in columns), None)
    if not col_match:
        return ""
    return ("upper(" + col_match + ") like '%CAFE%' OR "
            "upper(" + col_match + ") like '%CAFE%'")


def descargar_eva(socrata_id, *, limit=500_000):
    """Descarga EVA filtrado a cafe. Si la WHERE falla descarga todo."""
    print("\n[Socrata] " + socrata_id + " ...")
    URL = "https://www.datos.gov.co/resource/" + socrata_id + ".csv"
    headers = socrata_headers()

    columns = _socrata_columns(socrata_id)
    if columns:
        ejemplo = ", ".join(columns[:6])
        print("   columnas detectadas: " + str(len(columns)) +
              " (ej: " + ejemplo + ")")
    where = _build_where(columns)

    if where:
        try:
            r = requests.get(URL, params={"$limit": limit, "$where": where},
                             headers=headers, timeout=180)
            r.raise_for_status()
            df = pd.read_csv(StringIO(r.text))
            print("   OK " + str(len(df)) + " filas con filtro cafe")
            return df
        except Exception as e:
            print("   WARN WHERE fallo (" + str(e) + ") - descargando todo")

    pages = []
    offset = 0
    page_size = 50_000
    try:
        while offset < limit:
            r = requests.get(URL,
                             params={"$limit": page_size, "$offset": offset},
                             headers=headers, timeout=300)
            r.raise_for_status()
            df_page = pd.read_csv(StringIO(r.text))
            if df_page.empty:
                break
            pages.append(df_page)
            offset += len(df_page)
            print("   pagina: +" + str(len(df_page)) +
                  " filas (total " + str(offset) + ")")
            if len(df_page) < page_size:
                break
            time.sleep(0.3)
    except Exception as e:
        print("   FAIL paginacion " + socrata_id + ": " + str(e))

    if not pages:
        return pd.DataFrame()

    df = pd.concat(pages, ignore_index=True)
    posibles = ["cultivo", "nombre_cultivo", "cul", "producto", "nom_cultivo"]
    col = next((c for c in posibles if c in df.columns), None)
    if col:
        antes = len(df)
        df = df[df[col].astype(str).str.contains(
            "cafe|caf", case=False, na=False, regex=True)]
        print("   filtrado pandas: " + str(antes) +
              " -> " + str(len(df)) + " filas (cafe)")
    return df


def main():
    print("=" * 70)
    print(" Descarga EVA Municipal - Cafe (extendido a 2007-2024)")
    print("=" * 70)
    if SOCRATA_APP_TOKEN:
        print("   OK App Token Socrata configurado (" +
              SOCRATA_APP_TOKEN[:8] + "...)")
    else:
        print("   WARN Sin App Token - rate limits muy bajos")

    todos = []
    for sid, desc in DATASETS_EVA:
        df = descargar_eva(sid)
        if not df.empty:
            df["fuente_socrata"] = sid
            todos.append(df)
            if len(df) > 1000:
                break
        time.sleep(1)

    if not todos:
        print("\nFAIL Ningun dataset Socrata respondio.")
        print("   Verifica https://www.datos.gov.co que los IDs sigan activos.")
        return 1

    df = pd.concat(todos, ignore_index=True)

    rename_map = {
        "anio": "anio", "ano": "anio", "year": "anio", "ao": "anio",
        "departamento": "departamento", "depto": "departamento",
        "nom_dep": "departamento", "nombre_dep": "departamento",
        "municipio": "municipio", "muni": "municipio",
        "nom_mun": "municipio", "nombre_municipio": "municipio",
        "codigo_dane_municipio": "codigo_dane",
        "cod_mun": "codigo_dane", "cod_dane": "codigo_dane",
        "cultivo": "cultivo", "nombre_cultivo": "cultivo",
        "area_sembrada__ha_": "area_sembrada_ha",
        "area_sembrada_ha": "area_sembrada_ha",
        "area_sembrada": "area_sembrada_ha",
        "area_cosechada__ha_": "area_cosechada_ha",
        "area_cosechada_ha": "area_cosechada_ha",
        "area_cosechada": "area_cosechada_ha",
        "produccion__t_": "produccion_ton",
        "produccion_t": "produccion_ton",
        "produccion": "produccion_ton",
        "rendimiento__t_ha_": "rendimiento_ton_ha",
        "rendimiento_t_ha": "rendimiento_ton_ha",
        "rendimiento": "rendimiento_ton_ha",
    }
    df = df.rename(columns={c: rename_map.get(c.lower(), c) for c in df.columns})

    if "cultivo" in df.columns:
        df = df[~df["cultivo"].astype(str).str.contains(
            "tostado|soluble|extracto|descafeinado", case=False, na=False)]

    out_path = OUT_DIR / "eva_cafe_municipal_2007_2024.csv"
    df.to_csv(out_path, index=False)
    print("\nOK " + out_path.name + ": " + str(len(df)) + " filas")

    if "anio" in df.columns and "produccion_ton" in df.columns:
        for col in ["area_sembrada_ha", "area_cosechada_ha",
                    "produccion_ton", "rendimiento_ton_ha"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["anio"] = pd.to_numeric(df["anio"], errors="coerce")

        agg_kwargs = {}
        if "municipio" in df.columns:
            agg_kwargs["n_municipios"] = ("municipio", "nunique")
        if "area_sembrada_ha" in df.columns:
            agg_kwargs["area_total_ha"] = ("area_sembrada_ha", "sum")
        if "produccion_ton" in df.columns:
            agg_kwargs["produccion_total_ton"] = ("produccion_ton", "sum")
        if "rendimiento_ton_ha" in df.columns:
            agg_kwargs["rendimiento_medio"] = ("rendimiento_ton_ha", "mean")

        resumen = df.dropna(subset=["anio"]).groupby("anio").agg(**agg_kwargs).reset_index()
        out_resumen = OUT_DIR / "eva_cafe_resumen_anual.csv"
        resumen.to_csv(out_resumen, index=False)
        print("OK " + out_resumen.name + ": " + str(len(resumen)) + " anios")
        print(resumen.to_string(index=False))

    print("\nOK Listo. Siguiente: 05_descargar_dem_suelos.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
