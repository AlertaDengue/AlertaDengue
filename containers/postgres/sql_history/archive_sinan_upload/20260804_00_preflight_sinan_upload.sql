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

BEGIN;
SET TRANSACTION READ ONLY;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
SET LOCAL idle_in_transaction_session_timeout = '60s';

SELECT current_database() AS database_name,
       (SELECT oid FROM pg_catalog.pg_database WHERE datname = current_database()) AS database_oid,
       current_setting('server_version') AS server_version,
       pg_is_in_recovery() AS is_in_recovery,
       current_user AS execution_role,
       has_database_privilege(current_user, current_database(), 'CONNECT') AS can_connect,
       has_database_privilege(current_user, current_database(), 'CREATE') AS can_create_schema;

DO $guard$
DECLARE
    expected_tables constant text[] := ARRAY[
        'upload_sinanchunkedupload', 'upload_sinanupload',
        'upload_sinanuploadlogstatus'];
    expected_sequences constant text[] := ARRAY[
        'upload_sinanchunkedupload_id_seq', 'upload_sinanupload_id_seq',
        'upload_sinanuploadlogstatus_id_seq'];
    actual_tables text[];
    actual_sequences text[];
BEGIN
    IF pg_is_in_recovery() THEN RAISE EXCEPTION 'database is in recovery'; END IF;
    IF NOT has_database_privilege(current_user, current_database(), 'CONNECT')
       OR NOT has_database_privilege(current_user, current_database(), 'CREATE') THEN
        RAISE EXCEPTION 'execution role lacks required database privileges';
    END IF;
    SELECT coalesce(array_agg(c.relname ORDER BY c.relname), ARRAY[]::text[])
      INTO actual_tables
      FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public' AND c.relkind = 'r'
       AND c.relname = ANY(expected_tables);
    IF actual_tables IS DISTINCT FROM expected_tables THEN
        RAISE EXCEPTION 'source table inventory is not exact: %', actual_tables;
    END IF;
    SELECT coalesce(array_agg(c.relname ORDER BY c.relname), ARRAY[]::text[])
      INTO actual_sequences
      FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public' AND c.relkind = 'S'
       AND c.relname = ANY(expected_sequences);
    IF actual_sequences IS DISTINCT FROM expected_sequences THEN
        RAISE EXCEPTION 'source sequence inventory is not exact: %', actual_sequences;
    END IF;
    IF to_regclass('ingestion.run') IS NULL
       OR to_regclass('ingestion.sinan_stage') IS NULL
       OR to_regclass('public.auth_user') IS NULL THEN
        RAISE EXCEPTION 'protected active object is absent';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_namespace n JOIN pg_class c ON c.relnamespace = n.oid
        WHERE n.nspname = 'archive_sinan_upload'
          AND c.relkind IN ('r','S','i','v','m','f','p')) THEN
        RAISE EXCEPTION 'archive_sinan_upload exists and is not empty';
    END IF;
END
$guard$;

SELECT c.oid::regclass AS object_name,
       (xpath('/row/count/text()', query_to_xml(
           format('SELECT count(*) AS count FROM %I.%I', n.nspname, c.relname),
           false, true, '')))[1]::text::bigint AS exact_rows,
       pg_relation_size(c.oid) AS table_bytes,
       pg_indexes_size(c.oid) AS index_bytes,
       pg_total_relation_size(c.oid) AS total_bytes
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public'
   AND c.relname IN ('upload_sinanchunkedupload','upload_sinanupload',
                     'upload_sinanuploadlogstatus')
 ORDER BY 1;

SELECT format('%I.%I', n.nspname, c.relname) AS table_name,
       a.attnum, a.attname, format_type(a.atttypid, a.atttypmod) AS data_type,
       a.attnotnull, pg_get_expr(ad.adbin, ad.adrelid) AS default_expression
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  LEFT JOIN pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
 WHERE n.nspname = 'public'
   AND c.relname IN ('upload_sinanchunkedupload','upload_sinanupload',
                     'upload_sinanuploadlogstatus')
   AND a.attnum > 0 AND NOT a.attisdropped
 ORDER BY 1, 2;

SELECT con.conrelid::regclass AS table_name, con.conname, con.contype,
       con.conkey, con.confrelid::regclass AS referenced_table, con.confkey,
       con.confmatchtype, con.confupdtype, con.confdeltype,
       con.condeferrable, con.condeferred, con.convalidated,
       pg_get_constraintdef(con.oid) AS definition
  FROM pg_constraint con
 WHERE con.conrelid IN ('public.upload_sinanchunkedupload'::regclass,
                        'public.upload_sinanupload'::regclass,
                        'public.upload_sinanuploadlogstatus'::regclass)
    OR con.confrelid IN ('public.upload_sinanchunkedupload'::regclass,
                         'public.upload_sinanupload'::regclass,
                         'public.upload_sinanuploadlogstatus'::regclass)
 ORDER BY 1, 2;

SELECT x.indrelid::regclass AS table_name, i.relname AS index_name,
       x.indisprimary, x.indisunique, pg_get_indexdef(i.oid) AS definition
  FROM pg_index x JOIN pg_class i ON i.oid = x.indexrelid
 WHERE x.indrelid IN ('public.upload_sinanchunkedupload'::regclass,
                      'public.upload_sinanupload'::regclass,
                      'public.upload_sinanuploadlogstatus'::regclass)
 ORDER BY 1, 2;

SELECT tgrelid::regclass AS table_name, tgname, pg_get_triggerdef(oid) AS definition
  FROM pg_trigger
 WHERE tgrelid IN ('public.upload_sinanchunkedupload'::regclass,
                   'public.upload_sinanupload'::regclass,
                   'public.upload_sinanuploadlogstatus'::regclass)
   AND NOT tgisinternal;

SELECT schemaname, tablename, rulename, definition
  FROM pg_rules
 WHERE schemaname = 'public'
   AND tablename IN ('upload_sinanchunkedupload','upload_sinanupload',
                     'upload_sinanuploadlogstatus');

DO $fk$
DECLARE matched integer;
BEGIN
    SELECT count(*) INTO matched
      FROM pg_constraint con
      JOIN pg_attribute sa ON sa.attrelid = con.conrelid AND sa.attnum = con.conkey[1]
      JOIN pg_attribute ra ON ra.attrelid = con.confrelid AND ra.attnum = con.confkey[1]
     WHERE con.contype = 'f'
       AND con.conrelid IN ('public.upload_sinanchunkedupload'::regclass,
                            'public.upload_sinanupload'::regclass,
                            'public.upload_sinanuploadlogstatus'::regclass)
       AND ((con.conname = 'upload_sinanchunkedupload_user_id_d183233a_fk_auth_user_id'
             AND con.conrelid = 'public.upload_sinanchunkedupload'::regclass
             AND con.confrelid = 'public.auth_user'::regclass
             AND sa.attname = 'user_id' AND ra.attname = 'id')
         OR (con.conname = 'upload_sinanupload_upload_id_97f6c7e1_fk_upload_si'
             AND con.conrelid = 'public.upload_sinanupload'::regclass
             AND con.confrelid = 'public.upload_sinanchunkedupload'::regclass
             AND sa.attname = 'upload_id' AND ra.attname = 'id')
         OR (con.conname = 'upload_sinanupload_status_id_998c10bf_fk_upload_si'
             AND con.conrelid = 'public.upload_sinanupload'::regclass
             AND con.confrelid = 'public.upload_sinanuploadlogstatus'::regclass
             AND sa.attname = 'status_id' AND ra.attname = 'id'))
       AND con.confmatchtype = 's' AND con.confupdtype = 'a' AND con.confdeltype = 'a'
       AND con.condeferrable AND con.condeferred AND con.convalidated;
    IF matched <> 3 THEN RAISE EXCEPTION 'reviewed FK structure did not match: %', matched; END IF;
    IF (SELECT count(*) FROM pg_constraint
        WHERE contype = 'f' AND conrelid IN (
          'public.upload_sinanchunkedupload'::regclass,'public.upload_sinanupload'::regclass,
          'public.upload_sinanuploadlogstatus'::regclass)) <> 3 THEN
        RAISE EXCEPTION 'unexpected outbound FK exists';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint
        WHERE contype = 'f' AND confrelid IN (
          'public.upload_sinanchunkedupload'::regclass,'public.upload_sinanupload'::regclass,
          'public.upload_sinanuploadlogstatus'::regclass)
          AND conrelid NOT IN ('public.upload_sinanchunkedupload'::regclass,
                               'public.upload_sinanupload'::regclass,
                               'public.upload_sinanuploadlogstatus'::regclass)) THEN
        RAISE EXCEPTION 'unreviewed inbound FK exists';
    END IF;
END
$fk$;

SELECT 'upload_sinanchunkedupload_id_seq' AS sequence_name,
       last_value, is_called
  FROM public.upload_sinanchunkedupload_id_seq
UNION ALL
SELECT 'upload_sinanupload_id_seq', last_value, is_called
  FROM public.upload_sinanupload_id_seq
UNION ALL
SELECT 'upload_sinanuploadlogstatus_id_seq', last_value, is_called
  FROM public.upload_sinanuploadlogstatus_id_seq
ORDER BY 1;

SELECT seq.oid::regclass AS sequence_name, tbl.oid::regclass AS owned_table,
       dep.refobjsubid AS owned_column,
       pg_get_serial_sequence(tbl.oid::regclass::text, 'id') AS serial_sequence
  FROM pg_class seq
  JOIN pg_depend dep ON dep.objid = seq.oid AND dep.deptype = 'a'
  JOIN pg_class tbl ON tbl.oid = dep.refobjid
 WHERE seq.oid IN ('public.upload_sinanchunkedupload_id_seq'::regclass,
                   'public.upload_sinanupload_id_seq'::regclass,
                   'public.upload_sinanuploadlogstatus_id_seq'::regclass)
 ORDER BY 1;

SELECT c.oid::regclass AS object_name, pg_get_userbyid(c.relowner) AS owner,
       COALESCE(array_to_string(c.relacl, ','), '') AS grants
  FROM pg_class c
 WHERE c.oid IN ('public.upload_sinanchunkedupload'::regclass,
                 'public.upload_sinanupload'::regclass,
                 'public.upload_sinanuploadlogstatus'::regclass,
                 'public.upload_sinanchunkedupload_id_seq'::regclass,
                 'public.upload_sinanupload_id_seq'::regclass,
                 'public.upload_sinanuploadlogstatus_id_seq'::regclass)
 ORDER BY 1;

SELECT 'historical_period_validation' AS check_name,
       'NOT_INDEPENDENTLY_VERIFIABLE' AS status,
       'The tables have timestamps but no authoritative epiweek; operator must confirm 202552.' AS detail;

SELECT 'file_prefix' AS profile, COALESCE(NULLIF(split_part(file, '/', 1), ''), '[empty]') AS safe_prefix,
       count(*) AS rows FROM public.upload_sinanchunkedupload GROUP BY 2
UNION ALL
SELECT 'log_prefix', COALESCE(NULLIF(split_part(log_file, '/', 1), ''), '[empty]'), count(*)
  FROM public.upload_sinanuploadlogstatus GROUP BY 2
ORDER BY 1, 2;

SELECT min(created_on) AS chunk_created_min, max(created_on) AS chunk_created_max,
       min(uploaded_at) AS upload_min, max(uploaded_at) AS upload_max
  FROM public.upload_sinanchunkedupload c
  FULL JOIN public.upload_sinanupload u ON false;

ROLLBACK;
