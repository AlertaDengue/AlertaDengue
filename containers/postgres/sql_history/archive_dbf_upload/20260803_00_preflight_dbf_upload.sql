\set ON_ERROR_STOP on
\pset pager off
SET statement_timeout = '60s';
SET lock_timeout = '5s';
SET default_transaction_read_only = on;
BEGIN;

SELECT current_database() AS database_name,
       (
         SELECT oid
         FROM pg_catalog.pg_database
         WHERE datname = current_database()
       ) AS database_oid,
       current_setting('server_version') AS server_version,
       current_setting('server_version_num') AS server_version_num,
       pg_is_in_recovery() AS is_in_recovery,
       current_user AS execution_role,
       has_database_privilege(current_user, current_database(), 'CONNECT') AS can_connect;

DO $$
DECLARE
  target text;
BEGIN
  IF current_database() <> 'dengue' THEN
    RAISE EXCEPTION 'refusing DBF archive preflight outside database dengue';
  END IF;
  IF pg_is_in_recovery() THEN RAISE EXCEPTION 'database is in recovery; primary is required'; END IF;
  IF NOT has_database_privilege(current_user, current_database(), 'CONNECT') THEN RAISE EXCEPTION 'execution role lacks CONNECT'; END IF;
  FOREACH target IN ARRAY ARRAY[
    'public.dbf_dbf', 'public.dbf_dbfchunkedupload',
    'public.dbf_dbf_id_seq', 'public.dbf_dbfchunkedupload_id_seq'
  ] LOOP
    IF to_regclass(target) IS NULL THEN
      RAISE EXCEPTION 'required target is absent: %', target;
    END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'archive_dbf_upload') THEN
    RAISE EXCEPTION 'archive_dbf_upload already exists; unexpected resume state';
  END IF;
  -- Intentionally do not use the broad archive-cleanup protected-object list:
  -- this script archives only legacy DBF upload metadata.
  IF to_regclass('public.auth_user') IS NULL
     OR to_regclass('ingestion.run') IS NULL
     OR to_regclass('ingestion.sinan_stage') IS NULL THEN
    RAISE EXCEPTION 'protected active object is absent';
  END IF;
END $$;

SELECT c.oid::regclass AS object_name,
       CASE c.relkind WHEN 'r' THEN 'table' WHEN 'S' THEN 'sequence' ELSE c.relkind::text END AS relation_type,
       pg_get_userbyid(c.relowner) AS owner_name,
       (xpath('/row/count/text()', query_to_xml(format('SELECT count(*) AS count FROM %I.%I',n.nspname,c.relname),false,true,'')))[1]::text AS exact_rows,
       pg_relation_size(c.oid) AS table_bytes, pg_indexes_size(c.oid) AS index_bytes,
       pg_total_relation_size(c.oid)-pg_relation_size(c.oid)-pg_indexes_size(c.oid) AS toast_and_other_bytes,
       pg_total_relation_size(c.oid) AS total_bytes
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.oid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass)
ORDER BY 1;

SELECT format('%I.%I',n.nspname,c.relname) AS table_name, a.attnum, a.attname,
       pg_catalog.format_type(a.atttypid,a.atttypmod) AS data_type,
       a.attnotnull, pg_get_expr(ad.adbin,ad.adrelid) AS default_expression,
       col_description(a.attrelid,a.attnum) AS column_comment
FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
LEFT JOIN pg_attrdef ad ON ad.adrelid=a.attrelid AND ad.adnum=a.attnum
WHERE c.oid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass) AND a.attnum>0 AND NOT a.attisdropped
ORDER BY 1,2;

SELECT c.oid::regclass AS object_name, c.relkind,
       pg_get_userbyid(c.relowner) AS owner_name,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
       pg_total_relation_size(c.oid) AS total_size_bytes,
       CASE WHEN c.relkind = 'r' THEN c.reltuples::bigint ELSE NULL END AS estimated_rows
FROM pg_class c
WHERE c.oid IN (
  'public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass,
  'public.dbf_dbf_id_seq'::regclass, 'public.dbf_dbfchunkedupload_id_seq'::regclass
)
ORDER BY c.oid::regclass::text;

SELECT c.oid::regclass AS object_name, i.relname AS index_name,
       pg_get_indexdef(i.oid) AS index_definition
FROM pg_index x
JOIN pg_class c ON c.oid = x.indrelid
JOIN pg_class i ON i.oid = x.indexrelid
WHERE c.oid IN ('public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass)
ORDER BY 1, 2;

SELECT con.conrelid::regclass AS table_name, con.conname,
       pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con
WHERE con.conrelid IN ('public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass)
   OR con.confrelid IN ('public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass)
ORDER BY 1, 2;

SELECT tgrelid::regclass AS table_name, tgname, pg_get_triggerdef(oid) AS definition
FROM pg_trigger
WHERE tgrelid IN ('public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass)
  AND NOT tgisinternal ORDER BY 1, 2;

SELECT format('%I.%I',schemaname,tablename) AS table_name, rulename, definition
FROM pg_rules WHERE schemaname='public' AND tablename IN ('dbf_dbf','dbf_dbfchunkedupload');

SELECT con.conrelid::regclass AS source_table, con.conname, con.confrelid::regclass AS referenced_table,
       pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con
WHERE con.contype='f' AND con.conrelid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass)
ORDER BY 1,2;

DO $dbf_fk_validation$
DECLARE
    source_schema text := 'public';
    expected_fk_count constant integer := 2;
    actual_fk_count integer;
    matched_fk_count integer;
BEGIN
    SELECT count(*) INTO actual_fk_count
    FROM pg_catalog.pg_constraint AS con
    WHERE con.contype = 'f'
      AND con.conrelid IN (
          to_regclass(format('%I.%I', source_schema, 'dbf_dbf')),
          to_regclass(format('%I.%I', source_schema, 'dbf_dbfchunkedupload'))
      );
    IF actual_fk_count <> expected_fk_count THEN
        RAISE EXCEPTION 'Expected exactly % outbound FKs from %.dbf_dbf and %.dbf_dbfchunkedupload, found %', expected_fk_count, source_schema, source_schema, actual_fk_count;
    END IF;
    WITH expected(table_name, constraint_name, source_column) AS (
        VALUES
            ('dbf_dbf', 'dbf_dbf_uploaded_by_id_ad662eb4_fk_auth_user_id', 'uploaded_by_id'),
            ('dbf_dbfchunkedupload', 'dbf_dbfchunkedupload_user_id_c7cc2beb_fk_auth_user_id', 'user_id')
    )
    SELECT count(*) INTO matched_fk_count
    FROM expected AS exp
    JOIN pg_catalog.pg_constraint AS con
      ON con.contype = 'f'
     AND con.conname = exp.constraint_name
     AND con.conrelid = to_regclass(format('%I.%I', source_schema, exp.table_name))
     AND con.confrelid = 'public.auth_user'::regclass
     AND pg_catalog.array_length(con.conkey, 1) = 1
     AND pg_catalog.array_length(con.confkey, 1) = 1
    JOIN pg_catalog.pg_attribute AS source_attribute
      ON source_attribute.attrelid = con.conrelid AND source_attribute.attnum = con.conkey[1]
     AND NOT source_attribute.attisdropped
    JOIN pg_catalog.pg_attribute AS referenced_attribute
      ON referenced_attribute.attrelid = con.confrelid AND referenced_attribute.attnum = con.confkey[1]
     AND NOT referenced_attribute.attisdropped
    WHERE source_attribute.attname = exp.source_column
      AND referenced_attribute.attname = 'id'
      AND con.confmatchtype = 's' AND con.confupdtype = 'a' AND con.confdeltype = 'a'
      AND con.condeferrable AND con.condeferred AND con.convalidated;
    IF matched_fk_count <> expected_fk_count THEN
        RAISE EXCEPTION 'Reviewed DBF outbound FK catalog structure does not match in schema %: expected %, matched %', source_schema, expected_fk_count, matched_fk_count;
    END IF;
END
$dbf_fk_validation$;

SELECT d.classid::regclass AS dependency_class, d.objid, d.refobjid, d.deptype,
       d.objsubid, d.refobjsubid
FROM pg_depend d
WHERE d.refobjid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass,
                     'public.dbf_dbf_id_seq'::regclass,'public.dbf_dbfchunkedupload_id_seq'::regclass)
ORDER BY 1,2,3;

SELECT c.oid::regclass AS object_name, COALESCE(array_to_string(c.relacl, ','), '') AS grants
FROM pg_class c
WHERE c.oid IN ('public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass,
                'public.dbf_dbf_id_seq'::regclass, 'public.dbf_dbfchunkedupload_id_seq'::regclass)
ORDER BY 1;

SELECT seq.relname AS sequence_name, tbl.oid::regclass AS owned_by,
       pg_get_serial_sequence(tbl.oid::regclass::text, cols.column_name) AS serial_sequence
FROM pg_class seq
JOIN pg_depend dep ON dep.objid = seq.oid AND dep.deptype = 'a'
JOIN pg_class tbl ON tbl.oid = dep.refobjid
JOIN LATERAL (SELECT CASE seq.relname
  WHEN 'dbf_dbf_id_seq' THEN 'id'
  WHEN 'dbf_dbfchunkedupload_id_seq' THEN 'id' END AS column_name) cols ON true
WHERE seq.oid IN ('public.dbf_dbf_id_seq'::regclass, 'public.dbf_dbfchunkedupload_id_seq'::regclass);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint con
    WHERE con.contype = 'f'
      AND con.confrelid IN ('public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass)
      AND con.conrelid NOT IN ('public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass)
  ) THEN RAISE EXCEPTION 'active foreign key points to a DBF target'; END IF;
  IF EXISTS (
    SELECT 1 FROM pg_depend d
    JOIN pg_rewrite r ON r.oid = d.objid
    WHERE d.refobjid IN ('public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass)
  ) THEN RAISE EXCEPTION 'view or rule depends on a DBF target'; END IF;
END $$;

SELECT 'historical_period_validation' AS check_name,
       'NOT_INDEPENDENTLY_VERIFIABLE' AS status,
       'DBF tables contain no epidemiological-week field; operator must confirm cutoff 202552 before archive' AS detail;
ROLLBACK;
