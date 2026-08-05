\set ON_ERROR_STOP on
\pset pager off
SET statement_timeout = '5min';
SET lock_timeout = '5s';
BEGIN;
SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.archive_dbf_upload'));
DO $$
BEGIN
  IF current_database() <> 'dengue' THEN RAISE EXCEPTION 'wrong database'; END IF;
  IF to_regclass('public.dbf_dbf') IS NULL OR to_regclass('public.dbf_dbfchunkedupload') IS NULL
     OR to_regclass('public.dbf_dbf_id_seq') IS NULL OR to_regclass('public.dbf_dbfchunkedupload_id_seq') IS NULL
  THEN RAISE EXCEPTION 'DBF target inventory is incomplete'; END IF;
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'archive_dbf_upload')
  THEN RAISE EXCEPTION 'archive schema already exists'; END IF;
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE contype = 'f'
    AND confrelid IN ('public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass)
    AND conrelid NOT IN ('public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass))
  THEN RAISE EXCEPTION 'unexpected active dependency on DBF target'; END IF;
END $$;
DO $dbf_fk_validation$
DECLARE
    source_schema text := 'public';
    expected_fk_count constant integer := 2;
    actual_fk_count integer;
    matched_fk_count integer;
BEGIN
    SELECT count(*) INTO actual_fk_count FROM pg_catalog.pg_constraint AS con
    WHERE con.contype = 'f' AND con.conrelid IN (to_regclass(format('%I.%I', source_schema, 'dbf_dbf')), to_regclass(format('%I.%I', source_schema, 'dbf_dbfchunkedupload')));
    IF actual_fk_count <> expected_fk_count THEN RAISE EXCEPTION 'Expected exactly % outbound FKs, found %', expected_fk_count, actual_fk_count; END IF;
    WITH expected(table_name, constraint_name, source_column) AS (VALUES
      ('dbf_dbf','dbf_dbf_uploaded_by_id_ad662eb4_fk_auth_user_id','uploaded_by_id'),
      ('dbf_dbfchunkedupload','dbf_dbfchunkedupload_user_id_c7cc2beb_fk_auth_user_id','user_id'))
    SELECT count(*) INTO matched_fk_count FROM expected exp JOIN pg_catalog.pg_constraint con
      ON con.contype='f' AND con.conname=exp.constraint_name AND con.conrelid=to_regclass(format('%I.%I',source_schema,exp.table_name))
     AND con.confrelid='public.auth_user'::regclass AND pg_catalog.array_length(con.conkey,1)=1 AND pg_catalog.array_length(con.confkey,1)=1
    JOIN pg_catalog.pg_attribute sa ON sa.attrelid=con.conrelid AND sa.attnum=con.conkey[1] AND NOT sa.attisdropped
    JOIN pg_catalog.pg_attribute ra ON ra.attrelid=con.confrelid AND ra.attnum=con.confkey[1] AND NOT ra.attisdropped
    WHERE sa.attname=exp.source_column AND ra.attname='id' AND con.confmatchtype='s' AND con.confupdtype='a' AND con.confdeltype='a' AND con.condeferrable AND con.condeferred AND con.convalidated;
    IF matched_fk_count <> expected_fk_count THEN RAISE EXCEPTION 'Reviewed DBF outbound FK catalog structure does not match in schema %', source_schema; END IF;
END
$dbf_fk_validation$;
CREATE TEMP TABLE dbf_archive_before AS
SELECT c.oid::regclass::text AS object_name,
       (xpath('/row/count/text()', query_to_xml(format('SELECT count(*) AS count FROM %I.%I',n.nspname,c.relname),false,true,'')))[1]::text::bigint AS exact_rows,
       pg_total_relation_size(c.oid) AS total_size
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.oid IN ('public.dbf_dbf'::regclass, 'public.dbf_dbfchunkedupload'::regclass);
CREATE TEMP TABLE dbf_sequence_state_before ON COMMIT DROP AS
SELECT 'dbf_dbf_id_seq'::text AS sequence_name, last_value, is_called
FROM public.dbf_dbf_id_seq
UNION ALL
SELECT 'dbf_dbfchunkedupload_id_seq'::text, last_value, is_called
FROM public.dbf_dbfchunkedupload_id_seq;
DO $$
BEGIN
  IF (SELECT count(*) FROM dbf_sequence_state_before) <> 2
     OR EXISTS (SELECT 1 FROM dbf_sequence_state_before
               WHERE sequence_name NOT IN ('dbf_dbf_id_seq','dbf_dbfchunkedupload_id_seq'))
  THEN RAISE EXCEPTION 'sequence snapshot before archive is not exact'; END IF;
END $$;
CREATE TEMP TABLE dbf_metadata_before AS
SELECT 'column' AS kind, c.relname||':'||a.attnum::text AS object_name,
       a.attname||':'||format_type(a.atttypid,a.atttypmod)||':'||a.attnotnull::text||':'||COALESCE(pg_get_expr(ad.adbin,ad.adrelid),'') AS definition
FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid LEFT JOIN pg_attrdef ad ON ad.adrelid=a.attrelid AND ad.adnum=a.attnum
WHERE c.oid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass) AND a.attnum>0 AND NOT a.attisdropped
UNION ALL SELECT 'constraint',c.relname||':'||con.conname,pg_get_constraintdef(con.oid) FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
WHERE con.conrelid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass)
UNION ALL SELECT 'index',i.relname,replace(pg_get_indexdef(i.oid),'public.','archive_dbf_upload.') FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid
WHERE x.indrelid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass)
UNION ALL SELECT 'acl',c.relname,COALESCE(array_to_string(c.relacl,','),'')||':'||COALESCE(obj_description(c.oid,'pg_class'),'')||':'||pg_get_userbyid(c.relowner)
FROM pg_class c WHERE c.oid IN ('public.dbf_dbf'::regclass,'public.dbf_dbfchunkedupload'::regclass);
CREATE SCHEMA archive_dbf_upload;
ALTER SCHEMA archive_dbf_upload OWNER TO CURRENT_USER;
ALTER TABLE public.dbf_dbf SET SCHEMA archive_dbf_upload;
ALTER TABLE public.dbf_dbfchunkedupload SET SCHEMA archive_dbf_upload;
DO $dbf_fk_validation$
DECLARE
    source_schema text := 'archive_dbf_upload';
    expected_fk_count constant integer := 2;
    actual_fk_count integer;
    matched_fk_count integer;
BEGIN
    SELECT count(*) INTO actual_fk_count FROM pg_catalog.pg_constraint AS con
    WHERE con.contype = 'f' AND con.conrelid IN (to_regclass(format('%I.%I', source_schema, 'dbf_dbf')), to_regclass(format('%I.%I', source_schema, 'dbf_dbfchunkedupload')));
    IF actual_fk_count <> expected_fk_count THEN RAISE EXCEPTION 'Expected exactly % outbound FKs, found %', expected_fk_count, actual_fk_count; END IF;
    WITH expected(table_name, constraint_name, source_column) AS (VALUES
      ('dbf_dbf','dbf_dbf_uploaded_by_id_ad662eb4_fk_auth_user_id','uploaded_by_id'),
      ('dbf_dbfchunkedupload','dbf_dbfchunkedupload_user_id_c7cc2beb_fk_auth_user_id','user_id'))
    SELECT count(*) INTO matched_fk_count FROM expected exp JOIN pg_catalog.pg_constraint con
      ON con.contype='f' AND con.conname=exp.constraint_name AND con.conrelid=to_regclass(format('%I.%I',source_schema,exp.table_name))
     AND con.confrelid='public.auth_user'::regclass AND pg_catalog.array_length(con.conkey,1)=1 AND pg_catalog.array_length(con.confkey,1)=1
    JOIN pg_catalog.pg_attribute sa ON sa.attrelid=con.conrelid AND sa.attnum=con.conkey[1] AND NOT sa.attisdropped
    JOIN pg_catalog.pg_attribute ra ON ra.attrelid=con.confrelid AND ra.attnum=con.confkey[1] AND NOT ra.attisdropped
    WHERE sa.attname=exp.source_column AND ra.attname='id' AND con.confmatchtype='s' AND con.confupdtype='a' AND con.confdeltype='a' AND con.condeferrable AND con.condeferred AND con.convalidated;
    IF matched_fk_count <> expected_fk_count THEN RAISE EXCEPTION 'Reviewed DBF outbound FK catalog structure does not match in schema %', source_schema; END IF;
END
$dbf_fk_validation$;
DO $$
BEGIN
  IF to_regclass('public.dbf_dbf') IS NOT NULL OR to_regclass('public.dbf_dbfchunkedupload') IS NOT NULL
     OR to_regclass('public.dbf_dbf_id_seq') IS NOT NULL OR to_regclass('public.dbf_dbfchunkedupload_id_seq') IS NOT NULL
  THEN RAISE EXCEPTION 'source objects remain in public; refusing commit'; END IF;
  IF to_regclass('archive_dbf_upload.dbf_dbf') IS NULL OR to_regclass('archive_dbf_upload.dbf_dbfchunkedupload') IS NULL
     OR to_regclass('archive_dbf_upload.dbf_dbf_id_seq') IS NULL OR to_regclass('archive_dbf_upload.dbf_dbfchunkedupload_id_seq') IS NULL
  THEN RAISE EXCEPTION 'archived table/sequence inventory is incomplete'; END IF;
  IF (SELECT exact_rows FROM dbf_archive_before WHERE object_name='dbf_dbf') IS DISTINCT FROM
       (xpath('/row/count/text()', query_to_xml('SELECT count(*) AS count FROM archive_dbf_upload.dbf_dbf',false,true,'')))[1]::text::bigint
     OR (SELECT exact_rows FROM dbf_archive_before WHERE object_name='dbf_dbfchunkedupload') IS DISTINCT FROM
       (xpath('/row/count/text()', query_to_xml('SELECT count(*) AS count FROM archive_dbf_upload.dbf_dbfchunkedupload',false,true,'')))[1]::text::bigint
  THEN RAISE EXCEPTION 'row count changed during archive'; END IF;
  IF (SELECT count(*) FROM (
        SELECT 'dbf_dbf_id_seq'::text AS sequence_name, last_value, is_called
        FROM archive_dbf_upload.dbf_dbf_id_seq
        UNION ALL
        SELECT 'dbf_dbfchunkedupload_id_seq'::text, last_value, is_called
        FROM archive_dbf_upload.dbf_dbfchunkedupload_id_seq
      ) AS states) <> 2
  THEN RAISE EXCEPTION 'sequence snapshot after archive is not exact'; END IF;
  IF EXISTS (SELECT 1 FROM (
        SELECT 'dbf_dbf_id_seq'::text AS sequence_name, last_value, is_called
        FROM archive_dbf_upload.dbf_dbf_id_seq
        UNION ALL
        SELECT 'dbf_dbfchunkedupload_id_seq'::text, last_value, is_called
        FROM archive_dbf_upload.dbf_dbfchunkedupload_id_seq
      ) AS after_state
      FULL JOIN dbf_sequence_state_before before_state USING (sequence_name)
      WHERE after_state.sequence_name IS NULL OR before_state.sequence_name IS NULL
         OR after_state.last_value IS DISTINCT FROM before_state.last_value
         OR after_state.is_called IS DISTINCT FROM before_state.is_called)
  THEN RAISE EXCEPTION 'sequence value changed during archive'; END IF;
  IF EXISTS (SELECT 1 FROM pg_depend d JOIN pg_class s ON s.oid=d.objid JOIN pg_class t ON t.oid=d.refobjid
             WHERE d.deptype='a' AND s.oid IN ('archive_dbf_upload.dbf_dbf_id_seq'::regclass,'archive_dbf_upload.dbf_dbfchunkedupload_id_seq'::regclass)
             AND t.oid NOT IN ('archive_dbf_upload.dbf_dbf'::regclass,'archive_dbf_upload.dbf_dbfchunkedupload'::regclass))
  THEN RAISE EXCEPTION 'sequence ownership changed'; END IF;
  -- Intentionally do not use the broad archive-cleanup protected-object list:
  -- this script archives only legacy DBF upload metadata.
  IF to_regclass('public.auth_user') IS NULL
     OR to_regclass('ingestion.run') IS NULL
     OR to_regclass('ingestion.sinan_stage') IS NULL
  THEN RAISE EXCEPTION 'protected active object disappeared'; END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
             WHERE n.nspname='archive_dbf_upload'
               AND c.relkind IN ('r','S')
               AND c.relname NOT IN ('dbf_dbf','dbf_dbfchunkedupload','dbf_dbf_id_seq','dbf_dbfchunkedupload_id_seq'))
  THEN RAISE EXCEPTION 'unexpected archive object exists'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_depend d JOIN pg_class s ON s.oid=d.objid JOIN pg_class t ON t.oid=d.refobjid
    WHERE d.deptype='a' AND s.oid='archive_dbf_upload.dbf_dbf_id_seq'::regclass
      AND t.oid='archive_dbf_upload.dbf_dbf'::regclass AND d.refobjsubid=1)
  THEN RAISE EXCEPTION 'dbf_dbf_id_seq ownership was not preserved'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_depend d JOIN pg_class s ON s.oid=d.objid JOIN pg_class t ON t.oid=d.refobjid
    WHERE d.deptype='a' AND s.oid='archive_dbf_upload.dbf_dbfchunkedupload_id_seq'::regclass
      AND t.oid='archive_dbf_upload.dbf_dbfchunkedupload'::regclass AND d.refobjsubid=1)
  THEN RAISE EXCEPTION 'dbf_dbfchunkedupload_id_seq ownership was not preserved'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_attrdef d JOIN pg_class c ON c.oid=d.adrelid JOIN pg_namespace ns ON ns.oid=c.relnamespace
    WHERE ns.nspname='archive_dbf_upload' AND c.relname='dbf_dbf'
      AND pg_get_expr(d.adbin,d.adrelid) LIKE '%archive_dbf_upload.dbf_dbf_id_seq%')
  THEN RAISE EXCEPTION 'dbf_dbf default does not point to archived sequence'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_attrdef d JOIN pg_class c ON c.oid=d.adrelid JOIN pg_namespace ns ON ns.oid=c.relnamespace
    WHERE ns.nspname='archive_dbf_upload' AND c.relname='dbf_dbfchunkedupload'
      AND pg_get_expr(d.adbin,d.adrelid) LIKE '%archive_dbf_upload.dbf_dbfchunkedupload_id_seq%')
  THEN RAISE EXCEPTION 'chunked-upload default does not point to archived sequence'; END IF;
  -- Intentionally do not use the broad archive-cleanup protected-object list:
  -- this script archives only legacy DBF upload metadata.
  IF EXISTS (SELECT 1 FROM (VALUES
    ('public','auth_user'),('ingestion','run'),('ingestion','sinan_stage')) AS p(s,r)
    WHERE to_regclass(format('%I.%I',p.s,p.r)) IS NULL)
  THEN RAISE EXCEPTION 'protected active object missing'; END IF;
END $$;
SELECT 'archive_dbf_upload' AS archive_schema,
       c.oid::regclass AS object_name, c.reltuples::bigint AS estimated_rows,
       pg_total_relation_size(c.oid) AS total_size
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'archive_dbf_upload' AND c.relname IN
 ('dbf_dbf','dbf_dbfchunkedupload','dbf_dbf_id_seq','dbf_dbfchunkedupload_id_seq')
ORDER BY 2;
SELECT c.oid::regclass AS object_name,c.relkind,pg_get_userbyid(c.relowner) AS owner_name,
       pg_total_relation_size(c.oid) AS total_size,obj_description(c.oid,'pg_class') AS comment,
       COALESCE(array_to_string(c.relacl,','),'') AS grants
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='archive_dbf_upload' AND c.relname IN ('dbf_dbf','dbf_dbfchunkedupload','dbf_dbf_id_seq','dbf_dbfchunkedupload_id_seq')
ORDER BY 1;
SELECT con.conrelid::regclass,con.conname,pg_get_constraintdef(con.oid)
FROM pg_constraint con WHERE con.conrelid IN ('archive_dbf_upload.dbf_dbf'::regclass,'archive_dbf_upload.dbf_dbfchunkedupload'::regclass)
ORDER BY 1,2;
SELECT i.indexrelid::regclass,pg_get_indexdef(i.indexrelid)
FROM pg_index i WHERE i.indrelid IN ('archive_dbf_upload.dbf_dbf'::regclass,'archive_dbf_upload.dbf_dbfchunkedupload'::regclass);
SELECT tgrelid::regclass,tgname,pg_get_triggerdef(oid) FROM pg_trigger
WHERE tgrelid IN ('archive_dbf_upload.dbf_dbf'::regclass,'archive_dbf_upload.dbf_dbfchunkedupload'::regclass) AND NOT tgisinternal;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace ns ON ns.oid=c.relnamespace
             WHERE ns.nspname='archive_dbf_upload' AND c.relkind NOT IN ('r','S','i'))
  THEN RAISE EXCEPTION 'archive schema contains unexpected objects'; END IF;
END $$;
COMMIT;
