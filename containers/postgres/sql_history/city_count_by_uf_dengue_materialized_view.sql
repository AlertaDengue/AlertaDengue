SET statement_timeout TO '10min';

CREATE MATERIALIZED VIEW public.city_count_by_uf_dengue_materialized_view AS
SELECT
    b.uf,
    'dengue' AS disease,
    COUNT(DISTINCT a.municipio_geocodigo) AS city_count
FROM
    "Municipio"."Historico_alerta" AS a
JOIN
    "Dengue_global"."Municipio" AS b ON a.municipio_geocodigo = b.geocodigo
GROUP BY b.uf;

RESET statement_timeout;
