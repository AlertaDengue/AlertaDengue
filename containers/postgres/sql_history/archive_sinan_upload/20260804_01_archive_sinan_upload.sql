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
SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.archive_sinan_upload'));

DO $guard$
DECLARE
    expected_tables constant text[] := ARRAY['upload_sinanchunkedupload','upload_sinanupload','upload_sinanuploadlogstatus'];
    expected_sequences constant text[] := ARRAY['upload_sinanchunkedupload_id_seq','upload_sinanupload_id_seq','upload_sinanuploadlogstatus_id_seq'];
    actual text[];
BEGIN
    IF pg_is_in_recovery() THEN RAISE EXCEPTION 'database is in recovery'; END IF;
    IF (SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()) IS NULL THEN RAISE EXCEPTION 'database OID unavailable'; END IF;
    IF NOT has_database_privilege(current_user,current_database(),'CONNECT') OR NOT has_database_privilege(current_user,current_database(),'CREATE') THEN RAISE EXCEPTION 'role lacks required access'; END IF;
    SELECT coalesce(array_agg(c.relname ORDER BY c.relname),ARRAY[]::text[]) INTO actual FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relname=ANY(expected_tables);
    IF actual IS DISTINCT FROM expected_tables THEN RAISE EXCEPTION 'source table inventory is incomplete: %',actual; END IF;
    SELECT coalesce(array_agg(c.relname ORDER BY c.relname),ARRAY[]::text[]) INTO actual FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='S' AND c.relname=ANY(expected_sequences);
    IF actual IS DISTINCT FROM expected_sequences THEN RAISE EXCEPTION 'source sequence inventory is incomplete: %',actual; END IF;
    IF EXISTS (SELECT 1 FROM pg_namespace n JOIN pg_class c ON c.relnamespace=n.oid WHERE n.nspname='archive_sinan_upload' AND c.relkind IN ('r','S','i','v','m','f','p')) THEN RAISE EXCEPTION 'archive schema is not empty'; END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid IN ('public.upload_sinanchunkedupload'::regclass,'public.upload_sinanupload'::regclass,'public.upload_sinanuploadlogstatus'::regclass) AND conrelid NOT IN ('public.upload_sinanchunkedupload'::regclass,'public.upload_sinanupload'::regclass,'public.upload_sinanuploadlogstatus'::regclass)) THEN RAISE EXCEPTION 'unexpected inbound FK'; END IF;
    IF EXISTS (SELECT 1 FROM pg_depend d JOIN pg_rewrite r ON r.oid=d.objid WHERE d.refobjid IN ('public.upload_sinanchunkedupload'::regclass,'public.upload_sinanupload'::regclass,'public.upload_sinanuploadlogstatus'::regclass)) THEN RAISE EXCEPTION 'view or rule depends on source'; END IF;
    IF EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_proc'::regclass AND d.refobjid IN ('public.upload_sinanchunkedupload'::regclass,'public.upload_sinanupload'::regclass,'public.upload_sinanuploadlogstatus'::regclass)) THEN RAISE EXCEPTION 'function or procedure depends on source'; END IF;
    IF to_regclass('ingestion.run') IS NULL OR to_regclass('ingestion.sinan_stage') IS NULL OR to_regclass('public.auth_user') IS NULL THEN RAISE EXCEPTION 'protected active object is absent'; END IF;
END
$guard$;

LOCK TABLE public.upload_sinanchunkedupload, public.upload_sinanupload, public.upload_sinanuploadlogstatus IN ACCESS EXCLUSIVE MODE;

CREATE TEMP TABLE sinan_archive_before ON COMMIT DROP AS
SELECT c.oid AS table_oid, format('%I.%I', n.nspname, c.relname) AS object_name,
       (xpath('/row/count/text()',query_to_xml(format('SELECT count(*) AS count FROM %I.%I',n.nspname,c.relname),false,true,'')))[1]::text::bigint AS exact_rows,
       pg_get_userbyid(c.relowner) AS owner_name, c.relacl
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE c.oid IN ('public.upload_sinanchunkedupload'::regclass,'public.upload_sinanupload'::regclass,'public.upload_sinanuploadlogstatus'::regclass);

CREATE TEMP TABLE sinan_sequence_before ON COMMIT DROP AS
SELECT 'upload_sinanchunkedupload_id_seq'::text AS sequence_name,last_value,is_called FROM public.upload_sinanchunkedupload_id_seq
UNION ALL SELECT 'upload_sinanupload_id_seq',last_value,is_called FROM public.upload_sinanupload_id_seq
UNION ALL SELECT 'upload_sinanuploadlogstatus_id_seq',last_value,is_called FROM public.upload_sinanuploadlogstatus_id_seq;

CREATE TEMP TABLE sinan_fk_before ON COMMIT DROP AS
SELECT con.oid AS constraint_oid,con.conname,con.conrelid,con.confrelid,sa.attname AS source_column,ra.attname AS referenced_column,con.conkey,con.confkey,con.confmatchtype,con.confupdtype,con.confdeltype,con.condeferrable,con.condeferred,con.convalidated
  FROM pg_constraint con JOIN pg_attribute sa ON sa.attrelid=con.conrelid AND sa.attnum=con.conkey[1] JOIN pg_attribute ra ON ra.attrelid=con.confrelid AND ra.attnum=con.confkey[1]
 WHERE con.contype='f' AND con.conrelid IN ('public.upload_sinanchunkedupload'::regclass,'public.upload_sinanupload'::regclass,'public.upload_sinanuploadlogstatus'::regclass);

DO $fk$
BEGIN
    IF (SELECT count(*) FROM sinan_fk_before) <> 3 THEN RAISE EXCEPTION 'unexpected outbound FK count'; END IF;
END
$fk$;

DO $schema$
BEGIN
    IF to_regnamespace('archive_sinan_upload') IS NULL THEN
        CREATE SCHEMA archive_sinan_upload;
    END IF;
    ALTER SCHEMA archive_sinan_upload OWNER TO CURRENT_USER;
END
$schema$;

ALTER TABLE public.upload_sinanchunkedupload SET SCHEMA archive_sinan_upload;
ALTER TABLE public.upload_sinanupload SET SCHEMA archive_sinan_upload;
ALTER TABLE public.upload_sinanuploadlogstatus SET SCHEMA archive_sinan_upload;

DO $validate$
DECLARE matched integer;
BEGIN
    IF to_regclass('public.upload_sinanchunkedupload') IS NOT NULL OR to_regclass('public.upload_sinanupload') IS NOT NULL OR to_regclass('public.upload_sinanuploadlogstatus') IS NOT NULL OR to_regclass('public.upload_sinanchunkedupload_id_seq') IS NOT NULL OR to_regclass('public.upload_sinanupload_id_seq') IS NOT NULL OR to_regclass('public.upload_sinanuploadlogstatus_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'source objects remain public'; END IF;
    IF to_regclass('archive_sinan_upload.upload_sinanchunkedupload') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanupload') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanchunkedupload_id_seq') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanupload_id_seq') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus_id_seq') IS NULL THEN RAISE EXCEPTION 'archive inventory is incomplete'; END IF;
    IF (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_sinan_upload' AND c.relkind IN ('r','S','i')) <> 14 THEN RAISE EXCEPTION 'archive schema has unexpected relation inventory'; END IF;
    IF (SELECT count(*) FROM sinan_archive_before WHERE object_name='public.upload_sinanchunkedupload') IS DISTINCT FROM 1 OR (SELECT exact_rows FROM sinan_archive_before WHERE object_name='public.upload_sinanchunkedupload') IS DISTINCT FROM (SELECT count(*) FROM archive_sinan_upload.upload_sinanchunkedupload) THEN RAISE EXCEPTION 'chunk row count changed'; END IF;
    IF (SELECT exact_rows FROM sinan_archive_before WHERE object_name='public.upload_sinanupload') IS DISTINCT FROM (SELECT count(*) FROM archive_sinan_upload.upload_sinanupload) OR (SELECT exact_rows FROM sinan_archive_before WHERE object_name='public.upload_sinanuploadlogstatus') IS DISTINCT FROM (SELECT count(*) FROM archive_sinan_upload.upload_sinanuploadlogstatus) THEN RAISE EXCEPTION 'upload row count changed'; END IF;
    IF EXISTS (SELECT 1 FROM sinan_archive_before b JOIN pg_class c ON c.oid=b.table_oid WHERE c.relname IN ('upload_sinanchunkedupload','upload_sinanupload','upload_sinanuploadlogstatus') AND (pg_get_userbyid(c.relowner) IS DISTINCT FROM b.owner_name OR c.relacl IS DISTINCT FROM b.relacl)) THEN RAISE EXCEPTION 'owner or grants changed'; END IF;
    IF EXISTS (SELECT 1 FROM sinan_sequence_before b JOIN LATERAL (SELECT last_value,is_called FROM archive_sinan_upload.upload_sinanchunkedupload_id_seq) s ON b.sequence_name='upload_sinanchunkedupload_id_seq' WHERE s.last_value IS DISTINCT FROM b.last_value OR s.is_called IS DISTINCT FROM b.is_called) OR EXISTS (SELECT 1 FROM sinan_sequence_before b JOIN LATERAL (SELECT last_value,is_called FROM archive_sinan_upload.upload_sinanupload_id_seq) s ON b.sequence_name='upload_sinanupload_id_seq' WHERE s.last_value IS DISTINCT FROM b.last_value OR s.is_called IS DISTINCT FROM b.is_called) OR EXISTS (SELECT 1 FROM sinan_sequence_before b JOIN LATERAL (SELECT last_value,is_called FROM archive_sinan_upload.upload_sinanuploadlogstatus_id_seq) s ON b.sequence_name='upload_sinanuploadlogstatus_id_seq' WHERE s.last_value IS DISTINCT FROM b.last_value OR s.is_called IS DISTINCT FROM b.is_called) THEN RAISE EXCEPTION 'sequence state changed'; END IF;
    IF EXISTS (SELECT 1 FROM pg_class seq JOIN pg_depend dep ON dep.objid=seq.oid AND dep.deptype='a' JOIN pg_class tbl ON tbl.oid=dep.refobjid WHERE seq.oid IN ('archive_sinan_upload.upload_sinanchunkedupload_id_seq'::regclass,'archive_sinan_upload.upload_sinanupload_id_seq'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus_id_seq'::regclass) AND (tbl.relnamespace <> 'archive_sinan_upload'::regnamespace OR dep.refobjsubid <> 1)) THEN RAISE EXCEPTION 'sequence ownership changed'; END IF;
    IF pg_get_serial_sequence('archive_sinan_upload.upload_sinanchunkedupload','id') IS DISTINCT FROM 'archive_sinan_upload.upload_sinanchunkedupload_id_seq' OR pg_get_serial_sequence('archive_sinan_upload.upload_sinanupload','id') IS DISTINCT FROM 'archive_sinan_upload.upload_sinanupload_id_seq' OR pg_get_serial_sequence('archive_sinan_upload.upload_sinanuploadlogstatus','id') IS DISTINCT FROM 'archive_sinan_upload.upload_sinanuploadlogstatus_id_seq' THEN RAISE EXCEPTION 'sequence default mapping changed'; END IF;
    SELECT count(*) INTO matched FROM pg_constraint con JOIN pg_attribute sa ON sa.attrelid=con.conrelid AND sa.attnum=con.conkey[1] JOIN pg_attribute ra ON ra.attrelid=con.confrelid AND ra.attnum=con.confkey[1] WHERE con.contype='f' AND con.conrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass) AND con.convalidated AND con.confmatchtype='s' AND con.confupdtype='a' AND con.confdeltype='a' AND con.condeferrable AND con.condeferred AND ((con.conname='upload_sinanchunkedupload_user_id_d183233a_fk_auth_user_id' AND con.confrelid='public.auth_user'::regclass AND sa.attname='user_id' AND ra.attname='id') OR (con.conname='upload_sinanupload_upload_id_97f6c7e1_fk_upload_si' AND con.confrelid='archive_sinan_upload.upload_sinanchunkedupload'::regclass AND sa.attname='upload_id' AND ra.attname='id') OR (con.conname='upload_sinanupload_status_id_998c10bf_fk_upload_si' AND con.confrelid='archive_sinan_upload.upload_sinanuploadlogstatus'::regclass AND sa.attname='status_id' AND ra.attname='id'));
    IF matched <> 3 OR (SELECT count(*) FROM pg_constraint WHERE contype='f' AND conrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass)) <> 3 THEN RAISE EXCEPTION 'archived FK structure changed'; END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass) AND conrelid NOT IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass)) THEN RAISE EXCEPTION 'new inbound dependency exists'; END IF;
    IF to_regclass('ingestion.run') IS NULL OR to_regclass('ingestion.sinan_stage') IS NULL OR to_regclass('public.auth_user') IS NULL THEN RAISE EXCEPTION 'protected object disappeared'; END IF;
END
$validate$;

SELECT 'archive_sinan_upload' AS archive_schema, c.oid::regclass AS object_name,
       pg_get_userbyid(c.relowner) AS owner, pg_total_relation_size(c.oid) AS total_bytes
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='archive_sinan_upload' AND c.relkind IN ('r','S','i')
 ORDER BY 2;

COMMIT;
