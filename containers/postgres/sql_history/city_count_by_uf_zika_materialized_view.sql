CREATE MATERIALIZED VIEW public.city_count_by_uf_zika_materialized_view AS
SELECT
    b.uf,
    'zika' AS disease,
    COUNT(DISTINCT a.municipio_geocodigo) AS city_count
FROM
    "Municipio"."Historico_alerta_zika" AS a
JOIN
    "Dengue_global"."Municipio" AS b ON a.municipio_geocodigo = b.geocodigo
GROUP BY b.uf;
