-- Validate the archive_tweets batch after running 20260728_01.
--
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

SET LOCAL statement_timeout = '30min';
SET LOCAL lock_timeout = '5s';
SET LOCAL temp_file_limit = '1GB';
SET TRANSACTION READ ONLY;

DO $guard$
DECLARE
    expected_table_acl text[] := ARRAY[
        'administrador=arwdDxt/administrador',
        'Dengue=arwdDxt/administrador',
        'dengue=arwdDxt/administrador',
        'infodenguedev=r/administrador',
        'analista=r/administrador'
    ];
    expected_sequence_acl text[] := ARRAY[
        'administrador=rwU/administrador',
        'dengue=rU/administrador'
    ];
    expected_table_oid oid := COALESCE(
        NULLIF(current_setting('archive_tweets.expected_table_oid', true), ''),
        '17570'
    )::oid;
    expected_sequence_oid oid := COALESCE(
        NULLIF(current_setting('archive_tweets.expected_sequence_oid', true), ''),
        '17573'
    )::oid;
    expected_row_count bigint := COALESCE(
        NULLIF(current_setting('archive_tweets.expected_row_count', true), ''),
        '3879263'
    )::bigint;
    expected_min_date date := COALESCE(
        NULLIF(current_setting('archive_tweets.expected_min_date', true), ''),
        '2012-08-01'
    )::date;
    expected_max_date date := COALESCE(
        NULLIF(current_setting('archive_tweets.expected_max_date', true), ''),
        '2022-09-05'
    )::date;
    expected_municipalities bigint := COALESCE(
        NULLIF(current_setting('archive_tweets.expected_municipalities', true), ''),
        '5570'
    )::bigint;
    expected_min_numero integer := COALESCE(
        NULLIF(current_setting('archive_tweets.expected_min_numero', true), ''),
        '0'
    )::integer;
    expected_max_numero integer := COALESCE(
        NULLIF(current_setting('archive_tweets.expected_max_numero', true), ''),
        '512'
    )::integer;
    expected_total_numero bigint := COALESCE(
        NULLIF(current_setting('archive_tweets.expected_total_numero', true), ''),
        '369888'
    )::bigint;
BEGIN
    IF to_regclass('"Municipio"."Tweet"') IS NOT NULL THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" must be absent after archival';
    END IF;

    IF to_regclass('archive_tweets."Tweet"') IS NULL
       OR to_regclass('archive_tweets."Tweet_id_seq"') IS NULL THEN
        RAISE EXCEPTION
            'archive_tweets must contain Tweet table and sequence after archival';
    END IF;

    IF 'archive_tweets."Tweet"'::regclass::oid <> expected_table_oid THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" OID changed unexpectedly';
    END IF;

    IF 'archive_tweets."Tweet_id_seq"'::regclass::oid <> expected_sequence_oid THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet_id_seq" OID changed unexpectedly';
    END IF;

    IF (
        SELECT c.relkind
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_tweets'
          AND c.relname = 'Tweet'
    ) <> 'r' THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" must remain an ordinary table';
    END IF;

    IF (
        SELECT pg_get_userbyid(c.relowner)
        FROM pg_class AS c
        WHERE c.oid = 'archive_tweets."Tweet"'::regclass
    ) <> 'administrador' THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" owner changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'archive_tweets."Tweet"'::regclass
    ), ARRAY[]::text[]) <> expected_table_acl THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" grants changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT obj_description('archive_tweets."Tweet"'::regclass, 'pg_class')
    ), '') <> 'Série de tweets diários' THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" comment changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'archive_tweets."Tweet_id_seq"'::regclass
    ), ARRAY[]::text[]) <> expected_sequence_acl THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet_id_seq" grants changed unexpectedly';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = 'archive_tweets."Tweet"'::regclass
          AND con.contype = 'p'
          AND con.conname = 'Tweet_pk'
    ) <> 1
       OR (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = 'archive_tweets."Tweet"'::regclass
          AND con.contype = 'f'
          AND con.conname = 'Tweet_CID10'
    ) <> 1 THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" constraints changed unexpectedly';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_indexes
        WHERE schemaname = 'archive_tweets'
          AND tablename = 'Tweet'
          AND indexname = 'Tweet_pk'
    ) <> 1
       OR (
        SELECT count(*)
        FROM pg_indexes
        WHERE schemaname = 'archive_tweets'
          AND tablename = 'Tweet'
          AND indexname = 'Tweets_idx_data'
    ) <> 1 THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" indexes changed unexpectedly';
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
        WHERE ns.nspname = 'archive_tweets'
          AND s.relname = 'Tweet_id_seq'
          AND t.oid = 'archive_tweets."Tweet"'::regclass
          AND a.attname = 'id'
    ) <> 1 THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet_id_seq" ownership changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT pg_get_expr(ad.adbin, ad.adrelid)
        FROM pg_attrdef AS ad
        JOIN pg_attribute AS a
          ON a.attrelid = ad.adrelid
         AND a.attnum = ad.adnum
        WHERE ad.adrelid = 'archive_tweets."Tweet"'::regclass
          AND a.attname = 'id'
    ), '') <> 'nextval(''archive_tweets."Tweet_id_seq"''::regclass)' THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet".id default changed unexpectedly';
    END IF;

    IF (
        SELECT count(*)
        FROM archive_tweets."Tweet"
    ) <> expected_row_count THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" row count changed unexpectedly';
    END IF;

    IF (
        SELECT min(data_dia) FROM archive_tweets."Tweet"
    ) <> expected_min_date
       OR (
        SELECT max(data_dia) FROM archive_tweets."Tweet"
    ) <> expected_max_date THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" date range changed unexpectedly';
    END IF;

    IF (
        SELECT count(DISTINCT "Municipio_geocodigo")
        FROM archive_tweets."Tweet"
    ) <> expected_municipalities
       OR (
        SELECT min(numero) FROM archive_tweets."Tweet"
    ) <> expected_min_numero
       OR (
        SELECT max(numero) FROM archive_tweets."Tweet"
    ) <> expected_max_numero
       OR (
        SELECT sum(numero)::bigint FROM archive_tweets."Tweet"
    ) <> expected_total_numero THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" numeric profile changed unexpectedly';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM archive_tweets."Tweet"
        WHERE "CID10_codigo" <> 'A90'
    ) THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" disease coverage changed unexpectedly';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_tweets'
          AND c.relname NOT IN ('Tweet', 'Tweet_id_seq', 'Tweet_pk', 'Tweets_idx_data')
          AND c.relkind IN ('r', 'S', 'i')
    ) <> 0 THEN
        RAISE EXCEPTION
            'archive_tweets contains unexpected table, sequence, or index objects';
    END IF;
END
$guard$;

SELECT n.nspname AS schema_name,
       c.relname AS object_name,
       c.relkind,
       c.oid,
       pg_get_userbyid(c.relowner) AS owner,
       c.relacl::text[] AS acl,
       obj_description(c.oid, 'pg_class') AS comment
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE n.nspname = 'archive_tweets'
  AND c.relname IN ('Tweet', 'Tweet_id_seq', 'Tweet_pk', 'Tweets_idx_data')
ORDER BY c.relname;

SELECT count(*) AS exact_row_count,
       min(data_dia) AS min_date,
       max(data_dia) AS max_date,
       count(DISTINCT "Municipio_geocodigo") AS municipalities,
       min(numero) AS min_numero,
       max(numero) AS max_numero,
       sum(numero)::bigint AS total_numero
FROM archive_tweets."Tweet";

SELECT "CID10_codigo",
       count(*) AS rows,
       min(data_dia) AS min_date,
       max(data_dia) AS max_date
FROM archive_tweets."Tweet"
GROUP BY "CID10_codigo"
ORDER BY "CID10_codigo";

SELECT con.conname,
       con.contype,
       pg_get_constraintdef(con.oid) AS constraint_definition
FROM pg_constraint AS con
WHERE con.conrelid = 'archive_tweets."Tweet"'::regclass
ORDER BY con.contype, con.conname;

SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'archive_tweets'
  AND tablename = 'Tweet'
ORDER BY indexname;

SELECT last_value, is_called
FROM archive_tweets."Tweet_id_seq";

ROLLBACK;
