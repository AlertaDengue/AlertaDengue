-- Restore the archived tweet dataset back to the Municipio schema.
--
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
    archived_table_oid oid := COALESCE(
        NULLIF(current_setting('archive_tweets.expected_table_oid', true), ''),
        '17570'
    )::oid;
    archived_sequence_oid oid := COALESCE(
        NULLIF(current_setting('archive_tweets.expected_sequence_oid', true), ''),
        '17573'
    )::oid;
BEGIN
    IF to_regclass('archive_tweets."Tweet"') IS NULL
       OR to_regclass('archive_tweets."Tweet_id_seq"') IS NULL THEN
        RAISE EXCEPTION
            'archive_tweets does not contain the full Tweet batch required for restoration';
    END IF;

    IF to_regclass('"Municipio"."Tweet"') IS NOT NULL
       OR to_regclass('"Municipio"."Tweet_id_seq"') IS NOT NULL THEN
        RAISE EXCEPTION
            '"Municipio" already contains Tweet objects; restoration would conflict';
    END IF;

    IF 'archive_tweets."Tweet"'::regclass::oid <> archived_table_oid
       OR 'archive_tweets."Tweet_id_seq"'::regclass::oid <> archived_sequence_oid THEN
        RAISE EXCEPTION
            'archive_tweets object OIDs changed unexpectedly before restoration';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'archive_tweets."Tweet"'::regclass
    ), ARRAY[]::text[]) <> expected_table_acl
       OR COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'archive_tweets."Tweet_id_seq"'::regclass
    ), ARRAY[]::text[]) <> expected_sequence_acl THEN
        RAISE EXCEPTION
            'archive_tweets Tweet grants changed unexpectedly before restoration';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_rewrite AS r
        JOIN pg_depend AS d
          ON d.objid = r.oid
        WHERE d.refobjid = 'archive_tweets."Tweet"'::regclass
    ) THEN
        RAISE EXCEPTION
            'unexpected view or materialized-view dependency blocks restoring archive_tweets."Tweet"';
    END IF;

    ALTER TABLE archive_tweets."Tweet"
        SET SCHEMA "Municipio";

    IF '"Municipio"."Tweet"'::regclass::oid <> archived_table_oid
       OR '"Municipio"."Tweet_id_seq"'::regclass::oid <> archived_sequence_oid THEN
        RAISE EXCEPTION
            '"Municipio" Tweet object OIDs changed unexpectedly during restoration';
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
            '"Municipio"."Tweet".id default changed unexpectedly after restoration';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = '"Municipio"."Tweet"'::regclass
          AND con.contype = 'p'
          AND con.conname = 'Tweet_pk'
    ) <> 1
       OR (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = '"Municipio"."Tweet"'::regclass
          AND con.contype = 'f'
          AND con.conname = 'Tweet_CID10'
    ) <> 1 THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" constraints changed unexpectedly after restoration';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_indexes
        WHERE schemaname = 'Municipio'
          AND tablename = 'Tweet'
          AND indexname IN ('Tweet_pk', 'Tweets_idx_data')
    ) <> 2 THEN
        RAISE EXCEPTION
            '"Municipio"."Tweet" indexes changed unexpectedly after restoration';
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
            '"Municipio"."Tweet_id_seq" ownership changed unexpectedly after restoration';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_tweets'
    ) <> 0 THEN
        RAISE EXCEPTION
            'archive_tweets is not empty after restoration';
    END IF;

    DROP SCHEMA archive_tweets;
END
$guard$;

COMMIT;
