-- Validate the archive_copernicus batch after running 20260727_01.
--
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DO $guard$
DECLARE
    expected_arg_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'analista=r/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'mosqlimate_dev=r/dengueadmin'
    ];
    expected_foz_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'analista=r/dengueadmin',
        'mosqlimate_dev=r/dengueadmin'
    ];
    expected_bra_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'analista=r/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'mosqlimate_dev=r/dengueadmin'
    ];
BEGIN
    IF to_regclass('weather.copernicus_arg') IS NOT NULL
       OR to_regclass('weather.copernicus_foz_do_iguacu') IS NOT NULL THEN
        RAISE EXCEPTION
            'weather still contains one or more archived Copernicus relations';
    END IF;

    IF to_regclass('archive_copernicus.copernicus_arg') IS NULL
       OR to_regclass('archive_copernicus.copernicus_foz_do_iguacu') IS NULL THEN
        RAISE EXCEPTION
            'archive_copernicus is missing one or more expected tables';
    END IF;

    IF to_regclass('weather.copernicus_bra') IS NULL THEN
        RAISE EXCEPTION
            'weather.copernicus_bra must remain active and present';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_copernicus'
          AND c.relname IN ('copernicus_arg', 'copernicus_foz_do_iguacu')
          AND c.relkind <> 'r'
    ) THEN
        RAISE EXCEPTION
            'archive_copernicus contains an unexpected relation type for the Copernicus batch';
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
          AND tgt_ns.nspname = 'archive_copernicus'
          AND tgt.relname IN ('copernicus_arg', 'copernicus_foz_do_iguacu')
          AND src_ns.nspname <> 'archive_copernicus'
    ) THEN
        RAISE EXCEPTION
            'unexpected inbound foreign-key dependency remains on archive_copernicus';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_constraint AS con
        JOIN pg_class AS src
          ON src.oid = con.conrelid
        JOIN pg_namespace AS src_ns
          ON src_ns.oid = src.relnamespace
        WHERE con.contype = 'f'
          AND src_ns.nspname = 'archive_copernicus'
          AND src.relname IN ('copernicus_arg', 'copernicus_foz_do_iguacu')
    ) THEN
        RAISE EXCEPTION
            'unexpected foreign-key dependency remains inside archive_copernicus';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_rewrite AS r
        JOIN pg_class AS c
          ON c.oid = r.ev_class
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        JOIN pg_depend AS d
          ON d.objid = r.oid
        WHERE d.refobjid IN (
            'archive_copernicus.copernicus_arg'::regclass,
            'archive_copernicus.copernicus_foz_do_iguacu'::regclass
        )
          AND n.nspname <> 'archive_copernicus'
    ) THEN
        RAISE EXCEPTION
            'unexpected external view dependency remains on archive_copernicus';
    END IF;

    IF (
        SELECT count(*)
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
        WHERE cls_ns.nspname = 'archive_copernicus'
          AND cls.relname IN ('copernicus_arg', 'copernicus_foz_do_iguacu')
          AND seq_ns.nspname = 'archive_copernicus'
    ) <> 1 THEN
        RAISE EXCEPTION
            'expected exactly 1 owned sequence in archive_copernicus';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_copernicus'
          AND c.relname IN ('copernicus_arg', 'copernicus_foz_do_iguacu')
          AND pg_get_userbyid(c.relowner) <> 'dengueadmin'
    ) THEN
        RAISE EXCEPTION
            'one or more archived Copernicus tables changed owner unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_copernicus'
          AND c.relname = 'copernicus_arg'
    ), ARRAY[]::text[]) <> expected_arg_acl THEN
        RAISE EXCEPTION
            'archive_copernicus.copernicus_arg grants changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_copernicus'
          AND c.relname = 'copernicus_foz_do_iguacu'
    ), ARRAY[]::text[]) <> expected_foz_acl THEN
        RAISE EXCEPTION
            'archive_copernicus.copernicus_foz_do_iguacu grants changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_copernicus'
          AND c.relname = 'copernicus_foz_do_iguacu_index_seq'
    ), ARRAY[]::text[]) <> ARRAY[]::text[] THEN
        RAISE EXCEPTION
            'archive_copernicus.copernicus_foz_do_iguacu_index_seq grants changed unexpectedly';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = 'weather.copernicus_bra'::regclass
          AND con.contype = 'u'
          AND con.conname = 'copernicus_bra_unique_date_geocode'
    ) <> 1 THEN
        RAISE EXCEPTION
            'weather.copernicus_bra unique constraint changed unexpectedly';
    END IF;

    IF (
        SELECT pg_get_userbyid(c.relowner)
        FROM pg_class AS c
        WHERE c.oid = 'weather.copernicus_bra'::regclass
    ) <> 'dengueadmin' THEN
        RAISE EXCEPTION
            'weather.copernicus_bra owner changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'weather.copernicus_bra'::regclass
    ), ARRAY[]::text[]) <> expected_bra_acl THEN
        RAISE EXCEPTION
            'weather.copernicus_bra grants changed unexpectedly';
    END IF;
END
$guard$;

SELECT n.nspname AS schema_name,
       c.relname AS object_name,
       c.relkind,
       pg_get_userbyid(c.relowner) AS owner,
       pg_total_relation_size(c.oid) AS total_size,
       obj_description(c.oid, 'pg_class') AS table_comment
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE (n.nspname = 'archive_copernicus'
       AND c.relname IN ('copernicus_arg', 'copernicus_foz_do_iguacu'))
   OR (n.nspname = 'weather'
       AND c.relname = 'copernicus_bra')
ORDER BY n.nspname, c.relname;

SELECT 'copernicus_arg' AS object_name,
       COUNT(*) AS row_count,
       MIN(date) AS earliest_ts,
       MAX(date) AS latest_ts
FROM archive_copernicus.copernicus_arg
UNION ALL
SELECT 'copernicus_foz_do_iguacu',
       COUNT(*),
       MIN(datetime),
       MAX(datetime)
FROM archive_copernicus.copernicus_foz_do_iguacu
UNION ALL
SELECT 'copernicus_bra',
       COUNT(*),
       MIN(date),
       MAX(date)
FROM weather.copernicus_bra;

SELECT con.conname,
       con.contype,
       src_ns.nspname AS src_schema,
       src.relname AS src_table,
       pg_get_constraintdef(con.oid) AS constraint_definition
FROM pg_constraint AS con
JOIN pg_class AS src
  ON src.oid = con.conrelid
JOIN pg_namespace AS src_ns
  ON src_ns.oid = src.relnamespace
WHERE (src_ns.nspname = 'archive_copernicus'
       AND src.relname IN ('copernicus_arg', 'copernicus_foz_do_iguacu'))
   OR (src_ns.nspname = 'weather'
       AND src.relname = 'copernicus_bra')
ORDER BY src.relname, con.conname;

SELECT schemaname,
       tablename,
       indexname,
       indexdef
FROM pg_indexes
WHERE (schemaname = 'archive_copernicus'
       AND tablename IN ('copernicus_arg', 'copernicus_foz_do_iguacu'))
   OR (schemaname = 'weather'
       AND tablename = 'copernicus_bra')
ORDER BY tablename, indexname;

SELECT cls.relname AS table_name,
       att.attname AS column_name,
       seq_ns.nspname AS sequence_schema,
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
WHERE cls_ns.nspname = 'archive_copernicus'
  AND cls.relname IN ('copernicus_arg', 'copernicus_foz_do_iguacu')
ORDER BY cls.relname, att.attname;

COMMIT;
