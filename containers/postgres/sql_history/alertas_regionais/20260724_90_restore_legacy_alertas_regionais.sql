-- Restore the archived regional-alert tables back to the active schemas.
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
    IF to_regclass('archive_alertas_regionais.alerta_regional_dengue') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_regional_chik') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_regional_zika') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_mrj') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_mrj_chik') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_mrj_zika') IS NULL THEN
        RAISE EXCEPTION
            'archive_alertas_regionais does not contain the full regional-alert batch required for restoration';
    END IF;

    IF to_regclass('"Dengue_global".alerta_regional_dengue') IS NOT NULL
       OR to_regclass('"Dengue_global".alerta_regional_chik') IS NOT NULL
       OR to_regclass('"Dengue_global".alerta_regional_zika') IS NOT NULL
       OR to_regclass('"Municipio".alerta_mrj') IS NOT NULL
       OR to_regclass('"Municipio".alerta_mrj_chik') IS NOT NULL
       OR to_regclass('"Municipio".alerta_mrj_zika') IS NOT NULL THEN
        RAISE EXCEPTION
            'active schemas already contain one or more regional-alert relations; restoration would conflict';
    END IF;

    IF to_regclass('"Dengue_global"."regional_saude"') IS NULL THEN
        RAISE EXCEPTION
            '"Dengue_global"."regional_saude" must remain active during restoration';
    END IF;

    SELECT string_agg(target_name, ', ')
    INTO conflicting_targets
    FROM (
        SELECT format('%I.%I', target_schema, relname) AS target_name
        FROM (
            VALUES
                ('Dengue_global', 'alerta_regional_dengue_id_seq'),
                ('Dengue_global', 'alerta_regional_chik_id_seq'),
                ('Dengue_global', 'alerta_regional_zika_id_seq'),
                ('Municipio', 'alerta_mrj_id_seq'),
                ('Municipio', 'alerta_mrj_chik_id_seq'),
                ('Municipio', 'alerta_mrj_zika_id_seq')
        ) AS expected(target_schema, relname)
        WHERE to_regclass(format('%I.%I', target_schema, relname)) IS NOT NULL
    ) AS conflicts;

    IF conflicting_targets IS NOT NULL THEN
        RAISE EXCEPTION
            'target sequence names already exist in active schemas: %',
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
          AND tgt_ns.nspname = 'archive_alertas_regionais'
          AND tgt.relname IN (
              'alerta_regional_dengue',
              'alerta_regional_chik',
              'alerta_regional_zika',
              'alerta_mrj',
              'alerta_mrj_chik',
              'alerta_mrj_zika'
          )
          AND src_ns.nspname <> 'archive_alertas_regionais'
    ) THEN
        RAISE EXCEPTION
            'unexpected inbound foreign-key dependency blocks restoring archive_alertas_regionais';
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
            'archive_alertas_regionais.alerta_regional_dengue'::regclass,
            'archive_alertas_regionais.alerta_regional_chik'::regclass,
            'archive_alertas_regionais.alerta_regional_zika'::regclass,
            'archive_alertas_regionais.alerta_mrj'::regclass,
            'archive_alertas_regionais.alerta_mrj_chik'::regclass,
            'archive_alertas_regionais.alerta_mrj_zika'::regclass
        )
          AND n.nspname <> 'archive_alertas_regionais'
    ) THEN
        RAISE EXCEPTION
            'unexpected view or materialized-view dependency blocks restoring archive_alertas_regionais';
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
            'expected exactly 6 owned sequences in archive_alertas_regionais before restoration; found %',
            owned_sequence_count;
    END IF;
END
$guard$;

ALTER TABLE archive_alertas_regionais.alerta_regional_dengue SET SCHEMA "Dengue_global";
ALTER TABLE archive_alertas_regionais.alerta_regional_chik SET SCHEMA "Dengue_global";
ALTER TABLE archive_alertas_regionais.alerta_regional_zika SET SCHEMA "Dengue_global";
ALTER TABLE archive_alertas_regionais.alerta_mrj SET SCHEMA "Municipio";
ALTER TABLE archive_alertas_regionais.alerta_mrj_chik SET SCHEMA "Municipio";
ALTER TABLE archive_alertas_regionais.alerta_mrj_zika SET SCHEMA "Municipio";

DO $move_sequences$
DECLARE
    owned_sequence record;
BEGIN
    FOR owned_sequence IN
        SELECT cls.relname AS table_name,
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
          AND seq_ns.nspname = 'archive_alertas_regionais'
        ORDER BY seq.relname
    LOOP
        IF owned_sequence.table_name IN (
            'alerta_regional_dengue',
            'alerta_regional_chik',
            'alerta_regional_zika'
        ) THEN
            EXECUTE format(
                'ALTER SEQUENCE %I.%I SET SCHEMA "Dengue_global"',
                owned_sequence.sequence_schema,
                owned_sequence.sequence_name
            );
        ELSE
            EXECUTE format(
                'ALTER SEQUENCE %I.%I SET SCHEMA "Municipio"',
                owned_sequence.sequence_schema,
                owned_sequence.sequence_name
            );
        END IF;
    END LOOP;
END
$move_sequences$;

DO $postcheck$
DECLARE
    owned_sequence_count integer;
BEGIN
    IF to_regclass('"Dengue_global".alerta_regional_dengue') IS NULL
       OR to_regclass('"Dengue_global".alerta_regional_chik') IS NULL
       OR to_regclass('"Dengue_global".alerta_regional_zika') IS NULL
       OR to_regclass('"Municipio".alerta_mrj') IS NULL
       OR to_regclass('"Municipio".alerta_mrj_chik') IS NULL
       OR to_regclass('"Municipio".alerta_mrj_zika') IS NULL THEN
        RAISE EXCEPTION
            'active schemas do not contain the expected regional-alert tables after restoration';
    END IF;

    IF to_regclass('"Dengue_global"."regional_saude"') IS NULL THEN
        RAISE EXCEPTION
            '"Dengue_global"."regional_saude" disappeared during restoration';
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
            'expected Dengue_global regional foreign keys were not restored';
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

    IF owned_sequence_count <> 6 THEN
        RAISE EXCEPTION
            'expected exactly 6 owned sequences in active schemas after restoration; found %',
            owned_sequence_count;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND c.relname IN (
              'alerta_regional_dengue',
              'alerta_regional_chik',
              'alerta_regional_zika',
              'alerta_mrj',
              'alerta_mrj_chik',
              'alerta_mrj_zika',
              'alerta_regional_dengue_id_seq',
              'alerta_regional_chik_id_seq',
              'alerta_regional_zika_id_seq',
              'alerta_mrj_id_seq',
              'alerta_mrj_chik_id_seq',
              'alerta_mrj_zika_id_seq'
          )
    ) THEN
        RAISE EXCEPTION
            'archive_alertas_regionais still contains regional-alert batch objects after restoration';
    END IF;
END
$postcheck$;

DO $cleanup$
BEGIN
    IF to_regnamespace('archive_alertas_regionais') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM pg_class AS c
           JOIN pg_namespace AS n
             ON n.oid = c.relnamespace
           WHERE n.nspname = 'archive_alertas_regionais'
             AND c.relkind IN ('r', 'S', 'v', 'm', 'f', 'p')
       ) THEN
        DROP SCHEMA archive_alertas_regionais;
    END IF;
END
$cleanup$;

COMMIT;
