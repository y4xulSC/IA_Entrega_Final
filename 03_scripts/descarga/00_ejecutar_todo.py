"""
Orquestador maestro: ejecuta todos los scripts de descarga en orden.

Uso:
  python 00_ejecutar_todo.py                     # todo
  python 00_ejecutar_todo.py --solo precios eva  # solo lo listado
  python 00_ejecutar_todo.py --skip imagenes     # omitir imágenes (lentas)
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve().parent

SCRIPTS = [
    ("imagenes",    "01_descargar_imagenes_cafe.py",     "Imágenes café (~30 min)"),
    ("precios",     "02_descargar_precios_extendidos.py","Precios FRED+WB+IMF (~3 min)"),
    ("clima",       "03_descargar_clima_satelital.py",   "Clima Open-Meteo (~5 min)"),
    ("eva",         "04_descargar_eva_municipal.py",     "EVA municipal (~5 min)"),
    ("geografia",   "05_descargar_dem_suelos.py",        "DEM y suelos (~5 min)"),
    ("consolidar",  "06_consolidar_imagenes.py",         "Consolidar imágenes"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo", nargs="+", default=None,
                        choices=[s[0] for s in SCRIPTS])
    parser.add_argument("--skip", nargs="+", default=[],
                        choices=[s[0] for s in SCRIPTS])
    args = parser.parse_args()

    sel = args.solo if args.solo else [s[0] for s in SCRIPTS]
    sel = [s for s in sel if s not in args.skip]

    print("=" * 70)
    print(" ORQUESTADOR de descargas — Entrega Final")
    print("=" * 70)
    print(f"Scripts a ejecutar: {sel}")
    print(f"Inicio: {datetime.now()}")

    resultados = []
    for clave, script, desc in SCRIPTS:
        if clave not in sel:
            continue
        path = HERE / script
        if not path.exists():
            print(f"\n[{clave}] ✗ no existe: {path}")
            resultados.append((clave, False))
            continue

        print(f"\n{'─' * 70}\n[{clave.upper()}] {desc}\n{'─' * 70}")
        try:
            r = subprocess.run([sys.executable, str(path)],
                               capture_output=False)
            ok = r.returncode == 0
            resultados.append((clave, ok))
        except Exception as e:
            print(f"   ✗ Error ejecutando {script}: {e}")
            resultados.append((clave, False))

    print("\n" + "=" * 70)
    print(" RESUMEN")
    print("=" * 70)
    for clave, ok in resultados:
        print(f"  {clave:12s}: {'✓ OK' if ok else '✗ FALLÓ'}")
    print(f"Fin: {datetime.now()}")


if __name__ == "__main__":
    main()
