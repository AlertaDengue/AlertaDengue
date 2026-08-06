\set ON_ERROR_STOP on
\pset pager off
\if :{?expected_database_name}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_database_name is required'; END $$;
\endif
SELECT current_database() = :'expected_database_name' AS database_name_matches \gset
\if :database_name_matches
\else
  DO $$ BEGIN RAISE EXCEPTION 'connected database does not match expected_database_name'; END $$;
\endif
BEGIN;
SET TRANSACTION READ ONLY;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

SELECT current_database() AS database_name,
       (SELECT oid FROM pg_database WHERE datname = current_database()) AS database_oid,
       current_setting('server_version') AS server_version,
       pg_is_in_recovery() AS in_recovery,
       current_user AS execution_role;

DO $guard$
DECLARE
  expected_tables constant text[] := ARRAY[
    'DengueConfirmados_2013', 'Dengue_2010', 'Dengue_2011',
    'Dengue_2012', 'Dengue_2013'
  ];
  actual_tables text[];
BEGIN
  IF current_database() <> 'infodengue' THEN
    RAISE EXCEPTION 'this workflow requires the infodengue database';
  END IF;
  IF pg_is_in_recovery() THEN
    RAISE EXCEPTION 'database is in recovery';
  END IF;
  SELECT coalesce(array_agg(c.relname ORDER BY c.relname), ARRAY[]::text[])
    INTO actual_tables
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'public'
     AND c.relkind IN ('r', 'p')
     AND c.relname = ANY(expected_tables);
  IF actual_tables IS DISTINCT FROM expected_tables THEN
    RAISE EXCEPTION 'candidate table inventory mismatch: %', actual_tables;
  END IF;
END $guard$;

SELECT 'public."Dengue_2010"' AS table_name, count(*) AS exact_rows,
       pg_total_relation_size('public."Dengue_2010"'::regclass) AS total_bytes
  FROM public."Dengue_2010"
UNION ALL
SELECT 'public."Dengue_2011"', count(*),
       pg_total_relation_size('public."Dengue_2011"'::regclass)
  FROM public."Dengue_2011"
UNION ALL
SELECT 'public."Dengue_2012"', count(*),
       pg_total_relation_size('public."Dengue_2012"'::regclass)
  FROM public."Dengue_2012"
UNION ALL
SELECT 'public."Dengue_2013"', count(*),
       pg_total_relation_size('public."Dengue_2013"'::regclass)
  FROM public."Dengue_2013"
UNION ALL
SELECT 'public."DengueConfirmados_2013"', count(*),
       pg_total_relation_size('public."DengueConfirmados_2013"'::regclass)
  FROM public."DengueConfirmados_2013"
ORDER BY table_name;

DO $empty$
BEGIN
  IF (SELECT count(*) FROM public."Dengue_2010") <> 0
     OR (SELECT count(*) FROM public."Dengue_2011") <> 0
     OR (SELECT count(*) FROM public."Dengue_2012") <> 0
     OR (SELECT count(*) FROM public."Dengue_2013") <> 0
     OR (SELECT count(*) FROM public."DengueConfirmados_2013") <> 0
  THEN
    RAISE EXCEPTION 'one or more candidate tables contains rows';
  END IF;
END $empty$;

SELECT table_name, column_name, ordinal_position, data_type, is_nullable,
       column_default
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND table_name IN (
     'Dengue_2010', 'Dengue_2011', 'Dengue_2012',
     'Dengue_2013', 'DengueConfirmados_2013'
   )
 ORDER BY table_name, ordinal_position;

SELECT conrelid::regclass AS table_name, conname, contype,
       pg_get_constraintdef(oid) AS definition, convalidated
  FROM pg_constraint
 WHERE conrelid IN (
   'public."Dengue_2010"'::regclass,
   'public."Dengue_2011"'::regclass,
   'public."Dengue_2012"'::regclass,
   'public."Dengue_2013"'::regclass,
   'public."DengueConfirmados_2013"'::regclass
 )
 ORDER BY 1, 2;

SELECT indrelid::regclass AS table_name, indexrelid::regclass AS index_name,
       pg_get_indexdef(indexrelid) AS definition
  FROM pg_index
 WHERE indrelid IN (
   'public."Dengue_2010"'::regclass,
   'public."Dengue_2011"'::regclass,
   'public."Dengue_2012"'::regclass,
   'public."Dengue_2013"'::regclass,
   'public."DengueConfirmados_2013"'::regclass
 )
 ORDER BY 1, 2;

SELECT tgrelid::regclass AS table_name, tgname,
       pg_get_triggerdef(oid) AS definition
  FROM pg_trigger
 WHERE tgrelid IN (
   'public."Dengue_2010"'::regclass,
   'public."Dengue_2011"'::regclass,
   'public."Dengue_2012"'::regclass,
   'public."Dengue_2013"'::regclass,
   'public."DengueConfirmados_2013"'::regclass
 )
   AND NOT tgisinternal
 ORDER BY 1, 2;

SELECT schemaname, tablename, rulename, definition
  FROM pg_rules
 WHERE schemaname = 'public'
   AND tablename IN (
     'Dengue_2010', 'Dengue_2011', 'Dengue_2012',
     'Dengue_2013', 'DengueConfirmados_2013'
   )
 ORDER BY 1, 2, 3;

SELECT d.classid::regclass AS dependency_catalog,
       d.objid::text AS dependent_object,
       d.refobjid::regclass AS referenced_object,
       d.deptype
  FROM pg_depend d
 WHERE d.refobjid IN (
   'public."Dengue_2010"'::regclass,
   'public."Dengue_2011"'::regclass,
   'public."Dengue_2012"'::regclass,
   'public."Dengue_2013"'::regclass,
   'public."DengueConfirmados_2013"'::regclass
 )
 ORDER BY 1, 2, 3, 4;

DO $dependencies$
BEGIN
  IF EXISTS (
    SELECT 1
      FROM pg_constraint con
     WHERE con.contype = 'f'
       AND con.confrelid IN (
         'public."Dengue_2010"'::regclass,
         'public."Dengue_2011"'::regclass,
         'public."Dengue_2012"'::regclass,
         'public."Dengue_2013"'::regclass,
         'public."DengueConfirmados_2013"'::regclass
       )
       AND con.conrelid NOT IN (
         'public."Dengue_2010"'::regclass,
         'public."Dengue_2011"'::regclass,
         'public."Dengue_2012"'::regclass,
         'public."Dengue_2013"'::regclass,
         'public."DengueConfirmados_2013"'::regclass
       )
  ) THEN
    RAISE EXCEPTION 'unexpected inbound foreign-key dependency exists';
  END IF;
  IF EXISTS (
    SELECT 1
      FROM pg_depend d
      JOIN pg_rewrite r ON r.oid = d.objid
     WHERE d.classid = 'pg_rewrite'::regclass
       AND d.refobjid IN (
       'public."Dengue_2010"'::regclass,
       'public."Dengue_2011"'::regclass,
       'public."Dengue_2012"'::regclass,
       'public."Dengue_2013"'::regclass,
       'public."DengueConfirmados_2013"'::regclass
     )
  ) THEN
    RAISE EXCEPTION 'unexpected view or rule dependency exists';
  END IF;
END $dependencies$;

ROLLBACK;
