--
-- PostgreSQL database dump
--

-- Dumped from database version 15.3 (Ubuntu 15.3-0ubuntu0.23.04.1)
-- Dumped by pg_dump version 15.3 (Ubuntu 15.3-0ubuntu0.23.04.1)

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

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: dengueadmin
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO dengueadmin;

--
-- Name: topology; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA topology;


ALTER SCHEMA topology OWNER TO postgres;

--
-- Name: SCHEMA topology; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA topology IS 'PostGIS Topology schema';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry, geography, and raster spatial types and functions';


--
-- Name: postgis_raster; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_raster WITH SCHEMA public;


--
-- Name: EXTENSION postgis_raster; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_raster IS 'PostGIS raster types and functions';


--
-- Name: postgis_topology; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;


--
-- Name: EXTENSION postgis_topology; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_topology IS 'PostGIS topology spatial types and functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: DengueConfirmados_2013; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public."DengueConfirmados_2013" (
    "PK_UID" integer NOT NULL,
    nu_notific character varying(7),
    coord_x double precision,
    coord_y double precision,
    tp_not character varying(1),
    id_agravo character varying(4),
    dt_notific date,
    sem_not character varying(6),
    nu_ano character varying(4),
    id_unidade character varying(7),
    dt_sin_pri date,
    sem_pri character varying(6),
    cs_raca character varying(1),
    cs_escol_n character varying(2),
    id_cns_sus character varying(15),
    id_distrit character varying(9),
    nduplic_n character varying(1),
    dt_digita date,
    dt_transus date,
    dt_transdm date,
    dt_transsm date,
    dt_transrm date,
    dt_transrs date,
    dt_transse date,
    nu_lote_v character varying(7),
    nu_lote_h character varying(7),
    cs_flxret character varying(1),
    flxrecebi character varying(7),
    ident_micr character varying(50),
    migrado_w character varying(1),
    dt_invest date,
    id_ocupa_n character varying(6),
    dt_soro date,
    resul_soro character varying(1),
    histopa_n character varying(1),
    dt_viral date,
    resul_vi_n character varying(1),
    sorotipo character varying(1),
    imunoh_n character varying(1),
    dt_pcr date,
    resul_pcr_field character varying(1),
    dt_ns1 date,
    resul_ns1 character varying(1),
    coufinf character varying(2),
    copaisinf character varying(4),
    comuninf character varying(6),
    codisinf character varying(4),
    co_bainf character varying(8),
    nobaiinf character varying(60),
    doenca_tra character varying(1),
    epistaxe character varying(1),
    gengivo character varying(1),
    metro character varying(1),
    petequias character varying(1),
    hematura character varying(1),
    sangram character varying(1),
    laco_n character varying(1),
    plasmatico character varying(1),
    evidencia character varying(1),
    plaq_menor double precision,
    nu_lote_i character varying(9),
    tp_sistema character varying(1),
    geom public.geometry(Point)
);


ALTER TABLE public."DengueConfirmados_2013" OWNER TO dengueadmin;

--
-- Name: Dengue_2010; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public."Dengue_2010" (
    "PK_UID" integer NOT NULL,
    nu_notif character varying(7),
    x character varying(20),
    y character varying(20),
    tp_not character varying(1),
    id_agravo character varying(4),
    dt_notific date,
    sem_not character varying(6),
    nu_ano character varying(4),
    sg_uf_not character varying(2),
    id_unidade character varying(7),
    dt_sin_pri date,
    sem_pri character varying(6),
    cs_raca character varying(1),
    cs_escol_n character varying(2),
    id_cns_sus character varying(15),
    sg_uf character varying(2),
    nduplic_n character varying(1),
    dt_digita date,
    dt_transus date,
    dt_transdm date,
    dt_transsm date,
    dt_transrm date,
    dt_transrs date,
    dt_transse date,
    nu_lote_v character varying(7),
    nu_lote_h character varying(7),
    cs_flxret character varying(1),
    flxrecebi character varying(1),
    ident_micr character varying(50),
    migrado_w character varying(1),
    dt_invest date,
    id_ocupa_n character varying(6),
    dt_soro date,
    resul_soro character varying(1),
    dt_ns1 date,
    resul_ns1 character varying(1),
    dt_viral date,
    resul_vi_n character varying(1),
    dt_pcr date,
    resul_pcr_field character varying(1),
    sorotipo character varying(1),
    histopa_n character varying(1),
    imunoh_n character varying(1),
    coufinf character varying(2),
    copaisinf character varying(4),
    comuninf character varying(6),
    codisinf character varying(4),
    doenca_tra character varying(1),
    epistaxe character varying(1),
    gengivo character varying(1),
    metro character varying(1),
    petequias character varying(1),
    hematura character varying(1),
    sangram character varying(1),
    laco_n character varying(1),
    plasmatico character varying(1),
    evidencia character varying(1),
    plaq_menor double precision,
    tp_sistema character varying(1),
    fid_field integer,
    geom public.geometry(Point)
);


ALTER TABLE public."Dengue_2010" OWNER TO dengueadmin;

--
-- Name: Dengue_2011; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public."Dengue_2011" (
    "PK_UID" integer NOT NULL,
    nu_notif character varying(7),
    tp_not character varying(1),
    id_agravo character varying(4),
    dt_notific date,
    sem_not character varying(6),
    nu_ano character varying(4),
    sg_uf_not character varying(2),
    id_unidade character varying(7),
    dt_sin_pri date,
    sem_pri character varying(6),
    cs_raca character varying(1),
    cs_escol_n character varying(2),
    id_cns_sus character varying(15),
    sg_uf character varying(2),
    nduplic_n character varying(1),
    dt_digita date,
    dt_transus date,
    dt_transdm date,
    dt_transsm date,
    dt_transrm date,
    dt_transrs date,
    dt_transse date,
    nu_lote_v character varying(7),
    nu_lote_h character varying(7),
    cs_flxret character varying(1),
    flxrecebi character varying(1),
    ident_micr character varying(50),
    migrado_w character varying(1),
    dt_invest date,
    id_ocupa_n character varying(6),
    dt_soro date,
    resul_soro character varying(1),
    dt_ns1 date,
    resul_ns1 character varying(1),
    dt_viral date,
    resul_vi_n character varying(1),
    dt_pcr date,
    resul_pcr_field character varying(1),
    sorotipo character varying(1),
    histopa_n character varying(1),
    imunoh_n character varying(1),
    coufinf character varying(2),
    copaisinf character varying(4),
    comuninf character varying(6),
    codisinf character varying(4),
    co_bainf character varying(8),
    nobaiinf character varying(60),
    doenca_tra character varying(1),
    epistaxe character varying(1),
    gengivo character varying(1),
    metro character varying(1),
    petequias character varying(1),
    hematura character varying(1),
    sangram character varying(1),
    laco_n character varying(1),
    plasmatico character varying(1),
    evidencia character varying(1),
    plaq_menor double precision,
    uf character varying(2),
    municipio character varying(6),
    nu_lote_i character varying(7),
    tp_sistema character varying(1),
    x character varying(20),
    y character varying(20),
    geom public.geometry(Point)
);


ALTER TABLE public."Dengue_2011" OWNER TO dengueadmin;

--
-- Name: Dengue_2012; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public."Dengue_2012" (
    "PK_UID" integer NOT NULL,
    nu_notific character varying(7),
    status_r character varying(14),
    coord_x double precision,
    coord_y double precision,
    tp_not character varying(1),
    id_agravo character varying(4),
    dt_notific date,
    sem_not character varying(6),
    nu_ano character varying(4),
    sg_uf_not character varying(2),
    id_unidade character varying(7),
    dt_sin_pri date,
    sem_pri character varying(6),
    cs_raca character varying(1),
    cs_escol_n character varying(2),
    id_cns_sus character varying(15),
    sg_uf character varying(2),
    nduplic_n character varying(1),
    dt_digita date,
    dt_transus date,
    dt_transdm date,
    dt_transsm date,
    dt_transrm date,
    dt_transrs date,
    dt_transse date,
    nu_lote_v character varying(7),
    nu_lote_h character varying(7),
    cs_flxret character varying(1),
    flxrecebi character varying(7),
    ident_micr character varying(50),
    migrado_w character varying(1),
    dt_invest date,
    id_ocupa_n character varying(6),
    dt_soro date,
    resul_soro character varying(1),
    histopa_n character varying(1),
    dt_viral date,
    resul_vi_n character varying(1),
    sorotipo character varying(1),
    imunoh_n character varying(1),
    dt_pcr date,
    resul_pcr_field character varying(1),
    dt_ns1 date,
    resul_ns1 character varying(1),
    coufinf character varying(2),
    copaisinf character varying(4),
    doenca_tra character varying(1),
    epistaxe character varying(1),
    gengivo character varying(1),
    metro character varying(1),
    petequias character varying(1),
    hematura character varying(1),
    sangram character varying(1),
    laco_n character varying(1),
    plasmatico character varying(1),
    plaq_menor double precision,
    uf character varying(2),
    municipio character varying(6),
    nu_lote_i character varying(9),
    tp_sistema character varying(1),
    geom public.geometry(Point)
);


ALTER TABLE public."Dengue_2012" OWNER TO dengueadmin;

--
-- Name: Dengue_2013; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public."Dengue_2013" (
    "PK_UID" integer NOT NULL,
    nu_notific character varying(7),
    coord_x double precision,
    coord_y double precision,
    tp_not character varying(1),
    id_agravo character varying(4),
    dt_notific date,
    sem_not character varying(6),
    nu_ano character varying(4),
    sg_uf_not character varying(2),
    dt_sin_pri date,
    sem_pri character varying(6),
    cs_raca character varying(1),
    cs_escol_n character varying(2),
    id_cns_sus character varying(15),
    nduplic_n character varying(1),
    dt_digita date,
    dt_transus date,
    dt_transdm date,
    dt_transsm date,
    dt_transrm date,
    dt_transrs date,
    dt_transse date,
    nu_lote_v character varying(7),
    nu_lote_h character varying(7),
    cs_flxret character varying(1),
    flxrecebi character varying(7),
    ident_micr character varying(50),
    migrado_w character varying(1),
    dt_invest date,
    id_ocupa_n character varying(6),
    dt_soro date,
    resul_soro character varying(1),
    histopa_n character varying(1),
    dt_viral date,
    resul_vi_n character varying(1),
    sorotipo character varying(1),
    imunoh_n character varying(1),
    dt_pcr date,
    resul_pcr_field character varying(1),
    dt_ns1 date,
    resul_ns1 character varying(1),
    doenca_tra character varying(1),
    epistaxe character varying(1),
    gengivo character varying(1),
    metro character varying(1),
    petequias character varying(1),
    hematura character varying(1),
    sangram character varying(1),
    laco_n character varying(1),
    plasmatico character varying(1),
    evidencia character varying(1),
    plaq_menor double precision,
    nu_lote_i character varying(9),
    tp_sistema character varying(1),
    geom public.geometry(Point)
);


ALTER TABLE public."Dengue_2013" OWNER TO dengueadmin;

--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO dengueadmin;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_id_seq OWNER TO dengueadmin;

--
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.auth_group_id_seq OWNED BY public.auth_group.id;


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.auth_group_permissions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO dengueadmin;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_permissions_id_seq OWNER TO dengueadmin;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.auth_group_permissions_id_seq OWNED BY public.auth_group_permissions.id;


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO dengueadmin;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_permission_id_seq OWNER TO dengueadmin;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.auth_permission_id_seq OWNED BY public.auth_permission.id;


--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: dengueadmin
--

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

--
-- Name: auth_user_groups; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.auth_user_groups (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.auth_user_groups OWNER TO dengueadmin;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.auth_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_groups_id_seq OWNER TO dengueadmin;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.auth_user_groups_id_seq OWNED BY public.auth_user_groups.id;


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_id_seq OWNER TO dengueadmin;

--
-- Name: auth_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.auth_user_id_seq OWNED BY public.auth_user.id;


--
-- Name: auth_user_user_permissions; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.auth_user_user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_user_user_permissions OWNER TO dengueadmin;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.auth_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_user_permissions_id_seq OWNER TO dengueadmin;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.auth_user_user_permissions_id_seq OWNED BY public.auth_user_user_permissions.id;


--
-- Name: chunked_upload_chunkedupload; Type: TABLE; Schema: public; Owner: dengueadmin
--

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

--
-- Name: chunked_upload_chunkedupload_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.chunked_upload_chunkedupload_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.chunked_upload_chunkedupload_id_seq OWNER TO dengueadmin;

--
-- Name: chunked_upload_chunkedupload_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.chunked_upload_chunkedupload_id_seq OWNED BY public.chunked_upload_chunkedupload.id;


--
-- Name: dbf_dbf; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.dbf_dbf (
    id integer NOT NULL,
    file character varying(100) NOT NULL,
    uploaded_at timestamp with time zone NOT NULL,
    export_date date NOT NULL,
    notification_year integer NOT NULL,
    uploaded_by_id integer NOT NULL,
    abbreviation character varying(2),
    municipio character varying(255) NOT NULL
);


ALTER TABLE public.dbf_dbf OWNER TO dengueadmin;

--
-- Name: dbf_dbf_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.dbf_dbf_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dbf_dbf_id_seq OWNER TO dengueadmin;

--
-- Name: dbf_dbf_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.dbf_dbf_id_seq OWNED BY public.dbf_dbf.id;


--
-- Name: dbf_dbfchunkedupload; Type: TABLE; Schema: public; Owner: dengueadmin
--

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

--
-- Name: dbf_dbfchunkedupload_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.dbf_dbfchunkedupload_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dbf_dbfchunkedupload_id_seq OWNER TO dengueadmin;

--
-- Name: dbf_dbfchunkedupload_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.dbf_dbfchunkedupload_id_seq OWNED BY public.dbf_dbfchunkedupload.id;


--
-- Name: dbf_sendtopartner; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.dbf_sendtopartner (
    id integer NOT NULL,
    geocode character varying(7) NOT NULL,
    name character varying(50) NOT NULL,
    state_abbreviation character varying(5) NOT NULL,
    level character varying(10) NOT NULL,
    contact character varying(50) NOT NULL,
    email character varying(50) NOT NULL,
    status boolean NOT NULL
);


ALTER TABLE public.dbf_sendtopartner OWNER TO dengueadmin;

--
-- Name: dbf_sendtopartner_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.dbf_sendtopartner_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dbf_sendtopartner_id_seq OWNER TO dengueadmin;

--
-- Name: dbf_sendtopartner_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.dbf_sendtopartner_id_seq OWNED BY public.dbf_sendtopartner.id;


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: dengueadmin
--

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

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_admin_log_id_seq OWNER TO dengueadmin;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.django_admin_log_id_seq OWNED BY public.django_admin_log.id;


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO dengueadmin;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_content_type_id_seq OWNER TO dengueadmin;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.django_content_type_id_seq OWNED BY public.django_content_type.id;


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_migrations (
    id integer NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO dengueadmin;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_migrations_id_seq OWNER TO dengueadmin;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.django_migrations_id_seq OWNED BY public.django_migrations.id;


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO dengueadmin;

--
-- Name: auth_group id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group ALTER COLUMN id SET DEFAULT nextval('public.auth_group_id_seq'::regclass);


--
-- Name: auth_group_permissions id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_group_permissions_id_seq'::regclass);


--
-- Name: auth_permission id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_permission ALTER COLUMN id SET DEFAULT nextval('public.auth_permission_id_seq'::regclass);


--
-- Name: auth_user id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user ALTER COLUMN id SET DEFAULT nextval('public.auth_user_id_seq'::regclass);


--
-- Name: auth_user_groups id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_groups ALTER COLUMN id SET DEFAULT nextval('public.auth_user_groups_id_seq'::regclass);


--
-- Name: auth_user_user_permissions id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_user_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_user_user_permissions_id_seq'::regclass);


--
-- Name: chunked_upload_chunkedupload id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.chunked_upload_chunkedupload ALTER COLUMN id SET DEFAULT nextval('public.chunked_upload_chunkedupload_id_seq'::regclass);


--
-- Name: dbf_dbf id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.dbf_dbf ALTER COLUMN id SET DEFAULT nextval('public.dbf_dbf_id_seq'::regclass);


--
-- Name: dbf_dbfchunkedupload id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.dbf_dbfchunkedupload ALTER COLUMN id SET DEFAULT nextval('public.dbf_dbfchunkedupload_id_seq'::regclass);


--
-- Name: dbf_sendtopartner id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.dbf_sendtopartner ALTER COLUMN id SET DEFAULT nextval('public.dbf_sendtopartner_id_seq'::regclass);


--
-- Name: django_admin_log id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_admin_log ALTER COLUMN id SET DEFAULT nextval('public.django_admin_log_id_seq'::regclass);


--
-- Name: django_content_type id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_content_type ALTER COLUMN id SET DEFAULT nextval('public.django_content_type_id_seq'::regclass);


--
-- Name: django_migrations id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_migrations ALTER COLUMN id SET DEFAULT nextval('public.django_migrations_id_seq'::regclass);


--
-- Name: DengueConfirmados_2013 DengueConfirmados_2013_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public."DengueConfirmados_2013"
    ADD CONSTRAINT "DengueConfirmados_2013_pkey" PRIMARY KEY ("PK_UID");


--
-- Name: Dengue_2010 Dengue_2010_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public."Dengue_2010"
    ADD CONSTRAINT "Dengue_2010_pkey" PRIMARY KEY ("PK_UID");


--
-- Name: Dengue_2011 Dengue_2011_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public."Dengue_2011"
    ADD CONSTRAINT "Dengue_2011_pkey" PRIMARY KEY ("PK_UID");


--
-- Name: Dengue_2012 Dengue_2012_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public."Dengue_2012"
    ADD CONSTRAINT "Dengue_2012_pkey" PRIMARY KEY ("PK_UID");


--
-- Name: Dengue_2013 Dengue_2013_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public."Dengue_2013"
    ADD CONSTRAINT "Dengue_2013_pkey" PRIMARY KEY ("PK_UID");


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_user_id_94350c0c_uniq; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_94350c0c_uniq UNIQUE (user_id, group_id);


--
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_14a6b632_uniq; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_14a6b632_uniq UNIQUE (user_id, permission_id);


--
-- Name: auth_user auth_user_username_key; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);


--
-- Name: chunked_upload_chunkedupload chunked_upload_chunkedupload_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_pkey PRIMARY KEY (id);


--
-- Name: chunked_upload_chunkedupload chunked_upload_chunkedupload_upload_id_key; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_upload_id_key UNIQUE (upload_id);


--
-- Name: dbf_dbf dbf_dbf_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.dbf_dbf
    ADD CONSTRAINT dbf_dbf_pkey PRIMARY KEY (id);


--
-- Name: dbf_dbfchunkedupload dbf_dbfchunkedupload_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.dbf_dbfchunkedupload
    ADD CONSTRAINT dbf_dbfchunkedupload_pkey PRIMARY KEY (id);


--
-- Name: dbf_dbfchunkedupload dbf_dbfchunkedupload_upload_id_key; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.dbf_dbfchunkedupload
    ADD CONSTRAINT dbf_dbfchunkedupload_upload_id_key UNIQUE (upload_id);


--
-- Name: dbf_sendtopartner dbf_sendtopartner_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.dbf_sendtopartner
    ADD CONSTRAINT dbf_sendtopartner_pkey PRIMARY KEY (id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: DengueConfirmados_2013_geom_id; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX "DengueConfirmados_2013_geom_id" ON public."DengueConfirmados_2013" USING gist (geom);


--
-- Name: Dengue_2010_geom_id; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX "Dengue_2010_geom_id" ON public."Dengue_2010" USING gist (geom);


--
-- Name: Dengue_2011_geom_id; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX "Dengue_2011_geom_id" ON public."Dengue_2011" USING gist (geom);


--
-- Name: Dengue_2012_geom_id; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX "Dengue_2012_geom_id" ON public."Dengue_2012" USING gist (geom);


--
-- Name: Dengue_2013_geom_id; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX "Dengue_2013_geom_id" ON public."Dengue_2013" USING gist (geom);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_0e939a4f; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_group_permissions_0e939a4f ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_8373b171; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_group_permissions_8373b171 ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_417f1b1c; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_permission_417f1b1c ON public.auth_permission USING btree (content_type_id);


--
-- Name: auth_user_groups_0e939a4f; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_user_groups_0e939a4f ON public.auth_user_groups USING btree (group_id);


--
-- Name: auth_user_groups_e8701ad4; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_user_groups_e8701ad4 ON public.auth_user_groups USING btree (user_id);


--
-- Name: auth_user_user_permissions_8373b171; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_user_user_permissions_8373b171 ON public.auth_user_user_permissions USING btree (permission_id);


--
-- Name: auth_user_user_permissions_e8701ad4; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_user_user_permissions_e8701ad4 ON public.auth_user_user_permissions USING btree (user_id);


--
-- Name: auth_user_username_6821ab7c_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);


--
-- Name: chunked_upload_chunkedupload_upload_id_23703435_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX chunked_upload_chunkedupload_upload_id_23703435_like ON public.chunked_upload_chunkedupload USING btree (upload_id varchar_pattern_ops);


--
-- Name: chunked_upload_chunkedupload_user_id_70ff6dbf; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX chunked_upload_chunkedupload_user_id_70ff6dbf ON public.chunked_upload_chunkedupload USING btree (user_id);


--
-- Name: dbf_dbf_4095e96b; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX dbf_dbf_4095e96b ON public.dbf_dbf USING btree (uploaded_by_id);


--
-- Name: dbf_dbfchunkedupload_e8701ad4; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX dbf_dbfchunkedupload_e8701ad4 ON public.dbf_dbfchunkedupload USING btree (user_id);


--
-- Name: dbf_dbfchunkedupload_upload_id_e3989f45_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX dbf_dbfchunkedupload_upload_id_e3989f45_like ON public.dbf_dbfchunkedupload USING btree (upload_id varchar_pattern_ops);


--
-- Name: django_admin_log_417f1b1c; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_admin_log_417f1b1c ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_e8701ad4; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_admin_log_e8701ad4 ON public.django_admin_log USING btree (user_id);


--
-- Name: django_session_de54fa62; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_session_de54fa62 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: auth_group_permissions auth_group_permiss_permission_id_84c5c92e_fk_auth_permission_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permiss_permission_id_84c5c92e_fk_auth_permission_id FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permiss_content_type_id_2f476e4b_fk_django_content_type_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permiss_content_type_id_2f476e4b_fk_django_content_type_id FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_group_id_97559544_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_user_id_6a12ed8b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_per_permission_id_1fbb5f2c_fk_auth_permission_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_per_permission_id_1fbb5f2c_fk_auth_permission_id FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: chunked_upload_chunkedupload chunked_upload_chunkedupload_user_id_70ff6dbf_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_user_id_70ff6dbf_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dbf_dbf dbf_dbf_uploaded_by_id_ad662eb4_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.dbf_dbf
    ADD CONSTRAINT dbf_dbf_uploaded_by_id_ad662eb4_fk_auth_user_id FOREIGN KEY (uploaded_by_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dbf_dbfchunkedupload dbf_dbfchunkedupload_user_id_c7cc2beb_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.dbf_dbfchunkedupload
    ADD CONSTRAINT dbf_dbfchunkedupload_user_id_c7cc2beb_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_content_type_id_c4bce8eb_fk_django_content_type_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_content_type_id_c4bce8eb_fk_django_content_type_id FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: dengueadmin
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- Name: TABLE geometry_columns; Type: ACL; Schema: public; Owner: dengueadmin
--

REVOKE SELECT ON TABLE public.geometry_columns FROM PUBLIC;
GRANT ALL ON TABLE public.geometry_columns TO PUBLIC;


--
-- Name: TABLE raster_columns; Type: ACL; Schema: public; Owner: dengueadmin
--

REVOKE SELECT ON TABLE public.raster_columns FROM PUBLIC;
GRANT ALL ON TABLE public.raster_columns TO PUBLIC;


--
-- Name: TABLE raster_overviews; Type: ACL; Schema: public; Owner: dengueadmin
--

REVOKE SELECT ON TABLE public.raster_overviews FROM PUBLIC;
GRANT ALL ON TABLE public.raster_overviews TO PUBLIC;


--
-- Name: TABLE spatial_ref_sys; Type: ACL; Schema: public; Owner: dengueadmin
--

REVOKE SELECT ON TABLE public.spatial_ref_sys FROM PUBLIC;
GRANT ALL ON TABLE public.spatial_ref_sys TO PUBLIC;


--
-- PostgreSQL database dump complete
--
