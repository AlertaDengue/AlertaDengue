\set ON_ERROR_STOP on
\pset pager off
\if :{?expected_database_name}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_database_name is required'; END $$;
\endif
\if :{?removal_approval}
\else
  DO $$ BEGIN RAISE EXCEPTION 'removal_approval is required'; END $$;
\endif
SELECT current_database() = :'expected_database_name' AS database_name_matches \gset
\if :database_name_matches
\else
  DO $$ BEGIN RAISE EXCEPTION 'connected database does not match expected_database_name'; END $$;
\endif
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';
SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.remove_empty_infodengue_dengue_history'));

DO $guard$
BEGIN
  IF current_database() <> 'infodengue' THEN
    RAISE EXCEPTION 'this workflow requires the infodengue database';
  END IF;
  IF pg_is_in_recovery() THEN
    RAISE EXCEPTION 'database is in recovery';
  END IF;
  IF :'removal_approval' <> 'REMOVE_APPROVED_EMPTY_INFODENGUE_DENGUE_HISTORY' THEN
    RAISE EXCEPTION 'explicit removal approval token is invalid';
  END IF;
  IF to_regclass('public."Dengue_2010"') IS NULL
     OR to_regclass('public."Dengue_2011"') IS NULL
     OR to_regclass('public."Dengue_2012"') IS NULL
     OR to_regclass('public."Dengue_2013"') IS NULL
     OR to_regclass('public."DengueConfirmados_2013"') IS NULL
  THEN
    RAISE EXCEPTION 'candidate table inventory is incomplete';
  END IF;
  IF (SELECT count(*) FROM public."Dengue_2010") <> 0
     OR (SELECT count(*) FROM public."Dengue_2011") <> 0
     OR (SELECT count(*) FROM public."Dengue_2012") <> 0
     OR (SELECT count(*) FROM public."Dengue_2013") <> 0
     OR (SELECT count(*) FROM public."DengueConfirmados_2013") <> 0
  THEN
    RAISE EXCEPTION 'candidate table contains rows';
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_constraint con
     WHERE con.contype = 'f'
       AND con.confrelid IN (
         'public."Dengue_2010"'::regclass, 'public."Dengue_2011"'::regclass,
         'public."Dengue_2012"'::regclass, 'public."Dengue_2013"'::regclass,
         'public."DengueConfirmados_2013"'::regclass
       )
       AND con.conrelid NOT IN (
         'public."Dengue_2010"'::regclass, 'public."Dengue_2011"'::regclass,
         'public."Dengue_2012"'::regclass, 'public."Dengue_2013"'::regclass,
         'public."DengueConfirmados_2013"'::regclass
       )
  ) THEN RAISE EXCEPTION 'unexpected inbound foreign-key dependency exists'; END IF;
  IF EXISTS (
    SELECT 1 FROM pg_depend d JOIN pg_rewrite r ON r.oid = d.objid
     WHERE d.classid = 'pg_rewrite'::regclass
       AND d.refobjid IN (
       'public."Dengue_2010"'::regclass, 'public."Dengue_2011"'::regclass,
       'public."Dengue_2012"'::regclass, 'public."Dengue_2013"'::regclass,
       'public."DengueConfirmados_2013"'::regclass
     )
  ) THEN RAISE EXCEPTION 'unexpected view or rule dependency exists'; END IF;
END $guard$;

SELECT 'PRE-REMOVAL' AS receipt, current_database() AS database_name,
       clock_timestamp() AT TIME ZONE 'UTC' AS receipt_utc,
       'public."Dengue_2010"' AS table_name, count(*) AS exact_rows
  FROM public."Dengue_2010"
UNION ALL SELECT 'PRE-REMOVAL', current_database(), clock_timestamp() AT TIME ZONE 'UTC', 'public."Dengue_2011"', count(*) FROM public."Dengue_2011"
UNION ALL SELECT 'PRE-REMOVAL', current_database(), clock_timestamp() AT TIME ZONE 'UTC', 'public."Dengue_2012"', count(*) FROM public."Dengue_2012"
UNION ALL SELECT 'PRE-REMOVAL', current_database(), clock_timestamp() AT TIME ZONE 'UTC', 'public."Dengue_2013"', count(*) FROM public."Dengue_2013"
UNION ALL SELECT 'PRE-REMOVAL', current_database(), clock_timestamp() AT TIME ZONE 'UTC', 'public."DengueConfirmados_2013"', count(*) FROM public."DengueConfirmados_2013";

DROP TABLE public."Dengue_2010";
DROP TABLE public."Dengue_2011";
DROP TABLE public."Dengue_2012";
DROP TABLE public."Dengue_2013";
DROP TABLE public."DengueConfirmados_2013";

DO $post_remove$
BEGIN
  IF to_regclass('public."Dengue_2010"') IS NOT NULL
     OR to_regclass('public."Dengue_2011"') IS NOT NULL
     OR to_regclass('public."Dengue_2012"') IS NOT NULL
     OR to_regclass('public."Dengue_2013"') IS NOT NULL
     OR to_regclass('public."DengueConfirmados_2013"') IS NOT NULL
  THEN RAISE EXCEPTION 'candidate table remains after removal'; END IF;
  IF to_regclass('public.dbf_dbf') IS NULL OR to_regclass('public.dbf_dbfchunkedupload') IS NULL OR to_regclass('public.dbf_sendtopartner') IS NULL OR to_regclass('public.auth_user') IS NULL OR to_regclass('public.django_migrations') IS NULL OR to_regclass('public.spatial_ref_sys') IS NULL OR to_regclass('topology.topology') IS NULL OR to_regclass('topology.layer') IS NULL THEN RAISE EXCEPTION 'protected object is missing'; END IF;
END $post_remove$;

SELECT 'REMOVAL PASS' AS receipt, current_database() AS database_name,
       clock_timestamp() AT TIME ZONE 'UTC' AS completed_utc;
COMMIT;
