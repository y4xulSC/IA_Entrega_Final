"""Calendario cafetero de referencia (zona andina central) y estado fenológico.

Lo usan el Asesor del Caficultor (tareas del mes) y el agente RAG (estado
fenológico que se inyecta en la pregunta). Es el calendario del equipo, no un
calendario validado por Cenicafé: la floración y las cosechas cambian por
región y altitud, por eso todo texto que lo usa dice «de referencia».

Regla del proyecto: aquí no va ninguna dosis. Las tareas de fertilización
remiten al análisis de suelos y las de control químico, al umbral de roya.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Cenicafé (Avances Técnicos 586, 2026): «El control de la roya del café debe
# realizarse entre los 60 y 150 días después de la floración principal».
VENTANA_CONTROL_ROYA_DDF: tuple[int, int] = (60, 150)

CALENDARIO = {
    1:  {"actividad": "Manejo de arvenses y planeación",
         "tareas": ["Plato limpio alrededor del tronco (40 cm radio)",
                    "Revisar plan de fertilización del año",
                    "Limpiar herramientas (machete, tijeras de poda)"]},
    2:  {"actividad": "PRIMERA FERTILIZACIÓN del año",
         "tareas": ["Fertilizar con la fórmula y la cantidad que indique el análisis de suelos",
                    "Mojar bien antes de abonar si está seco",
                    "Hacer deshije: dejar 2-3 chupones por tronco"]},
    3:  {"actividad": "Inicio cosecha mitaca (Antioquia, Tolima, Valle)",
         "tareas": ["Recolección selectiva: SOLO cereza roja madura",
                    "Beneficio: lavar bien, secar lento (6-12 días)",
                    "Monitorear roya en hojas jóvenes"]},
    4:  {"actividad": "Cosecha mitaca + control roya",
         "tareas": ["Continuar cosecha selectiva",
                    "Medir la incidencia de roya en el lote; si supera 5 %, consultar el manejo "
                    "con el asistente o el extensionista",
                    "Revisar trampas de broca"]},
    5:  {"actividad": "SEGUNDA FERTILIZACIÓN (poscosecha mitaca)",
         "tareas": ["Fertilizar según el análisis de suelos",
                    "Si hay hojas amarillas, consultar al extensionista (puede ser una deficiencia nutricional)",
                    "Podas selectivas de ramas improductivas"]},
    6:  {"actividad": "Final mitaca, secado, mantenimiento",
         "tareas": ["Terminar de secar el café (humedad 10-12%)",
                    "Almacenar en pergamino, lugar seco",
                    "Sembrar nuevas chapolas si renovó zoca"]},
    7:  {"actividad": "Floración principal (depende del clima)",
         "tareas": ["NO regar fuerte durante floración",
                    "Vigilar broca: muestreo semanal",
                    "Revisar sombrío: ralear si está muy denso"]},
    8:  {"actividad": "TERCERA FERTILIZACIÓN + control plagas",
         "tareas": ["Fertilizar según el análisis de suelos",
                    "Control de broca con trampas + buenas prácticas",
                    "Control de minador si infestación >30%"]},
    9:  {"actividad": "Inicio cosecha principal (zona andina)",
         "tareas": ["Recolección selectiva diaria",
                    "Beneficio inmediato (máx 6h después de recoger)",
                    "Monitorear gotera con humedad alta"]},
    10: {"actividad": "Pico de cosecha principal",
         "tareas": ["Maximizar mano de obra de recolección",
                    "Asegurar capacidad de fermentadores y patios",
                    "Revisar puntaje SCA con muestras a tostadora"]},
    11: {"actividad": "CUARTA FERTILIZACIÓN + cosecha",
         "tareas": ["Última fertilización del año, según el análisis de suelos",
                    "Continuar recolección selectiva",
                    "Si viene El Niño anticipado: reforzar sombrío"]},
    12: {"actividad": "Final cosecha + planeación próximo año",
         "tareas": ["Cierre de cosecha y secado final",
                    "Mantenimiento de equipos (despulpadora)",
                    "Decidir qué lotes vender por SCA y cuáles por FNC"]},
}


def estado_fenologico(hoy: Optional[date] = None, floracion: Optional[date] = None) -> str:
    """Texto del estado fenológico estimado para el prompt del agente.

    Con fecha de floración principal se calculan los días después de la
    floración (DDF) y si se está en la ventana de control de roya de Cenicafé.
    Sin ella, solo se puede dar la etapa del calendario de referencia del mes.

    >>> estado_fenologico(date(2026, 10, 8))
    'octubre — pico de cosecha principal según el calendario de referencia de la zona andina (varía por región)'
    """
    hoy = hoy or date.today()
    texto = (f"{MESES[hoy.month - 1]} — {CALENDARIO[hoy.month]['actividad'].lower()} según el "
             "calendario de referencia de la zona andina (varía por región)")
    if floracion and floracion <= hoy:
        ddf = (hoy - floracion).days
        inicio, fin = VENTANA_CONTROL_ROYA_DDF
        if ddf < inicio:
            ventana = f"antes de la ventana de control de roya ({inicio}–{fin} DDF)"
        elif ddf <= fin:
            ventana = f"dentro de la ventana de control de roya ({inicio}–{fin} DDF)"
        else:
            ventana = f"después de la ventana de control de roya ({inicio}–{fin} DDF)"
        texto += f"; {ddf} días después de la floración principal, {ventana}"
    return texto
