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
CREATE TEMP TABLE archive_acl (
  object_name text,
  relkind "char",
  baseline_owner name,
  baseline_relacl_text text
) ON COMMIT DROP;
INSERT INTO archive_acl(object_name, relkind, baseline_owner, baseline_relacl_text)
SELECT c.relname, c.relkind, pg_get_userbyid(c.relowner), coalesce(c.relacl::text, '')
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public'
   AND c.relname IN (
     'dbf_dbf', 'dbf_dbf_id_seq',
     'dbf_dbfchunkedupload', 'dbf_dbfchunkedupload_id_seq',
     'dbf_sendtopartner', 'dbf_sendtopartner_id_seq'
   );
CREATE SCHEMA archive_infodengue_dbf_legacy;
ALTER SCHEMA archive_infodengue_dbf_legacy OWNER TO CURRENT_USER;
ALTER TABLE public.dbf_dbf SET SCHEMA archive_infodengue_dbf_legacy;
ALTER TABLE public.dbf_dbfchunkedupload SET SCHEMA archive_infodengue_dbf_legacy;
ALTER TABLE public.dbf_sendtopartner SET SCHEMA archive_infodengue_dbf_legacy;
DO $$ DECLARE x record; BEGIN
  IF to_regclass('archive_infodengue_dbf_legacy.dbf_dbf') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_dbf_id_seq') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_dbfchunkedupload') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_dbfchunkedupload_id_seq') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_sendtopartner') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_sendtopartner_id_seq') IS NULL THEN RAISE EXCEPTION 'archive table/sequence inventory is incomplete'; END IF;
  IF to_regclass('public.dbf_dbf') IS NOT NULL OR to_regclass('public.dbf_dbfchunkedupload') IS NOT NULL OR to_regclass('public.dbf_sendtopartner') IS NOT NULL OR to_regclass('public.dbf_dbf_id_seq') IS NOT NULL OR to_regclass('public.dbf_dbfchunkedupload_id_seq') IS NOT NULL OR to_regclass('public.dbf_sendtopartner_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'public objects remain'; END IF;
  IF (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_dbf) <> (SELECT rows FROM archive_counts WHERE name='dbf_dbf') OR (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_dbfchunkedupload) <> (SELECT rows FROM archive_counts WHERE name='dbf_dbfchunkedupload') OR (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_sendtopartner) <> (SELECT rows FROM archive_counts WHERE name='dbf_sendtopartner') THEN RAISE EXCEPTION 'row count changed'; END IF;
  IF (SELECT count(*) FROM archive_acl) <> 6 THEN RAISE EXCEPTION 'baseline owner/grant inventory is incomplete'; END IF;
END $$;
SELECT b.object_name,
       b.baseline_owner,
       pg_get_userbyid(c.relowner) AS archived_owner,
       b.baseline_relacl_text,
       coalesce(c.relacl::text, '') AS archived_relacl_text
  FROM archive_acl b
  LEFT JOIN (
    SELECT c.relname, c.relkind, c.relowner, c.relacl
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'archive_infodengue_dbf_legacy'
  ) c
    ON c.relname = b.object_name
   AND c.relkind = b.relkind
 ORDER BY b.object_name;
DO $$ DECLARE x record; BEGIN
  FOR x IN
    SELECT b.object_name,
           b.baseline_owner,
           b.baseline_relacl_text,
           pg_get_userbyid(c.relowner) AS archived_owner,
           coalesce(c.relacl::text, '') AS archived_relacl_text
      FROM archive_acl b
      LEFT JOIN (
        SELECT c.relname, c.relkind, c.relowner, c.relacl
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'archive_infodengue_dbf_legacy'
      ) c
        ON c.relname = b.object_name
       AND c.relkind = b.relkind
  LOOP
    IF x.archived_owner IS NULL
       OR x.archived_owner IS DISTINCT FROM x.baseline_owner
       OR x.archived_relacl_text IS DISTINCT FROM x.baseline_relacl_text
    THEN
      RAISE EXCEPTION 'owner or grants changed: %', x.object_name;
    END IF;
  END LOOP;
END $$;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.deptype='a' AND d.objid='archive_infodengue_dbf_legacy.dbf_dbf_id_seq'::regclass AND d.refobjid='archive_infodengue_dbf_legacy.dbf_dbf'::regclass AND d.refobjsubid=1) OR NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.deptype='a' AND d.objid='archive_infodengue_dbf_legacy.dbf_dbfchunkedupload_id_seq'::regclass AND d.refobjid='archive_infodengue_dbf_legacy.dbf_dbfchunkedupload'::regclass AND d.refobjsubid=1) OR NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.deptype='a' AND d.objid='archive_infodengue_dbf_legacy.dbf_sendtopartner_id_seq'::regclass AND d.refobjid='archive_infodengue_dbf_legacy.dbf_sendtopartner'::regclass AND d.refobjsubid=1) THEN RAISE EXCEPTION 'sequence ownership not preserved'; END IF;
  IF pg_get_serial_sequence('archive_infodengue_dbf_legacy.dbf_dbf','id') IS DISTINCT FROM 'archive_infodengue_dbf_legacy.dbf_dbf_id_seq' OR pg_get_serial_sequence('archive_infodengue_dbf_legacy.dbf_dbfchunkedupload','id') IS DISTINCT FROM 'archive_infodengue_dbf_legacy.dbf_dbfchunkedupload_id_seq' OR pg_get_serial_sequence('archive_infodengue_dbf_legacy.dbf_sendtopartner','id') IS DISTINCT FROM 'archive_infodengue_dbf_legacy.dbf_sendtopartner_id_seq' THEN RAISE EXCEPTION 'pg_get_serial_sequence ownership mapping is incorrect'; END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_infodengue_dbf_legacy' AND c.relkind NOT IN ('r','S','i')) THEN RAISE EXCEPTION 'unexpected archive object'; END IF;
END $$;
SELECT c.oid::regclass AS object_name,pg_get_userbyid(c.relowner) AS owner_name,coalesce(array_to_string(c.relacl,','),'') AS grants FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_infodengue_dbf_legacy' AND c.relkind IN ('r','S') ORDER BY 1;
COMMIT;
