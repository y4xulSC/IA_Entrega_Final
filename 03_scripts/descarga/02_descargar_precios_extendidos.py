"""
===============================================================================
 02_descargar_precios_extendidos.py
===============================================================================
 Descarga series de precios del cafe (mensual) desde 1990 hasta hoy:
   - FRED St. Louis Fed (Brasil + Robusta)  - con API key
   - World Bank Pink Sheet (Arabica + Robusta)
   - IMF Primary Commodity (DataMapper API)
   - ICO Composite ampliado (con descubrimiento dinamico de XLS)
   - BanRep TRM (USD/COP) - yfinance como fuente primaria

 RESUELVE: La 2da entrega solo tenia precios mensuales 2018-2025.
 Con esta extension: 1990-2026 ~= 432 obs.

 v2 (2026-05-07): URLs actualizadas, FRED API key oficial, IMF DataMapper,
                  yfinance como fallback primario para TRM, ICO con scraping.

 Output:
   01_datos/enriquecidos/precios/
     fred_coffee_brazil.csv
     fred_coffee_robusta.csv
     world_bank_coffee.csv
     imf_coffee.csv
     banrep_trm.csv
     ico_composite_extended.csv
     precios_consolidados_mensual.csv
===============================================================================
"""
from __future__ import annotations
from pathlib import Path
import io
import re
import sys
import time

import requests
import pandas as pd

from _config import UA, FRED_API_KEY

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
OUT_DIR = PROJECT_ROOT / "01_datos" / "enriquecidos" / "precios"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# FRED
FRED_SERIES = {
    "fred_coffee_brazil.csv":  "PCOFFOTMUSDM",   # Other Mild Arabicas
    "fred_coffee_robusta.csv": "PCOFFROBUSDM",   # Robusta
}


def fred_csv(series_id):
    """
    Descarga una serie FRED. Si hay FRED_API_KEY usa la API JSON,
    si no cae al CSV publico de fredgraph.
    """
    if FRED_API_KEY:
        url = ("https://api.stlouisfed.org/fred/series/observations"
               "?series_id=" + series_id +
               "&api_key=" + FRED_API_KEY +
               "&file_type=json&observation_start=1990-01-01")
        try:
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            obs = r.json().get("observations", [])
            if obs:
                df = pd.DataFrame(obs)[["date", "value"]]
                df.columns = ["fecha", "valor"]
                df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
                df["valor"] = pd.to_numeric(df["valor"].replace(".", None),
                                            errors="coerce")
                df = df.dropna()
                df["serie"] = series_id
                return df
        except Exception as e:
            print("   WARN FRED API " + series_id + ": " + str(e) + " - fallback CSV")

    url = ("https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series_id +
           "&cosd=1990-01-01")
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
        print("   FAIL FRED " + series_id + ": " + str(e))
        return None


def descargar_fred():
    fuente = "API key oficial" if FRED_API_KEY else "CSV publico"
    print("\n[1/5] FRED - Cafe Brasil + Robusta (1990-presente, " + fuente + ")")
    out = {}
    for nombre, sid in FRED_SERIES.items():
        df = fred_csv(sid)
        if df is not None:
            df.to_csv(OUT_DIR / nombre, index=False)
            print("   OK " + nombre + ": " + str(len(df)) + " obs")
            out[nombre] = df
        time.sleep(0.5)
    return out


# World Bank Pink Sheet
def descargar_world_bank():
    print("\n[2/5] World Bank - Pink Sheet Commodity ...")
    URL = ("https://thedocs.worldbank.org/en/doc/"
           "5d903e848db1d1b83e0ec8f744e55570-0350012021/related/"
           "CMO-Historical-Data-Monthly.xlsx")
    try:
        r = requests.get(URL, headers=UA, timeout=120)
        r.raise_for_status()
        try:
            df = pd.read_excel(io.BytesIO(r.content),
                               sheet_name="Monthly Prices", skiprows=4)
        except Exception:
            df = pd.read_excel(io.BytesIO(r.content), sheet_name=0, skiprows=4)
        df.columns = [str(c).strip() for c in df.columns]

        col_arabica = next((c for c in df.columns
                            if "ARABICA" in c.upper() or "Coffee, Arabic" in c), None)
        col_robusta = next((c for c in df.columns
                            if "ROBUSTA" in c.upper() or "Coffee, Robusta" in c), None)
        col_fecha = df.columns[0]
        cols = [col_fecha]
        if col_arabica:
            cols.append(col_arabica)
        if col_robusta:
            cols.append(col_robusta)
        df = df[cols].dropna(how="all")
        nuevos = ["fecha"]
        if col_arabica:
            nuevos.append("arabica_usd_kg")
        if col_robusta:
            nuevos.append("robusta_usd_kg")
        df.columns = nuevos
        df["fecha"] = pd.to_datetime(df["fecha"].astype(str).str.replace("M", "-"),
                                     errors="coerce")
        df = df.dropna(subset=["fecha"])
        df.to_csv(OUT_DIR / "world_bank_coffee.csv", index=False)
        print("   OK world_bank_coffee.csv: " + str(len(df)) + " obs")
        return df
    except Exception as e:
        print("   FAIL World Bank: " + str(e))
        return None


# IMF DataMapper
def descargar_imf():
    """IMF Primary Commodity Prices via DataMapper API."""
    print("\n[3/5] IMF - Primary Commodity (DataMapper API) ...")
    INDICADORES = {
        "PCOFFOTM_USD": "Coffee Other Mild Arabicas (USD/lb)",
        "PCOFFROB_USD": "Coffee Robusta (USD/lb)",
    }
    frames = []
    for ind, label in INDICADORES.items():
        url = "https://www.imf.org/external/datamapper/api/v1/" + ind
        try:
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            data = r.json().get("values", {}).get(ind, {})
            for region, anios in data.items():
                for anio, val in anios.items():
                    frames.append({"fecha": str(anio) + "-01-01",
                                   "indicador": ind,
                                   "valor": val,
                                   "region": region})
        except Exception as e:
            print("   WARN IMF " + ind + ": " + str(e))

    if not frames:
        print("   WARN DataMapper sin datos - intentando fallback XLS ...")
        for url_xls in [
            "https://www.imf.org/-/media/Files/Research/CommodityPrices/Monthly/external-data.ashx",
            "https://www.imf.org/external/np/res/commod/External_Data.xls",
        ]:
            try:
                r = requests.get(url_xls, headers=UA, timeout=120)
                r.raise_for_status()
                df = pd.read_excel(io.BytesIO(r.content), sheet_name=0)
                df.to_csv(OUT_DIR / "imf_coffee.csv", index=False)
                print("   OK imf_coffee.csv (XLS): " + str(len(df)) + " obs")
                return df
            except Exception as e:
                print("   FAIL XLS " + url_xls + ": " + str(e))
        return None

    df = pd.DataFrame(frames)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.dropna(subset=["valor"])
    df.to_csv(OUT_DIR / "imf_coffee.csv", index=False)
    print("   OK imf_coffee.csv: " + str(len(df)) + " obs (anual desde DataMapper)")
    return df


# BanRep TRM (yfinance primario)
def descargar_banrep():
    """TRM mensual (USD/COP). Primario yfinance, fallback FRED DEXCOUS."""
    print("\n[4/5] BanRep TRM (USD/COP) - primario yfinance ...")
    try:
        import yfinance as yf
        ticker = yf.Ticker("USDCOP=X")
        hist = ticker.history(start="1990-01-01", interval="1mo",
                              auto_adjust=False)
        if not hist.empty:
            hist = hist[["Close"]].reset_index()
            hist.columns = ["fecha", "trm_cop_usd"]
            hist["fecha"] = pd.to_datetime(hist["fecha"]).dt.tz_localize(None)
            hist.to_csv(OUT_DIR / "banrep_trm.csv", index=False)
            print("   OK banrep_trm.csv (yfinance): " + str(len(hist)) + " obs")
            return hist
    except ImportError:
        print("   WARN yfinance no instalado (pip install yfinance)")
    except Exception as e:
        print("   WARN yfinance: " + str(e))

    print("   intentando FRED DEXCOUS como fallback ...")
    df = fred_csv("DEXCOUS")
    if df is not None and not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"])
        df_mensual = (df.set_index("fecha")["valor"]
                      .resample("MS").mean().dropna().reset_index())
        df_mensual.columns = ["fecha", "trm_cop_usd"]
        df_mensual.to_csv(OUT_DIR / "banrep_trm.csv", index=False)
        print("   OK banrep_trm.csv (FRED DEXCOUS): " + str(len(df_mensual)) + " obs")
        return df_mensual

    URL_TRM = ("https://www.banrep.gov.co/sites/default/files/paginas/"
               "Tasa_Cambio_TRM.csv")
    try:
        r = requests.get(URL_TRM, headers=UA, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text), sep=";")
        df.to_csv(OUT_DIR / "banrep_trm.csv", index=False)
        print("   OK banrep_trm.csv (BanRep): " + str(len(df)) + " obs")
        return df
    except Exception as e:
        print("   FAIL BanRep: " + str(e))
    return None


# ICO
def descargar_ico():
    """Descubre dinamicamente XLS en ico.org."""
    print("\n[5/5] ICO - Composite indicator price ...")
    candidatas = []

    # Headers de browser real para esquivar 404 del CDN cuando ven UA "python"
    BROWSER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    page_urls = [
        "https://www.ico.org/coffee_prices.asp",
        "https://ico.org/coffee_prices.asp",
    ]
    encontrados = []
    for page_url in page_urls:
        try:
            r = requests.get(page_url, headers=BROWSER_HEADERS, timeout=60,
                             allow_redirects=True)
            if r.status_code == 200:
                encontrados = re.findall(r'href="([^"]+\.xlsx)"', r.text)
                if encontrados:
                    break
            else:
                print("   WARN scraping ICO: " + page_url +
                      " status " + str(r.status_code))
        except Exception as e:
            print("   WARN scraping ICO: " + page_url + " " + str(e))
    for href in encontrados:
        if href.startswith("http"):
            candidatas.append(href)
        else:
            prefix = "https://www.ico.org"
            if not href.startswith("/"):
                prefix += "/"
            candidatas.append(prefix + href)

    for ed in range(2300, 2400):
        candidatas.append("https://www.ico.org/documents/cy2024-25/ed-" + str(ed) +
                          "-historical-data.xlsx")
        candidatas.append("https://www.ico.org/documents/ed-" + str(ed) +
                          "-historical-data.xlsx")

    vistos = set()
    candidatas_unicas = []
    for u in candidatas:
        if u not in vistos:
            vistos.add(u)
            candidatas_unicas.append(u)

    for url in candidatas_unicas[:20]:
        try:
            r = requests.get(url, headers=BROWSER_HEADERS, timeout=60,
                             allow_redirects=True)
            r.raise_for_status()
            ctype = r.headers.get("Content-Type", "").lower()
            if "html" in ctype or len(r.content) < 5000:
                continue
            df = pd.read_excel(io.BytesIO(r.content), sheet_name=0)
            if df.empty:
                continue
            # Asegurar columna 'fecha' para que entre al consolidado
            if "fecha" not in df.columns and df.shape[1] >= 1:
                df = df.rename(columns={df.columns[0]: "fecha"})
                df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
                df = df.dropna(subset=["fecha"])
            df.to_csv(OUT_DIR / "ico_composite_extended.csv", index=False)
            print("   OK ICO desde " + url + ": " + str(len(df)) + " filas")
            return df
        except Exception:
            continue

    print("   FAIL No se encontro XLS de ICO disponible")
    print("   Descarga manual: https://www.ico.org/coffee_prices.asp")
    return None


# Consolidacion
ORIG_PRECIOS_DIR = PROJECT_ROOT / "01_datos" / "originales" / "precios"


def consolidar(out_dir):
    """
    Une todas las fuentes a frecuencia mensual.

    Lee CSVs de DOS carpetas:
      1. enriquecidos/precios/   (este out_dir, generado por scripts)
      2. originales/precios/     (manuales del usuario / 2da entrega)

    Si una columna existe en ambos, los valores se promedian por mes
    (merge outer + groupby). Esto permite que tu ICO descargado a mano
    enriquezca el master sin pisar los datos automaticos.
    """
    print("\n[consolidar] Uniendo fuentes (enriquecidos/ + originales/) a mensual ...")
    archivos = [f for f in out_dir.glob("*.csv")
                if f.name != "precios_consolidados_mensual.csv"]
    if ORIG_PRECIOS_DIR.exists():
        manuales = [f for f in ORIG_PRECIOS_DIR.glob("*.csv")]
        if manuales:
            print("   incluyendo " + str(len(manuales)) +
                  " archivo(s) manual(es) de originales/precios/:")
            for m in manuales:
                print("     - " + m.name)
        archivos += manuales

    if not archivos:
        print("   WARN Sin archivos. Ejecuta las descargas primero.")
        return pd.DataFrame()

    master = None
    for f in archivos:
        try:
            df = pd.read_csv(f)
            if "fecha" not in df.columns:
                # Intentar detectar columna de fecha alternativa
                for cand in ["date", "Date", "FECHA", "month", "mes"]:
                    if cand in df.columns:
                        df = df.rename(columns={cand: "fecha"})
                        break
            if "fecha" not in df.columns:
                print("   WARN " + f.name + ": sin columna 'fecha', omitido")
                continue
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            df = df.dropna(subset=["fecha"]).copy()
            df["mes"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
            grouped = df.groupby("mes").mean(numeric_only=True).reset_index()
            # Prefijar con 'orig_' si viene de originales/, para distinguir
            prefijo = "orig_" if str(f).startswith(str(ORIG_PRECIOS_DIR)) else ""
            grouped.columns = ["fecha"] + [prefijo + str(c) + "__" + f.stem
                                            for c in grouped.columns[1:]]
            master = grouped if master is None else master.merge(
                grouped, on="fecha", how="outer")
        except Exception as e:
            print("   WARN " + f.name + ": " + str(e))

    if master is not None:
        master = master.sort_values("fecha").reset_index(drop=True)
        out_path = out_dir / "precios_consolidados_mensual.csv"
        master.to_csv(out_path, index=False)
        print("   OK " + out_path.name + ": " + str(len(master)) + " meses (" +
              str(master['fecha'].min().date()) + " -> " +
              str(master['fecha'].max().date()) + ")")
        return master
    return pd.DataFrame()


def main():
    print("=" * 70)
    print(" Descarga de precios extendidos del cafe - Entrega Final")
    print("=" * 70)
    print("Salida: " + str(OUT_DIR))

    res = {
        "fred":   bool(descargar_fred()),
        "wb":     descargar_world_bank() is not None,
        "imf":    descargar_imf() is not None,
        "banrep": descargar_banrep() is not None,
        "ico":    descargar_ico() is not None,
    }
    master = consolidar(OUT_DIR)

    n_ok = sum(res.values())
    print("\n  fuentes OK: " + str(n_ok) + "/" + str(len(res)) + "  -> " + str(res))
    print("\nOK Listo. Siguiente: 03_descargar_clima_satelital.py")

    if n_ok < 2 or master.empty:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
