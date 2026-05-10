"""
Orquestador maestro: ejecuta todos los scripts de descarga en orden.

v2 (2026-05-07): captura stdout/stderr para analisis, detecta correctamente
                 fallos via exit code (cada subscript ahora sale con 1 si no
                 produjo datos), reporta tiempo por paso y deja un log
                 consolidado en logs/orquestador_<fecha>.log

Uso:
  python 00_ejecutar_todo.py                     # todo
  python 00_ejecutar_todo.py --solo precios eva  # solo lo listado
  python 00_ejecutar_todo.py --skip imagenes     # omitir imagenes (lentas)
  python 00_ejecutar_todo.py --quiet             # solo resumen, sin tee a stdout
"""
from __future__ import annotations
import argparse
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve().parent
LOG_DIR = HERE.parent.parent / "05_resultados" / "logs"

SCRIPTS = [
    ("imagenes",    "01_descargar_imagenes_cafe.py",     "Imagenes cafe (~30 min)"),
    ("precios",     "02_descargar_precios_extendidos.py","Precios FRED+WB+IMF (~3 min)"),
    ("clima",       "03_descargar_clima_satelital.py",   "Clima Open-Meteo (~5 min)"),
    ("eva",         "04_descargar_eva_municipal.py",     "EVA municipal (~5 min)"),
    ("geografia",   "05_descargar_dem_suelos.py",        "DEM y suelos (~5 min)"),
    ("bracol",      "07_procesar_bracol_yolo.py",        "BRACOL YOLO -> crops (~1 min)"),
    ("consolidar",  "06_consolidar_imagenes.py",         "Consolidar imagenes"),
    # ETL del master municipal: corre despues de las descargas para producir
    # 01_datos/procesados/master_cafe_municipal_mensual.csv que consumen los NBs
    ("master",      "../utilidades/construir_master_municipal.py",
                                                          "ETL master municipal mensual (~1 min)"),
]


def run_step(clave, script_path, *, quiet, log_file):
    """
    Ejecuta un script capturando stdout/stderr.
    Devuelve (ok, segundos, snippet).
    """
    t0 = time.time()
    proc = subprocess.Popen(
        [sys.executable, "-u", str(script_path)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, encoding="utf-8", errors="replace",
    )
    lineas = []
    try:
        for line in proc.stdout:
            lineas.append(line)
            log_file.write(line)
            if not quiet:
                sys.stdout.write(line)
                sys.stdout.flush()
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        raise

    elapsed = time.time() - t0
    ok = proc.returncode == 0
    n_warn = sum(1 for l in lineas if "FAIL" in l or "ERROR" in l)
    n_ok = sum(1 for l in lineas if "OK" in l)
    snippet = "".join(lineas[-8:]).strip().replace("\n", " | ")
    return ok, elapsed, "checks=" + str(n_ok) + " warns=" + str(n_warn) + " | " + snippet[:200]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo", nargs="+", default=None,
                        choices=[s[0] for s in SCRIPTS])
    parser.add_argument("--skip", nargs="+", default=[],
                        choices=[s[0] for s in SCRIPTS])
    parser.add_argument("--quiet", action="store_true",
                        help="No re-imprimir stdout de subscripts; solo resumen")
    args = parser.parse_args()

    sel = args.solo if args.solo else [s[0] for s in SCRIPTS]
    sel = [s for s in sel if s not in args.skip]

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fecha_iso = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / ("orquestador_" + fecha_iso + ".log")

    print("=" * 70)
    print(" ORQUESTADOR de descargas - Entrega Final (v2)")
    print("=" * 70)
    print("Scripts a ejecutar : " + str(sel))
    print("Inicio             : " + str(datetime.now()))
    print("Log                : " + str(log_path))

    resultados = []
    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write("# Orquestador inicio " + str(datetime.now()) + "\n")
        log_file.write("# Seleccion: " + str(sel) + "\n\n")

        for clave, script, desc in SCRIPTS:
            if clave not in sel:
                continue
            path = HERE / script
            if not path.exists():
                print("\n[" + clave + "] FAIL no existe: " + str(path))
                resultados.append((clave, False, 0.0, "archivo ausente " + path.name))
                continue

            print("\n" + "-" * 70)
            print("[" + clave.upper() + "] " + desc)
            print("-" * 70)
            log_file.write("\n" + "=" * 70 + "\n[" + clave + "] " + script + "\n" + "=" * 70 + "\n")
            log_file.flush()

            try:
                ok, elapsed, snippet = run_step(clave, path,
                                                quiet=args.quiet,
                                                log_file=log_file)
            except Exception as e:
                print("   FAIL Error ejecutando " + script + ": " + str(e))
                ok, elapsed, snippet = False, 0.0, str(e)
            resultados.append((clave, ok, elapsed, snippet))

    # Resumen
    print("\n" + "=" * 70)
    print(" RESUMEN")
    print("=" * 70)
    total_ok = 0
    total_t = 0.0
    for clave, ok, elapsed, snippet in resultados:
        marca = "OK    " if ok else "FAIL  "
        print("  " + clave.ljust(11) + " " + marca + "  (" + ("%6.1f" % elapsed) + "s)  " + snippet)
        total_ok += int(ok)
        total_t += elapsed
    print("\n  Total OK : " + str(total_ok) + "/" + str(len(resultados)))
    print("  Tiempo   : " + ("%.1f" % (total_t / 60)) + " min")
    print("  Log      : " + str(log_path))
    print("  Fin      : " + str(datetime.now()))

    if total_ok < len(resultados):
        sys.exit(1)


if __name__ == "__main__":
    main()
