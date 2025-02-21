SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;
SET default_tablespace = '';
SET default_table_access_method = heap;


ALTER SCHEMA public OWNER TO dengueadmin;

CREATE SCHEMA weather;
ALTER SCHEMA weather OWNER TO dengueadmin;


ALTER TABLE "Dengue_global"."Municipio" OWNER TO administrador;
ALTER TABLE "Dengue_global".estado OWNER TO administrador;
ALTER TABLE "Dengue_global".parameters OWNER TO dengueadmin;
ALTER TABLE "Municipio"."Bairro" OWNER TO administrador;
ALTER TABLE "Municipio"."Clima_wu" OWNER TO administrador;
ALTER TABLE "Municipio"."Estacao_cemaden" OWNER TO administrador;
ALTER TABLE "Municipio"."Estacao_wu" OWNER TO administrador;
ALTER TABLE "Municipio"."Localidade" OWNER TO administrador;
ALTER TABLE "Municipio"."Notificacao" OWNER TO administrador;


ALTER TABLE "Municipio".historico_casos OWNER TO postgres;


ALTER TABLE public.auth_group OWNER TO dengueadmin;


ALTER TABLE public.auth_group_id_seq OWNER TO dengueadmin;


ALTER TABLE public.auth_group_permissions OWNER TO dengueadmin;


ALTER TABLE public.auth_permission OWNER TO dengueadmin;


ALTER TABLE public.auth_permission_id_seq OWNER TO dengueadmin;


ALTER TABLE public.auth_user OWNER TO dengueadmin;


ALTER TABLE public.auth_user_groups OWNER TO dengueadmin;


ALTER TABLE public.auth_user_id_seq OWNER TO dengueadmin;


ALTER TABLE public.auth_user_user_permissions OWNER TO dengueadmin;


ALTER TABLE public.dbf_dbf OWNER TO dengueadmin;


ALTER TABLE public.dbf_dbfchunkedupload OWNER TO dengueadmin;


ALTER TABLE public.django_admin_log OWNER TO dengueadmin;


ALTER TABLE public.django_admin_log_id_seq OWNER TO dengueadmin;


ALTER TABLE public.django_content_type OWNER TO dengueadmin;


ALTER TABLE public.django_migrations OWNER TO dengueadmin;


ALTER TABLE public.django_session OWNER TO dengueadmin;


CREATE MATERIALIZED VIEW public.hist_uf_chik_materialized_view AS
 SELECT upper((state.uf)::text) AS state_abbv,
    city.uf AS state_name,
    alerta.municipio_geocodigo,
    alerta."SE",
    alerta."data_iniSE",
    alerta.casos_est,
    alerta.casos,
    alerta.nivel,
    alerta.receptivo
   FROM (("Municipio"."Historico_alerta_chik" alerta
     JOIN "Dengue_global"."Municipio" city ON ((alerta.municipio_geocodigo = city.geocodigo)))
     JOIN "Dengue_global".estado state ON ((upper((city.uf)::text) = (state.nome)::text)))
  WHERE (alerta."data_iniSE" >= ( SELECT (max(alerta_1."data_iniSE") - '28 days'::interval) AS max_date
           FROM "Municipio"."Historico_alerta_chik" alerta_1))
  ORDER BY alerta."data_iniSE"
  WITH NO DATA;


ALTER TABLE public.hist_uf_chik_materialized_view OWNER TO dengueadmin;


CREATE MATERIALIZED VIEW public.hist_uf_dengue_materialized_view AS
 SELECT upper((state.uf)::text) AS state_abbv,
    city.uf AS state_name,
    alerta.municipio_geocodigo,
    alerta."SE",
    alerta."data_iniSE",
    alerta.casos_est,
    alerta.casos,
    alerta.nivel,
    alerta.receptivo
   FROM (("Municipio"."Historico_alerta" alerta
     JOIN "Dengue_global"."Municipio" city ON ((alerta.municipio_geocodigo = city.geocodigo)))
     JOIN "Dengue_global".estado state ON ((upper((city.uf)::text) = (state.nome)::text)))
  WHERE (alerta."data_iniSE" >= ( SELECT (max(alerta_1."data_iniSE") - '28 days'::interval) AS max_date
           FROM "Municipio"."Historico_alerta" alerta_1))
  ORDER BY alerta."data_iniSE"
  WITH NO DATA;


ALTER TABLE public.hist_uf_dengue_materialized_view OWNER TO dengueadmin;


CREATE MATERIALIZED VIEW public.hist_uf_zika_materialized_view AS
 SELECT upper((state.uf)::text) AS state_abbv,
    city.uf AS state_name,
    alerta.municipio_geocodigo,
    alerta."SE",
    alerta."data_iniSE",
    alerta.casos_est,
    alerta.casos,
    alerta.nivel,
    alerta.receptivo
   FROM (("Municipio"."Historico_alerta_zika" alerta
     JOIN "Dengue_global"."Municipio" city ON ((alerta.municipio_geocodigo = city.geocodigo)))
     JOIN "Dengue_global".estado state ON ((upper((city.uf)::text) = (state.nome)::text)))
  WHERE (alerta."data_iniSE" >= ( SELECT (max(alerta_1."data_iniSE") - '28 days'::interval) AS max_date
           FROM "Municipio"."Historico_alerta_zika" alerta_1))
  ORDER BY alerta."data_iniSE"
  WITH NO DATA;


ALTER TABLE public.hist_uf_zika_materialized_view OWNER TO dengueadmin;


CREATE MATERIALIZED VIEW public.uf_total_chik_view AS
 SELECT "Municipio".uf,
    "Historico_alerta_chik"."data_iniSE" AS data,
    sum("Historico_alerta_chik".casos) AS casos_s,
    sum("Historico_alerta_chik".casos_est) AS casos_est_s
   FROM ("Municipio"."Historico_alerta_chik"
     JOIN "Dengue_global"."Municipio" ON (("Historico_alerta_chik".municipio_geocodigo = "Municipio".geocodigo)))
  GROUP BY "Historico_alerta_chik"."data_iniSE", "Municipio".uf
  ORDER BY "Municipio".uf, "Historico_alerta_chik"."data_iniSE"
  WITH NO DATA;


ALTER TABLE public.uf_total_chik_view OWNER TO administrador;


CREATE MATERIALIZED VIEW public.uf_total_view AS
 SELECT "Municipio".uf,
    "Historico_alerta"."data_iniSE" AS data,
    sum("Historico_alerta".casos) AS casos_s,
    sum("Historico_alerta".casos_est) AS casos_est_s
   FROM ("Municipio"."Historico_alerta"
     JOIN "Dengue_global"."Municipio" ON (("Historico_alerta".municipio_geocodigo = "Municipio".geocodigo)))
  GROUP BY "Historico_alerta"."data_iniSE", "Municipio".uf
  ORDER BY "Municipio".uf, "Historico_alerta"."data_iniSE"
  WITH NO DATA;


ALTER TABLE public.uf_total_view OWNER TO administrador;


CREATE MATERIALIZED VIEW public.uf_total_zika_view AS
 SELECT "Municipio".uf,
    "Historico_alerta_zika"."data_iniSE" AS data,
    sum("Historico_alerta_zika".casos) AS casos_s,
    sum("Historico_alerta_zika".casos_est) AS casos_est_s
   FROM ("Municipio"."Historico_alerta_zika"
     JOIN "Dengue_global"."Municipio" ON (("Historico_alerta_zika".municipio_geocodigo = "Municipio".geocodigo)))
  GROUP BY "Historico_alerta_zika"."data_iniSE", "Municipio".uf
  ORDER BY "Municipio".uf, "Historico_alerta_zika"."data_iniSE"
  WITH NO DATA;


ALTER TABLE public.uf_total_zika_view OWNER TO postgres;


GRANT USAGE ON SCHEMA "Dengue_global" TO "Read_only";
GRANT USAGE ON SCHEMA "Dengue_global" TO infodenguedev;


GRANT USAGE ON SCHEMA "Municipio" TO infodenguedev;


GRANT USAGE ON SCHEMA forecast TO infodenguedev;


REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;
GRANT USAGE ON SCHEMA public TO infodenguedev;


GRANT USAGE ON SCHEMA weather TO infodenguedev;


GRANT ALL ON TABLE "Dengue_global"."CID10" TO "Dengue";
GRANT ALL ON TABLE "Dengue_global"."CID10" TO dengue;
GRANT SELECT ON TABLE "Dengue_global"."CID10" TO "Read_only";
GRANT SELECT ON TABLE "Dengue_global"."CID10" TO infodenguedev;


GRANT ALL ON TABLE "Dengue_global"."Municipio" TO "Dengue";
GRANT ALL ON TABLE "Dengue_global"."Municipio" TO dengue;
GRANT SELECT ON TABLE "Dengue_global"."Municipio" TO "Read_only";
GRANT SELECT ON TABLE "Dengue_global"."Municipio" TO infodenguedev;


GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLE "Dengue_global".estado TO "Dengue";
GRANT ALL ON TABLE "Dengue_global".estado TO dengue;
GRANT SELECT ON TABLE "Dengue_global".estado TO "Read_only";
GRANT SELECT ON TABLE "Dengue_global".estado TO infodenguedev;


GRANT ALL ON TABLE "Dengue_global".parameters TO dengue;
GRANT SELECT ON TABLE "Dengue_global".parameters TO "Read_only";
GRANT SELECT ON TABLE "Dengue_global".parameters TO infodenguedev;


GRANT ALL ON TABLE "Municipio"."Bairro" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Bairro" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Bairro" TO infodenguedev;


GRANT ALL ON TABLE "Municipio"."Clima_cemaden" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Clima_cemaden" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Clima_cemaden" TO infodenguedev;
ALTER TABLE "Municipio"."Clima_cemaden" OWNER TO administrador;


GRANT ALL ON TABLE "Municipio"."Clima_wu" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Clima_wu" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Clima_wu" TO infodenguedev;


GRANT ALL ON TABLE "Municipio"."Estacao_cemaden" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Estacao_cemaden" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Estacao_cemaden" TO infodenguedev;


GRANT ALL ON TABLE "Municipio"."Estacao_wu" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Estacao_wu" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Estacao_wu" TO infodenguedev;


GRANT ALL ON TABLE "Municipio"."Localidade" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Localidade" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Localidade" TO infodenguedev;


GRANT ALL ON TABLE "Municipio"."Notificacao" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Notificacao" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Notificacao" TO infodenguedev;


GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Notificacao_id_seq" TO dengue;


GRANT ALL ON TABLE "Municipio".historico_casos TO dengue;
GRANT SELECT ON TABLE "Municipio".historico_casos TO infodenguedev;


GRANT SELECT ON TABLE forecast.auth_group TO infodenguedev;


GRANT SELECT ON TABLE forecast.auth_group_permissions TO infodenguedev;


GRANT SELECT ON TABLE forecast.auth_permission TO infodenguedev;


GRANT SELECT ON TABLE forecast.auth_user TO infodenguedev;


GRANT SELECT ON TABLE forecast.auth_user_groups TO infodenguedev;


GRANT SELECT ON TABLE forecast.auth_user_user_permissions TO infodenguedev;


GRANT SELECT ON TABLE forecast.chunked_upload_chunkedupload TO infodenguedev;


GRANT SELECT ON TABLE forecast.django_admin_log TO infodenguedev;


GRANT SELECT ON TABLE forecast.django_content_type TO infodenguedev;


GRANT SELECT ON TABLE forecast.django_migrations TO infodenguedev;


GRANT SELECT ON TABLE forecast.django_session TO infodenguedev;


GRANT SELECT ON TABLE forecast.forecast_cases TO infodenguedev;


GRANT SELECT ON TABLE forecast.forecast_city TO infodenguedev;


GRANT SELECT ON TABLE forecast.forecast_model TO infodenguedev;


GRANT SELECT ON TABLE public.auth_group TO infodenguedev;


GRANT SELECT ON TABLE public.auth_group_permissions TO infodenguedev;


GRANT SELECT ON TABLE public.auth_permission TO infodenguedev;


GRANT SELECT ON TABLE public.auth_user TO infodenguedev;


GRANT SELECT ON TABLE public.auth_user_groups TO infodenguedev;


GRANT SELECT ON TABLE public.auth_user_user_permissions TO infodenguedev;


GRANT SELECT ON TABLE public.chunked_upload_chunkedupload TO infodenguedev;


GRANT SELECT ON TABLE public.dbf_dbf TO infodenguedev;


GRANT SELECT ON TABLE public.dbf_dbfchunkedupload TO infodenguedev;


GRANT SELECT ON TABLE public.django_admin_log TO infodenguedev;


GRANT SELECT ON TABLE public.django_content_type TO infodenguedev;


GRANT SELECT ON TABLE public.django_migrations TO infodenguedev;


GRANT SELECT ON TABLE public.django_session TO infodenguedev;


GRANT SELECT ON TABLE public.geography_columns TO infodenguedev;


GRANT SELECT ON TABLE public.geometry_columns TO infodenguedev;


GRANT SELECT ON TABLE public.hist_uf_chik_materialized_view TO infodenguedev;


GRANT SELECT ON TABLE public.hist_uf_dengue_materialized_view TO infodenguedev;


GRANT SELECT ON TABLE public.hist_uf_zika_materialized_view TO infodenguedev;


GRANT SELECT ON TABLE public.spatial_ref_sys TO infodenguedev;


GRANT SELECT,INSERT,REFERENCES,TRIGGER,UPDATE ON TABLE public.uf_total_chik_view TO "Dengue";
GRANT SELECT ON TABLE public.uf_total_chik_view TO infodenguedev;


GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLE public.uf_total_view TO "Dengue";
GRANT SELECT ON TABLE public.uf_total_view TO infodenguedev;


GRANT SELECT ON TABLE public.uf_total_zika_view TO infodenguedev;


ALTER DEFAULT PRIVILEGES FOR ROLE administrador GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLES  TO "Dengue";
ALTER DEFAULT PRIVILEGES FOR ROLE administrador GRANT SELECT ON TABLES  TO "Read_only";
