"""
═══════════════════════════════════════════════════════════════════════════════
 05_descargar_dem_suelos.py
═══════════════════════════════════════════════════════════════════════════════
 Descarga variables agronómicas faltantes (mencionadas como limitación crítica
 en la 2da entrega):
   - Altitud media municipal (DEM SRTM 30m vía Open-Elevation API)
   - pH y materia orgánica del suelo (SoilGrids 250m API REST)

 RESUELVE: La 2da entrega lista entre las "mejoras propuestas" la integración
 de DEM (altitud) y suelos IGAC. Esto está reflejado en el documento como
 trabajo futuro pero no se implementó. Lo implementamos aquí.

 Fuentes (todas gratis sin auth):
   - Open-Elevation: https://api.open-elevation.com (datos SRTM)
   - SoilGrids ISRIC: https://rest.isric.org/soilgrids/v2.0/

 Output:
   01_datos/enriquecidos/geografia/
     dem_municipal_altitud.csv
     soilgrids_municipal.csv

 Nota: Para escala de PROYECTO (validar en 18 capitales cafeteras) está
 perfecto. Para escala MUNICIPAL completa (1100+ municipios) recomendamos
 usar archivos shapefile DIVIPOLA + raster SRTM en local con rasterio.
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
from pathlib import Path
import time
import requests
import pandas as pd

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
OUT_DIR = PROJECT_ROOT / "01_datos" / "enriquecidos" / "geografia"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (UAO IA Cafe Project)"}

# Mismas coordenadas que script 03 (compartido)
MUNICIPIOS_CAFETEROS = [
    ("41001", "Neiva",        "Huila",       2.9389,  -75.2819),
    ("05001", "Medellin",     "Antioquia",   6.2442,  -75.5812),
    ("52001", "Pasto",        "Nariño",      1.2136,  -77.2811),
    ("17001", "Manizales",    "Caldas",      5.0703,  -75.5138),
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
    # Adicionales emblemáticos de zona cafetera
    ("17873", "Villamaria",   "Caldas",      5.0438,  -75.5067),
    ("63594", "Salento",      "Quindio",     4.6371,  -75.5705),
    ("17653", "Salamina",     "Caldas",      5.4072,  -75.4868),
    ("17442", "Marsella",     "Risaralda",   4.9352,  -75.7398),
]


# ╔════════════════════════════════════════════════════════════════════════════
# ║ Open-Elevation API
# ╚════════════════════════════════════════════════════════════════════════════
def consultar_altitud(lat: float, lon: float) -> float | None:
    URL = "https://api.open-elevation.com/api/v1/lookup"
    try:
        r = requests.get(URL, params={"locations": f"{lat},{lon}"},
                         headers=UA, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data["results"][0]["elevation"]
    except Exception:
        return None


def descargar_altitudes() -> pd.DataFrame:
    print("\n[DEM] consultando altitud SRTM via Open-Elevation ...")
    rows = []
    for cod, nombre, dpto, lat, lon in MUNICIPIOS_CAFETEROS:
        alt = consultar_altitud(lat, lon)
        if alt is None:
            # Fallback: Open-Topo Data
            URL = f"https://api.opentopodata.org/v1/srtm30m?locations={lat},{lon}"
            try:
                r = requests.get(URL, headers=UA, timeout=20)
                r.raise_for_status()
                alt = r.json()["results"][0]["elevation"]
            except Exception:
                pass
        print(f"   {nombre:18s} ({dpto:14s}) → {alt} msnm")
        rows.append({
            "codigo_dane": cod, "municipio": nombre, "departamento": dpto,
            "lat": lat, "lon": lon, "altitud_msnm": alt,
        })
        time.sleep(1.0)  # rate-limit considerado

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "dem_municipal_altitud.csv", index=False)
    print(f"\n   ✓ dem_municipal_altitud.csv: {len(df)} municipios")
    return df


# ╔════════════════════════════════════════════════════════════════════════════
# ║ SoilGrids API
# ╚════════════════════════════════════════════════════════════════════════════
def consultar_soilgrids(lat: float, lon: float) -> dict:
    """
    SoilGrids API REST. Devuelve pH (phh2o), MO (soc), arcilla, etc.
    a 0-30 cm de profundidad.
    """
    URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    params = {
        "lon": lon, "lat": lat,
        "property": ["phh2o", "soc", "clay", "sand", "cec"],
        "depth": "0-30cm", "value": "mean",
    }
    try:
        r = requests.get(URL, params=params, headers=UA, timeout=30)
        r.raise_for_status()
        layers = r.json().get("properties", {}).get("layers", [])
        out = {}
        for layer in layers:
            name = layer.get("name", "?")
            d_factor = layer.get("unit_measure", {}).get("d_factor", 1)
            for d in layer.get("depths", []):
                val = d.get("values", {}).get("mean")
                if val is not None:
                    out[f"{name}_0_30cm"] = val / d_factor
        return out
    except Exception as e:
        return {}


def descargar_suelos() -> pd.DataFrame:
    print("\n[SoilGrids] consultando suelos a 0-30 cm ...")
    rows = []
    for cod, nombre, dpto, lat, lon in MUNICIPIOS_CAFETEROS:
        props = consultar_soilgrids(lat, lon)
        row = {"codigo_dane": cod, "municipio": nombre, "departamento": dpto,
               "lat": lat, "lon": lon, **props}
        ph = props.get("phh2o_0_30cm")
        soc = props.get("soc_0_30cm")
        print(f"   {nombre:18s} pH={ph:.2f}" if ph else f"   {nombre:18s} pH=?",
              f"SOC={soc:.1f}" if soc else "SOC=?")
        rows.append(row)
        time.sleep(2.0)  # rate-limit más conservador

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "soilgrids_municipal.csv", index=False)
    print(f"\n   ✓ soilgrids_municipal.csv: {len(df)} municipios")
    return df


def main():
    print("=" * 70)
    print(" Descarga DEM + Suelos (variables agronómicas)")
    print("=" * 70)
    descargar_altitudes()
    descargar_suelos()
    print("\n✓ Listo.")


if __name__ == "__main__":
    main()
