"""
===============================================================================
 validar_pre_carga.py  ·  Reporte de calidad antes de cargar a PostgreSQL
===============================================================================
 Lee los archivos *_validado.csv en 01_datos/procesados/ y reporta:
   - Conteo de filas y columnas
   - Compatibilidad de columnas con el DDL (alineacion BD)
   - Nulos por columna (% y conteo absoluto)
   - Duplicados por la PK natural de cada tabla
   - Outliers en variables criticas (rangos fisicos)

 NO modifica datos. Genera:
   05_resultados/logs/validar_pre_carga_<timestamp>.log
   05_resultados/reportes/pre_carga_<timestamp>.md
===============================================================================
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Reutiliza modulo comun (.env + logging)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config_bd import PROJECT, DIR_PROC, get_logger

DIR_REPORTES = PROJECT / "05_resultados" / "reportes"
DIR_REPORTES.mkdir(parents=True, exist_ok=True)


# Esquema esperado por tabla: (csv_validado, columnas_minimas_requeridas, pk_natural)
ESQUEMA = {
    "fact_precio": (
        "precios_validado.csv",
        ["fecha"],
        ["fecha"],
    ),
    "fact_clima": (
        "clima_validado.csv",
        ["codigo_dane", "fecha", "temp_media_c", "precipitacion_mm"],
        ["codigo_dane", "fecha"],
    ),
    "dim_periodo (oni)": (
        "enso_validado.csv",
        ["fecha", "oni", "fase_enso"],
        ["fecha"],
    ),
    "fact_produccion": (
        "produccion_validado.csv",
        ["codigo_dane", "anio", "cultivo", "produccion_ton"],
        ["codigo_dane", "anio", "cultivo"],
    ),
    "dim_municipio (geo)": (
        "geografia_validado.csv",
        ["codigo_dane", "altitud_msnm"],
        ["codigo_dane"],
    ),
    "fact_imagen_enfermedad": (
        "imagenes_validado.csv",
        ["split", "clase", "ruta"],
        ["ruta"],
    ),
}

# Outliers fisicos por columna (lo, hi)
RANGOS_FISICOS = {
    "temp_media_c":               (-5, 45),
    "temp_min_c":                 (-10, 40),
    "temp_max_c":                 (-5, 50),
    "precipitacion_mm":           (0, 2500),
    "et0_mm":                     (0, 400),
    "altitud_msnm":               (0, 4500),
    "rendimiento_ton_ha":         (0.0, 10.0),
    "produccion_ton":             (0, 500_000),
    "area_sembrada_ha":           (0, 100_000),
    "area_cosechada_ha":          (0, 100_000),
    "oni":                        (-3, 3),
    "trm_cop_usd":                (1500, 6500),
    "precio_arabica_brasil_usd_kg": (0.5, 30),
    "precio_robusta_usd_kg":      (0.5, 20),
    "precio_fnc_cop_kg":          (3_000, 50_000),
}


def reportar_tabla(logger, tabla, csv_path, cols_min, pk):
    """Reporte de calidad para una tabla. Devuelve dict con metricas."""
    logger.info(f"--- {tabla} ({csv_path.name}) ---")
    if not csv_path.exists():
        logger.error(f"  no existe: {csv_path}")
        return {"tabla": tabla, "ok": False, "razon": "archivo_no_existe"}

    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except Exception as e:
        logger.error(f"  no se pudo leer: {e}")
        return {"tabla": tabla, "ok": False, "razon": f"lectura_fallo: {e}"}

    metricas = {
        "tabla": tabla,
        "archivo": csv_path.name,
        "filas": len(df),
        "columnas": len(df.columns),
        "ok": True,
        "razones": [],
    }

    logger.info(f"  shape: {len(df):,} filas × {len(df.columns)} columnas")

    # 1) Columnas minimas
    faltantes = [c for c in cols_min if c not in df.columns]
    if faltantes:
        metricas["ok"] = False
        metricas["razones"].append(f"faltan columnas: {faltantes}")
        logger.error(f" FAIL    FALTAN columnas requeridas: {faltantes}")
    else:
        logger.info(f" OK   Todas las columnas minimas presentes ({len(cols_min)})")

    # 2) Nulos por columna
    nulos = df.isna().sum()
    nulos_clave = nulos[[c for c in cols_min if c in df.columns]]
    n_nulos_clave = int(nulos_clave.sum())
    if n_nulos_clave:
        logger.warning(f"  WARING {n_nulos_clave} nulos en columnas clave (PK/required):")
        for c, n in nulos_clave[nulos_clave > 0].items():
            logger.warning(f"      {c}: {n}")
    metricas["nulos_columnas_clave"] = n_nulos_clave
    metricas["nulos_total"] = int(nulos.sum())
    # Top 5 columnas con mas nulos
    top_nulos = nulos[nulos > 0].sort_values(ascending=False).head(5)
    if len(top_nulos):
        metricas["top_nulos"] = {c: int(n) for c, n in top_nulos.items()}

    # 3) Duplicados por PK natural
    if all(c in df.columns for c in pk):
        n_dup = int(df.duplicated(subset=pk).sum())
        metricas["duplicados_pk"] = n_dup
        if n_dup:
            logger.warning(f"  WARING {n_dup} duplicados por PK natural {pk}")
            metricas["razones"].append(f"{n_dup} duplicados PK {pk}")
        else:
            logger.info(f"  OK sin duplicados por PK natural {pk}")

    # 4) Outliers en variables fisicas
    outliers_total = 0
    for col, (lo, hi) in RANGOS_FISICOS.items():
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        n = int(((s < lo) | (s > hi)).sum())
        if n:
            outliers_total += n
            logger.warning(f"  WARING {col}: {n} outliers fuera [{lo},{hi}]")
    metricas["outliers_fisicos"] = outliers_total

    # 5) Coverage temporal si hay fecha o anio
    if "fecha" in df.columns:
        try:
            f = pd.to_datetime(df["fecha"], errors="coerce")
            metricas["rango_fechas"] = f"{f.min().date()} -> {f.max().date()}"
            logger.info(f"  rango fechas: {metricas['rango_fechas']}")
        except Exception:
            pass
    if "anio" in df.columns:
        a = pd.to_numeric(df["anio"], errors="coerce").dropna()
        if len(a):
            metricas["rango_anios"] = f"{int(a.min())}->{int(a.max())}"
            logger.info(f"  rango anios:  {metricas['rango_anios']}")

    return metricas


def escribir_reporte_md(reportes, ruta):
    """Reporte resumido en markdown."""
    lines = [f"# Validacion pre-carga · {datetime.now().isoformat(timespec='seconds')}\n"]
    lines.append("| Tabla | Archivo | Filas | Cols | Nulos PK | Dup PK | Outliers | Estado |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|")
    for m in reportes:
        estado = " OK " if m.get("ok") else "✗ FAIL"
        lines.append(
            f"| {m['tabla']} | `{m.get('archivo','-')}` | "
            f"{m.get('filas',0):,} | {m.get('columnas',0)} | "
            f"{m.get('nulos_columnas_clave',0)} | {m.get('duplicados_pk','-')} | "
            f"{m.get('outliers_fisicos',0)} | {estado} |"
        )
    lines.append("")
    for m in reportes:
        lines.append(f"## {m['tabla']}")
        if m.get("razones"):
            lines.append("**Issues:**")
            for r in m["razones"]:
                lines.append(f"- {r}")
        if m.get("top_nulos"):
            lines.append("**Top 5 columnas con nulos:**")
            for c, n in m["top_nulos"].items():
                lines.append(f"- `{c}`: {n:,}")
        if m.get("rango_fechas"):
            lines.append(f"- rango fechas: `{m['rango_fechas']}`")
        if m.get("rango_anios"):
            lines.append(f"- rango años: `{m['rango_anios']}`")
        lines.append("")

    Path(ruta).write_text("\n".join(lines), encoding="utf-8")


def main():
    logger = get_logger("validar_pre_carga")
    logger.info("=" * 70)
    logger.info(" VALIDACION PRE-CARGA · revision de los *_validado.csv")
    logger.info("=" * 70)
    logger.info(f"DIR_PROC: {DIR_PROC}")

    reportes = []
    for tabla, (archivo, cols_min, pk) in ESQUEMA.items():
        m = reportar_tabla(logger, tabla, DIR_PROC / archivo, cols_min, pk)
        reportes.append(m)

    # Resumen
    logger.info("\n" + "=" * 70)
    logger.info(" RESUMEN")
    logger.info("=" * 70)
    n_ok = sum(1 for m in reportes if m.get("ok"))
    for m in reportes:
        marca = "OK  " if m.get("ok") else "FAIL"
        logger.info(f"  [{marca}] {m['tabla']}: "
                     f"{m.get('filas','?')} filas, "
                     f"{m.get('nulos_columnas_clave',0)} nulos clave, "
                     f"{m.get('duplicados_pk','-')} dup, "
                     f"{m.get('outliers_fisicos',0)} outliers")
    logger.info(f"\n  Total OK: {n_ok}/{len(reportes)}")

    # Reporte MD
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = DIR_REPORTES / f"pre_carga_{timestamp}.md"
    escribir_reporte_md(reportes, md_path)
    logger.info(f"  Reporte MD: {md_path.relative_to(PROJECT)}")

    if n_ok < len(reportes):
        logger.error("Algunos validados no estan listos para cargar. Revisa los issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()
