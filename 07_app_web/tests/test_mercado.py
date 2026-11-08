"""Venta directa (RF09): reglas de negocio, respaldo local, Supabase y pantallas.

    cd 07_app_web
    python -m pytest tests/test_mercado.py -q -rs

Las pruebas de base de datos solo corren con ``COFITECH_TEST_DB_URL`` (una base
de pruebas con ``03_supabase_schema.sql`` v1.5 o ``05_marketplace.sql``). Crean
lotes con ``es_demo = true`` y los borran al terminar.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from cofitech import mercado, repositorio, telemetria  # noqa: E402
from cofitech.contexto_finca import ContextoFinca, Finca, Mercado, Rol, Zona  # noqa: E402
from cofitech.repositorio import db_client  # noqa: E402

URL_PRUEBAS = os.environ.get("COFITECH_TEST_DB_URL")
requiere_bd = pytest.mark.skipif(not URL_PRUEBAS, reason="define COFITECH_TEST_DB_URL con una base de pruebas")
SQL = APP.parent / "03_scripts" / "bd" / "05_marketplace.sql"
FNC = 2_650_000


def _lote(**cambios) -> mercado.Lote:
    base = dict(tipo_cafe="Pergamino seco", cantidad_cargas=20, precio_esperado_cop_carga=2_800_000,
                precio_fnc_ref_cop_carga=FNC, municipio="Caicedonia", departamento="Valle del Cauca",
                codigo_dane="76122", altitud_msnm=1450, variedad="Castillo", puntaje_sca=83)
    base.update(cambios)
    return mercado.Lote(**base)


def _demo(id_comprador: str) -> mercado.Comprador:
    return next(c for c in mercado.COMPRADORES_DEMO if c.id == id_comprador)


@pytest.fixture
def local(tmp_path, monkeypatch):
    """Sin base de datos y con archivos en una carpeta temporal."""
    monkeypatch.setattr(db_client, "_dsn", lambda: None)
    monkeypatch.setattr(mercado, "DIR_LOCAL", tmp_path)
    monkeypatch.setattr(repositorio, "id_sesion", lambda: "sesion-prueba")
    return tmp_path


# ───────────────────────────── Reglas de negocio ────────────────────────────
def test_semilla_sql_igual_al_catalogo_de_la_app():
    sql = SQL.read_text(encoding="utf-8")
    ids = re.findall(r"\('(demo-[a-z-]+)'", sql)
    assert ids == [c.id for c in mercado.COMPRADORES_DEMO]
    for c in mercado.COMPRADORES_DEMO:
        assert f"'{c.nombre}'" in sql and f"'{c.codigo_dane}'" in sql
        assert re.search(rf"{c.prima_cop_carga},\s*{c.puntaje_min if c.puntaje_min else 'NULL'}", sql)
        assert c.es_demo and "(demo)" in c.nombre        # nunca se presentan como compradores reales


def test_interes_por_puntaje_cantidad_y_tipo():
    tostadora, exportadora, cooperativa = (_demo("demo-tostadora-montana"), _demo("demo-exportadora-andina"),
                                           _demo("demo-cafes-altos-valle"))
    assert not mercado.le_interesa(tostadora, _lote(puntaje_sca=83))          # pide 84
    assert mercado.le_interesa(tostadora, _lote(puntaje_sca=86))
    assert not mercado.le_interesa(tostadora, _lote(puntaje_sca=None))
    assert not mercado.le_interesa(exportadora, _lote(cantidad_cargas=20))    # pide 50
    assert mercado.le_interesa(exportadora, _lote(cantidad_cargas=60))
    assert mercado.le_interesa(cooperativa, _lote(tipo_cafe="Cereza", puntaje_sca=None))
    assert not mercado.le_interesa(tostadora, _lote(tipo_cafe="Cereza", puntaje_sca=90))


def test_oferta_no_pasa_lo_que_pidio_el_caficultor():
    coop = _demo("demo-cafes-altos-valle")
    assert mercado.precio_ofrecido(coop, _lote(precio_esperado_cop_carga=3_000_000)) == FNC + 40_000
    assert mercado.precio_ofrecido(coop, _lote(precio_esperado_cop_carga=2_660_000)) == 2_660_000
    assert mercado.precio_ofrecido(coop, _lote(precio_fnc_ref_cop_carga=None)) is None


def test_contraoferta_acepta_dentro_del_margen_y_si_no_parte_la_diferencia():
    tostadora = _demo("demo-tostadora-montana")                 # prima 180.000 → máximo FNC + 225.000
    lote = _lote(puntaje_sca=86)
    assert mercado.respuesta_a_contraoferta(tostadora, lote, 2_830_000, 2_870_000) == ("acepta", 2_870_000)
    decision, precio = mercado.respuesta_a_contraoferta(tostadora, lote, 2_830_000, 3_100_000)
    assert decision == "contraoferta"
    assert 2_830_000 <= precio <= FNC + 225_000


def test_validacion_del_lote():
    assert _lote().validar() == []
    assert any("especial" in e for e in _lote(tipo_cafe="Especial", puntaje_sca=None).validar())
    assert _lote(cantidad_cargas=0).validar()
    assert _lote(canales=[]).validar()
    with pytest.raises(ValueError):
        mercado.publicar_lote(_lote(cantidad_cargas=-1))


# ──────────────────────────────── Sin base ──────────────────────────────────
def test_flujo_completo_con_respaldo_local(local):
    lote, ofertas = mercado.publicar_lote(_lote(puntaje_sca=86))
    ids = {o.id_comprador for o in ofertas}
    assert ids == {"demo-tostadora-montana", "demo-cafes-altos-valle", "demo-cooperativa-suroeste",
                   "demo-tostadora-sur-huila"}                   # la exportadora pide 50 cargas
    assert all(o.es_simulada for o in ofertas)
    assert [l.id for l in mercado.mis_lotes()] == [lote.id]
    assert mercado.mis_lotes()[0].estado == "negociando"

    tostadora = next(o for o in ofertas if o.id_comprador == "demo-tostadora-montana")
    vigente = mercado.contraofertar(lote, tostadora, 2_870_000)
    assert vigente.estado == "aceptada" and vigente.origen == "caficultor"
    assert mercado.mis_lotes()[0].estado == "vendido"
    mensajes = mercado.mensajes_de(lote.id, "demo-tostadora-montana")
    assert [m.autor for m in mensajes] == ["comprador", "caficultor", "comprador"]
    assert mensajes[-1].es_simulado
    estados = {o.id: o.estado for o in mercado.ofertas_de(lote.id)}
    assert estados[tostadora.id] == "contraofertada"
    # No se guarda nada que identifique a la persona.
    texto = "".join(p.read_text(encoding="utf-8") for p in local.glob("*.jsonl"))
    assert "nombre_caficultor" not in texto and "telefono" not in texto


def test_aceptar_y_rechazar(local):
    lote, ofertas = mercado.publicar_lote(_lote(puntaje_sca=None))
    coop, suroeste = ofertas[0], ofertas[1]
    mercado.rechazar(lote, suroeste)
    mercado.aceptar(lote, coop)
    estados = {o.id: o.estado for o in mercado.ofertas_de(lote.id)}
    assert estados[coop.id] == "aceptada" and estados[suroeste.id] == "rechazada"
    with pytest.raises(ValueError):
        mercado.aceptar(lote, coop)                            # ya no está pendiente


def test_lote_sin_compradores_queda_publicado(local):
    lote, ofertas = mercado.publicar_lote(_lote(tipo_cafe="Cereza", puntaje_sca=None, precio_fnc_ref_cop_carga=None))
    assert ofertas == [] and mercado.mis_lotes()[0].estado == "publicado"


def test_resumen_para_la_cooperativa_excluye_demo_y_vendidos(local):
    mercado.publicar_lote(_lote(es_demo=True))
    vendido, ofertas = mercado.publicar_lote(_lote(codigo_dane="76736", municipio="Sevilla", puntaje_sca=None))
    mercado.aceptar(vendido, ofertas[0])
    mercado.publicar_lote(_lote(tipo_cafe="Especial", puntaje_sca=87, cantidad_cargas=5))
    tabla, fuente = mercado.lotes_por_municipio(incluir_demo=False)
    assert fuente == "archivo local"
    assert tabla["lotes"].sum() == 1 and tabla["lotes_especiales"].sum() == 1
    assert mercado.lotes_por_municipio(incluir_demo=True)[0]["lotes"].sum() == 2


# ─────────────────────────────── Con Supabase ───────────────────────────────
@pytest.fixture
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db_client, "_dsn", lambda: URL_PRUEBAS)
    monkeypatch.setattr(db_client, "_pool", None)
    monkeypatch.setattr(db_client, "_ultimo_fallo", 0.0)
    monkeypatch.setattr(mercado, "DIR_LOCAL", tmp_path)
    monkeypatch.setattr(repositorio, "id_sesion", lambda: "prueba-mercado")
    mercado.refrescar()
    yield
    with db_client._conexion() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM cafe.mk_lote WHERE id_sesion = 'prueba-mercado'")


@requiere_bd
def test_supabase_guarda_lote_ofertas_y_mensajes(bd):
    compradores = mercado.compradores()
    assert {c.id for c in mercado.COMPRADORES_DEMO} <= {c.id for c in compradores}
    lote, ofertas = mercado.publicar_lote(_lote(puntaje_sca=86, es_demo=True))
    mercado.contraofertar(lote, ofertas[0], 4_000_000)          # fuera del margen: el comprador contraoferta
    with db_client._conexion() as conn, conn.cursor() as cur:
        cur.execute("SELECT estado FROM cafe.mk_lote WHERE id = %s", (lote.id,))
        assert cur.fetchone()[0] == "negociando"
        cur.execute("SELECT count(*), sum(total_cop) FILTER (WHERE origen = 'caficultor') "
                    "FROM cafe.mk_oferta WHERE id_lote = %s", (lote.id,))
        cantidad, total_caficultor = cur.fetchone()
        assert cantidad == len(ofertas) + 2 and total_caficultor == 4_000_000 * 20
        cur.execute("SELECT count(*) FROM cafe.mk_mensaje WHERE id_lote = %s", (lote.id,))
        assert cur.fetchone()[0] == len(ofertas) + 2
    assert mercado.mis_lotes()[0].id == lote.id
    assert len(mercado.mensajes_de(lote.id, ofertas[0].id_comprador)) == 3
    tabla, fuente = mercado.lotes_por_municipio(incluir_demo=True)
    assert fuente == "Supabase" and "76122" in set(tabla["codigo_dane"])


@requiere_bd
def test_restricciones_de_la_base(bd):
    with pytest.raises(Exception, match="check"):
        db_client.insertar_lote({**mercado._registro_lote(_lote()), "tipo_cafe": "Tostado", "id_sesion": "prueba-mercado"})


# ───────────────────────────────── Pantallas ────────────────────────────────
def _caficultor(tmp_path, monkeypatch) -> AppTest:
    monkeypatch.setattr(db_client, "_dsn", lambda: None)
    monkeypatch.setattr(mercado, "DIR_LOCAL", tmp_path)        # AppTest corre en este mismo proceso
    monkeypatch.setattr(telemetria, "RUTA_EVENTOS", tmp_path / "eventos.jsonl")
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=120).run()
    at.radio[0].set_value("Soy caficultor").run()
    at.selectbox[0].set_value(next(o for o in at.selectbox[0].options if o.startswith("Caicedonia"))).run()
    at.button[0].click()
    return at.run()


def _pantalla(archivo: str, ctx, tmp_path, monkeypatch) -> AppTest:
    """Una pantalla sola con el contexto ya cargado (AppTest no navega bien entre páginas con widgets)."""
    monkeypatch.setattr(db_client, "_dsn", lambda: None)
    monkeypatch.setattr(mercado, "DIR_LOCAL", tmp_path)
    monkeypatch.setattr(telemetria, "RUTA_EVENTOS", tmp_path / "eventos.jsonl")
    at = AppTest.from_file(str(APP / archivo), default_timeout=120)
    at.session_state["cofitech_ctx"] = ctx
    return at.run()


def _ctx(rol=Rol.CAFICULTOR) -> ContextoFinca:
    return ContextoFinca(
        rol=rol, finca=Finca(municipio="Caicedonia", departamento="Valle del Cauca", codigo_dane="76122",
                             altitud_msnm=1450, area_ha=3.2, variedad="Castillo"),
        zona=Zona(departamentos=["Valle del Cauca"]),
        mercado=Mercado(precio_fnc_cop_carga=FNC, fecha=date(2026, 9, 1)))


def test_vender_publica_lote_y_muestra_ofertas(tmp_path, monkeypatch):
    at = _pantalla("vistas/vender.py", _ctx(), tmp_path, monkeypatch)
    assert not at.exception
    assert any("Vender mi café" in t.value for t in at.title)
    assert any("Demostración" in m.value for m in at.markdown)
    at.button(key="ofrecer_demo-cafes-altos-valle").click().run()
    assert at.session_state["vender_seccion"] == "Publicar mi lote"
    next(b for b in at.button if b.label == "Publicar lote").click().run()
    assert not at.exception
    assert at.session_state["vender_seccion"] == "Mis lotes y mensajes"
    assert any("Lote publicado" in s.value for s in at.success)
    assert any("Oferta formal" in m.value for m in at.markdown)
    next(b for b in at.button if b.label == "Aceptar").click().run()
    assert not at.exception
    assert any("Oferta aceptada" in m.value for m in at.markdown)
    eventos = (tmp_path / "eventos.jsonl").read_text(encoding="utf-8")
    assert '"herramienta": "Mercado"' in eventos and '"oferta_aceptada"' in eventos


def test_inicio_sin_formulario_repetido_y_con_logo(tmp_path, monkeypatch):
    at = _caficultor(tmp_path, monkeypatch)
    assert any("Hoy en mi finca" in t.value for t in at.title)
    assert not at.sidebar.text_input and not at.sidebar.number_input     # RF01: no vuelve a pedir la finca
    assert any("Precio interno FNC" in m.value for m in at.markdown)
    assert any("compradores" in m.value for m in at.markdown)


def test_consola_de_la_cooperativa(tmp_path, monkeypatch):
    at = _pantalla("vistas/lotes_zona.py", _ctx(Rol.AGRONOMO), tmp_path, monkeypatch)
    assert not at.exception
    assert any("Todavía no hay lotes" in i.value for i in at.info)
    mercado.publicar_lote(_lote())
    at.run()
    assert not at.exception
    assert at.metric[0].value == "1" and at.dataframe
