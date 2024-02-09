CREATE MATERIALIZED VIEW public.city_count_by_uf_chik_materialized_view AS
SELECT
    b.uf,
    'chikungunya' AS disease,
    COUNT(DISTINCT a.municipio_geocodigo) AS city_count
FROM
    "Municipio"."Historico_alerta_chik" AS a
JOIN
    "Dengue_global"."Municipio" AS b ON a.municipio_geocodigo = b.geocodigo
GROUP BY b.uf;
