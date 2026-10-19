"""Sistema de diseño de las láminas de MockUp de CofiTech (clon del estilo de la lámina de Sofía).

Tokens, marcos de dispositivo (teléfono y navegador), badges de trazabilidad,
flechas conectoras y tarjetas de COMENTARIOS. Las láminas (``laminas.py``)
solo describen el contenido de cada pantalla con estas piezas.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

SRC = Path(__file__).resolve().parent
DOCS = SRC.parent
LOGO = DOCS / "logo_cofitech.jpeg"

# Región del emblema (sin el texto) dentro de logo_cofitech.jpeg (1254 × 1254 px).
EMBLEMA = {"x": 270, "y": 170, "w": 715, "h": 570, "lado": 1254}

ANCHO_MOVIL = 320
ANCHO_WEB = 520

CSS = """
:root{
  --lienzo:#F3EFE6; --tinta:#2C1A11; --paso:#3D2314; --cafe:#6B4A35; --cafe-2:#8C6B55;
  --suave:#7A685B; --linea:#E6DCCF; --pantalla:#FAF7F2; --tarjeta:#FFFFFF; --crema:#F1EBE1;
  --verde:#2E6F40; --verde-s:#E4F1E8; --verde-b:#B8DEC6; --oro:#E5A93B;
  --rojo:#B5462F; --rojo-s:#F8E3DD; --ambar:#B7790F; --ambar-s:#FBEFD3; --marco:#1E1E1E;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--lienzo)}
body{font-family:'Inter',system-ui,sans-serif;color:var(--tinta);-webkit-font-smoothing:antialiased;
     font-feature-settings:'cv11','ss01'}
.lienzo{display:flex;gap:36px;align-items:flex-start;padding:48px;width:max-content;background:var(--lienzo)}
.col{display:flex;flex-direction:column;gap:20px;flex:none}
.col.movil{width:320px}.col.web{width:520px}
.paso{display:flex;align-items:center;gap:12px;font-weight:700;font-size:19px;letter-spacing:-.01em;height:34px;white-space:nowrap}
.paso .n{width:30px;height:30px;border-radius:50%;background:var(--paso);color:#fff;display:grid;place-items:center;font-size:15px;font-weight:700;flex:none}

/* ── Conector entre pantallas ── */
.conector{flex:none;width:112px;display:flex;flex-direction:column;align-items:center;gap:10px}
.conector .pildora{background:#fff;border:1.5px solid var(--verde);color:var(--verde);border-radius:10px;padding:7px 9px;
  font-size:11.5px;font-weight:700;line-height:1.25;text-align:center;max-width:112px}
.conector svg{display:block}

/* ── Marco teléfono ── */
.telefono{width:320px;height:664px;border:10px solid var(--marco);border-radius:42px;background:var(--pantalla);overflow:hidden;
  display:flex;flex-direction:column;box-shadow:0 22px 44px -18px rgba(61,35,20,.35)}
.estado{height:36px;flex:none;display:flex;justify-content:space-between;align-items:center;padding:4px 22px 0;font-weight:600;font-size:13px}
.estado .ico{display:flex;gap:5px;align-items:center}
.cuerpo{flex:1;min-height:0;padding:4px 15px 10px;display:flex;flex-direction:column;gap:9px;overflow:hidden}
.tabbar{flex:none;height:60px;border-top:1px solid var(--linea);background:#fff;display:flex;justify-content:space-around;align-items:center;padding:0 6px 4px}
.tab{display:flex;flex-direction:column;align-items:center;gap:3px;font-size:9px;font-weight:600;color:#A79A8E;width:56px}
.tab .i{width:40px;height:26px;border-radius:13px;display:grid;place-items:center}
.tab.on{color:var(--tinta)}.tab.on .i{background:var(--crema)}

/* ── Marco navegador ── */
.navegador{width:520px;border:8px solid var(--marco);border-radius:20px;background:var(--pantalla);overflow:hidden;
  box-shadow:0 22px 44px -18px rgba(61,35,20,.35);display:flex;flex-direction:column}
.barra-nav{height:30px;flex:none;background:#2A2623;display:flex;align-items:center;gap:6px;padding:0 10px}
.barra-nav .s{width:9px;height:9px;border-radius:50%}
.barra-nav .url{margin-left:14px;flex:1;height:18px;border-radius:6px;background:#3B3532;color:#D9CFC4;font-size:9.5px;
  display:flex;align-items:center;gap:5px;padding:0 8px;font-weight:500}
.app{display:flex;height:540px;min-height:0}
.lateral{width:104px;flex:none;background:#fff;border-right:1px solid var(--linea);padding:10px 8px;display:flex;flex-direction:column;gap:3px}
.lateral .item{display:flex;align-items:center;gap:6px;font-size:9.5px;font-weight:600;color:var(--suave);padding:6px 6px;border-radius:7px;white-space:nowrap}
.lateral .item.on{background:var(--crema);color:var(--tinta)}
.lateral .sec{font-size:8px;font-weight:700;letter-spacing:.06em;color:#B4A698;margin:8px 6px 2px;text-transform:uppercase}
.principal{flex:1;min-width:0;padding:12px 14px;display:flex;flex-direction:column;gap:9px;overflow:hidden}

/* ── Encabezado de marca ── */
.marca{display:flex;align-items:center;gap:6px;font-weight:800;font-size:13.5px;color:var(--tinta);letter-spacing:-.01em}
.emblema{flex:none;background-repeat:no-repeat;mix-blend-mode:multiply}
.h1{font-size:21px;font-weight:800;letter-spacing:-.02em;line-height:1.1;margin:0}
.h1.web{font-size:17px}
.sub{font-size:11px;color:var(--suave);margin-top:2px;line-height:1.3}

/* ── Componentes ── */
.c{position:relative;background:var(--tarjeta);border:1px solid var(--linea);border-radius:14px;padding:10px 11px}
.c.crema{background:var(--crema);border-color:transparent}
.c.cafe{background:var(--cafe);border-color:transparent;color:#fff}
.c.verde{background:var(--verde-s);border-color:var(--verde-b)}
.c.ambar{background:var(--ambar-s);border-color:#EED690}
.c.rojo{background:var(--rojo-s);border-color:#EFC2B6}
.c.web{border-radius:11px;padding:8px 10px}
.fila{display:flex;gap:8px;align-items:center}
.fila.top{align-items:flex-start}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.et{font-size:10px;color:var(--suave);line-height:1.3}
.c.cafe .et{color:#E8D9CC}
.v{font-size:15px;font-weight:800;letter-spacing:-.01em;line-height:1.15}
.v.xl{font-size:24px}.v.l{font-size:19px}.v.s{font-size:13px}
.t{font-size:11px;line-height:1.35}
.t.s{font-size:10px}.t.xs{font-size:9px}
.b6{font-weight:600}.b7{font-weight:700}.b8{font-weight:800}
.mut{color:var(--suave)}.verde-t{color:var(--verde)}.rojo-t{color:var(--rojo)}.ambar-t{color:var(--ambar)}
.chip{display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:3px 8px;font-size:9.5px;font-weight:700;white-space:nowrap;background:var(--crema);color:var(--cafe)}
.chip.verde{background:var(--verde-s);color:var(--verde)}.chip.rojo{background:var(--rojo-s);color:var(--rojo)}
.chip.ambar{background:var(--ambar-s);color:var(--ambar)}.chip.osc{background:var(--cafe);color:#fff}
.chip.borde{background:#fff;border:1px solid var(--linea);color:var(--suave)}
.btn{display:flex;align-items:center;justify-content:center;gap:6px;border-radius:12px;height:36px;font-size:11.5px;font-weight:700;background:var(--cafe);color:#fff}
.btn.sec{background:var(--crema);color:var(--cafe)}.btn.verde{background:var(--verde)}
.btn.s{height:28px;font-size:10px;border-radius:9px}
.barra{height:6px;border-radius:3px;background:var(--crema);overflow:hidden}
.barra>i{display:block;height:100%;border-radius:3px;background:var(--rojo)}
.sep{height:1px;background:var(--linea)}
.lista{display:flex;flex-direction:column;gap:6px}
.lista .it{display:flex;gap:7px;align-items:center;font-size:10.5px}
.punto{width:16px;height:16px;border-radius:50%;display:grid;place-items:center;flex:none;font-size:9px}
.burbuja{border-radius:14px;padding:8px 10px;font-size:10.5px;line-height:1.4;max-width:88%}
.burbuja.yo{align-self:flex-end;background:var(--cafe);color:#fff;border-bottom-right-radius:4px}
.burbuja.ia{align-self:flex-start;background:#fff;border:1px solid var(--linea);border-bottom-left-radius:4px}
.entrada{display:flex;align-items:center;gap:6px;border:1px solid var(--linea);background:#fff;border-radius:22px;padding:6px 6px 6px 12px;font-size:10.5px;color:#A79A8E}
.entrada .go{margin-left:auto;width:26px;height:26px;border-radius:50%;background:var(--cafe);display:grid;place-items:center}
.ctx{display:flex;gap:6px;align-items:center;flex-wrap:nowrap;white-space:nowrap;background:#fff;border:1px solid var(--linea);border-radius:10px;padding:6px 8px;font-size:9.5px;position:relative}
.ctx .k{color:var(--suave)}.ctx .vv{font-weight:700}
.tabla{width:100%;border-collapse:collapse;font-size:9.5px}
.tabla th{text-align:left;font-weight:600;color:var(--suave);padding:4px 5px;border-bottom:1px solid var(--linea)}
.tabla td{padding:4px 5px;border-bottom:1px solid #F0E9DF;white-space:nowrap}
.tabla td.n{text-align:right;font-variant-numeric:tabular-nums}

/* ── Badge de trazabilidad ── */
.badge{position:absolute;top:-8px;right:-8px;width:21px;height:21px;border-radius:50%;background:var(--oro);color:#fff;
  font-weight:800;font-size:11px;display:grid;place-items:center;border:2px solid #fff;box-shadow:0 2px 5px rgba(61,35,20,.25);z-index:5}

/* ── Tarjeta de COMENTARIOS ── */
.coment{border-radius:16px;padding:13px 15px 14px;background:#FDF6E2;border:1px solid #EED690}
.coment.menta{background:#EAF4EE;border-color:#B8DEC6}
.coment h4{margin:0 0 9px;font-size:11px;font-weight:800;letter-spacing:.06em;color:#8A6510}
.coment.menta h4{color:var(--verde)}
.coment .it{display:flex;gap:9px;align-items:flex-start;margin-top:7px;font-size:11.5px;line-height:1.4}
.coment .it .nb{flex:none;width:20px;height:20px;border-radius:50%;background:var(--oro);color:#fff;font-weight:800;font-size:10.5px;display:grid;place-items:center;margin-top:0}
.coment .rf{display:inline-block;white-space:nowrap;margin-left:4px;font-size:9.5px;font-weight:800;color:var(--cafe);background:rgba(255,255,255,.75);border:1px solid rgba(107,74,53,.25);border-radius:6px;padding:0 5px;line-height:15px;vertical-align:1px}
.pie{position:absolute;left:48px;bottom:18px;font-size:11px;color:#9B8B7D;font-weight:500}
"""

# ───────────────────────────── Iconos (trazo) ───────────────────────────────
_ICONOS = {
    "casa": '<path d="M3 10.5 12 4l9 6.5"/><path d="M5 9.5V20h14V9.5"/><path d="M10 20v-5h4v5"/>',
    "camara": '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
    "chat": '<path d="M4 5h16v11H9l-5 4z"/>',
    "barras": '<path d="M4 20h16"/><path d="M7 20v-6"/><path d="M12 20V8"/><path d="M17 20v-9"/>',
    "historial": '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
    "mapa": '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14"/><path d="M15 6v14"/>',
    "alerta": '<path d="M12 4 2.8 19h18.4z"/><path d="M12 10v4"/><path d="M12 17h.01"/>',
    "precio": '<path d="M4 17 9 12l4 4 7-8"/><path d="M15 8h5v5"/>',
    "doc": '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M9 13h7"/><path d="M9 17h5"/>',
    "pin": '<path d="M12 21s-6-5.5-6-11a6 6 0 0 1 12 0c0 5.5-6 11-6 11z"/><circle cx="12" cy="10" r="2.2"/>',
    "nube": '<path d="M7 17h10a4 4 0 0 0 .5-8A6 6 0 0 0 6 10a3.5 3.5 0 0 0 1 7z"/>',
    "hoja": '<path d="M5 19C5 10 11 5 20 5c0 9-5 15-14 14z"/><path d="M5 19 13 11"/>',
    "check": '<path d="m5 12 4 4 10-10"/>',
    "flecha": '<path d="M5 12h13"/><path d="m13 6 6 6-6 6"/>',
    "sub": '<path d="M12 19V6"/><path d="m6 11 6-6 6 6"/>',
    "descarga": '<path d="M12 4v11"/><path d="m7 10 5 5 5-5"/><path d="M5 20h14"/>',
    "enviar": '<path d="M4 12 20 4l-6 16-3-7z"/>',
    "senal": '<path d="M5 18v-2"/><path d="M9 18v-5"/><path d="M13 18v-8"/><path d="M17 18V6"/>',
    "mas": '<path d="M12 5v14"/><path d="M5 12h14"/>',
    "lupa": '<circle cx="11" cy="11" r="6"/><path d="m20 20-4.5-4.5"/>',
    "filtro": '<path d="M4 5h16l-6 8v6l-4-2v-4z"/>',
    "usuarios": '<circle cx="9" cy="8" r="3"/><path d="M3 19c0-3.3 2.7-5 6-5s6 1.7 6 5"/><path d="M16 11a3 3 0 0 0 0-6"/><path d="M21 19c0-2.6-1.6-4.2-4-4.8"/>',
    "pulgar": '<path d="M7 11v9H4v-9z"/><path d="M7 11l4-7c1.5 0 2.5 1 2.2 2.6L12.6 10H19a2 2 0 0 1 2 2.3l-1.2 6A2 2 0 0 1 17.8 20H7"/>',
    "pulgar_no": '<path d="M7 13V4H4v9z"/><path d="M7 13l4 7c1.5 0 2.5-1 2.2-2.6L12.6 14H19a2 2 0 0 0 2-2.3l-1.2-6A2 2 0 0 0 17.8 4H7"/>',
    "calendario": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16"/><path d="M9 3v4"/><path d="M15 3v4"/>',
    "candado": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "wifi_off": '<path d="M3 3l18 18"/><path d="M8.5 16.5a5 5 0 0 1 7 0"/><path d="M5 12.5a10 10 0 0 1 4-2.3"/><path d="M19 12.5a10 10 0 0 0-3.2-2"/><path d="M12 20h.01"/>',
}


def icono(nombre: str, tam: int = 14, color: str = "currentColor", grosor: float = 1.9) -> str:
    return (f'<svg width="{tam}" height="{tam}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{grosor}" stroke-linecap="round" stroke-linejoin="round">{_ICONOS[nombre]}</svg>')


# ───────────────────────────── Marca ────────────────────────────────────────
def _logo_b64() -> str:
    if not LOGO.exists():
        raise FileNotFoundError(f"No encuentro el logo en {LOGO}")
    return base64.b64encode(LOGO.read_bytes()).decode("ascii")


def emblema(ancho: float = 30) -> str:
    """Solo el emblema del logo oficial (sin el texto), recortado con CSS a partir del JPEG en base64."""
    e = EMBLEMA
    escala = ancho / e["w"]
    alto = e["h"] * escala
    return (f'<span class="emblema" style="width:{ancho:.1f}px;height:{alto:.1f}px;'
            f'background-image:url(data:image/jpeg;base64,{{LOGO}});'
            f'background-size:{e["lado"] * escala:.2f}px {e["lado"] * escala:.2f}px;'
            f'background-position:{-e["x"] * escala:.2f}px {-e["y"] * escala:.2f}px"></span>')


def marca(ancho: float = 30) -> str:
    return f'<div class="marca">{emblema(ancho)}CofiTech</div>'


def badge(n: int) -> str:
    return f'<span class="badge">{n}</span>'


# ───────────────────────────── Marcos ───────────────────────────────────────
TABS_CAFICULTOR = [("casa", "Mi finca"), ("camara", "Revisar hoja"), ("chat", "¿Qué hago?"),
                   ("barras", "Cosecha"), ("precio", "Vender")]


def telefono(contenido: str, tabs: list[tuple[str, str]], activa: int) -> str:
    barra = "".join(
        f'<div class="tab{" on" if i == activa else ""}"><span class="i">{icono(ic, 16)}</span>{escape(et)}</div>'
        for i, (ic, et) in enumerate(tabs))
    return (f'<div class="telefono marco"><div class="estado"><span>9:41</span><span class="ico">'
            f'{icono("senal", 15, grosor=2.4)}<svg width="22" height="11" viewBox="0 0 22 11"><rect x=".5" y=".5" width="18" '
            f'height="10" rx="3" fill="none" stroke="#2C1A11"/><rect x="2" y="2" width="14" height="7" rx="1.5" fill="#2C1A11"/>'
            f'<rect x="19.5" y="3.5" width="2" height="4" rx="1" fill="#2C1A11"/></svg></span></div>'
            f'<div class="cuerpo">{contenido}</div><div class="tabbar">{barra}</div></div>')


def navegador(contenido: str, url: str, menu: list[tuple[str, str] | str], activa: str, ancho_lateral: int = 104,
              alto: int = 540) -> str:
    items = []
    for m in menu:
        if isinstance(m, str):
            items.append(f'<div class="sec">{escape(m)}</div>')
        else:
            ic, et = m
            items.append(f'<div class="item{" on" if et == activa else ""}">{icono(ic, 12)}{escape(et)}</div>')
    lateral = (f'<div class="lateral" style="width:{ancho_lateral}px"><div style="margin:0 2px 8px">{marca(24)}</div>'
               f'{"".join(items)}</div>') if menu else ""
    return (f'<div class="navegador marco"><div class="barra-nav"><span class="s" style="background:#FF5F57"></span>'
            f'<span class="s" style="background:#FEBC2E"></span><span class="s" style="background:#28C840"></span>'
            f'<span class="url">{icono("candado", 10, "#BFB3A7", 2.2)}{escape(url)}</span></div>'
            f'<div class="app" style="height:{alto}px">{lateral}<div class="principal">{contenido}</div></div></div>')


# ───────────────────────────── Lámina ───────────────────────────────────────
@dataclass
class Pantalla:
    titulo: str
    marco: str                     # HTML del teléfono o navegador ya armado
    comentarios: list[tuple[str, str]]   # (texto, RF/criterio)
    tipo: str = "movil"            # "movil" | "web"
    menta: bool = False
    transicion: str = ""           # texto de la flecha hacia la siguiente pantalla
    punteada: bool = False
    alto_app: int = 540            # solo vistas web: alto del área de la app


@dataclass
class Lamina:
    archivo: str
    titulo_html: str
    pantallas: list[Pantalla] = field(default_factory=list)
    pie: str = ""


def _conector(texto: str, punteada: bool, tipo: str, alto_app: int = 540) -> str:
    alto_titulo = 34 + 20
    centro = alto_titulo + (664 if tipo == "movil" else alto_app + 46) * 0.46
    trazo = 'stroke-dasharray="7 6"' if punteada else ""
    return (f'<div class="conector" style="margin-top:{centro - 60:.0f}px"><div class="pildora">{escape(texto)}</div>'
            f'<svg width="104" height="20" viewBox="0 0 104 20"><path d="M4 10H96" stroke="#2E6F40" stroke-width="2.5" '
            f'stroke-linecap="round" {trazo}/><path d="M88 3l9 7-9 7" fill="none" stroke="#2E6F40" stroke-width="2.5" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg></div>')


def _comentarios(items: list[tuple[str, str]], menta: bool) -> str:
    filas = "".join(
        f'<div class="it"><span class="nb">{i}</span><span>{texto}'
        + (f'<span class="rf">{escape(rf)}</span>' if rf else "") + "</span></div>"
        for i, (texto, rf) in enumerate(items, start=1))
    return f'<div class="coment{" menta" if menta else ""}"><h4>COMENTARIOS</h4>{filas}</div>'


def _fuentes() -> str:
    reglas = []
    for peso in (400, 500, 600, 700, 800):
        datos = base64.b64encode((SRC / "fonts" / f"inter-latin-{peso}-normal.woff2").read_bytes()).decode("ascii")
        reglas.append(f"@font-face{{font-family:'Inter';font-weight:{peso};font-style:normal;"
                      f"src:url(data:font/woff2;base64,{datos}) format('woff2')}}")
    return "\n".join(reglas)


def html(lamina: Lamina) -> str:
    partes = []
    for i, p in enumerate(lamina.pantallas, start=1):
        partes.append(
            f'<div class="col {p.tipo}"><div class="paso"><span class="n">{i}</span>{escape(p.titulo)}</div>'
            f'{p.marco}{_comentarios(p.comentarios, p.menta)}</div>')
        if i < len(lamina.pantallas):
            partes.append(_conector(p.transicion, p.punteada, p.tipo, p.alto_app))
    pie = f'<div class="pie">{escape(lamina.pie)}</div>' if lamina.pie else ""
    cuerpo = (f'<div class="lienzo" id="lienzo" style="position:relative;padding-bottom:64px">{"".join(partes)}{pie}</div>')
    documento = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{escape(lamina.titulo_html)}</title>'
                 f'<style>{_fuentes()}\n{CSS}</style></head><body>{cuerpo}</body></html>')
    return documento.replace("{LOGO}", _logo_b64())
