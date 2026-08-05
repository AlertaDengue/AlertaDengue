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
BEGIN; SET TRANSACTION READ ONLY; SET LOCAL statement_timeout='60s';
DO $$ BEGIN
  IF current_database()<>'infodengue' OR to_regclass('archive_infodengue_dbf_legacy.dbf_dbf') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_dbfchunkedupload') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_sendtopartner') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_dbf_id_seq') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_dbfchunkedupload_id_seq') IS NULL OR to_regclass('archive_infodengue_dbf_legacy.dbf_sendtopartner_id_seq') IS NULL THEN RAISE EXCEPTION 'archive inventory is incomplete'; END IF;
  IF to_regclass('public.dbf_dbf') IS NOT NULL OR to_regclass('public.dbf_dbfchunkedupload') IS NOT NULL OR to_regclass('public.dbf_sendtopartner') IS NOT NULL THEN RAISE EXCEPTION 'public DBF table remains'; END IF;
  IF (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_dbf)<>6964 OR (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_dbfchunkedupload)<>7635 OR (SELECT count(*) FROM archive_infodengue_dbf_legacy.dbf_sendtopartner)<>13 THEN RAISE EXCEPTION 'row counts differ from reviewed inventory'; END IF;
  IF (SELECT min(uploaded_at)::date FROM archive_infodengue_dbf_legacy.dbf_dbf)<>DATE '2016-10-05' OR (SELECT max(uploaded_at)::date FROM archive_infodengue_dbf_legacy.dbf_dbf)<>DATE '2026-01-20' OR (SELECT min(export_date) FROM archive_infodengue_dbf_legacy.dbf_dbf)<>DATE '2015-03-23' OR (SELECT max(export_date) FROM archive_infodengue_dbf_legacy.dbf_dbf)<>DATE '2026-01-20' OR (SELECT min(created_on)::date FROM archive_infodengue_dbf_legacy.dbf_dbfchunkedupload)<>DATE '2016-11-07' OR (SELECT max(created_on)::date FROM archive_infodengue_dbf_legacy.dbf_dbfchunkedupload)<>DATE '2026-01-20' OR (SELECT min(completed_on)::date FROM archive_infodengue_dbf_legacy.dbf_dbfchunkedupload)<>DATE '2016-11-07' OR (SELECT max(completed_on)::date FROM archive_infodengue_dbf_legacy.dbf_dbfchunkedupload)<>DATE '2026-01-20' THEN RAISE EXCEPTION 'date evidence differs from reviewed inventory'; END IF;
  IF (SELECT count(*) FROM pg_constraint WHERE conrelid IN ('archive_infodengue_dbf_legacy.dbf_dbf'::regclass,'archive_infodengue_dbf_legacy.dbf_dbfchunkedupload'::regclass,'archive_infodengue_dbf_legacy.dbf_sendtopartner'::regclass))<>7 THEN RAISE EXCEPTION 'constraint count mismatch'; END IF;
  IF (SELECT count(*) FROM pg_index WHERE indrelid IN ('archive_infodengue_dbf_legacy.dbf_dbf'::regclass,'archive_infodengue_dbf_legacy.dbf_dbfchunkedupload'::regclass,'archive_infodengue_dbf_legacy.dbf_sendtopartner'::regclass))<>7 THEN RAISE EXCEPTION 'index count mismatch'; END IF;
  IF (SELECT count(*) FROM pg_constraint WHERE contype='f' AND conrelid IN ('archive_infodengue_dbf_legacy.dbf_dbf'::regclass,'archive_infodengue_dbf_legacy.dbf_dbfchunkedupload'::regclass) AND confrelid='public.auth_user'::regclass)<>2 THEN RAISE EXCEPTION 'foreign-key inventory mismatch'; END IF;
END $$;
SELECT 'archive_infodengue_dbf_legacy.dbf_dbf' AS object_name,count(*) AS rows FROM archive_infodengue_dbf_legacy.dbf_dbf UNION ALL SELECT 'archive_infodengue_dbf_legacy.dbf_dbfchunkedupload',count(*) FROM archive_infodengue_dbf_legacy.dbf_dbfchunkedupload UNION ALL SELECT 'archive_infodengue_dbf_legacy.dbf_sendtopartner',count(*) FROM archive_infodengue_dbf_legacy.dbf_sendtopartner;
SELECT sequence_name,last_value,is_called FROM (SELECT 'dbf_dbf_id_seq' sequence_name,last_value,is_called FROM archive_infodengue_dbf_legacy.dbf_dbf_id_seq UNION ALL SELECT 'dbf_dbfchunkedupload_id_seq',last_value,is_called FROM archive_infodengue_dbf_legacy.dbf_dbfchunkedupload_id_seq UNION ALL SELECT 'dbf_sendtopartner_id_seq',last_value,is_called FROM archive_infodengue_dbf_legacy.dbf_sendtopartner_id_seq) q ORDER BY 1;
SELECT c.oid::regclass AS object_name,pg_get_userbyid(c.relowner) AS owner_name,coalesce(array_to_string(c.relacl,','),'') AS grants FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_infodengue_dbf_legacy' AND c.relkind IN ('r','S') ORDER BY 1;
SELECT conrelid::regclass AS table_name,conname,contype,pg_get_constraintdef(oid) AS definition,convalidated FROM pg_constraint WHERE conrelid IN ('archive_infodengue_dbf_legacy.dbf_dbf'::regclass,'archive_infodengue_dbf_legacy.dbf_dbfchunkedupload'::regclass,'archive_infodengue_dbf_legacy.dbf_sendtopartner'::regclass) ORDER BY 1,2;
SELECT indrelid::regclass AS table_name,indexrelid::regclass AS index_name,pg_get_indexdef(indexrelid) AS definition FROM pg_index WHERE indrelid IN ('archive_infodengue_dbf_legacy.dbf_dbf'::regclass,'archive_infodengue_dbf_legacy.dbf_dbfchunkedupload'::regclass,'archive_infodengue_dbf_legacy.dbf_sendtopartner'::regclass) ORDER BY 1,2;
ROLLBACK;
