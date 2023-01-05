--
-- DATABASE: DENGUE
-- https://github.com/AlertaDengue/AlertaDengue/issues/527
--
--
-- Dengue disease
ALTER TABLE "Municipio"."Historico_alerta" ADD COLUMN casprov INTEGER;
ALTER TABLE "Municipio"."Historico_alerta" ADD COLUMN casprov_est REAL;
ALTER TABLE "Municipio"."Historico_alerta" ADD COLUMN casprov_est_min INTEGER;
ALTER TABLE "Municipio"."Historico_alerta" ADD COLUMN casprov_est_max INTEGER;
ALTER TABLE "Municipio"."Historico_alerta" ADD COLUMN casconf INTEGER;
-- Chikungunya disease
ALTER TABLE "Municipio"."Historico_alerta_chik" ADD COLUMN casprov INTEGER;
ALTER TABLE "Municipio"."Historico_alerta_chik" ADD COLUMN casprov_est REAL;
ALTER TABLE "Municipio"."Historico_alerta_chik" ADD COLUMN casprov_est_min INTEGER;
ALTER TABLE "Municipio"."Historico_alerta_chik" ADD COLUMN casprov_est_max INTEGER;
ALTER TABLE "Municipio"."Historico_alerta_chik" ADD COLUMN casconf INTEGER;
-- Zika disease
ALTER TABLE "Municipio"."Historico_alerta_zika" ADD COLUMN casprov INTEGER;
ALTER TABLE "Municipio"."Historico_alerta_zika" ADD COLUMN casprov_est REAL;
ALTER TABLE "Municipio"."Historico_alerta_zika" ADD COLUMN casprov_est_min INTEGER;
ALTER TABLE "Municipio"."Historico_alerta_zika" ADD COLUMN casprov_est_max INTEGER;
ALTER TABLE "Municipio"."Historico_alerta_zika" ADD COLUMN casconf INTEGER;
--
