-- ════════════════════════════════════════════════════════════════════════════
-- CofiTech · Revisión de diagnósticos (migración v1.6 → v1.7, nov-2026)
-- Para bases ya creadas con 03_supabase_schema.sql v1.6 (o anterior + 06/07).
-- Las bases nuevas no la necesitan: 03_supabase_schema.sql v1.7 ya la incluye.
-- Idempotente y sin borrar datos. PostgreSQL 15+.
-- ════════════════════════════════════════════════════════════════════════════
-- Qué agrega
--   · registro_diagnosticos.probabilidades (JSONB): las 7 probabilidades de la CNN.
--   · registro_fotos_donadas: fotos que el usuario dona de forma voluntaria,
--     reducidas y sin EXIF, con vencimiento (borrar_despues) y campos para la
--     revisión del experto (clase_revisada, notas_revision).
-- ════════════════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────────────────
-- v1.7 · REVISIÓN DE DIAGNÓSTICOS: probabilidades y fotos donadas
-- ────────────────────────────────────────────────────────────────────────────
-- 1) Las 7 probabilidades de la CNN en cada diagnóstico: sin datos personales,
--    permiten ver los casos dudosos (certeza baja o dos clases parecidas).
ALTER TABLE cafe.registro_diagnosticos ADD COLUMN IF NOT EXISTS probabilidades JSONB;
COMMENT ON COLUMN cafe.registro_diagnosticos.probabilidades IS
    'Probabilidad de cada clase de la CNN, p. ej. {"Roya": 0.81, "Sano": 0.12, ...}. NULL antes de la v1.7.';

-- 2) Fotos que el usuario DONA de forma voluntaria (casilla por foto, desmarcada
--    por defecto) para revisar el diagnóstico y mejorar el modelo. Sin donación
--    la foto no se guarda. Se guardan reducidas (máx. 1024 px) y sin metadatos
--    EXIF (GPS, cámara). Se borran solas al vencer borrar_despues.
--    Sin llave foránea a registro_diagnosticos a propósito: si la base no
--    respondió al diagnosticar, ese registro solo quedó en el archivo local.
CREATE TABLE IF NOT EXISTS cafe.registro_fotos_donadas (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo             VARCHAR(9)  NOT NULL UNIQUE,       -- se le muestra al usuario para pedir el borrado
    fecha              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id_diagnostico     UUID,
    id_sesion          VARCHAR(32),
    imagen             BYTEA       NOT NULL,
    mime               VARCHAR(20) NOT NULL DEFAULT 'image/jpeg',
    ancho_px           INT,
    alto_px            INT,
    bytes              INT,
    clase_modelo       VARCHAR(30) NOT NULL,
    confianza_modelo   NUMERIC(5,4) CHECK (confianza_modelo BETWEEN 0 AND 1),
    probabilidades     JSONB,
    modelo             VARCHAR(80),
    municipio          VARCHAR(80),
    departamento       VARCHAR(60),
    codigo_dane        VARCHAR(5) CHECK (codigo_dane ~ '^[0-9]{5}$'),
    version_aviso      VARCHAR(20) NOT NULL,              -- aviso de privacidad vigente al donar
    borrar_despues     TIMESTAMPTZ NOT NULL,
    clase_revisada     VARCHAR(30) CHECK (clase_revisada IN
                       ('Cercospora','Gotera','Miner','Phoma','Roya','Sano','SpiderMite','Indeterminada')),
    notas_revision     VARCHAR(500),
    revisada_en        TIMESTAMPTZ,
    es_demo            BOOLEAN NOT NULL DEFAULT false,
    CHECK (bytes IS NULL OR bytes <= 1500000)
);
CREATE INDEX IF NOT EXISTS idx_fotos_pendientes ON cafe.registro_fotos_donadas (fecha DESC) WHERE clase_revisada IS NULL;
CREATE INDEX IF NOT EXISTS idx_fotos_vencen     ON cafe.registro_fotos_donadas (borrar_despues);
CREATE INDEX IF NOT EXISTS idx_fotos_diag       ON cafe.registro_fotos_donadas (id_diagnostico);
COMMENT ON TABLE cafe.registro_fotos_donadas IS
    'Fotos donadas voluntariamente (Ley 1581: autorización por foto). Revisión experta del diagnóstico de la CNN.';

ALTER TABLE cafe.registro_fotos_donadas ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA cafe FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA cafe FROM authenticated;
    END IF;
END
$$;

SELECT 'OK (v1.7) · revisión de diagnósticos lista · ' ||
       (SELECT count(*) FROM cafe.registro_fotos_donadas) || ' fotos donadas' AS status;
