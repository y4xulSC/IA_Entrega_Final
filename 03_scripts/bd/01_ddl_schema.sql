-- ════════════════════════════════════════════════════════════════════════════
-- DDL — Sistema IA Café Colombia
-- PostgreSQL 18.3 · esquema cafe
-- Universidad Autónoma de Occidente · IA 2026-1
-- ════════════════════════════════════════════════════════════════════════════
-- Ejecutar:
--   psql -U postgres -h localhost -p 5432 -f 01_ddl_schema.sql
--
-- Pre-requisito: crear la base
--   CREATE DATABASE cafe_ia;
--   \c cafe_ia
-- ════════════════════════════════════════════════════════════════════════════

-- Crear esquema (idempotente)
CREATE SCHEMA IF NOT EXISTS cafe;
SET search_path TO cafe, public;

-- ────────────────────────────────────────────────────────────────────────────
-- DIMENSIONES
-- ────────────────────────────────────────────────────────────────────────────

DROP TABLE IF EXISTS cafe.dim_departamento CASCADE;
CREATE TABLE cafe.dim_departamento (
    id_departamento     SERIAL PRIMARY KEY,
    codigo_dane         VARCHAR(2) NOT NULL UNIQUE,
    nombre              VARCHAR(60) NOT NULL,
    region              VARCHAR(20),
    es_cafetero         BOOLEAN NOT NULL DEFAULT false,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE cafe.dim_departamento IS
    'Catálogo de departamentos colombianos (DIVIPOLA DANE)';
COMMENT ON COLUMN cafe.dim_departamento.codigo_dane IS
    'Código DANE 2 dígitos (ej: 41 = Huila)';
COMMENT ON COLUMN cafe.dim_departamento.region IS
    'Andina | Caribe | Pacífico | Orinoquía | Amazonía | Insular';

DROP TABLE IF EXISTS cafe.dim_municipio CASCADE;
CREATE TABLE cafe.dim_municipio (
    id_municipio        SERIAL PRIMARY KEY,
    codigo_dane         VARCHAR(5) NOT NULL UNIQUE,
    nombre              VARCHAR(80) NOT NULL,
    id_departamento     INT NOT NULL REFERENCES cafe.dim_departamento(id_departamento),
    altitud_msnm        NUMERIC(6,1),
    lat                 NUMERIC(8,5),
    lon                 NUMERIC(8,5),
    zona_cafetera       VARCHAR(20),
    area_total_ha       NUMERIC(12,2),
    soil_ph             NUMERIC(4,2),
    soil_soc_pct        NUMERIC(5,2),
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_municipio_dpto ON cafe.dim_municipio(id_departamento);
COMMENT ON TABLE cafe.dim_municipio IS
    'Catálogo de municipios colombianos con metadata geográfica y agronómica';
COMMENT ON COLUMN cafe.dim_municipio.zona_cafetera IS
    'Norte | Centro | Sur (clasificación FNC)';
COMMENT ON COLUMN cafe.dim_municipio.soil_ph IS
    'pH del suelo a 0-30cm (SoilGrids)';
COMMENT ON COLUMN cafe.dim_municipio.soil_soc_pct IS
    'Carbono orgánico del suelo % a 0-30cm (SoilGrids)';

DROP TABLE IF EXISTS cafe.dim_periodo CASCADE;
CREATE TABLE cafe.dim_periodo (
    id_periodo          SERIAL PRIMARY KEY,
    fecha               DATE NOT NULL UNIQUE,
    anio                INT NOT NULL,
    mes                 INT,
    semestre            INT CHECK (semestre IN (1,2)),
    trimestre           INT CHECK (trimestre BETWEEN 1 AND 4),
    oni                 NUMERIC(4,2),
    fase_enso           VARCHAR(10) CHECK (fase_enso IN ('Nino','Nina','Neutro')),
    es_cosecha          BOOLEAN
);
CREATE INDEX idx_periodo_anio ON cafe.dim_periodo(anio);
CREATE INDEX idx_periodo_anio_mes ON cafe.dim_periodo(anio, mes);
COMMENT ON TABLE cafe.dim_periodo IS
    'Calendario maestro 1990-2030 con índice ENSO y bandera de cosecha';

DROP TABLE IF EXISTS cafe.dim_variedad_cafe CASCADE;
CREATE TABLE cafe.dim_variedad_cafe (
    id_variedad         SERIAL PRIMARY KEY,
    nombre              VARCHAR(50) NOT NULL UNIQUE,
    especie             VARCHAR(20) NOT NULL,
    resistencia_roya    VARCHAR(15),
    altitud_optima_min  INT,
    altitud_optima_max  INT,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE cafe.dim_variedad_cafe IS
    'Variedades de café cultivadas en Colombia (Caturra, Castillo, Colombia, etc.)';

DROP TABLE IF EXISTS cafe.dim_enfermedad CASCADE;
CREATE TABLE cafe.dim_enfermedad (
    id_enfermedad       SERIAL PRIMARY KEY,
    nombre              VARCHAR(50) NOT NULL UNIQUE,
    nombre_cientifico   VARCHAR(80),
    sintomas            TEXT,
    color_lesion        VARCHAR(30),
    severidad_tipica    VARCHAR(20)
);
COMMENT ON TABLE cafe.dim_enfermedad IS
    'Catálogo de enfermedades del café detectables por la CNN';

-- ────────────────────────────────────────────────────────────────────────────
-- HECHOS
-- ────────────────────────────────────────────────────────────────────────────

DROP TABLE IF EXISTS cafe.fact_produccion CASCADE;
CREATE TABLE cafe.fact_produccion (
    id_produccion       BIGSERIAL PRIMARY KEY,
    id_municipio        INT NOT NULL REFERENCES cafe.dim_municipio(id_municipio),
    id_periodo          INT NOT NULL REFERENCES cafe.dim_periodo(id_periodo),
    id_variedad         INT REFERENCES cafe.dim_variedad_cafe(id_variedad),
    area_sembrada_ha    NUMERIC(12,2) CHECK (area_sembrada_ha >= 0),
    area_cosechada_ha   NUMERIC(12,2) CHECK (area_cosechada_ha >= 0),
    produccion_ton      NUMERIC(14,2) CHECK (produccion_ton >= 0),
    rendimiento_ton_ha  NUMERIC(8,4)  CHECK (rendimiento_ton_ha >= 0),
    estado_fisico       VARCHAR(30),
    ciclo_cultivo       VARCHAR(20),
    fuente              VARCHAR(50) NOT NULL DEFAULT 'EVA-MADR',
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_prod_mun_per ON cafe.fact_produccion(id_municipio, id_periodo);
CREATE INDEX idx_prod_periodo ON cafe.fact_produccion(id_periodo);
CREATE INDEX idx_prod_fuente  ON cafe.fact_produccion(fuente);
COMMENT ON TABLE cafe.fact_produccion IS
    'Hechos de producción agrícola por municipio y período';

DROP TABLE IF EXISTS cafe.fact_clima CASCADE;
CREATE TABLE cafe.fact_clima (
    id_clima            BIGSERIAL PRIMARY KEY,
    id_municipio        INT NOT NULL REFERENCES cafe.dim_municipio(id_municipio),
    id_periodo          INT NOT NULL REFERENCES cafe.dim_periodo(id_periodo),
    temp_media_c        NUMERIC(5,2) CHECK (temp_media_c BETWEEN -5 AND 50),
    temp_min_c          NUMERIC(5,2),
    temp_max_c          NUMERIC(5,2),
    precipitacion_mm    NUMERIC(8,2) CHECK (precipitacion_mm >= 0),
    precipitacion_chirps_mm NUMERIC(8,2),
    et0_mm              NUMERIC(8,2),
    humedad_rel_pct     NUMERIC(5,2),
    viento_max_kmh      NUMERIC(6,2),
    radiacion_mj_m2     NUMERIC(7,2),
    ndvi                NUMERIC(5,3),
    fuente              VARCHAR(20) NOT NULL DEFAULT 'OpenMeteo',
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(id_municipio, id_periodo, fuente)
);
CREATE INDEX idx_clima_mun_per ON cafe.fact_clima(id_municipio, id_periodo);
CREATE INDEX idx_clima_periodo ON cafe.fact_clima(id_periodo);
COMMENT ON TABLE cafe.fact_clima IS
    'Hechos climáticos por municipio y período (IDEAM, CHIRPS, ERA5, Open-Meteo)';

DROP TABLE IF EXISTS cafe.fact_precio CASCADE;
CREATE TABLE cafe.fact_precio (
    id_precio                       BIGSERIAL PRIMARY KEY,
    id_periodo                      INT NOT NULL UNIQUE
                                        REFERENCES cafe.dim_periodo(id_periodo),
    -- Unidades canonicas: USD/kg para internacionales, COP/kg para FNC
    -- (provienen del ETL en 01_datos/procesados/precios_validado.csv)
    precio_arabica_brasil_usd_kg    NUMERIC(10,4),
    precio_robusta_usd_kg           NUMERIC(10,4),
    precio_arabica_wb_usd_kg        NUMERIC(10,4),
    precio_robusta_wb_usd_kg        NUMERIC(10,4),
    precio_fnc_cop_kg               NUMERIC(12,2),
    precio_arabica_brasil_cop_kg    NUMERIC(14,2),
    fnc_cosecha_60kg                NUMERIC(12,2),
    fnc_export_60kg                 NUMERIC(12,2),
    trm_cop_usd                     NUMERIC(10,2),
    ipc_general                     NUMERIC(10,4),
    surge_flag                      BOOLEAN DEFAULT false,
    creado_en                       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE cafe.fact_precio IS
    'Precios mensuales del café — fuentes nacionales e internacionales';

DROP TABLE IF EXISTS cafe.fact_imagen_enfermedad CASCADE;
CREATE TABLE cafe.fact_imagen_enfermedad (
    id_imagen           BIGSERIAL PRIMARY KEY,
    id_enfermedad       INT REFERENCES cafe.dim_enfermedad(id_enfermedad),
    ruta_archivo        TEXT NOT NULL,
    nombre_archivo      VARCHAR(200) NOT NULL,
    parte_planta        VARCHAR(20) CHECK (parte_planta IN ('hoja','fruto','tallo','rama','flor')),
    severidad_pct       NUMERIC(5,2) CHECK (severidad_pct BETWEEN 0 AND 100),
    nivel_severidad     VARCHAR(15) CHECK (nivel_severidad IN ('Sin','Bajo','Medio','Alto')),
    fuente_dataset      VARCHAR(20) NOT NULL,
    resolucion_px       VARCHAR(15),
    variedad_cafe       VARCHAR(50),
    split_modelo        VARCHAR(10) CHECK (split_modelo IN ('train','val','test')),
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_img_enf ON cafe.fact_imagen_enfermedad(id_enfermedad);
CREATE INDEX idx_img_ds  ON cafe.fact_imagen_enfermedad(fuente_dataset);
CREATE INDEX idx_img_split ON cafe.fact_imagen_enfermedad(split_modelo);
COMMENT ON TABLE cafe.fact_imagen_enfermedad IS
    'Catálogo de imágenes consolidadas (RoCoLe + BRACOL + JMuBEN + CALIBRO)';

DROP TABLE IF EXISTS cafe.fact_prediccion_modelo CASCADE;
CREATE TABLE cafe.fact_prediccion_modelo (
    id_prediccion       BIGSERIAL PRIMARY KEY,
    nombre_modelo       VARCHAR(80) NOT NULL,
    version             VARCHAR(20),
    id_municipio        INT REFERENCES cafe.dim_municipio(id_municipio),
    id_periodo          INT REFERENCES cafe.dim_periodo(id_periodo),
    variable_predicha   VARCHAR(30) NOT NULL,
    valor_predicho      NUMERIC(14,4) NOT NULL,
    valor_real          NUMERIC(14,4),
    confianza_lo        NUMERIC(14,4),
    confianza_hi        NUMERIC(14,4),
    timestamp_pred      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata_json       JSONB,
    notas               TEXT
);
CREATE INDEX idx_pred_modelo ON cafe.fact_prediccion_modelo(nombre_modelo);
CREATE INDEX idx_pred_var    ON cafe.fact_prediccion_modelo(variable_predicha);
CREATE INDEX idx_pred_ts     ON cafe.fact_prediccion_modelo(timestamp_pred);
COMMENT ON TABLE cafe.fact_prediccion_modelo IS
    'Bitácora de predicciones de los modelos en producción';

-- ────────────────────────────────────────────────────────────────────────────
-- AUXILIARES
-- ────────────────────────────────────────────────────────────────────────────

DROP TABLE IF EXISTS cafe.aux_evento_climatico CASCADE;
CREATE TABLE cafe.aux_evento_climatico (
    id_evento           SERIAL PRIMARY KEY,
    fase                VARCHAR(10) NOT NULL CHECK (fase IN ('Nino','Nina')),
    intensidad          VARCHAR(20),
    fecha_inicio        DATE,
    fecha_fin           DATE,
    oni_pico            NUMERIC(4,2),
    descripcion         TEXT
);
COMMENT ON TABLE cafe.aux_evento_climatico IS
    'Eventos ENSO catalogados (Niño/Niña con fechas y picos)';

DROP TABLE IF EXISTS cafe.aux_diccionario_columnas CASCADE;
CREATE TABLE cafe.aux_diccionario_columnas (
    id                  SERIAL PRIMARY KEY,
    tabla               VARCHAR(80) NOT NULL,
    columna             VARCHAR(80) NOT NULL,
    tipo_dato           VARCHAR(40),
    descripcion         TEXT,
    ejemplos            TEXT,
    es_pii              BOOLEAN DEFAULT false,
    UNIQUE(tabla, columna)
);
COMMENT ON TABLE cafe.aux_diccionario_columnas IS
    'Metadata viva auto-documentada del diccionario de datos';

-- ────────────────────────────────────────────────────────────────────────────
-- VISTAS MATERIALIZADAS
-- ────────────────────────────────────────────────────────────────────────────

DROP MATERIALIZED VIEW IF EXISTS cafe.vw_master_municipal_mensual;
CREATE MATERIALIZED VIEW cafe.vw_master_municipal_mensual AS
SELECT
    m.codigo_dane               AS cod_mun,
    m.nombre                    AS municipio,
    d.nombre                    AS departamento,
    m.altitud_msnm,
    m.zona_cafetera,
    m.soil_ph, m.soil_soc_pct,
    p.fecha, p.anio, p.mes, p.semestre,
    p.oni, p.fase_enso, p.es_cosecha,
    pr.area_sembrada_ha, pr.area_cosechada_ha,
    pr.produccion_ton, pr.rendimiento_ton_ha,
    pr.estado_fisico,
    cl.temp_media_c, cl.temp_min_c, cl.temp_max_c,
    cl.precipitacion_mm, cl.precipitacion_chirps_mm, cl.et0_mm,
    cl.viento_max_kmh, cl.radiacion_mj_m2, cl.ndvi,
    pc.precio_fnc_cop_kg, pc.precio_arabica_brasil_usd_kg,
    pc.precio_robusta_usd_kg, pc.precio_arabica_wb_usd_kg,
    pc.precio_arabica_brasil_cop_kg,
    pc.fnc_cosecha_60kg, pc.fnc_export_60kg, pc.trm_cop_usd, pc.surge_flag
FROM cafe.dim_municipio m
JOIN cafe.dim_departamento d USING (id_departamento)
JOIN cafe.dim_periodo p ON true
LEFT JOIN cafe.fact_produccion pr ON pr.id_municipio = m.id_municipio AND pr.id_periodo = p.id_periodo
LEFT JOIN cafe.fact_clima cl     ON cl.id_municipio = m.id_municipio AND cl.id_periodo = p.id_periodo
LEFT JOIN cafe.fact_precio pc    ON pc.id_periodo = p.id_periodo
WHERE m.zona_cafetera IS NOT NULL OR true;  -- todos los municipios cargados

CREATE INDEX idx_master_anio_mes_mun
    ON cafe.vw_master_municipal_mensual(anio, mes, cod_mun);

COMMENT ON MATERIALIZED VIEW cafe.vw_master_municipal_mensual IS
    'Tablón maestro: produccion + clima + precio + ENSO a nivel municipio-mes. '
    'Refresh con: REFRESH MATERIALIZED VIEW cafe.vw_master_municipal_mensual;';

-- ────────────────────────────────────────────────────────────────────────────
-- FUNCIONES Y TRIGGERS DE CALIDAD
-- ────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION cafe.calcular_rendimiento()
RETURNS TRIGGER AS $$
BEGIN
    -- Auto-calcular rendimiento si producción y área están y rendimiento es null
    IF NEW.rendimiento_ton_ha IS NULL
       AND NEW.produccion_ton IS NOT NULL
       AND NEW.area_cosechada_ha IS NOT NULL
       AND NEW.area_cosechada_ha > 0 THEN
        NEW.rendimiento_ton_ha := NEW.produccion_ton / NEW.area_cosechada_ha;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_rendimiento ON cafe.fact_produccion;
CREATE TRIGGER trg_rendimiento
    BEFORE INSERT OR UPDATE ON cafe.fact_produccion
    FOR EACH ROW EXECUTE FUNCTION cafe.calcular_rendimiento();

-- ────────────────────────────────────────────────────────────────────────────
-- DATOS INICIALES (semilla)
-- ────────────────────────────────────────────────────────────────────────────

INSERT INTO cafe.dim_enfermedad
    (nombre, nombre_cientifico, color_lesion, sintomas) VALUES
('Roya',       'Hemileia vastatrix',     'Amarillo-naranja',
 'Manchas amarillentas en envés de hojas, polvillo naranja'),
('Gotera',     'Mycena citricolor',      'Marrón claro',
 'Manchas circulares con halo amarillo en hojas y frutos'),
('Cercospora', 'Cercospora coffeicola',  'Marrón-gris',
 'Manchas circulares marrones en hojas con borde amarillo'),
('Phoma',      'Phoma costarricensis',   'Negruzco',
 'Necrosis en bordes y puntas de hojas jóvenes'),
('Miner',      'Leucoptera coffeella',   'Marrón',
 'Galerías de minador en hojas'),
('Sano',       NULL,                     NULL,
 'Hoja sin signos de enfermedad')
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO cafe.dim_variedad_cafe
    (nombre, especie, resistencia_roya, altitud_optima_min, altitud_optima_max) VALUES
('Caturra',   'Arábica',  'Baja',  1200, 1700),
('Castillo',  'Arábica',  'Alta',  1200, 1900),
('Colombia',  'Arábica',  'Alta',  1300, 1800),
('Bourbon',   'Arábica',  'Media', 1200, 1700),
('Tabi',      'Arábica',  'Alta',  1300, 1800),
('Geisha',    'Arábica',  'Media', 1500, 1900),
('Cenicafé 1','Arábica',  'Alta',  1200, 1900),
('Tipica',    'Arábica',  'Baja',  1200, 1600),
('Robusta',   'Robusta',   'Alta',  100,  900)
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO cafe.dim_departamento
    (codigo_dane, nombre, region, es_cafetero) VALUES
('05', 'Antioquia',     'Andina',     true),
('41', 'Huila',         'Andina',     true),
('52', 'Nariño',        'Andina',     true),
('17', 'Caldas',        'Andina',     true),
('66', 'Risaralda',     'Andina',     true),
('63', 'Quindio',       'Andina',     true),
('73', 'Tolima',        'Andina',     true),
('19', 'Cauca',         'Andina',     true),
('76', 'Valle del Cauca','Andina',    true),
('68', 'Santander',     'Andina',     true),
('54', 'Norte de Santander','Andina', true),
('15', 'Boyaca',        'Andina',     true),
('25', 'Cundinamarca',  'Andina',     true),
('18', 'Caqueta',       'Amazonía',   true),
('44', 'Guajira',       'Caribe',     true),
('47', 'Magdalena',     'Caribe',     true),
('20', 'Cesar',         'Caribe',     true),
('70', 'Sucre',         'Caribe',     false),
('11', 'Bogota DC',     'Andina',     false),
('08', 'Atlantico',     'Caribe',     false),
('13', 'Bolivar',       'Caribe',     false),
('23', 'Cordoba',       'Caribe',     false),
('27', 'Choco',         'Pacífico',   false),
('50', 'Meta',          'Orinoquía',  false),
('85', 'Casanare',      'Orinoquía',  false),
('94', 'Guainia',       'Amazonía',   false),
('95', 'Guaviare',      'Amazonía',   false),
('86', 'Putumayo',      'Amazonía',   false),
('91', 'Amazonas',      'Amazonía',   false),
('97', 'Vaupes',        'Amazonía',   false),
('99', 'Vichada',       'Orinoquía',  false),
('81', 'Arauca',        'Orinoquía',  false),
('88', 'San Andres',    'Insular',    false)
ON CONFLICT (codigo_dane) DO NOTHING;

-- Eventos ENSO históricos catalogados
INSERT INTO cafe.aux_evento_climatico
    (fase, intensidad, fecha_inicio, fecha_fin, oni_pico, descripcion) VALUES
('Nino', 'Muy Fuerte', '2015-04-01', '2016-05-01',  2.6, 'El Niño 2015-2016 (super)'),
('Nino', 'Fuerte',     '2023-04-01', '2024-05-01',  2.0, 'El Niño 2023-2024'),
('Nina', 'Moderada',   '2020-08-01', '2023-02-01', -1.4, 'La Niña triple-dip 2020-2023'),
('Nina', 'Fuerte',     '2010-06-01', '2011-04-01', -1.7, 'La Niña 2010-2011'),
('Nino', 'Muy Fuerte', '1997-05-01', '1998-05-01',  2.4, 'El Niño 1997-1998'),
('Nina', 'Fuerte',     '1988-05-01', '1989-05-01', -1.9, 'La Niña 1988-1989')
ON CONFLICT DO NOTHING;

-- ────────────────────────────────────────────────────────────────────────────
-- VERIFICACIÓN
-- ────────────────────────────────────────────────────────────────────────────
SELECT 'OK · Schema cafe creado con ' ||
       (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'cafe') ||
       ' tablas' AS status;
