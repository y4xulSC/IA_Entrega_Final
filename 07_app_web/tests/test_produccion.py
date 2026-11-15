"""Ajustes de la versión Beta para producción (Streamlit Community Cloud).

    cd 07_app_web
    python -m pytest tests/test_produccion.py -q

Cubre: aviso Beta, mercado inactivo por defecto, autorización de datos al
entrar, aviso de privacidad y el orden de carga Triton → TensorFlow en Linux.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from cofitech import config, mercado, privacidad, telemetria  # noqa: E402
from cofitech import navegacion as nav  # noqa: E402
from cofitech.contexto_finca import ContextoFinca, Finca, Mercado, Rol, Zona  # noqa: E402
from cofitech.repositorio import db_client  # noqa: E402


@pytest.fixture(autouse=True)
def sin_base_y_sin_env(tmp_path, monkeypatch):
    """Sin base de datos, sin .env del proyecto y con archivos en una carpeta temporal."""
    monkeypatch.delenv("COFITECH_MERCADO_ACTIVO", raising=False)
    monkeypatch.setattr(config, "PROYECTO", Path("/no/existe"))
    monkeypatch.setattr(db_client, "_dsn", lambda: None)
    monkeypatch.setattr(mercado, "DIR_LOCAL", tmp_path)
    monkeypatch.setattr(telemetria, "RUTA_EVENTOS", tmp_path / "eventos.jsonl")


def _ctx(rol=Rol.CAFICULTOR) -> ContextoFinca:
    return ContextoFinca(
        rol=rol, finca=Finca(municipio="Caicedonia", departamento="Valle del Cauca", codigo_dane="76122",
                             altitud_msnm=1450, area_ha=3.2, variedad="Castillo"),
        zona=Zona(departamentos=["Valle del Cauca"]),
        mercado=Mercado(precio_fnc_cop_carga=2_650_000, fecha=date(2026, 9, 1)))


def _pantalla(archivo: str, ctx) -> AppTest:
    at = AppTest.from_file(str(APP / archivo), default_timeout=120)
    at.session_state["cofitech_ctx"] = ctx
    return at.run()


# ─────────────────────────────── Configuración ──────────────────────────────
def test_mercado_inactivo_por_defecto_y_se_enciende_por_variable(monkeypatch):
    assert config.mercado_activo() is False
    monkeypatch.setenv("COFITECH_MERCADO_ACTIVO", "1")
    assert config.mercado_activo() is True
    monkeypatch.setenv("COFITECH_MERCADO_ACTIVO", "no")
    assert config.mercado_activo() is False


def test_menu_marca_el_mercado_como_inactivo_y_lo_saca_del_recorrido():
    for rol, clave in ((Rol.CAFICULTOR, "venta"), (Rol.AGRONOMO, "lotes")):
        pantalla = next(p for p in nav.menu(rol) if p.clave == clave)
        assert pantalla.titulo.endswith(nav.SUFIJO_INACTIVO)
        assert clave not in nav.flujo(rol)
    # Las herramientas de IA siguen en el recorrido del caficultor.
    assert nav.flujo(Rol.CAFICULTOR) == ["inicio", "diagnostico", "que_hago", "cosecha"]
    # Ninguna pantalla se borró del menú.
    assert {p.clave for p in nav.menu(Rol.CAFICULTOR)} == {p.clave for p in nav.MENU[Rol.CAFICULTOR]}


def test_menu_con_mercado_activo_queda_como_antes(monkeypatch):
    monkeypatch.setenv("COFITECH_MERCADO_ACTIVO", "1")
    assert nav.menu(Rol.CAFICULTOR) == nav.MENU[Rol.CAFICULTOR]
    assert nav.flujo(Rol.AGRONOMO) == nav.FLUJO[Rol.AGRONOMO]


def test_aviso_de_privacidad_describe_lo_que_se_guarda():
    texto = privacidad.texto_aviso()
    for frase in ("artículo 8", "La foto no", "Groq", "Supabase", "no pide nombre", "simulador de venta no guarda"):
        assert frase in texto
    assert "inactiva en la Beta" in texto


# ───────────────────────────────── Pantallas ────────────────────────────────
def test_vender_inactivo_muestra_aviso_y_no_permite_publicar():
    at = _pantalla("vistas/vender.py", _ctx())
    assert not at.exception
    assert any("Inactivo en la Beta" in m.value for m in at.markdown)
    assert not [b for b in at.button if b.label == "Publicar lote"]
    assert not [r for r in at.radio if r.label == "Sección"]          # no aparecen las secciones del mercado
    assert [b for b in at.button if b.label == "Ver ofertas simuladas"]
    assert any("¿Te gustaría vender tu café" in m.value for m in at.markdown)


def _boton(at: AppTest, texto: str):
    return next(b for b in at.button if texto in b.label)


def _eventos(tmp_path) -> list[dict]:
    import json
    ruta = tmp_path / "eventos.jsonl"
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines()] if ruta.exists() else []


def test_simulador_de_venta_completo_sin_guardar_el_lote(tmp_path):
    at = _pantalla("vistas/vender.py", _ctx())
    _boton(at, "Ver ofertas simuladas").click().run()
    assert not at.exception
    assert any("Mejor oferta simulada" in m.value for m in at.markdown)
    assert any("Cafés Altos del Valle" in m.value for m in at.markdown)

    _boton(at, "Negociar con este comprador").click().run()          # el primero = la mejor oferta
    assert any("Negocia (práctica)" in m.value for m in at.markdown)
    at.number_input[-1].set_value(3_000_000).run()
    _boton(at, "Enviar contraoferta").click().run()
    assert any("No llegamos a tanto" in m.value for m in at.markdown)
    _boton(at, "Aceptar $").click().run()
    assert not at.exception
    assert any("Venta de práctica cerrada" in s.value for s in at.success)

    assert not list(tmp_path.glob("*.jsonl")) or {f.name for f in tmp_path.iterdir()} == {"eventos.jsonl"}
    acciones = [e["accion"] for e in _eventos(tmp_path)]
    assert {"simulacion_venta", "simulacion_contraoferta", "simulacion_cierre"} <= set(acciones)
    assert "lote_publicado" not in acciones


def test_voto_de_interes_queda_como_kpi(tmp_path):
    at = _pantalla("vistas/vender.py", _ctx())
    _boton(at, "Ver ofertas simuladas").click().run()
    _boton(at, "Sí, me gustaría").click().run()
    assert not at.exception
    assert _boton(at, "Sí, me gustaría").disabled and _boton(at, "No la usaría").disabled
    votos = [e for e in _eventos(tmp_path) if e["accion"] == "interes_venta_directa"]
    assert len(votos) == 1
    assert votos[0]["herramienta"] == "Mercado"
    assert votos[0]["metadata"]["le_gustaria"] is True and votos[0]["metadata"]["uso_simulador"] is True
    kpis = telemetria.calcular_kpis(telemetria.leer_eventos())
    assert kpis["votos_interes_mercado"] == 1 and kpis["interes_mercado"] == 1.0
    assert kpis["sesiones_simulador"] == 1


# ───────────────────────────── Simulador (reglas) ───────────────────────────
from cofitech import simulador_mercado as sim  # noqa: E402


def _lote(**cambios) -> mercado.Lote:
    datos = dict(tipo_cafe="Pergamino seco", cantidad_cargas=20.0, precio_esperado_cop_carga=2_782_000,
                 precio_fnc_ref_cop_carga=2_650_000, departamento="Valle del Cauca")
    datos.update(cambios)
    return mercado.Lote(**datos)


def test_simulador_usa_las_reglas_del_mercado():
    r = sim.simular(_lote())
    assert [o.comprador.id for o in r.ofertas] == ["demo-cafes-altos-valle", "demo-cooperativa-suroeste"]
    assert r.mejor.precio_cop_carga == 2_690_000 and r.mejor.total_cop == 53_800_000
    assert r.ganancia_vs_fnc == 800_000
    motivos = dict((c.id, m) for c, m in r.sin_oferta)
    assert "puntaje" in motivos["demo-tostadora-montana"]
    assert any("84 puntos" in c for c in sim.consejos(r))


def test_simulador_especial_y_cereza():
    especial = sim.simular(_lote(tipo_cafe="Especial", puntaje_sca=86, cantidad_cargas=60,
                                 precio_esperado_cop_carga=3_000_000))
    assert len(especial.ofertas) == 5 and especial.mejor.comprador.id == "demo-tostadora-sur-huila"
    cereza = sim.simular(_lote(tipo_cafe="Cereza"))
    assert {o.comprador.tipo for o in cereza.ofertas} == {"Cooperativa"}
    assert all("cereza" in m.lower() for c, m in cereza.sin_oferta if c.tipo != "Cooperativa")


def test_negociacion_simulada():
    lote = _lote()
    neg = sim.iniciar_negociacion(sim.simular(lote).mejor)
    assert sim.contraofertar(neg, lote, 2_780_000) == "contraoferta"
    assert neg.vigente == 2_700_000                                  # tope: FNC + 1,25 × prima de 40.000
    assert sim.contraofertar(neg, lote, 2_700_000) == "acepta"
    cierre = sim.cerrar(neg, lote)
    assert cierre["total"] == 54_000_000 and cierre["diferencia_vs_fnc"] == 1_000_000
    assert neg.cerrada and neg.historial[-1][0] == "sistema"


def test_simulador_nunca_usa_compradores_reales():
    real = replace(mercado.COMPRADORES_DEMO[1], id="real-1", es_demo=False)
    r = sim.simular(_lote(), (real,) + mercado.COMPRADORES_DEMO)
    assert "real-1" not in {o.comprador.id for o in r.ofertas} | {c.id for c, _ in r.sin_oferta}


def test_oferta_de_zona_inactiva():
    at = _pantalla("vistas/lotes_zona.py", _ctx(Rol.AGRONOMO))
    assert not at.exception
    assert any("Inactivo en la Beta" in m.value for m in at.markdown)
    assert not at.dataframe


def test_inicio_lleva_al_diagnostico_y_no_a_compradores():
    at = _pantalla("pages/8_Asesor_Caficultor.py", _ctx())
    assert not at.exception
    assert any("manchas en las hojas" in m.value for m in at.markdown)
    assert not any("compradores busca" in m.value for m in at.markdown)


def test_ingreso_muestra_beta_y_pide_autorizacion():
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=120).run()
    assert not at.exception
    assert any("BETA" in m.value and config.VERSION in m.value for m in at.markdown)
    at.radio[0].set_value("Soy agrónomo o trabajo en una cooperativa").run()
    at.multiselect[0].set_value(["Quindío"])
    at.button[0].click().run()                                     # sin marcar la casilla
    assert any("autorización" in e.value for e in at.error)
    assert at.session_state["cofitech_ctx"].rol is None
    at.checkbox[0].check()
    at.button[0].click().run()
    assert at.session_state["cofitech_ctx"].rol == Rol.AGRONOMO
    assert at.session_state[privacidad._CLAVE_ACEPTO] == privacidad.VERSION_AVISO
    assert any("BETA" in m.value for m in at.markdown)              # la franja sigue después de entrar


def test_pagina_de_aviso_de_privacidad():
    at = _pantalla("vistas/privacidad.py", _ctx())
    assert not at.exception
    assert any("Tus derechos" in m.value for m in at.markdown)


# ─────────────────────────── Despliegue en Linux ────────────────────────────
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="el choque Triton/TensorFlow solo ocurre en Linux")
def test_tensorflow_y_el_asistente_conviven_en_el_mismo_proceso():
    """Abrir «Revisar una hoja» (TensorFlow) y luego el asistente (PyTorch/Triton) no debe tumbar el servidor."""
    pytest.importorskip("tensorflow")
    pytest.importorskip("sentence_transformers")
    codigo = "import cofitech, tensorflow, sentence_transformers; print('ok')"
    r = subprocess.run([sys.executable, "-c", codigo], cwd=APP, capture_output=True, text=True, timeout=600,
                       env={"TF_CPP_MIN_LOG_LEVEL": "3", "PATH": "/usr/bin:/bin"})
    assert r.returncode == 0 and r.stdout.strip().endswith("ok"), r.stderr[-500:]


def test_pantalla_de_telemetria_muestra_el_kpi_de_interes(tmp_path):
    from cofitech import seguridad
    _pantalla("vistas/vender.py", _ctx())                           # crea el archivo de eventos
    import json
    with (tmp_path / "eventos.jsonl").open("a", encoding="utf-8") as f:
        for voto in (True, True, False):
            f.write(json.dumps({"timestamp": "2026-11-15T08:00:00-05:00", "id_sesion": f"s{voto}{id(voto)}",
                                "usuario_rol": "Caficultor", "herramienta": "Mercado",
                                "accion": "interes_venta_directa",
                                "metadata": {"le_gustaria": voto, "uso_simulador": False}}) + "\n")
    at = AppTest.from_file(str(APP / "vistas/telemetria.py"), default_timeout=120)
    at.session_state["cofitech_ctx"] = _ctx()
    at.session_state[seguridad._CLAVE_ADMIN] = True
    at.run()
    assert not at.exception
    metrica = next(m for m in at.metric if m.label == "Interés en la venta directa")
    assert metrica.value == "67%"


def test_icono_se_puede_usar_desde_varios_hilos():
    """En la nube varias sesiones llaman st.set_page_config a la vez con el mismo ICONO."""
    import io
    import threading
    from cofitech import marca
    assert not isinstance(marca.ICONO, str) and getattr(marca.ICONO, "fp", None) is None   # sin archivo abierto
    errores = []

    def guardar():
        try:
            marca.ICONO.save(io.BytesIO(), format="PNG")
        except Exception as error:                     # noqa: BLE001
            errores.append(error)

    hilos = [threading.Thread(target=guardar) for _ in range(16)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert not errores


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="el ajuste de hilos solo aplica en Linux")
def test_hilos_limitados_y_faulthandler_activo():
    """En la nube TensorFlow no debe dimensionar sus hilos con los núcleos del servidor físico."""
    import faulthandler
    import os
    import cofitech
    assert faulthandler.is_enabled()
    assert 1 <= cofitech._nucleos_disponibles() <= (os.cpu_count() or 1)
    assert int(os.environ["TF_NUM_INTRAOP_THREADS"]) <= 4
    assert os.environ["TF_NUM_INTEROP_THREADS"] == "1"
