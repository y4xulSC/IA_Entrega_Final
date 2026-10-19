"""Contenido de las láminas: MockUp A (monolítico web), MockUp B (móvil asistencial) y
MockUp C · vista web B2B del Agrónomo / Cooperativa (complementa la vista móvil de Sofía).

Los números son de ejemplo, coherentes con los datos del proyecto (precio FNC de
diciembre de 2025, validación del Ridge 2024–2025, clases de la CNN de NB08).
"""
from __future__ import annotations

from graficos import hoja, linea, mapa_calor
from sistema import Lamina, Pantalla, badge, icono, marca, navegador, telefono

# ═════════════════════════════ MockUp A ════════════════════════════════════
URL_A = "app.cofitech.co/dashboard"
ALTO_A = 470
PESTANAS_A = ["Inicio", "Dashboard", "Rendimiento", "Precios", "Enfermedades", "Chatbot", "Mapa", "Calidad SCA", "Asesor"]


def _pestanas(activa: str, con_badge: bool = False) -> str:
    tabs = "".join(
        f'<span style="padding:5px 7px;border-radius:7px;font-size:8.6px;font-weight:600;white-space:nowrap;'
        f'{"background:#6B4A35;color:#fff" if t == activa else "color:#7A685B"}">{t}</span>' for t in PESTANAS_A)
    return (f'<div class="c web" style="padding:4px;display:flex;flex-wrap:wrap;gap:2px 1px">{tabs}'
            f'{badge(1) if con_badge else ""}</div>')


def _cabecera_a(titulo: str, sub: str) -> str:
    return f'<div class="fila" style="justify-content:space-between">{marca(26)}<span class="chip borde">Entrega final · 2026-1</span></div>' \
           f'<div><p class="h1 web">{titulo}</p><div class="sub">{sub}</div></div>'


def lamina_a() -> Lamina:
    p1 = navegador(f'''
{_cabecera_a("Sistema Integral de IA Agrícola", "Café Colombia · EVA, FNC, ICO, IDEAM, NOAA")}
{_pestanas("Inicio", True)}
<div class="grid4" style="position:relative">{badge(2)}
 <div class="c web"><div class="et">Datasets</div><div class="v l">11</div></div>
 <div class="c web"><div class="et">Modelos</div><div class="v l">13+</div></div>
 <div class="c web"><div class="et">Imágenes</div><div class="v l">~10K</div></div>
 <div class="c web"><div class="et">Syllabus</div><div class="v l">I–IV</div></div>
</div>
<div class="grid2" style="position:relative">{badge(3)}
 <div class="c web"><div class="t b7">{icono("barras",11)} Dashboard</div><div class="t s mut">Indicadores por departamento y año</div></div>
 <div class="c web"><div class="t b7">{icono("hoja",11)} Rendimiento</div><div class="t s mut">Predicción ton/ha (MLP + Stacking)</div></div>
 <div class="c web"><div class="t b7">{icono("precio",11)} Precios</div><div class="t s mut">Pronóstico FNC e ICO</div></div>
 <div class="c web"><div class="t b7">{icono("camara",11)} Enfermedades</div><div class="t s mut">CNN: 7 clases de hoja</div></div>
 <div class="c web"><div class="t b7">{icono("chat",11)} Chatbot RAG</div><div class="t s mut">Preguntas al corpus técnico</div></div>
 <div class="c web"><div class="t b7">{icono("mapa",11)} Mapa</div><div class="t s mut">Municipios y clústeres</div></div>
</div>
<div class="c web crema"><div class="t s"><b>Estado de los modelos</b> · Ridge R² 0,945 · CNN Acc 81,9 % · BiGRU en ajuste</div></div>
''', URL_A, [], "", alto=ALTO_A)

    serie_valle = [1.05, 1.10, 0.98, 0.92, 1.01, 1.12, 1.18, 1.15, 1.21, 1.19, 1.24, 1.22]
    serie_nal = [0.98, 1.02, 0.90, 0.85, 0.93, 1.05, 1.10, 1.08, 1.12, 1.10, 1.14, 1.13]
    p2 = navegador(f'''
{_pestanas("Dashboard")}
<div><p class="h1 web">Dashboard agroclimático</p><div class="sub">Rendimiento, precio y ENSO por departamento</div></div>
<div class="fila" style="position:relative">{badge(1)}
 <span class="chip borde">{icono("filtro",10)} Departamento: Valle del Cauca ▾</span>
 <span class="chip borde">Años: 2007–2018 ▾</span><span class="chip borde">Variable: rendimiento ▾</span>
</div>
<div class="c web" style="position:relative">{badge(2)}
 <div class="fila" style="justify-content:space-between"><span class="t b7">Rendimiento (t/ha)</span>
 <span class="t xs mut">— Valle · - - Nacional</span></div>
 {linea([(serie_valle, "#6B4A35", False), (serie_nal, "#B8A796", True)], 350, 150,
        ["2007", "", "", "2010", "", "", "2013", "", "", "2016", "", "2018"], 0.8, 1.3, 0.1)}
</div>
<div class="c web" style="position:relative;padding:4px 6px">{badge(3)}
 <table class="tabla"><tr><th>Año</th><th>Área (ha)</th><th>Producción (t)</th><th>t/ha</th><th>ONI</th><th>Fase</th></tr>
 <tr><td>2018</td><td class="n">71.420</td><td class="n">87.130</td><td class="n">1,22</td><td class="n">+0,1</td><td>Neutro</td></tr>
 <tr><td>2017</td><td class="n">72.050</td><td class="n">89.340</td><td class="n">1,24</td><td class="n">−0,4</td><td>Neutro</td></tr>
 <tr><td>2016</td><td class="n">73.110</td><td class="n">87.000</td><td class="n">1,19</td><td class="n">+1,4</td><td>Niño</td></tr>
 <tr><td>2015</td><td class="n">74.300</td><td class="n">89.900</td><td class="n">1,21</td><td class="n">+1,6</td><td>Niño</td></tr></table>
</div>
''', URL_A, [], "", alto=ALTO_A)

    p3 = navegador(f'''
{_pestanas("Rendimiento")}
<div><p class="h1 web">Predicción de rendimiento</p><div class="sub">Ingresa las condiciones del cultivo</div></div>
<div class="c web" style="position:relative;display:flex;flex-direction:column;gap:7px">{badge(1)}
 <div class="grid2"><div><div class="et">Municipio</div><div class="ctx" style="padding:5px 7px">Escribe el municipio…</div></div>
 <div><div class="et">Altitud (msnm)</div><div class="ctx" style="padding:5px 7px">1.450</div></div></div>
 {''.join(f'<div><div class="fila" style="justify-content:space-between"><span class="et">{et}</span><span class="t s b7">{v}</span></div><div class="barra" style="height:5px"><i style="width:{w}%;background:#8C6B55"></i></div></div>' for et, v, w in [("Temperatura media (°C)", "20,5", 55), ("Precipitación mensual (mm)", "210", 48), ("ONI (ENSO)", "+0,1", 52)])}
 <div class="btn s" style="width:120px">Predecir</div>
</div>
<div class="grid2">
 <div class="c web" style="position:relative">{badge(2)}<div class="et">Rendimiento estimado</div><div class="v xl">1,24 <span class="t">t/ha</span></div><div class="t xs mut">Modelo: Stacking</div></div>
 <div class="c web rojo" style="position:relative">{badge(3)}<div class="t s b7 rojo-t">{icono("alerta",11)} Sin datos sanitarios</div><div class="t xs" style="margin-top:3px">El cálculo no sabe si la finca tiene roya.</div></div>
</div>
''', URL_A, [], "", alto=ALTO_A)

    p4 = navegador(f'''
{_pestanas("Enfermedades")}
<div><p class="h1 web">Detector de enfermedades</p><div class="sub">Sube una foto de hoja de café</div></div>
<div class="c web" style="position:relative;border-style:dashed;display:flex;align-items:center;gap:10px">{badge(1)}
 <div style="width:150px;flex:none;border-radius:8px;overflow:hidden;background:#fff">{hoja(150, 84, uid="a4")}</div>
 <div><div class="t b7">hoja_lote2.jpg</div><div class="t xs mut">Arrastra o selecciona · JPG, PNG</div></div>
</div>
<div class="c web" style="position:relative">{badge(2)}
 <div class="fila" style="justify-content:space-between"><span class="v">Roya</span><span class="chip rojo">Confianza 87 %</span></div>
 <table class="tabla" style="margin-top:4px"><tr><th>Clase</th><th>Probabilidad</th></tr>
 <tr><td>Roya</td><td class="n">0,871</td></tr><tr><td>Cercospora</td><td class="n">0,082</td></tr>
 <tr><td>Sano</td><td class="n">0,031</td></tr><tr><td>Phoma</td><td class="n">0,016</td></tr></table>
</div>
<div class="c web crema" style="position:relative">{badge(3)}<div class="t s">Fin del flujo: para saber qué hacer, abre la pestaña <b>Chatbot</b>.</div></div>
''', URL_A, [], "", alto=ALTO_A)

    p5 = navegador(f'''
{_pestanas("Chatbot")}
<div><p class="h1 web">Chatbot RAG</p><div class="sub">Pregunta al asistente técnico</div></div>
<div class="c web" style="flex:1;display:flex;flex-direction:column;gap:8px;background:#FCFAF6">
 <div class="burbuja yo" style="position:relative">{badge(1)}Tengo roya en una hoja, vivo en Caicedonia a 1.450 m. ¿Qué hago?</div>
 <div class="burbuja ia" style="position:relative">{badge(2)}La roya del cafeto (<i>Hemileia vastatrix</i>) se controla con manejo integrado: nutrición, regulación de sombra y, según el nivel de infección, fungicidas. Consulte a un técnico.</div>
 <div class="burbuja yo">¿Y cuánto me afecta la cosecha?</div>
 <div class="burbuja ia">No tengo información de su cultivo. Use la pestaña <b>Rendimiento</b>.</div>
</div>
<div class="entrada" style="position:relative">{badge(3)}Escribe tu pregunta…<span class="go">{icono("flecha",13,"#fff")}</span></div>
''', URL_A, [], "", alto=ALTO_A)

    return Lamina(
        archivo="CofiTech_mockup_A_dashboard_monolitico.png",
        titulo_html="MockUp A · Dashboard analítico monolítico",
        pie="CofiTech · MockUp A: Dashboard Analítico Monolítico Web (alternativa evaluada en el AHP · puntaje 0,1455) · datos de ejemplo",
        pantallas=[
            Pantalla("Inicio · 9 pestañas", p1, [
                ("Nueve pestañas al mismo nivel: el caficultor no sabe por dónde empezar.", "C1"),
                ("Métricas para el evaluador (datasets, modelos), no para decidir en la finca.", ""),
                ("Cada módulo es una isla: no comparten finca ni diagnóstico.", "RF01 ✗"),
            ], "web", alto_app=ALTO_A, transicion="Elige la pestaña Dashboard"),
            Pantalla("Dashboard agroclimático", p2, [
                ("Filtra por departamento: no conoce el municipio del usuario.", "RF01 ✗"),
                ("Serie EVA útil para el analista de una cooperativa.", "RF04 · C2"),
                ("Tabla densa sin una acción sugerida.", ""),
            ], "web", alto_app=ALTO_A, transicion="Cambia a Rendimiento"),
            Pantalla("Predicción de rendimiento", p3, [
                ("Vuelve a pedir municipio y altitud: captura duplicada.", "RF01 ✗"),
                ("Cifra sin fuente ni fecha del dato de entrada.", "RNF05"),
                ("El riesgo de roya no ajusta la proyección: Visión y Predicción desconectadas.", "RF02 → RF04 ✗"),
            ], "web", alto_app=ALTO_A, transicion="Abre Enfermedades"),
            Pantalla("Detector de enfermedades", p4, [
                ("Diagnóstico por foto con la CNN.", "RF02"),
                ("Probabilidades crudas, sin mapa de atención ni explicación.", "RF02 parcial"),
                ("Termina ahí: no hay «¿Qué hago?» ni registro para alertas.", "RF05 ✗"),
            ], "web", alto_app=ALTO_A, transicion="Copia el resultado al chat"),
            Pantalla("Chatbot RAG", p5, [
                ("El usuario repite lo que la app ya sabía.", "RF01 ✗"),
                ("Respuesta genérica, sin contexto de la finca ni fuente citada.", "RF03 parcial"),
                ("Sin 👍/👎: no mide la Tasa de Resolución del RAG.", "KPI ✗"),
            ], "web"),
        ])


# ═════════════════════════════ MockUp B ════════════════════════════════════
TABS_B = [("casa", "Inicio"), ("camara", "Foto"), ("chat", "Chat"), ("historial", "Mis fotos")]


def lamina_b() -> Lamina:
    b1 = telefono(f'''
{marca(30)}
<div><p class="h1">Hola, don Arturo</p><div class="sub">¿Cómo están tus cafetos hoy?</div></div>
<div class="c cafe" style="position:relative;display:flex;flex-direction:column;gap:8px;padding:14px 13px">{badge(1)}
 <div style="width:42px;height:42px;border-radius:12px;background:rgba(255,255,255,.14);display:grid;place-items:center">{icono("camara",22,"#fff")}</div>
 <div class="v l" style="color:#fff">Revisa una hoja</div>
 <div class="t" style="color:#EBDDD0">Toma una foto y la IA te dice si tiene roya u otra enfermedad.</div>
 <div class="btn" style="background:#fff;color:#6B4A35;margin-top:2px">{icono("camara",14)} Tomar foto</div>
</div>
<div class="c verde" style="position:relative">{badge(2)}
 <div class="fila"><span class="punto" style="background:#fff;width:28px;height:28px">{icono("wifi_off",14,"#2E6F40")}</span>
 <div><div class="t b7 verde-t">Funciona con poca señal</div><div class="t s mut">2 fotos en cola: se envían al volver la señal</div></div></div>
</div>
<div class="c" style="position:relative">{badge(3)}
 <div class="et">Consejo del día</div>
 <div class="t" style="margin-top:3px">Revisa el envés de las hojas del tercio medio: ahí aparece primero la roya.</div>
</div>
<div class="c crema"><div class="fila"><span>{icono("chat",14)}</span><div><div class="t b7">¿Tienes una duda?</div><div class="t s mut">Pregúntale al asistente</div></div></div></div>
''', TABS_B, 0)

    b2 = telefono(f'''
<div class="fila" style="justify-content:space-between">{marca(26)}<span class="chip borde">Paso 1 de 2</span></div>
<div><p class="h1">Toma la foto</p><div class="sub">Una sola hoja, de cerca y con buena luz</div></div>
<div style="position:relative">{badge(1)}<div style="position:relative;height:300px;border-radius:18px;background:#24302A;overflow:hidden;display:grid;place-items:center">
 <div style="transform:rotate(-12deg)">{hoja(220, 123, uid="b2")}</div>
 <div style="position:absolute;inset:34px 26px;border:2px dashed rgba(255,255,255,.8);border-radius:14px"></div>
 <div style="position:absolute;top:12px;left:0;right:0;text-align:center;color:#fff;font-size:11px;font-weight:600">Centra la hoja en el recuadro</div>
</div></div>
<div class="grid3" style="position:relative">{badge(2)}
 <div class="c crema" style="padding:7px;text-align:center"><div class="t s b7">☀ Luz</div><div class="t xs mut">sin sombra fuerte</div></div>
 <div class="c crema" style="padding:7px;text-align:center"><div class="t s b7">↔ 20 cm</div><div class="t xs mut">de distancia</div></div>
 <div class="c crema" style="padding:7px;text-align:center"><div class="t s b7">↺ Envés</div><div class="t xs mut">si ves polvillo</div></div>
</div>
<div style="display:flex;justify-content:center;position:relative;margin-top:2px">
 <div style="position:relative;width:62px;height:62px;border-radius:50%;border:4px solid #6B4A35;display:grid;place-items:center">{badge(3)}
 <div style="width:46px;height:46px;border-radius:50%;background:#6B4A35"></div></div></div>
''', TABS_B, 1)

    b3 = telefono(f'''
{marca(30)}
<div><p class="h1">Resultado</p><div class="sub">hoja_lote2.jpg · hace 1 minuto</div></div>
<div class="c" style="position:relative;padding:0;overflow:visible">{badge(2)}
 <div style="border-radius:14px 14px 0 0;overflow:hidden;display:flex">{hoja(134, 90, uid="b3a")}{hoja(134, 90, gradcam=True, uid="b3b")}</div>
 <div class="fila" style="justify-content:space-around;padding:4px 0 6px"><span class="t xs mut">Tu foto</span><span class="t xs rojo-t b7">Dónde miró la IA</span></div>
</div>
<div class="c" style="position:relative">{badge(1)}
 <div class="fila" style="justify-content:space-between"><span class="v l">Roya del cafeto</span><span class="chip rojo">87 %</span></div>
 <div class="et" style="margin:6px 0 4px">Confianza del modelo</div><div class="barra"><i style="width:87%"></i></div>
 <div class="t s mut" style="margin-top:6px">Manchas amarillo-naranja con polvillo en el envés. Otras posibilidades: Cercospora 8 %.</div>
</div>
<div class="btn" style="position:relative">{badge(3)}{icono("chat",14,"#fff")} Preguntar qué hacer</div>
<div class="btn sec">{icono("camara",14)} Revisar otra hoja</div>
''', TABS_B, 1)

    b4 = telefono(f'''
{marca(30)}
<div><p class="h1">Chat</p><div class="sub">Respuestas cortas para tu cultivo</div></div>
<div class="burbuja yo">Me salió roya en una hoja. ¿Qué hago?</div>
<div class="burbuja ia" style="position:relative">{badge(1)}Revisa más hojas del lote para saber cuánta roya hay. Si es poca, mejora la nutrición y la sombra. Si hay mucha, consulta al técnico del Comité.
 <div class="t xs mut" style="margin-top:6px;position:relative">{badge(2)}Fuente: Boletines Técnicos Cenicafé</div></div>
<div class="et" style="margin-top:4px">Preguntas frecuentes</div>
<div style="display:flex;flex-wrap:wrap;gap:5px;position:relative">{badge(3)}
 <span class="chip borde">¿Cómo reviso el lote?</span><span class="chip borde">¿Qué variedad resiste?</span><span class="chip borde">¿Cuándo fertilizar?</span></div>
<div style="flex:1"></div>
<div class="entrada">Escribe tu pregunta…<span class="go">{icono("flecha",13,"#fff")}</span></div>
''', TABS_B, 2)

    filas = [("Roya", "87 %", "Hoy · lote 2", "rojo"), ("Sana", "93 %", "12 oct · lote 1", "verde"),
             ("Minador", "71 %", "5 oct · lote 2", "ambar"), ("Sana", "95 %", "28 sep · lote 3", "verde")]
    b5 = telefono(f'''
{marca(30)}
<div><p class="h1">Mis fotos</p><div class="sub">Diagnósticos guardados en este celular</div></div>
<div class="c" style="position:relative;padding:4px 10px">{badge(1)}
 {''.join(f'<div class="fila" style="padding:8px 0;border-bottom:1px solid #F0E9DF"><span class="punto" style="width:30px;height:30px;border-radius:9px;background:var(--{c}-s)">{icono("hoja",14)}</span><div style="flex:1"><div class="t b7">{n}</div><div class="t xs mut">{f}</div></div><span class="chip {c}">{p}</span></div>' for n, p, f, c in filas)}
</div>
<div class="c ambar" style="position:relative">{badge(2)}
 <div class="t b7 ambar-t">{icono("barras",12)} Sin proyección de cosecha</div>
 <div class="t s" style="margin-top:3px">Esta app no estima cuánto afecta la roya tu cosecha ni tu ingreso.</div>
</div>
<div class="c ambar" style="position:relative">{badge(3)}
 <div class="t b7 ambar-t">{icono("usuarios",12)} Tus reportes no salen del celular</div>
 <div class="t s" style="margin-top:3px">La cooperativa no recibe alertas de tu zona.</div>
</div>
''', TABS_B, 3)

    return Lamina(
        archivo="CofiTech_mockup_B_movil_asistencial.png",
        titulo_html="MockUp B · App móvil asistencial pura",
        pie="CofiTech · MockUp B: App Móvil Asistencial Pura (alternativa evaluada en el AHP · puntaje 0,2706) · datos de ejemplo",
        pantallas=[
            Pantalla("Inicio", b1, [
                ("Una sola acción principal: revisar una hoja.", "C1"),
                ("Fotos en cola sin señal; se envían después.", "C4"),
                ("Consejo genérico: la app no conoce la finca.", "RF01 ✗"),
            ], menta=True, transicion="Toca «Tomar foto»"),
            Pantalla("Tomar la foto", b2, [
                ("Guía de encuadre para una foto útil.", "RF02"),
                ("Consejos de luz, distancia y envés.", "RF02"),
                ("Obturador grande, se usa con una mano.", "RNF02"),
            ], menta=True, transicion="Captura y espera 1 s"),
            Pantalla("Resultado", b3, [
                ("Clase y confianza del modelo, en lenguaje sencillo.", "RF02"),
                ("Grad-CAM: dónde miró la IA.", "RF02"),
                ("Pasa al chat, pero sin datos de la finca.", "RF03 parcial"),
            ], menta=True, transicion="Pregunta qué hacer"),
            Pantalla("Chat básico", b4, [
                ("Respuesta corta y prudente, sin dosis.", "RF03"),
                ("Cita la fuente técnica.", "RNF05"),
                ("Sin 👍/👎: no alimenta los KPIs.", "KPI ✗"),
            ], transicion="Revisa su historial"),
            Pantalla("Mis fotos", b5, [
                ("Historial local de diagnósticos.", ""),
                ("Sin proyección de cosecha ni precio: KR3 no se puede cumplir.", "RF04 ✗"),
                ("Los datos no llegan a la cooperativa: no hay alertas territoriales.", "RF05 ✗"),
            ]),
        ])


# ═════════════════════ MockUp C · vista web B2B (Agrónomo) ═════════════════
URL_C = "app.cofitech.co/cooperativa"
ALTO_C = 500
MENU_C = ["Panorama", ("mapa", "Mi zona"), ("alerta", "Alertas"), ("barras", "Indicadores"),
          "Modelos", ("precio", "Precios"), ("chat", "Consola RAG"), "Reportes", ("doc", "Alerta epid.")]


def _contexto(con_badge: bool = False) -> str:
    relleno = ' style="padding-right:22px"' if con_badge else ""
    return (f'<div class="ctx"{relleno}>{badge(1) if con_badge else ""}<span>{icono("pin",11)}</span>'
            f'<span class="vv">Quindío, Risaralda</span><span class="k">·</span><span class="k">ENSO</span>'
            f'<span class="vv">Neutro</span><span class="k">·</span><span class="k">FNC</span>'
            f'<span class="vv">$2.745.226</span><span class="k">·</span><span class="vv rojo-t">128 fotos (30 d)</span></div>')


def _titulo_c(titulo: str, sub: str) -> str:
    return f'<div><p class="h1 web">{titulo}</p><div class="sub">{sub}</div></div>'


PUNTOS_ZONA = [("Pijao", 118, 150, .85), ("Génova", 150, 188, .62), ("Salento", 196, 52, .35),
               ("Calarcá", 168, 104, .48), ("Marsella", 82, 40, .40), ("Armenia", 110, 102, .18),
               ("Santa Rosa", 252, 32, .10), ("Filandia", 236, 88, .22)]


def lamina_c() -> Lamina:
    c1 = navegador(f'''
{_contexto(True)}
<div class="fila" style="justify-content:space-between">{_titulo_c("Mi zona de trabajo", "Asociados que reportan desde la app móvil")}
 <span class="chip borde" style="position:relative;padding-right:16px">{badge(2)}{icono("lupa",10)} Foco: toda la zona ▾</span></div>
<div class="grid3">
 <div class="c web"><div class="et">Fotos (30 días)</div><div class="v l">128</div><div class="t xs verde-t b7">↑ 18 % vs. mes anterior</div></div>
 <div class="c web"><div class="et">Municipios con roya</div><div class="v l rojo-t">5 de 8</div><div class="t xs mut">con fotos confirmadas</div></div>
 <div class="c web"><div class="et">Sesiones activas</div><div class="v l">41</div><div class="t xs mut">caficultores y técnicos</div></div>
</div>
<div class="c web" style="position:relative;padding:5px">{badge(3)}
 {mapa_calor(354, 200, [(n, x, y, 0.0) for n, x, y, _ in PUNTOS_ZONA], uid="c1")}
</div>
<div class="t xs mut">Mapa ilustrativo de la zona · coordenadas DIVIPOLA (DANE)</div>
''', URL_C, MENU_C, alto=ALTO_C, activa="Mi zona")

    filas_alerta = [("Pijao", "Quindío", 31, 13, 42), ("Génova", "Quindío", 22, 7, 32), ("Calarcá", "Quindío", 19, 5, 26),
                    ("Marsella", "Risaralda", 15, 3, 20), ("Salento", "Quindío", 17, 3, 18)]
    c2 = navegador(f'''
{_contexto()}
{_titulo_c("Alertas fitosanitarias", "Fotos con roya enviadas por los caficultores")}
<div class="fila" style="position:relative;justify-content:space-between">{badge(1)}
 <div class="fila" style="gap:4px"><span class="chip borde">7 d</span><span class="chip osc">30 d</span><span class="chip borde">90 d</span></div>
 <span class="chip borde" style="margin-right:6px">{icono("check",10)} Sin simulados ni rechazados</span></div>
<div class="c web" style="position:relative;padding:5px">{badge(2)}{mapa_calor(354, 168, PUNTOS_ZONA, uid="c2")}</div>
<div class="c web" style="position:relative;padding:3px 6px">{badge(3)}
 <table class="tabla"><tr><th>Municipio</th><th>Depto.</th><th>Fotos</th><th>Roya</th><th style="width:120px">% fotos con roya</th></tr>
 {''.join(f'<tr><td class="b7">{m}</td><td>{d}</td><td class="n">{f}</td><td class="n">{r}</td><td><div class="fila" style="gap:5px"><div class="barra" style="flex:1"><i style="width:{p}%"></i></div><span class="t xs b7">{p} %</span></div></td></tr>' for m, d, f, r, p in filas_alerta)}
 </table>
</div>
<div class="fila" style="position:relative;justify-content:space-between">{badge(4)}
 <span class="t xs verde-t b7">● En vivo · Supabase · cada 30 s</span><span class="t xs mut" style="margin-right:12px">% de fotos ≠ incidencia del lote</span></div>
''', URL_C, MENU_C, alto=ALTO_C, activa="Alertas")

    anios = ["2013", "", "", "2016", "", "", "2019", "", "", "2022", "", "2024"]
    pijao = [1.21, 1.18, 1.25, 1.12, 1.16, 1.09, 1.14, 1.05, 1.11, 1.02, 1.07, 1.04]
    depto = [1.30, 1.27, 1.31, 1.22, 1.24, 1.20, 1.23, 1.18, 1.21, 1.16, 1.19, 1.17]
    c3 = navegador(f'''
{_contexto()}
<div class="fila" style="justify-content:space-between">{_titulo_c("Indicadores · Pijao", "Rendimiento municipal EVA (MADR/UPRA)")}<span class="chip rojo">Riesgo roya: alto</span></div>
<div class="c web" style="position:relative">{badge(1)}
 <div class="fila" style="justify-content:space-between"><span class="t b7">Rendimiento (t/ha)</span><span class="t xs mut">— Pijao · - - Quindío</span></div>
 {linea([(pijao, "#6B4A35", False), (depto, "#B8A796", True)], 350, 150, anios, 0.9, 1.4, 0.1)}
</div>
<div class="grid3">
 <div class="c web" style="position:relative">{badge(2)}<div class="et">Último dato EVA</div><div class="v l">1,04</div><div class="t xs mut">t/ha · 2024</div></div>
 <div class="c web"><div class="et">vs. Quindío</div><div class="v l rojo-t">−11 %</div><div class="t xs mut">1,17 t/ha</div></div>
 <div class="c web rojo" style="position:relative">{badge(3)}<div class="et">Con roya sin control</div><div class="v l rojo-t">0,73–0,80</div><div class="t xs mut">t/ha (−23 % a −30 %)</div></div>
</div>
<div class="t xs mut">Descuento por roya según Cenicafé, Boletín Técnico 36 · solo variedades susceptibles</div>
''', URL_C, MENU_C, alto=ALTO_C, activa="Indicadores")

    c4 = navegador(f'''
{_contexto()}
{_titulo_c("Escenarios de precio", "Simulador Ridge: arábica internacional + TRM → precio interno FNC")}
<div class="c web" style="position:relative;display:flex;flex-direction:column;gap:7px">{badge(1)}
 {''.join(f'<div><div class="fila" style="justify-content:space-between"><span class="et">{et}</span><span class="t s b7">{v}</span></div><div class="barra" style="height:5px"><i style="width:{w}%;background:#2E6F40"></i></div></div>' for et, v, w in [("Arábica Brasil (USD/kg)", "8,40", 66), ("TRM (COP por USD)", "4.120", 45)])}
</div>
<div class="c web cafe" style="position:relative">{badge(2)}
 <div class="et">Precio interno estimado por carga</div><div class="v xl" style="color:#fff">$2.739.253</div>
 <div class="t s" style="color:#EBDDD0">Rango probable (90 %): $2.661.821 – $2.818.938</div>
</div>
<div class="c web" style="position:relative;padding:3px 6px">{badge(3)}
 <table class="tabla"><tr><th>Validación 2024–2025</th><th>R²</th><th>Error medio</th></tr>
 <tr><td class="b7">Ridge (arábica + TRM)</td><td class="n b7 verde-t">0,989</td><td class="n b7 verde-t">2,5 %</td></tr>
 <tr><td>Repetir el mes anterior</td><td class="n">0,890</td><td class="n">6,1 %</td></tr></table>
</div>
<div class="c web ambar" style="position:relative">{badge(4)}<div class="t s"><b>Modelos Experimentales de Alta Volatilidad (En calibración)</b> · BiGRU, LSTM, Transformer</div></div>
''', URL_C, MENU_C, alto=ALTO_C, activa="Precios")

    c5 = navegador(f'''
{_contexto()}
{_titulo_c("Consola técnica (RAG)", "Respuestas con fuente, para el técnico de campo")}
<div class="c web crema" style="position:relative;padding:6px 8px">{badge(1)}<div class="t xs"><b>Contexto inyectado:</b> Pijao · 1.600 msnm · Caturra · incidencia medida 8 % · floración hace 150 días · ENSO neutro</div></div>
<div class="burbuja yo" style="max-width:80%">¿Qué manejo recomiendo a los asociados de Pijao con 8 % de incidencia?</div>
<div class="burbuja ia" style="position:relative;max-width:96%">{badge(2)}Con incidencia ≥ 5 % en variedad susceptible se considera un <b>fungicida sistémico (triazol con registro ICA)</b>, alternando grupos químicos. Respete el <b>periodo de carencia</b> de la etiqueta y el uso de EPP. Repita el muestreo a los 30 días.
 <div class="t xs mut" style="margin-top:5px">(Fuente: Manual de Caficultura / Boletines Técnicos Cenicafé)</div></div>
<div class="fila" style="position:relative;gap:6px">{badge(3)}<span class="t xs mut">¿Te sirvió?</span>
 <span class="chip borde">{icono("pulgar",10)} Sí</span><span class="chip borde">{icono("pulgar_no",10)} No</span></div>
<div style="flex:1"></div>
<div class="entrada">Pregunta técnica…<span class="go">{icono("flecha",13,"#fff")}</span></div>
''', URL_C, MENU_C, alto=ALTO_C, activa="Consola RAG")

    c6 = navegador(f'''
{_contexto()}
<div class="fila" style="justify-content:space-between">{_titulo_c("Alerta epidemiológica", "Semana 42 · Quindío y Risaralda")}<span class="chip rojo">Prioridad alta</span></div>
<div class="c web" style="position:relative">{badge(1)}
 <div class="t b7" style="margin-bottom:5px">Municipios priorizados para visita</div>
 {''.join(f'<div class="fila" style="padding:4px 0;border-bottom:1px solid #F0E9DF"><span class="punto" style="background:var(--{c}-s);color:var(--{c})">{i}</span><span class="t b7" style="flex:1">{m}</span><span class="t xs mut">{f}</span><span class="chip {c}">{p} %</span></div>' for i, (m, f, p, c) in enumerate([("Pijao", "31 fotos · 13 con roya", 42, "rojo"), ("Génova", "22 fotos · 7 con roya", 32, "rojo"), ("Calarcá", "19 fotos · 5 con roya", 26, "ambar")], start=1))}
</div>
<div class="c web verde" style="position:relative">{badge(2)}
 <div class="t b7 verde-t" style="margin-bottom:4px">Acciones sugeridas</div>
 <div class="lista">
  <div class="it">{icono("check",11,"#2E6F40")} Muestreo de incidencia en lotes de Caturra</div>
  <div class="it">{icono("check",11,"#2E6F40")} Visita del extensionista del Comité</div>
  <div class="it">{icono("check",11,"#2E6F40")} Aviso a asociados por la app móvil</div>
 </div>
</div>
<div class="grid3" style="position:relative">{badge(3)}
 <div class="btn s">{icono("descarga",11,"#fff")} PDF</div><div class="btn s sec">{icono("descarga",11)} CSV</div>
 <div class="btn s verde">{icono("enviar",11,"#fff")} Enviar</div>
</div>
''', URL_C, MENU_C, alto=ALTO_C, activa="Alerta epid.")

    return Lamina(
        archivo="CofiTech_mockup_dual_b2b_agronomo.png",
        titulo_html="MockUp C · Plataforma Dual · vista web Agrónomo / Cooperativa",
        pie="CofiTech · MockUp C: Plataforma Dual Adaptativa por Roles · vista web B2B del Agrónomo / Cooperativa (complementa la vista móvil del caficultor) · datos de ejemplo",
        pantallas=[
            Pantalla("Mi zona de trabajo", c1, [
                ("Barra de contexto fija: zona, ENSO, precio FNC y reportes.", "RF01"),
                ("Municipio en foco: mapa, indicadores y rendimiento se centran solos.", "RF01"),
                ("Municipios de la zona con coordenadas DIVIPOLA.", "RF05"),
            ], "web", alto_app=ALTO_C, transicion="Filtra por municipio"),
            Pantalla("Alertas fitosanitarias", c2, [
                ("Periodo y filtros: excluye simulados y diagnósticos rechazados con 👎.", "RF05"),
                ("Mapa de calor con las fotos de los caficultores.", "RF02 → RF05"),
                ("Tabla para priorizar visitas: % de fotos, no incidencia del lote.", "RF05"),
                ("Lectura en vivo desde Supabase cada 30 s.", "RNF03"),
            ], "web", alto_app=ALTO_C, transicion="Revisa el municipio"),
            Pantalla("Indicadores municipales", c3, [
                ("Serie EVA del municipio frente al departamento.", "RF04"),
                ("Cifra principal: el último dato real, con fuente y año.", "RNF05"),
                ("Impacto de la roya sin control según Cenicafé.", "RF02 → RF04"),
            ], "web", alto_app=ALTO_C, transicion="Simula precio Ridge"),
            Pantalla("Escenarios de precio", c4, [
                ("Escenarios con arábica y TRM del mismo mes.", "RF04"),
                ("Precio estimado con rango probable.", "RF04"),
                ("Validado en el tiempo contra la referencia ingenua.", "C4"),
                ("Redes recurrentes rotuladas como experimentales.", ""),
            ], "web", menta=True, alto_app=ALTO_C, transicion="Consulta a la IA"),
            Pantalla("Consola técnica (RAG)", c5, [
                ("El contexto de la zona y la incidencia viaja solo a la pregunta.", "RF01 → RF03"),
                ("Manejo por umbral del 5 %, sin dosis y con fuente Cenicafé.", "RF03"),
                ("👍/👎 alimentan la Tasa de Resolución del RAG.", "KPI"),
            ], "web", menta=True, alto_app=ALTO_C, transicion="Exporta alerta epidemiológica"),
            Pantalla("Alerta epidemiológica", c6, [
                ("Municipios priorizados a partir de las alertas.", "RF05"),
                ("Acciones de campo, sin prescripción química.", "RF03"),
                ("Exporta y envía a extensionistas (propuesto para la versión B2B).", "C2"),
            ], "web", menta=True),
        ])


LAMINAS = [lamina_a, lamina_b, lamina_c]
