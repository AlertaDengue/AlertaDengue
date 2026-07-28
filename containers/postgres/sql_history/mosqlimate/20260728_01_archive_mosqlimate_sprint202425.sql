-- Archive the frozen Mosqlimate 2025 dataset by moving sprint202425 into
-- archive_mosqlimate.
--
-- Run as the database owner, or as a role that owns the affected relation.
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
    expected_notificacao_owner text := 'administrador';
    expected_sequence_owner text := 'dengueadmin';
BEGIN
    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION
            'archive_mosqlimate archival must not run on a PostgreSQL standby';
    END IF;

    IF to_regclass('"Municipio".sprint202425') IS NULL THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 must exist before archival';
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
            '"Municipio".sprint202425 must be an ordinary table';
    END IF;

    IF (
        SELECT pg_get_userbyid(c.relowner)
        FROM pg_class AS c
        WHERE c.oid = '"Municipio".sprint202425'::regclass
    ) <> 'dengueadmin' THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 owner changed unexpectedly before archival';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = '"Municipio".sprint202425'::regclass
    ), ARRAY[]::text[]) <> expected_table_acl THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 grants changed unexpectedly before archival';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = '"Municipio".sprint202425'::regclass
          AND con.contype = 'p'
          AND con.conname = 'sprint202425_pkey'
    ) <> 1 THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 must retain sprint202425_pkey before archival';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_indexes
        WHERE schemaname = 'Municipio'
          AND tablename = 'sprint202425'
          AND indexname = 'sprint202425_pkey'
    ) <> 1 THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 must retain sprint202425_pkey index before archival';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_trigger AS t
        WHERE t.tgrelid = '"Municipio".sprint202425'::regclass
          AND NOT t.tgisinternal
    ) THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 unexpectedly has user-defined triggers';
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
            'expected "Municipio".sprint202425_id_seq to remain owned by sprint202425.id before archival';
    END IF;

    IF (
        SELECT pg_get_userbyid(c.relowner)
        FROM pg_class AS c
        WHERE c.oid = '"Municipio".sprint202425_id_seq'::regclass
    ) <> expected_sequence_owner THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425_id_seq owner changed unexpectedly before archival';
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
            '"Municipio".sprint202425.id default changed unexpectedly before archival';
    END IF;

    IF to_regclass('archive_mosqlimate.sprint202425') IS NOT NULL
       OR to_regclass('archive_mosqlimate.sprint202425_id_seq') IS NOT NULL THEN
        RAISE EXCEPTION
            'archive_mosqlimate already contains sprint202425 objects';
    END IF;

    IF to_regnamespace('archive_mosqlimate') IS NOT NULL THEN
        IF EXISTS (
            SELECT 1
            FROM pg_class AS c
            JOIN pg_namespace AS n
              ON n.oid = c.relnamespace
            WHERE n.nspname = 'archive_mosqlimate'
        ) THEN
            RAISE EXCEPTION
                'archive_mosqlimate already exists and is not empty; review it before rerunning';
        END IF;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_constraint AS con
        JOIN pg_class AS tgt
          ON tgt.oid = con.confrelid
        JOIN pg_namespace AS tgt_ns
          ON tgt_ns.oid = tgt.relnamespace
        JOIN pg_class AS src
          ON src.oid = con.conrelid
        JOIN pg_namespace AS src_ns
          ON src_ns.oid = src.relnamespace
        WHERE con.contype = 'f'
          AND tgt_ns.nspname = 'Municipio'
          AND tgt.relname = 'sprint202425'
          AND src_ns.nspname <> 'Municipio'
    ) THEN
        RAISE EXCEPTION
            'unexpected inbound foreign-key dependency found for "Municipio".sprint202425';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_constraint AS con
        JOIN pg_class AS src
          ON src.oid = con.conrelid
        JOIN pg_namespace AS src_ns
          ON src_ns.oid = src.relnamespace
        WHERE con.contype = 'f'
          AND src_ns.nspname = 'Municipio'
          AND src.relname = 'sprint202425'
    ) THEN
        RAISE EXCEPTION
            '"Municipio".sprint202425 unexpectedly has outbound foreign-key dependencies';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_rewrite AS r
        JOIN pg_depend AS d
          ON d.objid = r.oid
        WHERE d.refobjid = '"Municipio".sprint202425'::regclass
    ) THEN
        RAISE EXCEPTION
            'unexpected view or materialized-view dependency found for "Municipio".sprint202425';
    END IF;

    IF to_regclass('"Municipio"."Notificacao"') IS NULL THEN
        RAISE EXCEPTION
            '"Municipio"."Notificacao" must remain present during Mosqlimate archival';
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
            '"Municipio"."Notificacao" must remain an ordinary table during Mosqlimate archival';
    END IF;

    IF (
        SELECT pg_get_userbyid(c.relowner)
        FROM pg_class AS c
        WHERE c.oid = '"Municipio"."Notificacao"'::regclass
    ) <> expected_notificacao_owner THEN
        RAISE EXCEPTION
            '"Municipio"."Notificacao" owner changed unexpectedly before Mosqlimate archival';
    END IF;
END
$guard$;

CREATE SCHEMA IF NOT EXISTS archive_mosqlimate;
ALTER SCHEMA archive_mosqlimate OWNER TO postgres;
REVOKE ALL ON SCHEMA archive_mosqlimate FROM PUBLIC;

ALTER TABLE "Municipio".sprint202425
    SET SCHEMA archive_mosqlimate;

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
        WHERE cls_ns.nspname = 'archive_mosqlimate'
          AND cls.relname = 'sprint202425'
          AND seq_ns.nspname = 'Municipio'
        ORDER BY seq.relname
    LOOP
        EXECUTE format(
            'ALTER SEQUENCE %I.%I SET SCHEMA archive_mosqlimate',
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
            '"Municipio".sprint202425 still exists after archival';
    END IF;

    IF to_regclass('archive_mosqlimate.sprint202425') IS NULL THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 is missing after archival';
    END IF;

    IF to_regclass('archive_mosqlimate.sprint202425_id_seq') IS NULL THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425_id_seq is missing after archival';
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
            'archive_mosqlimate.sprint202425 is not an ordinary table after archival';
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
            'archive_mosqlimate.sprint202425_id_seq is not owned by sprint202425.id after archival';
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
            'archive_mosqlimate.sprint202425.id default did not move to the archive sequence';
    END IF;

    IF (
        SELECT COUNT(*)
        FROM archive_mosqlimate.sprint202425
    ) <> expected_row_count THEN
        RAISE EXCEPTION
            'archive_mosqlimate.sprint202425 row count changed unexpectedly after archival';
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

    IF to_regclass('"Municipio"."Notificacao"') IS NULL THEN
        RAISE EXCEPTION
            '"Municipio"."Notificacao" is missing after Mosqlimate archival';
    END IF;
END
$postcheck$;

COMMIT;
