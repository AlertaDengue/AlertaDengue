-- Archive the frozen historical tweet dataset by moving it into archive_tweets.
--
-- Run as the database owner, or as a role that owns the affected relation.
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

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
    source_table_oid oid;
    source_sequence_oid oid;
BEGIN
    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION
            'archive_tweets archival must not run on a PostgreSQL standby';
    END IF;

    IF to_regclass('"Municipio"."Tweet"') IS NULL
       OR to_regclass('"Municipio"."Tweet_id_seq"') IS NULL THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" and "Municipio"."Tweet_id_seq" must exist before archival';
    END IF;

    IF to_regclass('archive_tweets."Tweet"') IS NOT NULL
       OR to_regclass('archive_tweets."Tweet_id_seq"') IS NOT NULL THEN
        RAISE EXCEPTION
            'archive_tweets already contains Tweet objects';
    END IF;

    IF to_regnamespace('archive_tweets') IS NOT NULL
       AND EXISTS (
           SELECT 1
           FROM pg_class AS c
           JOIN pg_namespace AS n
             ON n.oid = c.relnamespace
           WHERE n.nspname = 'archive_tweets'
       ) THEN
        RAISE EXCEPTION
            'archive_tweets already exists and is not empty; review it before rerunning';
    END IF;

    IF (
        SELECT c.relkind
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname = 'Tweet'
    ) <> 'r' THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" must be an ordinary table';
    END IF;

    IF (
        SELECT pg_get_userbyid(c.relowner)
        FROM pg_class AS c
        WHERE c.oid = '"Municipio"."Tweet"'::regclass
    ) <> 'administrador' THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" owner changed unexpectedly before archival';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = '"Municipio"."Tweet"'::regclass
    ), ARRAY[]::text[]) <> expected_table_acl THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" grants changed unexpectedly before archival';
    END IF;

    IF COALESCE((
        SELECT obj_description('"Municipio"."Tweet"'::regclass, 'pg_class')
    ), '') <> 'Série de tweets diários' THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" comment changed unexpectedly before archival';
    END IF;

    IF (
        SELECT pg_get_userbyid(c.relowner)
        FROM pg_class AS c
        WHERE c.oid = '"Municipio"."Tweet_id_seq"'::regclass
    ) <> 'administrador' THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet_id_seq" owner changed unexpectedly before archival';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = '"Municipio"."Tweet_id_seq"'::regclass
    ), ARRAY[]::text[]) <> expected_sequence_acl THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet_id_seq" grants changed unexpectedly before archival';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = '"Municipio"."Tweet"'::regclass
          AND con.contype = 'p'
          AND con.conname = 'Tweet_pk'
    ) <> 1 THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" must retain Tweet_pk before archival';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = '"Municipio"."Tweet"'::regclass
          AND con.contype = 'f'
          AND con.conname = 'Tweet_CID10'
          AND pg_get_constraintdef(con.oid) = 'FOREIGN KEY ("CID10_codigo") REFERENCES "Dengue_global"."CID10"(codigo)'
    ) <> 1 THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" must retain Tweet_CID10 before archival';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_indexes
        WHERE schemaname = 'Municipio'
          AND tablename = 'Tweet'
          AND indexname = 'Tweet_pk'
    ) <> 1
       OR (
        SELECT count(*)
        FROM pg_indexes
        WHERE schemaname = 'Municipio'
          AND tablename = 'Tweet'
          AND indexname = 'Tweets_idx_data'
    ) <> 1 THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" indexes changed unexpectedly before archival';
    END IF;

    IF COALESCE((
        SELECT pg_get_expr(ad.adbin, ad.adrelid)
        FROM pg_attrdef AS ad
        JOIN pg_attribute AS a
          ON a.attrelid = ad.adrelid
         AND a.attnum = ad.adnum
        WHERE ad.adrelid = '"Municipio"."Tweet"'::regclass
          AND a.attname = 'id'
    ), '') <> 'nextval(''"Municipio"."Tweet_id_seq"''::regclass)' THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet".id default changed unexpectedly before archival';
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
        WHERE ns.nspname = 'Municipio'
          AND s.relname = 'Tweet_id_seq'
          AND t.oid = '"Municipio"."Tweet"'::regclass
          AND a.attname = 'id'
    ) <> 1 THEN
        RAISE EXCEPTION
            'expected "Municipio"."Tweet_id_seq" to remain owned by Tweet.id before archival';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_trigger AS t
        WHERE t.tgrelid = '"Municipio"."Tweet"'::regclass
          AND NOT t.tgisinternal
    ) THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" unexpectedly has user-defined triggers';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_constraint AS con
        JOIN pg_class AS src
          ON src.oid = con.conrelid
        JOIN pg_namespace AS src_ns
          ON src_ns.oid = src.relnamespace
        JOIN pg_class AS tgt
          ON tgt.oid = con.confrelid
        JOIN pg_namespace AS tgt_ns
          ON tgt_ns.oid = tgt.relnamespace
        WHERE con.contype = 'f'
          AND tgt_ns.nspname = 'Municipio'
          AND tgt.relname = 'Tweet'
          AND NOT (src_ns.nspname = 'Municipio' AND src.relname = 'Tweet')
    ) THEN
        RAISE EXCEPTION
            'unexpected inbound foreign-key dependency found for "Municipio"."Tweet"';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_rewrite AS r
        JOIN pg_depend AS d
          ON d.objid = r.oid
        WHERE d.refobjid = '"Municipio"."Tweet"'::regclass
    ) THEN
        RAISE EXCEPTION
            'unexpected view or materialized-view dependency found for "Municipio"."Tweet"';
    END IF;

    IF (
        SELECT count(*)
        FROM "Municipio"."Tweet"
    ) <> expected_row_count THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" row count changed unexpectedly before archival';
    END IF;

    IF (
        SELECT min(data_dia) FROM "Municipio"."Tweet"
    ) <> expected_min_date
       OR (
        SELECT max(data_dia) FROM "Municipio"."Tweet"
    ) <> expected_max_date THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" date range changed unexpectedly before archival';
    END IF;

    IF (
        SELECT count(DISTINCT "CID10_codigo")
        FROM "Municipio"."Tweet"
    ) <> 1
       OR EXISTS (
        SELECT 1
        FROM "Municipio"."Tweet"
        WHERE "CID10_codigo" <> 'A90'
    ) THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" disease coverage changed unexpectedly before archival';
    END IF;

    SELECT '"Municipio"."Tweet"'::regclass::oid,
           '"Municipio"."Tweet_id_seq"'::regclass::oid
    INTO source_table_oid, source_sequence_oid;

    CREATE SCHEMA IF NOT EXISTS archive_tweets;
    REVOKE ALL ON SCHEMA archive_tweets FROM PUBLIC;

    ALTER TABLE "Municipio"."Tweet"
        SET SCHEMA archive_tweets;

    IF 'archive_tweets."Tweet"'::regclass::oid <> source_table_oid THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet" OID changed unexpectedly during archival';
    END IF;

    IF 'archive_tweets."Tweet_id_seq"'::regclass::oid <> source_sequence_oid THEN
        RAISE EXCEPTION
            'archive_tweets."Tweet_id_seq" OID changed unexpectedly during archival';
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
            'archive_tweets."Tweet".id default changed unexpectedly during archival';
    END IF;
END
$guard$;

COMMIT;
