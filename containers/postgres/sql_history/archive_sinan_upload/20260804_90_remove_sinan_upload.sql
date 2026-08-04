\set ON_ERROR_STOP on
\pset pager off

\if :{?expected_database_name}
\else
  \echo 'ERROR: expected_database_name is required'
  \quit 3
\endif
SELECT current_database() = :'expected_database_name' AS database_name_matches
\gset
\if :database_name_matches
\else
  \echo 'ERROR: connected database does not match expected_database_name'
  \quit 3
\endif

\if :{?verified_package_path}
\else
  \echo 'verified_package_path is required'
  \quit 1
\endif
\if :{?expected_database_oid}
\else
  \echo 'expected_database_oid is required'
  \quit 1
\endif
\if :{?expected_dump_sha256}
\else
  \echo 'expected_dump_sha256 is required'
  \quit 1
\endif
\if :{?verification_status}
\else
  \echo 'verification_status is required'
  \quit 1
\endif
\if :{?expected_sinanchunkedupload_rows}
\else
  \echo 'expected_sinanchunkedupload_rows is required'
  \quit 1
\endif
\if :{?expected_sinanupload_rows}
\else
  \echo 'expected_sinanupload_rows is required'
  \quit 1
\endif
\if :{?expected_sinanuploadlogstatus_rows}
\else
  \echo 'expected_sinanuploadlogstatus_rows is required'
  \quit 1
\endif
\if :{?expected_sinanchunkedupload_id_seq_last_value}
\else
  \echo 'expected_sinanchunkedupload_id_seq_last_value is required'
  \quit 1
\endif
\if :{?expected_sinanchunkedupload_id_seq_is_called}
\else
  \echo 'expected_sinanchunkedupload_id_seq_is_called is required'
  \quit 1
\endif
\if :{?expected_sinanupload_id_seq_last_value}
\else
  \echo 'expected_sinanupload_id_seq_last_value is required'
  \quit 1
\endif
\if :{?expected_sinanupload_id_seq_is_called}
\else
  \echo 'expected_sinanupload_id_seq_is_called is required'
  \quit 1
\endif
\if :{?expected_sinanuploadlogstatus_id_seq_last_value}
\else
  \echo 'expected_sinanuploadlogstatus_id_seq_last_value is required'
  \quit 1
\endif
\if :{?expected_sinanuploadlogstatus_id_seq_is_called}
\else
  \echo 'expected_sinanuploadlogstatus_id_seq_is_called is required'
  \quit 1
\endif

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';
SET LOCAL idle_in_transaction_session_timeout = '5min';
SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.remove_sinan_upload'));

DO $guard$
BEGIN
    IF :'verification_status' <> 'PASS' THEN RAISE EXCEPTION 'verification_status must be PASS'; END IF;
    IF :'verified_package_path' !~ '^/' THEN RAISE EXCEPTION 'verified_package_path must be absolute'; END IF;
    IF :'verified_package_path' LIKE '/tmp/%' OR :'verified_package_path' LIKE '/opt/services/infodengue/AlertaDengue-sinan-archive/%' OR :'verified_package_path' LIKE current_setting('data_directory') || '/%' THEN RAISE EXCEPTION 'verified package path is not persistent and external'; END IF;
    IF :'expected_dump_sha256' !~ '^[0-9a-fA-F]{64}$' THEN RAISE EXCEPTION 'expected_dump_sha256 must be 64 hexadecimal characters'; END IF;
    IF pg_is_in_recovery() THEN RAISE EXCEPTION 'database is in recovery'; END IF;
    IF (SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()) <> :'expected_database_oid'::oid THEN RAISE EXCEPTION 'database OID mismatch'; END IF;
    IF to_regclass('archive_sinan_upload.upload_sinanchunkedupload') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanupload') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanchunkedupload_id_seq') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanupload_id_seq') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus_id_seq') IS NULL THEN RAISE EXCEPTION 'archive inventory is incomplete'; END IF;
    IF to_regclass('public.upload_sinanchunkedupload') IS NOT NULL OR to_regclass('public.upload_sinanupload') IS NOT NULL OR to_regclass('public.upload_sinanuploadlogstatus') IS NOT NULL OR to_regclass('public.upload_sinanchunkedupload_id_seq') IS NOT NULL OR to_regclass('public.upload_sinanupload_id_seq') IS NOT NULL OR to_regclass('public.upload_sinanuploadlogstatus_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'public target object exists'; END IF;
    IF (SELECT count(*) FROM archive_sinan_upload.upload_sinanchunkedupload) <> :'expected_sinanchunkedupload_rows'::bigint OR (SELECT count(*) FROM archive_sinan_upload.upload_sinanupload) <> :'expected_sinanupload_rows'::bigint OR (SELECT count(*) FROM archive_sinan_upload.upload_sinanuploadlogstatus) <> :'expected_sinanuploadlogstatus_rows'::bigint THEN RAISE EXCEPTION 'archive row count mismatch'; END IF;
    IF (SELECT last_value FROM archive_sinan_upload.upload_sinanchunkedupload_id_seq) <> :'expected_sinanchunkedupload_id_seq_last_value'::bigint OR (SELECT is_called FROM archive_sinan_upload.upload_sinanchunkedupload_id_seq) IS DISTINCT FROM :'expected_sinanchunkedupload_id_seq_is_called'::boolean OR (SELECT last_value FROM archive_sinan_upload.upload_sinanupload_id_seq) <> :'expected_sinanupload_id_seq_last_value'::bigint OR (SELECT is_called FROM archive_sinan_upload.upload_sinanupload_id_seq) IS DISTINCT FROM :'expected_sinanupload_id_seq_is_called'::boolean OR (SELECT last_value FROM archive_sinan_upload.upload_sinanuploadlogstatus_id_seq) <> :'expected_sinanuploadlogstatus_id_seq_last_value'::bigint OR (SELECT is_called FROM archive_sinan_upload.upload_sinanuploadlogstatus_id_seq) IS DISTINCT FROM :'expected_sinanuploadlogstatus_id_seq_is_called'::boolean THEN RAISE EXCEPTION 'archive sequence state mismatch'; END IF;
    IF pg_get_serial_sequence('archive_sinan_upload.upload_sinanchunkedupload','id') IS DISTINCT FROM 'archive_sinan_upload.upload_sinanchunkedupload_id_seq' OR pg_get_serial_sequence('archive_sinan_upload.upload_sinanupload','id') IS DISTINCT FROM 'archive_sinan_upload.upload_sinanupload_id_seq' OR pg_get_serial_sequence('archive_sinan_upload.upload_sinanuploadlogstatus','id') IS DISTINCT FROM 'archive_sinan_upload.upload_sinanuploadlogstatus_id_seq' THEN RAISE EXCEPTION 'archive sequence ownership/default mapping mismatch'; END IF;
    IF (SELECT count(*) FROM pg_constraint WHERE contype='f' AND conrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass)) <> 3 THEN RAISE EXCEPTION 'archive FK inventory mismatch'; END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass) AND conrelid NOT IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass)) THEN RAISE EXCEPTION 'new inbound FK exists'; END IF;
    IF to_regclass('ingestion.run') IS NULL OR to_regclass('ingestion.sinan_stage') IS NULL OR to_regclass('public.auth_user') IS NULL THEN RAISE EXCEPTION 'protected active object is absent'; END IF;
END
$guard$;

LOCK TABLE archive_sinan_upload.upload_sinanchunkedupload, archive_sinan_upload.upload_sinanupload, archive_sinan_upload.upload_sinanuploadlogstatus IN ACCESS EXCLUSIVE MODE;
DROP TABLE archive_sinan_upload.upload_sinanupload;
DROP TABLE archive_sinan_upload.upload_sinanchunkedupload;
DROP TABLE archive_sinan_upload.upload_sinanuploadlogstatus;

DO $receipt$
BEGIN
    IF to_regclass('archive_sinan_upload.upload_sinanchunkedupload') IS NOT NULL OR to_regclass('archive_sinan_upload.upload_sinanupload') IS NOT NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus') IS NOT NULL OR to_regclass('archive_sinan_upload.upload_sinanchunkedupload_id_seq') IS NOT NULL OR to_regclass('archive_sinan_upload.upload_sinanupload_id_seq') IS NOT NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'archived objects remain after removal'; END IF;
    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_sinan_upload' AND c.relkind IN ('r','S','i')) THEN RAISE EXCEPTION 'archive schema is not empty'; END IF;
END
$receipt$;
DROP SCHEMA archive_sinan_upload;

SELECT 'SINAN_UPLOAD_REMOVAL_RECEIPT' AS receipt,
       current_database() AS database_name,
       (SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()) AS database_oid,
       :'verified_package_path' AS verified_package_path,
       :'expected_dump_sha256' AS expected_dump_sha256,
       :'verification_status' AS verification_status,
       :'expected_sinanchunkedupload_rows'::bigint AS expected_sinanchunkedupload_rows,
       :'expected_sinanupload_rows'::bigint AS expected_sinanupload_rows,
       :'expected_sinanuploadlogstatus_rows'::bigint AS expected_sinanuploadlogstatus_rows,
       clock_timestamp() AS removed_at_utc;

COMMIT;
