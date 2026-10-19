"""Genera las láminas PNG de los MockUps de CofiTech con el sistema de diseño de la lámina de Sofía.

Uso (desde cualquier carpeta):
    pip install playwright && python -m playwright install chromium
    python 00_documentos/mockups_src/generar_mockups.py

Escribe el HTML fuente de cada lámina en ``00_documentos/mockups_src/`` y el
PNG en ``00_documentos/`` a 2× (``device_scale_factor=2``). Antes de guardar
verifica que ningún texto se salga de su pantalla ni quede cortado.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from laminas import LAMINAS  # noqa: E402
from sistema import DOCS, SRC, html  # noqa: E402

ESCALA = 2

# Revisa, dentro de cada marco, que ningún elemento se salga del área visible
# y que ningún contenedor con overflow:hidden esté recortando texto.
VERIFICAR = """
() => {
  const problemas = [];
  document.querySelectorAll('.marco').forEach((marco, i) => {
    const area = (marco.querySelector('.cuerpo') || marco.querySelector('.principal'));
    const caja = area.getBoundingClientRect();
    if (area.scrollHeight > area.clientHeight + 1)
      problemas.push(`pantalla ${i + 1}: el contenido mide ${area.scrollHeight}px y caben ${area.clientHeight}px`);
    area.querySelectorAll('*').forEach(el => {
      if (el.closest('svg') && el.tagName.toLowerCase() !== 'svg') return;
      if (el.classList.contains('badge')) return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      if (r.right > caja.right + 0.5 || r.left < caja.left - 0.5 || r.bottom > caja.bottom + 0.5)
        problemas.push(`pantalla ${i + 1}: «${(el.textContent || el.tagName).trim().slice(0, 40)}» se sale del marco`);
      const estilo = getComputedStyle(el);
      if (estilo.overflow === 'hidden' && el.scrollWidth > el.clientWidth + 1 && !el.closest('.marco > .barra-nav'))
        problemas.push(`pantalla ${i + 1}: texto recortado en «${(el.textContent || '').trim().slice(0, 40)}»`);
    });
  });
  document.querySelectorAll('.pildora, .paso, .coment').forEach(el => {
    if (el.scrollWidth > el.clientWidth + 1) problemas.push(`recorte en «${el.textContent.trim().slice(0, 40)}»`);
  });
  return problemas;
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    errores = 0
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": 1200, "height": 900}, device_scale_factor=ESCALA)
        for construir in LAMINAS:
            lamina = construir()
            fuente = SRC / lamina.archivo.replace(".png", ".html")
            fuente.write_text(html(lamina), encoding="utf-8")
            pagina.goto(fuente.as_uri())
            pagina.evaluate("document.fonts.ready")
            pagina.wait_for_timeout(300)
            problemas = pagina.evaluate(VERIFICAR)
            salida = DOCS / lamina.archivo
            pagina.locator("#lienzo").screenshot(path=str(salida))
            estado = "OK" if not problemas else f"{len(problemas)} PROBLEMAS"
            print(f"{estado:>12}  {salida.name}")
            for problema in problemas:
                print("              ·", problema)
            errores += len(problemas)
        navegador.close()
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
