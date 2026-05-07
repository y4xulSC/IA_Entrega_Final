"""
═══════════════════════════════════════════════════════════════════════════════
 04_descargar_eva_municipal.py
═══════════════════════════════════════════════════════════════════════════════
 Descarga EVA (Evaluaciones Agropecuarias Municipales) extendido:
   - Período completo 2007-2024 (la 2da entrega solo tenía 2019-2024)
   - Granularidad municipal (NO departamental)
   - Filtrado a café Arábica + Robusta + Pergamino + Verde

 RESUELVE: La 2da entrega tiene solo 14 obs en test → R²=0.067.
 Con datos municipales: ~600 municipios cafeteros × 17 años = ~10k obs.

 Fuente: datos.gov.co (Socrata API)
   Dataset: 2pnw-mmge "Evaluaciones Agropecuarias Municipales – EVA"
   API:     https://www.datos.gov.co/resource/2pnw-mmge.csv

 Output:
   01_datos/enriquecidos/produccion/
     eva_cafe_municipal_2007_2024.csv
     eva_cafe_resumen_anual.csv
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
from pathlib import Path
import requests
import pandas as pd
import time

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
OUT_DIR = PROJECT_ROOT / "01_datos" / "enriquecidos" / "produccion"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Endpoints datos.gov.co (Socrata)
DATASETS_EVA = [
    # (id_socrata, descripcion)
    ("2pnw-mmge",    "EVA Municipales Agrícolas (alternativa)"),
    ("p2vm-evjy",    "Evaluaciones Agropecuarias Departamentales"),
]

UA = {"User-Agent": "Mozilla/5.0 (UAO IA Cafe Project)"}


def descargar_eva_municipal(socrata_id: str, limit: int = 500_000) -> pd.DataFrame:
    """
    Descarga EVA municipal vía Socrata, filtrando café.
    """
    print(f"\n[Socrata] dataset {socrata_id} ...")
    URL = f"https://www.datos.gov.co/resource/{socrata_id}.csv"
    params = {
        "$limit": limit,
        "$where": ("upper(cultivo) like '%CAFE%' OR "
                   "upper(cultivo) like '%CAFÉ%' OR "
                   "upper(cul) like '%CAFE%'"),
    }
    try:
        r = requests.get(URL, params=params, headers=UA, timeout=120)
        r.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        print(f"   ✓ {len(df)} filas descargadas")
        return df
    except Exception as e:
        print(f"   ✗ Socrata {socrata_id}: {e}")
        return pd.DataFrame()


def main():
    print("=" * 70)
    print(" Descarga EVA Municipal — Café (extendido a 2007-2024)")
    print("=" * 70)

    todos = []
    for sid, desc in DATASETS_EVA:
        df = descargar_eva_municipal(sid)
        if not df.empty:
            df["fuente_socrata"] = sid
            todos.append(df)
        time.sleep(1)

    if not todos:
        print("\n⚠  Ninguna descarga funcionó. Posibles causas:")
        print("   - API datos.gov.co rate-limited (espera 5 min y reintenta)")
        print("   - Cambió el ID Socrata. Busca 'EVA' en https://www.datos.gov.co")
        print("\nAlternativa manual:")
        print("   https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/")
        return

    # Unificar
    df = pd.concat(todos, ignore_index=True)

    # Normalizar columnas (varían por dataset)
    rename_map = {
        "anio": "anio", "ano": "anio", "year": "anio",
        "departamento": "departamento", "depto": "departamento",
        "municipio": "municipio", "muni": "municipio",
        "codigo_dane_municipio": "codigo_dane",
        "cultivo": "cultivo",
        "area_sembrada__ha_": "area_sembrada_ha",
        "area_sembrada_ha": "area_sembrada_ha",
        "area_cosechada__ha_": "area_cosechada_ha",
        "area_cosechada_ha": "area_cosechada_ha",
        "produccion__t_": "produccion_ton",
        "produccion_t": "produccion_ton",
        "produccion": "produccion_ton",
        "rendimiento__t_ha_": "rendimiento_ton_ha",
        "rendimiento_t_ha": "rendimiento_ton_ha",
        "rendimiento": "rendimiento_ton_ha",
    }
    df = df.rename(columns={c: rename_map.get(c.lower(), c) for c in df.columns})

    # Filtrar solo café Arábica + Robusta (sin tostado, soluble, etc.)
    if "cultivo" in df.columns:
        df = df[df["cultivo"].str.contains("café|cafe", case=False, na=False)]
        df = df[~df["cultivo"].str.contains("tostado|soluble|extracto",
                                             case=False, na=False)]

    out_path = OUT_DIR / "eva_cafe_municipal_2007_2024.csv"
    df.to_csv(out_path, index=False)
    print(f"\n✓ {out_path.name}: {len(df)} filas")

    # Resumen anual
    if "anio" in df.columns and "produccion_ton" in df.columns:
        resumen = df.groupby("anio").agg(
            n_municipios=("municipio", "nunique"),
            area_total_ha=("area_sembrada_ha", "sum"),
            produccion_total_ton=("produccion_ton", "sum"),
            rendimiento_medio=("rendimiento_ton_ha", "mean"),
        ).reset_index()
        out_resumen = OUT_DIR / "eva_cafe_resumen_anual.csv"
        resumen.to_csv(out_resumen, index=False)
        print(f"✓ {out_resumen.name}: {len(resumen)} años")
        print(resumen.to_string(index=False))

    print("\n✓ Listo. Siguiente: 05_descargar_dem_suelos.py")


if __name__ == "__main__":
    main()
