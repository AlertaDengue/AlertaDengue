-- Restore the archived Ovitrampa tables back to the Municipio schema.
--
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DO $guard$
DECLARE
    owned_sequence_count integer;
    conflicting_targets text;
BEGIN
    IF to_regclass('archive_ovitrampa."Ovitrampa"') IS NULL
       OR to_regclass('archive_ovitrampa."Bairro"') IS NULL
       OR to_regclass('archive_ovitrampa."Localidade"') IS NULL THEN
        RAISE EXCEPTION
            'archive_ovitrampa does not contain the full Ovitrampa batch required for restoration';
    END IF;

    IF to_regclass('"Municipio"."Ovitrampa"') IS NOT NULL
       OR to_regclass('"Municipio"."Bairro"') IS NOT NULL
       OR to_regclass('"Municipio"."Localidade"') IS NOT NULL THEN
        RAISE EXCEPTION
            'Municipio already contains one or more Ovitrampa relations; restoration would conflict';
    END IF;

    SELECT string_agg(target_name, ', ')
    INTO conflicting_targets
    FROM (
        SELECT format('Municipio.%I', relname) AS target_name
        FROM (
            VALUES ('Ovitrampa_id_seq'), ('Bairro_id_seq')
        ) AS expected(relname)
        WHERE to_regclass(format('%I.%I', 'Municipio', relname)) IS NOT NULL
    ) AS conflicts;

    IF conflicting_targets IS NOT NULL THEN
        RAISE EXCEPTION
            'target Municipio sequence names already exist: %',
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
          AND tgt_ns.nspname = 'archive_ovitrampa'
          AND tgt.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
          AND src_ns.nspname <> 'archive_ovitrampa'
    ) THEN
        RAISE EXCEPTION
            'unexpected inbound foreign-key dependency blocks restoring archive_ovitrampa';
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
            'archive_ovitrampa."Ovitrampa"'::regclass,
            'archive_ovitrampa."Bairro"'::regclass,
            'archive_ovitrampa."Localidade"'::regclass
        )
          AND n.nspname <> 'archive_ovitrampa'
    ) THEN
        RAISE EXCEPTION
            'unexpected view or materialized-view dependency blocks restoring archive_ovitrampa';
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
    WHERE cls_ns.nspname = 'archive_ovitrampa'
      AND cls.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
      AND seq_ns.nspname = 'archive_ovitrampa';

    IF owned_sequence_count <> 2 THEN
        RAISE EXCEPTION
            'expected exactly 2 owned sequences in archive_ovitrampa before restoration; found %',
            owned_sequence_count;
    END IF;
END
$guard$;

ALTER TABLE archive_ovitrampa."Localidade" SET SCHEMA "Municipio";
ALTER TABLE archive_ovitrampa."Bairro" SET SCHEMA "Municipio";
ALTER TABLE archive_ovitrampa."Ovitrampa" SET SCHEMA "Municipio";

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
          AND cls.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
          AND seq_ns.nspname = 'archive_ovitrampa'
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
    owned_sequence_count integer;
BEGIN
    IF to_regclass('"Municipio"."Localidade"') IS NULL
       OR to_regclass('"Municipio"."Bairro"') IS NULL
       OR to_regclass('"Municipio"."Ovitrampa"') IS NULL THEN
        RAISE EXCEPTION
            'Municipio does not contain the expected Ovitrampa tables after restoration';
    END IF;

    IF (
        SELECT count(*)
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
          AND con.conname IN ('Bairro_Localidade', 'Ovitrampa_Localidade')
          AND src_ns.nspname = 'Municipio'
          AND tgt_ns.nspname = 'Municipio'
    ) <> 2 THEN
        RAISE EXCEPTION
            'expected Municipio foreign keys were not restored';
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
    WHERE cls_ns.nspname = 'Municipio'
      AND cls.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
      AND seq_ns.nspname = 'Municipio';

    IF owned_sequence_count <> 2 THEN
        RAISE EXCEPTION
            'expected exactly 2 owned sequences in Municipio after restoration; found %',
            owned_sequence_count;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_ovitrampa'
          AND c.relname IN ('Ovitrampa', 'Bairro', 'Localidade', 'Ovitrampa_id_seq', 'Bairro_id_seq')
    ) THEN
        RAISE EXCEPTION
            'archive_ovitrampa still contains Ovitrampa batch objects after restoration';
    END IF;
END
$postcheck$;

DO $cleanup$
BEGIN
    IF to_regnamespace('archive_ovitrampa') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM pg_class AS c
           JOIN pg_namespace AS n
             ON n.oid = c.relnamespace
           WHERE n.nspname = 'archive_ovitrampa'
             AND c.relkind IN ('r', 'S', 'v', 'm', 'f', 'p')
       ) THEN
        DROP SCHEMA archive_ovitrampa;
    END IF;
END
$cleanup$;

COMMIT;
