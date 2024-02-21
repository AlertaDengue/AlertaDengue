-- Script to create a materialized view
CREATE MATERIALIZED VIEW public.epiyear_summary_materialized_view AS
SELECT
  notif.ano_notif,
  notif.se_notif,
  COUNT(notif.se_notif) AS casos,
  municipio.uf,
  REPLACE(notif.cid10_codigo, '.', '') AS disease_code
FROM
  "Municipio"."Notificacao" AS notif
INNER JOIN "Dengue_global"."Municipio" AS municipio ON notif.municipio_geocodigo = municipio.geocodigo
GROUP BY notif.ano_notif, notif.se_notif, municipio.uf, disease_code
WITH DATA;

-- Create an index on the materialized view for faster filtering by uf and disease_code
CREATE INDEX idx_epiyear_summary_materialized_view_on_uf_and_disease_code ON public.epiyear_summary_materialized_view(uf, disease_code);

-- Command to refresh the materialized view, run as needed
-- REFRESH MATERIALIZED VIEW public.epiyear_summary_materialized_view;
