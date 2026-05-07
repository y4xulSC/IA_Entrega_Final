"""
═══════════════════════════════════════════════════════════════════════════════
 06_consolidar_imagenes.py
═══════════════════════════════════════════════════════════════════════════════
 Toma las imágenes raw descargadas por 01_descargar_imagenes_cafe.py y las
 consolida en una estructura unificada con etiquetas estándar:

   01_datos/imagenes_cafe/
     train/{Roya,Gotera,Cercospora,Phoma,Miner,Sano}/
     val/  {...}/
     test/ {...}/
     manifest_consolidado.csv

 También combina las 47 imágenes CALIBRO de la 2da entrega.

 Mapeo de clases (entre datasets):
   - "leaf rust", "rust", "roya", "Hemileia"          → Roya
   - "miner"                                          → Miner
   - "cercospora"                                     → Cercospora
   - "phoma"                                          → Phoma
   - "healthy", "sano", "Sin_enfermedad"              → Sano
   - "gotera", "ojo de gallo"                         → Gotera

 Split estratificado por clase: 70% train / 15% val / 15% test
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
from pathlib import Path
import csv
import random
import shutil
import sys

random.seed(42)

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
RAW_DIR = PROJECT_ROOT / "01_datos" / "imagenes_cafe" / "raw"
OUT_DIR = PROJECT_ROOT / "01_datos" / "imagenes_cafe"
CALIBRO_DIR = (PROJECT_ROOT.parent / "IA_Segunda_Entrega" / "datasets" /
               "calibro_imagenes")

# Clases canónicas
CLASES = ["Roya", "Gotera", "Cercospora", "Phoma", "Miner", "Sano"]

# Patrones para mapear clases originales → canónicas
PATRONES_CLASE = [
    ("Roya",      ["rust", "roya", "hemileia", "leaf_rust", "leafrust"]),
    ("Gotera",    ["gotera", "ojo_de_gallo", "ojo de gallo", "mycena"]),
    ("Cercospora",["cercospora"]),
    ("Phoma",     ["phoma"]),
    ("Miner",     ["miner", "leaf miner", "leaf_miner"]),
    ("Sano",      ["healthy", "sano", "sin_enfermedad", "sin enfermedad", "salu"]),
]

EXTENSIONES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def detectar_clase(nombre_clase_raw: str, ruta: Path) -> str | None:
    """Detecta clase canónica por nombre de carpeta original o filename."""
    texto = (nombre_clase_raw + " " + str(ruta)).lower()
    for canonica, patrones in PATRONES_CLASE:
        for p in patrones:
            if p in texto:
                return canonica
    return None


def recolectar_imagenes() -> list[dict]:
    """Construye lista unificada de imágenes con clase canónica."""
    print("[recolección] escaneando imágenes raw ...")
    out = []

    if not RAW_DIR.exists():
        print(f"   ⚠  {RAW_DIR} no existe — ejecuta 01_descargar_imagenes_cafe.py")
        return out

    # Datasets descargados
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

    # CALIBRO local (2da entrega)
    if CALIBRO_DIR.exists():
        print(f"   incluyendo CALIBRO desde {CALIBRO_DIR}")
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

    print(f"   ✓ {len(out)} imágenes con clase canónica detectada")
    # Conteo por clase
    from collections import Counter
    print("\n   Distribución por clase:")
    for cls, n in sorted(Counter(r["clase"] for r in out).items()):
        print(f"     {cls:12s}: {n}")

    return out


def split_estratificado(items: list[dict], train: float = 0.70,
                        val: float = 0.15) -> dict[str, list[dict]]:
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
        n_val   = int(n * val)
        splits["train"].extend(lista[:n_train])
        splits["val"]  .extend(lista[n_train:n_train+n_val])
        splits["test"] .extend(lista[n_train+n_val:])
    return splits


def copiar_y_manifest(splits: dict[str, list[dict]]):
    """Copia archivos a out_dir/<split>/<clase>/ y escribe manifest."""
    print("\n[copiar] organizando archivos ...")
    manifest_rows = []

    for split, items in splits.items():
        for it in items:
            origen = Path(it["ruta_origen"])
            destino_dir = OUT_DIR / split / it["clase"]
            destino_dir.mkdir(parents=True, exist_ok=True)
            destino = destino_dir / f"{it['dataset']}_{origen.stem}{origen.suffix}"
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
                print(f"   ⚠  copia falló {origen.name}: {e}")

    # Manifest
    out_csv = OUT_DIR / "manifest_consolidado.csv"
    if manifest_rows:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=manifest_rows[0].keys())
            w.writeheader()
            w.writerows(manifest_rows)
        print(f"   ✓ {out_csv.name}: {len(manifest_rows)} imágenes")
    print(f"\n   train: {len(splits['train'])}")
    print(f"   val:   {len(splits['val'])}")
    print(f"   test:  {len(splits['test'])}")


def main():
    print("=" * 70)
    print(" Consolidación de imágenes café — todas las fuentes")
    print("=" * 70)

    items = recolectar_imagenes()
    if not items:
        print("\n⚠  Sin imágenes raw. Ejecuta primero 01_descargar_imagenes_cafe.py")
        sys.exit(1)

    splits = split_estratificado(items)
    copiar_y_manifest(splits)

    print("\n✓ Listo. Imágenes consolidadas en", OUT_DIR)
    print("   Siguiente: 02_notebooks/NB08_CNN_dataset_ampliado.ipynb")


if __name__ == "__main__":
    main()
