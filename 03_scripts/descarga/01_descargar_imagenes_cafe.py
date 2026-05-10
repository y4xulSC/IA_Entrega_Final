"""
===============================================================================
 01_descargar_imagenes_cafe.py
===============================================================================
 Descarga datasets publicos de hojas de cafe con/sin enfermedad.

 v3 (2026-05-08): limpia zips invalidos al inicio, condicion de skip mas
                  inteligente (requiere imagenes reales), maneja correctamente
                  el caso de Kaggle 403 con instrucciones para aceptar terminos.

 Datasets:
   1. RoCoLe (Mendeley)    public-api JSON
   2. BRACOL (Kaggle)
   3. JMuBEN (Mendeley)
   4. Coffee Leaf (Kaggle)
   5. CALIBRO (local 2da entrega)
===============================================================================
"""
from __future__ import annotations
from pathlib import Path
import argparse
import csv
import sys
import zipfile

import requests

from _config import UA, setup_kaggle

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
RAW_DIR = PROJECT_ROOT / "01_datos" / "imagenes_cafe" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_RAW = PROJECT_ROOT / "01_datos" / "imagenes_cafe" / "manifest_raw.csv"

EXT_IMG = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


# helpers
def _es_zip_valido(path):
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        return magic in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
    except Exception:
        return False


def _tiene_imagenes(carpeta):
    """True si la carpeta contiene al menos una imagen real."""
    if not carpeta.exists():
        return False
    for p in carpeta.rglob("*"):
        if p.suffix.lower() in EXT_IMG:
            return True
    return False


def _limpiar_zips_invalidos(carpeta):
    """Vacia archivos .zip que no son ZIP real (HTML/JSON disfrazados)."""
    if not carpeta.exists():
        return
    for p in carpeta.glob("*.zip"):
        if not _es_zip_valido(p):
            print("   limpiando zip invalido " + p.name)
            try:
                p.unlink()
            except Exception:
                try:
                    p.write_bytes(b"")
                except Exception:
                    pass


def _descargar_archivo(url, dest, *, label="", timeout=300):
    try:
        with requests.get(url, headers=UA, stream=True, timeout=timeout,
                          allow_redirects=True) as r:
            r.raise_for_status()
            ctype = r.headers.get("Content-Type", "").lower()
            if "html" in ctype or "json" in ctype:
                print("   FAIL " + label + ": el servidor devolvio " + ctype)
                return False
            total = int(r.headers.get("content-length", 0))
            done = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = done / total * 100
                        msg = ("     " + label + " " + ("%5.1f" % pct) + "%  " +
                               ("%.1f" % (done / 1e6)) + "/" +
                               ("%.1f" % (total / 1e6)) + " MB")
                        print(msg, end="\r")
            print()
        return True
    except Exception as e:
        print("   FAIL " + label + " " + str(e))
        return False


def _extraer_zip(zip_path, dest):
    if not _es_zip_valido(zip_path):
        print("   FAIL " + zip_path.name + " no es ZIP valido")
        try:
            zip_path.unlink()
        except Exception:
            pass
        return False
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest)
        zip_path.unlink()
        return True
    except Exception as e:
        print("   FAIL extraccion " + zip_path.name + ": " + str(e))
        return False


# Mendeley API
def _mendeley_files(dataset_id, version=None):
    """
    Devuelve SIEMPRE una lista de dicts (cada uno con 'filename', 'content_details', etc).
    Si la API devuelve un dict envoltorio, extrae la lista interna.
    """
    base = "https://data.mendeley.com/public-api/datasets"
    try:
        r = requests.get(base + "/" + dataset_id, headers=UA, timeout=60)
        r.raise_for_status()
        meta = r.json()
        versions = meta.get("versions") if isinstance(meta, dict) else []
        versions = versions or []
        if version is None:
            ver = max((v.get("version", 0) for v in versions
                       if isinstance(v, dict)), default=None)
        else:
            ver = version
        if ver is None:
            r2 = requests.get(base + "/" + dataset_id + "/files",
                              headers=UA, timeout=60)
        else:
            r2 = requests.get(base + "/" + dataset_id + "/files",
                              headers=UA, timeout=60,
                              params={"version": ver})
        r2.raise_for_status()
        body = r2.json()
        # Normalizar a lista de dicts
        if isinstance(body, list):
            files_list = body
        elif isinstance(body, dict):
            # Buscar la primera key que sea lista
            files_list = None
            for k in ("files", "results", "items", "data"):
                if k in body and isinstance(body[k], list):
                    files_list = body[k]
                    break
            if files_list is None:
                # Si todo el dict es un solo archivo, envuelvelo en lista
                files_list = [body] if "filename" in body else []
        else:
            files_list = []
        # Filtrar solo dicts (defensivo)
        return [f for f in files_list if isinstance(f, dict)]
    except Exception as e:
        print("   WARN Mendeley API " + dataset_id + ": " + str(e))
        return []


def _mendeley_download_url(dataset_id, content_details_id):
    return ("https://data.mendeley.com/public-api/datasets/" +
            dataset_id + "/files/" + content_details_id + "/file_downloaded")


# 1. ROCOLE
def descargar_rocole(out):
    """v4: Kaggle mirror primero, Mendeley API como fallback."""
    print("\n[1/4] RoCoLe ...")
    out.mkdir(parents=True, exist_ok=True)
    _limpiar_zips_invalidos(out)

    # 1. Kaggle primero (mas confiable)
    setup_kaggle()
    print("   probando Kaggle mirror nirmalsankalana/rocole-... ...")
    if _kaggle_download("nirmalsankalana/rocole-a-robusta-coffee-leaf-images-dataset", out):
        print("   OK RoCoLe (Kaggle mirror) en " + str(out))
        return True

    # 2. Mendeley como fallback
    print("   Kaggle fallo, intentando Mendeley API...")
    DATASET_ID = "c5yvn32dzg"
    files = _mendeley_files(DATASET_ID)
    if not files:
        print("   FAIL Mendeley: no se pudieron listar archivos")
        print("   Descarga manual: https://data.mendeley.com/datasets/c5yvn32dzg/2")
        return False

    candidatos = [f for f in files
                  if isinstance(f, dict) and
                  f.get("filename", "").lower().endswith(
                      (".zip", ".tar", ".tar.gz", ".rar"))]
    if not candidatos:
        candidatos = [f for f in files if isinstance(f, dict)]

    ok_total = False
    for f in candidatos:
        fname = f.get("filename", "rocole.zip")
        cdid = (f.get("content_details") or {}).get("id") or f.get("id")
        if not cdid:
            continue
        url = _mendeley_download_url(DATASET_ID, cdid)
        dest = out / fname
        size_mb = f.get("size", 0) / 1e6
        print("   descargando " + fname + " (" + ("%.1f" % size_mb) + " MB)...")
        if not _descargar_archivo(url, dest, label="RoCoLe"):
            continue
        if dest.suffix.lower() == ".zip":
            if _extraer_zip(dest, out):
                ok_total = True
        else:
            ok_total = True
    if ok_total:
        print("   OK RoCoLe Mendeley en " + str(out))
    else:
        print("   Descarga manual: https://data.mendeley.com/datasets/c5yvn32dzg/2")
    return ok_total


# Kaggle helper
def _kaggle_download(slug, out):
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        print("   FAIL falta libreria: pip install kaggle")
        return False
    try:
        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(slug, path=str(out), unzip=True, quiet=False)
        return True
    except Exception as e:
        msg = str(e)
        if "403" in msg or "Forbidden" in msg:
            print("   FAIL " + slug + ": 403 Forbidden")
            print("        ABRE en navegador: https://www.kaggle.com/datasets/" +
                  slug)
            print("        click en 'I Understand and Accept' / 'Download'")
            print("        luego reejecuta este script")
        else:
            print("   FAIL " + slug + ": " + msg)
        return False


# 2. BRACOL
def descargar_bracol(out):
    print("\n[2/4] BRACOL (Kaggle) ...")
    out.mkdir(parents=True, exist_ok=True)
    _limpiar_zips_invalidos(out)
    setup_kaggle()
    candidatos = [
        "jonatanfragoso/bracol-for-yolov8-detection",
        "badasstechie/coffee-leaf-disease",
        "rahmasleam/bracol",
        "olafkrastovski/coffee-leaf-disease-bracol",
    ]
    for slug in candidatos:
        print("   probando " + slug + " ...")
        if _kaggle_download(slug, out):
            print("   OK BRACOL (" + slug + ") en " + str(out))
            return True
    print("   Mirror Mendeley sin auth (manual):")
    print("   https://data.mendeley.com/datasets/yy2k5y8mxg/1")
    return False


# 3. JMuBEN
def descargar_jmuben(out):
    """v4: Kaggle mirror primero, Mendeley API como fallback."""
    print("\n[3/4] JMuBEN - dataset grande (~5GB) ...")
    out.mkdir(parents=True, exist_ok=True)
    _limpiar_zips_invalidos(out)

    # 1. Kaggle primero (mucho mas rapido y confiable que Mendeley para 5GB)
    setup_kaggle()
    print("   probando Kaggle mirror noamaanabdulazeem/jmuben-coffee-dataset ...")
    if _kaggle_download("noamaanabdulazeem/jmuben-coffee-dataset", out):
        print("   OK JMuBEN (Kaggle mirror) en " + str(out))
        return True

    # 2. Mendeley API como fallback
    print("   Kaggle fallo, intentando Mendeley API...")
    DATASETS = [("t2r6rszp5c", "JMuBEN"), ("tgv3zb82nd", "JMuBEN2")]
    ok_global = False
    for dsid, label in DATASETS:
        files = _mendeley_files(dsid)
        if not files:
            print("   WARN no pude listar " + label + " (" + dsid + ")")
            continue
        for f in files:
            if not isinstance(f, dict):
                continue
            fname = f.get("filename", label.lower() + ".zip")
            if not fname.lower().endswith((".zip", ".rar")):
                continue
            cdid = (f.get("content_details") or {}).get("id") or f.get("id")
            if not cdid:
                continue
            url = _mendeley_download_url(dsid, cdid)
            dest = out / fname
            size_mb = f.get("size", 0) / 1e6
            print("   descargando " + fname + " (" + ("%.0f" % size_mb) + " MB)...")
            if not _descargar_archivo(url, dest, label=fname, timeout=900):
                continue
            if _extraer_zip(dest, out):
                ok_global = True
    if ok_global:
        print("   OK JMuBEN en " + str(out))
    else:
        print("   Descarga manual: https://data.mendeley.com/datasets/t2r6rszp5c/1")
    return ok_global


# 4. Coffee Leaf
def descargar_coffee_leaf(out):
    print("\n[4/4] Coffee Leaf Diseases (Kaggle) ...")
    out.mkdir(parents=True, exist_ok=True)
    _limpiar_zips_invalidos(out)
    setup_kaggle()
    candidatos = [
        "prinprin/coffee-leaf-disease",
        "alvarole/coffee-leaf-diseases",
        "ahmadyousrydaboor/coffee-leaf-diseases",
        "aliaffan/coffee-leaf-diseases",
        "yosefelmosehy/coffee-leaf-images",
    ]
    for slug in candidatos:
        print("   probando " + slug + " ...")
        if _kaggle_download(slug, out):
            print("   OK " + slug + " descargado en " + str(out))
            return True
    return False


# Manifest
def construir_manifest_raw(raw_dir, out_csv):
    print("\n[manifest] Construyendo manifest_raw.csv ...")
    rows = []
    for ds_path in raw_dir.iterdir():
        if not ds_path.is_dir():
            continue
        ds_name = ds_path.name
        for img_path in ds_path.rglob("*"):
            if img_path.suffix.lower() not in EXT_IMG:
                continue
            try:
                rel_parts = img_path.relative_to(raw_dir).parts
                clase_raw = rel_parts[1] if len(rel_parts) > 2 else "?"
                rows.append({
                    "ruta_relativa": str(img_path.relative_to(raw_dir)),
                    "dataset": ds_name,
                    "clase_original": clase_raw,
                    "parte_planta": "hoja",
                    "formato": img_path.suffix.lower().lstrip("."),
                })
            except Exception:
                pass

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print("   OK " + str(len(rows)) + " imagenes en " + out_csv.name)
    else:
        print("   FAIL Sin imagenes encontradas")
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo", nargs="+", default=None,
        choices=["rocole", "bracol", "jmuben", "coffee_leaf"])
    parser.add_argument("--skip", nargs="+", default=[],
        choices=["rocole", "bracol", "jmuben", "coffee_leaf"])
    parser.add_argument("--force", action="store_true",
        help="Re-descargar aunque la carpeta tenga imagenes")
    args = parser.parse_args()

    print("=" * 70)
    print(" Descarga de datasets publicos de hojas de cafe - Entrega Final v3")
    print("=" * 70)
    print("Salida: " + str(RAW_DIR))

    DESCARGAS = {
        "rocole":      (RAW_DIR / "rocole",      descargar_rocole),
        "bracol":      (RAW_DIR / "bracol",      descargar_bracol),
        "jmuben":      (RAW_DIR / "jmuben",      descargar_jmuben),
        "coffee_leaf": (RAW_DIR / "coffee_leaf", descargar_coffee_leaf),
    }

    seleccionados = args.solo if args.solo else list(DESCARGAS.keys())
    seleccionados = [s for s in seleccionados if s not in args.skip]

    resultados = {}
    for nombre in seleccionados:
        out, fn = DESCARGAS[nombre]
        if not args.force and _tiene_imagenes(out):
            n_imgs = sum(1 for _ in out.rglob("*") if _.suffix.lower() in EXT_IMG)
            print("\n[skip] " + nombre + ": ya tiene " + str(n_imgs) +
                  " imagenes en " + str(out))
            resultados[nombre] = True
            continue
        resultados[nombre] = fn(out)

    n_imgs = construir_manifest_raw(RAW_DIR, MANIFEST_RAW)

    print("\n" + "=" * 70)
    print(" RESUMEN")
    print("=" * 70)
    for k, v in resultados.items():
        print("  " + k.ljust(15) + ": " + ("OK" if v else "FAIL"))
    print("\nSiguiente: python 06_consolidar_imagenes.py")

    if not any(resultados.values()) and n_imgs == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
