\set ON_ERROR_STOP on
\pset pager off
\if :{?expected_database_name}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_database_name is required'; END $$;
\endif
\if :{?verified_package_path}
\else
  DO $$ BEGIN RAISE EXCEPTION 'verified_package_path is required'; END $$;
\endif
\if :{?expected_database_oid}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_database_oid is required'; END $$;
\endif
\if :{?expected_dump_sha256}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_dump_sha256 is required'; END $$;
\endif
\if :{?verification_status}
\else
  DO $$ BEGIN RAISE EXCEPTION 'verification_status is required'; END $$;
\endif
\if :{?expected_dbf_rows}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_dbf_rows is required'; END $$;
\endif
\if :{?expected_dbfchunkedupload_rows}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_dbfchunkedupload_rows is required'; END $$;
\endif
\if :{?expected_sendtopartner_rows}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_sendtopartner_rows is required'; END $$;
\endif
\if :{?expected_dbf_id_seq_last_value}
\else
  DO $$ BEGIN RAISE EXCEPTION 'sequence evidence is required'; END $$;
\endif
\if :{?expected_dbf_id_seq_is_called}
\else
  DO $$ BEGIN RAISE EXCEPTION 'sequence evidence is required'; END $$;
\endif
\if :{?expected_dbfchunkedupload_id_seq_last_value}
\else
  DO $$ BEGIN RAISE EXCEPTION 'sequence evidence is required'; END $$;
\endif
\if :{?expected_dbfchunkedupload_id_seq_is_called}
\else
  DO $$ BEGIN RAISE EXCEPTION 'sequence evidence is required'; END $$;
\endif
\if :{?expected_sendtopartner_id_seq_last_value}
\else
  DO $$ BEGIN RAISE EXCEPTION 'sequence evidence is required'; END $$;
\endif
\if :{?expected_sendtopartner_id_seq_is_called}
\else
  DO $$ BEGIN RAISE EXCEPTION 'sequence evidence is required'; END $$;
\endif
SELECT current_database() = :'expected_database_name' AS ok \gset
\if :ok
\else
  DO $$ BEGIN RAISE EXCEPTION 'wrong database'; END $$;
\endif
BEGIN; SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5min';
SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.remove_infodengue_dbf_legacy'));
DO $$ BEGIN
  IF current_database()<>'infodengue' OR (SELECT oid::text FROM pg_database WHERE datname=current_database())<>:'expected_database_oid' THEN RAISE EXCEPTION 'database identity mismatch'; END IF;
  IF :'verification_status' <> 'PASS' OR :'verified_package_path' LIKE '%PLACEHOLDER%' OR length(:'expected_dump_sha256')<>64 OR :'expected_dump_sha256' !~ '^[0-9A-Fa-f]{64}$' THEN RAISE EXCEPTION 'verified package evidence is not acceptable'; END IF;
  IF to_regclass('archive_infodengue_dbf_legacy.dbf_dbf') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_dbfchunkedupload') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_sendtopartner') IS NULL THEN RAISE EXCEPTION 'archive inventory incomplete'; END IF;
  IF (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_dbf)<>:'expected_dbf_rows' OR (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_dbfchunkedupload)<>:'expected_dbfchunkedupload_rows' OR (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_sendtopartner)<>:'expected_sendtopartner_rows' THEN RAISE EXCEPTION 'row count evidence mismatch'; END IF;
  IF NOT EXISTS (SELECT 1 FROM archive_infodengue_dbf_legacy.dbf_dbf_id_seq WHERE last_value=:'expected_dbf_id_seq_last_value' AND is_called=:'expected_dbf_id_seq_is_called') OR NOT EXISTS (SELECT 1 FROM archive_infodengue_dbf_legacy.dbf_dbfchunkedupload_id_seq WHERE last_value=:'expected_dbfchunkedupload_id_seq_last_value' AND is_called=:'expected_dbfchunkedupload_id_seq_is_called') OR NOT EXISTS (SELECT 1 FROM archive_infodengue_dbf_legacy.dbf_sendtopartner_id_seq WHERE last_value=:'expected_sendtopartner_id_seq_last_value' AND is_called=:'expected_sendtopartner_id_seq_is_called') THEN RAISE EXCEPTION 'sequence evidence mismatch'; END IF;
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid IN ('archive_infodengue_dbf_legacy.dbf_dbf'::regclass,'archive_infodengue_dbf_legacy.dbf_dbfchunkedupload'::regclass,'archive_infodengue_dbf_legacy.dbf_sendtopartner'::regclass) AND conrelid NOT IN ('archive_infodengue_dbf_legacy.dbf_dbf'::regclass,'archive_infodengue_dbf_legacy.dbf_dbfchunkedupload'::regclass,'archive_infodengue_dbf_legacy.dbf_sendtopartner'::regclass)) THEN RAISE EXCEPTION 'unexpected inbound dependency'; END IF;
END $$;
SELECT 'PRE-REMOVAL' AS receipt, current_database() AS database_name, clock_timestamp() AT TIME ZONE 'UTC' AS receipt_utc, :'verified_package_path' AS package_path, :'expected_dump_sha256' AS dump_sha256;
DROP TABLE archive_infodengue_dbf_legacy.dbf_dbfchunkedupload;
DROP TABLE archive_infodengue_dbf_legacy.dbf_dbf;
DROP TABLE archive_infodengue_dbf_legacy.dbf_sendtopartner;
DO $$ BEGIN
  IF to_regclass('archive_infodengue_dbf_legacy.dbf_dbf_id_seq') IS NOT NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_dbfchunkedupload_id_seq') IS NOT NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_sendtopartner_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'owned sequences remain'; END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_infodengue_dbf_legacy') THEN RAISE EXCEPTION 'archive schema is not empty'; END IF;
END $$;
DROP SCHEMA archive_infodengue_dbf_legacy;
SELECT 'REMOVAL PASS' AS receipt, current_database() AS database_name, clock_timestamp() AT TIME ZONE 'UTC' AS completed_utc;
COMMIT;
