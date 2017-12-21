CREATE OR REPLACE VIEW "Municipio".historico_casos AS 

SELECT 
    dengue."data_iniSE",
    dengue."SE",
    COALESCE(dengue.casos_est, 0.0) +
      COALESCE(chik.casos_est, 0.0) +
      COALESCE(zika.casos_est, 0.0) AS casos_est,
    COALESCE(dengue.casos_est_min, 0) +
      COALESCE(chik.casos_est_min, 0) +
      COALESCE(zika.casos_est_min, 0) AS casos_est_min,
    COALESCE(dengue.casos_est_max, 0) +
      COALESCE(chik.casos_est_max, 0) +
      COALESCE(zika.casos_est_max, 0) AS casos_est_max,
    COALESCE(dengue.casos, 0) +
      COALESCE(chik.casos, 0) +
      COALESCE(zika.casos, 0) AS casos,
    dengue.municipio_geocodigo
FROM 
    "Municipio"."Historico_alerta" AS dengue
    FULL OUTER JOIN "Municipio"."Historico_alerta_chik" AS chik
        ON dengue."SE" = chik."SE"
        AND dengue.municipio_geocodigo = chik.municipio_geocodigo
    FULL OUTER JOIN "Municipio"."Historico_alerta_zika" AS zika
        ON dengue."SE" = zika."SE"
        AND dengue.municipio_geocodigo = zika.municipio_geocodigo