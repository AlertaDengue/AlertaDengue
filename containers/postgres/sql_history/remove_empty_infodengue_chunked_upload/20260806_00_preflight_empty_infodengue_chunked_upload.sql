\set ON_ERROR_STOP on
\pset pager off
\if :{?expected_database_name}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_database_name is required'; END $$;
\endif
SELECT current_database() = :'expected_database_name' AS database_name_matches \gset
\if :database_name_matches
\else
  DO $$ BEGIN RAISE EXCEPTION 'connected database does not match expected_database_name'; END $$;
\endif
BEGIN;
SET TRANSACTION READ ONLY;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

SELECT current_database() AS database_name,
       (SELECT oid FROM pg_database WHERE datname = current_database()) AS database_oid,
       current_setting('server_version') AS server_version,
       pg_is_in_recovery() AS in_recovery,
       current_user AS execution_role;

DO $guard$
BEGIN
  IF current_database() <> 'infodengue' THEN
    RAISE EXCEPTION 'this workflow requires the infodengue database';
  END IF;
  IF pg_is_in_recovery() THEN
    RAISE EXCEPTION 'database is in recovery';
  END IF;
  IF to_regclass('public.chunked_upload_chunkedupload') IS NULL THEN
    RAISE EXCEPTION 'public.chunked_upload_chunkedupload is missing';
  END IF;
  IF to_regclass('public.chunked_upload_chunkedupload_id_seq') IS NULL THEN
    RAISE EXCEPTION 'public.chunked_upload_chunkedupload_id_seq is missing';
  END IF;
END $guard$;

SELECT 'public.chunked_upload_chunkedupload' AS table_name,
       count(*) AS exact_rows,
       pg_total_relation_size('public.chunked_upload_chunkedupload'::regclass) AS total_bytes
  FROM public.chunked_upload_chunkedupload;

DO $empty$
BEGIN
  IF (SELECT count(*) FROM public.chunked_upload_chunkedupload) <> 0 THEN
    RAISE EXCEPTION 'public.chunked_upload_chunkedupload contains rows';
  END IF;
END $empty$;

SELECT table_name, column_name, ordinal_position, data_type, is_nullable,
       column_default
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND table_name = 'chunked_upload_chunkedupload'
 ORDER BY ordinal_position;

SELECT conrelid::regclass AS table_name, conname, contype,
       pg_get_constraintdef(oid) AS definition, convalidated
  FROM pg_constraint
 WHERE conrelid = 'public.chunked_upload_chunkedupload'::regclass
 ORDER BY conname;

SELECT indrelid::regclass AS table_name, indexrelid::regclass AS index_name,
       pg_get_indexdef(indexrelid) AS definition
  FROM pg_index
 WHERE indrelid = 'public.chunked_upload_chunkedupload'::regclass
 ORDER BY indexrelid;

SELECT tgrelid::regclass AS table_name, tgname,
       pg_get_triggerdef(oid) AS definition
  FROM pg_trigger
 WHERE tgrelid = 'public.chunked_upload_chunkedupload'::regclass
   AND NOT tgisinternal
 ORDER BY tgname;

SELECT schemaname, tablename, rulename, definition
  FROM pg_rules
 WHERE schemaname = 'public'
   AND tablename = 'chunked_upload_chunkedupload'
 ORDER BY rulename;

SELECT c.oid::regclass AS object_name,
       pg_get_userbyid(c.relowner) AS owner_name,
       coalesce(c.relacl::text, '') AS relacl_text,
       s.last_value,
       s.is_called,
       pg_get_serial_sequence('public.chunked_upload_chunkedupload', 'id') AS serial_sequence
  FROM pg_class c
  JOIN public.chunked_upload_chunkedupload_id_seq s ON true
 WHERE c.oid = 'public.chunked_upload_chunkedupload_id_seq'::regclass;

SELECT dep.deptype,
       seq.oid::regclass AS sequence_name,
       tbl.oid::regclass AS owning_table,
       dep.refobjsubid AS owning_column_number,
       a.attname AS owning_column
  FROM pg_depend dep
  JOIN pg_class seq ON seq.oid = dep.objid
  JOIN pg_class tbl ON tbl.oid = dep.refobjid
  LEFT JOIN pg_attribute a
    ON a.attrelid = tbl.oid
   AND a.attnum = dep.refobjsubid
 WHERE seq.oid = 'public.chunked_upload_chunkedupload_id_seq'::regclass
 ORDER BY dep.deptype, dep.refobjsubid;

SELECT d.classid::regclass AS dependency_catalog,
       d.objid::text AS dependent_object,
       d.refobjid::regclass AS referenced_object,
       d.refobjsubid,
       d.deptype
  FROM pg_depend d
 WHERE d.refobjid IN (
   'public.chunked_upload_chunkedupload'::regclass,
   'public.chunked_upload_chunkedupload_id_seq'::regclass
 )
 ORDER BY 1, 2, 3, 4, 5;

DO $ownership$
BEGIN
  IF pg_get_serial_sequence('public.chunked_upload_chunkedupload', 'id') IS DISTINCT FROM 'public.chunked_upload_chunkedupload_id_seq' THEN
    RAISE EXCEPTION 'owned sequence does not match the table id default';
  END IF;
  IF NOT EXISTS (
    SELECT 1
      FROM pg_depend dep
     WHERE dep.objid = 'public.chunked_upload_chunkedupload_id_seq'::regclass
       AND dep.refobjid = 'public.chunked_upload_chunkedupload'::regclass
       AND dep.refobjsubid = 1
       AND dep.deptype = 'a'
  ) THEN
    RAISE EXCEPTION 'sequence is not owned by public.chunked_upload_chunkedupload.id';
  END IF;
END $ownership$;

DO $dependencies$
BEGIN
  IF EXISTS (
    SELECT 1
      FROM pg_constraint con
     WHERE con.contype = 'f'
       AND con.confrelid = 'public.chunked_upload_chunkedupload'::regclass
       AND con.conrelid <> 'public.chunked_upload_chunkedupload'::regclass
  ) THEN
    RAISE EXCEPTION 'unexpected inbound foreign-key dependency exists';
  END IF;
  IF EXISTS (
    SELECT 1
      FROM pg_depend d
      JOIN pg_rewrite r ON r.oid = d.objid
     WHERE d.classid = 'pg_rewrite'::regclass
       AND d.refobjid IN (
         'public.chunked_upload_chunkedupload'::regclass,
         'public.chunked_upload_chunkedupload_id_seq'::regclass
       )
  ) THEN
    RAISE EXCEPTION 'unexpected view or rule dependency exists';
  END IF;
END $dependencies$;

ROLLBACK;
