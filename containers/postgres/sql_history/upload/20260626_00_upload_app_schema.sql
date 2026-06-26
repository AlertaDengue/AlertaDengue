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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: chunked_upload_chunkedupload; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: chunked_upload_chunkedupload_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chunked_upload_chunkedupload_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chunked_upload_chunkedupload_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chunked_upload_chunkedupload_id_seq OWNED BY public.chunked_upload_chunkedupload.id;


--
-- Name: upload_sinanchunkedupload; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.upload_sinanchunkedupload (
    id bigint NOT NULL,
    upload_id character varying(32) NOT NULL,
    file character varying(255) NOT NULL,
    filename character varying(255) NOT NULL,
    "offset" bigint NOT NULL,
    created_on timestamp with time zone NOT NULL,
    status smallint NOT NULL,
    completed_on timestamp with time zone,
    user_id integer NOT NULL,
    CONSTRAINT upload_sinanchunkedupload_status_check CHECK ((status >= 0))
);


--
-- Name: upload_sinanchunkedupload_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.upload_sinanchunkedupload_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: upload_sinanchunkedupload_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.upload_sinanchunkedupload_id_seq OWNED BY public.upload_sinanchunkedupload.id;


--
-- Name: upload_sinanupload; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.upload_sinanupload (
    id bigint NOT NULL,
    year integer NOT NULL,
    uf character varying(2),
    uploaded_at timestamp with time zone NOT NULL,
    cid10 character varying(5) NOT NULL,
    upload_id bigint,
    status_id bigint,
    date_formats jsonb NOT NULL
);


--
-- Name: upload_sinanupload_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.upload_sinanupload_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: upload_sinanupload_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.upload_sinanupload_id_seq OWNED BY public.upload_sinanupload.id;


--
-- Name: upload_sinanuploadlogstatus; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.upload_sinanuploadlogstatus (
    id bigint NOT NULL,
    status integer NOT NULL,
    log_file character varying(100) NOT NULL,
    inserts_file character varying(100),
    updates_file character varying(100)
);


--
-- Name: upload_sinanuploadlogstatus_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.upload_sinanuploadlogstatus_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: upload_sinanuploadlogstatus_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.upload_sinanuploadlogstatus_id_seq OWNED BY public.upload_sinanuploadlogstatus.id;


--
-- Name: chunked_upload_chunkedupload id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunked_upload_chunkedupload ALTER COLUMN id SET DEFAULT nextval('public.chunked_upload_chunkedupload_id_seq'::regclass);


--
-- Name: upload_sinanchunkedupload id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_sinanchunkedupload ALTER COLUMN id SET DEFAULT nextval('public.upload_sinanchunkedupload_id_seq'::regclass);


--
-- Name: upload_sinanupload id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_sinanupload ALTER COLUMN id SET DEFAULT nextval('public.upload_sinanupload_id_seq'::regclass);


--
-- Name: upload_sinanuploadlogstatus id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_sinanuploadlogstatus ALTER COLUMN id SET DEFAULT nextval('public.upload_sinanuploadlogstatus_id_seq'::regclass);


--
-- Name: chunked_upload_chunkedupload chunked_upload_chunkedupload_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_pkey PRIMARY KEY (id);


--
-- Name: chunked_upload_chunkedupload chunked_upload_chunkedupload_upload_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_upload_id_key UNIQUE (upload_id);


--
-- Name: upload_sinanchunkedupload upload_sinanchunkedupload_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_sinanchunkedupload
    ADD CONSTRAINT upload_sinanchunkedupload_pkey PRIMARY KEY (id);


--
-- Name: upload_sinanchunkedupload upload_sinanchunkedupload_upload_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_sinanchunkedupload
    ADD CONSTRAINT upload_sinanchunkedupload_upload_id_key UNIQUE (upload_id);


--
-- Name: upload_sinanupload upload_sinanupload_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_sinanupload
    ADD CONSTRAINT upload_sinanupload_pkey PRIMARY KEY (id);


--
-- Name: upload_sinanuploadlogstatus upload_sinanuploadlogstatus_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_sinanuploadlogstatus
    ADD CONSTRAINT upload_sinanuploadlogstatus_pkey PRIMARY KEY (id);


--
-- Name: chunked_upload_chunkedupload_upload_id_23703435_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chunked_upload_chunkedupload_upload_id_23703435_like ON public.chunked_upload_chunkedupload USING btree (upload_id varchar_pattern_ops);


--
-- Name: chunked_upload_chunkedupload_user_id_70ff6dbf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chunked_upload_chunkedupload_user_id_70ff6dbf ON public.chunked_upload_chunkedupload USING btree (user_id);


--
-- Name: upload_sinanchunkedupload_upload_id_2d6c9813_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX upload_sinanchunkedupload_upload_id_2d6c9813_like ON public.upload_sinanchunkedupload USING btree (upload_id varchar_pattern_ops);


--
-- Name: upload_sinanchunkedupload_user_id_d183233a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX upload_sinanchunkedupload_user_id_d183233a ON public.upload_sinanchunkedupload USING btree (user_id);


--
-- Name: upload_sinanupload_status_id_998c10bf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX upload_sinanupload_status_id_998c10bf ON public.upload_sinanupload USING btree (status_id);


--
-- Name: upload_sinanupload_upload_id_97f6c7e1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX upload_sinanupload_upload_id_97f6c7e1 ON public.upload_sinanupload USING btree (upload_id);


--
-- Name: chunked_upload_chunkedupload chunked_upload_chunkedupload_user_id_70ff6dbf_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunked_upload_chunkedupload
    ADD CONSTRAINT chunked_upload_chunkedupload_user_id_70ff6dbf_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: upload_sinanchunkedupload upload_sinanchunkedupload_user_id_d183233a_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_sinanchunkedupload
    ADD CONSTRAINT upload_sinanchunkedupload_user_id_d183233a_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: upload_sinanupload upload_sinanupload_status_id_998c10bf_fk_upload_si; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_sinanupload
    ADD CONSTRAINT upload_sinanupload_status_id_998c10bf_fk_upload_si FOREIGN KEY (status_id) REFERENCES public.upload_sinanuploadlogstatus(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: upload_sinanupload upload_sinanupload_upload_id_97f6c7e1_fk_upload_si; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_sinanupload
    ADD CONSTRAINT upload_sinanupload_upload_id_97f6c7e1_fk_upload_si FOREIGN KEY (upload_id) REFERENCES public.upload_sinanchunkedupload(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--
