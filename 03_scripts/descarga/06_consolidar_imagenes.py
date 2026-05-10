"""
===============================================================================
 06_consolidar_imagenes.py
===============================================================================
 Consolida imagenes raw descargadas por 01_descargar_imagenes_cafe.py en una
 estructura unificada con etiquetas estandar.

   01_datos/imagenes_cafe/
     train/{Roya,Gotera,Cercospora,Phoma,Miner,Sano,SpiderMite}/
     val/  {...}/
     test/ {...}/
     manifest_consolidado.csv

 Combina ademas las 47 imagenes CALIBRO de la 2da entrega.

 v3 (2026-05-08): typo Cerscospora corregido, SpiderMite agregado, soporte
                  para crops BRACOL del script 07.

 Split estratificado por clase: 70% train / 15% val / 15% test
===============================================================================
"""
from __future__ import annotations
from pathlib import Path
import csv
import random
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

random.seed(42)

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
RAW_DIR = PROJECT_ROOT / "01_datos" / "imagenes_cafe" / "raw"
OUT_DIR = PROJECT_ROOT / "01_datos" / "imagenes_cafe"
CALIBRO_DIR = (PROJECT_ROOT.parent / "IA_Segunda_Entrega" / "datasets" /
               "calibro_imagenes")

CLASES = ["Roya", "Gotera", "Cercospora", "Phoma", "Miner", "Sano", "SpiderMite"]

PATRONES_CLASE = [
    ("Roya",       ["rust", "roya", "hemileia", "leaf_rust", "leafrust"]),
    ("Gotera",     ["gotera", "ojo_de_gallo", "ojo de gallo", "mycena"]),
    # JMuBEN trae el typo "Cerscospora" en su carpeta - mapearlo igual
    ("Cercospora", ["cercospora", "cerscospora", "cescospora", "cersospora"]),
    ("Phoma",      ["phoma"]),
    ("Miner",      ["miner", "leaf miner", "leaf_miner"]),
    ("Sano",       ["healthy", "sano", "sin_enfermedad", "sin enfermedad", "salu"]),
    # Plaga (acaro rojo) - presente en RoCoLe y Coffee Leaf
    ("SpiderMite", ["red_spider_mite", "red spider mite", "redspidermite",
                    "spider mite", "spidermite", "tetranychus"]),
]

EXTENSIONES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def detectar_clase(nombre_clase_raw, ruta):
    """Detecta clase canonica por nombre de carpeta original o filename."""
    texto = (nombre_clase_raw + " " + str(ruta)).lower()
    for canonica, patrones in PATRONES_CLASE:
        for p in patrones:
            if p in texto:
                return canonica
    return None


def recolectar_imagenes():
    """Lista unificada de imagenes con clase canonica."""
    print("[recoleccion] escaneando imagenes raw ...")
    out = []

    if not RAW_DIR.exists():
        print("   WARN " + str(RAW_DIR) +
              " no existe - ejecuta 01_descargar_imagenes_cafe.py")
        return out

    for ds_path in RAW_DIR.iterdir():
        if not ds_path.is_dir():
            continue
        ds_name = ds_path.name
        for img in ds_path.rglob("*"):
            if img.suffix.lower() not in EXTENSIONES:
                continue
            try:
                rel_parts = img.relative_to(RAW_DIR).parts
                clase_raw = rel_parts[1] if len(rel_parts) > 2 else ""
                clase_canonica = detectar_clase(clase_raw, img)
                if clase_canonica is None:
                    continue
                out.append({
                    "ruta_origen": str(img),
                    "dataset": ds_name,
                    "clase": clase_canonica,
                    "clase_original": clase_raw,
                })
            except Exception:
                pass

    if CALIBRO_DIR.exists():
        print("   incluyendo CALIBRO desde " + str(CALIBRO_DIR))
        for img in CALIBRO_DIR.glob("*"):
            if img.suffix.lower() not in EXTENSIONES:
                continue
            nombre = img.stem
            if "Roya" in nombre or "roya" in nombre:
                clase = "Roya"
            elif "Gotera" in nombre or "gotera" in nombre:
                clase = "Gotera"
            else:
                clase = "Sano"
            out.append({
                "ruta_origen": str(img),
                "dataset": "calibro",
                "clase": clase,
                "clase_original": nombre,
            })

    print("   OK " + str(len(out)) + " imagenes con clase canonica detectada")
    from collections import Counter
    print("\n   Distribucion por clase:")
    for cls, n in sorted(Counter(r["clase"] for r in out).items()):
        print("     " + cls.ljust(12) + ": " + str(n))

    return out


def split_estratificado(items, train=0.70, val=0.15):
    """Split estratificado por clase."""
    from collections import defaultdict
    por_clase = defaultdict(list)
    for it in items:
        por_clase[it["clase"]].append(it)
    splits = {"train": [], "val": [], "test": []}
    for clase, lista in por_clase.items():
        random.shuffle(lista)
        n = len(lista)
        n_train = int(n * train)
        n_val = int(n * val)
        splits["train"].extend(lista[:n_train])
        splits["val"].extend(lista[n_train:n_train + n_val])
        splits["test"].extend(lista[n_train + n_val:])
    return splits


def copiar_y_manifest(splits):
    """Copia archivos a out_dir/<split>/<clase>/ y escribe manifest."""
    print("\n[copiar] organizando archivos ...")
    manifest_rows = []

    for split, items in splits.items():
        for it in items:
            origen = Path(it["ruta_origen"])
            destino_dir = OUT_DIR / split / it["clase"]
            destino_dir.mkdir(parents=True, exist_ok=True)
            destino = destino_dir / (it['dataset'] + "_" +
                                     origen.stem + origen.suffix)
            try:
                if not destino.exists():
                    shutil.copy2(origen, destino)
                manifest_rows.append({
                    "split": split,
                    "clase": it["clase"],
                    "dataset_origen": it["dataset"],
                    "clase_original": it["clase_original"],
                    "ruta": str(destino.relative_to(OUT_DIR)),
                })
            except Exception as e:
                print("   WARN copia fallo " + origen.name + ": " + str(e))

    out_csv = OUT_DIR / "manifest_consolidado.csv"
    if manifest_rows:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
            w.writeheader()
            w.writerows(manifest_rows)
        print("   OK " + out_csv.name + ": " + str(len(manifest_rows)) + " imagenes")
    print("\n   train: " + str(len(splits['train'])))
    print("   val:   " + str(len(splits['val'])))
    print("   test:  " + str(len(splits['test'])))


def main():
    print("=" * 70)
    print(" Consolidacion de imagenes cafe - todas las fuentes")
    print("=" * 70)

    items = recolectar_imagenes()
    if not items:
        print("\nWARN Sin imagenes raw. Ejecuta primero 01_descargar_imagenes_cafe.py")
        sys.exit(1)

    splits = split_estratificado(items)
    copiar_y_manifest(splits)

    print("\nOK Listo. Imagenes consolidadas en " + str(OUT_DIR))
    print("   Siguiente: 02_notebooks/NB08_CNN_dataset_ampliado.ipynb")


if __name__ == "__main__":
    main()
