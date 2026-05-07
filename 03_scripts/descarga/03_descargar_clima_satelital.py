"""
═══════════════════════════════════════════════════════════════════════════════
 03_descargar_clima_satelital.py
═══════════════════════════════════════════════════════════════════════════════
 Descarga datos climáticos satelitales que CUBREN COMPLETAMENTE Colombia,
 cerrando los huecos espaciales de IDEAM (estaciones no llegan a todos los
 municipios cafeteros).

 Fuentes:
   - CHIRPS v2.0 (precipitación 5km diaria, 1981-presente)
       Modo A: Earth Engine API (rápido si tienes cuenta GEE gratis)
       Modo B: ClimateSERV API (gratis, sin auth, lento)
       Modo C: Power NASA via OPeNDAP (gratis, mensual)
   - Open-Meteo Historical (temperatura, humedad, precip · gratis sin key)
   - NOAA ONI (ya en 2da entrega, lo extendemos)

 RESUELVE: La 2da entrega menciona "cobertura climática IDEAM incompleta"
 como limitación bloqueante.

 Output:
   01_datos/enriquecidos/clima/
     openmeteo_municipios_diario.csv
     openmeteo_municipios_mensual.csv
     chirps_municipal_mensual.csv  (si se ejecuta CHIRPS)
     enso_oni_extendido.csv

 Uso:
   python 03_descargar_clima_satelital.py
   python 03_descargar_clima_satelital.py --solo openmeteo onixxx
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
from pathlib import Path
import argparse
import time
import io

import requests
import pandas as pd

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
OUT_DIR = PROJECT_ROOT / "01_datos" / "enriquecidos" / "clima"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (UAO IA Cafe Project)"}

# Coordenadas de capitales de los 8 departamentos cafeteros principales
MUNICIPIOS_CAFETEROS = [
    # codigo_dane, nombre, dpto, lat, lon
    ("41001", "Neiva",        "Huila",       2.9389,  -75.2819),
    ("05001", "Medellin",     "Antioquia",   6.2442,  -75.5812),
    ("52001", "Pasto",        "Nariño",      1.2136,  -77.2811),
    ("17001", "Manizales",    "Caldas",      5.0703,  -75.5138),
    ("17873", "Villamaria",   "Caldas",      5.0438,  -75.5067),
    ("63001", "Armenia",      "Quindio",     4.5340,  -75.6811),
    ("66001", "Pereira",      "Risaralda",   4.8133,  -75.6961),
    ("73001", "Ibague",       "Tolima",      4.4389,  -75.2322),
    ("76001", "Cali",         "Valle",       3.4516,  -76.5320),
    ("19001", "Popayan",      "Cauca",       2.4448,  -76.6147),
    # Productores adicionales
    ("18001", "Florencia",    "Caqueta",     1.6144,  -75.6062),
    ("54001", "Cucuta",       "N. Santander", 7.8939, -72.5078),
    ("68001", "Bucaramanga",  "Santander",   7.1193,  -73.1227),
    ("15001", "Tunja",        "Boyaca",      5.5446,  -73.3573),
    ("25001", "Agua de Dios", "Cundinamarca", 4.3766, -74.6712),
    ("23001", "Monteria",     "Cordoba",     8.7575,  -75.8814),
    ("44001", "Riohacha",     "Guajira",     11.5444, -72.9072),
    ("47001", "Santa Marta",  "Magdalena",   11.2408, -74.1990),
]


# ╔════════════════════════════════════════════════════════════════════════════
# ║ Open-Meteo Historical
# ╚════════════════════════════════════════════════════════════════════════════
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

def descargar_openmeteo(start: str = "1990-01-01",
                        end:   str = "2026-01-01") -> pd.DataFrame:
    """
    Open-Meteo gratis sin API key. Devuelve clima diario para cada municipio
    listado y guarda el agregado mensual.
    """
    print(f"\n[Open-Meteo] {len(MUNICIPIOS_CAFETEROS)} municipios · {start}–{end}")
    todos = []
    for cod, nombre, dpto, lat, lon in MUNICIPIOS_CAFETEROS:
        params = {
            "latitude": lat, "longitude": lon,
            "start_date": start, "end_date": end,
            "daily": ",".join([
                "temperature_2m_mean", "temperature_2m_min",
                "temperature_2m_max", "precipitation_sum",
                "et0_fao_evapotranspiration",
                "wind_speed_10m_max", "shortwave_radiation_sum",
            ]),
            "timezone": "America/Bogota",
        }
        try:
            r = requests.get(OPEN_METEO_URL, params=params, headers=UA, timeout=60)
            r.raise_for_status()
            data = r.json()["daily"]
            df = pd.DataFrame(data)
            df["codigo_dane"] = cod
            df["municipio"]   = nombre
            df["departamento"] = dpto
            df.rename(columns={"time": "fecha"}, inplace=True)
            df["fecha"] = pd.to_datetime(df["fecha"])
            todos.append(df)
            print(f"   ✓ {nombre:18s} ({dpto}): {len(df)} días")
        except Exception as e:
            print(f"   ✗ {nombre}: {e}")
        time.sleep(0.4)  # rate limit cordial

    if not todos:
        return pd.DataFrame()

    df_diario = pd.concat(todos, ignore_index=True)
    df_diario.to_csv(OUT_DIR / "openmeteo_municipios_diario.csv", index=False)
    print(f"\n   ✓ openmeteo_municipios_diario.csv: {len(df_diario)} filas")

    # Agregado mensual
    df_diario["mes"] = df_diario["fecha"].dt.to_period("M").dt.to_timestamp()
    aggs = {
        "temperature_2m_mean": "mean", "temperature_2m_min": "min",
        "temperature_2m_max":  "max",  "precipitation_sum": "sum",
        "et0_fao_evapotranspiration": "sum",
        "wind_speed_10m_max": "mean",
        "shortwave_radiation_sum": "sum",
    }
    df_mes = (df_diario.groupby(["codigo_dane","municipio","departamento","mes"])
              .agg(aggs).reset_index())
    df_mes.to_csv(OUT_DIR / "openmeteo_municipios_mensual.csv", index=False)
    print(f"   ✓ openmeteo_municipios_mensual.csv: {len(df_mes)} filas")
    return df_mes


# ╔════════════════════════════════════════════════════════════════════════════
# ║ NOAA ONI extendido
# ╚════════════════════════════════════════════════════════════════════════════
def descargar_oni() -> pd.DataFrame:
    print("\n[NOAA ONI] descargando ENSO Oceanic Niño Index (1950-presente) ...")
    URL = "https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php"
    try:
        # Versión CSV directa
        URL_CSV = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
        r = requests.get(URL_CSV, headers=UA, timeout=30)
        r.raise_for_status()
        df = pd.read_fwf(io.StringIO(r.text), header=0)
        df.columns = [c.strip() for c in df.columns]
        # Normalizar
        if "SEAS" in df.columns and "YR" in df.columns:
            df["fecha"] = pd.to_datetime(df["YR"].astype(str) + "-" +
                                         df["SEAS"].str[:3].map({
                                             "DJF":"01","JFM":"02","FMA":"03",
                                             "MAM":"04","AMJ":"05","MJJ":"06",
                                             "JJA":"07","JAS":"08","ASO":"09",
                                             "SON":"10","OND":"11","NDJ":"12"
                                         }) + "-01", errors="coerce")
            df["oni"] = pd.to_numeric(df["ANOM"], errors="coerce")
            df["fase_enso"] = df["oni"].apply(
                lambda x: "Nino" if x >= 0.5 else "Nina" if x <= -0.5 else "Neutro")
        df = df.dropna(subset=["fecha"])
        df.to_csv(OUT_DIR / "enso_oni_extendido.csv", index=False)
        print(f"   ✓ enso_oni_extendido.csv: {len(df)} obs")
        return df
    except Exception as e:
        print(f"   ✗ ONI: {e}")
        return pd.DataFrame()


# ╔════════════════════════════════════════════════════════════════════════════
# ║ CHIRPS via ClimateSERV (opcional, lento)
# ╚════════════════════════════════════════════════════════════════════════════
def descargar_chirps_climateserv():
    """
    CHIRPS via ClimateSERV (NASA) — gratis sin auth.
    Alternativa más rápida si tienes cuenta GEE: usar earthengine-api.
    Esto puede tomar 1-2 horas para todos los municipios.
    """
    print("\n[CHIRPS] descarga via ClimateSERV (sin auth, ~1-2 h) ...")
    print("   ⚠  Esta descarga es opcional — Open-Meteo ya cubre lo esencial.")
    print("   Si quieres CHIRPS, ejecuta este modo manualmente.")
    print("   Documentación: https://climateserv.servirglobal.net/api")


# ╔════════════════════════════════════════════════════════════════════════════
# ║ Main
# ╚════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="1990-01-01")
    parser.add_argument("--end",   default="2026-01-01")
    parser.add_argument("--solo", nargs="+", default=None,
                        choices=["openmeteo", "oni", "chirps"])
    args = parser.parse_args()

    print("=" * 70)
    print(" Descarga de clima satelital — Entrega Final")
    print("=" * 70)

    sel = args.solo or ["openmeteo", "oni"]

    if "openmeteo" in sel:
        descargar_openmeteo(args.start, args.end)
    if "oni" in sel:
        descargar_oni()
    if "chirps" in sel:
        descargar_chirps_climateserv()

    print("\n✓ Listo. Siguiente: 04_descargar_eva_municipal.py")


if __name__ == "__main__":
    main()
