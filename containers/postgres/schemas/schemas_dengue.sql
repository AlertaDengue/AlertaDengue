--
-- PostgreSQL database dump
--

-- Dumped from database version 14.23 (Debian 14.23-1.pgdg11+1)
-- Dumped by pg_dump version 14.18 (Debian 14.18-1.pgdg110+1)

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

CREATE SCHEMA "Dengue_global";


ALTER SCHEMA "Dengue_global" OWNER TO "Dengue";

--
-- Name: Municipio; Type: SCHEMA; Schema: -; Owner: Dengue
--

CREATE SCHEMA "Municipio";


ALTER SCHEMA "Municipio" OWNER TO "Dengue";

--
-- Name: archive_alertas_regionais; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA archive_alertas_regionais;


ALTER SCHEMA archive_alertas_regionais OWNER TO postgres;

--
-- Name: archive_ovitrampa; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA archive_ovitrampa;


ALTER SCHEMA archive_ovitrampa OWNER TO postgres;

--
-- Name: ingestion; Type: SCHEMA; Schema: -; Owner: dengueadmin
--

CREATE SCHEMA ingestion;


ALTER SCHEMA ingestion OWNER TO dengueadmin;

--
-- Name: staging_meta; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA staging_meta;


ALTER SCHEMA staging_meta OWNER TO postgres;

--
-- Name: weather; Type: SCHEMA; Schema: -; Owner: dengueadmin
--

CREATE SCHEMA weather;


ALTER SCHEMA weather OWNER TO dengueadmin;

--
-- Name: plpython3u; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plpython3u WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpython3u; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION plpython3u IS 'PL/Python3U untrusted procedural language';


--
-- Name: adminpack; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS adminpack WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION adminpack; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION adminpack IS 'administrative functions for PostgreSQL';


--
-- Name: hstore; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS hstore WITH SCHEMA public;


--
-- Name: EXTENSION hstore; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION hstore IS 'data type for storing sets of (key, value) pairs';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry, geography, and raster spatial types and functions';


--
-- Name: postgres_fdw; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgres_fdw WITH SCHEMA public;


--
-- Name: EXTENSION postgres_fdw; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION postgres_fdw IS 'foreign-data wrapper for remote PostgreSQL servers';


--
-- Name: add_dv(integer); Type: FUNCTION; Schema: public; Owner: dengueadmin
--

CREATE FUNCTION public.add_dv(geocodigo integer) RETURNS integer
    LANGUAGE plpython3u
    AS $$
    """
    Retorna o geocóodigo do município adicionando o digito verificador,
    se necessário.
    :param geocodigo: geocóodigo com 6 ou 7 dígitos
    """
    if len(str(geocodigo)) == 7:
        return geocodigo
    elif len(str(geocodigo)) == 6:
        dv = plpy.execute(f"select calculate_digit({geocodigo}) as dv;")[0]['dv']
        return int(str(geocodigo) + str(dv))
    else:
        print("geocode does not match!\n leaving it unchanged")
        return geocodigo
$$;


ALTER FUNCTION public.add_dv(geocodigo integer) OWNER TO dengueadmin;

--
-- Name: calculate_digit(integer); Type: FUNCTION; Schema: public; Owner: dengueadmin
--

CREATE FUNCTION public.calculate_digit(geocodigo integer) RETURNS integer
    LANGUAGE plpython3u
    AS $$
    """
    Calcula o digito verificador do geocodigo de municipio
    :param dig: geocodigo com 6 digitos
    :return: digito verificador
    """
    peso = [1, 2, 1, 2, 1, 2, 0]
    soma = 0
    digit = str(geocodigo)

    for i in range(6):
        valor = int(digit[i]) * peso[i]
        soma += sum([int(d) for d in str(valor)]) if valor > 9 else valor

    dv = 0 if soma % 10 == 0 else (10 - (soma % 10))
    return dv
$$;


ALTER FUNCTION public.calculate_digit(geocodigo integer) OWNER TO dengueadmin;

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

--
-- Name: extract_se(date); Type: FUNCTION; Schema: public; Owner: dengueadmin
--

CREATE FUNCTION public.extract_se(date date) RETURNS integer
    LANGUAGE plpython3u
    AS $$
from datetime import date as dt

def _system_adjustment(system: str) -> int:
    systems = ("iso", "cdc")  # Monday, Sunday
    return systems.index(system.lower())

def _year_start(year: int, system: str) -> int:
    adjustment = _system_adjustment(system)
    mid_weekday = 3 - adjustment  # Sun is 6 .. Mon is 0
    jan1 = dt(year, 1, 1)
    jan1_ordinal = jan1.toordinal()
    jan1_weekday = jan1.weekday()
    week1_start_ordinal = jan1_ordinal - jan1_weekday - adjustment
    if jan1_weekday > mid_weekday:
        week1_start_ordinal += 7
    return week1_start_ordinal

def fromdate(date: dt, system: str = "cdc") -> int:
    if isinstance(date, str):
        date = dt.fromisoformat(date)
    year = date.year
    date_ordinal = date.toordinal()
    year_start_ordinal = _year_start(year, system)
    week = (date_ordinal - year_start_ordinal) // 7
    if week < 0:
        year -= 1
        year_start_ordinal = _year_start(year, system)
        week = (date_ordinal - year_start_ordinal) // 7
    elif week >= 52:
        year_start_ordinal = _year_start(year + 1, system)
        if date_ordinal >= year_start_ordinal:
            year += 1
            week = 0
    week += 1
    return int(str(year) + f"{week:02d}")

return fromdate(date, "cdc")
$$;


ALTER FUNCTION public.extract_se(date date) OWNER TO dengueadmin;

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
    id_regional integer,
    regional character varying(128),
    macroregional_id integer,
    macroregional character varying(128)
);


ALTER TABLE "Dengue_global"."Municipio" OWNER TO administrador;

--
-- Name: TABLE "Municipio"; Type: COMMENT; Schema: Dengue_global; Owner: administrador
--

COMMENT ON TABLE "Dengue_global"."Municipio" IS 'Municipio integrado ao sistema de alerta';


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
    municipio_geocodigo integer NOT NULL,
    limiar_preseason double precision,
    limiar_posseason double precision,
    limiar_epidemico double precision,
    varcli text,
    clicrit numeric(5,0) DEFAULT NULL::numeric,
    cid10 character varying DEFAULT NULL::bpchar NOT NULL,
    codmodelo character varying,
    varcli2 character varying(16) DEFAULT NULL::character varying,
    clicrit2 numeric(5,0) DEFAULT NULL::numeric,
    codigo_estacao_wu character varying,
    estacao_wu_sec character varying
);


ALTER TABLE "Dengue_global".parameters OWNER TO dengueadmin;

--
-- Name: parameters_uf; Type: TABLE; Schema: Dengue_global; Owner: postgres
--

CREATE TABLE "Dengue_global".parameters_uf (
    state_code integer NOT NULL,
    state_abbr character varying(2) NOT NULL,
    state_name text NOT NULL,
    cid10 character varying NOT NULL,
    limiar_preseason double precision,
    limiar_posseason double precision,
    limiar_epidemico double precision
);


ALTER TABLE "Dengue_global".parameters_uf OWNER TO postgres;

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
    "Rt" real DEFAULT NULL::numeric,
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
    "Rt" real DEFAULT NULL::numeric,
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
    "Rt" real DEFAULT NULL::numeric,
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
    classi_fin numeric,
    dt_chik_s1 date,
    dt_chik_s2 date,
    dt_prnt date,
    res_chiks1 character varying(255),
    res_chiks2 character varying(255),
    resul_prnt character varying(255),
    dt_soro date,
    resul_soro character varying(255),
    dt_ns1 date,
    resul_ns1 character varying(255),
    dt_viral date,
    resul_vi_n character varying(255),
    dt_pcr date,
    sorotipo character varying(255),
    id_distrit numeric,
    id_bairro numeric,
    nm_bairro character varying(255),
    id_unidade numeric
);


ALTER TABLE "Municipio"."Notificacao" OWNER TO administrador;

--
-- Name: TABLE "Notificacao"; Type: COMMENT; Schema: Municipio; Owner: administrador
--

COMMENT ON TABLE "Municipio"."Notificacao" IS 'Casos de notificacao de dengue';


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
-- Name: historico_casos; Type: MATERIALIZED VIEW; Schema: Municipio; Owner: dengueadmin
--

CREATE MATERIALIZED VIEW "Municipio".historico_casos AS
 SELECT dengue."data_iniSE",
    dengue."SE",
    (COALESCE(dengue.casos_est, (0.0)::real) + COALESCE(chik.casos_est, (0.0)::real)) AS casos_est,
    (COALESCE(dengue.casos_est_min, 0) + COALESCE(chik.casos_est_min, 0)) AS casos_est_min,
    (COALESCE(dengue.casos_est_max, 0) + COALESCE(chik.casos_est_max, 0)) AS casos_est_max,
    (COALESCE(dengue.casos, 0) + COALESCE(chik.casos, 0)) AS casos,
    dengue.municipio_geocodigo
   FROM ("Municipio"."Historico_alerta" dengue
     FULL JOIN "Municipio"."Historico_alerta_chik" chik ON (((dengue."SE" = chik."SE") AND (dengue.municipio_geocodigo = chik.municipio_geocodigo))))
  WITH NO DATA;


ALTER TABLE "Municipio".historico_casos OWNER TO dengueadmin;

--
-- Name: sprint202425; Type: TABLE; Schema: Municipio; Owner: dengueadmin
--

CREATE TABLE "Municipio".sprint202425 (
    date date,
    year bigint,
    epiweek bigint,
    casos bigint,
    geocode bigint,
    regional text,
    regional_geocode bigint,
    macroregional text,
    macroregional_geocode bigint,
    uf text,
    train_1 boolean,
    train_2 boolean,
    target_1 boolean,
    target_2 boolean,
    id integer NOT NULL
);


ALTER TABLE "Municipio".sprint202425 OWNER TO dengueadmin;

--
-- Name: sprint202425_id_seq; Type: SEQUENCE; Schema: Municipio; Owner: dengueadmin
--

CREATE SEQUENCE "Municipio".sprint202425_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "Municipio".sprint202425_id_seq OWNER TO dengueadmin;

--
-- Name: sprint202425_id_seq; Type: SEQUENCE OWNED BY; Schema: Municipio; Owner: dengueadmin
--

ALTER SEQUENCE "Municipio".sprint202425_id_seq OWNED BY "Municipio".sprint202425.id;


--
-- Name: alerta_mrj; Type: TABLE; Schema: archive_alertas_regionais; Owner: dengueadmin
--

CREATE TABLE archive_alertas_regionais.alerta_mrj (
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


ALTER TABLE archive_alertas_regionais.alerta_mrj OWNER TO dengueadmin;

--
-- Name: alerta_mrj_chik; Type: TABLE; Schema: archive_alertas_regionais; Owner: dengueadmin
--

CREATE TABLE archive_alertas_regionais.alerta_mrj_chik (
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


ALTER TABLE archive_alertas_regionais.alerta_mrj_chik OWNER TO dengueadmin;

--
-- Name: alerta_mrj_chik_id_seq; Type: SEQUENCE; Schema: archive_alertas_regionais; Owner: dengueadmin
--

CREATE SEQUENCE archive_alertas_regionais.alerta_mrj_chik_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE archive_alertas_regionais.alerta_mrj_chik_id_seq OWNER TO dengueadmin;

--
-- Name: alerta_mrj_chik_id_seq; Type: SEQUENCE OWNED BY; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER SEQUENCE archive_alertas_regionais.alerta_mrj_chik_id_seq OWNED BY archive_alertas_regionais.alerta_mrj_chik.id;


--
-- Name: alerta_mrj_id_seq; Type: SEQUENCE; Schema: archive_alertas_regionais; Owner: dengueadmin
--

CREATE SEQUENCE archive_alertas_regionais.alerta_mrj_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE archive_alertas_regionais.alerta_mrj_id_seq OWNER TO dengueadmin;

--
-- Name: alerta_mrj_id_seq; Type: SEQUENCE OWNED BY; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER SEQUENCE archive_alertas_regionais.alerta_mrj_id_seq OWNED BY archive_alertas_regionais.alerta_mrj.id;


--
-- Name: alerta_mrj_zika; Type: TABLE; Schema: archive_alertas_regionais; Owner: postgres
--

CREATE TABLE archive_alertas_regionais.alerta_mrj_zika (
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


ALTER TABLE archive_alertas_regionais.alerta_mrj_zika OWNER TO postgres;

--
-- Name: alerta_mrj_zika_id_seq; Type: SEQUENCE; Schema: archive_alertas_regionais; Owner: postgres
--

CREATE SEQUENCE archive_alertas_regionais.alerta_mrj_zika_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE archive_alertas_regionais.alerta_mrj_zika_id_seq OWNER TO postgres;

--
-- Name: alerta_mrj_zika_id_seq; Type: SEQUENCE OWNED BY; Schema: archive_alertas_regionais; Owner: postgres
--

ALTER SEQUENCE archive_alertas_regionais.alerta_mrj_zika_id_seq OWNED BY archive_alertas_regionais.alerta_mrj_zika.id;


--
-- Name: alerta_regional_chik; Type: TABLE; Schema: archive_alertas_regionais; Owner: dengueadmin
--

CREATE TABLE archive_alertas_regionais.alerta_regional_chik (
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


ALTER TABLE archive_alertas_regionais.alerta_regional_chik OWNER TO dengueadmin;

--
-- Name: alerta_regional_chik_id_seq; Type: SEQUENCE; Schema: archive_alertas_regionais; Owner: dengueadmin
--

CREATE SEQUENCE archive_alertas_regionais.alerta_regional_chik_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE archive_alertas_regionais.alerta_regional_chik_id_seq OWNER TO dengueadmin;

--
-- Name: alerta_regional_chik_id_seq; Type: SEQUENCE OWNED BY; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER SEQUENCE archive_alertas_regionais.alerta_regional_chik_id_seq OWNED BY archive_alertas_regionais.alerta_regional_chik.id;


--
-- Name: alerta_regional_dengue; Type: TABLE; Schema: archive_alertas_regionais; Owner: dengueadmin
--

CREATE TABLE archive_alertas_regionais.alerta_regional_dengue (
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


ALTER TABLE archive_alertas_regionais.alerta_regional_dengue OWNER TO dengueadmin;

--
-- Name: alerta_regional_dengue_id_seq; Type: SEQUENCE; Schema: archive_alertas_regionais; Owner: dengueadmin
--

CREATE SEQUENCE archive_alertas_regionais.alerta_regional_dengue_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE archive_alertas_regionais.alerta_regional_dengue_id_seq OWNER TO dengueadmin;

--
-- Name: alerta_regional_dengue_id_seq; Type: SEQUENCE OWNED BY; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER SEQUENCE archive_alertas_regionais.alerta_regional_dengue_id_seq OWNED BY archive_alertas_regionais.alerta_regional_dengue.id;


--
-- Name: alerta_regional_zika; Type: TABLE; Schema: archive_alertas_regionais; Owner: dengueadmin
--

CREATE TABLE archive_alertas_regionais.alerta_regional_zika (
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


ALTER TABLE archive_alertas_regionais.alerta_regional_zika OWNER TO dengueadmin;

--
-- Name: alerta_regional_zika_id_seq; Type: SEQUENCE; Schema: archive_alertas_regionais; Owner: dengueadmin
--

CREATE SEQUENCE archive_alertas_regionais.alerta_regional_zika_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE archive_alertas_regionais.alerta_regional_zika_id_seq OWNER TO dengueadmin;

--
-- Name: alerta_regional_zika_id_seq; Type: SEQUENCE OWNED BY; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER SEQUENCE archive_alertas_regionais.alerta_regional_zika_id_seq OWNED BY archive_alertas_regionais.alerta_regional_zika.id;


--
-- Name: Bairro; Type: TABLE; Schema: archive_ovitrampa; Owner: administrador
--

CREATE TABLE archive_ovitrampa."Bairro" (
    nome text NOT NULL,
    bairro_id integer NOT NULL,
    "Localidade_id" integer NOT NULL,
    id bigint NOT NULL
);


ALTER TABLE archive_ovitrampa."Bairro" OWNER TO administrador;

--
-- Name: TABLE "Bairro"; Type: COMMENT; Schema: archive_ovitrampa; Owner: administrador
--

COMMENT ON TABLE archive_ovitrampa."Bairro" IS 'Lista de bairros por localidade';


--
-- Name: Bairro_id_seq; Type: SEQUENCE; Schema: archive_ovitrampa; Owner: administrador
--

CREATE SEQUENCE archive_ovitrampa."Bairro_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE archive_ovitrampa."Bairro_id_seq" OWNER TO administrador;

--
-- Name: Bairro_id_seq; Type: SEQUENCE OWNED BY; Schema: archive_ovitrampa; Owner: administrador
--

ALTER SEQUENCE archive_ovitrampa."Bairro_id_seq" OWNED BY archive_ovitrampa."Bairro".id;


--
-- Name: Localidade; Type: TABLE; Schema: archive_ovitrampa; Owner: administrador
--

CREATE TABLE archive_ovitrampa."Localidade" (
    nome character varying(32) NOT NULL,
    populacao integer NOT NULL,
    geojson text NOT NULL,
    id integer NOT NULL,
    "Municipio_geocodigo" integer NOT NULL,
    codigo_estacao_wu character varying(5) DEFAULT NULL::character varying
);


ALTER TABLE archive_ovitrampa."Localidade" OWNER TO administrador;

--
-- Name: TABLE "Localidade"; Type: COMMENT; Schema: archive_ovitrampa; Owner: administrador
--

COMMENT ON TABLE archive_ovitrampa."Localidade" IS 'Sub-unidades de analise no municipio';


--
-- Name: Ovitrampa; Type: TABLE; Schema: archive_ovitrampa; Owner: administrador
--

CREATE TABLE archive_ovitrampa."Ovitrampa" (
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


ALTER TABLE archive_ovitrampa."Ovitrampa" OWNER TO administrador;

--
-- Name: Ovitrampa_id_seq; Type: SEQUENCE; Schema: archive_ovitrampa; Owner: administrador
--

CREATE SEQUENCE archive_ovitrampa."Ovitrampa_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE archive_ovitrampa."Ovitrampa_id_seq" OWNER TO administrador;

--
-- Name: Ovitrampa_id_seq; Type: SEQUENCE OWNED BY; Schema: archive_ovitrampa; Owner: administrador
--

ALTER SEQUENCE archive_ovitrampa."Ovitrampa_id_seq" OWNED BY archive_ovitrampa."Ovitrampa".id;


--
-- Name: run; Type: TABLE; Schema: ingestion; Owner: dengueadmin
--

CREATE TABLE ingestion.run (
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    status character varying(16) NOT NULL,
    attempts integer NOT NULL,
    uf character varying(2) NOT NULL,
    source_format character varying(16) NOT NULL,
    disease character varying(16) NOT NULL,
    delivery_year smallint NOT NULL,
    delivery_week smallint NOT NULL,
    delivery_se integer NOT NULL,
    source_path text NOT NULL,
    filename text NOT NULL,
    sha256 character varying(64) NOT NULL,
    size_bytes bigint NOT NULL,
    mtime timestamp with time zone,
    celery_task_id text,
    worker_hostname text,
    rows_read bigint NOT NULL,
    rows_parsed bigint NOT NULL,
    rows_loaded bigint NOT NULL,
    rows_failed bigint NOT NULL,
    metadata jsonb NOT NULL,
    errors jsonb NOT NULL,
    rows_duplicate bigint NOT NULL,
    CONSTRAINT run_attempts_check CHECK ((attempts >= 0))
);


ALTER TABLE ingestion.run OWNER TO dengueadmin;

--
-- Name: sinan_stage; Type: TABLE; Schema: ingestion; Owner: dengueadmin
--

CREATE TABLE ingestion.sinan_stage (
    id bigint NOT NULL,
    chunk_id integer NOT NULL,
    source_rownum bigint NOT NULL,
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
    resul_pcr double precision,
    criterio double precision,
    classi_fin double precision,
    dt_chik_s1 date,
    dt_chik_s2 date,
    dt_prnt date,
    res_chiks1 character varying(255),
    res_chiks2 character varying(255),
    resul_prnt character varying(255),
    dt_soro date,
    resul_soro character varying(255),
    dt_ns1 date,
    resul_ns1 character varying(255),
    dt_viral date,
    resul_vi_n character varying(255),
    dt_pcr date,
    sorotipo character varying(255),
    id_distrit double precision,
    id_bairro double precision,
    nm_bairro character varying(255),
    id_unidade double precision,
    created_at timestamp with time zone NOT NULL,
    run_id uuid NOT NULL
);


ALTER TABLE ingestion.sinan_stage OWNER TO dengueadmin;

--
-- Name: sinan_stage_id_seq; Type: SEQUENCE; Schema: ingestion; Owner: dengueadmin
--

CREATE SEQUENCE ingestion.sinan_stage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE ingestion.sinan_stage_id_seq OWNER TO dengueadmin;

--
-- Name: sinan_stage_id_seq; Type: SEQUENCE OWNED BY; Schema: ingestion; Owner: dengueadmin
--

ALTER SEQUENCE ingestion.sinan_stage_id_seq OWNED BY ingestion.sinan_stage.id;


--
-- Name: "Municipio"."Notificacao"; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public."""Municipio"".""Notificacao""" (
    "NU_NOTIFIC" text,
    "TP_NOT" text,
    "ID_AGRAVO" text,
    "DT_NOTIFIC" text,
    "SEM_NOT" text,
    "NU_ANO" text,
    "SG_UF_NOT" text,
    "ID_MUNICIP" text,
    "ID_REGIONA" text,
    "ID_UNIDADE" text,
    "DT_SIN_PRI" text,
    "SEM_PRI" text,
    "DT_NASC" text,
    "NU_IDADE_N" text,
    "CS_SEXO" text,
    "CS_GESTANT" text,
    "CS_RACA" text,
    "CS_ESCOL_N" text,
    "SG_UF" text,
    "ID_MN_RESI" text,
    "ID_RG_RESI" text,
    "ID_DISTRIT" text,
    "ID_BAIRRO" text,
    "NM_BAIRRO" text,
    "ID_LOGRADO" text,
    "CS_ZONA" text,
    "ID_PAIS" text,
    "DT_INVEST" text,
    "ID_OCUPA_N" text,
    "FEBRE" text,
    "MIALGIA" text,
    "CEFALEIA" text,
    "EXANTEMA" text,
    "VOMITO" text,
    "NAUSEA" text,
    "DOR_COSTAS" text,
    "CONJUNTVIT" text,
    "ARTRITE" text,
    "ARTRALGIA" text,
    "PETEQUIA_N" text,
    "LEUCOPENIA" text,
    "LACO" text,
    "DOR_RETRO" text,
    "DIABETES" text,
    "HEMATOLOG" text,
    "HEPATOPAT" text,
    "RENAL" text,
    "HIPERTENSA" text,
    "ACIDO_PEPT" text,
    "AUTO_IMUNE" text,
    "DT_CHIK_S1" text,
    "DT_CHIK_S2" text,
    "DT_PRNT" text,
    "RES_CHIKS1" text,
    "RES_CHIKS2" text,
    "RESUL_PRNT" text,
    "DT_SORO" text,
    "RESUL_SORO" text,
    "DT_NS1" text,
    "RESUL_NS1" text,
    "DT_VIRAL" text,
    "RESUL_VI_N" text,
    "DT_PCR" text,
    "RESUL_PCR_" text,
    "SOROTIPO" text,
    "HISTOPA_N" text,
    "IMUNOH_N" text,
    "HOSPITALIZ" text,
    "DT_INTERNA" text,
    "UF" text,
    "MUNICIPIO" text,
    "CLASSI_FIN" text,
    "CRITERIO" text,
    "DOENCA_TRA" text,
    "CLINC_CHIK" text,
    "EVOLUCAO" text,
    "DT_OBITO" text,
    "DT_ENCERRA" text,
    "ALRM_HIPOT" text,
    "ALRM_PLAQ" text,
    "ALRM_VOM" text,
    "ALRM_SANG" text,
    "ALRM_HEMAT" text,
    "ALRM_ABDOM" text,
    "ALRM_LETAR" text,
    "ALRM_HEPAT" text,
    "ALRM_LIQ" text,
    "DT_ALRM" text,
    "GRAV_PULSO" text,
    "GRAV_CONV" text,
    "GRAV_ENCH" text,
    "GRAV_INSUF" text,
    "GRAV_TAQUI" text,
    "GRAV_EXTRE" text,
    "GRAV_HIPOT" text,
    "GRAV_HEMAT" text,
    "GRAV_MELEN" text,
    "GRAV_METRO" text,
    "GRAV_SANG" text,
    "GRAV_AST" text,
    "GRAV_MIOC" text,
    "GRAV_CONSC" text,
    "GRAV_ORGAO" text,
    "DT_GRAV" text,
    "MANI_HEMOR" text,
    "EPISTAXE" text,
    "GENGIVO" text,
    "METRO" text,
    "PETEQUIAS" text,
    "HEMATURA" text,
    "SANGRAM" text,
    "LACO_N" text,
    "PLASMATICO" text,
    "EVIDENCIA" text,
    "PLAQ_MENOR" text,
    "CON_FHD" text,
    "COMPLICA" text,
    "NU_LOTE_I" text,
    "DS_OBS" text,
    "TP_SISTEMA" text,
    "NDUPLIC_N" text,
    "DT_DIGITA" text
);


ALTER TABLE public."""Municipio"".""Notificacao""" OWNER TO dengueadmin;

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
-- Name: authtoken_token; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.authtoken_token (
    key character varying(40) NOT NULL,
    created timestamp with time zone NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.authtoken_token OWNER TO dengueadmin;

--
-- Name: chik_casprov_fill_stage; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.chik_casprov_fill_stage (
    municipio_geocodigo integer NOT NULL,
    "SE" integer NOT NULL,
    casprov integer NOT NULL
);


ALTER TABLE public.chik_casprov_fill_stage OWNER TO dengueadmin;

--
-- Name: city_count_by_uf_chikungunya_materialized_view; Type: MATERIALIZED VIEW; Schema: public; Owner: dengueadmin
--

CREATE MATERIALIZED VIEW public.city_count_by_uf_chikungunya_materialized_view AS
 SELECT b.uf,
    'chikungunya'::text AS disease,
    count(DISTINCT a.municipio_geocodigo) AS city_count
   FROM ("Municipio"."Historico_alerta_chik" a
     JOIN "Dengue_global"."Municipio" b ON ((a.municipio_geocodigo = b.geocodigo)))
  GROUP BY b.uf
  WITH NO DATA;


ALTER TABLE public.city_count_by_uf_chikungunya_materialized_view OWNER TO dengueadmin;

--
-- Name: city_count_by_uf_dengue_materialized_view; Type: MATERIALIZED VIEW; Schema: public; Owner: dengueadmin
--

CREATE MATERIALIZED VIEW public.city_count_by_uf_dengue_materialized_view AS
 SELECT b.uf,
    'dengue'::text AS disease,
    count(DISTINCT a.municipio_geocodigo) AS city_count
   FROM ("Municipio"."Historico_alerta" a
     JOIN "Dengue_global"."Municipio" b ON ((a.municipio_geocodigo = b.geocodigo)))
  GROUP BY b.uf
  WITH NO DATA;


ALTER TABLE public.city_count_by_uf_dengue_materialized_view OWNER TO dengueadmin;

--
-- Name: city_count_by_uf_zika_materialized_view; Type: MATERIALIZED VIEW; Schema: public; Owner: dengueadmin
--

CREATE MATERIALIZED VIEW public.city_count_by_uf_zika_materialized_view AS
 SELECT b.uf,
    'zika'::text AS disease,
    count(DISTINCT a.municipio_geocodigo) AS city_count
   FROM ("Municipio"."Historico_alerta_zika" a
     JOIN "Dengue_global"."Municipio" b ON ((a.municipio_geocodigo = b.geocodigo)))
  GROUP BY b.uf
  WITH NO DATA;


ALTER TABLE public.city_count_by_uf_zika_materialized_view OWNER TO dengueadmin;

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
-- Name: dengue_casprov_fill_stage; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.dengue_casprov_fill_stage (
    municipio_geocodigo integer NOT NULL,
    "SE" integer NOT NULL,
    casprov integer NOT NULL
);


ALTER TABLE public.dengue_casprov_fill_stage OWNER TO dengueadmin;

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
-- Name: django_celery_beat_clockedschedule; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_celery_beat_clockedschedule (
    id integer NOT NULL,
    clocked_time timestamp with time zone NOT NULL
);


ALTER TABLE public.django_celery_beat_clockedschedule OWNER TO dengueadmin;

--
-- Name: django_celery_beat_clockedschedule_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.django_celery_beat_clockedschedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_beat_clockedschedule_id_seq OWNER TO dengueadmin;

--
-- Name: django_celery_beat_clockedschedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.django_celery_beat_clockedschedule_id_seq OWNED BY public.django_celery_beat_clockedschedule.id;


--
-- Name: django_celery_beat_crontabschedule; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_celery_beat_crontabschedule (
    id integer NOT NULL,
    minute character varying(240) NOT NULL,
    hour character varying(96) NOT NULL,
    day_of_week character varying(64) NOT NULL,
    day_of_month character varying(124) NOT NULL,
    month_of_year character varying(64) NOT NULL,
    timezone character varying(63) NOT NULL
);


ALTER TABLE public.django_celery_beat_crontabschedule OWNER TO dengueadmin;

--
-- Name: django_celery_beat_crontabschedule_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.django_celery_beat_crontabschedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_beat_crontabschedule_id_seq OWNER TO dengueadmin;

--
-- Name: django_celery_beat_crontabschedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.django_celery_beat_crontabschedule_id_seq OWNED BY public.django_celery_beat_crontabschedule.id;


--
-- Name: django_celery_beat_intervalschedule; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_celery_beat_intervalschedule (
    id integer NOT NULL,
    every integer NOT NULL,
    period character varying(24) NOT NULL
);


ALTER TABLE public.django_celery_beat_intervalschedule OWNER TO dengueadmin;

--
-- Name: django_celery_beat_intervalschedule_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.django_celery_beat_intervalschedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_beat_intervalschedule_id_seq OWNER TO dengueadmin;

--
-- Name: django_celery_beat_intervalschedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.django_celery_beat_intervalschedule_id_seq OWNED BY public.django_celery_beat_intervalschedule.id;


--
-- Name: django_celery_beat_periodictask; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_celery_beat_periodictask (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    task character varying(200) NOT NULL,
    args text NOT NULL,
    kwargs text NOT NULL,
    queue character varying(200),
    exchange character varying(200),
    routing_key character varying(200),
    expires timestamp with time zone,
    enabled boolean NOT NULL,
    last_run_at timestamp with time zone,
    total_run_count integer NOT NULL,
    date_changed timestamp with time zone NOT NULL,
    description text NOT NULL,
    crontab_id integer,
    interval_id integer,
    solar_id integer,
    one_off boolean NOT NULL,
    start_time timestamp with time zone,
    priority integer,
    headers text NOT NULL,
    clocked_id integer,
    expire_seconds integer,
    CONSTRAINT django_celery_beat_periodictask_expire_seconds_check CHECK ((expire_seconds >= 0)),
    CONSTRAINT django_celery_beat_periodictask_priority_check CHECK ((priority >= 0)),
    CONSTRAINT django_celery_beat_periodictask_total_run_count_check CHECK ((total_run_count >= 0))
);


ALTER TABLE public.django_celery_beat_periodictask OWNER TO dengueadmin;

--
-- Name: django_celery_beat_periodictask_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.django_celery_beat_periodictask_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_beat_periodictask_id_seq OWNER TO dengueadmin;

--
-- Name: django_celery_beat_periodictask_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.django_celery_beat_periodictask_id_seq OWNED BY public.django_celery_beat_periodictask.id;


--
-- Name: django_celery_beat_periodictasks; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_celery_beat_periodictasks (
    ident smallint NOT NULL,
    last_update timestamp with time zone NOT NULL
);


ALTER TABLE public.django_celery_beat_periodictasks OWNER TO dengueadmin;

--
-- Name: django_celery_beat_solarschedule; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_celery_beat_solarschedule (
    id integer NOT NULL,
    event character varying(24) NOT NULL,
    latitude numeric(9,6) NOT NULL,
    longitude numeric(9,6) NOT NULL
);


ALTER TABLE public.django_celery_beat_solarschedule OWNER TO dengueadmin;

--
-- Name: django_celery_beat_solarschedule_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.django_celery_beat_solarschedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_beat_solarschedule_id_seq OWNER TO dengueadmin;

--
-- Name: django_celery_beat_solarschedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.django_celery_beat_solarschedule_id_seq OWNED BY public.django_celery_beat_solarschedule.id;


--
-- Name: django_celery_results_chordcounter; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_celery_results_chordcounter (
    id integer NOT NULL,
    group_id character varying(255) NOT NULL,
    sub_tasks text NOT NULL,
    count integer NOT NULL,
    CONSTRAINT django_celery_results_chordcounter_count_check CHECK ((count >= 0))
);


ALTER TABLE public.django_celery_results_chordcounter OWNER TO dengueadmin;

--
-- Name: django_celery_results_chordcounter_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.django_celery_results_chordcounter_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_results_chordcounter_id_seq OWNER TO dengueadmin;

--
-- Name: django_celery_results_chordcounter_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.django_celery_results_chordcounter_id_seq OWNED BY public.django_celery_results_chordcounter.id;


--
-- Name: django_celery_results_groupresult; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_celery_results_groupresult (
    id integer NOT NULL,
    group_id character varying(255) NOT NULL,
    date_created timestamp with time zone NOT NULL,
    date_done timestamp with time zone NOT NULL,
    content_type character varying(128) NOT NULL,
    content_encoding character varying(64) NOT NULL,
    result text
);


ALTER TABLE public.django_celery_results_groupresult OWNER TO dengueadmin;

--
-- Name: django_celery_results_groupresult_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.django_celery_results_groupresult_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_results_groupresult_id_seq OWNER TO dengueadmin;

--
-- Name: django_celery_results_groupresult_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.django_celery_results_groupresult_id_seq OWNED BY public.django_celery_results_groupresult.id;


--
-- Name: django_celery_results_taskresult; Type: TABLE; Schema: public; Owner: dengueadmin
--

CREATE TABLE public.django_celery_results_taskresult (
    id integer NOT NULL,
    task_id character varying(255) NOT NULL,
    status character varying(50) NOT NULL,
    content_type character varying(128) NOT NULL,
    content_encoding character varying(64) NOT NULL,
    result text,
    date_done timestamp with time zone NOT NULL,
    traceback text,
    meta text,
    task_args text,
    task_kwargs text,
    task_name character varying(255),
    worker character varying(100),
    date_created timestamp with time zone NOT NULL,
    periodic_task_name character varying(255),
    date_started timestamp with time zone
);


ALTER TABLE public.django_celery_results_taskresult OWNER TO dengueadmin;

--
-- Name: django_celery_results_taskresult_id_seq; Type: SEQUENCE; Schema: public; Owner: dengueadmin
--

CREATE SEQUENCE public.django_celery_results_taskresult_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_results_taskresult_id_seq OWNER TO dengueadmin;

--
-- Name: django_celery_results_taskresult_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dengueadmin
--

ALTER SEQUENCE public.django_celery_results_taskresult_id_seq OWNED BY public.django_celery_results_taskresult.id;


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
-- Name: epiyear_summary_materialized_view; Type: MATERIALIZED VIEW; Schema: public; Owner: dengueadmin
--

CREATE MATERIALIZED VIEW public.epiyear_summary_materialized_view AS
 SELECT notif.ano_notif,
    notif.se_notif,
    count(notif.se_notif) AS casos,
    municipio.uf,
    replace((notif.cid10_codigo)::text, '.'::text, ''::text) AS disease_code
   FROM ("Municipio"."Notificacao" notif
     JOIN "Dengue_global"."Municipio" municipio ON ((notif.municipio_geocodigo = municipio.geocodigo)))
  GROUP BY notif.ano_notif, notif.se_notif, municipio.uf, (replace((notif.cid10_codigo)::text, '.'::text, ''::text))
  WITH NO DATA;


ALTER TABLE public.epiyear_summary_materialized_view OWNER TO dengueadmin;

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
-- Name: copernicus_arg; Type: TABLE; Schema: weather; Owner: dengueadmin
--

CREATE TABLE weather.copernicus_arg (
    date timestamp without time zone,
    geocode text,
    temp_max double precision,
    precip_max double precision,
    umid_max double precision,
    pressao_max double precision,
    temp_med double precision,
    precip_med double precision,
    umid_med double precision,
    pressao_med double precision,
    temp_min double precision,
    precip_min double precision,
    umid_min double precision,
    pressao_min double precision,
    precip_tot double precision,
    epiweek text
);


ALTER TABLE weather.copernicus_arg OWNER TO dengueadmin;

--
-- Name: copernicus_bra; Type: TABLE; Schema: weather; Owner: dengueadmin
--

CREATE TABLE weather.copernicus_bra (
    date timestamp without time zone NOT NULL,
    geocode integer NOT NULL,
    temp_max double precision NOT NULL,
    precip_max double precision NOT NULL,
    umid_max double precision NOT NULL,
    pressao_max double precision NOT NULL,
    temp_med double precision NOT NULL,
    precip_med double precision NOT NULL,
    umid_med double precision NOT NULL,
    pressao_med double precision NOT NULL,
    temp_min double precision NOT NULL,
    precip_min double precision NOT NULL,
    umid_min double precision NOT NULL,
    pressao_min double precision NOT NULL,
    precip_tot double precision NOT NULL,
    epiweek integer NOT NULL
);


ALTER TABLE weather.copernicus_bra OWNER TO dengueadmin;

--
-- Name: copernicus_foz_do_iguacu; Type: TABLE; Schema: weather; Owner: dengueadmin
--

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

--
-- Name: copernicus_foz_do_iguacu_index_seq; Type: SEQUENCE; Schema: weather; Owner: dengueadmin
--

CREATE SEQUENCE weather.copernicus_foz_do_iguacu_index_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE weather.copernicus_foz_do_iguacu_index_seq OWNER TO dengueadmin;

--
-- Name: copernicus_foz_do_iguacu_index_seq; Type: SEQUENCE OWNED BY; Schema: weather; Owner: dengueadmin
--

ALTER SEQUENCE weather.copernicus_foz_do_iguacu_index_seq OWNED BY weather.copernicus_foz_do_iguacu.index;


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
-- Name: Tweet id; Type: DEFAULT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Tweet" ALTER COLUMN id SET DEFAULT nextval('"Municipio"."Tweet_id_seq"'::regclass);


--
-- Name: sprint202425 id; Type: DEFAULT; Schema: Municipio; Owner: dengueadmin
--

ALTER TABLE ONLY "Municipio".sprint202425 ALTER COLUMN id SET DEFAULT nextval('"Municipio".sprint202425_id_seq'::regclass);


--
-- Name: alerta_mrj id; Type: DEFAULT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj ALTER COLUMN id SET DEFAULT nextval('archive_alertas_regionais.alerta_mrj_id_seq'::regclass);


--
-- Name: alerta_mrj_chik id; Type: DEFAULT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj_chik ALTER COLUMN id SET DEFAULT nextval('archive_alertas_regionais.alerta_mrj_chik_id_seq'::regclass);


--
-- Name: alerta_mrj_zika id; Type: DEFAULT; Schema: archive_alertas_regionais; Owner: postgres
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj_zika ALTER COLUMN id SET DEFAULT nextval('archive_alertas_regionais.alerta_mrj_zika_id_seq'::regclass);


--
-- Name: alerta_regional_chik id; Type: DEFAULT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_regional_chik ALTER COLUMN id SET DEFAULT nextval('archive_alertas_regionais.alerta_regional_chik_id_seq'::regclass);


--
-- Name: alerta_regional_dengue id; Type: DEFAULT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_regional_dengue ALTER COLUMN id SET DEFAULT nextval('archive_alertas_regionais.alerta_regional_dengue_id_seq'::regclass);


--
-- Name: alerta_regional_zika id; Type: DEFAULT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_regional_zika ALTER COLUMN id SET DEFAULT nextval('archive_alertas_regionais.alerta_regional_zika_id_seq'::regclass);


--
-- Name: Bairro id; Type: DEFAULT; Schema: archive_ovitrampa; Owner: administrador
--

ALTER TABLE ONLY archive_ovitrampa."Bairro" ALTER COLUMN id SET DEFAULT nextval('archive_ovitrampa."Bairro_id_seq"'::regclass);


--
-- Name: Ovitrampa id; Type: DEFAULT; Schema: archive_ovitrampa; Owner: administrador
--

ALTER TABLE ONLY archive_ovitrampa."Ovitrampa" ALTER COLUMN id SET DEFAULT nextval('archive_ovitrampa."Ovitrampa_id_seq"'::regclass);


--
-- Name: sinan_stage id; Type: DEFAULT; Schema: ingestion; Owner: dengueadmin
--

ALTER TABLE ONLY ingestion.sinan_stage ALTER COLUMN id SET DEFAULT nextval('ingestion.sinan_stage_id_seq'::regclass);


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
-- Name: django_celery_beat_clockedschedule id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_clockedschedule ALTER COLUMN id SET DEFAULT nextval('public.django_celery_beat_clockedschedule_id_seq'::regclass);


--
-- Name: django_celery_beat_crontabschedule id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_crontabschedule ALTER COLUMN id SET DEFAULT nextval('public.django_celery_beat_crontabschedule_id_seq'::regclass);


--
-- Name: django_celery_beat_intervalschedule id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_intervalschedule ALTER COLUMN id SET DEFAULT nextval('public.django_celery_beat_intervalschedule_id_seq'::regclass);


--
-- Name: django_celery_beat_periodictask id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_periodictask ALTER COLUMN id SET DEFAULT nextval('public.django_celery_beat_periodictask_id_seq'::regclass);


--
-- Name: django_celery_beat_solarschedule id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_solarschedule ALTER COLUMN id SET DEFAULT nextval('public.django_celery_beat_solarschedule_id_seq'::regclass);


--
-- Name: django_celery_results_chordcounter id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_results_chordcounter ALTER COLUMN id SET DEFAULT nextval('public.django_celery_results_chordcounter_id_seq'::regclass);


--
-- Name: django_celery_results_groupresult id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_results_groupresult ALTER COLUMN id SET DEFAULT nextval('public.django_celery_results_groupresult_id_seq'::regclass);


--
-- Name: django_celery_results_taskresult id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_results_taskresult ALTER COLUMN id SET DEFAULT nextval('public.django_celery_results_taskresult_id_seq'::regclass);


--
-- Name: django_content_type id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_content_type ALTER COLUMN id SET DEFAULT nextval('public.django_content_type_id_seq'::regclass);


--
-- Name: django_migrations id; Type: DEFAULT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_migrations ALTER COLUMN id SET DEFAULT nextval('public.django_migrations_id_seq'::regclass);


--
-- Name: copernicus_foz_do_iguacu index; Type: DEFAULT; Schema: weather; Owner: dengueadmin
--

ALTER TABLE ONLY weather.copernicus_foz_do_iguacu ALTER COLUMN index SET DEFAULT nextval('weather.copernicus_foz_do_iguacu_index_seq'::regclass);


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
    ADD CONSTRAINT parameters_pkey PRIMARY KEY (municipio_geocodigo, cid10);


--
-- Name: parameters_uf parameters_uf_pkey; Type: CONSTRAINT; Schema: Dengue_global; Owner: postgres
--

ALTER TABLE ONLY "Dengue_global".parameters_uf
    ADD CONSTRAINT parameters_uf_pkey PRIMARY KEY (state_code, cid10);


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
-- Name: Notificacao Notificacao_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Notificacao"
    ADD CONSTRAINT "Notificacao_pk" PRIMARY KEY (id);


--
-- Name: Tweet Tweet_pk; Type: CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Tweet"
    ADD CONSTRAINT "Tweet_pk" PRIMARY KEY (id);


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
-- Name: sprint202425 sprint202425_pkey; Type: CONSTRAINT; Schema: Municipio; Owner: dengueadmin
--

ALTER TABLE ONLY "Municipio".sprint202425
    ADD CONSTRAINT sprint202425_pkey PRIMARY KEY (id);


--
-- Name: alerta_mrj_chik alerta_mrj_chik_pk; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj_chik
    ADD CONSTRAINT alerta_mrj_chik_pk PRIMARY KEY (id);


--
-- Name: alerta_mrj alerta_mrj_pk; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj
    ADD CONSTRAINT alerta_mrj_pk PRIMARY KEY (id);


--
-- Name: alerta_mrj_zika alerta_mrj_zika_pk; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: postgres
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj_zika
    ADD CONSTRAINT alerta_mrj_zika_pk PRIMARY KEY (id);


--
-- Name: alerta_regional_chik alertaregionalchik_pk; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_regional_chik
    ADD CONSTRAINT alertaregionalchik_pk PRIMARY KEY (id);


--
-- Name: alerta_regional_dengue alertaregionaldengue_pk; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_regional_dengue
    ADD CONSTRAINT alertaregionaldengue_pk PRIMARY KEY (id);


--
-- Name: alerta_regional_zika alertaregionalzika_pk; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_regional_zika
    ADD CONSTRAINT alertaregionalzika_pk PRIMARY KEY (id);


--
-- Name: alerta_mrj previsao; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj
    ADD CONSTRAINT previsao UNIQUE (aps, se);


--
-- Name: alerta_mrj_chik previsao_chik; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj_chik
    ADD CONSTRAINT previsao_chik UNIQUE (aps, se);


--
-- Name: alerta_mrj_zika previsao_zika; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: postgres
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj_zika
    ADD CONSTRAINT previsao_zika UNIQUE (aps, se);


--
-- Name: alerta_mrj unique_aps_se; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj
    ADD CONSTRAINT unique_aps_se UNIQUE (se, aps);


--
-- Name: alerta_mrj_chik unique_chik_aps_se; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj_chik
    ADD CONSTRAINT unique_chik_aps_se UNIQUE (se, aps);


--
-- Name: alerta_mrj_zika unique_zika_aps_se; Type: CONSTRAINT; Schema: archive_alertas_regionais; Owner: postgres
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_mrj_zika
    ADD CONSTRAINT unique_zika_aps_se UNIQUE (se, aps);


--
-- Name: Bairro Bairro_pkey; Type: CONSTRAINT; Schema: archive_ovitrampa; Owner: administrador
--

ALTER TABLE ONLY archive_ovitrampa."Bairro"
    ADD CONSTRAINT "Bairro_pkey" PRIMARY KEY (id);


--
-- Name: Localidade Localidade_pk; Type: CONSTRAINT; Schema: archive_ovitrampa; Owner: administrador
--

ALTER TABLE ONLY archive_ovitrampa."Localidade"
    ADD CONSTRAINT "Localidade_pk" PRIMARY KEY (id);


--
-- Name: Ovitrampa Ovitrampa_pk; Type: CONSTRAINT; Schema: archive_ovitrampa; Owner: administrador
--

ALTER TABLE ONLY archive_ovitrampa."Ovitrampa"
    ADD CONSTRAINT "Ovitrampa_pk" PRIMARY KEY (id);


--
-- Name: run run_pkey; Type: CONSTRAINT; Schema: ingestion; Owner: dengueadmin
--

ALTER TABLE ONLY ingestion.run
    ADD CONSTRAINT run_pkey PRIMARY KEY (id);


--
-- Name: run run_sha256_key; Type: CONSTRAINT; Schema: ingestion; Owner: dengueadmin
--

ALTER TABLE ONLY ingestion.run
    ADD CONSTRAINT run_sha256_key UNIQUE (sha256);


--
-- Name: sinan_stage sinan_stage_pkey; Type: CONSTRAINT; Schema: ingestion; Owner: dengueadmin
--

ALTER TABLE ONLY ingestion.sinan_stage
    ADD CONSTRAINT sinan_stage_pkey PRIMARY KEY (id);


--
-- Name: sinan_stage ux_ing_sinan_stage_row; Type: CONSTRAINT; Schema: ingestion; Owner: dengueadmin
--

ALTER TABLE ONLY ingestion.sinan_stage
    ADD CONSTRAINT ux_ing_sinan_stage_row UNIQUE (run_id, chunk_id, source_rownum);


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
-- Name: authtoken_token authtoken_token_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_pkey PRIMARY KEY (key);


--
-- Name: authtoken_token authtoken_token_user_id_key; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_key UNIQUE (user_id);


--
-- Name: chik_casprov_fill_stage chik_casprov_fill_stage_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.chik_casprov_fill_stage
    ADD CONSTRAINT chik_casprov_fill_stage_pkey PRIMARY KEY (municipio_geocodigo, "SE");


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
-- Name: dengue_casprov_fill_stage dengue_casprov_fill_stage_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.dengue_casprov_fill_stage
    ADD CONSTRAINT dengue_casprov_fill_stage_pkey PRIMARY KEY (municipio_geocodigo, "SE");


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_celery_beat_clockedschedule django_celery_beat_clockedschedule_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_clockedschedule
    ADD CONSTRAINT django_celery_beat_clockedschedule_pkey PRIMARY KEY (id);


--
-- Name: django_celery_beat_crontabschedule django_celery_beat_crontabschedule_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_crontabschedule
    ADD CONSTRAINT django_celery_beat_crontabschedule_pkey PRIMARY KEY (id);


--
-- Name: django_celery_beat_intervalschedule django_celery_beat_intervalschedule_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_intervalschedule
    ADD CONSTRAINT django_celery_beat_intervalschedule_pkey PRIMARY KEY (id);


--
-- Name: django_celery_beat_periodictask django_celery_beat_periodictask_name_key; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_periodictask_name_key UNIQUE (name);


--
-- Name: django_celery_beat_periodictask django_celery_beat_periodictask_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_periodictask_pkey PRIMARY KEY (id);


--
-- Name: django_celery_beat_periodictasks django_celery_beat_periodictasks_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_periodictasks
    ADD CONSTRAINT django_celery_beat_periodictasks_pkey PRIMARY KEY (ident);


--
-- Name: django_celery_beat_solarschedule django_celery_beat_solar_event_latitude_longitude_ba64999a_uniq; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_solarschedule
    ADD CONSTRAINT django_celery_beat_solar_event_latitude_longitude_ba64999a_uniq UNIQUE (event, latitude, longitude);


--
-- Name: django_celery_beat_solarschedule django_celery_beat_solarschedule_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_solarschedule
    ADD CONSTRAINT django_celery_beat_solarschedule_pkey PRIMARY KEY (id);


--
-- Name: django_celery_results_chordcounter django_celery_results_chordcounter_group_id_key; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_results_chordcounter
    ADD CONSTRAINT django_celery_results_chordcounter_group_id_key UNIQUE (group_id);


--
-- Name: django_celery_results_chordcounter django_celery_results_chordcounter_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_results_chordcounter
    ADD CONSTRAINT django_celery_results_chordcounter_pkey PRIMARY KEY (id);


--
-- Name: django_celery_results_groupresult django_celery_results_groupresult_group_id_key; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_results_groupresult
    ADD CONSTRAINT django_celery_results_groupresult_group_id_key UNIQUE (group_id);


--
-- Name: django_celery_results_groupresult django_celery_results_groupresult_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_results_groupresult
    ADD CONSTRAINT django_celery_results_groupresult_pkey PRIMARY KEY (id);


--
-- Name: django_celery_results_taskresult django_celery_results_taskresult_pkey; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_results_taskresult
    ADD CONSTRAINT django_celery_results_taskresult_pkey PRIMARY KEY (id);


--
-- Name: django_celery_results_taskresult django_celery_results_taskresult_task_id_key; Type: CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_results_taskresult
    ADD CONSTRAINT django_celery_results_taskresult_task_id_key UNIQUE (task_id);


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
-- Name: copernicus_bra copernicus_bra_unique_date_geocode; Type: CONSTRAINT; Schema: weather; Owner: dengueadmin
--

ALTER TABLE ONLY weather.copernicus_bra
    ADD CONSTRAINT copernicus_bra_unique_date_geocode UNIQUE (date, geocode);


--
-- Name: copernicus_foz_do_iguacu copernicus_foz_do_iguacu_pkey; Type: CONSTRAINT; Schema: weather; Owner: dengueadmin
--

ALTER TABLE ONLY weather.copernicus_foz_do_iguacu
    ADD CONSTRAINT copernicus_foz_do_iguacu_pkey PRIMARY KEY (index);


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
-- Name: parameters_uf_idx_state_code; Type: INDEX; Schema: Dengue_global; Owner: postgres
--

CREATE INDEX parameters_uf_idx_state_code ON "Dengue_global".parameters_uf USING btree (state_code);


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
-- Name: estacoes_idx; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX estacoes_idx ON "Municipio"."Clima_cemaden" USING btree ("Estacao_cemaden_codestacao");


--
-- Name: historico_casos_data_inise_idx; Type: INDEX; Schema: Municipio; Owner: dengueadmin
--

CREATE INDEX historico_casos_data_inise_idx ON "Municipio".historico_casos USING btree ("data_iniSE" DESC);


--
-- Name: historico_casos_municipio_geocodigo_idx; Type: INDEX; Schema: Municipio; Owner: dengueadmin
--

CREATE INDEX historico_casos_municipio_geocodigo_idx ON "Municipio".historico_casos USING btree (municipio_geocodigo DESC);


--
-- Name: notificacao_api_city_cid10_year_date_id_idx; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX notificacao_api_city_cid10_year_date_id_idx ON "Municipio"."Notificacao" USING btree (municipio_geocodigo, cid10_codigo, ano_notif, dt_notific DESC, id DESC);


--
-- Name: notificacao_cid10_idx; Type: INDEX; Schema: Municipio; Owner: administrador
--

CREATE INDEX notificacao_cid10_idx ON "Municipio"."Notificacao" USING btree (cid10_codigo);


--
-- Name: ix_ing_run_scope; Type: INDEX; Schema: ingestion; Owner: dengueadmin
--

CREATE INDEX ix_ing_run_scope ON ingestion.run USING btree (uf, disease, delivery_se DESC);


--
-- Name: ix_ing_run_status_created; Type: INDEX; Schema: ingestion; Owner: dengueadmin
--

CREATE INDEX ix_ing_run_status_created ON ingestion.run USING btree (status, created_at DESC);


--
-- Name: ix_ing_sinan_stage_keys; Type: INDEX; Schema: ingestion; Owner: dengueadmin
--

CREATE INDEX ix_ing_sinan_stage_keys ON ingestion.sinan_stage USING btree (run_id, cid10_codigo, nu_notific, municipio_geocodigo);


--
-- Name: ix_ing_sinan_stage_run; Type: INDEX; Schema: ingestion; Owner: dengueadmin
--

CREATE INDEX ix_ing_sinan_stage_run ON ingestion.sinan_stage USING btree (run_id);


--
-- Name: run_sha256_5d3b3c94_like; Type: INDEX; Schema: ingestion; Owner: dengueadmin
--

CREATE INDEX run_sha256_5d3b3c94_like ON ingestion.run USING btree (sha256 varchar_pattern_ops);


--
-- Name: sinan_stage_run_id_83470ec0; Type: INDEX; Schema: ingestion; Owner: dengueadmin
--

CREATE INDEX sinan_stage_run_id_83470ec0 ON ingestion.sinan_stage USING btree (run_id);


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
-- Name: authtoken_token_key_10f0b77e_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX authtoken_token_key_10f0b77e_like ON public.authtoken_token USING btree (key varchar_pattern_ops);


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
-- Name: django_cele_date_cr_bd6c1d_idx; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_cele_date_cr_bd6c1d_idx ON public.django_celery_results_groupresult USING btree (date_created);


--
-- Name: django_cele_date_cr_f04a50_idx; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_cele_date_cr_f04a50_idx ON public.django_celery_results_taskresult USING btree (date_created);


--
-- Name: django_cele_date_do_caae0e_idx; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_cele_date_do_caae0e_idx ON public.django_celery_results_groupresult USING btree (date_done);


--
-- Name: django_cele_date_do_f59aad_idx; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_cele_date_do_f59aad_idx ON public.django_celery_results_taskresult USING btree (date_done);


--
-- Name: django_cele_periodi_1993cf_idx; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_cele_periodi_1993cf_idx ON public.django_celery_results_taskresult USING btree (periodic_task_name);


--
-- Name: django_cele_status_9b6201_idx; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_cele_status_9b6201_idx ON public.django_celery_results_taskresult USING btree (status);


--
-- Name: django_cele_task_na_08aec9_idx; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_cele_task_na_08aec9_idx ON public.django_celery_results_taskresult USING btree (task_name);


--
-- Name: django_cele_worker_d54dd8_idx; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_cele_worker_d54dd8_idx ON public.django_celery_results_taskresult USING btree (worker);


--
-- Name: django_celery_beat_periodictask_clocked_id_47a69f82; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_celery_beat_periodictask_clocked_id_47a69f82 ON public.django_celery_beat_periodictask USING btree (clocked_id);


--
-- Name: django_celery_beat_periodictask_crontab_id_d3cba168; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_celery_beat_periodictask_crontab_id_d3cba168 ON public.django_celery_beat_periodictask USING btree (crontab_id);


--
-- Name: django_celery_beat_periodictask_interval_id_a8ca27da; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_celery_beat_periodictask_interval_id_a8ca27da ON public.django_celery_beat_periodictask USING btree (interval_id);


--
-- Name: django_celery_beat_periodictask_name_265a36b7_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_celery_beat_periodictask_name_265a36b7_like ON public.django_celery_beat_periodictask USING btree (name varchar_pattern_ops);


--
-- Name: django_celery_beat_periodictask_solar_id_a87ce72c; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_celery_beat_periodictask_solar_id_a87ce72c ON public.django_celery_beat_periodictask USING btree (solar_id);


--
-- Name: django_celery_results_chordcounter_group_id_1f70858c_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_celery_results_chordcounter_group_id_1f70858c_like ON public.django_celery_results_chordcounter USING btree (group_id varchar_pattern_ops);


--
-- Name: django_celery_results_groupresult_group_id_a085f1a9_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_celery_results_groupresult_group_id_a085f1a9_like ON public.django_celery_results_groupresult USING btree (group_id varchar_pattern_ops);


--
-- Name: django_celery_results_taskresult_task_id_de0d95bf_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_celery_results_taskresult_task_id_de0d95bf_like ON public.django_celery_results_taskresult USING btree (task_id varchar_pattern_ops);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: idx_epiyear_summary_materialized_view_on_uf_and_disease_code; Type: INDEX; Schema: public; Owner: dengueadmin
--

CREATE INDEX idx_epiyear_summary_materialized_view_on_uf_and_disease_code ON public.epiyear_summary_materialized_view USING btree (uf, disease_code);


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
-- Name: Tweet Tweet_CID10; Type: FK CONSTRAINT; Schema: Municipio; Owner: administrador
--

ALTER TABLE ONLY "Municipio"."Tweet"
    ADD CONSTRAINT "Tweet_CID10" FOREIGN KEY ("CID10_codigo") REFERENCES "Dengue_global"."CID10"(codigo);


--
-- Name: alerta_regional_dengue regional_fk; Type: FK CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_regional_dengue
    ADD CONSTRAINT regional_fk FOREIGN KEY (id_regional) REFERENCES "Dengue_global".regional(id);


--
-- Name: alerta_regional_chik regional_fk; Type: FK CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_regional_chik
    ADD CONSTRAINT regional_fk FOREIGN KEY (id_regional) REFERENCES "Dengue_global".regional(id);


--
-- Name: alerta_regional_zika regional_fk; Type: FK CONSTRAINT; Schema: archive_alertas_regionais; Owner: dengueadmin
--

ALTER TABLE ONLY archive_alertas_regionais.alerta_regional_zika
    ADD CONSTRAINT regional_fk FOREIGN KEY (id_regional) REFERENCES "Dengue_global".regional(id);


--
-- Name: Bairro Bairro_Localidade; Type: FK CONSTRAINT; Schema: archive_ovitrampa; Owner: administrador
--

ALTER TABLE ONLY archive_ovitrampa."Bairro"
    ADD CONSTRAINT "Bairro_Localidade" FOREIGN KEY ("Localidade_id") REFERENCES archive_ovitrampa."Localidade"(id);


--
-- Name: Ovitrampa Ovitrampa_Localidade; Type: FK CONSTRAINT; Schema: archive_ovitrampa; Owner: administrador
--

ALTER TABLE ONLY archive_ovitrampa."Ovitrampa"
    ADD CONSTRAINT "Ovitrampa_Localidade" FOREIGN KEY ("Localidade_id") REFERENCES archive_ovitrampa."Localidade"(id);


--
-- Name: sinan_stage sinan_stage_run_id_83470ec0_fk_run_id; Type: FK CONSTRAINT; Schema: ingestion; Owner: dengueadmin
--

ALTER TABLE ONLY ingestion.sinan_stage
    ADD CONSTRAINT sinan_stage_run_id_83470ec0_fk_run_id FOREIGN KEY (run_id) REFERENCES ingestion.run(id) DEFERRABLE INITIALLY DEFERRED;


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
-- Name: authtoken_token authtoken_token_user_id_35299eff_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_35299eff_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


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
-- Name: django_celery_beat_periodictask django_celery_beat_p_clocked_id_47a69f82_fk_django_ce; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_p_clocked_id_47a69f82_fk_django_ce FOREIGN KEY (clocked_id) REFERENCES public.django_celery_beat_clockedschedule(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_celery_beat_periodictask django_celery_beat_p_crontab_id_d3cba168_fk_django_ce; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_p_crontab_id_d3cba168_fk_django_ce FOREIGN KEY (crontab_id) REFERENCES public.django_celery_beat_crontabschedule(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_celery_beat_periodictask django_celery_beat_p_interval_id_a8ca27da_fk_django_ce; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_p_interval_id_a8ca27da_fk_django_ce FOREIGN KEY (interval_id) REFERENCES public.django_celery_beat_intervalschedule(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_celery_beat_periodictask django_celery_beat_p_solar_id_a87ce72c_fk_django_ce; Type: FK CONSTRAINT; Schema: public; Owner: dengueadmin
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_p_solar_id_a87ce72c_fk_django_ce FOREIGN KEY (solar_id) REFERENCES public.django_celery_beat_solarschedule(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: SCHEMA "Dengue_global"; Type: ACL; Schema: -; Owner: Dengue
--

GRANT USAGE ON SCHEMA "Dengue_global" TO "Read_only";
GRANT USAGE ON SCHEMA "Dengue_global" TO infodenguedev;
GRANT USAGE ON SCHEMA "Dengue_global" TO analista;
GRANT USAGE ON SCHEMA "Dengue_global" TO mosqlimate_dev;


--
-- Name: SCHEMA "Municipio"; Type: ACL; Schema: -; Owner: Dengue
--

GRANT USAGE ON SCHEMA "Municipio" TO infodenguedev;
GRANT USAGE ON SCHEMA "Municipio" TO analista;
GRANT USAGE ON SCHEMA "Municipio" TO mosqlimate_dev;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: dengueadmin
--

GRANT USAGE ON SCHEMA public TO infodenguedev;


--
-- Name: SCHEMA weather; Type: ACL; Schema: -; Owner: dengueadmin
--

GRANT USAGE ON SCHEMA weather TO infodenguedev;
GRANT USAGE ON SCHEMA weather TO analista;
GRANT USAGE ON SCHEMA weather TO mosqlimate_dev;


--
-- Name: TABLE "CID10"; Type: ACL; Schema: Dengue_global; Owner: administrador
--

GRANT ALL ON TABLE "Dengue_global"."CID10" TO "Dengue";
GRANT ALL ON TABLE "Dengue_global"."CID10" TO dengue;
GRANT SELECT ON TABLE "Dengue_global"."CID10" TO "Read_only";
GRANT SELECT ON TABLE "Dengue_global"."CID10" TO infodenguedev;
GRANT SELECT ON TABLE "Dengue_global"."CID10" TO analista;


--
-- Name: TABLE "Municipio"; Type: ACL; Schema: Dengue_global; Owner: administrador
--

GRANT ALL ON TABLE "Dengue_global"."Municipio" TO "Dengue";
GRANT ALL ON TABLE "Dengue_global"."Municipio" TO dengue;
GRANT SELECT ON TABLE "Dengue_global"."Municipio" TO "Read_only";
GRANT SELECT ON TABLE "Dengue_global"."Municipio" TO infodenguedev;
GRANT SELECT ON TABLE "Dengue_global"."Municipio" TO analista;
GRANT SELECT ON TABLE "Dengue_global"."Municipio" TO mosqlimate_dev;


--
-- Name: TABLE estado; Type: ACL; Schema: Dengue_global; Owner: administrador
--

GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLE "Dengue_global".estado TO "Dengue";
GRANT ALL ON TABLE "Dengue_global".estado TO dengue;
GRANT SELECT ON TABLE "Dengue_global".estado TO "Read_only";
GRANT SELECT ON TABLE "Dengue_global".estado TO infodenguedev;
GRANT SELECT ON TABLE "Dengue_global".estado TO analista;


--
-- Name: TABLE macroregional; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT ALL ON TABLE "Dengue_global".macroregional TO dengue;
GRANT SELECT ON TABLE "Dengue_global".macroregional TO "Read_only";
GRANT SELECT ON TABLE "Dengue_global".macroregional TO infodenguedev;
GRANT SELECT ON TABLE "Dengue_global".macroregional TO analista;


--
-- Name: SEQUENCE macroregional_id_seq; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT SELECT ON SEQUENCE "Dengue_global".macroregional_id_seq TO "Read_only";


--
-- Name: TABLE parameters; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT ALL ON TABLE "Dengue_global".parameters TO dengue;
GRANT SELECT ON TABLE "Dengue_global".parameters TO "Read_only";
GRANT SELECT ON TABLE "Dengue_global".parameters TO infodenguedev;
GRANT SELECT,INSERT,UPDATE ON TABLE "Dengue_global".parameters TO analista;


--
-- Name: TABLE regional; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT ALL ON TABLE "Dengue_global".regional TO dengue;
GRANT SELECT ON TABLE "Dengue_global".regional TO "Read_only";
GRANT SELECT ON TABLE "Dengue_global".regional TO infodenguedev;
GRANT SELECT ON TABLE "Dengue_global".regional TO analista;


--
-- Name: SEQUENCE regional_id_seq; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT SELECT ON SEQUENCE "Dengue_global".regional_id_seq TO "Read_only";


--
-- Name: TABLE regional_saude; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT ALL ON TABLE "Dengue_global".regional_saude TO dengue;
GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLE "Dengue_global".regional_saude TO "Dengue";
GRANT SELECT ON TABLE "Dengue_global".regional_saude TO "Read_only";
GRANT SELECT ON TABLE "Dengue_global".regional_saude TO infodenguedev;
GRANT SELECT ON TABLE "Dengue_global".regional_saude TO analista;


--
-- Name: SEQUENCE regional_saude_id_seq; Type: ACL; Schema: Dengue_global; Owner: dengueadmin
--

GRANT SELECT,USAGE ON SEQUENCE "Dengue_global".regional_saude_id_seq TO dengue;
GRANT SELECT ON SEQUENCE "Dengue_global".regional_saude_id_seq TO "Read_only";


--
-- Name: TABLE "Clima_Satelite"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Clima_Satelite" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Clima_Satelite" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Clima_Satelite" TO infodenguedev;
GRANT SELECT ON TABLE "Municipio"."Clima_Satelite" TO analista;


--
-- Name: SEQUENCE "Clima_Satelite_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Clima_Satelite_id_seq" TO dengue;


--
-- Name: TABLE "Clima_cemaden"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Clima_cemaden" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Clima_cemaden" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Clima_cemaden" TO infodenguedev;
GRANT SELECT ON TABLE "Municipio"."Clima_cemaden" TO analista;


--
-- Name: SEQUENCE "Clima_cemaden_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Clima_cemaden_id_seq" TO dengue;


--
-- Name: TABLE "Clima_wu"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Clima_wu" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Clima_wu" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Clima_wu" TO infodenguedev;
GRANT SELECT ON TABLE "Municipio"."Clima_wu" TO analista;


--
-- Name: SEQUENCE "Clima_wu_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Clima_wu_id_seq" TO dengue;


--
-- Name: TABLE "Estacao_cemaden"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Estacao_cemaden" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Estacao_cemaden" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Estacao_cemaden" TO infodenguedev;
GRANT SELECT ON TABLE "Municipio"."Estacao_cemaden" TO analista;


--
-- Name: TABLE "Estacao_wu"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Estacao_wu" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Estacao_wu" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Estacao_wu" TO infodenguedev;
GRANT SELECT ON TABLE "Municipio"."Estacao_wu" TO analista;


--
-- Name: TABLE "Historico_alerta"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Historico_alerta" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Historico_alerta" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Historico_alerta" TO infodenguedev;
GRANT SELECT,INSERT,UPDATE ON TABLE "Municipio"."Historico_alerta" TO analista;
GRANT SELECT ON TABLE "Municipio"."Historico_alerta" TO mosqlimate_dev;


--
-- Name: TABLE "Historico_alerta_chik"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Historico_alerta_chik" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Historico_alerta_chik" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Historico_alerta_chik" TO infodenguedev;
GRANT SELECT,INSERT,UPDATE ON TABLE "Municipio"."Historico_alerta_chik" TO analista;
GRANT SELECT ON TABLE "Municipio"."Historico_alerta_chik" TO mosqlimate_dev;


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
GRANT SELECT ON TABLE "Municipio"."Historico_alerta_zika" TO infodenguedev;
GRANT SELECT,INSERT,UPDATE ON TABLE "Municipio"."Historico_alerta_zika" TO analista;
GRANT SELECT ON TABLE "Municipio"."Historico_alerta_zika" TO mosqlimate_dev;


--
-- Name: SEQUENCE "Historico_alerta_zika_id_seq"; Type: ACL; Schema: Municipio; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Historico_alerta_zika_id_seq" TO dengue;


--
-- Name: TABLE "Notificacao"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Notificacao" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Notificacao" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Notificacao" TO infodenguedev;
GRANT SELECT ON TABLE "Municipio"."Notificacao" TO analista;


--
-- Name: SEQUENCE "Notificacao_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Notificacao_id_seq" TO dengue;


--
-- Name: TABLE "Tweet"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT ALL ON TABLE "Municipio"."Tweet" TO "Dengue";
GRANT ALL ON TABLE "Municipio"."Tweet" TO dengue;
GRANT SELECT ON TABLE "Municipio"."Tweet" TO infodenguedev;
GRANT SELECT ON TABLE "Municipio"."Tweet" TO analista;


--
-- Name: SEQUENCE "Tweet_id_seq"; Type: ACL; Schema: Municipio; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE "Municipio"."Tweet_id_seq" TO dengue;


--
-- Name: TABLE historico_casos; Type: ACL; Schema: Municipio; Owner: dengueadmin
--

GRANT SELECT ON TABLE "Municipio".historico_casos TO infodenguedev;
GRANT SELECT ON TABLE "Municipio".historico_casos TO analista;


--
-- Name: TABLE sprint202425; Type: ACL; Schema: Municipio; Owner: dengueadmin
--

GRANT SELECT ON TABLE "Municipio".sprint202425 TO infodenguedev;
GRANT SELECT ON TABLE "Municipio".sprint202425 TO analista;


--
-- Name: TABLE alerta_mrj; Type: ACL; Schema: archive_alertas_regionais; Owner: dengueadmin
--

GRANT ALL ON TABLE archive_alertas_regionais.alerta_mrj TO dengue;
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_mrj TO infodenguedev;
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_mrj TO analista;


--
-- Name: TABLE alerta_mrj_chik; Type: ACL; Schema: archive_alertas_regionais; Owner: dengueadmin
--

GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLE archive_alertas_regionais.alerta_mrj_chik TO "Dengue";
GRANT ALL ON TABLE archive_alertas_regionais.alerta_mrj_chik TO dengue;
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_mrj_chik TO infodenguedev;
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_mrj_chik TO analista;


--
-- Name: SEQUENCE alerta_mrj_chik_id_seq; Type: ACL; Schema: archive_alertas_regionais; Owner: dengueadmin
--

GRANT SELECT,USAGE ON SEQUENCE archive_alertas_regionais.alerta_mrj_chik_id_seq TO dengue;


--
-- Name: SEQUENCE alerta_mrj_id_seq; Type: ACL; Schema: archive_alertas_regionais; Owner: dengueadmin
--

GRANT SELECT,USAGE ON SEQUENCE archive_alertas_regionais.alerta_mrj_id_seq TO dengue;


--
-- Name: TABLE alerta_mrj_zika; Type: ACL; Schema: archive_alertas_regionais; Owner: postgres
--

GRANT ALL ON TABLE archive_alertas_regionais.alerta_mrj_zika TO dengue;
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_mrj_zika TO infodenguedev;
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_mrj_zika TO analista;


--
-- Name: SEQUENCE alerta_mrj_zika_id_seq; Type: ACL; Schema: archive_alertas_regionais; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE archive_alertas_regionais.alerta_mrj_zika_id_seq TO dengue;


--
-- Name: TABLE alerta_regional_chik; Type: ACL; Schema: archive_alertas_regionais; Owner: dengueadmin
--

GRANT SELECT ON TABLE archive_alertas_regionais.alerta_regional_chik TO "Read_only";
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_regional_chik TO infodenguedev;
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_regional_chik TO analista;


--
-- Name: SEQUENCE alerta_regional_chik_id_seq; Type: ACL; Schema: archive_alertas_regionais; Owner: dengueadmin
--

GRANT SELECT ON SEQUENCE archive_alertas_regionais.alerta_regional_chik_id_seq TO "Read_only";


--
-- Name: TABLE alerta_regional_dengue; Type: ACL; Schema: archive_alertas_regionais; Owner: dengueadmin
--

GRANT SELECT ON TABLE archive_alertas_regionais.alerta_regional_dengue TO "Read_only";
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_regional_dengue TO infodenguedev;
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_regional_dengue TO analista;


--
-- Name: SEQUENCE alerta_regional_dengue_id_seq; Type: ACL; Schema: archive_alertas_regionais; Owner: dengueadmin
--

GRANT SELECT ON SEQUENCE archive_alertas_regionais.alerta_regional_dengue_id_seq TO "Read_only";


--
-- Name: TABLE alerta_regional_zika; Type: ACL; Schema: archive_alertas_regionais; Owner: dengueadmin
--

GRANT SELECT ON TABLE archive_alertas_regionais.alerta_regional_zika TO "Read_only";
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_regional_zika TO infodenguedev;
GRANT SELECT ON TABLE archive_alertas_regionais.alerta_regional_zika TO analista;


--
-- Name: SEQUENCE alerta_regional_zika_id_seq; Type: ACL; Schema: archive_alertas_regionais; Owner: dengueadmin
--

GRANT SELECT ON SEQUENCE archive_alertas_regionais.alerta_regional_zika_id_seq TO "Read_only";


--
-- Name: TABLE "Bairro"; Type: ACL; Schema: archive_ovitrampa; Owner: administrador
--

GRANT ALL ON TABLE archive_ovitrampa."Bairro" TO "Dengue";
GRANT ALL ON TABLE archive_ovitrampa."Bairro" TO dengue;
GRANT SELECT ON TABLE archive_ovitrampa."Bairro" TO infodenguedev;
GRANT SELECT ON TABLE archive_ovitrampa."Bairro" TO analista;


--
-- Name: TABLE "Localidade"; Type: ACL; Schema: archive_ovitrampa; Owner: administrador
--

GRANT ALL ON TABLE archive_ovitrampa."Localidade" TO "Dengue";
GRANT ALL ON TABLE archive_ovitrampa."Localidade" TO dengue;
GRANT SELECT ON TABLE archive_ovitrampa."Localidade" TO infodenguedev;
GRANT SELECT ON TABLE archive_ovitrampa."Localidade" TO analista;


--
-- Name: TABLE "Ovitrampa"; Type: ACL; Schema: archive_ovitrampa; Owner: administrador
--

GRANT ALL ON TABLE archive_ovitrampa."Ovitrampa" TO "Dengue";
GRANT ALL ON TABLE archive_ovitrampa."Ovitrampa" TO dengue;
GRANT SELECT ON TABLE archive_ovitrampa."Ovitrampa" TO infodenguedev;
GRANT SELECT ON TABLE archive_ovitrampa."Ovitrampa" TO analista;


--
-- Name: SEQUENCE "Ovitrampa_id_seq"; Type: ACL; Schema: archive_ovitrampa; Owner: administrador
--

GRANT SELECT,USAGE ON SEQUENCE archive_ovitrampa."Ovitrampa_id_seq" TO dengue;


--
-- Name: TABLE auth_group; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.auth_group TO infodenguedev;


--
-- Name: TABLE auth_group_permissions; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.auth_group_permissions TO infodenguedev;


--
-- Name: TABLE auth_permission; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.auth_permission TO infodenguedev;


--
-- Name: TABLE auth_user; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.auth_user TO infodenguedev;


--
-- Name: TABLE auth_user_groups; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.auth_user_groups TO infodenguedev;


--
-- Name: TABLE auth_user_user_permissions; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.auth_user_user_permissions TO infodenguedev;


--
-- Name: TABLE dbf_dbf; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.dbf_dbf TO infodenguedev;


--
-- Name: TABLE dbf_dbfchunkedupload; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.dbf_dbfchunkedupload TO infodenguedev;


--
-- Name: TABLE django_admin_log; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.django_admin_log TO infodenguedev;


--
-- Name: TABLE django_content_type; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.django_content_type TO infodenguedev;


--
-- Name: TABLE django_migrations; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.django_migrations TO infodenguedev;


--
-- Name: TABLE django_session; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.django_session TO infodenguedev;


--
-- Name: TABLE geography_columns; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.geography_columns TO infodenguedev;


--
-- Name: TABLE geometry_columns; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.geometry_columns TO infodenguedev;


--
-- Name: TABLE hist_uf_chik_materialized_view; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.hist_uf_chik_materialized_view TO infodenguedev;


--
-- Name: TABLE hist_uf_dengue_materialized_view; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.hist_uf_dengue_materialized_view TO infodenguedev;


--
-- Name: TABLE hist_uf_zika_materialized_view; Type: ACL; Schema: public; Owner: dengueadmin
--

GRANT SELECT ON TABLE public.hist_uf_zika_materialized_view TO infodenguedev;


--
-- Name: TABLE spatial_ref_sys; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.spatial_ref_sys TO infodenguedev;


--
-- Name: TABLE uf_total_chik_view; Type: ACL; Schema: public; Owner: administrador
--

GRANT SELECT,INSERT,REFERENCES,TRIGGER,UPDATE ON TABLE public.uf_total_chik_view TO "Dengue";
GRANT SELECT ON TABLE public.uf_total_chik_view TO infodenguedev;


--
-- Name: TABLE uf_total_view; Type: ACL; Schema: public; Owner: administrador
--

GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLE public.uf_total_view TO "Dengue";
GRANT SELECT ON TABLE public.uf_total_view TO infodenguedev;


--
-- Name: TABLE uf_total_zika_view; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.uf_total_zika_view TO infodenguedev;


--
-- Name: TABLE copernicus_arg; Type: ACL; Schema: weather; Owner: dengueadmin
--

GRANT SELECT ON TABLE weather.copernicus_arg TO analista;
GRANT SELECT ON TABLE weather.copernicus_arg TO infodenguedev;
GRANT SELECT ON TABLE weather.copernicus_arg TO mosqlimate_dev;


--
-- Name: TABLE copernicus_bra; Type: ACL; Schema: weather; Owner: dengueadmin
--

GRANT SELECT ON TABLE weather.copernicus_bra TO analista;
GRANT SELECT ON TABLE weather.copernicus_bra TO infodenguedev;
GRANT SELECT ON TABLE weather.copernicus_bra TO mosqlimate_dev;


--
-- Name: TABLE copernicus_foz_do_iguacu; Type: ACL; Schema: weather; Owner: dengueadmin
--

GRANT SELECT ON TABLE weather.copernicus_foz_do_iguacu TO infodenguedev;
GRANT SELECT ON TABLE weather.copernicus_foz_do_iguacu TO analista;
GRANT SELECT ON TABLE weather.copernicus_foz_do_iguacu TO mosqlimate_dev;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: administrador
--

ALTER DEFAULT PRIVILEGES FOR ROLE administrador GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLES  TO "Dengue";
ALTER DEFAULT PRIVILEGES FOR ROLE administrador GRANT SELECT ON TABLES  TO "Read_only";


--
-- PostgreSQL database dump complete
--
