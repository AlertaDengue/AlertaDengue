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
BEGIN; SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5min';
SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.restore_infodengue_dbf_legacy'));
DO $$ BEGIN
  IF current_database()<>'infodengue' OR to_regclass('archive_infodengue_dbf_legacy.dbf_dbf') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_dbfchunkedupload') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_sendtopartner') IS NULL THEN RAISE EXCEPTION 'archive inventory incomplete'; END IF;
  IF to_regclass('public.dbf_dbf') IS NOT NULL OR to_regclass('public.dbf_dbfchunkedupload') IS NOT NULL OR to_regclass('public.dbf_sendtopartner') IS NOT NULL THEN RAISE EXCEPTION 'public target already exists'; END IF;
END $$;
ALTER TABLE archive_infodengue_dbf_legacy.dbf_dbf SET SCHEMA public;
ALTER TABLE archive_infodengue_dbf_legacy.dbf_dbfchunkedupload SET SCHEMA public;
ALTER TABLE archive_infodengue_dbf_legacy.dbf_sendtopartner SET SCHEMA public;
ALTER SEQUENCE archive_infodengue_dbf_legacy.dbf_dbf_id_seq SET SCHEMA public;
ALTER SEQUENCE archive_infodengue_dbf_legacy.dbf_dbfchunkedupload_id_seq SET SCHEMA public;
ALTER SEQUENCE archive_infodengue_dbf_legacy.dbf_sendtopartner_id_seq SET SCHEMA public;
DO $$ BEGIN
  IF to_regclass('archive_infodengue_dbf_legacy.dbf_dbf') IS NOT NULL OR to_regclass('public.dbf_dbf') IS NULL OR to_regclass('public.dbf_dbf_id_seq') IS NULL OR to_regclass('public.dbf_dbfchunkedupload') IS NULL OR to_regclass('public.dbf_sendtopartner') IS NULL THEN RAISE EXCEPTION 'restore inventory mismatch'; END IF;
  IF (SELECT count(*) FROM public.dbf_dbf)<>6964 OR (SELECT count(*) FROM public.dbf_dbfchunkedupload)<>7635 OR (SELECT count(*) FROM public.dbf_sendtopartner)<>13 THEN RAISE EXCEPTION 'restore row counts differ'; END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_infodengue_dbf_legacy') THEN RAISE EXCEPTION 'archive schema is not empty'; END IF;
END $$;
DROP SCHEMA archive_infodengue_dbf_legacy;
SELECT 'RESTORE PASS' AS receipt, current_database() AS database_name, clock_timestamp() AT TIME ZONE 'UTC' AS completed_utc;
COMMIT;
