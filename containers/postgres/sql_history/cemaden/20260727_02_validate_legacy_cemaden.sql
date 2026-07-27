-- Validate the archive_cemaden batch after running 20260727_01.
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
BEGIN
    IF to_regclass('"Municipio"."Clima_cemaden"') IS NOT NULL
       OR to_regclass('"Municipio"."Estacao_cemaden"') IS NOT NULL THEN
        RAISE EXCEPTION
            'Municipio still contains one or more archived CEMADEN relations';
    END IF;

    IF to_regclass('archive_cemaden."Clima_cemaden"') IS NULL
       OR to_regclass('archive_cemaden."Estacao_cemaden"') IS NULL THEN
        RAISE EXCEPTION
            'archive_cemaden is missing one or more expected tables';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_cemaden'
          AND c.relname IN ('Clima_cemaden', 'Estacao_cemaden')
          AND c.relkind <> 'r'
    ) THEN
        RAISE EXCEPTION
            'archive_cemaden contains an unexpected relation type for the CEMADEN batch';
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
            'unexpected inbound foreign-key dependency remains on archive_cemaden';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_constraint AS con
        JOIN pg_class AS src
          ON src.oid = con.conrelid
        JOIN pg_namespace AS src_ns
          ON src_ns.oid = src.relnamespace
        WHERE con.contype = 'f'
          AND src_ns.nspname = 'archive_cemaden'
          AND src.relname IN ('Clima_cemaden', 'Estacao_cemaden')
    ) THEN
        RAISE EXCEPTION
            'unexpected foreign-key dependency remains inside archive_cemaden';
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
            'unexpected external view dependency remains on archive_cemaden';
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
        WHERE cls_ns.nspname = 'archive_cemaden'
          AND cls.relname IN ('Clima_cemaden', 'Estacao_cemaden')
          AND seq_ns.nspname = 'archive_cemaden'
    ) <> 1 THEN
        RAISE EXCEPTION
            'expected exactly 1 owned sequence in archive_cemaden';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_cemaden'
          AND c.relname IN ('Clima_cemaden', 'Estacao_cemaden')
          AND pg_get_userbyid(c.relowner) <> 'administrador'
    ) THEN
        RAISE EXCEPTION
            'one or more archived CEMADEN tables changed owner unexpectedly';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_cemaden'
          AND c.relname IN ('Clima_cemaden', 'Estacao_cemaden')
          AND COALESCE(c.relacl::text[], ARRAY[]::text[]) <> expected_table_acl
    ) THEN
        RAISE EXCEPTION
            'one or more archived CEMADEN table grants changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_cemaden'
          AND c.relname = 'Clima_cemaden_id_seq'
    ), ARRAY[]::text[]) <> expected_sequence_acl THEN
        RAISE EXCEPTION
            'archive_cemaden.Clima_cemaden_id_seq grants changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT obj_description(c.oid, 'pg_class')
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_cemaden'
          AND c.relname = 'Clima_cemaden'
    ), '') <> 'dados de clima - CEMADEN' THEN
        RAISE EXCEPTION
            'archive_cemaden.Clima_cemaden comment changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT obj_description(c.oid, 'pg_class')
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_cemaden'
          AND c.relname = 'Estacao_cemaden'
    ), '') <> 'Metadados da estação do cemaden' THEN
        RAISE EXCEPTION
            'archive_cemaden.Estacao_cemaden comment changed unexpectedly';
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
WHERE n.nspname IN ('Municipio', 'archive_cemaden')
  AND c.relname IN ('Clima_cemaden', 'Estacao_cemaden')
ORDER BY n.nspname, c.relname;

SELECT 'Clima_cemaden' AS object_name, COUNT(*) AS row_count
FROM archive_cemaden."Clima_cemaden"
UNION ALL
SELECT 'Estacao_cemaden', COUNT(*)
FROM archive_cemaden."Estacao_cemaden";

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
WHERE src_ns.nspname = 'archive_cemaden'
  AND src.relname IN ('Clima_cemaden', 'Estacao_cemaden')
ORDER BY src.relname, con.conname;

SELECT schemaname,
       tablename,
       indexname,
       indexdef
FROM pg_indexes
WHERE schemaname = 'archive_cemaden'
  AND tablename IN ('Clima_cemaden', 'Estacao_cemaden')
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
WHERE cls_ns.nspname = 'archive_cemaden'
  AND cls.relname IN ('Clima_cemaden', 'Estacao_cemaden')
ORDER BY cls.relname, att.attname;

COMMIT;
