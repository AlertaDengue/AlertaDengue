--
-- PostgreSQL database dump
--

-- Dumped from database version 14.6 (Debian 14.6-1.pgdg110+1)
-- Dumped by pg_dump version 15.1

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
-- Name: Dengue_global; Type: SCHEMA; Schema: -; Owner: Dengue
--

\c dengue

CREATE SCHEMA "Dengue_global";


ALTER SCHEMA "Dengue_global" OWNER TO "Dengue";

--
-- Name: Municipio; Type: SCHEMA; Schema: -; Owner: Dengue
--

CREATE SCHEMA "Municipio";


ALTER SCHEMA "Municipio" OWNER TO "Dengue";

--
-- Name: forecast; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA forecast;


ALTER SCHEMA forecast OWNER TO postgres;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: dengueadmin
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO dengueadmin;

--
-- Name: adminpack; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS adminpack WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION adminpack; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION adminpack IS 'administrative functions for PostgreSQL';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry, geography, and raster spatial types and functions';


--
-- Name: epi_week(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.epi_week(dt date) RETURNS integer
    LANGUAGE plpgsql
    AS $$

DECLARE epiyear INTEGER;
DECLARE epiend DATE;
DECLARE epistart DATE;
DECLARE epi_dow INTEGER;
DECLARE epiweek INTEGER;

BEGIN
    epiyear = EXTRACT(YEAR FROM dt);
    epiend = CONCAT(CAST(epiyear AS VARCHAR), '-12-31')::DATE;
    epi_dow = EXTRACT(DOW FROM epiend);

    -- Last epiday
    IF epi_dow < 3 THEN
        epiend = epiend - CAST(CAST(epi_dow+1 AS VARCHAR) || ' DAY' AS INTERVAL);
    ELSE
        epiend = epiend + CAST(CAST(6-epi_dow AS VARCHAR) || ' DAY' AS INTERVAL);
    END IF;

    IF dt > epiend THEN
        epiyear = epiyear + 1;
        RETURN epiyear*100 + 01;
    END IF;

    -- First epiday
    epistart = CONCAT(CAST(epiyear AS VARCHAR), '-01-01')::DATE;
    epi_dow = EXTRACT(DOW FROM epistart);

    IF epi_dow < 4 THEN
        epistart = epistart - CAST(CAST(epi_dow AS VARCHAR) || ' DAY' AS INTERVAL);
    ELSE
        epistart = epistart + CAST(CAST(7-epi_dow AS VARCHAR) || ' DAY' AS INTERVAL);
    END IF;

    -- If current date is before its year first epiweek,
    -- then our base year is the previous one
    IF dt < epistart THEN
    epiyear = epiyear-1;

    epistart = CONCAT(CAST(epiyear AS VARCHAR), '-01-01')::DATE;
        epi_dow = EXTRACT(DOW FROM epistart);

        -- First epiday
        IF epi_dow < 4 THEN
        epistart = epistart - CAST(CAST(epi_dow AS VARCHAR) || ' DAY' AS INTERVAL);
        ELSE
            epistart = epistart + CAST(CAST(7-epi_dow AS VARCHAR) || ' DAY' AS INTERVAL);
        END IF;
    END IF;
    --epiweek = int(((x - epistart)/7).days) + 1
    epiweek = ((dt - epistart)/7)+1;
    --raise notice '%', ((dt - epistart)/7)+1;

    RETURN epiyear*100 + epiweek;
END;
$$;


ALTER FUNCTION public.epi_week(dt date) OWNER TO postgres;

--
-- Name: epiweek2date(integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.epiweek2date(epi_year_week integer, weekday integer DEFAULT 0) RETURNS date
    LANGUAGE plpgsql
    AS $$

DECLARE epiyear INTEGER;
DECLARE epiweek INTEGER;
DECLARE date_1 DATE;
DECLARE date_1_w INTEGER;
DECLARE epiweek_day_1 DATE;
DECLARE epi_interval INTERVAL;

BEGIN
    IF epi_year_week < 190000 THEN
        RAISE EXCEPTION 'INVALID epi_year_week value.';
    END IF;
    
    epiyear = epi_year_week/100;
    epiweek = CAST((epi_year_week/100.0) % 1 * 100 AS INT);
    date_1 = CAST(epiyear::varchar || '-01-01' AS DATE);
    date_1_w = EXTRACT(DOW FROM date_1);

    IF date_1_w <=3 THEN
	epi_interval = (date_1_w::varchar || ' days')::interval;
        epiweek_day_1 = date_1 - epi_interval;
    ELSE
        epi_interval = ((7-date_1_w)::varchar || ' days')::interval;
	epiweek_day_1 = date_1 + epi_interval;
    END IF; 
    
    epi_interval = ((7 * (epiweek-1) + weekday) || ' days')::interval;
    RETURN epiweek_day_1 + epi_interval;
END;
$$;


ALTER FUNCTION public.epiweek2date(epi_year_week integer, weekday integer) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: CID10; Type: TABLE; Schema: Dengue_global; Owner: administrador
--

CREATE TABLE "Dengue_global"."CID10" (
    nome character varying(512) NOT NULL,
    codigo character varying(5) NOT NULL
);


ALTER TABLE "Dengue_global"."CID10" OWNER TO administrador;

--
-- Name: Municipio; Type: TABLE; Schema: Dengue_global; Owner: administrador
--

CREATE TABLE "Dengue_global"."Municipio" (
    geocodigo integer NOT NULL,
    nome character varying(128) NOT NULL,
    geojson text NOT NULL,
    populacao bigint NOT NULL,
    uf character varying(20) NOT NULL,
    id_regional integer
);


ALTER TABLE "Dengue_global"."Municipio" OWNER TO administrador;

--
-- Name: TABLE "Municipio"; Type: COMMENT; Schema: Dengue_global; Owner: administrador
--

COMMENT ON TABLE "Dengue_global"."Municipio" IS 'Municipio integrado ao sistema de alerta';


--
-- Name: alerta_regional_chik; Type: TABLE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE TABLE "Dengue_global".alerta_regional_chik (
    id bigint NOT NULL,
    id_regional integer NOT NULL,
    data_inise date NOT NULL,
    se integer NOT NULL,
    casos_est real,
    casos_est_min real,
    casos_est_max real,
    casos integer,
    p_rt1 real,
    p_inc100k real,
    uf character varying(2),
    nivel smallint,
    tweet numeric(5,0),
    rt numeric(5,0),
    pop numeric(7,0),
    tempmin numeric(4,0),
    tempmed numeric(4,0),
    tempmax numeric(4,0),
    umidmin numeric(4,0),
    umidmed numeric(4,0),
    umidmax numeric(4,0),
    receptivo smallint,
    transmissao smallint,
    nivel_inc smallint
);


ALTER TABLE "Dengue_global".alerta_regional_chik OWNER TO dengueadmin;

--
-- Name: alerta_regional_chik_id_seq; Type: SEQUENCE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE SEQUENCE "Dengue_global".alerta_regional_chik_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Dengue_global".alerta_regional_chik_id_seq OWNER TO dengueadmin;

--
-- Name: alerta_regional_chik_id_seq; Type: SEQUENCE OWNED BY; Schema: Dengue_global; Owner: dengueadmin
--

ALTER SEQUENCE "Dengue_global".alerta_regional_chik_id_seq OWNED BY "Dengue_global".alerta_regional_chik.id;


--
-- Name: alerta_regional_dengue; Type: TABLE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE TABLE "Dengue_global".alerta_regional_dengue (
    id bigint NOT NULL,
    id_regional integer NOT NULL,
    data_inise date NOT NULL,
    se integer NOT NULL,
    casos_est real,
    casos_est_min real,
    casos_est_max real,
    casos integer,
    p_rt1 real,
    p_inc100k real,
    uf character varying(2),
    nivel smallint,
    tweet numeric(5,0),
    rt numeric(5,0),
    pop numeric(7,0),
    tempmin numeric(4,0),
    tempmed numeric(4,0),
    tempmax numeric(4,0),
    umidmin numeric(4,0),
    umidmed numeric(4,0),
    umidmax numeric(4,0),
    receptivo smallint,
    transmissao smallint,
    nivel_inc smallint
);


ALTER TABLE "Dengue_global".alerta_regional_dengue OWNER TO dengueadmin;

--
-- Name: alerta_regional_dengue_id_seq; Type: SEQUENCE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE SEQUENCE "Dengue_global".alerta_regional_dengue_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Dengue_global".alerta_regional_dengue_id_seq OWNER TO dengueadmin;

--
-- Name: alerta_regional_dengue_id_seq; Type: SEQUENCE OWNED BY; Schema: Dengue_global; Owner: dengueadmin
--

ALTER SEQUENCE "Dengue_global".alerta_regional_dengue_id_seq OWNED BY "Dengue_global".alerta_regional_dengue.id;


--
-- Name: alerta_regional_zika; Type: TABLE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE TABLE "Dengue_global".alerta_regional_zika (
    id bigint NOT NULL,
    id_regional integer NOT NULL,
    data_inise date NOT NULL,
    se integer NOT NULL,
    casos_est real,
    casos_est_min real,
    casos_est_max real,
    casos integer,
    p_rt1 real,
    p_inc100k real,
    uf character varying(2),
    nivel smallint,
    tweet numeric(5,0),
    rt numeric(5,0),
    pop numeric(7,0),
    tempmin numeric(4,0),
    tempmed numeric(4,0),
    tempmax numeric(4,0),
    umidmin numeric(4,0),
    umidmed numeric(4,0),
    umidmax numeric(4,0),
    receptivo smallint,
    transmissao smallint,
    nivel_inc smallint
);


ALTER TABLE "Dengue_global".alerta_regional_zika OWNER TO dengueadmin;

--
-- Name: alerta_regional_zika_id_seq; Type: SEQUENCE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE SEQUENCE "Dengue_global".alerta_regional_zika_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Dengue_global".alerta_regional_zika_id_seq OWNER TO dengueadmin;

--
-- Name: alerta_regional_zika_id_seq; Type: SEQUENCE OWNED BY; Schema: Dengue_global; Owner: dengueadmin
--

ALTER SEQUENCE "Dengue_global".alerta_regional_zika_id_seq OWNED BY "Dengue_global".alerta_regional_zika.id;


--
-- Name: estado; Type: TABLE; Schema: Dengue_global; Owner: administrador
--

CREATE TABLE "Dengue_global".estado (
    nome character varying(128) NOT NULL,
    geojson text NOT NULL,
    regiao character varying(32) NOT NULL,
    uf character varying(2) NOT NULL,
    geocodigo integer NOT NULL
);


ALTER TABLE "Dengue_global".estado OWNER TO administrador;

--
-- Name: macroregional; Type: TABLE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE TABLE "Dengue_global".macroregional (
    id integer NOT NULL,
    nome character varying(255) NOT NULL,
    codigo integer NOT NULL,
    uf character varying(2)
);


ALTER TABLE "Dengue_global".macroregional OWNER TO dengueadmin;

--
-- Name: macroregional_id_seq; Type: SEQUENCE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE SEQUENCE "Dengue_global".macroregional_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Dengue_global".macroregional_id_seq OWNER TO dengueadmin;

--
-- Name: macroregional_id_seq; Type: SEQUENCE OWNED BY; Schema: Dengue_global; Owner: dengueadmin
--

ALTER SEQUENCE "Dengue_global".macroregional_id_seq OWNED BY "Dengue_global".macroregional.id;


--
-- Name: parameters; Type: TABLE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE TABLE "Dengue_global".parameters (
    "row.names" text,
    municipio_geocodigo integer NOT NULL,
    limiar_preseason double precision,
    limiar_posseason double precision,
    limiar_epidemico double precision,
    varcli text,
    clicrit numeric(5,0) DEFAULT NULL::numeric,
    cid10 character varying DEFAULT NULL::bpchar,
    codmodelo character varying,
    varcli2 character varying(16) DEFAULT NULL::character varying,
    clicrit2 numeric(5,0) DEFAULT NULL::numeric,
    codigo_estacao_wu character varying,
    estacao_wu_sec character varying
);


ALTER TABLE "Dengue_global".parameters OWNER TO dengueadmin;

--
-- Name: regional; Type: TABLE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE TABLE "Dengue_global".regional (
    id integer NOT NULL,
    nome character varying(255) NOT NULL,
    codigo integer NOT NULL,
    id_macroregional integer NOT NULL
);


ALTER TABLE "Dengue_global".regional OWNER TO dengueadmin;

--
-- Name: regional_id_seq; Type: SEQUENCE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE SEQUENCE "Dengue_global".regional_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Dengue_global".regional_id_seq OWNER TO dengueadmin;

--
-- Name: regional_id_seq; Type: SEQUENCE OWNED BY; Schema: Dengue_global; Owner: dengueadmin
--

ALTER SEQUENCE "Dengue_global".regional_id_seq OWNED BY "Dengue_global".regional.id;


--
-- Name: regional_saude; Type: TABLE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE TABLE "Dengue_global".regional_saude (
    id integer NOT NULL,
    municipio_geocodigo integer,
    id_regional integer,
    codigo_estacao_wu character varying(16),
    nome_regional character varying(32),
    limiar_preseason real,
    limiar_posseason real,
    limiar_epidemico real,
    estacao_wu_sec character varying(10),
    varcli character varying(10),
    tcrit double precision,
    ucrit double precision,
    nome_macroreg character varying(32)
);


ALTER TABLE "Dengue_global".regional_saude OWNER TO dengueadmin;

--
-- Name: regional_saude_id_seq; Type: SEQUENCE; Schema: Dengue_global; Owner: dengueadmin
--

CREATE SEQUENCE "Dengue_global".regional_saude_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Dengue_global".regional_saude_id_seq OWNER TO dengueadmin;

--
-- Name: regional_saude_id_seq; Type: SEQUENCE OWNED BY; Schema: Dengue_global; Owner: dengueadmin
--

ALTER SEQUENCE "Dengue_global".regional_saude_id_seq OWNED BY "Dengue_global".regional_saude.id;


--
-- Name: Bairro; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Bairro" (
    nome text NOT NULL,
    bairro_id integer NOT NULL,
    "Localidade_id" integer NOT NULL
);


ALTER TABLE "Municipio"."Bairro" OWNER TO administrador;

--
-- Name: TABLE "Bairro"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Bairro" IS 'Lista de bairros por localidade';


--
-- Name: Clima_Satelite; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Clima_Satelite" (
    id bigint NOT NULL,
    data date NOT NULL,
    "Municipio_geocodigo" integer NOT NULL,
    ndvi integer NOT NULL,
    temperatura_max numeric(4,2) NOT NULL,
    temperaruta_min numeric(4,2) NOT NULL,
    precipitacao integer NOT NULL
);


ALTER TABLE "Municipio"."Clima_Satelite" OWNER TO administrador;

--
-- Name: TABLE "Clima_Satelite"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Clima_Satelite" IS 'Precipitação, temperatura e NVDI
(Normalized Difference Vegetation Index)';


--
-- Name: Clima_Satelite_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: administrador
--

CREATE SEQUENCE "Municipio"."Clima_Satelite_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio"."Clima_Satelite_id_seq" OWNER TO administrador;

--
-- Name: Clima_Satelite_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: administrador
--

ALTER SEQUENCE "Municipio"."Clima_Satelite_id_seq" OWNED BY "Municipio"."Clima_Satelite".id;


--
-- Name: Clima_cemaden; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Clima_cemaden" (
    valor real NOT NULL,
    sensor character varying(32) NOT NULL,
    id bigint NOT NULL,
    datahora timestamp without time zone NOT NULL,
    "Estacao_cemaden_codestacao" character varying(10) NOT NULL
);


ALTER TABLE "Municipio"."Clima_cemaden" OWNER TO administrador;

--
-- Name: TABLE "Clima_cemaden"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Clima_cemaden" IS 'dados de clima - CEMADEN';


--
-- Name: Clima_cemaden_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: administrador
--

CREATE SEQUENCE "Municipio"."Clima_cemaden_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio"."Clima_cemaden_id_seq" OWNER TO administrador;

--
-- Name: Clima_cemaden_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: administrador
--

ALTER SEQUENCE "Municipio"."Clima_cemaden_id_seq" OWNED BY "Municipio"."Clima_cemaden".id;


--
-- Name: Clima_wu; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Clima_wu" (
    temp_min real,
    temp_max real,
    temp_med real,
    data_dia date NOT NULL,
    umid_min real,
    umid_med real,
    umid_max real,
    pressao_min real,
    pressao_med real,
    pressao_max real,
    "Estacao_wu_estacao_id" character varying(4) NOT NULL,
    id bigint NOT NULL
);


ALTER TABLE "Municipio"."Clima_wu" OWNER TO administrador;

--
-- Name: TABLE "Clima_wu"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Clima_wu" IS 'série temporal de variaveis meteorologicas diarias do WU';


--
-- Name: Clima_wu_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: administrador
--

CREATE SEQUENCE "Municipio"."Clima_wu_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio"."Clima_wu_id_seq" OWNER TO administrador;

--
-- Name: Clima_wu_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: administrador
--

ALTER SEQUENCE "Municipio"."Clima_wu_id_seq" OWNED BY "Municipio"."Clima_wu".id;


--
-- Name: Estacao_cemaden; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Estacao_cemaden" (
    codestacao character varying(32) NOT NULL,
    nome character varying(128) NOT NULL,
    municipio character varying(128),
    uf character varying(2),
    latitude real NOT NULL,
    longitude real NOT NULL
);


ALTER TABLE "Municipio"."Estacao_cemaden" OWNER TO administrador;

--
-- Name: TABLE "Estacao_cemaden"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Estacao_cemaden" IS 'Metadados da estação do cemaden';


--
-- Name: Estacao_wu; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Estacao_wu" (
    estacao_id character varying(4) NOT NULL,
    latitude real NOT NULL,
    longitude real NOT NULL,
    "Localidades_id" integer,
    nome character varying(128) NOT NULL
);


ALTER TABLE "Municipio"."Estacao_wu" OWNER TO administrador;

--
-- Name: TABLE "Estacao_wu"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Estacao_wu" IS 'metadados das estacoes meteorologicas da WU';


--
-- Name: Historico_alerta; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Historico_alerta" (
    "data_iniSE" date NOT NULL,
    "SE" integer NOT NULL,
    casos_est real,
    casos_est_min integer,
    casos_est_max integer,
    casos integer,
    municipio_geocodigo integer NOT NULL,
    p_rt1 real,
    p_inc100k real,
    "Localidade_id" integer,
    nivel smallint,
    id bigint NOT NULL,
    versao_modelo character varying(40),
    municipio_nome character varying(128),
    tweet numeric(5,0) DEFAULT NULL::numeric,
    "Rt" numeric(5,0) DEFAULT NULL::numeric,
    pop numeric,
    tempmin numeric,
    umidmax numeric,
    receptivo smallint,
    transmissao smallint,
    nivel_inc smallint,
    umidmed numeric,
    umidmin numeric,
    tempmed numeric,
    tempmax numeric,
    casprov integer,
    casprov_est real,
    casprov_est_min integer,
    casprov_est_max integer,
    casconf integer
);


ALTER TABLE "Municipio"."Historico_alerta" OWNER TO administrador;

--
-- Name: TABLE "Historico_alerta"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Historico_alerta" IS 'Resultados  do alerta, conforme publicado.';


--
-- Name: Historico_alerta_chik; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Historico_alerta_chik" (
    "data_iniSE" date NOT NULL,
    "SE" integer NOT NULL,
    casos_est real,
    casos_est_min integer,
    casos_est_max integer,
    casos integer,
    municipio_geocodigo integer NOT NULL,
    p_rt1 real,
    p_inc100k real,
    "Localidade_id" integer,
    nivel smallint,
    id bigint NOT NULL,
    versao_modelo character varying(40),
    municipio_nome character varying(128),
    tweet numeric(5,0) DEFAULT NULL::numeric,
    "Rt" numeric(5,0) DEFAULT NULL::numeric,
    pop numeric,
    tempmin numeric,
    umidmax numeric,
    receptivo smallint,
    transmissao smallint,
    nivel_inc smallint,
    umidmed numeric,
    umidmin numeric,
    tempmed numeric,
    tempmax numeric,
    casprov integer,
    casprov_est real,
    casprov_est_min integer,
    casprov_est_max integer,
    casconf integer
);


ALTER TABLE "Municipio"."Historico_alerta_chik" OWNER TO administrador;

--
-- Name: TABLE "Historico_alerta_chik"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Historico_alerta_chik" IS 'Resultados  do alerta para chikungunya, conforme publicado.';


--
-- Name: Historico_alerta_chik_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: administrador
--

CREATE SEQUENCE "Municipio"."Historico_alerta_chik_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio"."Historico_alerta_chik_id_seq" OWNER TO administrador;

--
-- Name: Historico_alerta_chik_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: administrador
--

ALTER SEQUENCE "Municipio"."Historico_alerta_chik_id_seq" OWNED BY "Municipio"."Historico_alerta_chik".id;


--
-- Name: Historico_alerta_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: administrador
--

CREATE SEQUENCE "Municipio"."Historico_alerta_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio"."Historico_alerta_id_seq" OWNER TO administrador;

--
-- Name: Historico_alerta_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: administrador
--

ALTER SEQUENCE "Municipio"."Historico_alerta_id_seq" OWNED BY "Municipio"."Historico_alerta".id;


--
-- Name: Historico_alerta_zika; Type: TABLE; Schema: Municipio; Owner: postgres
--

CREATE TABLE "Municipio"."Historico_alerta_zika" (
    "data_iniSE" date NOT NULL,
    "SE" integer NOT NULL,
    casos_est real,
    casos_est_min integer,
    casos_est_max integer,
    casos integer,
    municipio_geocodigo integer NOT NULL,
    p_rt1 real,
    p_inc100k real,
    "Localidade_id" integer,
    nivel smallint,
    id bigint NOT NULL,
    versao_modelo character varying(40),
    municipio_nome character varying(128),
    tweet numeric(5,0) DEFAULT NULL::numeric,
    "Rt" numeric(5,0) DEFAULT NULL::numeric,
    pop numeric,
    tempmin numeric,
    umidmax numeric,
    receptivo smallint,
    transmissao smallint,
    nivel_inc smallint,
    umidmed numeric,
    umidmin numeric,
    tempmed numeric,
    tempmax numeric,
    casprov integer,
    casprov_est real,
    casprov_est_min integer,
    casprov_est_max integer,
    casconf integer
);


ALTER TABLE "Municipio"."Historico_alerta_zika" OWNER TO postgres;

--
-- Name: Historico_alerta_zika_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: postgres
--

CREATE SEQUENCE "Municipio"."Historico_alerta_zika_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio"."Historico_alerta_zika_id_seq" OWNER TO postgres;

--
-- Name: Historico_alerta_zika_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: postgres
--

ALTER SEQUENCE "Municipio"."Historico_alerta_zika_id_seq" OWNED BY "Municipio"."Historico_alerta_zika".id;


--
-- Name: Localidade; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Localidade" (
    nome character varying(32) NOT NULL,
    populacao integer NOT NULL,
    geojson text NOT NULL,
    id integer NOT NULL,
    "Municipio_geocodigo" integer NOT NULL,
    codigo_estacao_wu character varying(5) DEFAULT NULL::character varying
);


ALTER TABLE "Municipio"."Localidade" OWNER TO administrador;

--
-- Name: TABLE "Localidade"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Localidade" IS 'Sub-unidades de analise no municipio';


--
-- Name: Notificacao; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Notificacao" (
    id bigint NOT NULL,
    dt_notific date,
    se_notif integer,
    ano_notif integer,
    dt_sin_pri date,
    se_sin_pri integer,
    dt_digita date,
    municipio_geocodigo integer,
    nu_notific integer,
    cid10_codigo character varying(5),
    dt_nasc date,
    cs_sexo character varying(1),
    nu_idade_n integer,
    resul_pcr numeric,
    criterio numeric,
    classi_fin numeric
);


ALTER TABLE "Municipio"."Notificacao" OWNER TO administrador;

--
-- Name: TABLE "Notificacao"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Notificacao" IS 'Casos de notificacao de dengue';


--
-- Name: Notificacao__20220806; Type: TABLE; Schema: Municipio; Owner: dengueadmin
--

CREATE TABLE "Municipio"."Notificacao__20220806" (
    id bigint,
    dt_notific date,
    se_notif integer,
    ano_notif integer,
    dt_sin_pri date,
    se_sin_pri integer,
    dt_digita date,
    municipio_geocodigo integer,
    nu_notific integer,
    cid10_codigo character varying(5),
    dt_nasc date,
    cs_sexo character varying(1),
    nu_idade_n integer,
    resul_pcr numeric,
    criterio numeric,
    classi_fin numeric
);


ALTER TABLE "Municipio"."Notificacao__20220806" OWNER TO dengueadmin;

--
-- Name: Notificacao_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: administrador
--

CREATE SEQUENCE "Municipio"."Notificacao_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio"."Notificacao_id_seq" OWNER TO administrador;

--
-- Name: Notificacao_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: administrador
--

ALTER SEQUENCE "Municipio"."Notificacao_id_seq" OWNED BY "Municipio"."Notificacao".id;


--
-- Name: Ovitrampa; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Ovitrampa" (
    "Municipio_geocodigo" integer NOT NULL,
    latitude real NOT NULL,
    longitude real NOT NULL,
    "Arm_codigo" integer NOT NULL,
    "Perdida" boolean NOT NULL,
    "Positiva" boolean,
    "Ovos" integer,
    "Localidade_id" integer NOT NULL,
    id integer NOT NULL
);


ALTER TABLE "Municipio"."Ovitrampa" OWNER TO administrador;

--
-- Name: Ovitrampa_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: administrador
--

CREATE SEQUENCE "Municipio"."Ovitrampa_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio"."Ovitrampa_id_seq" OWNER TO administrador;

--
-- Name: Ovitrampa_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: administrador
--

ALTER SEQUENCE "Municipio"."Ovitrampa_id_seq" OWNED BY "Municipio"."Ovitrampa".id;


--
-- Name: Tweet; Type: TABLE; Schema: Municipio; Owner: administrador
--

CREATE TABLE "Municipio"."Tweet" (
    id bigint NOT NULL,
    "Municipio_geocodigo" integer NOT NULL,
    data_dia date NOT NULL,
    numero integer NOT NULL,
    "CID10_codigo" character varying(5) NOT NULL
);


ALTER TABLE "Municipio"."Tweet" OWNER TO administrador;

--
-- Name: TABLE "Tweet"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Tweet" IS 'Série de tweets diários';


--
-- Name: Tweet_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: administrador
--

CREATE SEQUENCE "Municipio"."Tweet_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio"."Tweet_id_seq" OWNER TO administrador;

--
-- Name: Tweet_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: administrador
--

ALTER SEQUENCE "Municipio"."Tweet_id_seq" OWNED BY "Municipio"."Tweet".id;


--
-- Name: alerta_mrj; Type: TABLE; Schema: Municipio; Owner: dengueadmin
--

CREATE TABLE "Municipio".alerta_mrj (
    id bigint NOT NULL,
    aps character varying(6) NOT NULL,
    se integer NOT NULL,
    data date NOT NULL,
    tweets integer,
    casos integer,
    casos_est real,
    casos_estmin real,
    casos_estmax real,
    tmin real,
    rt real,
    prt1 real,
    inc real,
    nivel integer
);


ALTER TABLE "Municipio".alerta_mrj OWNER TO dengueadmin;

--
-- Name: alerta_mrj_chik; Type: TABLE; Schema: Municipio; Owner: dengueadmin
--

CREATE TABLE "Municipio".alerta_mrj_chik (
    id bigint NOT NULL,
    aps character varying(6) NOT NULL,
    se integer NOT NULL,
    data date NOT NULL,
    tweets integer,
    casos integer,
    casos_est real,
    casos_estmin real,
    casos_estmax real,
    tmin real,
    rt real,
    prt1 real,
    inc real,
    nivel integer
);


ALTER TABLE "Municipio".alerta_mrj_chik OWNER TO dengueadmin;

--
-- Name: alerta_mrj_chik_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: dengueadmin
--

CREATE SEQUENCE "Municipio".alerta_mrj_chik_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio".alerta_mrj_chik_id_seq OWNER TO dengueadmin;

--
-- Name: alerta_mrj_chik_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: dengueadmin
--

ALTER SEQUENCE "Municipio".alerta_mrj_chik_id_seq OWNED BY "Municipio".alerta_mrj_chik.id;


--
-- Name: alerta_mrj_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: dengueadmin
--

CREATE SEQUENCE "Municipio".alerta_mrj_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio".alerta_mrj_id_seq OWNER TO dengueadmin;

--
-- Name: alerta_mrj_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: dengueadmin
--

ALTER SEQUENCE "Municipio".alerta_mrj_id_seq OWNED BY "Municipio".alerta_mrj.id;


--
-- Name: alerta_mrj_zika; Type: TABLE; Schema: Municipio; Owner: postgres
--

CREATE TABLE "Municipio".alerta_mrj_zika (
    id bigint NOT NULL,
    aps character varying(6) NOT NULL,
    se integer NOT NULL,
    data date NOT NULL,
    tweets integer,
    casos integer,
    casos_est real,
    casos_estmin real,
    casos_estmax real,
    tmin real,
    rt real,
    prt1 real,
    inc real,
    nivel integer
);


ALTER TABLE "Municipio".alerta_mrj_zika OWNER TO postgres;

--
-- Name: alerta_mrj_zika_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: postgres
--

CREATE SEQUENCE "Municipio".alerta_mrj_zika_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio".alerta_mrj_zika_id_seq OWNER TO postgres;

--
-- Name: alerta_mrj_zika_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: postgres
--

ALTER SEQUENCE "Municipio".alerta_mrj_zika_id_seq OWNED BY "Municipio".alerta_mrj_zika.id;


--
-- Name: copernicus_br; Type: TABLE; Schema: Municipio; Owner: dengueadmin
--

CREATE TABLE "Municipio".copernicus_br (
    date timestamp without time zone,
    geocodigo bigint,
    temp_min real,
    temp_med real,
    temp_max real,
    precip_min real,
    precip_med real,
    precip_max real,
    pressao_min real,
    pressao_med real,
    pressao_max real,
    umid_min real,
    umid_med real,
    umid_max real
);


ALTER TABLE "Municipio".copernicus_br OWNER TO dengueadmin;

--
-- Name: copernicus_foz; Type: TABLE; Schema: Municipio; Owner: dengueadmin
--

CREATE TABLE "Municipio".copernicus_foz (
    date timestamp without time zone,
    geocodigo bigint,
    temp real,
    precip real,
    pressao real,
    umid real
);


ALTER TABLE "Municipio".copernicus_foz OWNER TO dengueadmin;

--
-- Name: historico_casos; Type: VIEW; Schema: Municipio; Owner: postgres
--

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

--
-- Name: weather_copernicus; Type: TABLE; Schema: Municipio; Owner: dengueadmin
--

CREATE TABLE "Municipio".weather_copernicus (
    date timestamp without time zone,
    geocodigo bigint,
    temp_min real,
    temp_med real,
    temp_max real,
    precip_min real,
    precip_med real,
    precip_max real,
    pressao_min real,
    pressao_med real,
    pressao_max real,
    umid_min real,
    umid_med real,
    umid_max real
);


ALTER TABLE "Municipio".weather_copernicus OWNER TO dengueadmin;

--
-- Name: auth_group; Type: TABLE; Schema: forecast; Owner: forecast
--

CREATE TABLE forecast.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE forecast.auth_group OWNER TO forecast;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: forecast; Owner: forecast
--

CREATE SEQUENCE forecast.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_group_id_seq OWNER TO forecast;

--
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: forecast
--

ALTER SEQUENCE forecast.auth_group_id_seq OWNED BY forecast.auth_group.id;


--
-- Name: auth_group_permissions; Type: TABLE; Schema: forecast; Owner: forecast
--

CREATE TABLE forecast.auth_group_permissions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE forecast.auth_group_permissions OWNER TO forecast;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: forecast; Owner: forecast
--

CREATE SEQUENCE forecast.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_group_permissions_id_seq OWNER TO forecast;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: forecast
--

ALTER SEQUENCE forecast.auth_group_permissions_id_seq OWNED BY forecast.auth_group_permissions.id;


--
-- Name: auth_permission; Type: TABLE; Schema: forecast; Owner: forecast
--

CREATE TABLE forecast.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE forecast.auth_permission OWNER TO forecast;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: forecast; Owner: forecast
--

CREATE SEQUENCE forecast.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_permission_id_seq OWNER TO forecast;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: forecast
--

ALTER SEQUENCE forecast.auth_permission_id_seq OWNED BY forecast.auth_permission.id;


--
-- Name: auth_user; Type: TABLE; Schema: forecast; Owner: forecast
--

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

--
-- Name: auth_user_groups; Type: TABLE; Schema: forecast; Owner: forecast
--

CREATE TABLE forecast.auth_user_groups (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE forecast.auth_user_groups OWNER TO forecast;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: forecast; Owner: forecast
--

CREATE SEQUENCE forecast.auth_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_user_groups_id_seq OWNER TO forecast;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: forecast
--

ALTER SEQUENCE forecast.auth_user_groups_id_seq OWNED BY forecast.auth_user_groups.id;


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: forecast; Owner: forecast
--

CREATE SEQUENCE forecast.auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_user_id_seq OWNER TO forecast;

--
-- Name: auth_user_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: forecast
--

ALTER SEQUENCE forecast.auth_user_id_seq OWNED BY forecast.auth_user.id;


--
-- Name: auth_user_user_permissions; Type: TABLE; Schema: forecast; Owner: forecast
--

CREATE TABLE forecast.auth_user_user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE forecast.auth_user_user_permissions OWNER TO forecast;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: forecast; Owner: forecast
--

CREATE SEQUENCE forecast.auth_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.auth_user_user_permissions_id_seq OWNER TO forecast;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: forecast
--

ALTER SEQUENCE forecast.auth_user_user_permissions_id_seq OWNED BY forecast.auth_user_user_permissions.id;


--
-- Name: chunked_upload_chunkedupload; Type: TABLE; Schema: forecast; Owner: forecast
--

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

--
-- Name: chunked_upload_chunkedupload_id_seq; Type: SEQUENCE; Schema: forecast; Owner: forecast
--

CREATE SEQUENCE forecast.chunked_upload_chunkedupload_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.chunked_upload_chunkedupload_id_seq OWNER TO forecast;

--
-- Name: chunked_upload_chunkedupload_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: forecast
--

ALTER SEQUENCE forecast.chunked_upload_chunkedupload_id_seq OWNED BY forecast.chunked_upload_chunkedupload.id;


--
-- Name: django_admin_log; Type: TABLE; Schema: forecast; Owner: forecast
--

CREATE TABLE forecast.django_admin_log (
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


ALTER TABLE forecast.django_admin_log OWNER TO forecast;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: forecast; Owner: forecast
--

CREATE SEQUENCE forecast.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.django_admin_log_id_seq OWNER TO forecast;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: forecast
--

ALTER SEQUENCE forecast.django_admin_log_id_seq OWNED BY forecast.django_admin_log.id;


--
-- Name: django_content_type; Type: TABLE; Schema: forecast; Owner: forecast
--

CREATE TABLE forecast.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE forecast.django_content_type OWNER TO forecast;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: forecast; Owner: forecast
--

CREATE SEQUENCE forecast.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.django_content_type_id_seq OWNER TO forecast;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: forecast
--

ALTER SEQUENCE forecast.django_content_type_id_seq OWNED BY forecast.django_content_type.id;


--
-- Name: django_migrations; Type: TABLE; Schema: forecast; Owner: forecast
--

CREATE TABLE forecast.django_migrations (
    id integer NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE forecast.django_migrations OWNER TO forecast;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: forecast; Owner: forecast
--

CREATE SEQUENCE forecast.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.django_migrations_id_seq OWNER TO forecast;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: forecast
--

ALTER SEQUENCE forecast.django_migrations_id_seq OWNED BY forecast.django_migrations.id;


--
-- Name: django_session; Type: TABLE; Schema: forecast; Owner: forecast
--

CREATE TABLE forecast.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE forecast.django_session OWNER TO forecast;

--
-- Name: forecast_cases; Type: TABLE; Schema: forecast; Owner: postgres
--

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

--
-- Name: forecast_cases_id_seq; Type: SEQUENCE; Schema: forecast; Owner: postgres
--

CREATE SEQUENCE forecast.forecast_cases_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.forecast_cases_id_seq OWNER TO postgres;

--
-- Name: forecast_cases_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: postgres
--

ALTER SEQUENCE forecast.forecast_cases_id_seq OWNED BY forecast.forecast_cases.id;


--
-- Name: forecast_city; Type: TABLE; Schema: forecast; Owner: postgres
--

CREATE TABLE forecast.forecast_city (
    id integer NOT NULL,
    geocode integer NOT NULL,
    forecast_model_id integer,
    active boolean NOT NULL
);


ALTER TABLE forecast.forecast_city OWNER TO postgres;

--
-- Name: forecast_city_id_seq; Type: SEQUENCE; Schema: forecast; Owner: postgres
--

CREATE SEQUENCE forecast.forecast_city_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.forecast_city_id_seq OWNER TO postgres;

--
-- Name: forecast_city_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: postgres
--

ALTER SEQUENCE forecast.forecast_city_id_seq OWNED BY forecast.forecast_city.id;


--
-- Name: forecast_model; Type: TABLE; Schema: forecast; Owner: postgres
--

CREATE TABLE forecast.forecast_model (
    id integer NOT NULL,
    name character varying(128) NOT NULL,
    weeks smallint NOT NULL,
    commit_id character(7) NOT NULL,
    active boolean NOT NULL
);


ALTER TABLE forecast.forecast_model OWNER TO postgres;

--
-- Name: forecast_model_id_seq; Type: SEQUENCE; Schema: forecast; Owner: postgres
--

CREATE SEQUENCE forecast.forecast_model_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE forecast.forecast_model_id_seq OWNER TO postgres;

--
-- Name: forecast_model_id_seq; Type: SEQUENCE OWNED BY; Schema: forecast; Owner: postgres
--

ALTER SEQUENCE forecast.forecast_model_id_seq OWNED BY forecast.forecast_model.id;


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
    state_abbreviation character varying(2),
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
-- Name: hist_uf_chik_materialized_view; Type: MATERIALIZED VIEW; Schema: public; Owner: dengueadmin
--

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

--
-- Name: hist_uf_dengue_materialized_view; Type: MATERIALIZED VIEW; Schema: public; Owner: dengueadmin
--

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

--
-- Name: hist_uf_zika_materialized_view; Type: MATERIALIZED VIEW; Schema: public; Owner: dengueadmin
--

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

--
-- Name: uf_total_chik_view; Type: MATERIALIZED VIEW; Schema: public; Owner: administrador
--

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

--
-- Name: uf_total_view; Type: MATERIALIZED VIEW; Schema: public; Owner: administrador
--

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

--
-- Name: uf_total_zika_view; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres
--

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

--
-- Name: alerta_regional_chik id; Type: DEFAULT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".alerta_regional_chik ALTER COLUMN id SET DEFAULT nextval('"Dengue_global".alerta_regional_chik_id_seq'::regclass);


--
-- Name: alerta_regional_dengue id; Type: DEFAULT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".alerta_regional_dengue ALTER COLUMN id SET DEFAULT nextval('"Dengue_global".alerta_regional_dengue_id_seq'::regclass);


--
-- Name: alerta_regional_zika id; Type: DEFAULT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".alerta_regional_zika ALTER COLUMN id SET DEFAULT nextval('"Dengue_global".alerta_regional_zika_id_seq'::regclass);


--
-- Name: macroregional id; Type: DEFAULT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".macroregional ALTER COLUMN id SET DEFAULT nextval('"Dengue_global".macroregional_id_seq'::regclass);


--
-- Name: regional id; Type: DEFAULT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".regional ALTER COLUMN id SET DEFAULT nextval('"Dengue_global".regional_id_seq'::regclass);


--
-- Name: regional_saude id; Type: DEFAULT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".regional_saude ALTER COLUMN id SET DEFAULT nextval('"Dengue_global".regional_saude_id_seq'::regclass);


--
-- Name: Clima_Satelite id; Type: DEFAULT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Clima_Satelite" ALTER COLUMN id SET DEFAULT nextval('"Municipio"."Clima_Satelite_id_seq"'::regclass);


--
-- Name: Clima_cemaden id; Type: DEFAULT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Clima_cemaden" ALTER COLUMN id SET DEFAULT nextval('"Municipio"."Clima_cemaden_id_seq"'::regclass);


--
-- Name: Clima_wu id; Type: DEFAULT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Clima_wu" ALTER COLUMN id SET DEFAULT nextval('"Municipio"."Clima_wu_id_seq"'::regclass);


--
-- Name: Historico_alerta id; Type: DEFAULT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Historico_alerta" ALTER COLUMN id SET DEFAULT nextval('"Municipio"."Historico_alerta_id_seq"'::regclass);


--
-- Name: Historico_alerta_chik id; Type: DEFAULT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Historico_alerta_chik" ALTER COLUMN id SET DEFAULT nextval('"Municipio"."Historico_alerta_chik_id_seq"'::regclass);


--
-- Name: Historico_alerta_zika id; Type: DEFAULT; Schema: Municipio; Owner: postgres
--

ALTER TABLE ONLY "Municipio"."Historico_alerta_zika" ALTER COLUMN id SET DEFAULT nextval('"Municipio"."Historico_alerta_zika_id_seq"'::regclass);


--
-- Name: Notificacao id; Type: DEFAULT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Notificacao" ALTER COLUMN id SET DEFAULT nextval('"Municipio"."Notificacao_id_seq"'::regclass);


--
-- Name: Ovitrampa id; Type: DEFAULT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Ovitrampa" ALTER COLUMN id SET DEFAULT nextval('"Municipio"."Ovitrampa_id_seq"'::regclass);


--
-- Name: Tweet id; Type: DEFAULT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Tweet" ALTER COLUMN id SET DEFAULT nextval('"Municipio"."Tweet_id_seq"'::regclass);


--
-- Name: alerta_mrj id; Type: DEFAULT; Schema: Municipio; Owner: dengueadmin
--

ALTER TABLE ONLY "Municipio".alerta_mrj ALTER COLUMN id SET DEFAULT nextval('"Municipio".alerta_mrj_id_seq'::regclass);


--
-- Name: alerta_mrj_chik id; Type: DEFAULT; Schema: Municipio; Owner: dengueadmin
--

ALTER TABLE ONLY "Municipio".alerta_mrj_chik ALTER COLUMN id SET DEFAULT nextval('"Municipio".alerta_mrj_chik_id_seq'::regclass);


--
-- Name: alerta_mrj_zika id; Type: DEFAULT; Schema: Municipio; Owner: postgres
--

ALTER TABLE ONLY "Municipio".alerta_mrj_zika ALTER COLUMN id SET DEFAULT nextval('"Municipio".alerta_mrj_zika_id_seq'::regclass);


--
-- Name: auth_group id; Type: DEFAULT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_group ALTER COLUMN id SET DEFAULT nextval('forecast.auth_group_id_seq'::regclass);


--
-- Name: auth_group_permissions id; Type: DEFAULT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('forecast.auth_group_permissions_id_seq'::regclass);


--
-- Name: auth_permission id; Type: DEFAULT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_permission ALTER COLUMN id SET DEFAULT nextval('forecast.auth_permission_id_seq'::regclass);


--
-- Name: auth_user id; Type: DEFAULT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user ALTER COLUMN id SET DEFAULT nextval('forecast.auth_user_id_seq'::regclass);


--
-- Name: auth_user_groups id; Type: DEFAULT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user_groups ALTER COLUMN id SET DEFAULT nextval('forecast.auth_user_groups_id_seq'::regclass);


--
-- Name: auth_user_user_permissions id; Type: DEFAULT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user_user_permissions ALTER COLUMN id SET DEFAULT nextval('forecast.auth_user_user_permissions_id_seq'::regclass);


--
-- Name: chunked_upload_chunkedupload id; Type: DEFAULT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.chunked_upload_chunkedupload ALTER COLUMN id SET DEFAULT nextval('forecast.chunked_upload_chunkedupload_id_seq'::regclass);


--
-- Name: django_admin_log id; Type: DEFAULT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.django_admin_log ALTER COLUMN id SET DEFAULT nextval('forecast.django_admin_log_id_seq'::regclass);


--
-- Name: django_content_type id; Type: DEFAULT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.django_content_type ALTER COLUMN id SET DEFAULT nextval('forecast.django_content_type_id_seq'::regclass);


--
-- Name: django_migrations id; Type: DEFAULT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.django_migrations ALTER COLUMN id SET DEFAULT nextval('forecast.django_migrations_id_seq'::regclass);


--
-- Name: forecast_cases id; Type: DEFAULT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_cases ALTER COLUMN id SET DEFAULT nextval('forecast.forecast_cases_id_seq'::regclass);


--
-- Name: forecast_city id; Type: DEFAULT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_city ALTER COLUMN id SET DEFAULT nextval('forecast.forecast_city_id_seq'::regclass);


--
-- Name: forecast_model id; Type: DEFAULT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_model ALTER COLUMN id SET DEFAULT nextval('forecast.forecast_model_id_seq'::regclass);


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
-- Name: CID10 CID10_pk; Type: CONSTRAINT; Schema: Dengue_global; Owner: administrador
--

ALTER TABLE ONLY "Dengue_global"."CID10"
    ADD CONSTRAINT "CID10_pk" PRIMARY KEY (codigo);


--
-- Name: Municipio Municipio_pk; Type: CONSTRAINT; Schema: Dengue_global; Owner: administrador
--

ALTER TABLE ONLY "Dengue_global"."Municipio"
    ADD CONSTRAINT "Municipio_pk" PRIMARY KEY (geocodigo);


--
-- Name: alerta_regional_chik alertaregionalchik_pk; Type: CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".alerta_regional_chik
    ADD CONSTRAINT alertaregionalchik_pk PRIMARY KEY (id);


--
-- Name: alerta_regional_dengue alertaregionaldengue_pk; Type: CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".alerta_regional_dengue
    ADD CONSTRAINT alertaregionaldengue_pk PRIMARY KEY (id);


--
-- Name: alerta_regional_zika alertaregionalzika_pk; Type: CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".alerta_regional_zika
    ADD CONSTRAINT alertaregionalzika_pk PRIMARY KEY (id);


--
-- Name: estado estado_pkey; Type: CONSTRAINT; Schema: Dengue_global; Owner: administrador
--

ALTER TABLE ONLY "Dengue_global".estado
    ADD CONSTRAINT estado_pkey PRIMARY KEY (geocodigo);


--
-- Name: macroregional macroregional_pk; Type: CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".macroregional
    ADD CONSTRAINT macroregional_pk PRIMARY KEY (id);


--
-- Name: parameters parameters_pkey; Type: CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".parameters
    ADD CONSTRAINT parameters_pkey PRIMARY KEY (municipio_geocodigo);


--
-- Name: regional regional_pk; Type: CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".regional
    ADD CONSTRAINT regional_pk PRIMARY KEY (id);


--
-- Name: regional_saude regional_saude_pkey; Type: CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".regional_saude
    ADD CONSTRAINT regional_saude_pkey PRIMARY KEY (id);


--
-- Name: regional_saude regional_saude_uq_municipio_geocodigo; Type: CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".regional_saude
    ADD CONSTRAINT regional_saude_uq_municipio_geocodigo UNIQUE (municipio_geocodigo);


--
-- Name: Bairro Bairro_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Bairro"
    ADD CONSTRAINT "Bairro_pk" PRIMARY KEY (nome, bairro_id);


--
-- Name: Clima_Satelite Clima_Satelite_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Clima_Satelite"
    ADD CONSTRAINT "Clima_Satelite_pk" PRIMARY KEY (id);


--
-- Name: Clima_cemaden Clima_cemaden_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Clima_cemaden"
    ADD CONSTRAINT "Clima_cemaden_pk" PRIMARY KEY (id);


--
-- Name: Clima_wu Clima_wu_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Clima_wu"
    ADD CONSTRAINT "Clima_wu_pk" PRIMARY KEY (id);


--
-- Name: Estacao_cemaden Estacao_cemaden_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Estacao_cemaden"
    ADD CONSTRAINT "Estacao_cemaden_pk" PRIMARY KEY (codestacao);


--
-- Name: Estacao_wu Estacao_wu_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Estacao_wu"
    ADD CONSTRAINT "Estacao_wu_pk" PRIMARY KEY (estacao_id);


--
-- Name: Historico_alerta_chik Historico_alerta_chik_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Historico_alerta_chik"
    ADD CONSTRAINT "Historico_alerta_chik_pk" PRIMARY KEY (id);


--
-- Name: Historico_alerta Historico_alerta_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Historico_alerta"
    ADD CONSTRAINT "Historico_alerta_pk" PRIMARY KEY (id);


--
-- Name: Historico_alerta_zika Historico_alerta_zika_pk; Type: CONSTRAINT; Schema: Municipio; Owner: postgres
--

ALTER TABLE ONLY "Municipio"."Historico_alerta_zika"
    ADD CONSTRAINT "Historico_alerta_zika_pk" PRIMARY KEY (id);


--
-- Name: Localidade Localidade_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Localidade"
    ADD CONSTRAINT "Localidade_pk" PRIMARY KEY (id);


--
-- Name: Notificacao Notificacao_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Notificacao"
    ADD CONSTRAINT "Notificacao_pk" PRIMARY KEY (id);


--
-- Name: Ovitrampa Ovitrampa_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Ovitrampa"
    ADD CONSTRAINT "Ovitrampa_pk" PRIMARY KEY (id);


--
-- Name: Tweet Tweet_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Tweet"
    ADD CONSTRAINT "Tweet_pk" PRIMARY KEY (id);


--
-- Name: alerta_mrj_chik alerta_mrj_chik_pk; Type: CONSTRAINT; Schema: Municipio; Owner: dengueadmin
--

ALTER TABLE ONLY "Municipio".alerta_mrj_chik
    ADD CONSTRAINT alerta_mrj_chik_pk PRIMARY KEY (id);


--
-- Name: alerta_mrj alerta_mrj_pk; Type: CONSTRAINT; Schema: Municipio; Owner: dengueadmin
--

ALTER TABLE ONLY "Municipio".alerta_mrj
    ADD CONSTRAINT alerta_mrj_pk PRIMARY KEY (id);


--
-- Name: alerta_mrj_zika alerta_mrj_zika_pk; Type: CONSTRAINT; Schema: Municipio; Owner: postgres
--

ALTER TABLE ONLY "Municipio".alerta_mrj_zika
    ADD CONSTRAINT alerta_mrj_zika_pk PRIMARY KEY (id);


--
-- Name: Historico_alerta alertas_unicos; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Historico_alerta"
    ADD CONSTRAINT alertas_unicos UNIQUE ("SE", municipio_geocodigo, "Localidade_id");


--
-- Name: Historico_alerta_chik alertas_unicos_chik; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Historico_alerta_chik"
    ADD CONSTRAINT alertas_unicos_chik UNIQUE ("SE", municipio_geocodigo, "Localidade_id");


--
-- Name: Historico_alerta_zika alertas_unicos_zika; Type: CONSTRAINT; Schema: Municipio; Owner: postgres
--

ALTER TABLE ONLY "Municipio"."Historico_alerta_zika"
    ADD CONSTRAINT alertas_unicos_zika UNIQUE ("SE", municipio_geocodigo, "Localidade_id");


--
-- Name: Notificacao casos_unicos; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Notificacao"
    ADD CONSTRAINT casos_unicos UNIQUE (nu_notific, dt_notific, cid10_codigo, municipio_geocodigo);


--
-- Name: alerta_mrj previsao; Type: CONSTRAINT; Schema: Municipio; Owner: dengueadmin
--

ALTER TABLE ONLY "Municipio".alerta_mrj
    ADD CONSTRAINT previsao UNIQUE (aps, se);


--
-- Name: alerta_mrj_chik previsao_chik; Type: CONSTRAINT; Schema: Municipio; Owner: dengueadmin
--

ALTER TABLE ONLY "Municipio".alerta_mrj_chik
    ADD CONSTRAINT previsao_chik UNIQUE (aps, se);


--
-- Name: alerta_mrj_zika previsao_zika; Type: CONSTRAINT; Schema: Municipio; Owner: postgres
--

ALTER TABLE ONLY "Municipio".alerta_mrj_zika
    ADD CONSTRAINT previsao_zika UNIQUE (aps, se);


--
-- Name: alerta_mrj unique_aps_se; Type: CONSTRAINT; Schema: Municipio; Owner: dengueadmin
--

ALTER TABLE ONLY "Municipio".alerta_mrj
    ADD CONSTRAINT unique_aps_se UNIQUE (se, aps);


--
-- Name: alerta_mrj_chik unique_chik_aps_se; Type: CONSTRAINT; Schema: Municipio; Owner: dengueadmin
--

ALTER TABLE ONLY "Municipio".alerta_mrj_chik
    ADD CONSTRAINT unique_chik_aps_se UNIQUE (se, aps);


--
-- Name: alerta_mrj_zika unique_zika_aps_se; Type: CONSTRAINT; Schema: Municipio; Owner: postgres
--

ALTER TABLE ONLY "Municipio".alerta_mrj_zika
    ADD CONSTRAINT unique_zika_aps_se UNIQUE (se, aps);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_pkey; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_user_id_group_id_94350c0c_uniq; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);


--
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_pkey; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_permission_id_14a6b632_uniq; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);


--
-- Name: auth_user auth_user_username_key; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);


--
-- Name: chunked_upload_chunkedupload chunked_upload_chunkedupload_pkey; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_pkey PRIMARY KEY (id);


--
-- Name: chunked_upload_chunkedupload chunked_upload_chunkedupload_upload_id_key; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_upload_id_key UNIQUE (upload_id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: forecast_cases forecast_cases_epiweek_geocode_cid10_forecast_model_id_publ_key; Type: CONSTRAINT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_cases
    ADD CONSTRAINT forecast_cases_epiweek_geocode_cid10_forecast_model_id_publ_key UNIQUE (epiweek, geocode, cid10, forecast_model_id, published_date);


--
-- Name: forecast_cases forecast_cases_pkey; Type: CONSTRAINT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_cases
    ADD CONSTRAINT forecast_cases_pkey PRIMARY KEY (id);


--
-- Name: forecast_city forecast_city_geocode_forecast_model_id_key; Type: CONSTRAINT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_city
    ADD CONSTRAINT forecast_city_geocode_forecast_model_id_key UNIQUE (geocode, forecast_model_id);


--
-- Name: forecast_city forecast_city_pkey; Type: CONSTRAINT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_city
    ADD CONSTRAINT forecast_city_pkey PRIMARY KEY (id);


--
-- Name: forecast_model forecast_model_pkey; Type: CONSTRAINT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_model
    ADD CONSTRAINT forecast_model_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


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
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


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
-- Name: auth_user_groups auth_user_groups_user_id_group_id_94350c0c_uniq; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);


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
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_permission_id_14a6b632_uniq; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);


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
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


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
-- Name: Municipio_idx_gc; Type: INDEX; Schema: Dengue_global; Owner: administrador
--

CREATE INDEX "Municipio_idx_gc" ON "Dengue_global"."Municipio" USING btree (geocodigo);


--
-- Name: Municipio_idx_n; Type: INDEX; Schema: Dengue_global; Owner: administrador
--

CREATE INDEX "Municipio_idx_n" ON "Dengue_global"."Municipio" USING btree (nome);


--
-- Name: estado_idx_gc; Type: INDEX; Schema: Dengue_global; Owner: administrador
--

CREATE INDEX estado_idx_gc ON "Dengue_global".estado USING btree (geocodigo);


--
-- Name: macroregional_idx_codigo; Type: INDEX; Schema: Dengue_global; Owner: dengueadmin
--

CREATE INDEX macroregional_idx_codigo ON "Dengue_global".macroregional USING btree (codigo);


--
-- Name: parameters_idx_gc; Type: INDEX; Schema: Dengue_global; Owner: dengueadmin
--

CREATE INDEX parameters_idx_gc ON "Dengue_global".parameters USING btree (municipio_geocodigo);


--
-- Name: regional_idx_codigo; Type: INDEX; Schema: Dengue_global; Owner: dengueadmin
--

CREATE INDEX regional_idx_codigo ON "Dengue_global".regional USING btree (codigo);


--
-- Name: Alerta_chik_idx_data; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX "Alerta_chik_idx_data" ON "Municipio"."Historico_alerta_chik" USING btree ("data_iniSE" DESC);


--
-- Name: Alerta_idx_data; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX "Alerta_idx_data" ON "Municipio"."Historico_alerta" USING btree ("data_iniSE" DESC);


--
-- Name: Alerta_zika_idx_data; Type: INDEX; Schema: Municipio; Owner: postgres
--

CREATE INDEX "Alerta_zika_idx_data" ON "Municipio"."Historico_alerta_zika" USING btree ("data_iniSE" DESC);


--
-- Name: Clima_Satelite_idx_data; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX "Clima_Satelite_idx_data" ON "Municipio"."Clima_Satelite" USING btree (id);


--
-- Name: Dengue_idx_data; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX "Dengue_idx_data" ON "Municipio"."Notificacao" USING btree (dt_notific DESC, se_notif DESC);


--
-- Name: Tweets_idx_data; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX "Tweets_idx_data" ON "Municipio"."Tweet" USING btree (data_dia DESC);


--
-- Name: WU_idx_data; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX "WU_idx_data" ON "Municipio"."Clima_wu" USING btree (data_dia DESC);


--
-- Name: chuva_idx_data; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX chuva_idx_data ON "Municipio"."Clima_cemaden" USING btree (datahora DESC);


--
-- Name: date_idx; Type: INDEX; Schema: Municipio; Owner: dengueadmin
--

CREATE INDEX date_idx ON "Municipio".copernicus_br USING btree (date);


--
-- Name: estacoes_idx; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX estacoes_idx ON "Municipio"."Clima_cemaden" USING btree ("Estacao_cemaden_codestacao");


--
-- Name: geocodigo_idx; Type: INDEX; Schema: Municipio; Owner: dengueadmin
--

CREATE INDEX geocodigo_idx ON "Municipio".copernicus_br USING btree (geocodigo);


--
-- Name: ix_Municipio_weather_copernicus_date; Type: INDEX; Schema: Municipio; Owner: dengueadmin
--

CREATE INDEX "ix_Municipio_weather_copernicus_date" ON "Municipio".weather_copernicus USING btree (date);


--
-- Name: notificacao_cid10_idx; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX notificacao_cid10_idx ON "Municipio"."Notificacao" USING btree (cid10_codigo);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX auth_group_name_a6ea08ec_like ON forecast.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON forecast.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON forecast.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON forecast.auth_permission USING btree (content_type_id);


--
-- Name: auth_user_groups_group_id_97559544; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX auth_user_groups_group_id_97559544 ON forecast.auth_user_groups USING btree (group_id);


--
-- Name: auth_user_groups_user_id_6a12ed8b; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX auth_user_groups_user_id_6a12ed8b ON forecast.auth_user_groups USING btree (user_id);


--
-- Name: auth_user_user_permissions_permission_id_1fbb5f2c; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON forecast.auth_user_user_permissions USING btree (permission_id);


--
-- Name: auth_user_user_permissions_user_id_a95ead1b; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON forecast.auth_user_user_permissions USING btree (user_id);


--
-- Name: auth_user_username_6821ab7c_like; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX auth_user_username_6821ab7c_like ON forecast.auth_user USING btree (username varchar_pattern_ops);


--
-- Name: chunked_upload_chunkedupload_upload_id_23703435_like; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX chunked_upload_chunkedupload_upload_id_23703435_like ON forecast.chunked_upload_chunkedupload USING btree (upload_id varchar_pattern_ops);


--
-- Name: chunked_upload_chunkedupload_user_id_70ff6dbf; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX chunked_upload_chunkedupload_user_id_70ff6dbf ON forecast.chunked_upload_chunkedupload USING btree (user_id);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON forecast.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON forecast.django_admin_log USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX django_session_expire_date_a5c62663 ON forecast.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: forecast; Owner: forecast
--

CREATE INDEX django_session_session_key_c0390e0f_like ON forecast.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: auth_user_groups_group_id_97559544; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);


--
-- Name: auth_user_groups_user_id_6a12ed8b; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);


--
-- Name: auth_user_user_permissions_permission_id_1fbb5f2c; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);


--
-- Name: auth_user_user_permissions_user_id_a95ead1b; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);


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
-- Name: dbf_dbf_uploaded_by_id_ad662eb4; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX dbf_dbf_uploaded_by_id_ad662eb4 ON public.dbf_dbf USING btree (uploaded_by_id);


--
-- Name: dbf_dbfchunkedupload_upload_id_e3989f45_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX dbf_dbfchunkedupload_upload_id_e3989f45_like ON public.dbf_dbfchunkedupload USING btree (upload_id varchar_pattern_ops);


--
-- Name: dbf_dbfchunkedupload_user_id_c7cc2beb; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX dbf_dbfchunkedupload_user_id_c7cc2beb ON public.dbf_dbfchunkedupload USING btree (user_id);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: uf_total_chik_view_data_idx; Type: INDEX; Schema: public; Owner: administrador
--

CREATE INDEX uf_total_chik_view_data_idx ON public.uf_total_chik_view USING btree (data);


--
-- Name: uf_total_view_data_idx; Type: INDEX; Schema: public; Owner: administrador
--

CREATE INDEX uf_total_view_data_idx ON public.uf_total_view USING btree (data);


--
-- Name: uf_total_zika_view_data_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX uf_total_zika_view_data_idx ON public.uf_total_zika_view USING btree (data);


--
-- Name: regional macroregional_fk; Type: FK CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".regional
    ADD CONSTRAINT macroregional_fk FOREIGN KEY (id_macroregional) REFERENCES "Dengue_global".macroregional(id);


--
-- Name: Municipio regional_fk; Type: FK CONSTRAINT; Schema: Dengue_global; Owner: administrador
--

ALTER TABLE ONLY "Dengue_global"."Municipio"
    ADD CONSTRAINT regional_fk FOREIGN KEY (id_regional) REFERENCES "Dengue_global".regional(id);


--
-- Name: alerta_regional_dengue regional_fk; Type: FK CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".alerta_regional_dengue
    ADD CONSTRAINT regional_fk FOREIGN KEY (id_regional) REFERENCES "Dengue_global".regional(id);


--
-- Name: alerta_regional_chik regional_fk; Type: FK CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".alerta_regional_chik
    ADD CONSTRAINT regional_fk FOREIGN KEY (id_regional) REFERENCES "Dengue_global".regional(id);


--
-- Name: alerta_regional_zika regional_fk; Type: FK CONSTRAINT; Schema: Dengue_global; Owner: dengueadmin
--

ALTER TABLE ONLY "Dengue_global".alerta_regional_zika
    ADD CONSTRAINT regional_fk FOREIGN KEY (id_regional) REFERENCES "Dengue_global".regional(id);


--
-- Name: Bairro Bairro_Localidade; Type: FK CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Bairro"
    ADD CONSTRAINT "Bairro_Localidade" FOREIGN KEY ("Localidade_id") REFERENCES "Municipio"."Localidade"(id);


--
-- Name: Ovitrampa Ovitrampa_Localidade; Type: FK CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Ovitrampa"
    ADD CONSTRAINT "Ovitrampa_Localidade" FOREIGN KEY ("Localidade_id") REFERENCES "Municipio"."Localidade"(id);


--
-- Name: Tweet Tweet_CID10; Type: FK CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Tweet"
    ADD CONSTRAINT "Tweet_CID10" FOREIGN KEY ("CID10_codigo") REFERENCES "Dengue_global"."CID10"(codigo);


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES forecast.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES forecast.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES forecast.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_group_id_97559544_fk_auth_group_id; Type: FK CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES forecast.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_user_id_6a12ed8b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES forecast.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm; Type: FK CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES forecast.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES forecast.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: chunked_upload_chunkedupload chunked_upload_chunkedupload_user_id_70ff6dbf_fk_auth_user_id; Type: FK CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_user_id_70ff6dbf_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES forecast.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES forecast.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: forecast; Owner: forecast
--

ALTER TABLE ONLY forecast.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES forecast.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: forecast_cases forecast_cases_cid10_fkey; Type: FK CONSTRAINT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_cases
    ADD CONSTRAINT forecast_cases_cid10_fkey FOREIGN KEY (cid10) REFERENCES "Dengue_global"."CID10"(codigo);


--
-- Name: forecast_cases forecast_cases_forecast_model_id_fkey; Type: FK CONSTRAINT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_cases
    ADD CONSTRAINT forecast_cases_forecast_model_id_fkey FOREIGN KEY (forecast_model_id) REFERENCES forecast.forecast_model(id);


--
-- Name: forecast_cases forecast_cases_geocode_fkey; Type: FK CONSTRAINT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_cases
    ADD CONSTRAINT forecast_cases_geocode_fkey FOREIGN KEY (geocode) REFERENCES "Dengue_global"."Municipio"(geocodigo);


--
-- Name: forecast_city forecast_city_forecast_model_id_fkey; Type: FK CONSTRAINT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_city
    ADD CONSTRAINT forecast_city_forecast_model_id_fkey FOREIGN KEY (forecast_model_id) REFERENCES forecast.forecast_model(id);


--
-- Name: forecast_city forecast_city_geocode_fkey; Type: FK CONSTRAINT; Schema: forecast; Owner: postgres
--

ALTER TABLE ONLY forecast.forecast_city
    ADD CONSTRAINT forecast_city_geocode_fkey FOREIGN KEY (geocode) REFERENCES "Dengue_global"."Municipio"(geocodigo);


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


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
-- Name: auth_user_user_permissions auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


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
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


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
-- Name: TABLE "CID10"; Type: ACL; Schema: Dengue_global; Owner: administrador
--

GRANT ALL ON TABLE "Dengue_global"."CID10" TO "Dengue";
GRANT ALL ON TABLE "Dengue_global"."CID10" TO dengue;


--
-- Name: TABLE "Municipio"; Type: ACL; Schema: Dengue_global; Owner: administrador
--

GRANT ALL ON TABLE "Dengue_global"."Municipio" TO "Dengue";
GRANT ALL ON TABLE "Dengue_global"."Municipio" TO dengue;


--
-- Name: TABLE estado; Type: ACL; Schema: Dengue_global; Owner: administrador
--

GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLE "Dengue_global".estado TO "Dengue";
GRANT ALL ON TABLE "Dengue_global".estado TO dengue;


--
-- Name: TABLE macroregional; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT ALL ON TABLE "Dengue_global".macroregional TO dengue;


--
-- Name: TABLE parameters; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT ALL ON TABLE "Dengue_global".parameters TO dengue;


--
-- Name: TABLE regional; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT ALL ON TABLE "Dengue_global".regional TO dengue;


--
-- Name: TABLE regional_saude; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT ALL ON TABLE "Dengue_global".regional_saude TO dengue;
GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLE "Dengue_global".regional_saude TO "Dengue";


--
-- Name: SEQUENCE regional_saude_id_seq; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT SELECT,USAGE ON SEQUENCE "Dengue_global".regional_saude_id_seq TO dengue;


--
-- Name: TABLE "Bairro"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Bairro" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Bairro" TO dengue;


--
-- Name: TABLE "Clima_Satelite"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Clima_Satelite" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Clima_Satelite" TO dengue;


--
-- Name: SEQUENCE "Clima_Satelite_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Clima_Satelite_id_seq" TO dengue;


--
-- Name: TABLE "Clima_cemaden"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Clima_cemaden" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Clima_cemaden" TO dengue;


--
-- Name: SEQUENCE "Clima_cemaden_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Clima_cemaden_id_seq" TO dengue;


--
-- Name: TABLE "Clima_wu"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Clima_wu" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Clima_wu" TO dengue;


--
-- Name: SEQUENCE "Clima_wu_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Clima_wu_id_seq" TO dengue;


--
-- Name: TABLE "Estacao_cemaden"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Estacao_cemaden" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Estacao_cemaden" TO dengue;


--
-- Name: TABLE "Estacao_wu"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Estacao_wu" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Estacao_wu" TO dengue;


--
-- Name: TABLE "Historico_alerta"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Historico_alerta" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Historico_alerta" TO dengue;


--
-- Name: TABLE "Historico_alerta_chik"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Historico_alerta_chik" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Historico_alerta_chik" TO dengue;


--
-- Name: SEQUENCE "Historico_alerta_chik_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Historico_alerta_chik_id_seq" TO dengue;


--
-- Name: SEQUENCE "Historico_alerta_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Historico_alerta_id_seq" TO dengue;


--
-- Name: TABLE "Historico_alerta_zika"; Type: ACL; Schema: Municipio; Owner: postgres
--

GRANT ALL ON TABLE "Municipio"."Historico_alerta_zika" TO dengue;


--
-- Name: SEQUENCE "Historico_alerta_zika_id_seq"; Type: ACL; Schema: Municipio; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Historico_alerta_zika_id_seq" TO dengue;


--
-- Name: TABLE "Localidade"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Localidade" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Localidade" TO dengue;


--
-- Name: TABLE "Notificacao"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Notificacao" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Notificacao" TO dengue;


--
-- Name: SEQUENCE "Notificacao_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Notificacao_id_seq" TO dengue;


--
-- Name: TABLE "Ovitrampa"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Ovitrampa" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Ovitrampa" TO dengue;


--
-- Name: SEQUENCE "Ovitrampa_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Ovitrampa_id_seq" TO dengue;


--
-- Name: TABLE "Tweet"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Tweet" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Tweet" TO dengue;


--
-- Name: SEQUENCE "Tweet_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Tweet_id_seq" TO dengue;


--
-- Name: TABLE alerta_mrj; Type: ACL; Schema: Municipio; Owner: dengueadmin
--

GRANT ALL ON TABLE "Municipio".alerta_mrj TO dengue;


--
-- Name: TABLE alerta_mrj_chik; Type: ACL; Schema: Municipio; Owner: dengueadmin
--

GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLE "Municipio".alerta_mrj_chik TO "Dengue";
GRANT ALL ON TABLE "Municipio".alerta_mrj_chik TO dengue;


--
-- Name: SEQUENCE alerta_mrj_chik_id_seq; Type: ACL; Schema: Municipio; Owner: dengueadmin
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio".alerta_mrj_chik_id_seq TO dengue;


--
-- Name: SEQUENCE alerta_mrj_id_seq; Type: ACL; Schema: Municipio; Owner: dengueadmin
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio".alerta_mrj_id_seq TO dengue;


--
-- Name: TABLE alerta_mrj_zika; Type: ACL; Schema: Municipio; Owner: postgres
--

GRANT ALL ON TABLE "Municipio".alerta_mrj_zika TO dengue;


--
-- Name: SEQUENCE alerta_mrj_zika_id_seq; Type: ACL; Schema: Municipio; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio".alerta_mrj_zika_id_seq TO dengue;


--
-- Name: TABLE historico_casos; Type: ACL; Schema: Municipio; Owner: postgres
--

GRANT ALL ON TABLE "Municipio".historico_casos TO dengue;


--
-- Name: TABLE uf_total_chik_view; Type: ACL; Schema: public; Owner: administrador
--

GRANT SELECT,INSERT,REFERENCES,TRIGGER,UPDATE ON TABLE public.uf_total_chik_view TO "Dengue";


--
-- Name: TABLE uf_total_view; Type: ACL; Schema: public; Owner: administrador
--

GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLE public.uf_total_view TO "Dengue";


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: administrador
--

ALTER DEFAULT PRIVILEGES FOR ROLE administrador GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLES  TO "Dengue";
ALTER DEFAULT PRIVILEGES FOR ROLE administrador GRANT SELECT ON TABLES  TO "Read_only";


--
-- PostgreSQL database dump complete
--
