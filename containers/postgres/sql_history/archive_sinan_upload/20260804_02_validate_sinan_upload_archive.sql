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
SET TRANSACTION READ ONLY;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
SET LOCAL idle_in_transaction_session_timeout = '60s';

DO $guard$
DECLARE
    matched integer;
BEGIN
    IF pg_is_in_recovery() THEN RAISE EXCEPTION 'database is in recovery'; END IF;
    IF to_regclass('public.upload_sinanchunkedupload') IS NOT NULL OR to_regclass('public.upload_sinanupload') IS NOT NULL OR to_regclass('public.upload_sinanuploadlogstatus') IS NOT NULL OR to_regclass('public.upload_sinanchunkedupload_id_seq') IS NOT NULL OR to_regclass('public.upload_sinanupload_id_seq') IS NOT NULL OR to_regclass('public.upload_sinanuploadlogstatus_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'one or more archived objects remain in public'; END IF;
    IF to_regclass('archive_sinan_upload.upload_sinanchunkedupload') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanupload') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanchunkedupload_id_seq') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanupload_id_seq') IS NULL OR to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus_id_seq') IS NULL THEN RAISE EXCEPTION 'archive inventory is incomplete'; END IF;
    IF (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_sinan_upload' AND c.relkind IN ('r','S','i')) <> 14 THEN RAISE EXCEPTION 'archive inventory contains unexpected relations'; END IF;
    SELECT count(*) INTO matched FROM pg_constraint con JOIN pg_attribute sa ON sa.attrelid=con.conrelid AND sa.attnum=con.conkey[1] JOIN pg_attribute ra ON ra.attrelid=con.confrelid AND ra.attnum=con.confkey[1] WHERE con.contype='f' AND con.conrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass) AND con.confmatchtype='s' AND con.confupdtype='a' AND con.confdeltype='a' AND con.condeferrable AND con.condeferred AND con.convalidated AND ((con.conname='upload_sinanchunkedupload_user_id_d183233a_fk_auth_user_id' AND con.confrelid='public.auth_user'::regclass AND sa.attname='user_id' AND ra.attname='id') OR (con.conname='upload_sinanupload_upload_id_97f6c7e1_fk_upload_si' AND con.confrelid='archive_sinan_upload.upload_sinanchunkedupload'::regclass AND sa.attname='upload_id' AND ra.attname='id') OR (con.conname='upload_sinanupload_status_id_998c10bf_fk_upload_si' AND con.confrelid='archive_sinan_upload.upload_sinanuploadlogstatus'::regclass AND sa.attname='status_id' AND ra.attname='id'));
    IF matched <> 3 OR (SELECT count(*) FROM pg_constraint WHERE contype='f' AND conrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass)) <> 3 THEN RAISE EXCEPTION 'archive FK structure is incomplete or unexpected'; END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass) AND conrelid NOT IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass)) THEN RAISE EXCEPTION 'unexpected inbound FK dependency'; END IF;
    IF EXISTS (SELECT 1 FROM pg_depend d JOIN pg_rewrite r ON r.oid=d.objid WHERE d.refobjid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass)) THEN RAISE EXCEPTION 'unexpected view or rule dependency'; END IF;
    IF to_regclass('ingestion.run') IS NULL OR to_regclass('ingestion.sinan_stage') IS NULL OR to_regclass('public.auth_user') IS NULL THEN RAISE EXCEPTION 'protected active object is absent'; END IF;
    IF pg_get_serial_sequence('archive_sinan_upload.upload_sinanchunkedupload','id') IS DISTINCT FROM 'archive_sinan_upload.upload_sinanchunkedupload_id_seq' OR pg_get_serial_sequence('archive_sinan_upload.upload_sinanupload','id') IS DISTINCT FROM 'archive_sinan_upload.upload_sinanupload_id_seq' OR pg_get_serial_sequence('archive_sinan_upload.upload_sinanuploadlogstatus','id') IS DISTINCT FROM 'archive_sinan_upload.upload_sinanuploadlogstatus_id_seq' THEN RAISE EXCEPTION 'sequence defaults do not resolve to archived sequences'; END IF;
END
$guard$;

SELECT 'archive_sinan_upload.upload_sinanchunkedupload' AS object_name, count(*) AS exact_rows FROM archive_sinan_upload.upload_sinanchunkedupload
UNION ALL SELECT 'archive_sinan_upload.upload_sinanupload', count(*) FROM archive_sinan_upload.upload_sinanupload
UNION ALL SELECT 'archive_sinan_upload.upload_sinanuploadlogstatus', count(*) FROM archive_sinan_upload.upload_sinanuploadlogstatus;

SELECT 'archive_sinan_upload.upload_sinanchunkedupload_id_seq' AS sequence_name,last_value,is_called FROM archive_sinan_upload.upload_sinanchunkedupload_id_seq
UNION ALL SELECT 'archive_sinan_upload.upload_sinanupload_id_seq',last_value,is_called FROM archive_sinan_upload.upload_sinanupload_id_seq
UNION ALL SELECT 'archive_sinan_upload.upload_sinanuploadlogstatus_id_seq',last_value,is_called FROM archive_sinan_upload.upload_sinanuploadlogstatus_id_seq;

SELECT seq.oid::regclass AS sequence_name,tbl.oid::regclass AS owned_table,dep.refobjsubid AS owned_column,pg_get_serial_sequence(tbl.oid::regclass::text,'id') AS serial_sequence
  FROM pg_class seq JOIN pg_depend dep ON dep.objid=seq.oid AND dep.deptype='a' JOIN pg_class tbl ON tbl.oid=dep.refobjid
 WHERE seq.oid IN ('archive_sinan_upload.upload_sinanchunkedupload_id_seq'::regclass,'archive_sinan_upload.upload_sinanupload_id_seq'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus_id_seq'::regclass) ORDER BY 1;

SELECT c.oid::regclass AS object_name,pg_get_userbyid(c.relowner) AS owner,COALESCE(array_to_string(c.relacl,','),'') AS grants FROM pg_class c WHERE c.oid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass,'archive_sinan_upload.upload_sinanchunkedupload_id_seq'::regclass,'archive_sinan_upload.upload_sinanupload_id_seq'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus_id_seq'::regclass) ORDER BY 1;

SELECT con.conrelid::regclass AS table_name,con.conname,con.contype,con.conkey,con.confrelid::regclass AS referenced_table,con.confkey,con.confmatchtype,con.confupdtype,con.confdeltype,con.condeferrable,con.condeferred,con.convalidated,pg_get_constraintdef(con.oid) AS informational_definition FROM pg_constraint con WHERE con.conrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass) ORDER BY 1,2;

SELECT x.indrelid::regclass AS table_name,i.relname AS index_name,x.indisprimary,x.indisunique,pg_get_indexdef(i.oid) AS informational_definition FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid WHERE x.indrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,'archive_sinan_upload.upload_sinanupload'::regclass,'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass) ORDER BY 1,2;

ROLLBACK;
