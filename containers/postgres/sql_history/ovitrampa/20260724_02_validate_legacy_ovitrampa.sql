-- Validate the archive_ovitrampa batch after running 20260724_01.
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
    expected_ovitrampa_sequence_acl text[] := ARRAY[
        'administrador=rwU/administrador',
        'dengue=rU/administrador'
    ];
BEGIN
    IF to_regclass('"Municipio"."Ovitrampa"') IS NOT NULL
       OR to_regclass('"Municipio"."Bairro"') IS NOT NULL
       OR to_regclass('"Municipio"."Localidade"') IS NOT NULL THEN
        RAISE EXCEPTION
            'Municipio still contains one or more archived Ovitrampa relations';
    END IF;

    IF to_regclass('archive_ovitrampa."Ovitrampa"') IS NULL
       OR to_regclass('archive_ovitrampa."Bairro"') IS NULL
       OR to_regclass('archive_ovitrampa."Localidade"') IS NULL THEN
        RAISE EXCEPTION
            'archive_ovitrampa is missing one or more expected tables';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_ovitrampa'
          AND c.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
          AND c.relkind <> 'r'
    ) THEN
        RAISE EXCEPTION
            'archive_ovitrampa contains an unexpected relation type for the Ovitrampa batch';
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
          AND src_ns.nspname = 'archive_ovitrampa'
          AND tgt_ns.nspname = 'archive_ovitrampa'
    ) <> 2 THEN
        RAISE EXCEPTION
            'expected archive_ovitrampa foreign keys were not preserved';
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
            'unexpected inbound foreign-key dependency remains on archive_ovitrampa';
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
            'unexpected external view dependency remains on archive_ovitrampa';
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
        WHERE cls_ns.nspname = 'archive_ovitrampa'
          AND cls.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
          AND seq_ns.nspname = 'archive_ovitrampa'
    ) <> 2 THEN
        RAISE EXCEPTION
            'expected exactly 2 owned sequences in archive_ovitrampa';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_ovitrampa'
          AND c.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
          AND pg_get_userbyid(c.relowner) <> 'administrador'
    ) THEN
        RAISE EXCEPTION
            'one or more archived Ovitrampa tables changed owner unexpectedly';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_ovitrampa'
          AND c.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
          AND COALESCE(c.relacl::text[], ARRAY[]::text[]) <> expected_table_acl
    ) THEN
        RAISE EXCEPTION
            'one or more archived Ovitrampa table grants changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_ovitrampa'
          AND c.relname = 'Bairro_id_seq'
    ), ARRAY[]::text[]) <> ARRAY[]::text[] THEN
        RAISE EXCEPTION
            'archive_ovitrampa.Bairro_id_seq grants changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_ovitrampa'
          AND c.relname = 'Ovitrampa_id_seq'
    ), ARRAY[]::text[]) <> expected_ovitrampa_sequence_acl THEN
        RAISE EXCEPTION
            'archive_ovitrampa.Ovitrampa_id_seq grants changed unexpectedly';
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
WHERE n.nspname IN ('Municipio', 'archive_ovitrampa')
  AND c.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
ORDER BY n.nspname, c.relname;

SELECT 'Ovitrampa' AS object_name, COUNT(*) AS row_count
FROM archive_ovitrampa."Ovitrampa"
UNION ALL
SELECT 'Bairro', COUNT(*)
FROM archive_ovitrampa."Bairro"
UNION ALL
SELECT 'Localidade', COUNT(*)
FROM archive_ovitrampa."Localidade";

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
WHERE src_ns.nspname = 'archive_ovitrampa'
  AND src.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
ORDER BY src.relname, con.conname;

SELECT schemaname,
       tablename,
       indexname,
       indexdef
FROM pg_indexes
WHERE schemaname = 'archive_ovitrampa'
  AND tablename IN ('Ovitrampa', 'Bairro', 'Localidade')
ORDER BY tablename, indexname;

SELECT cls.relname AS table_name,
       att.attname AS column_name,
       pg_get_expr(def.adbin, def.adrelid) AS column_default
FROM pg_class AS cls
JOIN pg_namespace AS cls_ns
  ON cls_ns.oid = cls.relnamespace
JOIN pg_attribute AS att
  ON att.attrelid = cls.oid
 AND att.attnum > 0
 AND NOT att.attisdropped
LEFT JOIN pg_attrdef AS def
  ON def.adrelid = cls.oid
 AND def.adnum = att.attnum
WHERE cls_ns.nspname = 'archive_ovitrampa'
  AND cls.relname IN ('Ovitrampa', 'Bairro', 'Localidade')
  AND att.attname = 'id'
ORDER BY cls.relname;

SELECT cls.relname AS table_name,
       att.attname AS column_name,
       seq_ns.nspname AS sequence_schema,
       seq.relname AS sequence_name,
       pg_get_userbyid(seq.relowner) AS sequence_owner,
       seq.relacl AS sequence_acl
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
ORDER BY cls.relname, att.attname;

SELECT grantee,
       table_name,
       privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'archive_ovitrampa'
  AND table_name IN ('Ovitrampa', 'Bairro', 'Localidade')
ORDER BY table_name, grantee, privilege_type;

COMMIT;
