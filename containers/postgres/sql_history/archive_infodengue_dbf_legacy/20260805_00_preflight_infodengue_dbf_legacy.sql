\set ON_ERROR_STOP on
\pset pager off
\if :{?expected_database_name}
\else
  \echo 'ERROR: expected_database_name is required'
  DO $$ BEGIN RAISE EXCEPTION 'expected_database_name is required'; END $$;
\endif
SELECT current_database() = :'expected_database_name' AS ok \gset
\if :ok
\else
  DO $$ BEGIN RAISE EXCEPTION 'connected database does not match expected_database_name'; END $$;
\endif
BEGIN;
SET TRANSACTION READ ONLY;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='60s';

SELECT current_database() AS database_name,
       (SELECT oid FROM pg_database WHERE datname=current_database()) AS database_oid,
       current_setting('server_version') AS server_version,
       pg_is_in_recovery() AS in_recovery,
       current_user AS execution_role;

DO $guard$
DECLARE t text[]; s text[];
BEGIN
  IF current_database() <> 'infodengue' OR pg_is_in_recovery() THEN RAISE EXCEPTION 'wrong or recovering database'; END IF;
  SELECT coalesce(array_agg(c.relname ORDER BY c.relname),'{}') INTO t FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relname IN ('dbf_dbf','dbf_dbfchunkedupload','dbf_sendtopartner');
  IF t IS DISTINCT FROM ARRAY['dbf_dbf','dbf_dbfchunkedupload','dbf_sendtopartner'] THEN RAISE EXCEPTION 'table inventory mismatch: %',t; END IF;
  SELECT coalesce(array_agg(c.relname ORDER BY c.relname),'{}') INTO s FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='S' AND c.relname IN ('dbf_dbf_id_seq','dbf_dbfchunkedupload_id_seq','dbf_sendtopartner_id_seq');
  IF s IS DISTINCT FROM ARRAY['dbf_dbf_id_seq','dbf_dbfchunkedupload_id_seq','dbf_sendtopartner_id_seq'] THEN RAISE EXCEPTION 'sequence inventory mismatch: %',s; END IF;
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname='archive_infodengue_dbf_legacy') THEN RAISE EXCEPTION 'archive schema already exists'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname='auth_user') THEN RAISE EXCEPTION 'protected auth_user object missing'; END IF;
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass,'public.dbf_sendtopartner'::regclass) AND conrelid NOT IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass,'public.dbf_sendtopartner'::regclass)) THEN RAISE EXCEPTION 'unexpected inbound dependency'; END IF;
END $guard$;

CREATE TEMP TABLE preflight_target_counts (table_name text, exact_rows bigint, total_bytes bigint) ON COMMIT DROP;
DO $counts$
DECLARE
  target record;
  exact_rows bigint;
  total_bytes bigint;
BEGIN
  FOR target IN
    SELECT *
      FROM (VALUES
        ('public'::text, 'dbf_dbf'::text),
        ('public'::text, 'dbf_dbfchunkedupload'::text),
        ('public'::text, 'dbf_sendtopartner'::text)
      ) AS target_tables(schema_name, table_name)
  LOOP
    EXECUTE format(
      'SELECT count(*) FROM %I.%I',
      target.schema_name,
      target.table_name
    ) INTO exact_rows;
    EXECUTE format(
      'SELECT pg_total_relation_size(%L::regclass)',
      format('%I.%I', target.schema_name, target.table_name)
    ) INTO total_bytes;
    INSERT INTO preflight_target_counts(table_name, exact_rows, total_bytes)
    VALUES (format('%I.%I', target.schema_name, target.table_name), exact_rows, total_bytes);
  END LOOP;
END $counts$;
SELECT table_name, exact_rows, total_bytes
  FROM preflight_target_counts
 ORDER BY table_name;
SELECT c.oid::regclass AS object_name, pg_get_userbyid(c.relowner) AS owner_name, coalesce(array_to_string(c.relacl,','),'') AS grants, obj_description(c.oid,'pg_class') AS comment FROM pg_class c WHERE c.oid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass,'public.dbf_sendtopartner'::regclass,'public.dbf_dbf_id_seq'::regclass,'public.dbf_dbfchunkedupload_id_seq'::regclass,'public.dbf_sendtopartner_id_seq'::regclass) ORDER BY 1;
SELECT table_name, column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('dbf_dbf','dbf_dbfchunkedupload','dbf_sendtopartner') ORDER BY 1,ordinal_position;
SELECT conrelid::regclass AS table_name, conname, contype, pg_get_constraintdef(oid) AS definition, convalidated FROM pg_constraint WHERE conrelid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass,'public.dbf_sendtopartner'::regclass) ORDER BY 1,2;
SELECT indrelid::regclass AS table_name, indexrelid::regclass AS index_name, pg_get_indexdef(indexrelid) AS definition FROM pg_index WHERE indrelid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass,'public.dbf_sendtopartner'::regclass) ORDER BY 1,2;
SELECT sequence_name, last_value, is_called FROM (SELECT 'dbf_dbf_id_seq' sequence_name,last_value,is_called FROM public.dbf_dbf_id_seq UNION ALL SELECT 'dbf_dbfchunkedupload_id_seq',last_value,is_called FROM public.dbf_dbfchunkedupload_id_seq UNION ALL SELECT 'dbf_sendtopartner_id_seq',last_value,is_called FROM public.dbf_sendtopartner_id_seq) q ORDER BY 1;
SELECT 'dbf_dbf.uploaded_at' AS evidence, min(uploaded_at)::date AS min_date, max(uploaded_at)::date AS max_date FROM public.dbf_dbf UNION ALL SELECT 'dbf_dbf.export_date',min(export_date),max(export_date) FROM public.dbf_dbf UNION ALL SELECT 'dbf_dbfchunkedupload.created_on',min(created_on)::date,max(created_on)::date FROM public.dbf_dbfchunkedupload UNION ALL SELECT 'dbf_dbfchunkedupload.completed_on',min(completed_on)::date,max(completed_on)::date FROM public.dbf_dbfchunkedupload;
SELECT min(notification_year) AS notification_year_min, max(notification_year) AS notification_year_max, count(*) FILTER (WHERE notification_year < 1900 OR notification_year > 2100) AS invalid_or_extreme_years FROM public.dbf_dbf;
SELECT 'dbf_sendtopartner has no date columns' AS date_evidence;
SELECT conrelid::regclass,conname,confrelid::regclass,pg_get_constraintdef(oid) FROM pg_constraint WHERE contype='f' AND conrelid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass,'public.dbf_sendtopartner'::regclass);
ROLLBACK;
