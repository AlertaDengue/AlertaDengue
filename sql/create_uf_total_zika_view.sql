-- Materialized View: public.uf_total_zika_view

DROP MATERIALIZED VIEW IF EXISTS public.uf_total_zika_view;

CREATE MATERIALIZED VIEW public.uf_total_zika_view AS
 SELECT "Municipio".uf,
    "Historico_alerta_zika"."data_iniSE" AS data,
    SUM("Historico_alerta_zika".casos) AS casos_s,
    SUM("Historico_alerta_zika".casos_est) AS casos_est_s
   FROM "Municipio"."Historico_alerta_zika"
     JOIN "Dengue_global"."Municipio"
     ON "Historico_alerta_zika".municipio_geocodigo = "Municipio".geocodigo
  GROUP BY "Historico_alerta_zika"."data_iniSE", "Municipio".uf
  ORDER BY "Municipio".uf, "Historico_alerta_zika"."data_iniSE"
WITH DATA;
