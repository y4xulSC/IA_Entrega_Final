"""
===============================================================================
 03_descargar_clima_satelital.py
===============================================================================
 Descarga datos climaticos satelitales que CUBREN COMPLETAMENTE Colombia,
 cerrando los huecos espaciales de IDEAM.

 Fuentes:
   - Open-Meteo Historical (gratis sin key)
   - NOAA ONI (1950-presente)
   - CHIRPS via ClimateSERV (opcional, lento)

 v2 (2026-05-07): retry con backoff exponencial para 429, sleep adaptativo,
                  reintento de los municipios fallidos al final, exit(1) si
                  la descarga queda vacia.

 Output:
   01_datos/enriquecidos/clima/
     openmeteo_municipios_diario.csv
     openmeteo_municipios_mensual.csv
     enso_oni_extendido.csv
===============================================================================
"""
from __future__ import annotations
from pathlib import Path
import argparse
import io
import sys
import time

import requests
import pandas as pd

from _config import UA

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
OUT_DIR = PROJECT_ROOT / "01_datos" / "enriquecidos" / "clima"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MUNICIPIOS_CAFETEROS = [
    ("41001", "Neiva",        "Huila",       2.9389,  -75.2819),
    ("05001", "Medellin",     "Antioquia",   6.2442,  -75.5812),
    ("52001", "Pasto",        "Narino",      1.2136,  -77.2811),
    ("17001", "Manizales",    "Caldas",      5.0703,  -75.5138),
    ("17873", "Villamaria",   "Caldas",      5.0438,  -75.5067),
    ("63001", "Armenia",      "Quindio",     4.5340,  -75.6811),
    ("66001", "Pereira",      "Risaralda",   4.8133,  -75.6961),
    ("73001", "Ibague",       "Tolima",      4.4389,  -75.2322),
    ("76001", "Cali",         "Valle",       3.4516,  -76.5320),
    ("19001", "Popayan",      "Cauca",       2.4448,  -76.6147),
    ("18001", "Florencia",    "Caqueta",     1.6144,  -75.6062),
    ("54001", "Cucuta",       "N. Santander", 7.8939, -72.5078),
    ("68001", "Bucaramanga",  "Santander",   7.1193,  -73.1227),
    ("15001", "Tunja",        "Boyaca",      5.5446,  -73.3573),
    ("25001", "Agua de Dios", "Cundinamarca", 4.3766, -74.6712),
    ("23001", "Monteria",     "Cordoba",     8.7575,  -75.8814),
    ("44001", "Riohacha",     "Guajira",     11.5444, -72.9072),
    ("47001", "Santa Marta",  "Magdalena",   11.2408, -74.1990),
]


# Open-Meteo con retry/backoff
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARS = [
    "temperature_2m_mean", "temperature_2m_min", "temperature_2m_max",
    "precipitation_sum", "et0_fao_evapotranspiration",
    "wind_speed_10m_max", "shortwave_radiation_sum",
]


def _open_meteo_request(lat, lon, start, end,
                        max_attempts=5, timeout=90):
    """
    GET a Open-Meteo con retry exponencial.
    Devuelve el JSON o levanta excepcion si fallan todos los intentos.
    """
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "daily": ",".join(DAILY_VARS),
        "timezone": "America/Bogota",
    }
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.get(OPEN_METEO_URL, params=params,
                             headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 0)) or min(2 ** attempt * 5, 90)
                print("     - 429 esperando " + str(wait) + "s (intento " +
                      str(attempt) + "/" + str(max_attempts) + ")")
                time.sleep(wait)
                continue
            if 500 <= r.status_code < 600:
                wait = min(2 ** attempt, 60)
                print("     - " + str(r.status_code) + " esperando " + str(wait) + "s")
                time.sleep(wait)
                continue
            r.raise_for_status()
        except requests.exceptions.Timeout:
            wait = min(2 ** attempt, 60)
            print("     - timeout esperando " + str(wait) + "s")
            time.sleep(wait)
        except requests.exceptions.RequestException as e:
            last_exc = e
            wait = min(2 ** attempt, 60)
            print("     - " + type(e).__name__ + " esperando " + str(wait) + "s")
            time.sleep(wait)
    raise RuntimeError("agotados " + str(max_attempts) +
                       " intentos. Ultimo error: " + str(last_exc))


def descargar_openmeteo(start="1990-01-01", end="2026-01-01"):
    print("\n[Open-Meteo] " + str(len(MUNICIPIOS_CAFETEROS)) +
          " municipios . " + start + "-" + end)
    print("   (rate limit ~600/min . sleep adaptativo entre llamadas)")

    todos = []
    pendientes = []

    for cod, nombre, dpto, lat, lon in MUNICIPIOS_CAFETEROS:
        try:
            data = _open_meteo_request(lat, lon, start, end)
            df = pd.DataFrame(data["daily"])
            df["codigo_dane"] = cod
            df["municipio"] = nombre
            df["departamento"] = dpto
            df.rename(columns={"time": "fecha"}, inplace=True)
            df["fecha"] = pd.to_datetime(df["fecha"])
            todos.append(df)
            print("   OK " + nombre.ljust(18) + " (" + dpto + "): " +
                  str(len(df)) + " dias")
        except Exception as e:
            print("   FAIL " + nombre + ": " + str(e))
            pendientes.append((cod, nombre, dpto, lat, lon))
        time.sleep(2.5)

    if pendientes:
        print("\n[Open-Meteo] reintentando " + str(len(pendientes)) +
              " municipio(s) tras pausa de 60s ...")
        time.sleep(60)
        rezagados = []
        for cod, nombre, dpto, lat, lon in pendientes:
            try:
                data = _open_meteo_request(lat, lon, start, end, max_attempts=7)
                df = pd.DataFrame(data["daily"])
                df["codigo_dane"] = cod
                df["municipio"] = nombre
                df["departamento"] = dpto
                df.rename(columns={"time": "fecha"}, inplace=True)
                df["fecha"] = pd.to_datetime(df["fecha"])
                todos.append(df)
                print("   OK " + nombre.ljust(18) + " (" + dpto + "): " +
                      str(len(df)) + " dias (reintento)")
            except Exception as e:
                print("   FAIL " + nombre + " (reintento final): " + str(e))
                rezagados.append(nombre)
            time.sleep(4.0)
        if rezagados:
            print("\n   WARN Quedaron sin descargar: " + ", ".join(rezagados))

    if not todos:
        print("   FAIL Open-Meteo: ningun municipio se descargo")
        return pd.DataFrame()

    df_diario = pd.concat(todos, ignore_index=True)
    df_diario.to_csv(OUT_DIR / "openmeteo_municipios_diario.csv", index=False)
    print("\n   OK openmeteo_municipios_diario.csv: " + str(len(df_diario)) +
          " filas (" + str(df_diario['municipio'].nunique()) + " municipios)")

    df_diario["mes"] = df_diario["fecha"].dt.to_period("M").dt.to_timestamp()
    aggs = {
        "temperature_2m_mean": "mean", "temperature_2m_min": "min",
        "temperature_2m_max":  "max",  "precipitation_sum": "sum",
        "et0_fao_evapotranspiration": "sum",
        "wind_speed_10m_max": "mean",
        "shortwave_radiation_sum": "sum",
    }
    df_mes = (df_diario.groupby(["codigo_dane", "municipio", "departamento", "mes"])
              .agg(aggs).reset_index())
    df_mes.to_csv(OUT_DIR / "openmeteo_municipios_mensual.csv", index=False)
    print("   OK openmeteo_municipios_mensual.csv: " + str(len(df_mes)) + " filas")
    return df_mes


# NOAA ONI
def descargar_oni():
    print("\n[NOAA ONI] descargando ENSO Oceanic Nino Index (1950-presente) ...")
    URL_CSV = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
    try:
        r = requests.get(URL_CSV, headers=UA, timeout=30)
        r.raise_for_status()
        df = pd.read_fwf(io.StringIO(r.text), header=0)
        df.columns = [c.strip() for c in df.columns]
        if "SEAS" in df.columns and "YR" in df.columns:
            mes_map = {"DJF": "01", "JFM": "02", "FMA": "03",
                       "MAM": "04", "AMJ": "05", "MJJ": "06",
                       "JJA": "07", "JAS": "08", "ASO": "09",
                       "SON": "10", "OND": "11", "NDJ": "12"}
            df["fecha"] = pd.to_datetime(
                df["YR"].astype(str) + "-" +
                df["SEAS"].str[:3].map(mes_map) + "-01",
                errors="coerce")
            df["oni"] = pd.to_numeric(df["ANOM"], errors="coerce")
            df["fase_enso"] = df["oni"].apply(
                lambda x: "Nino" if x >= 0.5 else "Nina" if x <= -0.5 else "Neutro")
        df = df.dropna(subset=["fecha"])
        df.to_csv(OUT_DIR / "enso_oni_extendido.csv", index=False)
        print("   OK enso_oni_extendido.csv: " + str(len(df)) + " obs")
        return df
    except Exception as e:
        print("   FAIL ONI: " + str(e))
        return pd.DataFrame()


def descargar_chirps_climateserv():
    print("\n[CHIRPS] descarga via ClimateSERV (sin auth, ~1-2 h) ...")
    print("   WARN Esta descarga es opcional - Open-Meteo ya cubre lo esencial.")
    print("   Documentacion: https://climateserv.servirglobal.net/api")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="1990-01-01")
    parser.add_argument("--end",   default="2026-01-01")
    parser.add_argument("--solo", nargs="+", default=None,
                        choices=["openmeteo", "oni", "chirps"])
    args = parser.parse_args()

    print("=" * 70)
    print(" Descarga de clima satelital - Entrega Final")
    print("=" * 70)

    sel = args.solo or ["openmeteo", "oni"]

    df_om = pd.DataFrame()
    if "openmeteo" in sel:
        df_om = descargar_openmeteo(args.start, args.end)
    df_oni = pd.DataFrame()
    if "oni" in sel:
        df_oni = descargar_oni()
    if "chirps" in sel:
        descargar_chirps_climateserv()

    todo_ok = True
    if "openmeteo" in sel and df_om.empty:
        print("\nFAIL Open-Meteo no produjo datos.")
        todo_ok = False
    if "oni" in sel and df_oni.empty:
        print("\nFAIL NOAA ONI no produjo datos.")
        todo_ok = False

    if not todo_ok:
        return 1

    if "openmeteo" in sel:
        n_mun = df_om["municipio"].nunique() if not df_om.empty else 0
        if n_mun < len(MUNICIPIOS_CAFETEROS):
            print("\nWARN Open-Meteo cubrio " + str(n_mun) + "/" +
                  str(len(MUNICIPIOS_CAFETEROS)) +
                  " municipios. Considera reejecutar el script.")

    print("\nOK Listo. Siguiente: 04_descargar_eva_municipal.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
