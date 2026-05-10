"""
===============================================================================
 07_procesar_bracol_yolo.py
===============================================================================
 Convierte BRACOL (formato YOLOv8 deteccion) a clasificacion via crops:

  raw/bracol/BRACOL_REVIEWED_ANNOTATIONS/BRACOL_REVIEWED/{train,valid,test}/
                                          ├── images/   (1744 imagenes)
                                          └── labels/   (1744 .txt YOLO)

 Por cada imagen e .txt asociado, recorta cada bounding box y lo guarda
 como imagen separada en raw/bracol_crops/<clase>/<source_name>_box<i>.jpg.

 Las clases YOLO de BRACOL son:
   0=Cercospora  1=Miner  2=Phoma  3=Rust(Roya)

 Esto permite que 06_consolidar_imagenes.py tome los crops como datos
 normales de clasificacion.

 v1 (2026-05-08): primera version.

 Output:
   01_datos/imagenes_cafe/raw/bracol_crops/{Cercospora,Miner,Phoma,Roya}/
===============================================================================
"""
from __future__ import annotations
from pathlib import Path
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Pillow
try:
    from PIL import Image
except ImportError:
    print("FAIL falta libreria: pip install Pillow")
    sys.exit(1)


HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
RAW = PROJECT_ROOT / "01_datos" / "imagenes_cafe" / "raw"
BRACOL_BASE = RAW / "bracol" / "BRACOL_REVIEWED_ANNOTATIONS" / "BRACOL_REVIEWED"
CROPS_DIR = RAW / "bracol_crops"

# Mapeo de IDs YOLO BRACOL -> nombres canonicos del proyecto
# Segun data.yaml: nc=4, names=['Cercospora','Miner','Phoma','Rust']
YOLO_ID_TO_CLASE = {
    0: "Cercospora",
    1: "Miner",
    2: "Phoma",
    3: "Roya",   # Rust en YOLO -> Roya en nuestro proyecto
}

# Margen extra alrededor del bbox (% del tamanio) para no recortar tan al ras
MARGIN_PCT = 0.05  # 5%
MIN_CROP = 64  # px minimo para no guardar crops minusculos


def parse_yolo_label(label_path):
    """
    Parsea un .txt YOLO. Cada linea: class_id cx cy w h (todos normalizados 0-1).
    Devuelve lista de dicts.
    """
    boxes = []
    try:
        with open(label_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                try:
                    cls = int(parts[0])
                    cx, cy, w, h = map(float, parts[1:])
                    boxes.append({"cls": cls, "cx": cx, "cy": cy,
                                  "w": w, "h": h})
                except ValueError:
                    continue
    except Exception:
        pass
    return boxes


def yolo_to_pixels(box, img_w, img_h):
    """Convierte bbox YOLO normalizado a pixeles (left, top, right, bottom)."""
    cx, cy, w, h = box["cx"], box["cy"], box["w"], box["h"]
    # Aplicar margen
    w *= (1 + MARGIN_PCT)
    h *= (1 + MARGIN_PCT)
    left = max(0, (cx - w / 2) * img_w)
    top = max(0, (cy - h / 2) * img_h)
    right = min(img_w, (cx + w / 2) * img_w)
    bottom = min(img_h, (cy + h / 2) * img_h)
    return int(left), int(top), int(right), int(bottom)


def procesar_split(split_name):
    """Procesa train/valid/test de BRACOL."""
    img_dir = BRACOL_BASE / split_name / "images"
    lbl_dir = BRACOL_BASE / split_name / "labels"
    if not (img_dir.exists() and lbl_dir.exists()):
        print("   WARN " + split_name + ": images/labels no existen, salto")
        return 0

    n_crops = 0
    n_skipped = 0
    for img_path in img_dir.glob("*"):
        if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        lbl_path = lbl_dir / (img_path.stem + ".txt")
        if not lbl_path.exists():
            continue

        boxes = parse_yolo_label(lbl_path)
        if not boxes:
            continue

        try:
            img = Image.open(img_path).convert("RGB")
            W, H = img.size
        except Exception as e:
            print("   WARN " + img_path.name + ": " + str(e))
            continue

        for i, box in enumerate(boxes):
            clase = YOLO_ID_TO_CLASE.get(box["cls"])
            if not clase:
                continue
            left, top, right, bottom = yolo_to_pixels(box, W, H)
            if (right - left) < MIN_CROP or (bottom - top) < MIN_CROP:
                n_skipped += 1
                continue
            try:
                crop = img.crop((left, top, right, bottom))
                out_dir = CROPS_DIR / clase
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / (img_path.stem + "_box" + str(i) + ".jpg")
                crop.save(out_path, "JPEG", quality=92)
                n_crops += 1
            except Exception as e:
                n_skipped += 1
                continue

    print("   " + split_name + ": " + str(n_crops) + " crops generados (" +
          str(n_skipped) + " saltados por tamano)")
    return n_crops


def main():
    print("=" * 70)
    print(" BRACOL YOLO -> Crops para clasificacion")
    print("=" * 70)
    if not BRACOL_BASE.exists():
        print("FAIL " + str(BRACOL_BASE) + " no existe.")
        print("     Ejecuta primero 01_descargar_imagenes_cafe.py")
        return 1

    print("Origen   : " + str(BRACOL_BASE))
    print("Destino  : " + str(CROPS_DIR))
    print("Mapeo    : " + str(YOLO_ID_TO_CLASE))
    print()

    total = 0
    for split in ["train", "valid", "test"]:
        total += procesar_split(split)

    print()
    print("OK Total: " + str(total) + " crops generados en " + str(CROPS_DIR))
    if CROPS_DIR.exists():
        print()
        print("Distribucion por clase:")
        for c_dir in sorted(CROPS_DIR.iterdir()):
            if c_dir.is_dir():
                n = len(list(c_dir.glob("*.jpg")))
                print("  " + c_dir.name.ljust(15) + ": " + str(n))
    print()
    print("Siguiente: python 06_consolidar_imagenes.py")

    return 0 if total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
