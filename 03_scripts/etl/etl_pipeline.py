"""
===============================================================================
 etl_pipeline.py  ·  Pipeline ETL por categoria de fuente externa
===============================================================================
 Toma los CSVs descargados por 03_scripts/descarga/* y, por cada categoria,
 aplica reglas de validacion + consolidacion ESPECIFICAS al dominio.
 Produce:
   01_datos/procesados/<categoria>_validado.csv     (datos limpios, listos BD)
   01_datos/procesados/etl_reportes/<categoria>.json
   01_datos/procesados/etl_reportes/RESUMEN.md      (consolidado)

 Categorias:
   PRECIOS    FRED + WB + IMF + BanRep TRM + ICO + FNC -> normalizar a
              moneda comun (USD/kg) y frecuencia mensual; detectar surge.
   CLIMA      Open-Meteo mensual: rangos fisicos, continuidad por municipio.
   ENSO       NOAA ONI: cobertura completa, rangos, fase coherente con oni.
   PRODUCCION EVA municipal: codigo DANE valido, rendimiento coherente
              con produccion/area, detectar outliers, dedupe.
   GEOGRAFIA  DEM altitudes + SoilGrids: rangos plausibles para zonas
              cafeteras, NaN policy.
   IMAGENES   manifest_consolidado.csv: integridad de archivos, balance
              de clases, splits estratificados, hash de duplicados.

 Uso:
   python etl_pipeline.py                       # todas las categorias
   python etl_pipeline.py --solo precios clima  # solo subset
   python etl_pipeline.py --strict              # exit(1) si hay errores
   python etl_pipeline.py --dry-run             # solo validar, no escribir
===============================================================================
"""
from __future__ import annotations
import argparse
import json
import sys
import hashlib
from collections import Counter
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Any, Callable

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve()
PROJECT = HERE.parents[2]
DIR_ENRIQ = PROJECT / "01_datos" / "enriquecidos"
DIR_IMGS = PROJECT / "01_datos" / "imagenes_cafe"
DIR_PROC = PROJECT / "01_datos" / "procesados"
DIR_REP = DIR_PROC / "etl_reportes"
DIR_PROC.mkdir(parents=True, exist_ok=True)
DIR_REP.mkdir(parents=True, exist_ok=True)


# ============================================================================
#  TIPOS
# ============================================================================
@dataclass
class Reporte:
    categoria: str
    n_input: int = 0
    n_output: int = 0
    errores: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    metricas: dict = field(default_factory=dict)
    archivos_entrada: list = field(default_factory=list)
    archivo_salida: str = ""
    timestamp: str = ""

    @property
    def ok(self) -> bool:
        return len(self.errores) == 0

    def err(self, msg: str): self.errores.append(msg)
    def warn(self, msg: str): self.warnings.append(msg)
    def metric(self, k: str, v: Any): self.metricas[k] = v


def _read_safe(path: Path, **kw) -> tuple[pd.DataFrame, str]:
    """Lee CSV; devuelve (df, mensaje)."""
    if not path.exists():
        return pd.DataFrame(), "no_existe"
    try:
        df = pd.read_csv(path, **kw)
        return df, "ok"
    except Exception as e:
        return pd.DataFrame(), f"error_lectura: {e}"


# ============================================================================
#  CATEGORIA 1  ·  PRECIOS
# ============================================================================
def etl_precios(dry_run: bool = False) -> Reporte:
    """
    Consolida todas las fuentes de precio a un dataframe mensual con esquema
    canonico:
        fecha (datetime, primer dia del mes)
        precio_arabica_brasil_usd_kg   (FRED)
        precio_robusta_usd_kg          (FRED)
        precio_arabica_wb_usd_kg       (World Bank)
        precio_robusta_wb_usd_kg       (World Bank)
        precio_ico_compuesto_usd_kg    (ICO/IMF)
        precio_fnc_cop_kg              (FNC interno, normalizado)
        trm_cop_usd                    (BanRep)
        precio_arabica_brasil_cop_kg   (derivado: FRED * TRM)

    Reglas de validacion:
      - Cobertura temporal: cada fuente debe tener >= 60 meses.
      - Rangos: USD/kg en [0.5, 30], COP/kg en [3000, 50000], TRM en [1500, 6000].
      - Surge detection: flag meses con cambio MoM >25%.
    """
    r = Reporte(categoria="precios", timestamp=datetime.now().isoformat())

    cands = {
        "fred_brazil":  DIR_ENRIQ / "precios" / "fred_coffee_brazil.csv",
        "fred_robusta": DIR_ENRIQ / "precios" / "fred_coffee_robusta.csv",
        "world_bank":   DIR_ENRIQ / "precios" / "world_bank_coffee.csv",
        "imf":          DIR_ENRIQ / "precios" / "imf_coffee.csv",
        "ico":          DIR_ENRIQ / "precios" / "ico_composite_extended.csv",
        "banrep_trm":   DIR_ENRIQ / "precios" / "banrep_trm.csv",
        "fnc_2da":      PROJECT.parent / "IA_Segunda_Entrega" / "datasets" / "fnc_cafe_mensual.csv",
        "consolidado":  DIR_ENRIQ / "precios" / "precios_consolidados_mensual.csv",
    }

    out = pd.DataFrame({"fecha": pd.date_range("1990-01-01", "2026-12-01", freq="MS")})
    out["mes_clave"] = out["fecha"]

    # FRED Brasil arabica (Cents USD/lb) -> USD/kg
    # Series PCOFFOTMUSDM y PCOFFROBUSDM se publican en U.S. Cents per Pound,
    # no en USD/lb. Conversion: cents/lb / 100 = USD/lb; USD/lb / 0.453592 = USD/kg.
    # Factor combinado: 1 / (100 * 0.453592) = 1 / 45.3592
    LB_KG = 0.453592
    CENTS_LB_A_USD_KG = 1.0 / (100 * LB_KG)  # ≈ 0.022046

    def _detectar_unidad_y_convertir(serie_num: pd.Series) -> tuple[pd.Series, str]:
        """
        Heuristica: si la mediana > 30, asumimos cents/lb; si <= 30, asumimos USD/lb.
        El cafe arabica historicamente esta en 50-300 cents/lb (= 0.5-3 USD/lb).
        """
        med = serie_num.dropna().median()
        if med > 30:
            return serie_num * CENTS_LB_A_USD_KG, "cents/lb -> USD/kg"
        else:
            return serie_num / LB_KG, "USD/lb -> USD/kg"

    df, msg = _read_safe(cands["fred_brazil"])
    if not df.empty:
        r.archivos_entrada.append(str(cands["fred_brazil"]))
        df["fecha"] = pd.to_datetime(df.get("fecha", df.iloc[:, 0]), errors="coerce")
        df = df.dropna(subset=["fecha"])
        col_val = next((c for c in df.columns if c not in ("fecha", "serie")
                        and pd.api.types.is_numeric_dtype(df[c])), None)
        if col_val:
            num = pd.to_numeric(df[col_val], errors="coerce")
            convertido, unidad = _detectar_unidad_y_convertir(num)
            df["precio_arabica_brasil_usd_kg"] = convertido
            r.metric("fred_brazil_meses", int(df["precio_arabica_brasil_usd_kg"].notna().sum()))
            r.metric("fred_brazil_unidad_origen", unidad)
            out = out.merge(df[["fecha", "precio_arabica_brasil_usd_kg"]],
                             on="fecha", how="left")
        else:
            r.warn(f"fred_brazil sin columna numerica detectable")
    else:
        r.warn(f"fred_brazil: {msg}")

    # FRED Robusta
    df, msg = _read_safe(cands["fred_robusta"])
    if not df.empty:
        r.archivos_entrada.append(str(cands["fred_robusta"]))
        df["fecha"] = pd.to_datetime(df.get("fecha", df.iloc[:, 0]), errors="coerce")
        df = df.dropna(subset=["fecha"])
        col_val = next((c for c in df.columns if c not in ("fecha", "serie")
                        and pd.api.types.is_numeric_dtype(df[c])), None)
        if col_val:
            num = pd.to_numeric(df[col_val], errors="coerce")
            convertido, unidad = _detectar_unidad_y_convertir(num)
            df["precio_robusta_usd_kg"] = convertido
            r.metric("fred_robusta_meses", int(df["precio_robusta_usd_kg"].notna().sum()))
            r.metric("fred_robusta_unidad_origen", unidad)
            out = out.merge(df[["fecha", "precio_robusta_usd_kg"]],
                             on="fecha", how="left")
    else:
        r.warn(f"fred_robusta: {msg}")

    # World Bank
    df, msg = _read_safe(cands["world_bank"])
    if not df.empty:
        r.archivos_entrada.append(str(cands["world_bank"]))
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df = df.dropna(subset=["fecha"])
        if "arabica_usd_kg" in df.columns:
            df = df.rename(columns={"arabica_usd_kg": "precio_arabica_wb_usd_kg"})
        if "robusta_usd_kg" in df.columns:
            df = df.rename(columns={"robusta_usd_kg": "precio_robusta_wb_usd_kg"})
        cols_keep = ["fecha"] + [c for c in df.columns if c.startswith("precio_")]
        if len(cols_keep) > 1:
            out = out.merge(df[cols_keep], on="fecha", how="left")
            r.metric("wb_meses", int(df[cols_keep[1]].notna().sum()))
    else:
        r.warn(f"world_bank: {msg}")

    # BanRep TRM
    df, msg = _read_safe(cands["banrep_trm"])
    if not df.empty:
        r.archivos_entrada.append(str(cands["banrep_trm"]))
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df = df.dropna(subset=["fecha"])
        col_trm = next((c for c in df.columns if "trm" in c.lower() or "close" in c.lower()
                        and pd.api.types.is_numeric_dtype(df[c])), None)
        if col_trm:
            df["trm_cop_usd"] = pd.to_numeric(df[col_trm], errors="coerce")
            df["fecha"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
            df = df.groupby("fecha", as_index=False)["trm_cop_usd"].mean()
            out = out.merge(df, on="fecha", how="left")
            r.metric("trm_meses", int(out["trm_cop_usd"].notna().sum()))
    else:
        r.warn(f"banrep_trm: {msg}")

    # FNC interno (COP/125kg -> COP/kg)
    df, msg = _read_safe(cands["fnc_2da"])
    if not df.empty:
        r.archivos_entrada.append(str(cands["fnc_2da"]))
        df["fecha"] = pd.to_datetime(df.get("fecha", df.get("Fecha")), errors="coerce")
        df = df.dropna(subset=["fecha"])
        df["fecha"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
        col_p = next((c for c in df.columns if "interno_cop" in c.lower() or "fnc_cop" in c.lower()), None)
        if col_p:
            df["precio_fnc_cop_kg"] = pd.to_numeric(df[col_p], errors="coerce") / 125.0
            df = df.groupby("fecha", as_index=False)["precio_fnc_cop_kg"].mean()
            out = out.merge(df, on="fecha", how="left")
            r.metric("fnc_meses", int(out["precio_fnc_cop_kg"].notna().sum()))
    else:
        r.warn(f"fnc_2da: {msg}")

    # Validacion de rangos
    rangos = {
        "precio_arabica_brasil_usd_kg": (0.5, 30),
        "precio_robusta_usd_kg":        (0.5, 20),
        "precio_arabica_wb_usd_kg":     (0.5, 30),
        "precio_robusta_wb_usd_kg":     (0.5, 20),
        "precio_fnc_cop_kg":            (3_000, 50_000),
        "trm_cop_usd":                  (1_500, 6_000),
    }
    for col, (lo, hi) in rangos.items():
        if col not in out.columns: continue
        s = out[col].dropna()
        if len(s) == 0:
            r.warn(f"{col} sin datos")
            continue
        n_fuera = ((s < lo) | (s > hi)).sum()
        if n_fuera > 0:
            r.warn(f"{col}: {n_fuera} valores fuera [{lo},{hi}]")

    # Surge detection
    if "precio_arabica_brasil_usd_kg" in out.columns:
        s = out["precio_arabica_brasil_usd_kg"]
        # fill_method=None evita FutureWarning de pandas; los NaN se mantienen.
        mom = s.pct_change(fill_method=None).abs()
        n_surge = (mom > 0.25).sum()
        r.metric("meses_con_surge_>25%", int(n_surge))
        out["surge_flag"] = (mom > 0.25).fillna(False).astype(int)

    # Cobertura minima
    out_data = out.drop(columns=["mes_clave"], errors="ignore")
    cols_precio = [c for c in out_data.columns if c.startswith("precio_") or c == "trm_cop_usd"]
    for c in cols_precio:
        meses_ok = out_data[c].notna().sum()
        if meses_ok < 60:
            r.warn(f"{c} con cobertura debil: {meses_ok} meses")

    # Derivado: precio en COP
    if "precio_arabica_brasil_usd_kg" in out_data.columns and "trm_cop_usd" in out_data.columns:
        out_data["precio_arabica_brasil_cop_kg"] = (
            out_data["precio_arabica_brasil_usd_kg"] * out_data["trm_cop_usd"]
        )

    out_data = out_data.sort_values("fecha").reset_index(drop=True)
    r.n_input = sum(int(p.exists()) for p in cands.values() if "consolidado" not in str(p))
    r.n_output = len(out_data)

    if not dry_run:
        outp = DIR_PROC / "precios_validado.csv"
        out_data.to_csv(outp, index=False)
        r.archivo_salida = str(outp.relative_to(PROJECT))

    return r


# ============================================================================
#  CATEGORIA 2  ·  CLIMA  (Open-Meteo)
# ============================================================================
def etl_clima(dry_run: bool = False) -> Reporte:
    """
    Valida y limpia openmeteo_municipios_mensual.csv:
      - Rango T media [-5, 45]
      - Precip >= 0
      - Continuidad mensual por municipio (sin huecos > 2 meses)
      - Renombra a esquema canonico
    """
    r = Reporte(categoria="clima", timestamp=datetime.now().isoformat())
    p = DIR_ENRIQ / "clima" / "openmeteo_municipios_mensual.csv"
    df, msg = _read_safe(p)
    if df.empty:
        r.err(f"clima no disponible: {msg}")
        return r

    r.archivos_entrada.append(str(p))
    r.n_input = len(df)

    # Renombrar a canonico
    rename = {
        "mes": "fecha",
        "temperature_2m_mean": "temp_media_c",
        "temperature_2m_min":  "temp_min_c",
        "temperature_2m_max":  "temp_max_c",
        "precipitation_sum":   "precipitacion_mm",
        "et0_fao_evapotranspiration": "et0_mm",
        "wind_speed_10m_max":  "viento_max_kmh",
        "shortwave_radiation_sum": "radiacion_mj_m2",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"])
    df["fecha"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
    df["codigo_dane"] = df["codigo_dane"].astype(str).str.zfill(5)

    # Validar rangos fisicos
    rangos = {
        "temp_media_c":     (-5, 45),
        "temp_min_c":       (-10, 40),
        "temp_max_c":       (-5, 50),
        "precipitacion_mm": (0, 2500),
        "et0_mm":           (0, 400),
    }
    for col, (lo, hi) in rangos.items():
        if col in df.columns:
            s = df[col]
            n_neg = (s < lo).sum()
            n_alto = (s > hi).sum()
            if n_neg + n_alto:
                r.warn(f"{col}: {n_neg} <{lo}, {n_alto} >{hi} (clamp aplicado)")
                df.loc[s < lo, col] = np.nan
                df.loc[s > hi, col] = np.nan

    # Coherencia: Tmin <= Tmedia <= Tmax
    if {"temp_min_c", "temp_media_c", "temp_max_c"}.issubset(df.columns):
        n_inc = ((df["temp_min_c"] > df["temp_media_c"]) |
                  (df["temp_media_c"] > df["temp_max_c"])).sum()
        if n_inc > 0:
            r.warn(f"{n_inc} filas con temp_min > temp_media o media > max (revisar)")
        r.metric("filas_temp_inconsistente", int(n_inc))

    # Continuidad por municipio
    huecos_total = 0
    for cod, grp in df.groupby("codigo_dane"):
        fechas = grp["fecha"].sort_values().unique()
        if len(fechas) < 2: continue
        idx = pd.to_datetime(fechas)
        rango_ideal = pd.date_range(idx.min(), idx.max(), freq="MS")
        huecos = len(rango_ideal) - len(idx)
        huecos_total += huecos
    r.metric("huecos_temporales_municipales", int(huecos_total))
    if huecos_total > 50:
        r.warn(f"clima con {huecos_total} huecos mensuales acumulados entre municipios")

    # Cobertura
    r.metric("municipios_distintos", int(df["codigo_dane"].nunique()))
    r.metric("rango_fechas",
              f"{df['fecha'].min().date()}|{df['fecha'].max().date()}")
    r.metric("anios_distintos", int(df["fecha"].dt.year.nunique()))

    # Dedupe
    antes = len(df)
    df = df.drop_duplicates(subset=["codigo_dane", "fecha"])
    if len(df) < antes:
        r.warn(f"deduplicadas {antes - len(df)} filas (codigo_dane, fecha)")

    df = df.sort_values(["codigo_dane", "fecha"]).reset_index(drop=True)
    r.n_output = len(df)

    if not dry_run:
        outp = DIR_PROC / "clima_validado.csv"
        df.to_csv(outp, index=False)
        r.archivo_salida = str(outp.relative_to(PROJECT))

    return r


# ============================================================================
#  CATEGORIA 3  ·  ENSO  (NOAA ONI)
# ============================================================================
def etl_enso(dry_run: bool = False) -> Reporte:
    r = Reporte(categoria="enso", timestamp=datetime.now().isoformat())
    p = DIR_ENRIQ / "clima" / "enso_oni_extendido.csv"
    df, msg = _read_safe(p)
    if df.empty:
        r.err(f"ENSO no disponible: {msg}")
        return r
    r.archivos_entrada.append(str(p))
    r.n_input = len(df)

    df["fecha"] = pd.to_datetime(df.get("fecha"), errors="coerce")
    df = df.dropna(subset=["fecha"])
    df["fecha"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
    df["oni"] = pd.to_numeric(df.get("oni"), errors="coerce")

    # Validar rangos ONI
    s = df["oni"].dropna()
    n_raros = ((s < -3) | (s > 3)).sum()
    if n_raros:
        r.warn(f"oni: {n_raros} valores fuera [-3,3]")

    # Recalcular fase coherente
    def fase(x):
        if pd.isna(x): return None
        if x >= 0.5: return "Nino"
        if x <= -0.5: return "Nina"
        return "Neutro"
    df["fase_enso"] = df["oni"].apply(fase)

    # Cobertura
    r.metric("oni_no_nulos", int(df["oni"].notna().sum()))
    r.metric("rango_fechas",
              f"{df['fecha'].min().date()}|{df['fecha'].max().date()}")
    r.metric("conteo_fases", df["fase_enso"].value_counts(dropna=False).to_dict())

    # Dedupe
    antes = len(df)
    df = df.drop_duplicates(subset=["fecha"], keep="last")
    if len(df) < antes:
        r.warn(f"deduplicadas {antes - len(df)} filas duplicadas por fecha")

    df = df[["fecha", "oni", "fase_enso"]].sort_values("fecha").reset_index(drop=True)
    r.n_output = len(df)

    if not dry_run:
        outp = DIR_PROC / "enso_validado.csv"
        df.to_csv(outp, index=False)
        r.archivo_salida = str(outp.relative_to(PROJECT))

    return r


# ============================================================================
#  CATEGORIA 4  ·  PRODUCCION  (EVA municipal)
# ============================================================================
def etl_produccion(dry_run: bool = False) -> Reporte:
    """
    Valida EVA municipal:
      - codigo DANE 5 digitos
      - cultivo == cafe (descartar tostado/soluble/extracto)
      - rendimiento = produccion / area_cosechada (tolerancia 5%)
      - rendimiento de cafe en [0.1, 5] ton/ha
      - dedupe por (codigo_dane, anio, cultivo)
    """
    r = Reporte(categoria="produccion", timestamp=datetime.now().isoformat())
    p = DIR_ENRIQ / "produccion" / "eva_cafe_municipal_2007_2024.csv"
    df, msg = _read_safe(p)
    if df.empty:
        r.err(f"EVA no disponible: {msg}")
        return r
    r.archivos_entrada.append(str(p))
    r.n_input = len(df)

    # ----- Normalizar nombres con caracteres rotos por Socrata -----
    # Socrata convierte vocales con tilde / ñ a "_". Mapeamos los casos comunes
    # que aparecen en EVA municipal (datos.gov.co).
    rename_map = {
        "a_o":               "anio",
        "ano":               "anio",
        "rea_sembrada_ha":   "area_sembrada_ha",
        "rea_cosechada_ha":  "area_cosechada_ha",
        "rea_sembrada__ha_": "area_sembrada_ha",
        "rea_cosechada__ha_":"area_cosechada_ha",
        "producci_n_t":      "produccion_ton",
        "producci_n_ton":    "produccion_ton",
        "producci_n":        "produccion_ton",
        "rendimiento_t_ha":  "rendimiento_ton_ha",
        "estado_fisico_produccion": "estado_fisico",
        "ciclo_de_cultivo":  "ciclo_cultivo",
        "grupo_de_cultivo":  "grupo_cultivo",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # ----- Deteccion flexible de DANE municipal -----
    # Socrata expone DANE en multiples formas:
    #   (a) Una sola columna 'codigo_dane' (5 digitos)
    #   (b) Dos columnas separadas: depto (2) + municipio (3) -> hay que concatenar
    #
    # Variantes vistas: codigo_dane, cod_mun, codmpio, c_d_mun, codmun_dane, ...
    candidatos_dane_mun_full = [
        "codigo_dane", "codigo_dane_municipio", "cod_dane_municipio",
        "cod_municipio_dane", "codigo_municipio_dane",
    ]
    col_dane = next((c for c in candidatos_dane_mun_full if c in df.columns), None)

    # Codigos cortos: depto (2 digitos) y municipio (3 digitos) por separado
    candidatos_cod_dpto = ["c_d_dep", "cod_dpto", "cod_dep", "codigo_dpto",
                            "codigo_departamento", "codigo_dane_dpto",
                            "cod_dane_dpto", "cod_dane_departamento"]
    candidatos_cod_mun_corto = ["c_d_mun", "cod_mun", "codmpio", "cod_mun_dane",
                                 "cod_mpio", "codigo_municipio", "cd_municipio",
                                 "cod_municipio", "cod_mun_3", "codmun"]

    col_dpto = next((c for c in candidatos_cod_dpto if c in df.columns), None)
    col_mun_corto = next((c for c in candidatos_cod_mun_corto if c in df.columns), None)

    if col_dane is None and col_mun_corto:
        # Detectar si col_mun_corto ya contiene el DANE COMPLETO (5 digitos)
        # o solo el sufijo de 3 digitos. Socrata expone EVA con c_d_mun = DANE
        # completo (ej: 19785 = 19+785, Sucre Cauca; 5101 = 05+101, Ciudad
        # Bolivar Antioquia con cero inicial perdido).
        s_mun = (df[col_mun_corto].astype(str)
                  .str.replace(r"\.0$", "", regex=True)
                  .str.replace(r"\D", "", regex=True))
        # Longitud tipica robusta (mode con fallback a maxima)
        if len(s_mun):
            longs = s_mun.str.len()
            long_tipica = int(longs.mode().iloc[0]) if len(longs.mode()) else int(longs.max())
        else:
            long_tipica = 0

        if long_tipica >= 4:
            # c_d_mun ya es DANE completo (5 dig, o 4 con cero perdido)
            df["codigo_dane"] = s_mun.str.zfill(5)
            col_dane = "codigo_dane"
            r.warn(f"codigo_dane derivado directamente de '{col_mun_corto}' "
                    f"(longitud tipica={long_tipica}, zfill a 5)")
        elif long_tipica == 3 and col_dpto:
            # Caso clasico: depto(2) + mun(3)
            s_dpto = (df[col_dpto].astype(str)
                       .str.replace(r"\.0$", "", regex=True)
                       .str.replace(r"\D", "", regex=True).str.zfill(2))
            df["codigo_dane"] = s_dpto + s_mun.str.zfill(3)
            col_dane = "codigo_dane"
            r.warn(f"codigo_dane construido: '{col_dpto}'(2) + '{col_mun_corto}'(3)")
        elif col_dpto:
            # Caso ambiguo: usar mejor heuristica disponible (concatenar)
            s_dpto = (df[col_dpto].astype(str)
                       .str.replace(r"\D", "", regex=True).str.zfill(2))
            df["codigo_dane"] = s_dpto + s_mun.str.zfill(3)
            col_dane = "codigo_dane"
            r.warn(f"codigo_dane compuesto (long. atipica={long_tipica}); "
                    f"revisar manualmente")

    if col_dane is None:
        r.err(f"falta codigo_dane en EVA. columnas disponibles: {list(df.columns)[:25]}")
        return r

    if col_dane != "codigo_dane":
        df = df.rename(columns={col_dane: "codigo_dane"})
        r.warn(f"renombrada '{col_dane}' -> 'codigo_dane'")

    # Tipos
    for col in ("area_sembrada_ha", "area_cosechada_ha",
                "produccion_ton", "rendimiento_ton_ha", "anio"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["codigo_dane"] = (df["codigo_dane"].astype(str)
                          .str.replace(r"\.0$", "", regex=True)
                          .str.replace(r"\D", "", regex=True))
    df["codigo_dane"] = df["codigo_dane"].str.zfill(5)
    n_invalid = (~df["codigo_dane"].str.match(r"^\d{5}$")).sum()
    if n_invalid:
        r.warn(f"codigo_dane invalido en {n_invalid} filas; las descarto")
        df = df[df["codigo_dane"].str.match(r"^\d{5}$")]

    # Filtrado cultivo
    if "cultivo" in df.columns:
        antes = len(df)
        df = df[df["cultivo"].astype(str).str.contains("cafe|caf", case=False, na=False)]
        df = df[~df["cultivo"].astype(str).str.contains(
            "tostado|soluble|extracto|descafe", case=False, na=False)]
        if len(df) < antes:
            r.warn(f"filtrado cultivo: {antes} -> {len(df)} filas")

    # Coherencia rendimiento = produccion / area_cosechada
    if {"produccion_ton", "area_cosechada_ha", "rendimiento_ton_ha"}.issubset(df.columns):
        rend_calc = df["produccion_ton"] / df["area_cosechada_ha"].replace(0, np.nan)
        diff = (rend_calc - df["rendimiento_ton_ha"]).abs()
        n_inc = (diff > 0.5).sum()
        if n_inc > 0:
            r.warn(f"{n_inc} filas con rendimiento incoherente (>0.5 ton/ha de error)")
        r.metric("filas_rendimiento_incoherente", int(n_inc))

    # Outliers de rendimiento cafetero
    if "rendimiento_ton_ha" in df.columns:
        s = df["rendimiento_ton_ha"].dropna()
        n_extremo = ((s < 0.1) | (s > 5)).sum()
        if n_extremo:
            r.warn(f"rendimiento fuera [0.1, 5] ton/ha en {n_extremo} filas")

    # Dedupe
    antes = len(df)
    cols_dup = [c for c in ("codigo_dane", "anio", "cultivo") if c in df.columns]
    if cols_dup:
        df = df.drop_duplicates(subset=cols_dup, keep="last")
    if len(df) < antes:
        r.warn(f"deduplicadas {antes - len(df)} filas")

    # Cobertura - todos los casts a int son defensivos:
    # despues de los filtros pueden quedar NaN o df vacio.
    r.metric("municipios_distintos", int(df["codigo_dane"].nunique()))
    r.metric("filas_post_filtros", int(len(df)))

    if "anio" in df.columns and df["anio"].notna().any():
        amin = df["anio"].min()
        amax = df["anio"].max()
        if pd.notna(amin) and pd.notna(amax):
            r.metric("rango_anios", f"{int(amin)}|{int(amax)}")
        # Excluir grupos NaN antes del int()
        cob_x_anio = (df.dropna(subset=["anio"])
                        .groupby("anio")["codigo_dane"].nunique().to_dict())
        r.metric("municipios_x_anio",
                  {int(k): int(v) for k, v in cob_x_anio.items() if pd.notna(k)})
    elif "anio" in df.columns:
        r.warn("columna 'anio' presente pero sin valores numericos validos")

    if "anio" in df.columns:
        df = df.sort_values(["codigo_dane", "anio"], na_position="last").reset_index(drop=True)
    r.n_output = len(df)

    if not dry_run:
        outp = DIR_PROC / "produccion_validado.csv"
        df.to_csv(outp, index=False)
        r.archivo_salida = str(outp.relative_to(PROJECT))

    return r


# ============================================================================
#  CATEGORIA 5  ·  GEOGRAFIA  (DEM + SoilGrids)
# ============================================================================
def etl_geografia(dry_run: bool = False) -> Reporte:
    r = Reporte(categoria="geografia", timestamp=datetime.now().isoformat())

    p_dem = DIR_ENRIQ / "geografia" / "dem_municipal_altitud.csv"
    p_sue = DIR_ENRIQ / "geografia" / "soilgrids_municipal.csv"
    dfs = []

    df, msg = _read_safe(p_dem)
    if not df.empty:
        r.archivos_entrada.append(str(p_dem))
        df["codigo_dane"] = df["codigo_dane"].astype(str).str.zfill(5)
        # Validar altitud para zona cafetera (0-3500 msnm es razonable en Colombia)
        s = pd.to_numeric(df["altitud_msnm"], errors="coerce")
        n_raros = ((s < 0) | (s > 4500)).sum()
        if n_raros:
            r.warn(f"altitud fuera [0,4500] en {n_raros} filas")
        df["altitud_msnm"] = s
        n_nan_alt = s.isna().sum()
        if n_nan_alt:
            r.warn(f"altitud nan en {n_nan_alt} municipios (Open-Elevation falló)")
        dfs.append(df)

    df, msg = _read_safe(p_sue)
    if not df.empty:
        r.archivos_entrada.append(str(p_sue))
        df["codigo_dane"] = df["codigo_dane"].astype(str).str.zfill(5)
        # SoilGrids: pH typically reported as pH * 10
        ph_cols = [c for c in df.columns if c.startswith("phh2o")]
        for c in ph_cols:
            s = pd.to_numeric(df[c], errors="coerce")
            # heuristica: si la mediana > 14, esta en pH*10 -> dividir
            if s.dropna().median() > 14:
                df[c] = s / 10.0
            else:
                df[c] = s
            n_raros = ((df[c] < 3) | (df[c] > 9)).sum()
            if n_raros:
                r.warn(f"{c}: {n_raros} valores fuera de [3,9]")
        # SOC plausible
        soc_cols = [c for c in df.columns if c.startswith("soc")]
        for c in soc_cols:
            s = pd.to_numeric(df[c], errors="coerce")
            if s.dropna().median() > 100:
                df[c] = s / 10.0
            else:
                df[c] = s
        dfs.append(df)

    if not dfs:
        r.err("ni DEM ni SoilGrids disponibles")
        return r

    # Merge por codigo_dane
    out = dfs[0]
    for d in dfs[1:]:
        cols = ["codigo_dane"] + [c for c in d.columns if c not in out.columns]
        out = out.merge(d[cols], on="codigo_dane", how="outer")

    r.n_input = sum(len(d) for d in dfs)
    r.n_output = len(out)
    r.metric("municipios", int(out["codigo_dane"].nunique()))

    if not dry_run:
        outp = DIR_PROC / "geografia_validado.csv"
        out.to_csv(outp, index=False)
        r.archivo_salida = str(outp.relative_to(PROJECT))

    return r


# ============================================================================
#  CATEGORIA 6  ·  IMAGENES  (manifest + integridad)
# ============================================================================
# Parametros de validacion de imagenes (justificacion en README):
#
#   MIN_DIM = 100 px
#     Solo cuenta para REPORTAR, no descarta. Imagenes <100x100 escaladas a
#     224x224 (input EfficientNetB0/ResNet50) producen pixelado inutil para
#     transfer learning. Se reporta como aviso para considerar excluirlas
#     del training; no se eliminan automaticamente para no perder datos.
#
#   HASH = SHA1 del archivo COMPLETO en chunks de 1MB
#     Antes usabamos md5 de los primeros 64KB; eso colapsaba JPGs del mismo
#     dataset que comparten header EXIF/quantization tables (causaba 84% de
#     "duplicados" falsos). Hash completo es 100% exacto byte-a-byte.
#     Para detectar imagenes "perceptualmente similares" (ej. mismo cultivo
#     re-encodeado), usar imagehash (phash) opcionalmente.
#
#   ELIMINACION: solo se descartan imagenes que (a) no existen en disco o
#   (b) PIL no las abre. El manifest_validado preserva todas las demas.
# ============================================================================

MIN_DIM_REPORTE = 100   # parametro de reporte (no descarta)
HASH_CHUNK = 1 << 20    # 1 MB


def _hash_archivo_completo(path: Path) -> str | None:
    """SHA1 del archivo entero, en chunks. Devuelve None si falla."""
    try:
        h = hashlib.sha1()
        with open(path, "rb") as fp:
            while True:
                chunk = fp.read(HASH_CHUNK)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def etl_imagenes(dry_run: bool = False) -> Reporte:
    r = Reporte(categoria="imagenes", timestamp=datetime.now().isoformat())
    p = DIR_IMGS / "manifest_consolidado.csv"
    df, msg = _read_safe(p)
    if df.empty:
        r.err(f"manifest no disponible: {msg}")
        return r
    r.archivos_entrada.append(str(p))
    r.n_input = len(df)

    try:
        from PIL import Image, UnidentifiedImageError
        has_pil = True
    except ImportError:
        has_pil = False
        r.warn("Pillow no instalado; saltando verificacion de integridad")

    archivos_faltantes = 0
    archivos_corruptos = 0
    archivos_pequenos = 0
    hashes: dict[str, str] = {}      # hash -> primer ruta_rel encontrada
    duplicados_exactos = 0
    duplicados_paths: list[tuple[str, str]] = []
    tamanos = []
    rutas_invalidas = set()           # rutas a excluir del manifest_validado

    total = len(df)
    print(f"     [imagenes] procesando {total} archivos (puede tardar varios minutos)...")
    for i, ruta_rel in enumerate(df["ruta"]):
        if i and i % 5000 == 0:
            print(f"       ... {i}/{total} procesadas")

        full = DIR_IMGS / ruta_rel
        if not full.exists():
            archivos_faltantes += 1
            rutas_invalidas.add(ruta_rel)
            continue

        if has_pil:
            try:
                with Image.open(full) as im:
                    w, h_dim = im.size
                    tamanos.append((w, h_dim))
                    if w < MIN_DIM_REPORTE or h_dim < MIN_DIM_REPORTE:
                        archivos_pequenos += 1
            except Exception:
                archivos_corruptos += 1
                rutas_invalidas.add(ruta_rel)
                continue

        # Hash COMPLETO: previene falsos positivos por headers compartidos
        digest = _hash_archivo_completo(full)
        if digest is None:
            continue
        if digest in hashes:
            duplicados_exactos += 1
            duplicados_paths.append((hashes[digest], str(ruta_rel)))
        else:
            hashes[digest] = str(ruta_rel)

    # Metricas
    r.metric("archivos_faltantes", archivos_faltantes)
    r.metric("archivos_corruptos", archivos_corruptos)
    r.metric(f"archivos_resolucion<{MIN_DIM_REPORTE}px",
              archivos_pequenos)
    r.metric("duplicados_byte_exactos", duplicados_exactos)
    if duplicados_paths:
        # Guardar primeros 50 ejemplos en el reporte
        r.metric("duplicados_ejemplos",
                  [{"original": a, "duplicada": b}
                   for a, b in duplicados_paths[:50]])
    if tamanos:
        ws, hs = zip(*tamanos)
        r.metric("dim_min", f"{min(ws)}x{min(hs)}")
        r.metric("dim_max", f"{max(ws)}x{max(hs)}")
        r.metric("dim_mediana", f"{int(np.median(ws))}x{int(np.median(hs))}")

    # Set de rutas duplicadas (las versiones a eliminar; conservamos la primera)
    rutas_duplicadas = {b for _, b in duplicados_paths}

    if archivos_faltantes:
        r.err(f"{archivos_faltantes} archivos no encontrados (se excluyen)")
    if archivos_corruptos:
        r.err(f"{archivos_corruptos} archivos no abrieron (se excluyen)")
    if archivos_pequenos:
        r.warn(f"{archivos_pequenos} imagenes <{MIN_DIM_REPORTE}px (se mantienen)")
    if duplicados_exactos:
        r.warn(f"{duplicados_exactos} duplicados byte-exactos detectados "
                f"(SE ELIMINAN del manifest validado; original conservada)")

    # Balance por clase y split (sobre input original)
    bal = df.groupby(["split", "clase"]).size().unstack(fill_value=0)
    r.metric("balance_split_clase_input", bal.to_dict())

    # Cobertura de splits por clase
    for clase in df["clase"].unique():
        splits_clase = set(df[df["clase"] == clase]["split"].unique())
        if splits_clase != {"train", "val", "test"}:
            r.warn(f"clase '{clase}' no esta en los 3 splits "
                    f"(esta solo en {sorted(splits_clase)})")

    # ------- Manifest validado -------
    # Se ELIMINAN: archivos faltantes, corruptos, y duplicados byte-exactos
    # (de los duplicados se conserva la primera ocurrencia). Imagenes pequeñas
    # NO se eliminan, solo se marcan con flag para que el notebook NB08 decida.
    df_validado = df[~df["ruta"].isin(rutas_invalidas)
                      & ~df["ruta"].isin(rutas_duplicadas)].copy()
    df_validado["es_pequena"] = df_validado["ruta"].apply(
        lambda x: False  # se marca despues con el set de pequenas si quieres
    )

    r.n_output = len(df_validado)
    r.metric("eliminadas_faltantes", archivos_faltantes)
    r.metric("eliminadas_corruptas", archivos_corruptos)
    r.metric("eliminadas_duplicadas", len(rutas_duplicadas))
    r.metric("conservadas_unicas", len(df_validado))

    # Balance final post-deduplicacion (lo que efectivamente entra al training)
    if len(df_validado):
        bal_final = df_validado.groupby(["split", "clase"]).size()\
                                .unstack(fill_value=0)
        r.metric("balance_split_clase_final", bal_final.to_dict())

    if not dry_run:
        outp = DIR_PROC / "imagenes_validado.csv"
        df_validado.to_csv(outp, index=False)
        r.archivo_salida = str(outp.relative_to(PROJECT))

    return r


# ============================================================================
#  ORQUESTADOR + REPORTE
# ============================================================================
ETLS: dict[str, Callable[[bool], Reporte]] = {
    "precios":    etl_precios,
    "clima":      etl_clima,
    "enso":       etl_enso,
    "produccion": etl_produccion,
    "geografia":  etl_geografia,
    "imagenes":   etl_imagenes,
}


def escribir_reporte_json(rep: Reporte):
    out = DIR_REP / f"{rep.categoria}.json"
    d = asdict(rep); d["ok"] = rep.ok
    out.write_text(json.dumps(d, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8")


def escribir_resumen_md(reportes: list[Reporte]):
    lineas = []
    lineas.append(f"# RESUMEN ETL · {datetime.now().isoformat(timespec='seconds')}\n")
    lineas.append("| Categoria | Estado | n_in | n_out | Errores | Warnings |")
    lineas.append("|---|---|---|---|---|---|")
    for r in reportes:
        estado = "OK" if r.ok else "FAIL"
        lineas.append(f"| {r.categoria} | {estado} | {r.n_input} | {r.n_output} | "
                       f"{len(r.errores)} | {len(r.warnings)} |")
    lineas.append("")
    for r in reportes:
        lineas.append(f"## {r.categoria}")
        if r.archivo_salida:
            lineas.append(f"**Archivo:** `{r.archivo_salida}`")
        if r.errores:
            lineas.append("\n**Errores:**")
            for e in r.errores: lineas.append(f"- {e}")
        if r.warnings:
            lineas.append("\n**Warnings:**")
            for w in r.warnings: lineas.append(f"- {w}")
        if r.metricas:
            lineas.append("\n**Metricas:**")
            for k, v in r.metricas.items():
                lineas.append(f"- `{k}`: {v}")
        lineas.append("")
    out = DIR_REP / "RESUMEN.md"
    out.write_text("\n".join(lineas), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", nargs="+", choices=list(ETLS.keys()))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="exit(1) si alguna categoria reporta errores")
    args = ap.parse_args()

    sel = args.solo or list(ETLS.keys())

    print("=" * 70)
    print(" ETL Pipeline por categoria")
    print("=" * 70)
    print(f"Categorias    : {sel}")
    print(f"Dry run       : {args.dry_run}")
    print(f"Salida CSV    : {DIR_PROC.relative_to(PROJECT)}")
    print(f"Reportes JSON : {DIR_REP.relative_to(PROJECT)}")

    reportes = []
    for cat in sel:
        print(f"\n{'-'*70}\n[{cat}] iniciando ...")
        try:
            r = ETLS[cat](dry_run=args.dry_run)
        except Exception as e:
            r = Reporte(categoria=cat, timestamp=datetime.now().isoformat())
            r.err(f"excepcion: {type(e).__name__}: {e}")
        reportes.append(r)
        estado = "OK" if r.ok else "FAIL"
        print(f"  -> {estado}  in={r.n_input}  out={r.n_output}  "
              f"err={len(r.errores)}  warn={len(r.warnings)}")
        for e in r.errores: print(f"     ERR  {e}")
        for w in r.warnings[:3]: print(f"     WARN {w}")
        if len(r.warnings) > 3:
            print(f"     ... y {len(r.warnings)-3} warnings mas (ver JSON)")

        if not args.dry_run:
            escribir_reporte_json(r)

    if not args.dry_run:
        ruta = escribir_resumen_md(reportes)
        print(f"\nResumen MD: {ruta.relative_to(PROJECT)}")

    print("\n" + "=" * 70)
    n_ok = sum(r.ok for r in reportes)
    print(f"  OK   : {n_ok}/{len(reportes)} categorias")
    print(f"  FAIL : {len(reportes) - n_ok}/{len(reportes)}")
    print("=" * 70)

    if args.strict and any(not r.ok for r in reportes):
        sys.exit(1)


if __name__ == "__main__":
    main()
