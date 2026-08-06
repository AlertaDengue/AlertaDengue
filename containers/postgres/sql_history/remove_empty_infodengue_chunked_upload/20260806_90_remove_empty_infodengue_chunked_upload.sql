\set ON_ERROR_STOP on
\pset pager off
\if :{?expected_database_name}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_database_name is required'; END $$;
\endif
\if :{?removal_approval}
\else
  DO $$ BEGIN RAISE EXCEPTION 'removal_approval is required'; END $$;
\endif
SELECT current_database() = :'expected_database_name' AS database_name_matches \gset
\if :database_name_matches
\else
  DO $$ BEGIN RAISE EXCEPTION 'connected database does not match expected_database_name'; END $$;
\endif
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';
SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.remove_empty_infodengue_chunked_upload'));
SELECT set_config(
  'infodengue.empty_chunked_upload_removal_approval',
  :'removal_approval',
  true
);

DO $guard$
BEGIN
  IF current_database() <> 'infodengue' THEN
    RAISE EXCEPTION 'this workflow requires the infodengue database';
  END IF;
  IF pg_is_in_recovery() THEN
    RAISE EXCEPTION 'database is in recovery';
  END IF;
  IF current_setting('infodengue.empty_chunked_upload_removal_approval', true) <> 'REMOVE_APPROVED_EMPTY_INFODENGUE_CHUNKED_UPLOAD' THEN
    RAISE EXCEPTION 'explicit removal approval token is invalid';
  END IF;
  IF to_regclass('public.chunked_upload_chunkedupload') IS NULL OR to_regclass('public.chunked_upload_chunkedupload_id_seq') IS NULL THEN
    RAISE EXCEPTION 'candidate table/sequence inventory is incomplete';
  END IF;
  IF (SELECT count(*) FROM public.chunked_upload_chunkedupload) <> 0 THEN
    RAISE EXCEPTION 'candidate table contains rows';
  END IF;
  IF pg_get_serial_sequence('public.chunked_upload_chunkedupload', 'id') IS DISTINCT FROM 'public.chunked_upload_chunkedupload_id_seq' THEN
    RAISE EXCEPTION 'owned sequence does not match the table id default';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_depend dep
     WHERE dep.objid = 'public.chunked_upload_chunkedupload_id_seq'::regclass
       AND dep.refobjid = 'public.chunked_upload_chunkedupload'::regclass
       AND dep.refobjsubid = 1 AND dep.deptype = 'a'
  ) THEN RAISE EXCEPTION 'sequence is not owned by candidate table id'; END IF;
  IF EXISTS (
    SELECT 1 FROM pg_constraint con
     WHERE con.contype = 'f'
       AND con.confrelid = 'public.chunked_upload_chunkedupload'::regclass
       AND con.conrelid <> 'public.chunked_upload_chunkedupload'::regclass
  ) THEN RAISE EXCEPTION 'unexpected inbound foreign-key dependency exists'; END IF;
  IF EXISTS (
    SELECT 1 FROM pg_depend d JOIN pg_rewrite r ON r.oid = d.objid
     WHERE d.classid = 'pg_rewrite'::regclass
       AND d.refobjid IN ('public.chunked_upload_chunkedupload'::regclass, 'public.chunked_upload_chunkedupload_id_seq'::regclass)
  ) THEN RAISE EXCEPTION 'unexpected view or rule dependency exists'; END IF;
END $guard$;

SELECT 'PRE-REMOVAL' AS receipt, current_database() AS database_name,
       clock_timestamp() AT TIME ZONE 'UTC' AS receipt_utc,
       count(*) AS exact_rows
  FROM public.chunked_upload_chunkedupload;

DROP TABLE public.chunked_upload_chunkedupload;

DO $post_remove$
BEGIN
  IF to_regclass('public.chunked_upload_chunkedupload') IS NOT NULL THEN
    RAISE EXCEPTION 'candidate table remains after removal';
  END IF;
  IF to_regclass('public.chunked_upload_chunkedupload_id_seq') IS NOT NULL THEN
    RAISE EXCEPTION 'owned sequence remains after table removal';
  END IF;
END $post_remove$;

SELECT 'REMOVAL PASS' AS receipt, current_database() AS database_name,
       clock_timestamp() AT TIME ZONE 'UTC' AS completed_utc;
COMMIT;
