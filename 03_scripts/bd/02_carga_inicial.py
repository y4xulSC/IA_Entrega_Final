"""
===============================================================================
 02_carga_inicial.py  ·  Carga los *_validado.csv a PostgreSQL
===============================================================================
 Lee 01_datos/procesados/*_validado.csv (producidos por 03_scripts/etl/) y los
 inserta en la BD `cafe_ia` esquema `cafe`. Idempotente (UPSERTs por PK natural).

 Pre-requisitos:
   1. PostgreSQL >= 13 corriendo (config en .env)
   2. Pipeline ETL ejecutado: 03_scripts/etl/etl_pipeline.py
   3. (recomendado) Validacion previa: validar_pre_carga.py

 Pasos:
   psql -U postgres -c "CREATE DATABASE cafe_ia;"
   psql -U postgres -d cafe_ia -f 01_ddl_schema.sql
   pip install psycopg2-binary pandas
   python 02_carga_inicial.py

 Uso:
   python 02_carga_inicial.py                     # todo
   python 02_carga_inicial.py --solo periodos enso clima
   python 02_carga_inicial.py --skip imagenes
   python 02_carga_inicial.py --refresh-vistas
===============================================================================
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from datetime import date

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config_bd import (
    PG_CONFIG, DIR_PROC, DIR_ENRIQ, PROJECT, conectar, get_logger
)

try:
    from psycopg2.extras import execute_values
except ImportError:
    print("Falta psycopg2: pip install psycopg2-binary")
    sys.exit(1)

logger = get_logger("carga_inicial")


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════
def _safe_num(v):
    """None si NaN/None/'', sino el valor."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


def _read_csv(path: Path):
    if not path.exists():
        logger.warning(f"No existe: {path.relative_to(PROJECT)}")
        return None
    df = pd.read_csv(path, low_memory=False)
    logger.info(f"  leido {path.name}: {len(df)} filas")
    return df


# ════════════════════════════════════════════════════════════════════════════
#  1. dim_periodo  ·  calendario 1990-2030 + ONI desde enso_validado
# ════════════════════════════════════════════════════════════════════════════
def cargar_periodos(year_start=1990, year_end=2030):
    logger.info(f"\n[periodos] generando calendario {year_start}-{year_end}")
    rows = []
    d = date(year_start, 1, 1)
    while d.year <= year_end:
        rows.append((
            d, d.year, d.month,
            1 if d.month <= 6 else 2,
            (d.month - 1) // 3 + 1,
            None, "Neutro",
            d.month in (3, 4, 5, 6, 9, 10, 11, 12),
        ))
        d = date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)

    sql = """
        INSERT INTO cafe.dim_periodo
        (fecha, anio, mes, semestre, trimestre, oni, fase_enso, es_cosecha)
        VALUES %s ON CONFLICT (fecha) DO NOTHING
    """
    with conectar() as c, c.cursor() as cur:
        execute_values(cur, sql, rows)
    logger.info(f"  OK {len(rows)} periodos (upsert)")


def actualizar_oni():
    """Cruza enso_validado.csv con dim_periodo y actualiza oni + fase_enso."""
    logger.info("\n[oni] actualizando dim_periodo desde enso_validado.csv")
    df = _read_csv(DIR_PROC / "enso_validado.csv")
    if df is None:
        logger.warning("  WARING  Saltando ONI (sin archivo). El pipeline ETL debe correr antes.")
        return

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha", "oni"])

    sql = "UPDATE cafe.dim_periodo SET oni = %s, fase_enso = %s WHERE fecha = %s"
    rows = [(float(r.oni), str(r.fase_enso), r.fecha.date()) for r in df.itertuples()]
    with conectar() as c, c.cursor() as cur:
        cur.executemany(sql, rows)
    logger.info(f"  OK {len(rows)} periodos con ONI actualizado")


# ════════════════════════════════════════════════════════════════════════════
#  2. dim_municipio  ·  desde geografia_validado.csv
# ════════════════════════════════════════════════════════════════════════════
def cargar_municipios():
    logger.info("\n[municipios] cargando dim_municipio desde geografia_validado.csv")
    df = _read_csv(DIR_PROC / "geografia_validado.csv")
    if df is None:
        logger.warning("  WARING  Saltando municipios.")
        return

    df["codigo_dane"] = df["codigo_dane"].astype(str).str.zfill(5)

    rows = []
    with conectar() as c, c.cursor() as cur:
        cur.execute("SELECT codigo_dane, id_departamento FROM cafe.dim_departamento")
        dpto_map = {r[0]: r[1] for r in cur.fetchall()}

        for r in df.itertuples():
            cod_dpto = str(r.codigo_dane)[:2]
            id_dpto = dpto_map.get(cod_dpto)
            if id_dpto is None:
                continue
            # Heuristica: la columna phh2o_0_30cm contiene el pH ponderado.
            # SOC: soc_0_30cm.
            ph = _safe_num(getattr(r, "phh2o_0_30cm", None))
            soc = _safe_num(getattr(r, "soc_0_30cm", None))
            rows.append((
                r.codigo_dane, r.municipio, id_dpto,
                _safe_num(r.altitud_msnm),
                _safe_num(r.lat), _safe_num(r.lon),
                None, None, ph, soc,
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
    logger.info(f"  OK {len(rows)} municipios cargados (upsert)")


# ════════════════════════════════════════════════════════════════════════════
#  3. fact_clima  ·  desde clima_validado.csv
# ════════════════════════════════════════════════════════════════════════════
def cargar_clima():
    logger.info("\n  INFO [clima] cargando fact_clima desde clima_validado.csv")
    df = _read_csv(DIR_PROC / "clima_validado.csv")
    if df is None:
        return

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
    df["codigo_dane"] = df["codigo_dane"].astype(str).str.zfill(5)
    df = df.dropna(subset=["fecha"])

    with conectar() as c, c.cursor() as cur:
        cur.execute("SELECT codigo_dane, id_municipio FROM cafe.dim_municipio")
        muni_map = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT fecha, id_periodo FROM cafe.dim_periodo")
        per_map = {r[0]: r[1] for r in cur.fetchall()}

        rows, sin_mun, sin_per = [], 0, 0
        for r in df.itertuples():
            id_mun = muni_map.get(r.codigo_dane)
            id_per = per_map.get(r.fecha)
            if id_mun is None: sin_mun += 1; continue
            if id_per is None: sin_per += 1; continue
            rows.append((
                id_mun, id_per,
                _safe_num(r.temp_media_c),
                _safe_num(getattr(r, "temp_min_c", None)),
                _safe_num(getattr(r, "temp_max_c", None)),
                _safe_num(r.precipitacion_mm),
                None,  # precipitacion_chirps_mm
                _safe_num(getattr(r, "et0_mm", None)),
                None,  # humedad_rel_pct
                _safe_num(getattr(r, "viento_max_kmh", None)),
                _safe_num(getattr(r, "radiacion_mj_m2", None)),
                None,  # ndvi
                "OpenMeteo",
            ))

        sql = """
            INSERT INTO cafe.fact_clima
              (id_municipio, id_periodo, temp_media_c, temp_min_c, temp_max_c,
               precipitacion_mm, precipitacion_chirps_mm, et0_mm, humedad_rel_pct,
               viento_max_kmh, radiacion_mj_m2, ndvi, fuente)
            VALUES %s
            ON CONFLICT (id_municipio, id_periodo, fuente) DO UPDATE SET
              temp_media_c = EXCLUDED.temp_media_c,
              precipitacion_mm = EXCLUDED.precipitacion_mm,
              et0_mm = EXCLUDED.et0_mm
        """
        execute_values(cur, sql, rows)
    logger.info(f"  OK {len(rows)} filas clima · sin_mun={sin_mun} sin_per={sin_per}")


# ════════════════════════════════════════════════════════════════════════════
#  4. fact_precio  ·  desde precios_validado.csv
# ════════════════════════════════════════════════════════════════════════════
def cargar_precios():
    logger.info("\n  INFO [precios] cargando fact_precio desde precios_validado.csv")
    df = _read_csv(DIR_PROC / "precios_validado.csv")
    if df is None:
        return

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
    df = df.dropna(subset=["fecha"])

    with conectar() as c, c.cursor() as cur:
        cur.execute("SELECT fecha, id_periodo FROM cafe.dim_periodo")
        per_map = {r[0]: r[1] for r in cur.fetchall()}

        rows = []
        for r in df.itertuples():
            id_per = per_map.get(r.fecha)
            if id_per is None: continue
            rows.append((
                id_per,
                _safe_num(getattr(r, "precio_arabica_brasil_usd_kg", None)),
                _safe_num(getattr(r, "precio_robusta_usd_kg", None)),
                _safe_num(getattr(r, "precio_arabica_wb_usd_kg", None)),
                _safe_num(getattr(r, "precio_robusta_wb_usd_kg", None)),
                _safe_num(getattr(r, "precio_fnc_cop_kg", None)),
                _safe_num(getattr(r, "precio_arabica_brasil_cop_kg", None)),
                None, None,  # fnc_cosecha_60kg, fnc_export_60kg
                _safe_num(getattr(r, "trm_cop_usd", None)),
                None,  # ipc_general
                bool(getattr(r, "surge_flag", 0)),
            ))

        sql = """
            INSERT INTO cafe.fact_precio
              (id_periodo,
               precio_arabica_brasil_usd_kg, precio_robusta_usd_kg,
               precio_arabica_wb_usd_kg, precio_robusta_wb_usd_kg,
               precio_fnc_cop_kg, precio_arabica_brasil_cop_kg,
               fnc_cosecha_60kg, fnc_export_60kg,
               trm_cop_usd, ipc_general, surge_flag)
            VALUES %s
            ON CONFLICT (id_periodo) DO UPDATE SET
              precio_arabica_brasil_usd_kg = EXCLUDED.precio_arabica_brasil_usd_kg,
              precio_fnc_cop_kg = EXCLUDED.precio_fnc_cop_kg,
              trm_cop_usd = EXCLUDED.trm_cop_usd,
              surge_flag = EXCLUDED.surge_flag
        """
        execute_values(cur, sql, rows)
    logger.info(f"  OK {len(rows)} meses de precios cargados (upsert)")


# ════════════════════════════════════════════════════════════════════════════
#  5. fact_produccion  ·  desde produccion_validado.csv
# ════════════════════════════════════════════════════════════════════════════
def cargar_produccion():
    logger.info("\n  INFO [produccion] cargando fact_produccion desde produccion_validado.csv")
    df = _read_csv(DIR_PROC / "produccion_validado.csv")
    if df is None:
        return

    df["codigo_dane"] = df["codigo_dane"].astype(str).str.zfill(5)
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df = df.dropna(subset=["codigo_dane", "anio"])
    df["anio"] = df["anio"].astype(int)

    with conectar() as c, c.cursor() as cur:
        cur.execute("SELECT codigo_dane, id_municipio FROM cafe.dim_municipio")
        muni_map = {r[0]: r[1] for r in cur.fetchall()}
        # Auto-crear municipios faltantes (con dpto desde primer 2 dig DANE)
        cur.execute("SELECT codigo_dane, id_departamento FROM cafe.dim_departamento")
        dpto_map = {r[0]: r[1] for r in cur.fetchall()}

        # Periodo = primer dia del año
        cur.execute("SELECT fecha, id_periodo FROM cafe.dim_periodo")
        per_map = {r[0]: r[1] for r in cur.fetchall()}

        # Crear municipios faltantes en lote
        nuevos_muni = []
        for cod in df["codigo_dane"].unique():
            if cod in muni_map:
                continue
            id_dpto = dpto_map.get(cod[:2])
            if id_dpto is None:
                continue
            # Tomar nombre municipio del primer registro
            sub = df[df["codigo_dane"] == cod]
            nombre_mun = str(sub["municipio"].iloc[0])[:80] if "municipio" in sub.columns else f"Municipio {cod}"
            nuevos_muni.append((cod, nombre_mun, id_dpto, None, None, None, None, None, None, None))

        if nuevos_muni:
            sql_m = """
                INSERT INTO cafe.dim_municipio
                  (codigo_dane, nombre, id_departamento, altitud_msnm, lat, lon,
                   zona_cafetera, area_total_ha, soil_ph, soil_soc_pct)
                VALUES %s
                ON CONFLICT (codigo_dane) DO NOTHING
            """
            execute_values(cur, sql_m, nuevos_muni)
            logger.info(f"  INFO  + {len(nuevos_muni)} municipios nuevos auto-creados")
            # Refrescar map
            cur.execute("SELECT codigo_dane, id_municipio FROM cafe.dim_municipio")
            muni_map = {r[0]: r[1] for r in cur.fetchall()}

        rows, sin_mun, sin_per = [], 0, 0
        for r in df.itertuples():
            id_mun = muni_map.get(r.codigo_dane)
            id_per = per_map.get(date(int(r.anio), 1, 1))
            if id_mun is None: sin_mun += 1; continue
            if id_per is None: sin_per += 1; continue
            rows.append((
                id_mun, id_per, None,
                _safe_num(getattr(r, "area_sembrada_ha", None)),
                _safe_num(getattr(r, "area_cosechada_ha", None)),
                _safe_num(getattr(r, "produccion_ton", None)),
                _safe_num(getattr(r, "rendimiento_ton_ha", None)),
                str(getattr(r, "estado_fisico", ""))[:30] or None,
                "Permanente",
                "EVA-Socrata",
            ))

        sql = """
            INSERT INTO cafe.fact_produccion
              (id_municipio, id_periodo, id_variedad, area_sembrada_ha,
               area_cosechada_ha, produccion_ton, rendimiento_ton_ha,
               estado_fisico, ciclo_cultivo, fuente)
            VALUES %s
        """
        execute_values(cur, sql, rows)
    logger.info(f"  OK {len(rows)} registros producción · sin_mun={sin_mun} sin_per={sin_per}")


# ════════════════════════════════════════════════════════════════════════════
#  6. fact_imagen_enfermedad  ·  desde imagenes_validado.csv
# ════════════════════════════════════════════════════════════════════════════
def cargar_imagenes():
    logger.info("\n  INFO [imagenes] cargando fact_imagen_enfermedad desde imagenes_validado.csv")
    df = _read_csv(DIR_PROC / "imagenes_validado.csv")
    if df is None:
        return

    with conectar() as c, c.cursor() as cur:
        cur.execute("SELECT nombre, id_enfermedad FROM cafe.dim_enfermedad")
        enf_map = {r[0]: r[1] for r in cur.fetchall()}

        rows = []
        for r in df.itertuples():
            id_enf = enf_map.get(str(r.clase))
            ruta = str(r.ruta)
            nombre_arch = Path(ruta).name[:200]
            rows.append((
                id_enf, ruta, nombre_arch, "hoja",
                None, None, str(r.dataset_origen)[:20],
                None, None, str(r.split)[:10],
            ))

        sql = """
            INSERT INTO cafe.fact_imagen_enfermedad
              (id_enfermedad, ruta_archivo, nombre_archivo, parte_planta,
               severidad_pct, nivel_severidad, fuente_dataset, resolucion_px,
               variedad_cafe, split_modelo)
            VALUES %s
        """
        # Insercion en chunks (manifest grande)
        CHUNK = 5000
        for i in range(0, len(rows), CHUNK):
            execute_values(cur, sql, rows[i:i+CHUNK])
        logger.info(f"  OK {len(rows)} imagenes registradas")


# ════════════════════════════════════════════════════════════════════════════
#  7. Refresh vista materializada
# ════════════════════════════════════════════════════════════════════════════
def refresh_vistas():
    logger.info("\n  INFO [vistas] refrescando vw_master_municipal_mensual")
    with conectar() as c, c.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW cafe.vw_master_municipal_mensual;")
    logger.info("  OK vista refrescada")


# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════
PASOS = {
    "periodos":   cargar_periodos,
    "oni":        actualizar_oni,
    "municipios": cargar_municipios,
    "clima":      cargar_clima,
    "precios":    cargar_precios,
    "produccion": cargar_produccion,
    "imagenes":   cargar_imagenes,
    "vistas":     refresh_vistas,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo", nargs="+", choices=list(PASOS.keys()))
    parser.add_argument("--skip", nargs="+", default=[], choices=list(PASOS.keys()))
    parser.add_argument("--refresh-vistas", action="store_true")
    args = parser.parse_args()

    sel = args.solo or list(PASOS.keys())
    sel = [s for s in sel if s not in args.skip]
    if args.refresh_vistas and "vistas" not in sel:
        sel.append("vistas")

    logger.info(" =" * 70)
    logger.info("  INFO  CARGA INICIAL · base cafe_ia")
    logger.info(" =" * 70)
    logger.info(f"  INFO DB: {PG_CONFIG['user']}@{PG_CONFIG['host']}:"
                 f"  INFO {PG_CONFIG['port']}/{PG_CONFIG['dbname']}")
    logger.info(f"  INFO Pasos: {sel}")

    # Verificar conexion + schema
    try:
        with conectar() as c, c.cursor() as cur:
            cur.execute("SELECT version()")
            ver = cur.fetchone()[0]
            logger.info(f"  INFO Conectado · {ver[:60]}")
            cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='cafe'")
            n_tablas = cur.fetchone()[0]
            if n_tablas == 0:
                logger.error("  FAIL Schema 'cafe' vacio. Ejecuta primero:")
                logger.error("  FAIL  psql -U postgres -d cafe_ia -f 01_ddl_schema.sql")
                sys.exit(1)
            logger.info(f"  INFO Schema cafe: {n_tablas} tablas presentes")
    except Exception as e:
        logger.error(f"  FAILConexion fallo: {e}")
        sys.exit(1)

    for paso in sel:
        try:
            PASOS[paso]()
        except Exception as e:
            logger.error(f"  FAIL  paso '{paso}' fallo: {e}", exc_info=True)

    logger.info("\n  INFO " + "=" * 70)
    logger.info("  INFO  CARGA INICIAL COMPLETADA")
    logger.info(" =" * 70)


if __name__ == "__main__":
    main()
