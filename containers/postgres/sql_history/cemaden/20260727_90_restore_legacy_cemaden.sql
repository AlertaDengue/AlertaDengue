-- Restore the archived CEMADEN tables back to the Municipio schema.
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
    IF to_regclass('archive_cemaden."Clima_cemaden"') IS NULL
       OR to_regclass('archive_cemaden."Estacao_cemaden"') IS NULL THEN
        RAISE EXCEPTION
            'archive_cemaden does not contain the full CEMADEN batch required for restoration';
    END IF;

    IF to_regclass('"Municipio"."Clima_cemaden"') IS NOT NULL
       OR to_regclass('"Municipio"."Estacao_cemaden"') IS NOT NULL THEN
        RAISE EXCEPTION
            'Municipio already contains one or more CEMADEN relations; restoration would conflict';
    END IF;

    SELECT string_agg(target_name, ', ')
    INTO conflicting_targets
    FROM (
        SELECT format('Municipio.%I', relname) AS target_name
        FROM (
            VALUES ('Clima_cemaden_id_seq')
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
          AND tgt_ns.nspname = 'archive_cemaden'
          AND tgt.relname IN ('Clima_cemaden', 'Estacao_cemaden')
          AND src_ns.nspname <> 'archive_cemaden'
    ) THEN
        RAISE EXCEPTION
            'unexpected inbound foreign-key dependency blocks restoring archive_cemaden';
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
            'archive_cemaden."Clima_cemaden"'::regclass,
            'archive_cemaden."Estacao_cemaden"'::regclass
        )
          AND n.nspname <> 'archive_cemaden'
    ) THEN
        RAISE EXCEPTION
            'unexpected view or materialized-view dependency blocks restoring archive_cemaden';
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
    WHERE cls_ns.nspname = 'archive_cemaden'
      AND cls.relname IN ('Clima_cemaden', 'Estacao_cemaden')
      AND seq_ns.nspname = 'archive_cemaden';

    IF owned_sequence_count <> 1 THEN
        RAISE EXCEPTION
            'expected exactly 1 owned sequence in archive_cemaden before restoration; found %',
            owned_sequence_count;
    END IF;
END
$guard$;

ALTER TABLE archive_cemaden."Estacao_cemaden" SET SCHEMA "Municipio";
ALTER TABLE archive_cemaden."Clima_cemaden" SET SCHEMA "Municipio";

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
          AND cls.relname IN ('Clima_cemaden', 'Estacao_cemaden')
          AND seq_ns.nspname = 'archive_cemaden'
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
    IF to_regclass('"Municipio"."Clima_cemaden"') IS NULL
       OR to_regclass('"Municipio"."Estacao_cemaden"') IS NULL THEN
        RAISE EXCEPTION
            'Municipio does not contain the expected CEMADEN tables after restoration';
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
      AND cls.relname IN ('Clima_cemaden', 'Estacao_cemaden')
      AND seq_ns.nspname = 'Municipio';

    IF owned_sequence_count <> 1 THEN
        RAISE EXCEPTION
            'expected exactly 1 owned sequence in Municipio after restoration; found %',
            owned_sequence_count;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_cemaden'
          AND c.relname IN ('Clima_cemaden', 'Estacao_cemaden', 'Clima_cemaden_id_seq')
    ) THEN
        RAISE EXCEPTION
            'archive_cemaden still contains one or more CEMADEN relations after restoration';
    END IF;
END
$postcheck$;

COMMIT;
