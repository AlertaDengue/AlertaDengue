-- Drop the view if it exists
DROP MATERIALIZED VIEW IF EXISTS "Municipio".historico_casos;

-- Create the view
CREATE MATERIALIZED VIEW "Municipio".historico_casos AS
 SELECT dengue."data_iniSE",
    dengue."SE",
    (COALESCE(dengue.casos_est, (0.0)::real) + COALESCE(chik.casos_est, (0.0)::real)) AS casos_est,
    (COALESCE(dengue.casos_est_min, 0) + COALESCE(chik.casos_est_min, 0)) AS casos_est_min,
    (COALESCE(dengue.casos_est_max, 0) + COALESCE(chik.casos_est_max, 0)) AS casos_est_max,
    (COALESCE(dengue.casos, 0) + COALESCE(chik.casos, 0)) AS casos,
    dengue.municipio_geocodigo
   FROM ("Municipio"."Historico_alerta" dengue
     FULL JOIN "Municipio"."Historico_alerta_chik" chik ON (((dengue."SE" = chik."SE") AND (dengue.municipio_geocodigo = chik.municipio_geocodigo))));

-- Create the index on the view
CREATE INDEX historico_casos_data_iniSE_idx ON "Municipio".historico_casos ("data_iniSE" DESC);
CREATE INDEX historico_casos_municipio_geocodigo_idx ON "Municipio".historico_casos (municipio_geocodigo DESC);

-- Refresh the view to populate all data
REFRESH MATERIALIZED VIEW "Municipio".historico_casos;
