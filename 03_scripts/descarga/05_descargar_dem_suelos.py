"""
===============================================================================
 05_descargar_dem_suelos.py
===============================================================================
 Descarga variables agronomicas:
   - Altitud DEM SRTM 30m via Open-Elevation
   - pH y materia organica via SoilGrids 250m

 v3 (2026-05-08): SoilGrids con diagnostico HTTP detallado + sleep mas largo
                  + intento doble (0-30cm directo / fallback profundidades
                  individuales). Reporta exactamente que pasa en cada call.

 Output:
   01_datos/enriquecidos/geografia/
     dem_municipal_altitud.csv
     soilgrids_municipal.csv
===============================================================================
"""
from __future__ import annotations
from pathlib import Path
import sys
import time
import requests
import pandas as pd

from _config import UA

# UTF-8 stdout en Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
OUT_DIR = PROJECT_ROOT / "01_datos" / "enriquecidos" / "geografia"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MUNICIPIOS_CAFETEROS = [
    ("41001", "Neiva",        "Huila",       2.9389,  -75.2819),
    ("05001", "Medellin",     "Antioquia",   6.2442,  -75.5812),
    ("52001", "Pasto",        "Narino",      1.2136,  -77.2811),
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
    ("17873", "Villamaria",   "Caldas",      5.0438,  -75.5067),
    ("63594", "Salento",      "Quindio",     4.6371,  -75.5705),
    ("17653", "Salamina",     "Caldas",      5.4072,  -75.4868),
    ("17442", "Marsella",     "Risaralda",   4.9352,  -75.7398),
]


# Open-Elevation
def consultar_altitud(lat, lon):
    URL = "https://api.open-elevation.com/api/v1/lookup"
    try:
        r = requests.get(URL, params={"locations": str(lat) + "," + str(lon)},
                         headers=UA, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data["results"][0]["elevation"]
    except Exception:
        return None


def descargar_altitudes():
    print("\n[DEM] consultando altitud SRTM via Open-Elevation ...")
    rows = []
    for cod, nombre, dpto, lat, lon in MUNICIPIOS_CAFETEROS:
        alt = consultar_altitud(lat, lon)
        if alt is None:
            URL = ("https://api.opentopodata.org/v1/srtm30m?locations=" +
                   str(lat) + "," + str(lon))
            try:
                r = requests.get(URL, headers=UA, timeout=20)
                r.raise_for_status()
                alt = r.json()["results"][0]["elevation"]
            except Exception:
                pass
        print("   " + nombre.ljust(18) + " (" + dpto.ljust(14) + ") -> " +
              str(alt) + " msnm")
        rows.append({
            "codigo_dane": cod, "municipio": nombre, "departamento": dpto,
            "lat": lat, "lon": lon, "altitud_msnm": alt,
        })
        time.sleep(1.0)

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "dem_municipal_altitud.csv", index=False)
    print("\n   OK dem_municipal_altitud.csv: " + str(len(df)) + " municipios")
    return df


# SoilGrids
SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
PROPS = ["phh2o", "soc", "clay", "sand", "cec"]


def _soilgrids_call(lat, lon, depths, *, max_attempts=5, timeout=90):
    """
    GET con retry exponencial + diagnostico HTTP detallado.
    Devuelve (json, status_str). Si todo falla, devuelve ({}, 'error_x').
    """
    params = [("lon", lon), ("lat", lat)]
    for p in PROPS:
        params.append(("property", p))
    for d in depths:
        params.append(("depth", d))
    params.append(("value", "mean"))

    last_status = "no_intentos"
    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.get(SOILGRIDS_URL, params=params,
                             headers=UA, timeout=timeout)
            last_status = "http_" + str(r.status_code)
            if r.status_code == 200:
                return r.json(), "ok"
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 0)) or min(2 ** attempt * 5, 90)
                time.sleep(wait)
                continue
            if 500 <= r.status_code < 600:
                time.sleep(min(2 ** attempt, 30))
                continue
            # 4xx no recuperable: dump body para diagnostico
            body = r.text[:200]
            return {}, "http_" + str(r.status_code) + " body=" + body
        except requests.exceptions.Timeout:
            last_status = "timeout"
            time.sleep(min(2 ** attempt, 30))
        except Exception as e:
            last_status = type(e).__name__
            time.sleep(min(2 ** attempt, 30))
    return {}, last_status


def _parse_soilgrids(data):
    """
    Parser robusto del response. Estructura:
       data["properties"]["layers"][i]["depths"][j]["values"]["mean"]
    """
    out = {}
    layers = (data.get("properties") or {}).get("layers") or []
    for layer in layers:
        name = layer.get("name", "?")
        d_factor = ((layer.get("unit_measure") or {}).get("d_factor") or 1)
        suma, peso_total = 0.0, 0.0
        for d in (layer.get("depths") or []):
            label = d.get("label", "")
            mean_val = ((d.get("values") or {}).get("mean"))
            if mean_val is None:
                continue
            try:
                _from, _to = label.replace("cm", "").split("-")
                peso = float(_to) - float(_from)
            except Exception:
                peso = 1.0
            suma += float(mean_val) * peso
            peso_total += peso
            out[name + "_" + label] = float(mean_val) / d_factor
        if peso_total > 0:
            out[name + "_0_30cm"] = (suma / peso_total) / d_factor
    return out


import json as _json

DEBUG_DUMPED = {"flag": False}  # solo guardamos el primer JSON vacio


def _dump_debug(data, lat, lon):
    """Guarda 1 sola vez el JSON crudo para diagnosticar respuestas vacias."""
    if DEBUG_DUMPED["flag"]:
        return
    DEBUG_DUMPED["flag"] = True
    try:
        path = OUT_DIR / "soilgrids_debug_response.json"
        with open(path, "w", encoding="utf-8") as f:
            _json.dump({"lat": lat, "lon": lon, "response": data},
                       f, indent=2, ensure_ascii=False)
        print("   [debug] respuesta cruda dumpeada a " + str(path.name))
    except Exception:
        pass


# Offsets en grados (~5-10 km) para evitar pixeles urbanos/sellados.
# SoilGrids devuelve mean=null en zonas urbanas, agua, o sin cobertura.
OFFSETS_RURALES = [
    (0.0, 0.0),       # punto exacto
    (-0.05, -0.05),   # SO (zona rural mas baja)
    (0.05, 0.05),     # NE
    (-0.05, 0.05),    # NO
    (0.05, -0.05),    # SE
    (0.0, -0.10),     # 10km al W
    (-0.10, 0.0),     # 10km al S
]


def consultar_soilgrids(lat, lon):
    """
    Estrategia:
      1. Punto exacto (0-5/5-15/15-30 cm)
      2. Si null (zona urbana/agua), reintentar con offsets de ~5-10km
      3. Si todo falla, intentar solo 0-5cm
    Devuelve (props_dict, diagnostico_str). El dict incluye 'offset_deg'
    indicando si se uso un punto desplazado.
    """
    # Intento 1-7: punto exacto + offsets rurales con 3 profundidades
    for i, (dlat, dlon) in enumerate(OFFSETS_RURALES):
        data, status = _soilgrids_call(lat + dlat, lon + dlon,
                                        ["0-5cm", "5-15cm", "15-30cm"])
        props = _parse_soilgrids(data)
        if props.get("phh2o_0_30cm") is not None:
            offset_label = ("(" + str(dlat) + "," + str(dlon) + ")"
                            if (dlat or dlon) else "exacto")
            props["offset_deg"] = ("%.2f,%.2f" % (dlat, dlon))
            return props, status + " | offset:" + offset_label
        if i == 0 and status == "ok":
            # primera llamada ok pero parser vacio: dump JSON crudo
            _dump_debug(data, lat, lon)
        time.sleep(1.5)

    # Ultimo intento: solo 0-5cm punto exacto
    time.sleep(2)
    data2, status2 = _soilgrids_call(lat, lon, ["0-5cm"])
    props2 = _parse_soilgrids(data2)
    if (props2.get("phh2o_0-5cm") is not None or
            props2.get("phh2o_0_30cm") is not None):
        props2["offset_deg"] = "0.0,0.0"
        return props2, status + " | retry-0-5: " + status2

    return {}, status + " | offsets agotados | retry-0-5: " + status2


def descargar_suelos():
    print("\n[SoilGrids] consultando suelos (parser v4 con offsets rurales) ...")
    print("   nota: SoilGrids devuelve null en zonas urbanas/agua. Si el centro")
    print("         del municipio falla, el script reintenta con offset 5-10 km.")
    rows = []
    for cod, nombre, dpto, lat, lon in MUNICIPIOS_CAFETEROS:
        props, diag = consultar_soilgrids(lat, lon)
        row = {"codigo_dane": cod, "municipio": nombre, "departamento": dpto,
               "lat": lat, "lon": lon, "diag": diag}
        row.update(props)
        ph = props.get("phh2o_0_30cm") or props.get("phh2o_0-5cm")
        soc = props.get("soc_0_30cm") or props.get("soc_0-5cm")
        ph_str = ("%.2f" % ph) if ph is not None else "?"
        soc_str = ("%.1f" % soc) if soc is not None else "?"
        # Mostrar diagnostico solo si fallo
        if ph is None:
            print("   " + nombre.ljust(18) + " pH=?  SOC=?  (" + diag + ")")
        else:
            print("   " + nombre.ljust(18) + " pH=" + ph_str +
                  "  SOC=" + soc_str)
        rows.append(row)
        time.sleep(5.0)  # mas conservador que 2s

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "soilgrids_municipal.csv", index=False)
    n_validos = (df["phh2o_0_30cm"].notna().sum()
                 if "phh2o_0_30cm" in df.columns else 0)
    print("\n   OK soilgrids_municipal.csv: " + str(len(df)) +
          " municipios (" + str(n_validos) + " con pH valido)")
    if n_validos < len(df):
        print("   Si la mayoria fallo, revisa la columna 'diag' del CSV o:")
        print("   - reejecuta 'python 05_descargar_dem_suelos.py' tras unos minutos")
        print("   - el endpoint de ISRIC a veces tiene caidas")
    return df


def main():
    print("=" * 70)
    print(" Descarga DEM + Suelos (variables agronomicas)")
    print("=" * 70)
    df_alt = descargar_altitudes()
    df_suelos = descargar_suelos()

    n_alt_ok = df_alt["altitud_msnm"].notna().sum() if not df_alt.empty else 0
    n_suelos_ok = (df_suelos["phh2o_0_30cm"].notna().sum()
                   if not df_suelos.empty and "phh2o_0_30cm" in df_suelos.columns
                   else 0)

    print("\n  altitud OK : " + str(n_alt_ok) + "/" + str(len(MUNICIPIOS_CAFETEROS)))
    print("  suelos OK  : " + str(n_suelos_ok) + "/" + str(len(MUNICIPIOS_CAFETEROS)))
    print("\nOK Listo.")

    if n_alt_ok == 0 and n_suelos_ok == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
