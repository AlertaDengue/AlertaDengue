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


CREATE SCHEMA "Dengue_global";
ALTER SCHEMA "Dengue_global" OWNER TO "Dengue";


CREATE SCHEMA "Municipio";
ALTER SCHEMA "Municipio" OWNER TO "Dengue";


CREATE SCHEMA forecast;
ALTER SCHEMA forecast OWNER TO postgres;


ALTER SCHEMA public OWNER TO dengueadmin;


CREATE SCHEMA weather;
ALTER SCHEMA weather OWNER TO dengueadmin;


CREATE TABLE "Dengue_global"."CID10" (
    nome character varying(512) NOT NULL,
    codigo character varying(5) NOT NULL
);

ALTER TABLE "Dengue_global"."CID10" OWNER TO administrador;

CREATE TABLE "Dengue_global"."Municipio" (
    geocodigo integer NOT NULL,
    nome character varying(128) NOT NULL,
    geojson text NOT NULL,
    populacao bigint NOT NULL,
    uf character varying(20) NOT NULL,
    id_regional integer NOT NULL,
    regional character varying(128) NOT NULL,
    macroregional_id integer NOT NULL,
    macroregional character varying(128) NOT NULL
);

ALTER TABLE "Dengue_global"."Municipio" OWNER TO administrador;
ALTER TABLE "Dengue_global".estado OWNER TO administrador;
ALTER TABLE "Dengue_global".parameters OWNER TO dengueadmin;
ALTER TABLE "Municipio"."Bairro" OWNER TO administrador;
ALTER TABLE "Municipio"."Clima_wu" OWNER TO administrador;
ALTER TABLE "Municipio"."Estacao_cemaden" OWNER TO administrador;
ALTER TABLE "Municipio"."Estacao_wu" OWNER TO administrador;
ALTER TABLE "Municipio"."Localidade" OWNER TO administrador;
ALTER TABLE "Municipio"."Notificacao" OWNER TO administrador;


-- CREATE TABLE "Municipio"."Notificacao__20220806" (
--     id bigint,
--     dt_notific date,
--     se_notif integer,
--     ano_notif integer,
--     dt_sin_pri date,
--     se_sin_pri integer,
--     dt_digita date,
--     municipio_geocodigo integer,
--     nu_notific integer,
--     cid10_codigo character varying(5),
--     dt_nasc date,
--     cs_sexo character varying(1),
--     nu_idade_n integer,
--     resul_pcr numeric,
--     criterio numeric,
--     classi_fin numeric
-- );


-- ALTER TABLE "Municipio"."Notificacao__20220806" OWNER TO dengueadmin;

-- CREATE TABLE "Municipio".alerta_mrj (
--     id bigint NOT NULL,
--     aps character varying(6) NOT NULL,
--     se integer NOT NULL,
--     data date NOT NULL,
--     casos integer,
--     casos_est real,
--     casos_estmin real,
--     casos_estmax real,
--     tmin real,
--     rt real,
--     prt1 real,
--     inc real,
--     nivel integer
-- );


-- ALTER TABLE "Municipio".alerta_mrj OWNER TO dengueadmin;


-- CREATE TABLE "Municipio".alerta_mrj_chik (
--     id bigint NOT NULL,
--     aps character varying(6) NOT NULL,
--     se integer NOT NULL,
--     data date NOT NULL,
--     casos integer,
--     casos_est real,
--     casos_estmin real,
--     casos_estmax real,
--     tmin real,
--     rt real,
--     prt1 real,
--     inc real,
--     nivel integer
-- );


-- ALTER TABLE "Municipio".alerta_mrj_chik OWNER TO dengueadmin;


-- CREATE SEQUENCE "Municipio".alerta_mrj_chik_id_seq
--     START WITH 1
--     INCREMENT BY 1
--     NO MINVALUE
--     NO MAXVALUE
--     CACHE 1;


-- ALTER TABLE "Municipio".alerta_mrj_chik_id_seq OWNER TO dengueadmin;


-- ALTER SEQUENCE "Municipio".alerta_mrj_chik_id_seq OWNED BY "Municipio".alerta_mrj_chik.id;


-- CREATE SEQUENCE "Municipio".alerta_mrj_id_seq
--     START WITH 1
--     INCREMENT BY 1
--     NO MINVALUE
--     NO MAXVALUE
--     CACHE 1;


-- ALTER TABLE "Municipio".alerta_mrj_id_seq OWNER TO dengueadmin;


-- ALTER SEQUENCE "Municipio".alerta_mrj_id_seq OWNED BY "Municipio".alerta_mrj.id;


-- CREATE TABLE "Municipio".alerta_mrj_zika (
--     id bigint NOT NULL,
--     aps character varying(6) NOT NULL,
--     se integer NOT NULL,
--     data date NOT NULL,
--     casos integer,
--     casos_est real,
--     casos_estmin real,
--     casos_estmax real,
--     tmin real,
--     rt real,
--     prt1 real,
--     inc real,
--     nivel integer
-- );


-- ALTER TABLE "Municipio".alerta_mrj_zika OWNER TO postgres;


-- CREATE SEQUENCE "Municipio".alerta_mrj_zika_id_seq
--     START WITH 1
--     INCREMENT BY 1
--     NO MINVALUE
--     NO MAXVALUE
--     CACHE 1;


-- ALTER TABLE "Municipio".alerta_mrj_zika_id_seq OWNER TO postgres;


-- ALTER SEQUENCE "Municipio".alerta_mrj_zika_id_seq OWNED BY "Municipio".alerta_mrj_zika.id;



CREATE VIEW "Municipio".historico_casos AS
 SELECT dengue."data_iniSE",
    dengue."SE",
    (COALESCE(dengue.casos_est, (0.0)::real) + COALESCE(chik.casos_est, (0.0)::real)) AS casos_est,
    (COALESCE(dengue.casos_est_min, 0) + COALESCE(chik.casos_est_min, 0)) AS casos_est_min,
    (COALESCE(dengue.casos_est_max, 0) + COALESCE(chik.casos_est_max, 0)) AS casos_est_max,
    (COALESCE(dengue.casos, 0) + COALESCE(chik.casos, 0)) AS casos,
    dengue.municipio_geocodigo
   FROM ("Municipio"."Historico_alerta" dengue
     FULL JOIN "Municipio"."Historico_alerta_chik" chik ON (((dengue."SE" = chik."SE") AND (dengue.municipio_geocodigo = chik.municipio_geocodigo))));


ALTER TABLE "Municipio".historico_casos OWNER TO postgres;


CREATE TABLE forecast.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE forecast.auth_group OWNER TO forecast;


CREATE SEQUENCE forecast.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_group_id_seq OWNER TO forecast;


ALTER SEQUENCE forecast.auth_group_id_seq OWNED BY forecast.auth_group.id;


CREATE TABLE forecast.auth_group_permissions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE forecast.auth_group_permissions OWNER TO forecast;


CREATE SEQUENCE forecast.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_group_permissions_id_seq OWNER TO forecast;


ALTER SEQUENCE forecast.auth_group_permissions_id_seq OWNED BY forecast.auth_group_permissions.id;


CREATE TABLE forecast.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE forecast.auth_permission OWNER TO forecast;


CREATE SEQUENCE forecast.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_permission_id_seq OWNER TO forecast;


ALTER SEQUENCE forecast.auth_permission_id_seq OWNED BY forecast.auth_permission.id;


CREATE TABLE forecast.auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);


ALTER TABLE forecast.auth_user OWNER TO forecast;


CREATE TABLE forecast.auth_user_groups (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE forecast.auth_user_groups OWNER TO forecast;


CREATE SEQUENCE forecast.auth_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_user_groups_id_seq OWNER TO forecast;


ALTER SEQUENCE forecast.auth_user_groups_id_seq OWNED BY forecast.auth_user_groups.id;


CREATE SEQUENCE forecast.auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_user_id_seq OWNER TO forecast;


ALTER SEQUENCE forecast.auth_user_id_seq OWNED BY forecast.auth_user.id;


CREATE TABLE forecast.auth_user_user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE forecast.auth_user_user_permissions OWNER TO forecast;


CREATE SEQUENCE forecast.auth_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_user_user_permissions_id_seq OWNER TO forecast;


ALTER SEQUENCE forecast.auth_user_user_permissions_id_seq OWNED BY forecast.auth_user_user_permissions.id;


CREATE TABLE forecast.chunked_upload_chunkedupload (
    id integer NOT NULL,
    upload_id character varying(32) NOT NULL,
    file character varying(255) NOT NULL,
    filename character varying(255) NOT NULL,
    "offset" bigint NOT NULL,
    created_on timestamp with time zone NOT NULL,
    status smallint NOT NULL,
    completed_on timestamp with time zone,
    user_id integer,
    CONSTRAINT chunked_upload_chunkedupload_status_check CHECK ((status >= 0))
);


ALTER TABLE forecast.chunked_upload_chunkedupload OWNER TO forecast;


CREATE SEQUENCE forecast.chunked_upload_chunkedupload_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.chunked_upload_chunkedupload_id_seq OWNER TO forecast;


ALTER SEQUENCE forecast.chunked_upload_chunkedupload_id_seq OWNED BY forecast.chunked_upload_chunkedupload.id;


CREATE TABLE forecast.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL, content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE forecast.django_admin_log OWNER TO forecast;


CREATE SEQUENCE forecast.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.django_admin_log_id_seq OWNER TO forecast;


ALTER SEQUENCE forecast.django_admin_log_id_seq OWNED BY forecast.django_admin_log.id;


CREATE TABLE forecast.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE forecast.django_content_type OWNER TO forecast;


CREATE SEQUENCE forecast.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.django_content_type_id_seq OWNER TO forecast;


ALTER SEQUENCE forecast.django_content_type_id_seq OWNED BY forecast.django_content_type.id;


CREATE TABLE forecast.django_migrations (
    id integer NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE forecast.django_migrations OWNER TO forecast;


CREATE SEQUENCE forecast.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.django_migrations_id_seq OWNER TO forecast;


ALTER SEQUENCE forecast.django_migrations_id_seq OWNED BY forecast.django_migrations.id;


CREATE TABLE forecast.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE forecast.django_session OWNER TO forecast;


CREATE TABLE forecast.forecast_cases (
    id integer NOT NULL,
    epiweek integer NOT NULL,
    geocode integer NOT NULL,
    cid10 character varying(5) NOT NULL,
    forecast_model_id integer,
    published_date date NOT NULL,
    init_date_epiweek date NOT NULL,
    cases integer NOT NULL
);


ALTER TABLE forecast.forecast_cases OWNER TO postgres;


CREATE SEQUENCE forecast.forecast_cases_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.forecast_cases_id_seq OWNER TO postgres;


ALTER SEQUENCE forecast.forecast_cases_id_seq OWNED BY forecast.forecast_cases.id;


CREATE TABLE forecast.forecast_city (
    id integer NOT NULL,
    geocode integer NOT NULL,
    forecast_model_id integer,
    active boolean NOT NULL
);


ALTER TABLE forecast.forecast_city OWNER TO postgres;


CREATE SEQUENCE forecast.forecast_city_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.forecast_city_id_seq OWNER TO postgres;


ALTER SEQUENCE forecast.forecast_city_id_seq OWNED BY forecast.forecast_city.id;


CREATE TABLE forecast.forecast_model (
    id integer NOT NULL,
    name character varying(128) NOT NULL,
    weeks smallint NOT NULL,
    commit_id character(7) NOT NULL,
    active boolean NOT NULL
);


ALTER TABLE forecast.forecast_model OWNER TO postgres;


CREATE SEQUENCE forecast.forecast_model_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.forecast_model_id_seq OWNER TO postgres;


ALTER SEQUENCE forecast.forecast_model_id_seq OWNED BY forecast.forecast_model.id;


CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO dengueadmin;


CREATE SEQUENCE public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.auth_group_id_seq OWNED BY public.auth_group.id;


CREATE TABLE public.auth_group_permissions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO dengueadmin;


CREATE SEQUENCE public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_permissions_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.auth_group_permissions_id_seq OWNED BY public.auth_group_permissions.id;


CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO dengueadmin;


CREATE SEQUENCE public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_permission_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.auth_permission_id_seq OWNED BY public.auth_permission.id;



CREATE TABLE public.auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);


ALTER TABLE public.auth_user OWNER TO dengueadmin;


CREATE TABLE public.auth_user_groups (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.auth_user_groups OWNER TO dengueadmin;


CREATE SEQUENCE public.auth_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_groups_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.auth_user_groups_id_seq OWNED BY public.auth_user_groups.id;


CREATE SEQUENCE public.auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.auth_user_id_seq OWNED BY public.auth_user.id;


CREATE TABLE public.auth_user_user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_user_user_permissions OWNER TO dengueadmin;


CREATE SEQUENCE public.auth_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_user_permissions_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.auth_user_user_permissions_id_seq OWNED BY public.auth_user_user_permissions.id;


CREATE TABLE public.chunked_upload_chunkedupload (
    id integer NOT NULL,
    upload_id character varying(32) NOT NULL,
    file character varying(255) NOT NULL,
    filename character varying(255) NOT NULL,
    "offset" bigint NOT NULL,
    created_on timestamp with time zone NOT NULL,
    status smallint NOT NULL,
    completed_on timestamp with time zone,
    user_id integer,
    CONSTRAINT chunked_upload_chunkedupload_status_check CHECK ((status >= 0))
);


ALTER TABLE public.chunked_upload_chunkedupload OWNER TO dengueadmin;


CREATE SEQUENCE public.chunked_upload_chunkedupload_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.chunked_upload_chunkedupload_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.chunked_upload_chunkedupload_id_seq OWNED BY public.chunked_upload_chunkedupload.id;


CREATE TABLE public.dbf_dbf (
    id integer NOT NULL,
    file character varying(100) NOT NULL,
    uploaded_at timestamp with time zone NOT NULL,
    export_date date NOT NULL,
    notification_year integer NOT NULL,
    uploaded_by_id integer NOT NULL,
    state_abbreviation character varying(2),
    municipio character varying(255) NOT NULL
);


ALTER TABLE public.dbf_dbf OWNER TO dengueadmin;


CREATE SEQUENCE public.dbf_dbf_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dbf_dbf_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.dbf_dbf_id_seq OWNED BY public.dbf_dbf.id;


CREATE TABLE public.dbf_dbfchunkedupload (
    id integer NOT NULL,
    upload_id character varying(32) NOT NULL,
    file character varying(255) NOT NULL,
    filename character varying(255) NOT NULL,
    "offset" bigint NOT NULL,
    created_on timestamp with time zone NOT NULL,
    status smallint NOT NULL,
    completed_on timestamp with time zone,
    user_id integer NOT NULL,
    CONSTRAINT dbf_dbfchunkedupload_status_check CHECK ((status >= 0))
);


ALTER TABLE public.dbf_dbfchunkedupload OWNER TO dengueadmin;


CREATE SEQUENCE public.dbf_dbfchunkedupload_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dbf_dbfchunkedupload_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.dbf_dbfchunkedupload_id_seq OWNED BY public.dbf_dbfchunkedupload.id;


CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO dengueadmin;


CREATE SEQUENCE public.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_admin_log_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.django_admin_log_id_seq OWNED BY public.django_admin_log.id;


CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO dengueadmin;


CREATE SEQUENCE public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_content_type_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.django_content_type_id_seq OWNED BY public.django_content_type.id;


CREATE TABLE public.django_migrations (
    id integer NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO dengueadmin;


CREATE SEQUENCE public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_migrations_id_seq OWNER TO dengueadmin;


ALTER SEQUENCE public.django_migrations_id_seq OWNED BY public.django_migrations.id;


CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


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


CREATE TABLE weather.copernicus_brasil (
    index integer NOT NULL,
    date date NOT NULL,
    geocodigo bigint NOT NULL,
    temp_min real NOT NULL,
    temp_med real NOT NULL,
    temp_max real NOT NULL,
    precip_min real NOT NULL,
    precip_med real NOT NULL,
    precip_max real NOT NULL,
    precip_tot real NOT NULL,
    pressao_min real NOT NULL,
    pressao_med real NOT NULL,
    pressao_max real NOT NULL,
    umid_min real NOT NULL,
    umid_med real NOT NULL,
    umid_max real NOT NULL
);


ALTER TABLE weather.copernicus_brasil OWNER TO dengueadmin;


CREATE SEQUENCE weather.copernicus_brasil_index_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE weather.copernicus_brasil_index_seq OWNER TO dengueadmin;


ALTER SEQUENCE weather.copernicus_brasil_index_seq OWNED BY weather.copernicus_brasil.index;


CREATE TABLE weather.copernicus_foz_do_iguacu (
    index integer NOT NULL,
    datetime timestamp without time zone NOT NULL,
    geocodigo bigint NOT NULL,
    temp real NOT NULL,
    precip real NOT NULL,
    pressao real NOT NULL,
    umid real NOT NULL
);


ALTER TABLE weather.copernicus_foz_do_iguacu OWNER TO dengueadmin;


CREATE SEQUENCE weather.copernicus_foz_do_iguacu_index_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE weather.copernicus_foz_do_iguacu_index_seq OWNER TO dengueadmin;


ALTER SEQUENCE weather.copernicus_foz_do_iguacu_index_seq OWNED BY weather.copernicus_foz_do_iguacu.index;


ALTER TABLE ONLY "Municipio"."Notificacao" ALTER COLUMN id SET DEFAULT nextval('"Municipio"."Notificacao_id_seq"'::regclass);


ALTER TABLE ONLY "Municipio".alerta_mrj ALTER COLUMN id SET DEFAULT nextval('"Municipio".alerta_mrj_id_seq'::regclass);


ALTER TABLE ONLY "Municipio".alerta_mrj_chik ALTER COLUMN id SET DEFAULT nextval('"Municipio".alerta_mrj_chik_id_seq'::regclass);


ALTER TABLE ONLY "Municipio".alerta_mrj_zika ALTER COLUMN id SET DEFAULT nextval('"Municipio".alerta_mrj_zika_id_seq'::regclass);


ALTER TABLE ONLY forecast.auth_group ALTER COLUMN id SET DEFAULT nextval('forecast.auth_group_id_seq'::regclass);


ALTER TABLE ONLY forecast.auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('forecast.auth_group_permissions_id_seq'::regclass);


ALTER TABLE ONLY forecast.auth_permission ALTER COLUMN id SET DEFAULT nextval('forecast.auth_permission_id_seq'::regclass);


ALTER TABLE ONLY forecast.auth_user ALTER COLUMN id SET DEFAULT nextval('forecast.auth_user_id_seq'::regclass);


ALTER TABLE ONLY forecast.auth_user_groups ALTER COLUMN id SET DEFAULT nextval('forecast.auth_user_groups_id_seq'::regclass);


ALTER TABLE ONLY forecast.auth_user_user_permissions ALTER COLUMN id SET DEFAULT nextval('forecast.auth_user_user_permissions_id_seq'::regclass);


ALTER TABLE ONLY forecast.chunked_upload_chunkedupload ALTER COLUMN id SET DEFAULT nextval('forecast.chunked_upload_chunkedupload_id_seq'::regclass);


ALTER TABLE ONLY forecast.django_admin_log ALTER COLUMN id SET DEFAULT nextval('forecast.django_admin_log_id_seq'::regclass);


ALTER TABLE ONLY forecast.django_content_type ALTER COLUMN id SET DEFAULT nextval('forecast.django_content_type_id_seq'::regclass);


ALTER TABLE ONLY forecast.django_migrations ALTER COLUMN id SET DEFAULT nextval('forecast.django_migrations_id_seq'::regclass);


ALTER TABLE ONLY forecast.forecast_cases ALTER COLUMN id SET DEFAULT nextval('forecast.forecast_cases_id_seq'::regclass);


ALTER TABLE ONLY forecast.forecast_city ALTER COLUMN id SET DEFAULT nextval('forecast.forecast_city_id_seq'::regclass);


ALTER TABLE ONLY forecast.forecast_model ALTER COLUMN id SET DEFAULT nextval('forecast.forecast_model_id_seq'::regclass);


ALTER TABLE ONLY public.auth_group ALTER COLUMN id SET DEFAULT nextval('public.auth_group_id_seq'::regclass);


ALTER TABLE ONLY public.auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_group_permissions_id_seq'::regclass);


ALTER TABLE ONLY public.auth_permission ALTER COLUMN id SET DEFAULT nextval('public.auth_permission_id_seq'::regclass);


ALTER TABLE ONLY public.auth_user ALTER COLUMN id SET DEFAULT nextval('public.auth_user_id_seq'::regclass);


ALTER TABLE ONLY public.auth_user_groups ALTER COLUMN id SET DEFAULT nextval('public.auth_user_groups_id_seq'::regclass);


ALTER TABLE ONLY public.auth_user_user_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_user_user_permissions_id_seq'::regclass);


ALTER TABLE ONLY public.chunked_upload_chunkedupload ALTER COLUMN id SET DEFAULT nextval('public.chunked_upload_chunkedupload_id_seq'::regclass);


ALTER TABLE ONLY public.dbf_dbf ALTER COLUMN id SET DEFAULT nextval('public.dbf_dbf_id_seq'::regclass);


ALTER TABLE ONLY public.dbf_dbfchunkedupload ALTER COLUMN id SET DEFAULT nextval('public.dbf_dbfchunkedupload_id_seq'::regclass);


ALTER TABLE ONLY public.django_admin_log ALTER COLUMN id SET DEFAULT nextval('public.django_admin_log_id_seq'::regclass);


ALTER TABLE ONLY public.django_content_type ALTER COLUMN id SET DEFAULT nextval('public.django_content_type_id_seq'::regclass);


ALTER TABLE ONLY public.django_migrations ALTER COLUMN id SET DEFAULT nextval('public.django_migrations_id_seq'::regclass);


ALTER TABLE ONLY weather.copernicus_brasil ALTER COLUMN index SET DEFAULT nextval('weather.copernicus_brasil_index_seq'::regclass);


ALTER TABLE ONLY weather.copernicus_foz_do_iguacu ALTER COLUMN index SET DEFAULT nextval('weather.copernicus_foz_do_iguacu_index_seq'::regclass);


ALTER TABLE ONLY "Dengue_global"."CID10"
    ADD CONSTRAINT "CID10_pk" PRIMARY KEY (codigo);


ALTER TABLE ONLY "Dengue_global"."Municipio"
    ADD CONSTRAINT "Municipio_pk" PRIMARY KEY (geocodigo);


ALTER TABLE ONLY "Dengue_global".estado
    ADD CONSTRAINT estado_pkey PRIMARY KEY (geocodigo);


ALTER TABLE ONLY "Dengue_global".parameters
    ADD CONSTRAINT parameters_pkey PRIMARY KEY (municipio_geocodigo);













ALTER TABLE ONLY "Municipio"."Notificacao"
    ADD CONSTRAINT "Notificacao_pk" PRIMARY KEY (id);






ALTER TABLE ONLY "Municipio".alerta_mrj_chik
    ADD CONSTRAINT alerta_mrj_chik_pk PRIMARY KEY (id);






ALTER TABLE ONLY "Municipio".alerta_mrj
    ADD CONSTRAINT alerta_mrj_pk PRIMARY KEY (id);






ALTER TABLE ONLY "Municipio".alerta_mrj_zika
    ADD CONSTRAINT alerta_mrj_zika_pk PRIMARY KEY (id);






ALTER TABLE ONLY "Municipio"."Notificacao"
    ADD CONSTRAINT casos_unicos UNIQUE (nu_notific, dt_notific, cid10_codigo, municipio_geocodigo);






ALTER TABLE ONLY "Municipio".alerta_mrj
    ADD CONSTRAINT previsao UNIQUE (aps, se);






ALTER TABLE ONLY "Municipio".alerta_mrj_chik
    ADD CONSTRAINT previsao_chik UNIQUE (aps, se);






ALTER TABLE ONLY "Municipio".alerta_mrj_zika
    ADD CONSTRAINT previsao_zika UNIQUE (aps, se);






ALTER TABLE ONLY "Municipio".alerta_mrj
    ADD CONSTRAINT unique_aps_se UNIQUE (se, aps);






ALTER TABLE ONLY "Municipio".alerta_mrj_chik
    ADD CONSTRAINT unique_chik_aps_se UNIQUE (se, aps);






ALTER TABLE ONLY "Municipio".alerta_mrj_zika
    ADD CONSTRAINT unique_zika_aps_se UNIQUE (se, aps);






ALTER TABLE ONLY forecast.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);






ALTER TABLE ONLY forecast.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);






ALTER TABLE ONLY forecast.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);






ALTER TABLE ONLY forecast.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);






ALTER TABLE ONLY forecast.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);






ALTER TABLE ONLY forecast.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);






ALTER TABLE ONLY forecast.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_upload_id_key UNIQUE (upload_id);






ALTER TABLE ONLY forecast.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);






ALTER TABLE ONLY forecast.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);






ALTER TABLE ONLY forecast.forecast_cases
    ADD CONSTRAINT forecast_cases_epiweek_geocode_cid10_forecast_model_id_publ_key UNIQUE (epiweek, geocode, cid10, forecast_model_id, published_date);






ALTER TABLE ONLY forecast.forecast_cases
    ADD CONSTRAINT forecast_cases_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.forecast_city
    ADD CONSTRAINT forecast_city_geocode_forecast_model_id_key UNIQUE (geocode, forecast_model_id);






ALTER TABLE ONLY forecast.forecast_city
    ADD CONSTRAINT forecast_city_pkey PRIMARY KEY (id);






ALTER TABLE ONLY forecast.forecast_model
    ADD CONSTRAINT forecast_model_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);






ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);






ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);






ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);






ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);






ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);






ALTER TABLE ONLY public.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_upload_id_key UNIQUE (upload_id);






ALTER TABLE ONLY public.dbf_dbf
    ADD CONSTRAINT dbf_dbf_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.dbf_dbfchunkedupload
    ADD CONSTRAINT dbf_dbfchunkedupload_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.dbf_dbfchunkedupload
    ADD CONSTRAINT dbf_dbfchunkedupload_upload_id_key UNIQUE (upload_id);






ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);






ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);






ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);






ALTER TABLE ONLY weather.copernicus_brasil
    ADD CONSTRAINT copernicus_brasil_pkey PRIMARY KEY (date, geocodigo);






ALTER TABLE ONLY weather.copernicus_foz_do_iguacu
    ADD CONSTRAINT copernicus_foz_do_iguacu_pkey PRIMARY KEY (index);






CREATE INDEX "Municipio_idx_gc" ON "Dengue_global"."Municipio" USING btree (geocodigo);






CREATE INDEX "Municipio_idx_n" ON "Dengue_global"."Municipio" USING btree (nome);






CREATE INDEX estado_idx_gc ON "Dengue_global".estado USING btree (geocodigo);













CREATE INDEX parameters_idx_gc ON "Dengue_global".parameters USING btree (municipio_geocodigo);







CREATE INDEX "Dengue_idx_data" ON "Municipio"."Notificacao" USING btree (dt_notific DESC, se_notif DESC);






CREATE INDEX notificacao_cid10_idx ON "Municipio"."Notificacao" USING btree (cid10_codigo);






CREATE INDEX auth_group_name_a6ea08ec_like ON forecast.auth_group USING btree (name varchar_pattern_ops);






CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON forecast.auth_group_permissions USING btree (group_id);






CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON forecast.auth_group_permissions USING btree (permission_id);






CREATE INDEX auth_permission_content_type_id_2f476e4b ON forecast.auth_permission USING btree (content_type_id);






CREATE INDEX auth_user_groups_group_id_97559544 ON forecast.auth_user_groups USING btree (group_id);






CREATE INDEX auth_user_groups_user_id_6a12ed8b ON forecast.auth_user_groups USING btree (user_id);






CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON forecast.auth_user_user_permissions USING btree (permission_id);






CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON forecast.auth_user_user_permissions USING btree (user_id);






CREATE INDEX auth_user_username_6821ab7c_like ON forecast.auth_user USING btree (username varchar_pattern_ops);






CREATE INDEX chunked_upload_chunkedupload_upload_id_23703435_like ON forecast.chunked_upload_chunkedupload USING btree (upload_id varchar_pattern_ops);






CREATE INDEX chunked_upload_chunkedupload_user_id_70ff6dbf ON forecast.chunked_upload_chunkedupload USING btree (user_id);






CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON forecast.django_admin_log USING btree (content_type_id);






CREATE INDEX django_admin_log_user_id_c564eba6 ON forecast.django_admin_log USING btree (user_id);






CREATE INDEX django_session_expire_date_a5c62663 ON forecast.django_session USING btree (expire_date);






CREATE INDEX django_session_session_key_c0390e0f_like ON forecast.django_session USING btree (session_key varchar_pattern_ops);






CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);






CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);






CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);






CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);






CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);






CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);






CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);






CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);






CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);






CREATE INDEX chunked_upload_chunkedupload_upload_id_23703435_like ON public.chunked_upload_chunkedupload USING btree (upload_id varchar_pattern_ops);






CREATE INDEX chunked_upload_chunkedupload_user_id_70ff6dbf ON public.chunked_upload_chunkedupload USING btree (user_id);






CREATE INDEX dbf_dbf_uploaded_by_id_ad662eb4 ON public.dbf_dbf USING btree (uploaded_by_id);






CREATE INDEX dbf_dbfchunkedupload_upload_id_e3989f45_like ON public.dbf_dbfchunkedupload USING btree (upload_id varchar_pattern_ops);






CREATE INDEX dbf_dbfchunkedupload_user_id_c7cc2beb ON public.dbf_dbfchunkedupload USING btree (user_id);






CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);






CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);






CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);






CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);






CREATE INDEX uf_total_chik_view_data_idx ON public.uf_total_chik_view USING btree (data);






CREATE INDEX uf_total_view_data_idx ON public.uf_total_view USING btree (data);






CREATE INDEX uf_total_zika_view_data_idx ON public.uf_total_zika_view USING btree (data);






ALTER TABLE ONLY forecast.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES forecast.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY forecast.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES forecast.auth_group(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY forecast.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES forecast.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY forecast.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES forecast.auth_group(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY forecast.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES forecast.auth_user(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY forecast.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES forecast.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY forecast.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES forecast.auth_user(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY forecast.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_user_id_70ff6dbf_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES forecast.auth_user(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY forecast.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES forecast.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY forecast.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES forecast.auth_user(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY forecast.forecast_cases
    ADD CONSTRAINT forecast_cases_cid10_fkey FOREIGN KEY (cid10) REFERENCES "Dengue_global"."CID10"(codigo);






ALTER TABLE ONLY forecast.forecast_cases
    ADD CONSTRAINT forecast_cases_forecast_model_id_fkey FOREIGN KEY (forecast_model_id) REFERENCES forecast.forecast_model(id);






ALTER TABLE ONLY forecast.forecast_cases
    ADD CONSTRAINT forecast_cases_geocode_fkey FOREIGN KEY (geocode) REFERENCES "Dengue_global"."Municipio"(geocodigo);






ALTER TABLE ONLY forecast.forecast_city
    ADD CONSTRAINT forecast_city_forecast_model_id_fkey FOREIGN KEY (forecast_model_id) REFERENCES forecast.forecast_model(id);






ALTER TABLE ONLY forecast.forecast_city
    ADD CONSTRAINT forecast_city_geocode_fkey FOREIGN KEY (geocode) REFERENCES "Dengue_global"."Municipio"(geocodigo);






ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;






ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


ALTER TABLE ONLY public.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_user_id_70ff6dbf_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


ALTER TABLE ONLY public.dbf_dbf
    ADD CONSTRAINT dbf_dbf_uploaded_by_id_ad662eb4_fk_auth_user_id FOREIGN KEY (uploaded_by_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


ALTER TABLE ONLY public.dbf_dbfchunkedupload
    ADD CONSTRAINT dbf_dbfchunkedupload_user_id_c7cc2beb_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


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


GRANT SELECT ON TABLE "Municipio"."Notificacao__20220806" TO infodenguedev;


GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Notificacao_id_seq" TO dengue;


GRANT ALL ON TABLE "Municipio".alerta_mrj TO dengue;
GRANT SELECT ON TABLE "Municipio".alerta_mrj TO infodenguedev;


GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLE "Municipio".alerta_mrj_chik TO "Dengue";
GRANT ALL ON TABLE "Municipio".alerta_mrj_chik TO dengue;
GRANT SELECT ON TABLE "Municipio".alerta_mrj_chik TO infodenguedev;


GRANT SELECT,USAGE ON SEQUENCE "Municipio".alerta_mrj_chik_id_seq TO dengue;


GRANT SELECT,USAGE ON SEQUENCE "Municipio".alerta_mrj_id_seq TO dengue;


GRANT ALL ON TABLE "Municipio".alerta_mrj_zika TO dengue;
GRANT SELECT ON TABLE "Municipio".alerta_mrj_zika TO infodenguedev;


GRANT SELECT,USAGE ON SEQUENCE "Municipio".alerta_mrj_zika_id_seq TO dengue;


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
