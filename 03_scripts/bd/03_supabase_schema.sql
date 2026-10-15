-- ════════════════════════════════════════════════════════════════════════════
-- CofiTech · Esquema para Supabase (PostgreSQL 15+)
-- Adaptación de 01_ddl_schema.sql para pegar en el SQL Editor de Supabase.
-- ════════════════════════════════════════════════════════════════════════════
-- Diferencias con 01_ddl_schema.sql:
--   · No borra nada: CREATE ... IF NOT EXISTS en todo. Se puede ejecutar más de
--     una vez sin perder los diagnósticos ya guardados.
--   · Sin CREATE DATABASE ni comandos de psql: Supabase ya trae la base.
--   · Esquema `cafe`: Supabase no lo expone en su API pública (solo `public`),
--     así que la anon key del proyecto no puede leer ni escribir estas tablas.
--     Además se activa RLS sin políticas y se revocan permisos a anon y
--     authenticated, por si algún día se expone el esquema.
--   · La función del trigger fija su search_path (lo pide el Security Advisor).
--   · Los datos semilla se insertan con WHERE NOT EXISTS, no con ON CONFLICT:
--     funcionan aunque las tablas ya existan sin las restricciones UNIQUE
--     (p. ej. creadas con una versión anterior de 01_ddl_schema.sql). En el
--     original, aux_evento_climatico no tenía restricción y cada ejecución
--     duplicaba los eventos.
--   · Si el esquema ya existía, se puede correr este script encima: conserva
--     los datos y agrega lo que falta.
--   · dim_enfermedad incluye SpiderMite, que la CNN también predice.
--   · Nuevas tablas transaccionales (sección final): registro_diagnosticos y
--     registro_eventos_uso, que escribe la app de Streamlit, y las vistas de
--     KPIs telemetria_kpis y vw_kpis_consolidados.
-- ════════════════════════════════════════════════════════════════════════════

CREATE SCHEMA IF NOT EXISTS cafe;

-- ────────────────────────────────────────────────────────────────────────────
-- DIMENSIONES
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cafe.dim_departamento (
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

CREATE TABLE IF NOT EXISTS cafe.dim_municipio (
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
CREATE INDEX IF NOT EXISTS idx_municipio_dpto ON cafe.dim_municipio(id_departamento);
COMMENT ON TABLE cafe.dim_municipio IS
    'Catálogo de municipios colombianos con metadata geográfica y agronómica';
COMMENT ON COLUMN cafe.dim_municipio.zona_cafetera IS
    'Norte | Centro | Sur (clasificación FNC)';
COMMENT ON COLUMN cafe.dim_municipio.soil_ph IS
    'pH del suelo a 0-30cm (SoilGrids)';
COMMENT ON COLUMN cafe.dim_municipio.soil_soc_pct IS
    'Carbono orgánico del suelo % a 0-30cm (SoilGrids)';

CREATE TABLE IF NOT EXISTS cafe.dim_periodo (
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
CREATE INDEX IF NOT EXISTS idx_periodo_anio ON cafe.dim_periodo(anio);
CREATE INDEX IF NOT EXISTS idx_periodo_anio_mes ON cafe.dim_periodo(anio, mes);
COMMENT ON TABLE cafe.dim_periodo IS
    'Calendario maestro 1990-2030 con índice ENSO y bandera de cosecha';

CREATE TABLE IF NOT EXISTS cafe.dim_variedad_cafe (
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

CREATE TABLE IF NOT EXISTS cafe.dim_enfermedad (
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

CREATE TABLE IF NOT EXISTS cafe.fact_produccion (
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
CREATE INDEX IF NOT EXISTS idx_prod_mun_per ON cafe.fact_produccion(id_municipio, id_periodo);
CREATE INDEX IF NOT EXISTS idx_prod_periodo ON cafe.fact_produccion(id_periodo);
CREATE INDEX IF NOT EXISTS idx_prod_fuente  ON cafe.fact_produccion(fuente);
COMMENT ON TABLE cafe.fact_produccion IS
    'Hechos de producción agrícola por municipio y período';

CREATE TABLE IF NOT EXISTS cafe.fact_clima (
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
CREATE INDEX IF NOT EXISTS idx_clima_mun_per ON cafe.fact_clima(id_municipio, id_periodo);
CREATE INDEX IF NOT EXISTS idx_clima_periodo ON cafe.fact_clima(id_periodo);
COMMENT ON TABLE cafe.fact_clima IS
    'Hechos climáticos por municipio y período (IDEAM, CHIRPS, ERA5, Open-Meteo)';

CREATE TABLE IF NOT EXISTS cafe.fact_precio (
    id_precio                       BIGSERIAL PRIMARY KEY,
    id_periodo                      INT NOT NULL UNIQUE
                                        REFERENCES cafe.dim_periodo(id_periodo),
    -- Unidades canónicas: USD/kg para internacionales, COP/kg para FNC
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

CREATE TABLE IF NOT EXISTS cafe.fact_imagen_enfermedad (
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
CREATE INDEX IF NOT EXISTS idx_img_enf ON cafe.fact_imagen_enfermedad(id_enfermedad);
CREATE INDEX IF NOT EXISTS idx_img_ds  ON cafe.fact_imagen_enfermedad(fuente_dataset);
CREATE INDEX IF NOT EXISTS idx_img_split ON cafe.fact_imagen_enfermedad(split_modelo);
COMMENT ON TABLE cafe.fact_imagen_enfermedad IS
    'Catálogo de imágenes consolidadas (RoCoLe + BRACOL + JMuBEN + CALIBRO)';

CREATE TABLE IF NOT EXISTS cafe.fact_prediccion_modelo (
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
CREATE INDEX IF NOT EXISTS idx_pred_modelo ON cafe.fact_prediccion_modelo(nombre_modelo);
CREATE INDEX IF NOT EXISTS idx_pred_var    ON cafe.fact_prediccion_modelo(variable_predicha);
CREATE INDEX IF NOT EXISTS idx_pred_ts     ON cafe.fact_prediccion_modelo(timestamp_pred);
COMMENT ON TABLE cafe.fact_prediccion_modelo IS
    'Bitácora de predicciones de los modelos en producción';

-- ────────────────────────────────────────────────────────────────────────────
-- AUXILIARES
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cafe.aux_evento_climatico (
    id_evento           SERIAL PRIMARY KEY,
    fase                VARCHAR(10) NOT NULL CHECK (fase IN ('Nino','Nina')),
    intensidad          VARCHAR(20),
    fecha_inicio        DATE,
    fecha_fin           DATE,
    oni_pico            NUMERIC(4,2),
    descripcion         TEXT,
    UNIQUE (fase, fecha_inicio)
);
COMMENT ON TABLE cafe.aux_evento_climatico IS
    'Eventos ENSO catalogados (Niño/Niña con fechas y picos)';

CREATE TABLE IF NOT EXISTS cafe.aux_diccionario_columnas (
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
-- VISTA MATERIALIZADA (tablón maestro)
-- ────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS cafe.vw_master_municipal_mensual AS
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
LEFT JOIN cafe.fact_precio pc    ON pc.id_periodo = p.id_periodo;

CREATE INDEX IF NOT EXISTS idx_master_anio_mes_mun
    ON cafe.vw_master_municipal_mensual(anio, mes, cod_mun);

COMMENT ON MATERIALIZED VIEW cafe.vw_master_municipal_mensual IS
    'Tablón maestro: produccion + clima + precio + ENSO a nivel municipio-mes. '
    'Refresh con: REFRESH MATERIALIZED VIEW cafe.vw_master_municipal_mensual;';

-- ────────────────────────────────────────────────────────────────────────────
-- FUNCIONES Y TRIGGERS DE CALIDAD
-- ────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION cafe.calcular_rendimiento()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
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
$$;

CREATE OR REPLACE TRIGGER trg_rendimiento
    BEFORE INSERT OR UPDATE ON cafe.fact_produccion
    FOR EACH ROW EXECUTE FUNCTION cafe.calcular_rendimiento();

-- ────────────────────────────────────────────────────────────────────────────
-- DATOS INICIALES (semilla)
-- ────────────────────────────────────────────────────────────────────────────

INSERT INTO cafe.dim_enfermedad (nombre, nombre_cientifico, color_lesion, sintomas)
SELECT v.nombre, v.nombre_cientifico, v.color_lesion, v.sintomas
  FROM (VALUES
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
('SpiderMite', 'Tetranychus spp.',       'Amarillento',
 'Puntos amarillentos en hojas; ácaros rojizos en el envés'),
('Sano',       NULL,                     NULL,
 'Hoja sin signos de enfermedad')
) AS v (nombre, nombre_cientifico, color_lesion, sintomas)
 WHERE NOT EXISTS (SELECT 1 FROM cafe.dim_enfermedad t WHERE t.nombre IS NOT DISTINCT FROM v.nombre);

INSERT INTO cafe.dim_variedad_cafe (nombre, especie, resistencia_roya, altitud_optima_min, altitud_optima_max)
SELECT v.nombre, v.especie, v.resistencia_roya, v.altitud_optima_min, v.altitud_optima_max
  FROM (VALUES
('Caturra',   'Arábica',  'Baja',  1200, 1700),
('Castillo',  'Arábica',  'Alta',  1200, 1900),
('Colombia',  'Arábica',  'Alta',  1300, 1800),
('Bourbon',   'Arábica',  'Media', 1200, 1700),
('Tabi',      'Arábica',  'Alta',  1300, 1800),
('Geisha',    'Arábica',  'Media', 1500, 1900),
('Cenicafé 1','Arábica',  'Alta',  1200, 1900),
('Tipica',    'Arábica',  'Baja',  1200, 1600),
('Robusta',   'Robusta',   'Alta',  100,  900)
) AS v (nombre, especie, resistencia_roya, altitud_optima_min, altitud_optima_max)
 WHERE NOT EXISTS (SELECT 1 FROM cafe.dim_variedad_cafe t WHERE t.nombre IS NOT DISTINCT FROM v.nombre);

INSERT INTO cafe.dim_departamento (codigo_dane, nombre, region, es_cafetero)
SELECT v.codigo_dane, v.nombre, v.region, v.es_cafetero
  FROM (VALUES
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
) AS v (codigo_dane, nombre, region, es_cafetero)
 WHERE NOT EXISTS (SELECT 1 FROM cafe.dim_departamento t WHERE t.codigo_dane IS NOT DISTINCT FROM v.codigo_dane);

-- Eventos ENSO históricos catalogados
INSERT INTO cafe.aux_evento_climatico (fase, intensidad, fecha_inicio, fecha_fin, oni_pico, descripcion)
SELECT v.fase, v.intensidad, v.fecha_inicio, v.fecha_fin, v.oni_pico, v.descripcion
  FROM (VALUES
('Nino', 'Muy Fuerte', DATE '2015-04-01', DATE '2016-05-01',  2.6, 'El Niño 2015-2016 (super)'),
('Nino', 'Fuerte',     '2023-04-01', '2024-05-01',  2.0, 'El Niño 2023-2024'),
('Nina', 'Moderada',   '2020-08-01', '2023-02-01', -1.4, 'La Niña triple-dip 2020-2023'),
('Nina', 'Fuerte',     '2010-06-01', '2011-04-01', -1.7, 'La Niña 2010-2011'),
('Nino', 'Muy Fuerte', '1997-05-01', '1998-05-01',  2.4, 'El Niño 1997-1998'),
('Nina', 'Fuerte',     '1988-05-01', '1989-05-01', -1.9, 'La Niña 1988-1989')
) AS v (fase, intensidad, fecha_inicio, fecha_fin, oni_pico, descripcion)
 WHERE NOT EXISTS (SELECT 1 FROM cafe.aux_evento_climatico t WHERE t.fase IS NOT DISTINCT FROM v.fase AND t.fecha_inicio IS NOT DISTINCT FROM v.fecha_inicio);

-- ════════════════════════════════════════════════════════════════════════════
-- TABLAS TRANSACCIONALES (las escribe la app de Streamlit)
-- ════════════════════════════════════════════════════════════════════════════

-- Un registro por foto diagnosticada. El id lo genera la app (es el id del
-- diagnóstico en la sesión) para poder actualizar feedback_usuario cuando el
-- caficultor responde «¿El diagnóstico coincide con lo que ves?».
-- Sin llave foránea a dim_municipio / dim_enfermedad a propósito: si la
-- dimensión no está cargada en Supabase, el diagnóstico igual se guarda.
CREATE TABLE IF NOT EXISTS cafe.registro_diagnosticos (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fecha                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    municipio             VARCHAR(80),
    codigo_dane           VARCHAR(5) CHECK (codigo_dane ~ '^[0-9]{5}$'),
    departamento          VARCHAR(60),
    enfermedad_detectada  VARCHAR(30) NOT NULL,
    confianza             NUMERIC(5,4) NOT NULL CHECK (confianza BETWEEN 0 AND 1),
    feedback_usuario      BOOLEAN,
    fecha_feedback        TIMESTAMPTZ,
    modelo                VARCHAR(80),
    altitud_msnm          NUMERIC(6,1),
    rol_origen            VARCHAR(30),
    id_sesion             VARCHAR(32),
    es_demo               BOOLEAN NOT NULL DEFAULT false
);
-- BRIN para la columna temporal (tabla de solo inserción, ordenada por fecha);
-- B-tree para el mapa de calor, que filtra por enfermedad y fecha y agrupa por municipio.
CREATE INDEX IF NOT EXISTS idx_regdiag_fecha_brin ON cafe.registro_diagnosticos USING BRIN (fecha);
CREATE INDEX IF NOT EXISTS idx_regdiag_enf_fecha  ON cafe.registro_diagnosticos (enfermedad_detectada, fecha DESC);
CREATE INDEX IF NOT EXISTS idx_regdiag_mun_fecha  ON cafe.registro_diagnosticos (codigo_dane, fecha DESC);
COMMENT ON TABLE cafe.registro_diagnosticos IS
    'Diagnósticos por foto hechos en la app (CNN) con la validación del caficultor';
COMMENT ON COLUMN cafe.registro_diagnosticos.feedback_usuario IS
    'true = el caficultor confirmó el diagnóstico; false = lo rechazó; NULL = sin responder';
COMMENT ON COLUMN cafe.registro_diagnosticos.es_demo IS
    'Diagnósticos simulados desde el panel de depuración; se excluyen de las alertas';

-- Telemetría de uso (KPIs de la entrega de Data Thinking), incluida la
-- calificación 👍/👎 del asistente RAG (accion = 'feedback_respuesta').
-- No guarda el texto de las preguntas.
CREATE TABLE IF NOT EXISTS cafe.registro_eventos_uso (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id_sesion         VARCHAR(32),
    usuario_rol       VARCHAR(30),
    herramienta       VARCHAR(40) NOT NULL
                          CHECK (herramienta IN ('Visión', 'Predicción Rendimiento',
                                                 'Predicción Precios', 'RAG')),
    accion            VARCHAR(60) NOT NULL,
    metadata          JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_eventos_fecha_brin ON cafe.registro_eventos_uso USING BRIN (fecha);
CREATE INDEX IF NOT EXISTS idx_eventos_accion     ON cafe.registro_eventos_uso (accion, fecha DESC);
COMMENT ON TABLE cafe.registro_eventos_uso IS
    'Eventos de uso de Visión, Predicción y RAG enviados por la app';

-- Calificaciones del asistente RAG, en columnas, para consultarlas en el panel de Supabase.
CREATE OR REPLACE VIEW cafe.vw_feedback_rag AS
SELECT id,
       fecha,
       id_sesion,
       usuario_rol,
       metadata->>'municipio'        AS municipio,
       (metadata->>'util')::boolean  AS util,
       metadata->>'modelo'           AS modelo,
       metadata->>'id_respuesta'     AS id_respuesta
FROM cafe.registro_eventos_uso
WHERE accion = 'feedback_respuesta';

-- ────────────────────────────────────────────────────────────────────────────
-- TELEMETRÍA DE KPIs (vistas sobre registro_eventos_uso)
-- ────────────────────────────────────────────────────────────────────────────
-- telemetria_kpis es una VISTA y no una tabla aparte: cada evento ya queda una
-- sola vez en registro_eventos_uso (la app lo escribe en cada 👍/👎, diagnóstico,
-- simulación o pregunta). Una segunda tabla obligaría a escribir dos veces y
-- las dos copias podrían no coincidir. security_invoker (PostgreSQL 15+): la
-- vista respeta los permisos y el RLS de quien consulta, como pide Supabase.
CREATE OR REPLACE VIEW cafe.telemetria_kpis
WITH (security_invoker = true) AS
SELECT e.id,
       e.fecha,
       e.usuario_rol                                   AS rol,
       e.herramienta                                   AS herramienta_usada,
       e.accion,
       CASE
           WHEN e.accion = 'feedback_respuesta'
                AND jsonb_typeof(e.metadata->'util') = 'boolean'
               THEN (e.metadata->>'util')::boolean
           WHEN e.accion = 'validacion_diagnostico'
                AND jsonb_typeof(e.metadata->'confianza_aceptada') = 'boolean'
               THEN (e.metadata->>'confianza_aceptada')::boolean
       END                                             AS calificacion_utilidad,
       CASE WHEN jsonb_typeof(e.metadata->'confianza') = 'number'
            THEN (e.metadata->>'confianza')::numeric(5,4)
       END                                             AS confianza_modelo,
       e.metadata->>'municipio'                        AS municipio,
       e.metadata->>'codigo_dane'                      AS codigo_dane,
       e.id_sesion
FROM cafe.registro_eventos_uso e;

COMMENT ON VIEW cafe.telemetria_kpis IS
    'Un evento por fila con las columnas de KPI: calificacion_utilidad = 👍/👎 '
    '(RAG: respuesta útil; Visión: diagnóstico aceptado); confianza_modelo = certeza de la CNN.';

-- KPIs consolidados por rol y total (fila con rol = 'Total').
CREATE OR REPLACE VIEW cafe.vw_kpis_consolidados
WITH (security_invoker = true) AS
WITH sesiones_kr3 AS (
    SELECT id_sesion
      FROM cafe.registro_eventos_uso
     GROUP BY id_sesion
    HAVING bool_or(herramienta = 'Visión')
       AND bool_or(herramienta = 'RAG')
       AND bool_or(herramienta IN ('Predicción Rendimiento', 'Predicción Precios'))
)
SELECT COALESCE(k.rol, 'Total')                                                       AS rol,
       COUNT(DISTINCT k.id_sesion)                                                    AS sesiones,
       COUNT(*)                                                                       AS eventos,
       COUNT(k.calificacion_utilidad) FILTER (WHERE k.accion = 'feedback_respuesta')  AS valoraciones_rag,
       ROUND(AVG(k.calificacion_utilidad::int)
             FILTER (WHERE k.accion = 'feedback_respuesta'), 4)                       AS satisfaccion_rag,
       COUNT(k.calificacion_utilidad) FILTER (WHERE k.accion = 'validacion_diagnostico') AS validaciones_vision,
       ROUND(AVG(k.calificacion_utilidad::int)
             FILTER (WHERE k.accion = 'validacion_diagnostico'), 4)                   AS confianza_aceptada,
       ROUND(AVG(k.confianza_modelo)
             FILTER (WHERE k.accion = 'diagnostico_ejecutado'), 4)                    AS confianza_media_modelo,
       COUNT(DISTINCT k.id_sesion)
             FILTER (WHERE k.id_sesion IN (SELECT id_sesion FROM sesiones_kr3))       AS sesiones_3_herramientas,
       MAX(k.fecha)                                                                   AS ultimo_evento
FROM cafe.telemetria_kpis k
GROUP BY GROUPING SETS ((k.rol), ());

COMMENT ON VIEW cafe.vw_kpis_consolidados IS
    'KPIs de la entrega de Data Thinking: satisfacción RAG, confianza aceptada (Visión) y KR3, por rol y en total.';

-- ────────────────────────────────────────────────────────────────────────────
-- SEGURIDAD
-- ────────────────────────────────────────────────────────────────────────────
-- La app se conecta con el usuario postgres (dueño de las tablas): RLS no la
-- afecta. RLS sin políticas deja sin acceso a cualquier otro rol.
ALTER TABLE cafe.registro_diagnosticos ENABLE ROW LEVEL SECURITY;
ALTER TABLE cafe.registro_eventos_uso  ENABLE ROW LEVEL SECURITY;

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

-- ────────────────────────────────────────────────────────────────────────────
-- VERIFICACIÓN
-- ────────────────────────────────────────────────────────────────────────────
SELECT 'OK (v1.4) · esquema cafe con ' ||
       (SELECT count(*) FROM information_schema.tables
         WHERE table_schema = 'cafe' AND table_type = 'BASE TABLE') ||
       ' tablas; registro_diagnosticos con ' ||
       (SELECT count(*) FROM cafe.registro_diagnosticos) || ' filas' AS status;
