-- Validate the archive_mosqlimate batch after running 20260728_01.
--
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';
SET LOCAL temp_file_limit = '256MB';

DO $guard$
DECLARE
    expected_table_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'analista=r/dengueadmin'
    ];
    expected_row_count bigint := COALESCE(
        NULLIF(current_setting('archive_mosqlimate.expected_row_count', true), ''),
        '4187433'
    )::bigint;
    expected_min_epiweek bigint := COALESCE(
        NULLIF(current_setting('archive_mosqlimate.expected_min_epiweek', true), ''),
        '201001'
    )::bigint;
    expected_max_epiweek bigint := COALESCE(
        NULLIF(current_setting('archive_mosqlimate.expected_max_epiweek', true), ''),
        '202423'
    )::bigint;
    expected_min_date date := COALESCE(
        NULLIF(current_setting('archive_mosqlimate.expected_min_date', true), ''),
        '2010-01-03'
    )::date;
    expected_max_date date := COALESCE(
        NULLIF(current_setting('archive_mosqlimate.expected_max_date', true), ''),
        '2024-06-02'
    )::date;
BEGIN
    IF to_regclass('"Municipio".sprint202425') IS NOT NULL THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 must be absent after archival';
    END IF;

    IF to_regclass('archive_mosqlimate.sprint202425') IS NULL THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 must be present after archival';
    END IF;

    IF to_regclass('archive_mosqlimate.sprint202425_id_seq') IS NULL THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425_id_seq must be present after archival';
    END IF;

    IF (
        SELECT c.relkind
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_mosqlimate'
          AND c.relname = 'sprint202425'
    ) <> 'r' THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 must remain an ordinary table';
    END IF;

    IF (
        SELECT pg_get_userbyid(c.relowner)
        FROM pg_class AS c
        WHERE c.oid = 'archive_mosqlimate.sprint202425'::regclass
    ) <> 'dengueadmin' THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 owner changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'archive_mosqlimate.sprint202425'::regclass
    ), ARRAY[]::text[]) <> expected_table_acl THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 grants changed unexpectedly';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = 'archive_mosqlimate.sprint202425'::regclass
          AND con.contype = 'p'
          AND con.conname = 'sprint202425_pkey'
    ) <> 1 THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 primary key changed unexpectedly';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_indexes
        WHERE schemaname = 'archive_mosqlimate'
          AND tablename = 'sprint202425'
          AND indexname = 'sprint202425_pkey'
    ) <> 1 THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 primary-key index changed unexpectedly';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_trigger AS t
        WHERE t.tgrelid = 'archive_mosqlimate.sprint202425'::regclass
          AND NOT t.tgisinternal
    ) <> 0 THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 unexpectedly has user-defined triggers';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_class AS s
        JOIN pg_namespace AS ns
          ON ns.oid = s.relnamespace
        JOIN pg_depend AS d
          ON d.objid = s.oid
         AND d.classid = 'pg_class'::regclass
         AND d.refclassid = 'pg_class'::regclass
         AND d.deptype = 'a'
        JOIN pg_class AS t
          ON t.oid = d.refobjid
        JOIN pg_attribute AS a
          ON a.attrelid = t.oid
         AND a.attnum = d.refobjsubid
        WHERE ns.nspname = 'archive_mosqlimate'
          AND s.relname = 'sprint202425_id_seq'
          AND t.oid = 'archive_mosqlimate.sprint202425'::regclass
          AND a.attname = 'id'
    ) <> 1 THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425_id_seq ownership changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT pg_get_expr(ad.adbin, ad.adrelid)
        FROM pg_attrdef AS ad
        JOIN pg_attribute AS a
          ON a.attrelid = ad.adrelid
         AND a.attnum = ad.adnum
        WHERE ad.adrelid = 'archive_mosqlimate.sprint202425'::regclass
          AND a.attname = 'id'
    ), '') <> 'nextval(''archive_mosqlimate.sprint202425_id_seq''::regclass)' THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425.id default changed unexpectedly';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_rewrite AS r
        JOIN pg_depend AS d
          ON d.objid = r.oid
        WHERE d.refobjid = 'archive_mosqlimate.sprint202425'::regclass
    ) THEN
        RAISE EXCEPTION
            'unexpected view or materialized-view dependency found for archive_mosqlimate.sprint202425';
    END IF;

    IF to_regclass('"Municipio"."Notificacao"') IS NULL THEN
        RAISE EXCEPTION
            '"Municipio"."Notificacao" must remain present after Mosqlimate archival';
    END IF;

    IF (
        SELECT c.relkind
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname = 'Notificacao'
    ) <> 'r' THEN
        RAISE EXCEPTION
            '"Municipio"."Notificacao" changed type unexpectedly';
    END IF;

    IF (
        SELECT COUNT(*)
        FROM archive_mosqlimate.sprint202425
    ) <> expected_row_count THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 row count changed unexpectedly';
    END IF;

    IF (
        SELECT MIN(epiweek) FROM archive_mosqlimate.sprint202425
    ) <> expected_min_epiweek
       OR (
        SELECT MAX(epiweek) FROM archive_mosqlimate.sprint202425
    ) <> expected_max_epiweek THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 epidemiological range changed unexpectedly';
    END IF;

    IF (
        SELECT MIN(date) FROM archive_mosqlimate.sprint202425
    ) <> expected_min_date
       OR (
        SELECT MAX(date) FROM archive_mosqlimate.sprint202425
    ) <> expected_max_date THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 date range changed unexpectedly';
    END IF;
END
$guard$;

SELECT n.nspname AS schema_name,
       c.relname AS object_name,
       c.relkind,
       c.oid,
       pg_get_userbyid(c.relowner) AS owner,
       pg_total_relation_size(c.oid) AS total_size,
       obj_description(c.oid, 'pg_class') AS table_comment
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE (n.nspname = 'archive_mosqlimate'
       AND c.relname IN ('sprint202425', 'sprint202425_id_seq'))
   OR (n.nspname = 'Municipio'
       AND c.relname = 'Notificacao')
ORDER BY n.nspname, c.relname;

SELECT COUNT(*) AS exact_row_count,
       MIN(epiweek) AS min_epiweek,
       MAX(epiweek) AS max_epiweek,
       MIN(date) AS min_date,
       MAX(date) AS max_date
FROM archive_mosqlimate.sprint202425;

SELECT con.conname,
       con.contype,
       pg_get_constraintdef(con.oid) AS constraint_definition
FROM pg_constraint AS con
WHERE con.conrelid = 'archive_mosqlimate.sprint202425'::regclass
ORDER BY con.contype, con.conname;

SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'archive_mosqlimate'
  AND tablename = 'sprint202425'
ORDER BY indexname;

SELECT s.relname AS sequence_name,
       pg_get_userbyid(s.relowner) AS owner,
       d.deptype,
       a.attname AS owned_column,
       pg_get_expr(ad.adbin, ad.adrelid) AS default_expr
FROM pg_class AS s
JOIN pg_namespace AS ns
  ON ns.oid = s.relnamespace
JOIN pg_depend AS d
  ON d.objid = s.oid
 AND d.classid = 'pg_class'::regclass
 AND d.refclassid = 'pg_class'::regclass
JOIN pg_class AS t
  ON t.oid = d.refobjid
LEFT JOIN pg_attribute AS a
  ON a.attrelid = t.oid
 AND a.attnum = d.refobjsubid
LEFT JOIN pg_attrdef AS ad
  ON ad.adrelid = t.oid
 AND ad.adnum = a.attnum
WHERE ns.nspname = 'archive_mosqlimate'
  AND s.relname = 'sprint202425_id_seq';

SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'archive_mosqlimate'
  AND table_name = 'sprint202425'
ORDER BY grantee, privilege_type;

COMMIT;
