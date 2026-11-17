-- ════════════════════════════════════════════════════════════════════════════
-- CofiTech · Variedad «Catimor / Costa Rica 95» (nov-2026)
-- Para bases ya creadas con 01_ddl_schema.sql o 03_supabase_schema.sql.
-- Idempotente: se puede ejecutar varias veces. No borra ni cambia otras filas.
-- ════════════════════════════════════════════════════════════════════════════
-- Por qué: un usuario no encontró su variedad («catumorro»). Catimor es el
-- nombre genérico de líneas Caturra × Híbrido de Timor; en Colombia también le
-- dicen «Costa Rica». Cenicafé: los Catimores que entraron al país (Costa Rica
-- 95 y otros) no tienen resistencia suficiente a la roya → resistencia «Baja».
--
-- La app no lee esta tabla para decidir (usa VARIEDADES en
-- 07_app_web/cofitech/contexto_finca.py); se agrega para que el catálogo de la
-- base y el de la app coincidan.
-- ════════════════════════════════════════════════════════════════════════════

INSERT INTO cafe.dim_variedad_cafe (nombre, especie, resistencia_roya, altitud_optima_min, altitud_optima_max)
SELECT 'Catimor / Costa Rica 95', 'Arábica', 'Baja', NULL, NULL
 WHERE NOT EXISTS (SELECT 1 FROM cafe.dim_variedad_cafe WHERE nombre = 'Catimor / Costa Rica 95');

SELECT 'OK · ' || count(*) || ' variedades en cafe.dim_variedad_cafe' AS status
  FROM cafe.dim_variedad_cafe;
