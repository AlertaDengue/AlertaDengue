-- Validate the archive_alertas_regionais batch after running 20260724_01.
--
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DO $guard$
DECLARE
    expected_dengue_global_table_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'Read_only=r/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'analista=r/dengueadmin'
    ];
    expected_mrj_table_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'dengue=arwdDxt/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'analista=r/dengueadmin'
    ];
    expected_mrj_chik_table_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'Dengue=arwDxt/dengueadmin',
        'dengue=arwdDxt/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'analista=r/dengueadmin'
    ];
    expected_mrj_zika_table_acl text[] := ARRAY[
        'postgres=arwdDxt/postgres',
        'dengue=arwdDxt/postgres',
        'infodenguedev=r/postgres',
        'analista=r/postgres'
    ];
    expected_dengue_global_sequence_acl text[] := ARRAY[
        'dengueadmin=rwU/dengueadmin',
        'Read_only=r/dengueadmin'
    ];
    expected_mrj_sequence_acl text[] := ARRAY[
        'dengueadmin=rwU/dengueadmin',
        'dengue=rU/dengueadmin'
    ];
    expected_mrj_zika_sequence_acl text[] := ARRAY[
        'postgres=rwU/postgres',
        'dengue=rU/postgres'
    ];
BEGIN
    IF to_regclass('"Dengue_global".alerta_regional_dengue') IS NOT NULL
       OR to_regclass('"Dengue_global".alerta_regional_chik') IS NOT NULL
       OR to_regclass('"Dengue_global".alerta_regional_zika') IS NOT NULL
       OR to_regclass('"Municipio".alerta_mrj') IS NOT NULL
       OR to_regclass('"Municipio".alerta_mrj_chik') IS NOT NULL
       OR to_regclass('"Municipio".alerta_mrj_zika') IS NOT NULL THEN
        RAISE EXCEPTION
            'active schemas still contain one or more archived regional-alert relations';
    END IF;

    IF to_regclass('archive_alertas_regionais.alerta_regional_dengue') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_regional_chik') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_regional_zika') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_mrj') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_mrj_chik') IS NULL
       OR to_regclass('archive_alertas_regionais.alerta_mrj_zika') IS NULL THEN
        RAISE EXCEPTION
            'archive_alertas_regionais is missing one or more expected tables';
    END IF;

    IF to_regclass('"Dengue_global"."regional_saude"') IS NULL THEN
        RAISE EXCEPTION
            '"Dengue_global"."regional_saude" moved or disappeared';
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
              'alerta_mrj_zika'
          )
          AND c.relkind <> 'r'
    ) THEN
        RAISE EXCEPTION
            'archive_alertas_regionais contains an unexpected relation type for the regional-alert batch';
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
            'expected archive_alertas_regionais foreign keys to Dengue_global.regional were not preserved';
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
            'unexpected inbound foreign-key dependency remains on archive_alertas_regionais';
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
            'unexpected external view dependency remains on archive_alertas_regionais';
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
        WHERE cls_ns.nspname = 'archive_alertas_regionais'
          AND cls.relname IN (
              'alerta_regional_dengue',
              'alerta_regional_chik',
              'alerta_regional_zika',
              'alerta_mrj',
              'alerta_mrj_chik',
              'alerta_mrj_zika'
          )
          AND seq_ns.nspname = 'archive_alertas_regionais'
    ) <> 6 THEN
        RAISE EXCEPTION
            'expected exactly 6 owned sequences in archive_alertas_regionais';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND (
                (c.relname IN (
                    'alerta_regional_dengue',
                    'alerta_regional_chik',
                    'alerta_regional_zika'
                ) AND pg_get_userbyid(c.relowner) <> 'dengueadmin')
             OR (c.relname IN ('alerta_mrj', 'alerta_mrj_chik')
                 AND pg_get_userbyid(c.relowner) <> 'dengueadmin')
             OR (c.relname = 'alerta_mrj_zika'
                 AND pg_get_userbyid(c.relowner) <> 'postgres')
          )
    ) THEN
        RAISE EXCEPTION
            'one or more archived regional-alert tables changed owner unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND c.relname IN (
              'alerta_regional_dengue',
              'alerta_regional_chik',
              'alerta_regional_zika'
          )
        ORDER BY c.relname
        LIMIT 1
    ), ARRAY[]::text[]) <> expected_dengue_global_table_acl THEN
        RAISE EXCEPTION
            'archive_alertas_regionais regional-alert table grants changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND c.relname = 'alerta_mrj'
    ), ARRAY[]::text[]) <> expected_mrj_table_acl THEN
        RAISE EXCEPTION
            'archive_alertas_regionais.alerta_mrj grants changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND c.relname = 'alerta_mrj_chik'
    ), ARRAY[]::text[]) <> expected_mrj_chik_table_acl THEN
        RAISE EXCEPTION
            'archive_alertas_regionais.alerta_mrj_chik grants changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND c.relname = 'alerta_mrj_zika'
    ), ARRAY[]::text[]) <> expected_mrj_zika_table_acl THEN
        RAISE EXCEPTION
            'archive_alertas_regionais.alerta_mrj_zika grants changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND c.relname = 'alerta_regional_dengue_id_seq'
    ), ARRAY[]::text[]) <> expected_dengue_global_sequence_acl
       OR COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND c.relname = 'alerta_regional_chik_id_seq'
    ), ARRAY[]::text[]) <> expected_dengue_global_sequence_acl
       OR COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND c.relname = 'alerta_regional_zika_id_seq'
    ), ARRAY[]::text[]) <> expected_dengue_global_sequence_acl THEN
        RAISE EXCEPTION
            'one or more archived regional-alert sequences changed grants unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND c.relname = 'alerta_mrj_id_seq'
    ), ARRAY[]::text[]) <> expected_mrj_sequence_acl
       OR COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND c.relname = 'alerta_mrj_chik_id_seq'
    ), ARRAY[]::text[]) <> expected_mrj_sequence_acl THEN
        RAISE EXCEPTION
            'archive_alertas_regionais alerta_mrj sequences changed grants unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_alertas_regionais'
          AND c.relname = 'alerta_mrj_zika_id_seq'
    ), ARRAY[]::text[]) <> expected_mrj_zika_sequence_acl THEN
        RAISE EXCEPTION
            'archive_alertas_regionais.alerta_mrj_zika_id_seq grants changed unexpectedly';
    END IF;
END
$guard$;

SELECT n.nspname AS schema_name,
       c.relname AS object_name,
       c.relkind,
       pg_get_userbyid(c.relowner) AS owner,
       pg_total_relation_size(c.oid) AS total_size,
       obj_description(c.oid, 'pg_class') AS object_comment
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE (
        n.nspname = 'archive_alertas_regionais'
        AND c.relname IN (
            'alerta_regional_dengue',
            'alerta_regional_chik',
            'alerta_regional_zika',
            'alerta_mrj',
            'alerta_mrj_chik',
            'alerta_mrj_zika'
        )
      )
   OR (n.nspname = 'Dengue_global' AND c.relname = 'regional_saude')
ORDER BY n.nspname, c.relname;

SELECT 'alerta_regional_dengue' AS object_name, COUNT(*) AS row_count
FROM archive_alertas_regionais.alerta_regional_dengue
UNION ALL
SELECT 'alerta_regional_chik', COUNT(*)
FROM archive_alertas_regionais.alerta_regional_chik
UNION ALL
SELECT 'alerta_regional_zika', COUNT(*)
FROM archive_alertas_regionais.alerta_regional_zika
UNION ALL
SELECT 'alerta_mrj', COUNT(*)
FROM archive_alertas_regionais.alerta_mrj
UNION ALL
SELECT 'alerta_mrj_chik', COUNT(*)
FROM archive_alertas_regionais.alerta_mrj_chik
UNION ALL
SELECT 'alerta_mrj_zika', COUNT(*)
FROM archive_alertas_regionais.alerta_mrj_zika
UNION ALL
SELECT 'regional_saude_active', COUNT(*)
FROM "Dengue_global"."regional_saude";

SELECT con.conname,
       con.contype,
       src_ns.nspname AS src_schema,
       src.relname AS src_table,
       tgt_ns.nspname AS tgt_schema,
       tgt.relname AS tgt_table,
       pg_get_constraintdef(con.oid) AS constraint_definition
FROM pg_constraint AS con
JOIN pg_class AS src
  ON src.oid = con.conrelid
JOIN pg_namespace AS src_ns
  ON src_ns.oid = src.relnamespace
LEFT JOIN pg_class AS tgt
  ON tgt.oid = con.confrelid
LEFT JOIN pg_namespace AS tgt_ns
  ON tgt_ns.oid = tgt.relnamespace
WHERE src_ns.nspname = 'archive_alertas_regionais'
  AND src.relname IN (
      'alerta_regional_dengue',
      'alerta_regional_chik',
      'alerta_regional_zika',
      'alerta_mrj',
      'alerta_mrj_chik',
      'alerta_mrj_zika'
  )
ORDER BY src.relname, con.conname;

SELECT schemaname,
       tablename,
       indexname,
       indexdef
FROM pg_indexes
WHERE schemaname = 'archive_alertas_regionais'
  AND tablename IN (
      'alerta_regional_dengue',
      'alerta_regional_chik',
      'alerta_regional_zika',
      'alerta_mrj',
      'alerta_mrj_chik',
      'alerta_mrj_zika'
  )
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
WHERE cls_ns.nspname = 'archive_alertas_regionais'
  AND cls.relname IN (
      'alerta_regional_dengue',
      'alerta_regional_chik',
      'alerta_regional_zika',
      'alerta_mrj',
      'alerta_mrj_chik',
      'alerta_mrj_zika'
  )
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
WHERE cls_ns.nspname = 'archive_alertas_regionais'
  AND cls.relname IN (
      'alerta_regional_dengue',
      'alerta_regional_chik',
      'alerta_regional_zika',
      'alerta_mrj',
      'alerta_mrj_chik',
      'alerta_mrj_zika'
  )
ORDER BY cls.relname, att.attname;

SELECT grantee,
       table_name,
       privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'archive_alertas_regionais'
  AND table_name IN (
      'alerta_regional_dengue',
      'alerta_regional_chik',
      'alerta_regional_zika',
      'alerta_mrj',
      'alerta_mrj_chik',
      'alerta_mrj_zika'
  )
ORDER BY table_name, grantee, privilege_type;

SELECT con.contype,
       src_ns.nspname AS src_schema,
       src.relname AS src_table,
       tgt_ns.nspname AS tgt_schema,
       tgt.relname AS tgt_table,
       con.conname,
       pg_get_constraintdef(con.oid) AS constraint_definition
FROM pg_constraint AS con
JOIN pg_class AS src
  ON src.oid = con.conrelid
JOIN pg_namespace AS src_ns
  ON src_ns.oid = src.relnamespace
JOIN pg_class AS tgt
  ON tgt.oid = con.confrelid
JOIN pg_namespace AS tgt_ns
  ON tgt_ns.oid = tgt.relnamespace
WHERE src_ns.nspname = 'archive_alertas_regionais'
  AND src.relname IN (
      'alerta_regional_dengue',
      'alerta_regional_chik',
      'alerta_regional_zika'
  )
ORDER BY src.relname, con.conname;

SELECT dep_ns.nspname AS dependent_schema,
       dep.relname AS dependent_object,
       dep.relkind AS dependent_kind,
       ref_ns.nspname AS referenced_schema,
       ref.relname AS referenced_object
FROM pg_rewrite AS r
JOIN pg_class AS dep
  ON dep.oid = r.ev_class
JOIN pg_namespace AS dep_ns
  ON dep_ns.oid = dep.relnamespace
JOIN pg_depend AS d
  ON d.objid = r.oid
JOIN pg_class AS ref
  ON ref.oid = d.refobjid
JOIN pg_namespace AS ref_ns
  ON ref_ns.oid = ref.relnamespace
WHERE ref_ns.nspname = 'archive_alertas_regionais'
  AND ref.relname IN (
      'alerta_regional_dengue',
      'alerta_regional_chik',
      'alerta_regional_zika',
      'alerta_mrj',
      'alerta_mrj_chik',
      'alerta_mrj_zika'
  )
ORDER BY ref.relname, dep_ns.nspname, dep.relname;

COMMIT;
