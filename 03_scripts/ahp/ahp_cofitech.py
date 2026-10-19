"""AHP (Saaty) para elegir el MockUp final de CofiTech.

Calcula, para la matriz de criterios y para las cuatro matrices de alternativas:

* el vector propio principal ``w`` (método exacto, ``numpy.linalg.eig``),
* ``λmax``, el índice de consistencia ``CI = (λmax − n) / (n − 1)``,
* la razón de consistencia ``CR = CI / RI`` (RI de Saaty: 0,58 para n = 3; 0,90 para n = 4),
* la síntesis distributiva (los puntajes globales suman 1),
* un análisis de sensibilidad sobre el peso de cada criterio.

Uso:
    python 03_scripts/ahp/ahp_cofitech.py            # informe en consola
    python 03_scripts/ahp/ahp_cofitech.py --json     # además escribe 05_resultados/ahp/ahp_resultados.json

Los juicios están en ``CRITERIOS`` y ``ALTERNATIVAS``; la justificación de cada
juicio está en ``00_documentos/AHP_seleccion_mockup.md``.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
SALIDA_JSON = RAIZ / "05_resultados" / "ahp" / "ahp_resultados.json"

RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}
UMBRAL_CR = 0.10

NOMBRES_CRITERIOS = {
    "C1": "Usabilidad y Adopción Rural",
    "C2": "Generación de Valor B2B / Monetización",
    "C3": "Integración Sistémica (Visión + Clima + Precios + RAG)",
    "C4": "Factibilidad Técnica y Conectividad",
}
NOMBRES_ALTERNATIVAS = {
    "Op1": "Dashboard Analítico Monolítico Web",
    "Op2": "App Móvil Asistencial Pura",
    "Op3": "Plataforma Dual Adaptativa por Roles",
}

# Pesos que el equipo fijó para la defensa (diapositiva de síntesis). Solo se
# usan para comparar: los pesos del modelo salen siempre del vector propio.
PESOS_OBJETIVO = {"C1": 0.38, "C2": 0.28, "C3": 0.22, "C4": 0.12}


def _m(*filas: str) -> np.ndarray:
    """Matriz a partir de texto con fracciones ('1/4'); así se lee igual que en el documento."""
    return np.array([[float(Fraction(x)) for x in fila.split()] for fila in filas])


# ── Juicios de los criterios (C1, C2, C3, C4) ────────────────────────────────
# v2 (vigente): C1 vs C2 = 1, C1 vs C3 = 2, C1 vs C4 = 4, C2 vs C3 = 1,
#               C2 vs C4 = 2, C3 vs C4 = 2.  Reproduce los pesos 0,38/0,28/0,22/0,12.
CRITERIOS = _m("1   1   2   4",
               "1   1   1   2",
               "1/2 1   1   2",
               "1/4 1/2 1/2 1")

# v1 (primera versión del documento): C1 vs C2 = 2 y C1 vs C4 = 3.
CRITERIOS_V1 = _m("1   2   2   3",
                  "1/2 1   1   2",
                  "1/2 1   1   2",
                  "1/3 1/2 1/2 1")

# ── Juicios de las alternativas (Op1, Op2, Op3) respecto a cada criterio ─────
ALTERNATIVAS = {
    "C1": _m("1 1/4 1/5", "4 1 1/2", "5 2 1"),
    "C2": _m("1 5 1/3", "1/5 1 1/7", "3 7 1"),
    "C3": _m("1 1/2 1/7", "2 1 1/4", "7 4 1"),
    "C4": _m("1 1/4 1/2", "4 1 2", "2 1/2 1"),
}


@dataclass
class Prioridad:
    vector: list[float]
    lambda_max: float
    ci: float
    ri: float
    cr: float
    consistente: bool
    vector_aproximado: list[float]   # promedio de columnas normalizadas (método de la diapositiva)


def es_reciproca(a: np.ndarray) -> bool:
    return bool(np.allclose(a * a.T, 1.0) and np.allclose(np.diag(a), 1.0))


def prioridad(a: np.ndarray) -> Prioridad:
    """Vector propio principal normalizado (suma 1), λmax, CI y CR de una matriz de Saaty."""
    if not es_reciproca(a):
        raise ValueError("La matriz no es recíproca: a_ji debe ser 1 / a_ij y la diagonal 1.")
    n = a.shape[0]
    valores, vectores = np.linalg.eig(a)
    k = int(np.argmax(valores.real))           # Perron-Frobenius: autovalor real dominante
    w = np.abs(vectores[:, k].real)
    w = w / w.sum()
    lambda_max = float(valores[k].real)
    ci = max((lambda_max - n) / (n - 1), 0.0) if n > 2 else 0.0   # evita −0,0000 por redondeo
    ri = RI[n]
    cr = ci / ri if ri else 0.0
    aprox = (a / a.sum(axis=0)).mean(axis=1)
    return Prioridad(w.round(6).tolist(), round(lambda_max, 6), round(ci, 6), ri, round(cr, 6),
                     cr < UMBRAL_CR, aprox.round(6).tolist())


def sintesis(pesos: np.ndarray, locales: np.ndarray) -> np.ndarray:
    """Síntesis distributiva: puntaje_i = Σ_j w_j · p_ij (filas = alternativas, columnas = criterios)."""
    return locales @ pesos


def con_peso(pesos: np.ndarray, j: int, t: float) -> np.ndarray:
    """Fija el peso del criterio j en t y reparte 1 − t entre los demás en su proporción actual."""
    resto = np.delete(pesos, j)
    return np.insert(resto / resto.sum() * (1 - t), j, t)


def _ganador(w: np.ndarray, locales: np.ndarray) -> str:
    return list(NOMBRES_ALTERNATIVAS)[int(np.argmax(sintesis(w, locales)))]


def sensibilidad(pesos: np.ndarray, locales: np.ndarray, pasos: int = 101) -> dict:
    """Para cada criterio, barre su peso de 0 a 1 (los demás conservan su proporción)
    e informa el peso exacto (bisección) en el que cambiaría el ganador."""
    salida = {}
    for j, c in enumerate(NOMBRES_CRITERIOS):
        cambios, previo, t_previo = [], None, 0.0
        for t in np.linspace(0, 1, pasos):
            ganador = _ganador(con_peso(pesos, j, t), locales)
            if previo and ganador != previo:
                lo, hi = t_previo, float(t)
                for _ in range(50):
                    medio = (lo + hi) / 2
                    lo, hi = (medio, hi) if _ganador(con_peso(pesos, j, medio), locales) == previo else (lo, medio)
                cambios.append({"peso": round(hi, 3), "de": previo, "a": ganador})
            previo, t_previo = ganador, float(t)
        salida[c] = {"peso_actual": round(float(pesos[j]), 4), "cambios_de_ganador": cambios}
    return salida


def escenarios(pesos: np.ndarray, locales: np.ndarray) -> list[dict]:
    """Escenarios de la tabla de sensibilidad del documento."""
    casos = [("Pesos del equipo", pesos), ("Criterios iguales (0,25)", np.full(len(pesos), 0.25))]
    casos += [(f"{c} con peso 0,50", con_peso(pesos, j, 0.5)) for j, c in enumerate(NOMBRES_CRITERIOS)]
    return [{"escenario": n, "global": {a: round(float(v), 4) for a, v in zip(NOMBRES_ALTERNATIVAS, sintesis(w, locales))},
             "ganador": _ganador(w, locales)} for n, w in casos]


def calcular(criterios: np.ndarray = CRITERIOS) -> dict:
    pc = prioridad(criterios)
    pesos = np.array(pc.vector)
    locales_p = {c: prioridad(m) for c, m in ALTERNATIVAS.items()}
    locales = np.array([locales_p[c].vector for c in NOMBRES_CRITERIOS]).T     # 3 × 4
    globales = sintesis(pesos, locales)
    aportes = locales * pesos                                                   # w_j · p_ij
    ranking = sorted(zip(NOMBRES_ALTERNATIVAS, globales), key=lambda x: -x[1])
    return {
        "criterios": {"nombres": NOMBRES_CRITERIOS, "matriz": criterios.round(4).tolist(), **asdict(pc)},
        "alternativas": {"nombres": NOMBRES_ALTERNATIVAS,
                         **{c: {"matriz": ALTERNATIVAS[c].round(4).tolist(), **asdict(p)} for c, p in locales_p.items()}},
        "global": {a: round(float(g), 4) for a, g in zip(NOMBRES_ALTERNATIVAS, globales)},
        "aportes": {a: {c: round(float(aportes[i, j]), 4) for j, c in enumerate(NOMBRES_CRITERIOS)}
                    for i, a in enumerate(NOMBRES_ALTERNATIVAS)},
        "ranking": [a for a, _ in ranking],
        "ventaja_ganador": round(float(ranking[0][1] / ranking[1][1]), 3),
        "todas_consistentes": pc.consistente and all(p.consistente for p in locales_p.values()),
        "sensibilidad": sensibilidad(pesos, locales),
        "escenarios": escenarios(pesos, locales),
    }


def _f(x: float, d: int = 4) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def informe(r: dict) -> str:
    c = r["criterios"]
    lineas = ["AHP CofiTech · método del vector propio principal", "",
              "Pesos de los criterios (w_j)"]
    for (k, nombre), w, a in zip(NOMBRES_CRITERIOS.items(), c["vector"], c["vector_aproximado"]):
        lineas.append(f"  {k} {nombre:<55} {_f(w)}   (aprox. columnas: {_f(a)} · objetivo {_f(PESOS_OBJETIVO[k], 2)})")
    lineas.append(f"  λmax = {_f(c['lambda_max'])}  CI = {_f(c['ci'])}  RI = {_f(c['ri'], 2)}  "
                  f"CR = {_f(c['cr'])}  {'✓ < 0,10' if c['consistente'] else '✗ REVISAR JUICIOS'}")
    lineas += ["", "Prioridades locales de las alternativas (Op1, Op2, Op3)"]
    for k in NOMBRES_CRITERIOS:
        p = r["alternativas"][k]
        lineas.append(f"  {k}: {' · '.join(_f(v) for v in p['vector'])}   λmax = {_f(p['lambda_max'])}  "
                      f"CR = {_f(p['cr'])}  {'✓' if p['consistente'] else '✗'}")
    lineas += ["", "Síntesis global (suma 1)"]
    for a in r["ranking"]:
        aportes = " + ".join(f"{k} {_f(v, 3)}" for k, v in r["aportes"][a].items())
        lineas.append(f"  {a} {NOMBRES_ALTERNATIVAS[a]:<38} {_f(r['global'][a])}  = {aportes}")
    lineas.append(f"  Suma = {_f(sum(r['global'].values()))} · el ganador supera al segundo {_f(r['ventaja_ganador'], 2)} veces")
    lineas += ["", "Sensibilidad (peso de un criterio en el que cambiaría el ganador)"]
    for k, s in r["sensibilidad"].items():
        cambios = "; ".join(f"≥ {_f(x['peso'], 3)} → {x['a']}" for x in s["cambios_de_ganador"]) or "ninguno entre 0 y 1"
        lineas.append(f"  {k} (actual {_f(s['peso_actual'], 3)}): {cambios}")
    return "\n".join(lineas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help=f"escribe {SALIDA_JSON.relative_to(RAIZ)}")
    args = parser.parse_args()
    r = calcular()
    print(informe(r))
    v1 = calcular(CRITERIOS_V1)
    print("\nComparación con la matriz de criterios v1: pesos "
          + " · ".join(_f(w) for w in v1["criterios"]["vector"])
          + " → global " + " · ".join(f"{a} {_f(g)}" for a, g in v1["global"].items()))
    if args.json:
        SALIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
        r["comparacion_v1"] = {"pesos": v1["criterios"]["vector"], "cr": v1["criterios"]["cr"], "global": v1["global"]}
        SALIDA_JSON.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON escrito en {SALIDA_JSON}")
    return 0 if r["todas_consistentes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
