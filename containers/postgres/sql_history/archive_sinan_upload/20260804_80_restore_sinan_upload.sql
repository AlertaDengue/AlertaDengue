\set ON_ERROR_STOP on
\pset pager off

\if :{?expected_database_name}
\else
  \echo 'ERROR: expected_database_name is required'
  DO $error$
  BEGIN
    RAISE EXCEPTION 'expected_database_name is required';
  END
  $error$;
\endif
SELECT current_database() = :'expected_database_name' AS database_name_matches
\gset
\if :database_name_matches
\else
  \echo 'ERROR: connected database does not match expected_database_name'
  DO $error$
  BEGIN
    RAISE EXCEPTION 'connected database does not match expected_database_name';
  END
  $error$;
\endif

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';
SET LOCAL idle_in_transaction_session_timeout = '5min';
SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.restore_sinan_upload'));

DO $guard$
DECLARE matched integer;
BEGIN
    IF pg_is_in_recovery() THEN RAISE EXCEPTION 'database is in recovery'; END IF;
    IF to_regclass('public.upload_sinanchunkedupload') IS NOT NULL OR to_regclass('public.upload_sinanupload') IS NOT NULL OR to_regclass('public.upload_sinanuploadlogstatus') IS NOT NULL OR to_regclass('public.upload_sinanchunkedupload_id_seq') IS NOT NULL OR to_regclass('public.upload_sinanupload_id_seq') IS NOT NULL OR to_regclass('public.upload_sinanuploadlogstatus_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'public target inventory is not empty'; END IF;
    IF to_regclass('archive_sinan_upload.upload_sinanchunkedupload') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanupload') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanchunkedupload_id_seq') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanupload_id_seq') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus_id_seq') IS NULL THEN RAISE EXCEPTION 'archive inventory is incomplete'; END IF;
    IF (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_sinan_upload' AND c.relkind IN ('r','S','i')) <> 14 THEN RAISE EXCEPTION 'archive inventory contains unexpected relations'; END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass) AND conrelid NOT IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass)) THEN RAISE EXCEPTION 'unexpected inbound FK dependency blocks restore'; END IF;
    IF EXISTS (SELECT 1 FROM pg_depend d JOIN pg_rewrite r ON r.oid=d.objid WHERE d.refobjid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass)) THEN RAISE EXCEPTION 'unexpected view or rule dependency blocks restore'; END IF;
    SELECT count(*) INTO matched FROM pg_constraint con JOIN pg_attribute sa ON sa.attrelid=con.conrelid AND sa.attnum=con.conkey[1] JOIN pg_attribute ra ON ra.attrelid=con.confrelid AND ra.attnum=con.confkey[1] WHERE con.contype='f' AND con.conrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass) AND con.convalidated AND con.confmatchtype='s' AND con.confupdtype='a' AND con.confdeltype='a' AND con.condeferrable AND con.condeferred AND ((con.conname='upload_sinanchunkedupload_user_id_d183233a_fk_auth_user_id' AND con.confrelid='public.auth_user'::regclass AND sa.attname='user_id' AND ra.attname='id') OR (con.conname='upload_sinanupload_upload_id_97f6c7e1_fk_upload_si' AND con.confrelid='archive_sinan_upload.upload_sinanchunkedupload'::regclass AND sa.attname='upload_id' AND ra.attname='id') OR (con.conname='upload_sinanupload_status_id_998c10bf_fk_upload_si' AND con.confrelid='archive_sinan_upload.upload_sinanuploadlogstatus'::regclass AND sa.attname='status_id' AND ra.attname='id'));
    IF matched <> 3 THEN RAISE EXCEPTION 'archive FK structure is incomplete'; END IF;
    IF to_regclass('ingestion.run') IS NULL OR to_regclass('ingestion.sinan_stage') IS NULL OR to_regclass('public.auth_user') IS NULL THEN RAISE EXCEPTION 'protected active object is absent'; END IF;
END
$guard$;

LOCK TABLE archive_sinan_upload.upload_sinanchunkedupload,archive_sinan_upload.upload_sinanupload,archive_sinan_upload.upload_sinanuploadlogstatus IN ACCESS EXCLUSIVE MODE;
CREATE TEMP TABLE sinan_restore_before ON COMMIT DROP AS SELECT 'upload_sinanchunkedupload'::text AS table_name,count(*)::bigint AS exact_rows FROM archive_sinan_upload.upload_sinanchunkedupload UNION ALL SELECT 'upload_sinanupload',count(*) FROM archive_sinan_upload.upload_sinanupload UNION ALL SELECT 'upload_sinanuploadlogstatus',count(*) FROM archive_sinan_upload.upload_sinanuploadlogstatus;
CREATE TEMP TABLE sinan_restore_sequences ON COMMIT DROP AS SELECT 'upload_sinanchunkedupload_id_seq'::text AS sequence_name,last_value,is_called FROM archive_sinan_upload.upload_sinanchunkedupload_id_seq UNION ALL SELECT 'upload_sinanupload_id_seq',last_value,is_called FROM archive_sinan_upload.upload_sinanupload_id_seq UNION ALL SELECT 'upload_sinanuploadlogstatus_id_seq',last_value,is_called FROM archive_sinan_upload.upload_sinanuploadlogstatus_id_seq;
CREATE TEMP TABLE sinan_restore_acl ON COMMIT DROP AS SELECT c.oid,c.relname,pg_get_userbyid(c.relowner) AS owner_name,c.relacl FROM pg_class c WHERE c.oid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass,'archive_sinan_upload.upload_sinanchunkedupload_id_seq'::regclass,'archive_sinan_upload.upload_sinanupload_id_seq'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus_id_seq'::regclass);

ALTER TABLE archive_sinan_upload.upload_sinanchunkedupload SET SCHEMA public;
ALTER TABLE archive_sinan_upload.upload_sinanupload SET SCHEMA public;
ALTER TABLE archive_sinan_upload.upload_sinanuploadlogstatus SET SCHEMA public;

DO $postcheck$
BEGIN
    IF to_regclass('public.upload_sinanchunkedupload') IS NULL OR to_regclass('public.upload_sinanupload') IS NULL OR to_regclass('public.upload_sinanuploadlogstatus') IS NULL OR to_regclass('public.upload_sinanchunkedupload_id_seq') IS NULL OR to_regclass('public.upload_sinanupload_id_seq') IS NULL OR to_regclass('public.upload_sinanuploadlogstatus_id_seq') IS NULL THEN RAISE EXCEPTION 'public restore inventory is incomplete'; END IF;
    IF to_regclass('archive_sinan_upload.upload_sinanchunkedupload') IS NOT NULL OR to_regclass('archive_sinan_upload.upload_sinanupload') IS NOT NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus') IS NOT NULL OR to_regclass('archive_sinan_upload.upload_sinanchunkedupload_id_seq') IS NOT NULL OR to_regclass('archive_sinan_upload.upload_sinanupload_id_seq') IS NOT NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'archive objects remain after restore'; END IF;
    IF (SELECT exact_rows FROM sinan_restore_before WHERE table_name='upload_sinanchunkedupload') IS DISTINCT FROM (SELECT count(*) FROM public.upload_sinanchunkedupload) OR (SELECT exact_rows FROM sinan_restore_before WHERE table_name='upload_sinanupload') IS DISTINCT FROM (SELECT count(*) FROM public.upload_sinanupload) OR (SELECT exact_rows FROM sinan_restore_before WHERE table_name='upload_sinanuploadlogstatus') IS DISTINCT FROM (SELECT count(*) FROM public.upload_sinanuploadlogstatus) THEN RAISE EXCEPTION 'row count changed during restore'; END IF;
    IF (SELECT last_value FROM public.upload_sinanchunkedupload_id_seq) IS DISTINCT FROM (SELECT last_value FROM sinan_restore_sequences WHERE sequence_name='upload_sinanchunkedupload_id_seq') OR (SELECT is_called FROM public.upload_sinanchunkedupload_id_seq) IS DISTINCT FROM (SELECT is_called FROM sinan_restore_sequences WHERE sequence_name='upload_sinanchunkedupload_id_seq') OR (SELECT last_value FROM public.upload_sinanupload_id_seq) IS DISTINCT FROM (SELECT last_value FROM sinan_restore_sequences WHERE sequence_name='upload_sinanupload_id_seq') OR (SELECT is_called FROM public.upload_sinanupload_id_seq) IS DISTINCT FROM (SELECT is_called FROM sinan_restore_sequences WHERE sequence_name='upload_sinanupload_id_seq') OR (SELECT last_value FROM public.upload_sinanuploadlogstatus_id_seq) IS DISTINCT FROM (SELECT last_value FROM sinan_restore_sequences WHERE sequence_name='upload_sinanuploadlogstatus_id_seq') OR (SELECT is_called FROM public.upload_sinanuploadlogstatus_id_seq) IS DISTINCT FROM (SELECT is_called FROM sinan_restore_sequences WHERE sequence_name='upload_sinanuploadlogstatus_id_seq') THEN RAISE EXCEPTION 'sequence state changed during restore'; END IF;
    IF pg_get_serial_sequence('public.upload_sinanchunkedupload','id') IS DISTINCT FROM 'public.upload_sinanchunkedupload_id_seq' OR pg_get_serial_sequence('public.upload_sinanupload','id') IS DISTINCT FROM 'public.upload_sinanupload_id_seq' OR pg_get_serial_sequence('public.upload_sinanuploadlogstatus','id') IS DISTINCT FROM 'public.upload_sinanuploadlogstatus_id_seq' THEN RAISE EXCEPTION 'restored defaults do not resolve to public sequences'; END IF;
    IF EXISTS (SELECT 1 FROM sinan_restore_acl b JOIN pg_class c ON c.oid=b.oid WHERE pg_get_userbyid(c.relowner) IS DISTINCT FROM b.owner_name OR c.relacl IS DISTINCT FROM b.relacl) THEN RAISE EXCEPTION 'owner or grants changed during restore'; END IF;
    IF EXISTS (SELECT 1 FROM pg_class seq JOIN pg_depend dep ON dep.objid=seq.oid AND dep.deptype='a' JOIN pg_class tbl ON tbl.oid=dep.refobjid WHERE seq.oid IN ('public.upload_sinanchunkedupload_id_seq'::regclass,'public.upload_sinanupload_id_seq'::regclass,'public.upload_sinanuploadlogstatus_id_seq'::regclass) AND (tbl.relnamespace <> 'public'::regnamespace OR dep.refobjsubid <> 1)) THEN RAISE EXCEPTION 'owned sequence mapping changed during restore'; END IF;
    IF (SELECT count(*) FROM pg_constraint WHERE contype='f' AND conrelid IN ('public.upload_sinanchunkedupload'::regclass,'public.upload_sinanupload'::regclass,'public.upload_sinanuploadlogstatus'::regclass)) <> 3 THEN RAISE EXCEPTION 'restored FK inventory is incomplete'; END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid IN ('public.upload_sinanchunkedupload'::regclass,'public.upload_sinanupload'::regclass,'public.upload_sinanuploadlogstatus'::regclass) AND conrelid NOT IN ('public.upload_sinanchunkedupload'::regclass,'public.upload_sinanupload'::regclass,'public.upload_sinanuploadlogstatus'::regclass)) THEN RAISE EXCEPTION 'new inbound FK exists after restore'; END IF;
    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_sinan_upload' AND c.relkind IN ('r','S','i')) THEN RAISE EXCEPTION 'archive schema is not empty after restore'; END IF;
    IF to_regclass('ingestion.run') IS NULL OR to_regclass('ingestion.sinan_stage') IS NULL OR to_regclass('public.auth_user') IS NULL THEN RAISE EXCEPTION 'protected active object disappeared'; END IF;
END
$postcheck$;

DROP SCHEMA archive_sinan_upload;
COMMIT;
