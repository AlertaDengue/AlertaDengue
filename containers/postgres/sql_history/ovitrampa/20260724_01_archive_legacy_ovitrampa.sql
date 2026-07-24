-- Archive the legacy Ovitrampa tables by moving them into archive_ovitrampa.
--
-- Run as the database owner, or as a role that owns the affected relations.
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DO $guard$
DECLARE
    owned_sequence_count integer;
    unexpected_relation_types text;
    conflicting_targets text;
BEGIN
    IF to_regnamespace('archive_ovitrampa') IS NOT NULL THEN
        RAISE EXCEPTION
            'archive_ovitrampa already exists; review the existing archive before rerunning';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
    ) <> 3 THEN
        RAISE EXCEPTION
            'expected Municipio.Ovitrampa, Municipio.Bairro, and Municipio.Localidade to exist';
    END IF;

    SELECT string_agg(format('%I.%I(%s)', n.nspname, c.relname, c.relkind), ', ')
    INTO unexpected_relation_types
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = 'Municipio'
      AND c.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
      AND c.relkind <> 'r';

    IF unexpected_relation_types IS NOT NULL THEN
        RAISE EXCEPTION
            'expected ordinary tables only; found %',
            unexpected_relation_types;
    END IF;

    SELECT string_agg(target_name, ', ')
    INTO conflicting_targets
    FROM (
        SELECT format('archive_ovitrampa.%I', relname) AS target_name
        FROM (
            VALUES ('Ovitrampa'), ('Bairro'), ('Localidade'),
                   ('Ovitrampa_id_seq'), ('Bairro_id_seq')
        ) AS expected(relname)
        WHERE to_regclass(format('archive_ovitrampa.%I', relname)) IS NOT NULL
    ) AS conflicts;

    IF conflicting_targets IS NOT NULL THEN
        RAISE EXCEPTION
            'target archive objects already exist: %',
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
          AND tgt_ns.nspname = 'Municipio'
          AND tgt.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
          AND NOT (src_ns.nspname = 'Municipio' AND src.relname IN ('Ovitrampa', 'Bairro'))
    ) THEN
        RAISE EXCEPTION
            'unexpected inbound foreign-key dependency found outside the approved Ovitrampa batch';
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
          AND src_ns.nspname = 'Municipio'
          AND src.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
          AND NOT (tgt_ns.nspname = 'Municipio' AND tgt.relname = 'Localidade')
    ) THEN
        RAISE EXCEPTION
            'unexpected outbound foreign-key dependency found outside the approved Ovitrampa batch';
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
            '"Municipio"."Ovitrampa"'::regclass,
            '"Municipio"."Bairro"'::regclass,
            '"Municipio"."Localidade"'::regclass
        )
    ) THEN
        RAISE EXCEPTION
            'unexpected view or materialized-view dependency found for the approved Ovitrampa batch';
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
            'expected exactly 2 owned sequences for the Ovitrampa batch; found %',
            owned_sequence_count;
    END IF;
END
$guard$;

CREATE SCHEMA archive_ovitrampa;
REVOKE ALL ON SCHEMA archive_ovitrampa FROM PUBLIC;

ALTER TABLE "Municipio"."Localidade" SET SCHEMA archive_ovitrampa;
ALTER TABLE "Municipio"."Bairro" SET SCHEMA archive_ovitrampa;
ALTER TABLE "Municipio"."Ovitrampa" SET SCHEMA archive_ovitrampa;

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
        WHERE cls_ns.nspname = 'archive_ovitrampa'
          AND cls.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
          AND seq_ns.nspname = 'Municipio'
        ORDER BY seq.relname
    LOOP
        EXECUTE format(
            'ALTER SEQUENCE %I.%I SET SCHEMA archive_ovitrampa',
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
    IF to_regclass('archive_ovitrampa."Localidade"') IS NULL
       OR to_regclass('archive_ovitrampa."Bairro"') IS NULL
       OR to_regclass('archive_ovitrampa."Ovitrampa"') IS NULL THEN
        RAISE EXCEPTION
            'archive_ovitrampa does not contain the expected tables after the move';
    END IF;

    IF to_regclass('"Municipio"."Localidade"') IS NOT NULL
       OR to_regclass('"Municipio"."Bairro"') IS NOT NULL
       OR to_regclass('"Municipio"."Ovitrampa"') IS NOT NULL THEN
        RAISE EXCEPTION
            'Municipio still contains one or more archived Ovitrampa tables after the move';
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
          AND con.conname IN ('Bairro_Localidade', 'Ovitrampa_Localidade')
          AND (
              src_ns.nspname <> 'archive_ovitrampa'
              OR tgt_ns.nspname <> 'archive_ovitrampa'
          )
    ) THEN
        RAISE EXCEPTION
            'expected archive_ovitrampa foreign keys were not preserved inside archive_ovitrampa';
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
            'expected exactly 2 owned sequences inside archive_ovitrampa after the move; found %',
            owned_sequence_count;
    END IF;
END
$postcheck$;

COMMIT;
