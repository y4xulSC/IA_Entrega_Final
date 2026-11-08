-- ════════════════════════════════════════════════════════════════════════════
-- CofiTech · Venta directa (pasos 5–7 del MockUp ganador: «Vender»)
-- Migración para bases que ya tienen el esquema v1.4. Las bases nuevas no la
-- necesitan: 03_supabase_schema.sql (v1.5) ya la incluye.
-- Idempotente: se puede ejecutar varias veces sin perder datos.
-- ════════════════════════════════════════════════════════════════════════════
-- Tablas
--   mk_comprador  compradores (cooperativas, tostadores, exportadores)
--   mk_lote       lotes de café que publican los caficultores
--   mk_oferta     ofertas formales y contraofertas sobre un lote
--   mk_mensaje    chat entre caficultor y comprador, por lote
--   vw_lotes_zona oferta de café por municipio, para la consola de la cooperativa
--
-- Privacidad (Ley 1581 de 2012): no hay nombres, teléfonos ni documentos del
-- caficultor. El lote se liga a un id_sesion aleatorio, igual que los
-- diagnósticos. Los compradores sembrados aquí son FICTICIOS (es_demo = true)
-- y sus respuestas en el chat las genera la app (es_simulado = true).
-- ════════════════════════════════════════════════════════════════════════════

CREATE SCHEMA IF NOT EXISTS cafe;

CREATE TABLE IF NOT EXISTS cafe.mk_comprador (
    id                VARCHAR(40) PRIMARY KEY,
    nombre            VARCHAR(80)  NOT NULL,
    tipo              VARCHAR(20)  NOT NULL CHECK (tipo IN ('Cooperativa', 'Tostador', 'Exportador')),
    municipio         VARCHAR(80),
    departamento      VARCHAR(60),
    codigo_dane       VARCHAR(5)   CHECK (codigo_dane ~ '^[0-9]{5}$'),
    busca             VARCHAR(120),
    prima_cop_carga   INTEGER      NOT NULL DEFAULT 0 CHECK (prima_cop_carga BETWEEN 0 AND 2000000),
    puntaje_min       SMALLINT     CHECK (puntaje_min BETWEEN 60 AND 100),
    cargas_min        NUMERIC(7,1) NOT NULL DEFAULT 1 CHECK (cargas_min > 0),
    activo            BOOLEAN      NOT NULL DEFAULT true,
    es_demo           BOOLEAN      NOT NULL DEFAULT true,
    creado            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE cafe.mk_comprador IS
    'Compradores de café para la venta directa; es_demo = true marca los ficticios del prototipo';
COMMENT ON COLUMN cafe.mk_comprador.prima_cop_carga IS
    'Prima sobre el precio interno FNC que ofrece el comprador (COP por carga de 125 kg)';

CREATE TABLE IF NOT EXISTS cafe.mk_lote (
    id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fecha                      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    id_sesion                  VARCHAR(32),
    municipio                  VARCHAR(80),
    departamento               VARCHAR(60),
    codigo_dane                VARCHAR(5)   CHECK (codigo_dane ~ '^[0-9]{5}$'),
    altitud_msnm               NUMERIC(6,1),
    tipo_cafe                  VARCHAR(20)  NOT NULL CHECK (tipo_cafe IN ('Pergamino seco', 'Cereza', 'Especial')),
    variedad                   VARCHAR(40),
    cantidad_cargas            NUMERIC(7,1) NOT NULL CHECK (cantidad_cargas > 0 AND cantidad_cargas <= 10000),
    disponible_desde           DATE         NOT NULL DEFAULT CURRENT_DATE,
    precio_esperado_cop_carga  INTEGER      NOT NULL CHECK (precio_esperado_cop_carga > 0),
    precio_fnc_ref_cop_carga   INTEGER      CHECK (precio_fnc_ref_cop_carga > 0),
    puntaje_sca                SMALLINT     CHECK (puntaje_sca BETWEEN 60 AND 100),
    ultimo_diagnostico         VARCHAR(30),
    riesgo_fitosanitario       VARCHAR(10),
    canales                    TEXT[]       NOT NULL DEFAULT ARRAY['chat']::TEXT[],
    estado                     VARCHAR(12)  NOT NULL DEFAULT 'publicado'
                                   CHECK (estado IN ('publicado', 'negociando', 'vendido', 'retirado')),
    es_demo                    BOOLEAN      NOT NULL DEFAULT false,
    actualizado                TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mklote_mun_estado ON cafe.mk_lote (codigo_dane, estado);
CREATE INDEX IF NOT EXISTS idx_mklote_sesion     ON cafe.mk_lote (id_sesion, fecha DESC);
COMMENT ON TABLE cafe.mk_lote IS
    'Lotes de café publicados por los caficultores (sin datos personales: id_sesion aleatorio)';

CREATE TABLE IF NOT EXISTS cafe.mk_oferta (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_lote           UUID         NOT NULL REFERENCES cafe.mk_lote (id) ON DELETE CASCADE,
    id_comprador      VARCHAR(40)  NOT NULL REFERENCES cafe.mk_comprador (id),
    fecha             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    origen            VARCHAR(12)  NOT NULL CHECK (origen IN ('comprador', 'caficultor')),
    precio_cop_carga  INTEGER      NOT NULL CHECK (precio_cop_carga > 0),
    cantidad_cargas   NUMERIC(7,1) NOT NULL CHECK (cantidad_cargas > 0),
    total_cop         NUMERIC(14,0) GENERATED ALWAYS AS (precio_cop_carga * cantidad_cargas) STORED,
    recoge_en_finca   BOOLEAN      NOT NULL DEFAULT false,
    estado            VARCHAR(16)  NOT NULL DEFAULT 'pendiente'
                          CHECK (estado IN ('pendiente', 'aceptada', 'rechazada', 'contraofertada')),
    es_simulada       BOOLEAN      NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_mkoferta_lote ON cafe.mk_oferta (id_lote, fecha DESC);
COMMENT ON COLUMN cafe.mk_oferta.es_simulada IS
    'true = la generó la app en nombre de un comprador de demostración';

CREATE TABLE IF NOT EXISTS cafe.mk_mensaje (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_lote           UUID         NOT NULL REFERENCES cafe.mk_lote (id) ON DELETE CASCADE,
    id_comprador      VARCHAR(40)  NOT NULL REFERENCES cafe.mk_comprador (id),
    fecha             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    autor             VARCHAR(12)  NOT NULL CHECK (autor IN ('caficultor', 'comprador', 'sistema')),
    texto             VARCHAR(500) NOT NULL,
    es_simulado       BOOLEAN      NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_mkmensaje_conv ON cafe.mk_mensaje (id_lote, id_comprador, fecha);

-- Compradores de demostración (ficticios). Se insertan solo si no existen.
INSERT INTO cafe.mk_comprador (id, nombre, tipo, municipio, departamento, codigo_dane, busca,
                               prima_cop_carga, puntaje_min, cargas_min, es_demo)
SELECT v.id, v.nombre, v.tipo, v.municipio, v.departamento, v.codigo_dane, v.busca,
       v.prima, v.puntaje_min, v.cargas_min, true
FROM (VALUES
    ('demo-tostadora-montana', 'Tostadora La Montaña (demo)', 'Tostador',    'Cali',     'Valle del Cauca', '76001',
     'Café especial de 84 puntos o más',            180000, 84::SMALLINT,   1.0),
    ('demo-cafes-altos-valle', 'Cafés Altos del Valle (demo)', 'Cooperativa', 'Sevilla',  'Valle del Cauca', '76736',
     'Pergamino seco · precio FNC más bono',          40000, NULL::SMALLINT, 1.0),
    ('demo-exportadora-andina', 'Exportadora Andina (demo)',   'Exportador',  'Armenia',  'Quindío',         '63001',
     'Lotes de 50 cargas o más, 82 puntos o más',      90000, 82::SMALLINT,  50.0),
    ('demo-cooperativa-suroeste', 'Cooperativa del Suroeste (demo)', 'Cooperativa', 'Andes', 'Antioquia',    '05034',
     'Pergamino seco · precio FNC más bono',          35000, NULL::SMALLINT, 1.0),
    ('demo-tostadora-sur-huila', 'Tostadora Sur del Huila (demo)', 'Tostador',  'Pitalito', 'Huila',           '41551',
     'Café especial de 85 puntos o más',             200000, 85::SMALLINT,   1.0)
) AS v(id, nombre, tipo, municipio, departamento, codigo_dane, busca, prima, puntaje_min, cargas_min)
WHERE NOT EXISTS (SELECT 1 FROM cafe.mk_comprador c WHERE c.id = v.id);

-- Oferta de café por municipio (lotes publicados o en negociación).
CREATE OR REPLACE VIEW cafe.vw_lotes_zona WITH (security_invoker = true) AS
SELECT l.codigo_dane,
       MAX(l.municipio)                                         AS municipio,
       MAX(l.departamento)                                      AS departamento,
       COUNT(*)                                                 AS lotes,
       SUM(l.cantidad_cargas)                                   AS cargas,
       ROUND(AVG(l.precio_esperado_cop_carga))                  AS precio_esperado_medio,
       ROUND(AVG(l.precio_fnc_ref_cop_carga))                   AS precio_fnc_medio,
       ROUND(100.0 * (AVG(l.precio_esperado_cop_carga) / NULLIF(AVG(l.precio_fnc_ref_cop_carga), 0) - 1), 1)
                                                                AS pct_sobre_fnc,
       COUNT(*) FILTER (WHERE l.tipo_cafe = 'Especial')         AS lotes_especiales,
       MAX(l.fecha)                                             AS ultimo_lote,
       bool_and(l.es_demo)                                      AS solo_demo
FROM cafe.mk_lote l
WHERE l.estado IN ('publicado', 'negociando')
GROUP BY l.codigo_dane;
COMMENT ON VIEW cafe.vw_lotes_zona IS
    'Oferta de café publicada por municipio, para la consola de la cooperativa (RF09)';

-- Telemetría: la herramienta «Mercado» registra el uso de la venta directa.
DO $$
DECLARE
    nombre_check TEXT;
BEGIN
    IF to_regclass('cafe.registro_eventos_uso') IS NULL THEN
        RETURN;
    END IF;
    SELECT conname INTO nombre_check
      FROM pg_constraint
     WHERE conrelid = 'cafe.registro_eventos_uso'::regclass
       AND contype = 'c'
       AND pg_get_constraintdef(oid) LIKE '%herramienta%';
    IF nombre_check IS NOT NULL THEN
        EXECUTE format('ALTER TABLE cafe.registro_eventos_uso DROP CONSTRAINT %I', nombre_check);
    END IF;
    ALTER TABLE cafe.registro_eventos_uso
        ADD CONSTRAINT registro_eventos_uso_herramienta_check
        CHECK (herramienta IN ('Visión', 'Predicción Rendimiento', 'Predicción Precios', 'RAG', 'Mercado'));
END
$$;

-- Seguridad: igual que el resto del esquema (RLS sin políticas, sin acceso para anon/authenticated).
ALTER TABLE cafe.mk_comprador ENABLE ROW LEVEL SECURITY;
ALTER TABLE cafe.mk_lote      ENABLE ROW LEVEL SECURITY;
ALTER TABLE cafe.mk_oferta    ENABLE ROW LEVEL SECURITY;
ALTER TABLE cafe.mk_mensaje   ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA cafe FROM anon;
        REVOKE USAGE ON SCHEMA cafe FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA cafe FROM authenticated;
        REVOKE USAGE ON SCHEMA cafe FROM authenticated;
    END IF;
END
$$;

SELECT 'OK (venta directa) · ' ||
       (SELECT count(*) FROM cafe.mk_comprador) || ' compradores · ' ||
       (SELECT count(*) FROM cafe.mk_lote) || ' lotes' AS status;
