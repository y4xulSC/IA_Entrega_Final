"""
═══════════════════════════════════════════════════════════════════════════════
 01_descargar_imagenes_cafe.py
═══════════════════════════════════════════════════════════════════════════════
 Descarga datasets públicos de hojas de café con/sin enfermedad y los
 consolida en una estructura unificada para entrenar el CNN.

 RESUELVE: Limitación crítica de la 2da entrega — solo 47 imágenes CALIBRO
 (Acc=48.9%, R²=−0.45). Tras este script habrá ~10000 imágenes balanceadas.

 Datasets descargados (todos públicos):

   1. RoCoLe — Robusta Coffee Leaf images (Mendeley)
      https://data.mendeley.com/datasets/c5yvn32dzg/2
      ~1560 imgs · roya/sano/red-spider-mite

   2. BRACOL — Brazilian Arabica Coffee Leaf Disease (GitHub)
      https://github.com/esuiip/leaf-disease
      Mirror Kaggle: badasstechie/coffee-leaf-disease
      ~4707 imgs · roya/miner/cercospora/phoma/sano

   3. JMuBEN / JMuBEN2 (Mendeley)
      https://data.mendeley.com/datasets/tgv3zb82nd/1
      ~58k imgs · cercospora/leaf-rust/miner/phoma/sano

   4. Coffee Leaf Diseases — Kaggle (alphabetical)
      https://www.kaggle.com/datasets/alvarole/coffee-leaf-diseases
      ~5000 imgs

   5. CALIBRO — local, ya en la 2da entrega (47 imgs Colombia)

 Uso:
   python 01_descargar_imagenes_cafe.py
   python 01_descargar_imagenes_cafe.py --solo rocole bracol
   python 01_descargar_imagenes_cafe.py --skip jmuben

 Output:
   01_datos/imagenes_cafe/raw/{rocole,bracol,jmuben,coffee_leaf,calibro}/
   01_datos/imagenes_cafe/manifest_raw.csv

 Cita ROCOLE: Parraga-Alava et al. (2019). RoCoLe: A robusta coffee leaf
   images dataset for evaluation of machine learning based methods in plant
   diseases recognition. Data in Brief.
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
from pathlib import Path
import argparse
import shutil
import zipfile
import sys
import os
import csv
from typing import Optional

# ──────── rutas base ────────
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]                         # .../IA_Entrega_Final
RAW_DIR = PROJECT_ROOT / "01_datos" / "imagenes_cafe" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Manifest unificado de raw (sin filtrar/balancear)
MANIFEST_RAW = PROJECT_ROOT / "01_datos" / "imagenes_cafe" / "manifest_raw.csv"


# ╔════════════════════════════════════════════════════════════════════════════
# ║ 1. ROCOLE
# ╚════════════════════════════════════════════════════════════════════════════
def descargar_rocole(out: Path) -> bool:
    """RoCoLe via Mendeley (público, sin auth)."""
    import requests
    print("\n[1/4] RoCoLe (Mendeley) ...")
    out.mkdir(parents=True, exist_ok=True)
    URL = ("https://data.mendeley.com/public-files/datasets/c5yvn32dzg/files/"
           "97a9a0a5-fefd-44ee-9ffe-bf3bf6e4cdba/file_downloaded")
    zip_path = out / "rocole.zip"
    try:
        with requests.get(URL, stream=True, timeout=120) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            done = 0
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        print(f"  {done/total*100:5.1f}% — "
                              f"{done/1e6:.1f}/{total/1e6:.1f} MB", end="\r")
        print("\n   descomprimiendo ...")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(out)
        zip_path.unlink()
        print(f"   ✓ RoCoLe en {out}")
        return True
    except Exception as e:
        print(f"   ✗ Error RoCoLe: {e}")
        print("   Descarga manual: https://data.mendeley.com/datasets/c5yvn32dzg/2")
        return False


# ╔════════════════════════════════════════════════════════════════════════════
# ║ 2. BRACOL
# ╚════════════════════════════════════════════════════════════════════════════
def descargar_bracol(out: Path) -> bool:
    """BRACOL via Kaggle CLI (requiere kaggle.json)."""
    import subprocess
    print("\n[2/4] BRACOL (Kaggle) ...")
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        "kaggle", "datasets", "download",
        "-d", "badasstechie/coffee-leaf-disease",
        "-p", str(out), "--unzip",
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"   ✓ BRACOL en {out}")
        return True
    except FileNotFoundError:
        print("   ✗ Kaggle CLI no instalado (pip install kaggle)")
    except subprocess.CalledProcessError as e:
        print(f"   ✗ Error Kaggle: {e}")
        print("   Verifica ~/.kaggle/kaggle.json")
    print("   Mirror alternativo (Mendeley sin auth):")
    print("   https://data.mendeley.com/datasets/yy2k5y8mxg/1 (citar Krohling et al.)")
    return False


# ╔════════════════════════════════════════════════════════════════════════════
# ║ 3. JMuBEN
# ╚════════════════════════════════════════════════════════════════════════════
def descargar_jmuben(out: Path) -> bool:
    """JMuBEN/JMuBEN2 via Mendeley (público)."""
    import requests
    print("\n[3/4] JMuBEN (Mendeley) — dataset grande (~5GB) ...")
    out.mkdir(parents=True, exist_ok=True)
    URLS = [
        # JMuBEN — folder con 5 clases (cercospora, leaf rust, miner, phoma, sano)
        ("jmuben.zip",
         "https://data.mendeley.com/public-files/datasets/t2r6rszp5c/files/"
         "8f23f8a4-3fc3-4cb1-9e8e-7bf26bb0f0aa/file_downloaded"),
    ]
    for fname, url in URLS:
        zip_path = out / fname
        try:
            with requests.get(url, stream=True, timeout=300) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                done = 0
                with open(zip_path, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        done += len(chunk)
                        if total and done % (50 << 20) < (1 << 20):
                            print(f"  {fname}: {done/1e6:.1f}/{total/1e6:.1f} MB",
                                  end="\r")
            print(f"\n   descomprimiendo {fname} ...")
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(out)
            zip_path.unlink()
        except Exception as e:
            print(f"   ✗ Error {fname}: {e}")
            print("   Descarga manual: https://data.mendeley.com/datasets/t2r6rszp5c/1")
            return False
    print(f"   ✓ JMuBEN en {out}")
    return True


# ╔════════════════════════════════════════════════════════════════════════════
# ║ 4. Coffee Leaf Diseases (Kaggle alvarole)
# ╚════════════════════════════════════════════════════════════════════════════
def descargar_coffee_leaf(out: Path) -> bool:
    import subprocess
    print("\n[4/4] Coffee Leaf Diseases (Kaggle) ...")
    out.mkdir(parents=True, exist_ok=True)
    candidates = [
        "alvarole/coffee-leaf-diseases",
        "ahmadyousrydaboor/coffee-leaf-diseases",
    ]
    for ds in candidates:
        cmd = ["kaggle", "datasets", "download", "-d", ds,
               "-p", str(out), "--unzip"]
        try:
            subprocess.run(cmd, check=True)
            print(f"   ✓ {ds} descargado en {out}")
            return True
        except Exception as e:
            print(f"   intento {ds} falló: {e}")
            continue
    return False


# ╔════════════════════════════════════════════════════════════════════════════
# ║ Manifest builder
# ╚════════════════════════════════════════════════════════════════════════════
def construir_manifest_raw(raw_dir: Path, out_csv: Path) -> int:
    """
    Recorre todas las carpetas raw y construye un CSV con:
      ruta_relativa, dataset, clase_original, parte_planta, formato
    """
    print(f"\n[manifest] Construyendo manifest_raw.csv ...")
    rows = []
    extensiones = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}

    for ds_path in raw_dir.iterdir():
        if not ds_path.is_dir():
            continue
        ds_name = ds_path.name
        for img_path in ds_path.rglob("*"):
            if img_path.suffix.lower() not in extensiones:
                continue
            try:
                rel_parts = img_path.relative_to(raw_dir).parts
                clase_raw = rel_parts[1] if len(rel_parts) > 2 else "?"
                rows.append({
                    "ruta_relativa": str(img_path.relative_to(raw_dir)),
                    "dataset": ds_name,
                    "clase_original": clase_raw,
                    "parte_planta": "hoja",   # mayoría son hojas
                    "formato": img_path.suffix.lower().lstrip("."),
                })
            except Exception:
                pass

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"   ✓ {len(rows)} imágenes registradas en {out_csv.name}")
    else:
        print("   ✗ Sin imágenes encontradas")
    return len(rows)


# ╔════════════════════════════════════════════════════════════════════════════
# ║ Main
# ╚════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="Descarga datasets públicos de hojas de café")
    parser.add_argument("--solo", nargs="+", default=None,
        choices=["rocole", "bracol", "jmuben", "coffee_leaf"],
        help="Descargar solo los listados")
    parser.add_argument("--skip", nargs="+", default=[],
        choices=["rocole", "bracol", "jmuben", "coffee_leaf"],
        help="Omitir los listados")
    args = parser.parse_args()

    print("=" * 70)
    print(" Descarga de datasets públicos de hojas de café — Entrega Final")
    print("=" * 70)
    print(f"Salida: {RAW_DIR}")

    DESCARGAS = {
        "rocole":       (RAW_DIR / "rocole",       descargar_rocole),
        "bracol":       (RAW_DIR / "bracol",       descargar_bracol),
        "jmuben":       (RAW_DIR / "jmuben",       descargar_jmuben),
        "coffee_leaf":  (RAW_DIR / "coffee_leaf",  descargar_coffee_leaf),
    }

    seleccionados = args.solo if args.solo else list(DESCARGAS.keys())
    seleccionados = [s for s in seleccionados if s not in args.skip]

    resultados = {}
    for nombre in seleccionados:
        out, fn = DESCARGAS[nombre]
        if out.exists() and any(out.iterdir()):
            print(f"\n[skip] {nombre} ya existe en {out}")
            resultados[nombre] = True
            continue
        resultados[nombre] = fn(out)

    construir_manifest_raw(RAW_DIR, MANIFEST_RAW)

    print("\n" + "=" * 70)
    print(" RESUMEN")
    print("=" * 70)
    for k, v in resultados.items():
        print(f"  {k:15s}: {'✓ OK' if v else '✗ FALLÓ'}")
    print(f"\nSiguiente: python 06_consolidar_imagenes.py")


if __name__ == "__main__":
    main()
