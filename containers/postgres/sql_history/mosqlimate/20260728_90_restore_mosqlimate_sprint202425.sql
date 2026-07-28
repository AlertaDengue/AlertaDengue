-- Restore the archived Mosqlimate dataset back to the Municipio schema.
--
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DO $guard$
DECLARE
    expected_table_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'analista=r/dengueadmin'
    ];
BEGIN
    IF to_regclass('archive_mosqlimate.sprint202425') IS NULL
       OR to_regclass('archive_mosqlimate.sprint202425_id_seq') IS NULL THEN
        RAISE EXCEPTION
            'archive_mosqlimate does not contain the full sprint202425 batch required for restoration';
    END IF;

    IF to_regclass('"Municipio".sprint202425') IS NOT NULL
       OR to_regclass('"Municipio".sprint202425_id_seq') IS NOT NULL THEN
        RAISE EXCEPTION
            '"Municipio" already contains sprint202425 objects; restoration would conflict';
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
            'archive_mosqlimate.sprint202425 must remain an ordinary table before restoration';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'archive_mosqlimate.sprint202425'::regclass
    ), ARRAY[]::text[]) <> expected_table_acl THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 grants changed unexpectedly before restoration';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_rewrite AS r
        JOIN pg_depend AS d
          ON d.objid = r.oid
        WHERE d.refobjid = 'archive_mosqlimate.sprint202425'::regclass
    ) THEN
        RAISE EXCEPTION
            'unexpected view or materialized-view dependency blocks restoring archive_mosqlimate.sprint202425';
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
            'archive_mosqlimate.sprint202425_id_seq ownership changed unexpectedly before restoration';
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
            'archive_mosqlimate.sprint202425.id default changed unexpectedly before restoration';
    END IF;
END
$guard$;

ALTER TABLE archive_mosqlimate.sprint202425
    SET SCHEMA "Municipio";

DO $move_sequences$
DECLARE
    owned_sequence record;
BEGIN
    FOR owned_sequence IN
        SELECT seq_ns.nspname AS sequence_schema,
               seq.relname AS sequence_name
        FROM pg_class AS cls
        JOIN pg_namespace AS cls_ns
          ON cls_ns.oid = cls.relnamespace
        JOIN pg_attribute AS att
          ON att.attrelid = cls.oid
         AND att.attnum > 0
         AND NOT att.attisdropped
        JOIN pg_depend AS dep
          ON dep.refobjid = cls.oid
         AND dep.refobjsubid = att.attnum
         AND dep.deptype = 'a'
        JOIN pg_class AS seq
          ON seq.oid = dep.objid
         AND seq.relkind = 'S'
        JOIN pg_namespace AS seq_ns
          ON seq_ns.oid = seq.relnamespace
        WHERE cls_ns.nspname = 'Municipio'
          AND cls.relname = 'sprint202425'
          AND seq_ns.nspname = 'archive_mosqlimate'
        ORDER BY seq.relname
    LOOP
        EXECUTE format(
            'ALTER SEQUENCE %I.%I SET SCHEMA "Municipio"',
            owned_sequence.sequence_schema,
            owned_sequence.sequence_name
        );
    END LOOP;
END
$move_sequences$;

DO $postcheck$
DECLARE
    expected_table_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'analista=r/dengueadmin'
    ];
BEGIN
    IF to_regclass('"Municipio".sprint202425') IS NULL
       OR to_regclass('"Municipio".sprint202425_id_seq') IS NULL THEN
        RAISE EXCEPTION
            '"Municipio" does not contain the full sprint202425 batch after restoration';
    END IF;

    IF (
        SELECT c.relkind
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname = 'sprint202425'
    ) <> 'r' THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 is not an ordinary table after restoration';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = '"Municipio".sprint202425'::regclass
    ), ARRAY[]::text[]) <> expected_table_acl THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 grants changed unexpectedly after restoration';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = '"Municipio".sprint202425'::regclass
          AND con.contype = 'p'
          AND con.conname = 'sprint202425_pkey'
    ) <> 1 THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 primary key changed unexpectedly after restoration';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_indexes
        WHERE schemaname = 'Municipio'
          AND tablename = 'sprint202425'
          AND indexname = 'sprint202425_pkey'
    ) <> 1 THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 primary-key index changed unexpectedly after restoration';
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
          AND s.relname = 'sprint202425_id_seq'
          AND t.oid = '"Municipio".sprint202425'::regclass
          AND a.attname = 'id'
    ) <> 1 THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425_id_seq ownership changed unexpectedly after restoration';
    END IF;

    IF COALESCE((
        SELECT pg_get_expr(ad.adbin, ad.adrelid)
        FROM pg_attrdef AS ad
        JOIN pg_attribute AS a
          ON a.attrelid = ad.adrelid
         AND a.attnum = ad.adnum
        WHERE ad.adrelid = '"Municipio".sprint202425'::regclass
          AND a.attname = 'id'
    ), '') <> 'nextval(''"Municipio".sprint202425_id_seq''::regclass)' THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425.id default changed unexpectedly after restoration';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_mosqlimate'
    ) <> 0 THEN
        RAISE EXCEPTION
            'archive_mosqlimate is not empty after restoration';
    END IF;
END
$postcheck$;

DROP SCHEMA archive_mosqlimate;

COMMIT;
