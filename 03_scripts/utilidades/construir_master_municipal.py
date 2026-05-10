"""
===============================================================================
 construir_master_municipal.py
===============================================================================
 Construye el dataset maestro municipal-mensual que consumen los notebooks
 NB07-NB11.

 ENTRADA — dos modos posibles:

   MODO A · BD (preferido si PostgreSQL está cargado)
     Lee la vista materializada cafe.vw_master_municipal_mensual
     que ya cruza fact_produccion + fact_clima + fact_precio + dim_periodo.

   MODO B · CSVs (fallback si no hay BD)
     Lee y cruza directamente los CSVs en 01_datos/enriquecidos/:
       precios/precios_consolidados_mensual.csv     (FRED + WB + IMF + ICO)
       clima/openmeteo_municipios_mensual.csv       (Open-Meteo)
       clima/enso_oni_extendido.csv                 (NOAA ONI)
       produccion/eva_cafe_municipal_2007_2024.csv  (DANE EVA municipal)
       geografia/dem_municipal_altitud.csv          (Open-Elevation)
       geografia/soilgrids_municipal.csv            (SoilGrids ISRIC)

 SALIDA:
   01_datos/procesados/master_cafe_municipal_mensual.csv
   01_datos/procesados/master_cafe_municipal_anual.csv  (resumen por año)

 Este script materializa el "feature engineering integrado" pero a nivel
 MUNICIPAL (no departamental como en la 2da entrega NB04). Crea variables
 lag (1, 3, 6, 12 meses), rolling means, indicadores ENSO, estrés hídrico
 y amplitud térmica.

 Uso:
   python construir_master_municipal.py                    # modo auto: BD si hay, si no CSVs
   python construir_master_municipal.py --modo bd          # forzar BD
   python construir_master_municipal.py --modo csv         # forzar CSVs
   python construir_master_municipal.py --solo-cafeteros   # solo dptos cafeteros
===============================================================================
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# UTF-8 stdout en Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve()
PROJECT = HERE.parents[2]
DIR_ENRIQ = PROJECT / "01_datos" / "enriquecidos"
DIR_OUT = PROJECT / "01_datos" / "procesados"
DIR_OUT.mkdir(parents=True, exist_ok=True)

PG_CONFIG = {
    "host": os.environ.get("PG_HOST", "localhost"),
    "port": int(os.environ.get("PG_PORT", "5432")),
    "user": os.environ.get("PG_USER", "postgres"),
    "password": os.environ.get("PG_PASSWORD", "root"),
    "dbname": os.environ.get("PG_DB", "cafe_ia"),
}

DPTOS_CAFETEROS = {
    "Antioquia", "Huila", "Narino", "Nariño", "Caldas", "Risaralda", "Quindio",
    "Tolima", "Cauca", "Valle", "Valle del Cauca", "Santander",
    "N. Santander", "Norte de Santander", "Boyaca", "Cundinamarca",
    "Caqueta", "Magdalena", "Guajira", "Cesar",
}


# =============================================================================
# MODO A · BD
# =============================================================================
def construir_desde_bd() -> pd.DataFrame | None:
    try:
        import psycopg2
    except ImportError:
        print("   psycopg2 no instalado; modo BD no disponible")
        return None

    print(f"\n[BD] conectando a {PG_CONFIG['user']}@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['dbname']} ...")
    try:
        conn = psycopg2.connect(**PG_CONFIG)
    except Exception as e:
        print(f"   no se pudo conectar: {e}")
        return None

    try:
        # Verificar que existe la vista
        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(*) FROM pg_matviews
                WHERE schemaname='cafe' AND matviewname='vw_master_municipal_mensual'
            """)
            if cur.fetchone()[0] == 0:
                print("   la vista cafe.vw_master_municipal_mensual no existe")
                print("   ejecuta primero: psql -d cafe_ia -f 03_scripts/bd/01_ddl_schema.sql")
                return None

        print("   leyendo vw_master_municipal_mensual ...")
        df = pd.read_sql("SELECT * FROM cafe.vw_master_municipal_mensual ORDER BY cod_mun, fecha", conn)
        print(f"   OK · {len(df)} filas · {len(df.columns)} columnas")
        return df
    finally:
        conn.close()


# =============================================================================
# MODO B · CSVs
# =============================================================================
def _read_csv_safe(path: Path, **kw) -> pd.DataFrame:
    if not path.exists():
        print(f"   ! no existe: {path.relative_to(PROJECT)}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, **kw)
        print(f"   OK {path.name}: {len(df)} filas")
        return df
    except Exception as e:
        print(f"   ! error leyendo {path.name}: {e}")
        return pd.DataFrame()


def construir_desde_csv() -> pd.DataFrame:
    print("\n[CSV] cargando fuentes ...")
    precios = _read_csv_safe(DIR_ENRIQ / "precios"     / "precios_consolidados_mensual.csv")
    clima   = _read_csv_safe(DIR_ENRIQ / "clima"       / "openmeteo_municipios_mensual.csv")
    enso    = _read_csv_safe(DIR_ENRIQ / "clima"       / "enso_oni_extendido.csv")
    eva     = _read_csv_safe(DIR_ENRIQ / "produccion"  / "eva_cafe_municipal_2007_2024.csv")
    dem     = _read_csv_safe(DIR_ENRIQ / "geografia"   / "dem_municipal_altitud.csv")
    suelos  = _read_csv_safe(DIR_ENRIQ / "geografia"   / "soilgrids_municipal.csv")

    if clima.empty:
        print("\n[!] sin clima Open-Meteo. Ejecuta 03_descargar_clima_satelital.py primero.")
        return pd.DataFrame()

    # ---- normalizar fecha mensual ----
    # Convencion: mes_clave es la unica columna de tiempo durante el merge.
    # Las columnas crudas (fecha, mes) se eliminan tras crear mes_clave para
    # evitar colisiones cuando varios CSVs traen su propia "fecha".
    print("\n[transform] normalizando fechas a mes ...")
    fuente_tiempo = "mes" if "mes" in clima.columns else "fecha"
    clima["mes_clave"] = pd.to_datetime(clima[fuente_tiempo], errors="coerce")
    clima = clima.dropna(subset=["mes_clave"])
    clima["mes_clave"] = clima["mes_clave"].dt.to_period("M").dt.to_timestamp()
    clima = clima.drop(columns=[c for c in ("fecha", "mes") if c in clima.columns])

    if not precios.empty:
        precios["mes_clave"] = pd.to_datetime(precios["fecha"], errors="coerce")
        precios = precios.dropna(subset=["mes_clave"])
        precios["mes_clave"] = precios["mes_clave"].dt.to_period("M").dt.to_timestamp()
        precios = precios.drop(columns=[c for c in ("fecha", "mes") if c in precios.columns])

    if not enso.empty:
        if "fecha" in enso.columns:
            enso["mes_clave"] = pd.to_datetime(enso["fecha"], errors="coerce")
            enso = enso.dropna(subset=["mes_clave"])
            enso["mes_clave"] = enso["mes_clave"].dt.to_period("M").dt.to_timestamp()
            cols_enso = [c for c in ["mes_clave", "oni", "fase_enso"] if c in enso.columns]
            enso = enso[cols_enso].drop_duplicates(subset=["mes_clave"], keep="last")

    # ---- merge ----
    print("[merge] uniendo clima + precios + ENSO ...")
    df = clima.copy()

    if not precios.empty:
        df = df.merge(precios, on="mes_clave", how="left")

    if not enso.empty:
        df = df.merge(enso, on="mes_clave", how="left")

    # Geografía (constante por municipio)
    if not dem.empty and "codigo_dane" in dem.columns:
        dem["codigo_dane"] = dem["codigo_dane"].astype(str).str.zfill(5)
        df["codigo_dane"]  = df["codigo_dane"].astype(str).str.zfill(5)
        df = df.merge(dem[["codigo_dane", "altitud_msnm"]], on="codigo_dane", how="left")

    if not suelos.empty and "codigo_dane" in suelos.columns:
        suelos["codigo_dane"] = suelos["codigo_dane"].astype(str).str.zfill(5)
        cols_suelo = [c for c in suelos.columns if "ph" in c.lower() or "soc" in c.lower() or "clay" in c.lower()]
        if cols_suelo:
            df = df.merge(suelos[["codigo_dane"] + cols_suelo], on="codigo_dane", how="left")

    # EVA producción - cruce por municipio + año (granularidad anual)
    if not eva.empty:
        # Detectar columnas
        col_mun = next((c for c in eva.columns if "codigo_dane" in c.lower() or "mun" in c.lower()), None)
        col_ano = next((c for c in eva.columns if c.lower() in ("anio", "ano", "year")), None)
        col_prod = next((c for c in eva.columns if "produccion" in c.lower()), None)
        col_area = next((c for c in eva.columns if "cosechada" in c.lower()), None)
        col_rend = next((c for c in eva.columns if "rendimiento" in c.lower()), None)

        if col_mun and col_ano:
            eva_red = eva[[col_mun, col_ano] + [c for c in (col_prod, col_area, col_rend) if c]].copy()
            eva_red.columns = ["codigo_dane", "anio"] + [c for c in ("produccion_ton", "area_cosechada_ha", "rendimiento_ton_ha") if {"produccion": col_prod, "area": col_area, "rend": col_rend}.get(c.split('_')[0])]
            # Esquema simplificado: aplicar al primer mes del año en que toque
            eva_red["codigo_dane"] = eva_red["codigo_dane"].astype(str).str.zfill(5)
            df["anio"] = df["mes_clave"].dt.year
            df = df.merge(eva_red, on=["codigo_dane", "anio"], how="left")

    # Si despues del merge llegan columnas heredadas con el nombre "fecha"
    # (p.ej. de un CSV legacy), las eliminamos antes del rename para que
    # mes_clave -> fecha sea el unico "fecha" final.
    if "fecha" in df.columns:
        df = df.drop(columns=["fecha"])

    df = df.rename(columns={"mes_clave": "fecha", "temperature_2m_mean": "temp_media_c",
                              "temperature_2m_min": "temp_min_c", "temperature_2m_max": "temp_max_c",
                              "precipitation_sum": "precipitacion_mm",
                              "et0_fao_evapotranspiration": "et0_mm"})

    # Garantia ultima de unicidad: si algun merge dejo columnas con sufijos
    # _x/_y o duplicados exactos, los colapsamos.
    if df.columns.duplicated().any():
        dups = df.columns[df.columns.duplicated()].tolist()
        print(f"   ! columnas duplicadas tras merge: {dups} - colapsando")
        df = df.loc[:, ~df.columns.duplicated()]

    print(f"   OK master con {len(df)} filas, {len(df.columns)} columnas")
    return df


# =============================================================================
# Feature engineering
# =============================================================================
def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """Lags, rolling, derivadas. Asume df ordenado por (cod_mun, fecha)."""
    print("\n[fe] calculando lags + rolling + derivadas ...")

    # Defensa: deduplicar columnas para evitar 'cannot assemble with duplicate keys'
    if df.columns.duplicated().any():
        dups = df.columns[df.columns.duplicated()].tolist()
        print(f"   ! deduplicando columnas: {dups}")
        df = df.loc[:, ~df.columns.duplicated()].copy()

    if "fecha" not in df.columns:
        print("   ! falta columna fecha; saltando FE")
        return df

    # df["fecha"] puede ser un DataFrame de 2 cols si hay duplicados aun;
    # tras el dedup anterior siempre debe ser una Serie, pero blindamos:
    serie_fecha = df["fecha"]
    if isinstance(serie_fecha, pd.DataFrame):
        serie_fecha = serie_fecha.iloc[:, 0]
    df["fecha"] = pd.to_datetime(serie_fecha, errors="coerce")
    df = df.dropna(subset=["fecha"]).copy()

    # Detectar identificador de municipio
    id_col = "cod_mun" if "cod_mun" in df.columns else "codigo_dane" if "codigo_dane" in df.columns else None
    if id_col is None:
        print("   ! sin id de municipio; saltando lags por grupo")
        df = df.sort_values("fecha")
    else:
        df = df.sort_values([id_col, "fecha"])

    # Variables a las que aplicamos lags
    cols_lag = [c for c in df.columns if any(k in c.lower() for k in
                ["temp_media", "precipitacion", "et0", "oni",
                 "precio_fnc", "precio_ico", "fred_coffee", "ndvi"])]

    # Aplicar lags
    for c in cols_lag:
        for lag in (1, 3, 6, 12):
            new = f"{c}_lag{lag}"
            if id_col:
                df[new] = df.groupby(id_col)[c].shift(lag)
            else:
                df[new] = df[c].shift(lag)

    # Rolling means
    for c in [x for x in cols_lag if "temp_media" in x.lower() or "precipitacion" in x.lower()]:
        for w in (3, 6, 12):
            new = f"{c}_ma{w}"
            if id_col:
                df[new] = df.groupby(id_col)[c].transform(lambda s: s.rolling(w, min_periods=1).mean())
            else:
                df[new] = df[c].rolling(w, min_periods=1).mean()

    # Derivadas
    if "precipitacion_mm" in df.columns and "et0_mm" in df.columns:
        df["estres_hidrico"] = (df["et0_mm"] - df["precipitacion_mm"]).clip(lower=0)
    if "temp_max_c" in df.columns and "temp_min_c" in df.columns:
        df["amplitud_termica"] = df["temp_max_c"] - df["temp_min_c"]

    # Dummies ENSO
    if "fase_enso" in df.columns:
        df["es_nino"]   = (df["fase_enso"] == "Nino").astype(int)
        df["es_nina"]   = (df["fase_enso"] == "Nina").astype(int)
    if "oni" in df.columns:
        df["enso_intensidad"] = df["oni"].abs().where(df["oni"].abs() > 0.5, 0)

    # Year/mes/cosecha
    df["anio"] = df["fecha"].dt.year
    df["mes"]  = df["fecha"].dt.month
    df["es_cosecha"] = df["mes"].isin([3, 4, 5, 6, 9, 10, 11, 12]).astype(int)

    print(f"   OK {len(df.columns)} columnas finales")
    return df


# =============================================================================
# Main
# =============================================================================
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--modo", choices=["auto", "bd", "csv"], default="auto")
    p.add_argument("--solo-cafeteros", action="store_true",
                    help="filtrar a departamentos cafeteros")
    args = p.parse_args()

    print("=" * 70)
    print(" ETL Master Municipal Mensual")
    print("=" * 70)

    df = None
    if args.modo in ("auto", "bd"):
        df = construir_desde_bd()
        if df is not None and len(df) > 0:
            print("\n[OK] usando datos de PostgreSQL")
    if df is None or len(df) == 0:
        if args.modo == "bd":
            print("\n[FAIL] modo BD forzado pero sin datos. Aborto.")
            sys.exit(1)
        print("\n[fallback] usando CSVs ...")
        df = construir_desde_csv()

    if df is None or len(df) == 0:
        print("\n[FAIL] no se pudo construir el master por ningún modo.")
        print("       Ejecuta antes:")
        print("       1. python 03_scripts/descarga/00_ejecutar_todo.py")
        print("       2. (opcional) cargar BD con 03_scripts/bd/")
        sys.exit(1)

    df = feature_engineering(df)

    # Filtrado opcional
    if args.solo_cafeteros and "departamento" in df.columns:
        before = len(df)
        df = df[df["departamento"].isin(DPTOS_CAFETEROS)]
        print(f"\n[filter] solo cafeteros: {before} -> {len(df)} filas")

    # Persistir
    out_mensual = DIR_OUT / "master_cafe_municipal_mensual.csv"
    df.to_csv(out_mensual, index=False)
    print(f"\n[save] {out_mensual.relative_to(PROJECT)}")
    print(f"       {len(df)} filas · {len(df.columns)} columnas")

    # Resumen anual (más útil para algunos modelos de rendimiento)
    if "anio" in df.columns:
        id_col = "cod_mun" if "cod_mun" in df.columns else "codigo_dane" if "codigo_dane" in df.columns else None
        keys = [k for k in (id_col, "municipio", "departamento", "anio") if k in df.columns]
        agg_dict = {}
        for c in df.select_dtypes(include="number").columns:
            if c in keys: continue
            agg_dict[c] = "mean"
        if keys and agg_dict:
            anual = df.groupby(keys, dropna=False).agg(agg_dict).reset_index()
            out_anual = DIR_OUT / "master_cafe_municipal_anual.csv"
            anual.to_csv(out_anual, index=False)
            print(f"\n[save] {out_anual.relative_to(PROJECT)}")
            print(f"       {len(anual)} filas · {len(anual.columns)} columnas")

    print("\nOK siguiente:")
    print("    cd 02_notebooks && jupyter notebook NB07_MLP_profundo.ipynb")


if __name__ == "__main__":
    main()
