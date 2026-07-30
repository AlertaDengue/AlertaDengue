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
-- Name: TABLE copernicus_bra; Type: ACL; Schema: weather; Owner: dengueadmin
--

GRANT SELECT ON TABLE weather.copernicus_bra TO analista;
GRANT SELECT ON TABLE weather.copernicus_bra TO infodenguedev;
GRANT SELECT ON TABLE weather.copernicus_bra TO mosqlimate_dev;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: administrador
--

ALTER DEFAULT PRIVILEGES FOR ROLE administrador GRANT SELECT,INSERT,REFERENCES,TRIGGER,TRUNCATE,UPDATE ON TABLES  TO "Dengue";
ALTER DEFAULT PRIVILEGES FOR ROLE administrador GRANT SELECT ON TABLES  TO "Read_only";


--
-- PostgreSQL database dump complete
--
