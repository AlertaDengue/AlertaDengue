-- Restore the archived Copernicus tables back to the weather schema.
--
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DO $guard$
DECLARE
    owned_sequence_count integer;
    conflicting_targets text;
    expected_bra_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'analista=r/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'mosqlimate_dev=r/dengueadmin'
    ];
BEGIN
    IF to_regclass('archive_copernicus.copernicus_arg') IS NULL
       OR to_regclass('archive_copernicus.copernicus_foz_do_iguacu') IS NULL THEN
        RAISE EXCEPTION
            'archive_copernicus does not contain the full Copernicus batch required for restoration';
    END IF;

    IF to_regclass('weather.copernicus_arg') IS NOT NULL
       OR to_regclass('weather.copernicus_foz_do_iguacu') IS NOT NULL THEN
        RAISE EXCEPTION
            'weather already contains one or more Copernicus relations; restoration would conflict';
    END IF;

    IF to_regclass('weather.copernicus_bra') IS NULL THEN
        RAISE EXCEPTION
            'weather.copernicus_bra must remain active and present during restoration';
    END IF;

    SELECT string_agg(target_name, ', ')
    INTO conflicting_targets
    FROM (
        SELECT format('weather.%I', relname) AS target_name
        FROM (
            VALUES ('copernicus_foz_do_iguacu_index_seq')
        ) AS expected(relname)
        WHERE to_regclass(format('%I.%I', 'weather', relname)) IS NOT NULL
    ) AS conflicts;

    IF conflicting_targets IS NOT NULL THEN
        RAISE EXCEPTION
            'target weather sequence names already exist: %',
            conflicting_targets;
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
            'unexpected inbound foreign-key dependency blocks restoring archive_copernicus';
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
            'unexpected view or materialized-view dependency blocks restoring archive_copernicus';
    END IF;

    SELECT count(*)
    INTO owned_sequence_count
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
      AND seq_ns.nspname = 'archive_copernicus';

    IF owned_sequence_count <> 1 THEN
        RAISE EXCEPTION
            'expected exactly 1 owned sequence in archive_copernicus before restoration; found %',
            owned_sequence_count;
    END IF;

    IF (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = 'weather.copernicus_bra'::regclass
          AND con.contype = 'u'
          AND con.conname = 'copernicus_bra_unique_date_geocode'
    ) <> 1 THEN
        RAISE EXCEPTION
            'weather.copernicus_bra unique constraint changed unexpectedly before restoration';
    END IF;

    IF (
        SELECT pg_get_userbyid(c.relowner)
        FROM pg_class AS c
        WHERE c.oid = 'weather.copernicus_bra'::regclass
    ) <> 'dengueadmin' THEN
        RAISE EXCEPTION
            'weather.copernicus_bra owner changed unexpectedly before restoration';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'weather.copernicus_bra'::regclass
    ), ARRAY[]::text[]) <> expected_bra_acl THEN
        RAISE EXCEPTION
            'weather.copernicus_bra grants changed unexpectedly before restoration';
    END IF;
END
$guard$;

ALTER TABLE archive_copernicus.copernicus_arg SET SCHEMA weather;
ALTER TABLE archive_copernicus.copernicus_foz_do_iguacu SET SCHEMA weather;

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
        WHERE cls_ns.nspname = 'weather'
          AND cls.relname IN ('copernicus_arg', 'copernicus_foz_do_iguacu')
          AND seq_ns.nspname = 'archive_copernicus'
        ORDER BY seq.relname
    LOOP
        EXECUTE format(
            'ALTER SEQUENCE %I.%I SET SCHEMA weather',
            owned_sequence.sequence_schema,
            owned_sequence.sequence_name
        );
    END LOOP;
END
$move_sequences$;

DO $postcheck$
DECLARE
    owned_sequence_count integer;
    expected_bra_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'analista=r/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'mosqlimate_dev=r/dengueadmin'
    ];
BEGIN
    IF to_regclass('weather.copernicus_arg') IS NULL
       OR to_regclass('weather.copernicus_foz_do_iguacu') IS NULL THEN
        RAISE EXCEPTION
            'weather does not contain the expected Copernicus tables after restoration';
    END IF;

    IF to_regclass('weather.copernicus_bra') IS NULL THEN
        RAISE EXCEPTION
            'weather.copernicus_bra is missing after Copernicus restoration';
    END IF;

    SELECT count(*)
    INTO owned_sequence_count
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
    WHERE cls_ns.nspname = 'weather'
      AND cls.relname IN ('copernicus_arg', 'copernicus_foz_do_iguacu')
      AND seq_ns.nspname = 'weather';

    IF owned_sequence_count <> 1 THEN
        RAISE EXCEPTION
            'expected exactly 1 owned sequence in weather after restoration; found %',
            owned_sequence_count;
    END IF;

    IF (
        SELECT count(*)
        FROM pg_constraint AS con
        WHERE con.conrelid = 'weather.copernicus_bra'::regclass
          AND con.contype = 'u'
          AND con.conname = 'copernicus_bra_unique_date_geocode'
    ) <> 1 THEN
        RAISE EXCEPTION
            'weather.copernicus_bra unique constraint changed unexpectedly after restoration';
    END IF;

    IF (
        SELECT pg_get_userbyid(c.relowner)
        FROM pg_class AS c
        WHERE c.oid = 'weather.copernicus_bra'::regclass
    ) <> 'dengueadmin' THEN
        RAISE EXCEPTION
            'weather.copernicus_bra owner changed unexpectedly after restoration';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'weather.copernicus_bra'::regclass
    ), ARRAY[]::text[]) <> expected_bra_acl THEN
        RAISE EXCEPTION
            'weather.copernicus_bra grants changed unexpectedly after restoration';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_copernicus'
          AND c.relname IN (
              'copernicus_arg',
              'copernicus_foz_do_iguacu',
              'copernicus_foz_do_iguacu_index_seq'
          )
    ) THEN
        RAISE EXCEPTION
            'archive_copernicus still contains one or more Copernicus relations after restoration';
    END IF;
END
$postcheck$;

COMMIT;
