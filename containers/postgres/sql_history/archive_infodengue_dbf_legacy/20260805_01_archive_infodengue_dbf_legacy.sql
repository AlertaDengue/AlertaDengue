\set ON_ERROR_STOP on
\pset pager off
\if :{?expected_database_name}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_database_name is required'; END $$;
\endif
SELECT current_database() = :'expected_database_name' AS ok \gset
\if :ok
\else
  DO $$ BEGIN RAISE EXCEPTION 'wrong database'; END $$;
\endif
BEGIN;
SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5min';
SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.archive_infodengue_dbf_legacy'));
DO $$ BEGIN
  IF current_database() <> 'infodengue' OR pg_is_in_recovery() THEN RAISE EXCEPTION 'wrong or recovering database'; END IF;
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname='archive_infodengue_dbf_legacy') THEN RAISE EXCEPTION 'archive schema already exists'; END IF;
  IF to_regclass('public.dbf_dbf') IS NULL OR to_regclass('public.dbf_dbfchunkedupload') IS NULL OR to_regclass('public.dbf_sendtopartner') IS NULL OR to_regclass('public.dbf_dbf_id_seq') IS NULL OR to_regclass('public.dbf_dbfchunkedupload_id_seq') IS NULL OR to_regclass('public.dbf_sendtopartner_id_seq') IS NULL THEN RAISE EXCEPTION 'exact DBF inventory is incomplete'; END IF;
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass,'public.dbf_sendtopartner'::regclass) AND conrelid NOT IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass,'public.dbf_sendtopartner'::regclass)) THEN RAISE EXCEPTION 'unexpected inbound dependency'; END IF;
END $$;
CREATE TEMP TABLE archive_counts(name text primary key, rows bigint, last_value bigint, is_called boolean) ON COMMIT DROP;
INSERT INTO archive_counts VALUES ('dbf_dbf',(SELECT count(*) FROM public.dbf_dbf),(SELECT last_value FROM public.dbf_dbf_id_seq),(SELECT is_called FROM public.dbf_dbf_id_seq)),('dbf_dbfchunkedupload',(SELECT count(*) FROM public.dbf_dbfchunkedupload),(SELECT last_value FROM public.dbf_dbfchunkedupload_id_seq),(SELECT is_called FROM public.dbf_dbfchunkedupload_id_seq)),('dbf_sendtopartner',(SELECT count(*) FROM public.dbf_sendtopartner),(SELECT last_value FROM public.dbf_sendtopartner_id_seq),(SELECT is_called FROM public.dbf_sendtopartner_id_seq));
CREATE TEMP TABLE archive_acl AS SELECT c.oid::regclass::text object_name, pg_get_userbyid(c.relowner) owner_name, coalesce(array_to_string(c.relacl,','),'') grants FROM pg_class c WHERE c.oid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass,'public.dbf_sendtopartner'::regclass,'public.dbf_dbf_id_seq'::regclass,'public.dbf_dbfchunkedupload_id_seq'::regclass,'public.dbf_sendtopartner_id_seq'::regclass);
CREATE SCHEMA archive_infodengue_dbf_legacy;
ALTER SCHEMA archive_infodengue_dbf_legacy OWNER TO CURRENT_USER;
ALTER TABLE public.dbf_dbf SET SCHEMA archive_infodengue_dbf_legacy;
ALTER TABLE public.dbf_dbfchunkedupload SET SCHEMA archive_infodengue_dbf_legacy;
ALTER TABLE public.dbf_sendtopartner SET SCHEMA archive_infodengue_dbf_legacy;
ALTER SEQUENCE public.dbf_dbf_id_seq SET SCHEMA archive_infodengue_dbf_legacy;
ALTER SEQUENCE public.dbf_dbfchunkedupload_id_seq SET SCHEMA archive_infodengue_dbf_legacy;
ALTER SEQUENCE public.dbf_sendtopartner_id_seq SET SCHEMA archive_infodengue_dbf_legacy;
DO $$ DECLARE x record; BEGIN
  IF to_regclass('public.dbf_dbf') IS NOT NULL OR to_regclass('public.dbf_dbfchunkedupload') IS NOT NULL OR to_regclass('public.dbf_sendtopartner') IS NOT NULL OR to_regclass('public.dbf_dbf_id_seq') IS NOT NULL OR to_regclass('public.dbf_dbfchunkedupload_id_seq') IS NOT NULL OR to_regclass('public.dbf_sendtopartner_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'public objects remain'; END IF;
  IF (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_dbf) <> (SELECT rows FROM archive_counts WHERE name='dbf_dbf') OR (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_dbfchunkedupload) <> (SELECT rows FROM archive_counts WHERE name='dbf_dbfchunkedupload') OR (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_sendtopartner) <> (SELECT rows FROM archive_counts WHERE name='dbf_sendtopartner') THEN RAISE EXCEPTION 'row count changed'; END IF;
  FOR x IN SELECT * FROM archive_acl LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_class c WHERE c.oid::regclass::text = replace(x.object_name,'public.','archive_infodengue_dbf_legacy.') AND pg_get_userbyid(c.relowner)=x.owner_name AND coalesce(array_to_string(c.relacl,','),'')=x.grants) THEN RAISE EXCEPTION 'owner or grants changed: %',x.object_name; END IF;
  END LOOP;
  IF NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.deptype='a' AND d.objid='archive_infodengue_dbf_legacy.dbf_dbf_id_seq'::regclass AND d.refobjid='archive_infodengue_dbf_legacy.dbf_dbf'::regclass AND d.refobjsubid=1) OR NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.deptype='a' AND d.objid='archive_infodengue_dbf_legacy.dbf_dbfchunkedupload_id_seq'::regclass AND d.refobjid='archive_infodengue_dbf_legacy.dbf_dbfchunkedupload'::regclass AND d.refobjsubid=1) OR NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.deptype='a' AND d.objid='archive_infodengue_dbf_legacy.dbf_sendtopartner_id_seq'::regclass AND d.refobjid='archive_infodengue_dbf_legacy.dbf_sendtopartner'::regclass AND d.refobjsubid=1) THEN RAISE EXCEPTION 'sequence ownership not preserved'; END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_infodengue_dbf_legacy' AND c.relkind NOT IN ('r','S','i')) THEN RAISE EXCEPTION 'unexpected archive object'; END IF;
END $$;
SELECT c.oid::regclass AS object_name,pg_get_userbyid(c.relowner) AS owner_name,coalesce(array_to_string(c.relacl,','),'') AS grants FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_infodengue_dbf_legacy' AND c.relkind IN ('r','S') ORDER BY 1;
COMMIT;
