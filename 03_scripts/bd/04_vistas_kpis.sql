-- ════════════════════════════════════════════════════════════════════════════
-- CofiTech · Vistas de KPIs (migración v1.3 → v1.4)
-- Para pegar en el SQL Editor de Supabase si ya se ejecutó 03_supabase_schema.sql.
-- Idempotente (CREATE OR REPLACE VIEW). 03_supabase_schema.sql v1.4 ya las incluye.
-- Requiere PostgreSQL 15+ (security_invoker).
-- ════════════════════════════════════════════════════════════════════════════

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

-- Las vistas heredan el bloqueo del esquema: anon y authenticated no tienen USAGE sobre cafe.
SELECT rol, satisfaccion_rag, confianza_aceptada, sesiones_3_herramientas FROM cafe.vw_kpis_consolidados;
