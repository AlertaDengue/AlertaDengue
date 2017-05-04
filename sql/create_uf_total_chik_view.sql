-- Materialized View: public.uf_total_view

-- DROP MATERIALIZED VIEW public.uf_total_view;

CREATE MATERIALIZED VIEW public.uf_total_chik_view AS 
 SELECT "Municipio".uf,
    "Historico_alerta_chik"."data_iniSE" AS data,
    SUM("Historico_alerta_chik".casos) AS casos_s,
    SUM("Historico_alerta_chik".casos_est) AS casos_est_s
   FROM "Municipio"."Historico_alerta_chik"
     JOIN "Dengue_global"."Municipio"
     ON "Historico_alerta_chik".municipio_geocodigo = "Municipio".geocodigo
  GROUP BY "Historico_alerta_chik"."data_iniSE", "Municipio".uf
  ORDER BY "Municipio".uf, "Historico_alerta_chik"."data_iniSE"
WITH DATA;

ALTER TABLE public.uf_total_chik_view
  OWNER TO administrador;

GRANT ALL ON TABLE public.uf_total_chik_view TO administrador;
GRANT SELECT, UPDATE, INSERT, REFERENCES, TRIGGER
    ON TABLE public.uf_total_chik_view TO "Dengue";

-- Index: public.uf_total_view_data_idx

-- DROP INDEX public.uf_total_view_data_idx;

CREATE INDEX uf_total_chik_view_data_idx
  ON public.uf_total_chik_view
  USING btree
  (data);
