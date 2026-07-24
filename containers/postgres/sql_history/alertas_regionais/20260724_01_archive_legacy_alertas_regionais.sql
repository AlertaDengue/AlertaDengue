-- Archive the legacy regional-alert tables by moving them into
-- archive_alertas_regionais.
--
-- Run as the database owner, or as a role that owns the affected relations.
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DO $guard$
DECLARE
    expected_owned_sequence_count integer := 6;
    owned_sequence_count integer;
    unexpected_relation_types text;
    conflicting_targets text;
BEGIN
    IF to_regnamespace('archive_alertas_regionais') IS NOT NULL THEN
        RAISE EXCEPTION
            'archive_alertas_regionais already exists; review the existing archive before rerunning';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE (n.nspname = 'Dengue_global'
               AND c.relname IN (
                   'alerta_regional_dengue',
                   'alerta_regional_chik',
                   'alerta_regional_zika'
               ))
           OR (n.nspname = 'Municipio'
               AND c.relname IN (
                   'alerta_mrj',
                   'alerta_mrj_chik',
                   'alerta_mrj_zika'
               ))
    ) <> 6 THEN
        RAISE EXCEPTION
            'expected all six legacy regional-alert tables to exist in Dengue_global and Municipio';
    END IF;

    IF to_regclass('"Dengue_global"."regional_saude"') IS NULL THEN
        RAISE EXCEPTION
            '"Dengue_global"."regional_saude" must remain active and present';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Dengue_global'
          AND c.relname = 'regional_saude'
          AND c.relkind <> 'r'
    ) THEN
        RAISE EXCEPTION
            '"Dengue_global"."regional_saude" must remain an ordinary table';
    END IF;

    SELECT string_agg(format('%I.%I(%s)', n.nspname, c.relname, c.relkind), ', ')
    INTO unexpected_relation_types
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE (
            (
                n.nspname = 'Dengue_global'
                AND c.relname IN (
                    'alerta_regional_dengue',
                    'alerta_regional_chik',
                    'alerta_regional_zika'
                )
            )
         OR (
                n.nspname = 'Municipio'
                AND c.relname IN ('alerta_mrj', 'alerta_mrj_chik', 'alerta_mrj_zika')
            )
          )
      AND c.relkind <> 'r';

    IF unexpected_relation_types IS NOT NULL THEN
        RAISE EXCEPTION
            'expected ordinary tables only; found %',
            unexpected_relation_types;
    END IF;

    SELECT string_agg(target_name, ', ')
    INTO conflicting_targets
    FROM (
        SELECT format('archive_alertas_regionais.%I', relname) AS target_name
        FROM (
            VALUES
                ('alerta_regional_dengue'),
                ('alerta_regional_chik'),
                ('alerta_regional_zika'),
                ('alerta_mrj'),
                ('alerta_mrj_chik'),
                ('alerta_mrj_zika'),
                ('alerta_regional_dengue_id_seq'),
                ('alerta_regional_chik_id_seq'),
                ('alerta_regional_zika_id_seq'),
                ('alerta_mrj_id_seq'),
                ('alerta_mrj_chik_id_seq'),
                ('alerta_mrj_zika_id_seq')
        ) AS expected(relname)
        WHERE to_regclass(format('archive_alertas_regionais.%I', relname)) IS NOT NULL
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
          AND (
                (tgt_ns.nspname = 'Dengue_global'
                 AND tgt.relname IN (
                     'alerta_regional_dengue',
                     'alerta_regional_chik',
                     'alerta_regional_zika'
                 ))
             OR (tgt_ns.nspname = 'Municipio'
                 AND tgt.relname IN ('alerta_mrj', 'alerta_mrj_chik', 'alerta_mrj_zika'))
          )
          AND NOT (
                src_ns.nspname = 'Dengue_global'
                AND src.relname IN (
                    'alerta_regional_dengue',
                    'alerta_regional_chik',
                    'alerta_regional_zika'
                )
                AND tgt_ns.nspname = 'Dengue_global'
                AND tgt.relname = 'regional'
          )
    ) THEN
        RAISE EXCEPTION
            'unexpected inbound foreign-key dependency found outside the approved regional-alert batch';
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
          AND src_ns.nspname = 'Dengue_global'
          AND src.relname IN (
              'alerta_regional_dengue',
              'alerta_regional_chik',
              'alerta_regional_zika'
          )
          AND tgt_ns.nspname = 'Dengue_global'
          AND tgt.relname = 'regional'
    ) <> 3 THEN
        RAISE EXCEPTION
            'expected exactly 3 outbound regional foreign keys for the approved regional-alert batch';
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
          AND (
                (src_ns.nspname = 'Dengue_global'
                 AND src.relname IN (
                     'alerta_regional_dengue',
                     'alerta_regional_chik',
                     'alerta_regional_zika'
                 ))
             OR (src_ns.nspname = 'Municipio'
                 AND src.relname IN ('alerta_mrj', 'alerta_mrj_chik', 'alerta_mrj_zika'))
          )
          AND NOT (
                src_ns.nspname = 'Dengue_global'
                AND src.relname IN (
                    'alerta_regional_dengue',
                    'alerta_regional_chik',
                    'alerta_regional_zika'
                )
                AND tgt_ns.nspname = 'Dengue_global'
                AND tgt.relname = 'regional'
          )
    ) THEN
        RAISE EXCEPTION
            'unexpected outbound foreign-key dependency found outside the approved regional-alert batch';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_rewrite AS r
        JOIN pg_class AS c
          ON c.oid = r.ev_class
        JOIN pg_depend AS d
          ON d.objid = r.oid
        WHERE d.refobjid IN (
            '"Dengue_global".alerta_regional_dengue'::regclass,
            '"Dengue_global".alerta_regional_chik'::regclass,
            '"Dengue_global".alerta_regional_zika'::regclass,
            '"Municipio".alerta_mrj'::regclass,
            '"Municipio".alerta_mrj_chik'::regclass,
            '"Municipio".alerta_mrj_zika'::regclass
        )
    ) THEN
        RAISE EXCEPTION
            'unexpected view or materialized-view dependency found for the approved regional-alert batch';
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
    WHERE (
            (
                cls_ns.nspname = 'Dengue_global'
                AND cls.relname IN (
                    'alerta_regional_dengue',
                    'alerta_regional_chik',
                    'alerta_regional_zika'
                )
            )
         OR (
                cls_ns.nspname = 'Municipio'
                AND cls.relname IN ('alerta_mrj', 'alerta_mrj_chik', 'alerta_mrj_zika')
            )
          )
      AND seq_ns.nspname IN ('Dengue_global', 'Municipio');

    IF owned_sequence_count <> expected_owned_sequence_count THEN
        RAISE EXCEPTION
            'expected exactly % owned sequences for the regional-alert batch; found %',
            expected_owned_sequence_count,
            owned_sequence_count;
    END IF;
END
$guard$;

CREATE SCHEMA archive_alertas_regionais;
REVOKE ALL ON SCHEMA archive_alertas_regionais FROM PUBLIC;

ALTER TABLE "Dengue_global".alerta_regional_dengue SET SCHEMA archive_alertas_regionais;
ALTER TABLE "Dengue_global".alerta_regional_chik SET SCHEMA archive_alertas_regionais;
ALTER TABLE "Dengue_global".alerta_regional_zika SET SCHEMA archive_alertas_regionais;
ALTER TABLE "Municipio".alerta_mrj SET SCHEMA archive_alertas_regionais;
ALTER TABLE "Municipio".alerta_mrj_chik SET SCHEMA archive_alertas_regionais;
ALTER TABLE "Municipio".alerta_mrj_zika SET SCHEMA archive_alertas_regionais;

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
        WHERE cls_ns.nspname = 'archive_alertas_regionais'
          AND cls.relname IN (
              'alerta_regional_dengue',
              'alerta_regional_chik',
              'alerta_regional_zika',
              'alerta_mrj',
              'alerta_mrj_chik',
              'alerta_mrj_zika'
          )
          AND seq_ns.nspname IN ('Dengue_global', 'Municipio')
        ORDER BY seq.relname
    LOOP
        EXECUTE format(
            'ALTER SEQUENCE %I.%I SET SCHEMA archive_alertas_regionais',
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
    IF to_regclass('archive_alertas_regionais.alerta_regional_dengue') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_regional_chik') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_regional_zika') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_mrj') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_mrj_chik') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_mrj_zika') IS NULL THEN
        RAISE EXCEPTION
            'archive_alertas_regionais does not contain the expected tables after the move';
    END IF;

    IF to_regclass('"Dengue_global".alerta_regional_dengue') IS NOT NULL
       OR to_regclass('"Dengue_global".alerta_regional_chik') IS NOT NULL
       OR to_regclass('"Dengue_global".alerta_regional_zika') IS NOT NULL
       OR to_regclass('"Municipio".alerta_mrj') IS NOT NULL
       OR to_regclass('"Municipio".alerta_mrj_chik') IS NOT NULL
       OR to_regclass('"Municipio".alerta_mrj_zika') IS NOT NULL THEN
        RAISE EXCEPTION
            'one or more legacy regional-alert tables remain in active schemas after the move';
    END IF;

    IF to_regclass('"Dengue_global"."regional_saude"') IS NULL THEN
        RAISE EXCEPTION
            '"Dengue_global"."regional_saude" moved or disappeared unexpectedly';
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
          AND src_ns.nspname = 'archive_alertas_regionais'
          AND src.relname IN (
              'alerta_regional_dengue',
              'alerta_regional_chik',
              'alerta_regional_zika'
          )
          AND tgt_ns.nspname = 'Dengue_global'
          AND tgt.relname = 'regional'
    ) <> 3 THEN
        RAISE EXCEPTION
            'expected regional foreign keys were not preserved after archiving';
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
    WHERE cls_ns.nspname = 'archive_alertas_regionais'
      AND cls.relname IN (
          'alerta_regional_dengue',
          'alerta_regional_chik',
          'alerta_regional_zika',
          'alerta_mrj',
          'alerta_mrj_chik',
          'alerta_mrj_zika'
      )
      AND seq_ns.nspname = 'archive_alertas_regionais';

    IF owned_sequence_count <> 6 THEN
        RAISE EXCEPTION
            'expected exactly 6 owned sequences inside archive_alertas_regionais after the move; found %',
            owned_sequence_count;
    END IF;
END
$postcheck$;

COMMIT;
