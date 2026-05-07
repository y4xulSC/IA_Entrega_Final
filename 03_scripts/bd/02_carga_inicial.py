"""
═══════════════════════════════════════════════════════════════════════════════
 02_carga_inicial.py
═══════════════════════════════════════════════════════════════════════════════
 Carga todos los CSVs (originales + enriquecidos) a la base de datos
 PostgreSQL `cafe_ia` (esquema `cafe`).

 Pre-requisitos:
   1. PostgreSQL 18.3 corriendo en localhost:5432 (usuario postgres / root)
   2. Base creada:        psql -U postgres -c "CREATE DATABASE cafe_ia;"
   3. Schema cargado:     psql -U postgres -d cafe_ia -f 01_ddl_schema.sql
   4. pip install psycopg2-binary pandas python-dotenv

 Uso:
   python 02_carga_inicial.py
   python 02_carga_inicial.py --solo periodos enso
   python 02_carga_inicial.py --refresh-vistas
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from datetime import date, datetime
import pandas as pd

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("Falta psycopg2: pip install psycopg2-binary")
    sys.exit(1)

# Configuración (sobrescribible con env vars)
PG_CONFIG = {
    "host":     os.environ.get("PG_HOST", "localhost"),
    "port":     int(os.environ.get("PG_PORT", "5432")),
    "user":     os.environ.get("PG_USER", "postgres"),
    "password": os.environ.get("PG_PASSWORD", "root"),
    "dbname":   os.environ.get("PG_DB", "cafe_ia"),
}

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
DIR_ORIGINALES = PROJECT_ROOT / "01_datos" / "originales"
DIR_ENRIQUECIDOS = PROJECT_ROOT / "01_datos" / "enriquecidos"

# También buscamos en la 2da entrega para reaprovechar
DIR_2DA = PROJECT_ROOT.parent / "IA_Segunda_Entrega" / "datasets"


def conn():
    return psycopg2.connect(**PG_CONFIG)


# ────────────────────────────────────────────────────────────────────────────
# 1. Periodos (calendar table)
# ────────────────────────────────────────────────────────────────────────────
def cargar_periodos(year_start: int = 1990, year_end: int = 2030):
    print(f"\n[periodos] generando calendario {year_start}-{year_end} ...")
    rows = []
    d = date(year_start, 1, 1)
    while d.year <= year_end:
        rows.append((
            d, d.year, d.month,
            1 if d.month <= 6 else 2,
            (d.month - 1) // 3 + 1,
            None,        # oni rellenado luego
            "Neutro",    # default
            d.month in (3, 4, 5, 6, 9, 10, 11, 12),  # cosecha bimodal
        ))
        # mes siguiente
        if d.month == 12:
            d = date(d.year + 1, 1, 1)
        else:
            d = date(d.year, d.month + 1, 1)

    sql = """
        INSERT INTO cafe.dim_periodo
        (fecha, anio, mes, semestre, trimestre, oni, fase_enso, es_cosecha)
        VALUES %s
        ON CONFLICT (fecha) DO NOTHING
    """
    with conn() as c, c.cursor() as cur:
        execute_values(cur, sql, rows)
    print(f"   ✓ {len(rows)} periodos insertados (con upsert)")


# ────────────────────────────────────────────────────────────────────────────
# 2. Actualizar dim_periodo con ONI
# ────────────────────────────────────────────────────────────────────────────
def actualizar_oni():
    """Cruza enso_oni_extendido.csv con dim_periodo y actualiza oni y fase_enso."""
    archivo = DIR_ENRIQUECIDOS / "clima" / "enso_oni_extendido.csv"
    if not archivo.exists():
        archivo = DIR_2DA / "ENSO_1950-2026.csv"
    if not archivo.exists():
        print("[oni] sin archivo ENSO. Salta.")
        return
    print(f"\n[oni] {archivo.name}")
    df = pd.read_csv(archivo)
    # Normalizar columnas
    if "fecha" not in df.columns:
        for cand in ["Fecha", "Date", "date"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "fecha"})
                break
    if "oni" not in df.columns:
        for cand in ["ANOM", "ONI", "value", "valor"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "oni"})
                break
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha", "oni"])
    df["oni"] = pd.to_numeric(df["oni"], errors="coerce")
    df["fase_enso"] = df["oni"].apply(
        lambda x: "Nino" if x >= 0.5 else "Nina" if x <= -0.5 else "Neutro")

    sql = """
        UPDATE cafe.dim_periodo
        SET oni = %s, fase_enso = %s
        WHERE fecha = %s
    """
    with conn() as c, c.cursor() as cur:
        cur.executemany(sql, [(r.oni, r.fase_enso,
                               r.fecha.date() if hasattr(r.fecha, "date") else r.fecha)
                              for r in df.itertuples()])
    print(f"   ✓ {len(df)} periodos actualizados con ONI")


# ────────────────────────────────────────────────────────────────────────────
# 3. Cargar municipios
# ────────────────────────────────────────────────────────────────────────────
def cargar_municipios():
    archivo = DIR_ENRIQUECIDOS / "geografia" / "dem_municipal_altitud.csv"
    if not archivo.exists():
        print("[municipios] sin archivo DEM. Saltando — usa solo dim_municipio mínima.")
        return
    print(f"\n[municipios] {archivo.name}")
    df = pd.read_csv(archivo)

    # cargar también soilgrids si existe
    suelos = DIR_ENRIQUECIDOS / "geografia" / "soilgrids_municipal.csv"
    if suelos.exists():
        ds = pd.read_csv(suelos)
        df = df.merge(ds[["codigo_dane", "phh2o_0_30cm", "soc_0_30cm"]]
                       .rename(columns={"phh2o_0_30cm":"soil_ph",
                                        "soc_0_30cm":"soil_soc_pct"}),
                       on="codigo_dane", how="left")

    rows = []
    with conn() as c, c.cursor() as cur:
        # Mapear departamento → id_departamento
        cur.execute("SELECT codigo_dane, id_departamento FROM cafe.dim_departamento")
        dpto_map = {r[0]: r[1] for r in cur.fetchall()}

        for r in df.itertuples():
            cod_dpto = str(r.codigo_dane)[:2].zfill(2)
            id_dpto = dpto_map.get(cod_dpto)
            if id_dpto is None:
                continue
            rows.append((
                str(r.codigo_dane).zfill(5), r.municipio, id_dpto,
                getattr(r, "altitud_msnm", None),
                getattr(r, "lat", None), getattr(r, "lon", None),
                None, None, getattr(r, "soil_ph", None),
                getattr(r, "soil_soc_pct", None),
            ))

        sql = """
            INSERT INTO cafe.dim_municipio
            (codigo_dane, nombre, id_departamento, altitud_msnm, lat, lon,
             zona_cafetera, area_total_ha, soil_ph, soil_soc_pct)
            VALUES %s
            ON CONFLICT (codigo_dane) DO UPDATE SET
                altitud_msnm = EXCLUDED.altitud_msnm,
                soil_ph = EXCLUDED.soil_ph,
                soil_soc_pct = EXCLUDED.soil_soc_pct
        """
        execute_values(cur, sql, rows)
    print(f"   ✓ {len(rows)} municipios cargados")


# ────────────────────────────────────────────────────────────────────────────
# 4. Cargar EVA producción (segunda entrega)
# ────────────────────────────────────────────────────────────────────────────
def cargar_eva():
    arch_2da = DIR_2DA / "EVA_cafe_2019_2024.csv"
    arch_municipal = DIR_ENRIQUECIDOS / "produccion" / "eva_cafe_municipal_2007_2024.csv"

    archivos = [a for a in [arch_2da, arch_municipal] if a.exists()]
    if not archivos:
        print("[eva] sin archivos EVA. Saltando.")
        return

    print(f"\n[eva] cargando {len(archivos)} archivos ...")
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT codigo_dane, id_municipio FROM cafe.dim_municipio")
        muni_map = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT fecha, id_periodo FROM cafe.dim_periodo")
        per_map = {r[0]: r[1] for r in cur.fetchall()}

        rows = []
        for archivo in archivos:
            df = pd.read_csv(archivo)
            df.columns = [c.strip().lower() for c in df.columns]
            for r in df.itertuples():
                # Detectar cod_municipio
                cod = None
                for cand in ("codigo_dane", "codigo_dane_municipio",
                             "cod_municipio", "cod_mun"):
                    if hasattr(r, cand):
                        cod = str(getattr(r, cand)).zfill(5)
                        break
                if cod is None or cod not in muni_map:
                    continue

                # Detectar año
                anio = getattr(r, "anio", getattr(r, "ano", None))
                if anio is None or pd.isna(anio):
                    continue
                fecha = date(int(anio), 1, 1)
                id_per = per_map.get(fecha)
                if id_per is None:
                    continue

                rows.append((
                    muni_map[cod], id_per, None,
                    getattr(r, "area_sembrada_ha", None),
                    getattr(r, "area_cosechada_ha", None),
                    getattr(r, "produccion_ton", None),
                    getattr(r, "rendimiento_ton_ha", None),
                    getattr(r, "estado_fisico", None),
                    "Permanente",  # café es permanente
                    archivo.name[:30],
                ))

        if rows:
            sql = """
                INSERT INTO cafe.fact_produccion
                (id_municipio, id_periodo, id_variedad, area_sembrada_ha,
                 area_cosechada_ha, produccion_ton, rendimiento_ton_ha,
                 estado_fisico, ciclo_cultivo, fuente)
                VALUES %s
            """
            execute_values(cur, sql, rows)
        print(f"   ✓ {len(rows)} registros producción insertados")


# ────────────────────────────────────────────────────────────────────────────
# 5. Cargar precios
# ────────────────────────────────────────────────────────────────────────────
def cargar_precios():
    archivo_2da = DIR_2DA / "fnc_cafe_mensual.csv"
    archivo_extendido = DIR_ENRIQUECIDOS / "precios" / "precios_consolidados_mensual.csv"

    print(f"\n[precios] cargando ...")

    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT fecha, id_periodo FROM cafe.dim_periodo")
        per_map = {r[0]: r[1] for r in cur.fetchall()}

        # 2da entrega: FNC mensual (precio interno)
        if archivo_2da.exists():
            df = pd.read_csv(archivo_2da)
            df["fecha"] = pd.to_datetime(df.get("fecha", df.get("Fecha")), errors="coerce")
            df = df.dropna(subset=["fecha"])
            rows = []
            for r in df.itertuples():
                f_mes = date(r.fecha.year, r.fecha.month, 1)
                id_per = per_map.get(f_mes)
                if id_per is None: continue
                rows.append((id_per,
                    getattr(r, "precio_interno_cop_125kg", None),
                    getattr(r, "precio_oic_compuesto_cusd_libra", None),
                    None, None, None, None,
                    getattr(r, "produccion_total_60kg", None),
                    getattr(r, "exportaciones_60kg", None),
                    None, None))
            sql = """
                INSERT INTO cafe.fact_precio
                (id_periodo, precio_fnc_cop_125kg, precio_ico_usd_lb,
                 precio_arabica_brasil_usd_lb, precio_robusta_usd_lb,
                 precio_world_bank_arabica_usd_kg, precio_world_bank_robusta_usd_kg,
                 fnc_cosecha_60kg, fnc_export_60kg,
                 trm_cop_usd, ipc_general)
                VALUES %s
                ON CONFLICT (id_periodo) DO UPDATE SET
                    precio_fnc_cop_125kg = EXCLUDED.precio_fnc_cop_125kg,
                    precio_ico_usd_lb    = EXCLUDED.precio_ico_usd_lb
            """
            execute_values(cur, sql, rows)
            print(f"   ✓ {len(rows)} meses de precios FNC")


# ────────────────────────────────────────────────────────────────────────────
# 6. Cargar imágenes manifest
# ────────────────────────────────────────────────────────────────────────────
def cargar_imagenes():
    manifest = PROJECT_ROOT / "01_datos" / "imagenes_cafe" / "manifest_consolidado.csv"
    if not manifest.exists():
        print("[imagenes] sin manifest_consolidado.csv. Saltando.")
        return
    print(f"\n[imagenes] {manifest.name}")
    df = pd.read_csv(manifest)
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT nombre, id_enfermedad FROM cafe.dim_enfermedad")
        enf_map = {r[0]: r[1] for r in cur.fetchall()}

        rows = []
        for r in df.itertuples():
            id_enf = enf_map.get(r.clase)
            rows.append((
                id_enf, r.ruta, Path(r.ruta).name, "hoja",
                None, None, r.dataset_origen, None, None, r.split,
            ))
        sql = """
            INSERT INTO cafe.fact_imagen_enfermedad
            (id_enfermedad, ruta_archivo, nombre_archivo, parte_planta,
             severidad_pct, nivel_severidad, fuente_dataset, resolucion_px,
             variedad_cafe, split_modelo)
            VALUES %s
        """
        execute_values(cur, sql, rows)
    print(f"   ✓ {len(rows)} imágenes registradas")


# ────────────────────────────────────────────────────────────────────────────
# 7. Refrescar vista materializada
# ────────────────────────────────────────────────────────────────────────────
def refresh_vistas():
    print("\n[vistas] refrescando vw_master_municipal_mensual ...")
    with conn() as c, c.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW cafe.vw_master_municipal_mensual;")
    print("   ✓ vista refrescada")


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo", nargs="+", default=None,
        choices=["periodos","oni","municipios","eva","precios","imagenes","vistas"])
    parser.add_argument("--refresh-vistas", action="store_true")
    args = parser.parse_args()

    print("=" * 70)
    print(" Carga inicial — base cafe_ia")
    print("=" * 70)
    print(f"DB: {PG_CONFIG['user']}@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['dbname']}")

    # Probar conexión
    try:
        with conn() as c:
            with c.cursor() as cur:
                cur.execute("SELECT version();")
                print(f"   ✓ Conectado · {cur.fetchone()[0][:40]}")
    except Exception as e:
        print(f"\n✗ No se pudo conectar a PostgreSQL: {e}")
        print("\n  Verifica:")
        print("  1. PostgreSQL está corriendo")
        print("  2. CREATE DATABASE cafe_ia;  (con: psql -U postgres)")
        print("  3. psql -U postgres -d cafe_ia -f 01_ddl_schema.sql")
        sys.exit(1)

    sel = args.solo or ["periodos","oni","municipios","eva","precios","imagenes","vistas"]

    if "periodos"   in sel: cargar_periodos()
    if "oni"        in sel: actualizar_oni()
    if "municipios" in sel: cargar_municipios()
    if "eva"        in sel: cargar_eva()
    if "precios"    in sel: cargar_precios()
    if "imagenes"   in sel: cargar_imagenes()
    if "vistas"     in sel or args.refresh_vistas:
        refresh_vistas()

    print("\n✓ Carga inicial completada")


if __name__ == "__main__":
    main()
