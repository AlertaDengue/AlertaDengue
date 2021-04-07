-- Materialized View: public.uf_total_view
-- DISEASE: DENGUE
-- CREATE VIEW vista AS SELECT 'Hello World';

DROP MATERIALIZED
VIEW
IF EXISTS public.hist_uf_dengue_materialized_view CASCADE;
CREATE MATERIALIZED VIEW public.hist_uf_dengue_materialized_view
AS
SELECT city.uf,
    alerta.municipio_geocodigo,
    alerta."SE",
    alerta."data_iniSE",
    alerta.casos_est,
    alerta.casos,
    alerta.nivel,
    alerta.receptivo
FROM "Municipio"."Historico_alerta" AS alerta
INNER JOIN "Dengue_global"."Municipio" AS city ON (
                alerta.municipio_geocodigo=city.geocodigo)
WHERE alerta."data_iniSE" >= (
        SELECT MAX(alerta."data_iniSE") - interval '4 weeks'
            AS max_date FROM "Municipio"."Historico_alerta" AS alerta
        )                    
    ORDER BY alerta."data_iniSE";

DROP MATERIALIZED VIEW
IF EXISTS public.hist_uf_chik_materialized_view CASCADE;
CREATE MATERIALIZED VIEW public.hist_uf_chik_materialized_view
AS
SELECT city.uf,
    alerta.municipio_geocodigo,
    alerta."SE",
    alerta."data_iniSE",
    alerta.casos_est,
    alerta.casos,
    alerta.nivel,
    alerta.receptivo
FROM "Municipio"."Historico_alerta_chik" AS alerta
INNER JOIN "Dengue_global"."Municipio" AS city ON (
            alerta.municipio_geocodigo=city.geocodigo)
WHERE alerta."data_iniSE" >= (
        SELECT MAX(alerta."data_iniSE") - interval '4 weeks'
            AS max_date FROM "Municipio"."Historico_alerta_chik" AS alerta
        )                    
ORDER BY alerta."data_iniSE";

DROP MATERIALIZED VIEW
IF EXISTS public.hist_uf_zika_materialized_view CASCADE;
CREATE MATERIALIZED VIEW public.hist_uf_zika_materialized_view
AS
SELECT city.uf,
    alerta.municipio_geocodigo,
    alerta."SE",
    alerta."data_iniSE",
    alerta.casos_est,
    alerta.casos,
    alerta.nivel,
    alerta.receptivo
FROM "Municipio"."Historico_alerta_zika" AS alerta
INNER JOIN "Dengue_global"."Municipio" AS city ON (
            alerta.municipio_geocodigo=city.geocodigo)
WHERE alerta."data_iniSE" >= (
        SELECT MAX(alerta."data_iniSE") - interval '4 weeks'
            AS max_date FROM "Municipio"."Historico_alerta_zika" AS alerta
        )                    
ORDER BY alerta."data_iniSE";
