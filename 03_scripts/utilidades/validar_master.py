"""
===============================================================================
 validar_master.py
===============================================================================
 Sanity check del archivo procesado:
   01_datos/procesados/master_cafe_municipal_mensual.csv

 Reporta:
   - Cobertura temporal y geografica
   - Nulos por columna
   - Distribucion del target (rendimiento_ton_ha)
   - Coherencia de joins (precios, ENSO, EVA, DEM, suelos)
   - Posibles outliers en variables clave

 No corrige, solo reporta. Usar antes de cargar a la BD o entrenar modelos.

 Uso:
   python validar_master.py
   python validar_master.py --anual    # validar tambien el archivo anual
===============================================================================
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve()
PROJECT = HERE.parents[2]
DIR_PROC = PROJECT / "01_datos" / "procesados"


def fila(label, valor, ancho=40):
    print("  " + str(label).ljust(ancho) + " : " + str(valor))


def seccion(titulo):
    print("\n" + "=" * 70)
    print(" " + titulo)
    print("=" * 70)


def reportar(df: pd.DataFrame, nombre: str):
    seccion(f"VALIDACION - {nombre}")
    fila("filas", f"{len(df):,}")
    fila("columnas", len(df.columns))
    fila("tamaño memoria", f"{df.memory_usage(deep=True).sum()/1e6:.1f} MB")

    # Cobertura temporal
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        fila("rango fechas", f"{df['fecha'].min().date()} -> {df['fecha'].max().date()}")
        fila("años distintos", df["fecha"].dt.year.nunique())
    if "anio" in df.columns:
        fila("años distintos (anio)", df["anio"].nunique())
        fila("rango anio", f"{int(df['anio'].min())} -> {int(df['anio'].max())}")

    # Cobertura geografica
    if "codigo_dane" in df.columns:
        fila("municipios distintos", df["codigo_dane"].nunique())
    if "departamento" in df.columns:
        fila("departamentos distintos", df["departamento"].nunique())
        top_dpto = df["departamento"].value_counts().head(5).to_dict()
        print(f"\n  Top 5 departamentos por filas:")
        for d, n in top_dpto.items():
            print(f"    {d}: {n:,}")

    # Nulos por bloque
    print("\n  Nulos por categoria de columna:")
    bloques = {
        "clima":     [c for c in df.columns if any(k in c.lower() for k in ["temp", "precip", "et0", "humedad", "viento", "radiacion", "ndvi"])],
        "precio":    [c for c in df.columns if "precio" in c.lower() or "fred" in c.lower() or "trm" in c.lower() or "ico" in c.lower() or "wb_" in c.lower() or "imf" in c.lower()],
        "enso":      [c for c in df.columns if "oni" in c.lower() or "fase" in c.lower() or "nino" in c.lower() or "nina" in c.lower() or "enso" in c.lower()],
        "produccion":[c for c in df.columns if any(k in c.lower() for k in ["produccion", "rendimiento", "area_sembrada", "area_cosechada"])],
        "geografia": [c for c in df.columns if any(k in c.lower() for k in ["altitud", "lat", "lon", "ph", "soc", "clay", "sand", "cec"])],
    }
    for bloque, cols in bloques.items():
        cols = [c for c in cols if c in df.columns]
        if not cols:
            continue
        nulos = df[cols].isna().sum().sum()
        total = len(df) * len(cols)
        pct = nulos / total * 100 if total else 0
        print(f"    {bloque:11s} : {len(cols):3d} cols · {nulos:>9,} nulos / {total:>9,} ({pct:5.1f}%)")

    # Target principal
    if "rendimiento_ton_ha" in df.columns:
        s = df["rendimiento_ton_ha"].dropna()
        print(f"\n  Target rendimiento_ton_ha:")
        if len(s) > 0:
            fila("    no-nulos", f"{len(s):,} ({len(s)/len(df)*100:.1f}%)")
            fila("    min / max", f"{s.min():.4f} / {s.max():.4f}")
            fila("    mediana / media", f"{s.median():.4f} / {s.mean():.4f}")
            # Outliers IQR
            q1, q3 = s.quantile([0.25, 0.75])
            iqr = q3 - q1
            n_out = ((s < q1 - 1.5*iqr) | (s > q3 + 1.5*iqr)).sum()
            fila("    outliers IQR", f"{n_out} ({n_out/len(s)*100:.1f}%)")
        else:
            print("    ! sin datos no-nulos")

    # Plausibilidad fisica
    print("\n  Plausibilidad fisica:")
    if "temp_media_c" in df.columns:
        s = df["temp_media_c"].dropna()
        if len(s):
            n_raros = ((s < -5) | (s > 45)).sum()
            fila("    temperatura fuera [-5,45]°C", f"{n_raros}")
    if "precipitacion_mm" in df.columns:
        s = df["precipitacion_mm"].dropna()
        if len(s):
            n_raros = (s < 0).sum()
            fila("    precipitacion negativa", f"{n_raros}")
    if "altitud_msnm" in df.columns:
        s = df["altitud_msnm"].dropna()
        if len(s):
            n_raros = ((s < 0) | (s > 4500)).sum()
            fila("    altitud fuera [0,4500] msnm", f"{n_raros}")
    if "rendimiento_ton_ha" in df.columns:
        s = df["rendimiento_ton_ha"].dropna()
        if len(s):
            n_raros = (s < 0).sum() + (s > 10).sum()
            fila("    rendimiento fuera [0,10] ton/ha", f"{n_raros}")

    # Joins entre bloques
    print("\n  Coherencia de joins:")
    if "fecha" in df.columns and "oni" in df.columns:
        cobertura = df.groupby(df["fecha"].dt.year)["oni"].apply(lambda s: s.notna().mean())
        anios_sin_enso = cobertura[cobertura < 0.5].index.tolist()
        fila("    años con <50% ENSO", f"{anios_sin_enso}" if anios_sin_enso else "ninguno")

    if "rendimiento_ton_ha" in df.columns and "anio" in df.columns:
        cobertura = df.groupby("anio")["rendimiento_ton_ha"].apply(lambda s: s.notna().sum())
        print(f"\n  Cobertura del target por año (top y bottom):")
        print(cobertura.sort_values().head(3).to_string())
        print("  ...")
        print(cobertura.sort_values().tail(3).to_string())

    # Duplicados
    print("\n  Duplicados:")
    if "fecha" in df.columns and "codigo_dane" in df.columns:
        n_dup = df.duplicated(subset=["fecha", "codigo_dane"]).sum()
        fila("    (fecha, codigo_dane) duplicados", n_dup)
    if df.columns.duplicated().any():
        fila("    columnas duplicadas", df.columns[df.columns.duplicated()].tolist())

    # Resumen final
    print("\n  Estado:")
    advertencias = []
    if "rendimiento_ton_ha" in df.columns:
        cob = df["rendimiento_ton_ha"].notna().mean()
        if cob < 0.05:
            advertencias.append(f"target casi vacio ({cob*100:.1f}% no-nulo)")
    if "oni" in df.columns:
        cob = df["oni"].notna().mean()
        if cob < 0.5:
            advertencias.append(f"ENSO con baja cobertura ({cob*100:.1f}%)")
    if "precio_fnc_cop_125kg" in df.columns:
        cob = df["precio_fnc_cop_125kg"].notna().mean()
        if cob < 0.5:
            advertencias.append(f"precio FNC con baja cobertura ({cob*100:.1f}%)")

    if advertencias:
        for w in advertencias:
            print(f"    WARN {w}")
    else:
        print("    OK sin advertencias mayores")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anual", action="store_true", help="incluir master anual")
    args = ap.parse_args()

    mensual = DIR_PROC / "master_cafe_municipal_mensual.csv"
    if not mensual.exists():
        print(f"FAIL no existe {mensual}")
        print("Ejecuta antes: python construir_master_municipal.py")
        sys.exit(1)

    df_m = pd.read_csv(mensual)
    reportar(df_m, "master_cafe_municipal_mensual.csv")

    if args.anual:
        anual = DIR_PROC / "master_cafe_municipal_anual.csv"
        if anual.exists():
            df_a = pd.read_csv(anual)
            reportar(df_a, "master_cafe_municipal_anual.csv")

    print("\n" + "=" * 70)
    print(" Validacion completa.")
    print("=" * 70)


if __name__ == "__main__":
    main()
