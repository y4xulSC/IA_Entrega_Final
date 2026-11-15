-- ════════════════════════════════════════════════════════════════════════════
-- CofiTech · KPI «Interés en la venta directa» (migración v1.5 → v1.6)
-- Para bases que ya tienen 03_supabase_schema.sql v1.5 (o 05_marketplace.sql).
-- Las bases nuevas no la necesitan: 03_supabase_schema.sql v1.6 ya la incluye.
-- Idempotente y sin tocar datos: solo reemplaza vistas. PostgreSQL 15+.
-- ════════════════════════════════════════════════════════════════════════════
-- Qué agrega
--   · telemetria_kpis: el voto 👍/👎 de «¿Te gustaría vender tu café desde
--     CofiTech?» (accion = 'interes_venta_directa', metadata.le_gustaria) entra
--     en calificacion_utilidad.
--   · vw_kpis_consolidados: columnas nuevas al final
--       votos_interes_mercado  votos recibidos
--       interes_mercado        votos 👍 / votos (0 a 1)
--       sesiones_simulador     sesiones que usaron el simulador de venta
--   · vw_interes_venta_directa: un voto por fila, con rol, municipio y si la
--     sesión probó el simulador antes de votar.
--
-- No crea tablas: los votos ya llegan a registro_eventos_uso como cualquier
-- otro evento de la app (herramienta 'Mercado').
-- ════════════════════════════════════════════════════════════════════════════

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
           WHEN e.accion = 'interes_venta_directa'
                AND jsonb_typeof(e.metadata->'le_gustaria') = 'boolean'
               THEN (e.metadata->>'le_gustaria')::boolean
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
    '(RAG: respuesta útil; Visión: diagnóstico aceptado; Mercado: le gustaría la venta directa); '
    'confianza_modelo = certeza de la CNN.';

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
       MAX(k.fecha)                                                                   AS ultimo_evento,
       -- v1.6 (columnas al final para que CREATE OR REPLACE VIEW funcione sobre la v1.5)
       COUNT(k.calificacion_utilidad) FILTER (WHERE k.accion = 'interes_venta_directa') AS votos_interes_mercado,
       ROUND(AVG(k.calificacion_utilidad::int)
             FILTER (WHERE k.accion = 'interes_venta_directa'), 4)                    AS interes_mercado,
       COUNT(DISTINCT k.id_sesion) FILTER (WHERE k.accion = 'simulacion_venta')       AS sesiones_simulador
FROM cafe.telemetria_kpis k
GROUP BY GROUPING SETS ((k.rol), ());

COMMENT ON VIEW cafe.vw_kpis_consolidados IS
    'KPIs de la entrega de Data Thinking: satisfacción RAG, confianza aceptada (Visión), KR3 e interés en la '
    'venta directa (Beta), por rol y en total.';

-- KPI «Interés en la venta directa»: un voto 👍/👎 por sesión desde «Vender mi café»
-- (inactiva en la Beta). uso_simulador = la sesión probó el simulador antes de votar.
CREATE OR REPLACE VIEW cafe.vw_interes_venta_directa
WITH (security_invoker = true) AS
SELECT e.id,
       e.fecha,
       e.id_sesion,
       e.usuario_rol                                   AS rol,
       e.metadata->>'municipio'                        AS municipio,
       e.metadata->>'codigo_dane'                      AS codigo_dane,
       (e.metadata->>'le_gustaria')::boolean           AS le_gustaria,
       COALESCE((e.metadata->>'uso_simulador')::boolean, false) AS uso_simulador
FROM cafe.registro_eventos_uso e
WHERE e.accion = 'interes_venta_directa'
  AND jsonb_typeof(e.metadata->'le_gustaria') = 'boolean';

COMMENT ON VIEW cafe.vw_interes_venta_directa IS
    'Votos de la pregunta «¿Te gustaría vender tu café desde CofiTech?» (Beta 0.9.0). Sin datos personales.';

-- Seguridad: las vistas nuevas tampoco son visibles para anon/authenticated.
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

SELECT 'OK (v1.6) · KPI de interés en la venta directa · ' ||
       (SELECT count(*) FROM cafe.vw_interes_venta_directa) || ' votos' AS status;
