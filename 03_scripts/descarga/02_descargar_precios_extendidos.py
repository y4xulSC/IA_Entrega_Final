"""
═══════════════════════════════════════════════════════════════════════════════
 02_descargar_precios_extendidos.py
═══════════════════════════════════════════════════════════════════════════════
 Descarga series de precios del café (mensual) desde 1990 hasta hoy:
   - FRED St. Louis Fed (Brasil + Robusta + Composite)
   - World Bank Pink Sheet (Arabica + Robusta)
   - IMF Primary Commodity (Coffee composite)
   - ICO Composite ampliado
   - BanRep TRM (USD/COP) y IPC

 RESUELVE: La 2da entrega solo tenía precios mensuales 2018-2025 (~84 obs).
 Esto explica el R²=−2.12 del LSTM (surge 2024-2025 fuera de distribución).
 Con esta extensión: 1990-2026 ≈ 432 observaciones para entrenar correctamente.

 Output:
   01_datos/enriquecidos/precios/
     fred_coffee_brazil.csv
     fred_coffee_robusta.csv
     world_bank_coffee.csv
     imf_coffee.csv
     banrep_trm_ipc.csv
     precios_consolidados_mensual.csv  (master de los anteriores)

 No requiere API key. Si tienes una FRED API key (gratis), exportala como
 FRED_API_KEY para usar la API oficial; si no, baja CSVs públicos.
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
from pathlib import Path
import os
import sys
import io
import time
from datetime import datetime

import requests
import pandas as pd

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
OUT_DIR = PROJECT_ROOT / "01_datos" / "enriquecidos" / "precios"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (UAO IA Cafe Project)"}


# ╔════════════════════════════════════════════════════════════════════════════
# ║ FRED — St. Louis Fed
# ╚════════════════════════════════════════════════════════════════════════════
FRED_SERIES = {
    "fred_coffee_brazil.csv": "PCOFFOTMUSDM",
    "fred_coffee_robusta.csv": "PCOFFROBUSDM",
}


def fred_csv(series_id: str) -> Optional[pd.DataFrame]:
    """Descarga una serie FRED como CSV directo (sin necesidad de API key)."""
    url = (f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
           f"&cosd=1990-01-01")
    try:
        r = requests.get(url, headers=UA, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["fecha", "valor"]
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        df = df.dropna()
        df["serie"] = series_id
        return df
    except Exception as e:
        print(f"   ✗ FRED {series_id}: {e}")
        return None


def descargar_fred() -> dict[str, pd.DataFrame]:
    print("\n[1/5] FRED — Café Brasil + Robusta (1990-presente) ...")
    out = {}
    for nombre, sid in FRED_SERIES.items():
        df = fred_csv(sid)
        if df is not None:
            df.to_csv(OUT_DIR / nombre, index=False)
            print(f"   ✓ {nombre}: {len(df)} obs")
            out[nombre] = df
        time.sleep(0.5)
    return out


# ╔════════════════════════════════════════════════════════════════════════════
# ║ World Bank Pink Sheet (Commodity Markets)
# ╚════════════════════════════════════════════════════════════════════════════
def descargar_world_bank() -> Optional[pd.DataFrame]:
    """
    Pink Sheet: precios mensuales de commodities desde 1960.
    Usamos el endpoint XLSX directo.
    """
    print("\n[2/5] World Bank — Pink Sheet Commodity ...")
    URL = ("https://thedocs.worldbank.org/en/doc/"
           "5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Monthly.xlsx")
    try:
        r = requests.get(URL, headers=UA, timeout=120)
        r.raise_for_status()
        # Leer hoja de precios mensuales
        try:
            df = pd.read_excel(io.BytesIO(r.content), sheet_name="Monthly Prices",
                               skiprows=4)
        except Exception:
            df = pd.read_excel(io.BytesIO(r.content), sheet_name=0, skiprows=4)
        df.columns = [str(c).strip() for c in df.columns]

        # Detectar columnas de café (varía por año)
        col_arabica = next((c for c in df.columns if "ARABICA" in c.upper() or
                            "Coffee, Arabic" in c), None)
        col_robusta = next((c for c in df.columns if "ROBUSTA" in c.upper() or
                            "Coffee, Robusta" in c), None)
        col_fecha = df.columns[0]
        cols = [col_fecha]
        if col_arabica: cols.append(col_arabica)
        if col_robusta: cols.append(col_robusta)
        df = df[cols].dropna(how="all")
        df.columns = ["fecha"] + (["arabica_usd_kg"] if col_arabica else []) + \
                     (["robusta_usd_kg"] if col_robusta else [])
        # Fecha en formato YYYYMMM
        df["fecha"] = pd.to_datetime(df["fecha"].astype(str).str.replace("M", "-"),
                                     errors="coerce")
        df = df.dropna(subset=["fecha"])
        df.to_csv(OUT_DIR / "world_bank_coffee.csv", index=False)
        print(f"   ✓ world_bank_coffee.csv: {len(df)} obs")
        return df
    except Exception as e:
        print(f"   ✗ World Bank: {e}")
        print("   Descarga manual: https://www.worldbank.org/en/research/commodity-markets")
        return None


# ╔════════════════════════════════════════════════════════════════════════════
# ║ IMF Primary Commodity
# ╚════════════════════════════════════════════════════════════════════════════
def descargar_imf() -> Optional[pd.DataFrame]:
    """IMF Coffee composite via DataMapper API o fallback CSV oficial."""
    print("\n[3/5] IMF — Primary Commodity (coffee) ...")
    # IMF SDMX endpoint
    URL = ("https://www.imf.org/external/np/res/commod/External_Data.xls")
    try:
        r = requests.get(URL, headers=UA, timeout=120)
        r.raise_for_status()
        try:
            df = pd.read_excel(io.BytesIO(r.content), sheet_name=0, skiprows=2)
        except Exception:
            df = pd.read_excel(io.BytesIO(r.content), sheet_name=0)
        # Buscar columnas de café
        col_coffee = [c for c in df.columns if "Coffee" in str(c)]
        if not col_coffee:
            print("   ⚠  Sin columnas Coffee en este sheet")
            return None
        df = df[[df.columns[0]] + col_coffee].dropna(how="all")
        df.to_csv(OUT_DIR / "imf_coffee.csv", index=False)
        print(f"   ✓ imf_coffee.csv: {len(df)} obs")
        return df
    except Exception as e:
        print(f"   ✗ IMF: {e}")
        return None


# ╔════════════════════════════════════════════════════════════════════════════
# ║ BanRep — TRM y IPC
# ╚════════════════════════════════════════════════════════════════════════════
def descargar_banrep() -> Optional[pd.DataFrame]:
    """TRM mensual (USD/COP) e IPC general desde 1990."""
    print("\n[4/5] BanRep — TRM e IPC ...")
    # BanRep no tiene API pública estable; usamos archivos del SRTM/datos.gov.co
    URL_TRM = ("https://www.banrep.gov.co/sites/default/files/paginas/"
               "Tasa_Cambio_TRM.csv")
    try:
        r = requests.get(URL_TRM, headers=UA, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text), sep=";")
        df.to_csv(OUT_DIR / "banrep_trm.csv", index=False)
        print(f"   ✓ banrep_trm.csv: {len(df)} obs")
        return df
    except Exception as e:
        print(f"   ✗ BanRep TRM: {e}")
        # Fallback: yfinance USDCOP
        try:
            import yfinance as yf
            ticker = yf.Ticker("USDCOP=X")
            hist = ticker.history(start="1990-01-01", interval="1mo")
            hist = hist[["Close"]].reset_index()
            hist.columns = ["fecha", "trm_cop_usd"]
            hist.to_csv(OUT_DIR / "banrep_trm.csv", index=False)
            print(f"   ✓ TRM fallback yfinance: {len(hist)} obs")
            return hist
        except Exception as e2:
            print(f"   ✗ Fallback yfinance: {e2}")
            return None


# ╔════════════════════════════════════════════════════════════════════════════
# ║ ICO Composite ampliado
# ╚════════════════════════════════════════════════════════════════════════════
def descargar_ico() -> Optional[pd.DataFrame]:
    """ICO composite indicator price desde 1990 (HTML scraping)."""
    print("\n[5/5] ICO — Composite indicator price (mensual) ...")
    URL = "https://www.ico.org/historical/1990%20onwards/PDF/3a-prices-monthly.pdf"
    # Alternativa simple: tabla pública en formato Excel
    URL_XLS = "https://www.ico.org/documents/ed-2354-historical-data.xlsx"
    for url in [URL_XLS]:
        try:
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            df = pd.read_excel(io.BytesIO(r.content), sheet_name=0)
            df.to_csv(OUT_DIR / "ico_composite_extended.csv", index=False)
            print(f"   ✓ ICO: {len(df)} obs")
            return df
        except Exception as e:
            print(f"   ✗ ICO via {url}: {e}")
    print("   Descarga manual: https://www.ico.org/coffee_prices.asp")
    return None


# ╔════════════════════════════════════════════════════════════════════════════
# ║ Consolidación
# ╚════════════════════════════════════════════════════════════════════════════
def consolidar(out_dir: Path) -> pd.DataFrame:
    """Une todos los archivos en un master mensual."""
    print("\n[consolidar] Uniendo todas las fuentes a frecuencia mensual ...")
    archivos = list(out_dir.glob("*.csv"))
    if not archivos:
        print("   ⚠  Sin archivos. Ejecuta las descargas primero.")
        return pd.DataFrame()

    master = None
    for f in archivos:
        try:
            df = pd.read_csv(f)
            if "fecha" not in df.columns:
                continue
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            df = df.dropna(subset=["fecha"]).copy()
            df["mes"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
            grouped = df.groupby("mes").mean(numeric_only=True).reset_index()
            grouped.columns = ["fecha"] + [f"{c}__{f.stem}" for c in grouped.columns[1:]]
            master = grouped if master is None else master.merge(
                grouped, on="fecha", how="outer")
        except Exception as e:
            print(f"   ⚠  {f.name}: {e}")

    if master is not None:
        master = master.sort_values("fecha").reset_index(drop=True)
        out_path = out_dir / "precios_consolidados_mensual.csv"
        master.to_csv(out_path, index=False)
        print(f"   ✓ {out_path.name}: {len(master)} meses ({master['fecha'].min().date()} → {master['fecha'].max().date()})")
        return master
    return pd.DataFrame()


def main():
    print("=" * 70)
    print(" Descarga de precios extendidos del café — Entrega Final")
    print("=" * 70)
    print(f"Salida: {OUT_DIR}")

    descargar_fred()
    descargar_world_bank()
    descargar_imf()
    descargar_banrep()
    descargar_ico()
    consolidar(OUT_DIR)

    print("\n✓ Listo. Siguiente: 03_descargar_clima_satelital.py")


from typing import Optional  # late import compatibility
if __name__ == "__main__":
    main()
