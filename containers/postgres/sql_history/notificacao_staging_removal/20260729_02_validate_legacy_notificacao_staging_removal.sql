-- Validate legacy notification staging removal without modifying data.

BEGIN;

SET LOCAL statement_timeout = '30min';
SET LOCAL lock_timeout = '5s';
SET LOCAL temp_file_limit = '1GB';
SET TRANSACTION READ ONLY;

DO $$
DECLARE
    expected_acl text[] := ARRAY[
        'administrador=arwdDxt/administrador',
        'Dengue=arwdDxt/administrador',
        'dengue=arwdDxt/administrador',
        'infodenguedev=r/administrador',
        'analista=r/administrador',
        'mosqlimate_dev=r/administrador'
    ];
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE (n.nspname = 'public' AND c.relname = '"Municipio"."Notificacao"')
           OR (n.nspname = 'Municipio' AND c.relname IN ('Notificacao__20220806', 'Corrigido2022'))
    ) THEN
        RAISE EXCEPTION 'one or more approved targets still exist';
    END IF;

    IF to_regclass('"Municipio"."Notificacao"') IS NULL THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" must remain present';
    END IF;

    IF (
        SELECT c.relkind
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname = 'Notificacao'
    ) <> 'r' THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" must remain an ordinary table';
    END IF;

    IF (
        SELECT pg_get_userbyid(c.relowner)
        FROM pg_class AS c
        WHERE c.oid = '"Municipio"."Notificacao"'::regclass
    ) <> 'administrador' THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" owner changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = '"Municipio"."Notificacao"'::regclass
    ), ARRAY[]::text[]) <> expected_acl THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" ACL changed unexpectedly';
    END IF;

    IF COALESCE((
        SELECT obj_description('"Municipio"."Notificacao"'::regclass, 'pg_class')
    ), '') <> 'Casos de notificacao de dengue' THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" comment changed unexpectedly';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_attribute AS a
        WHERE a.attrelid = '"Municipio"."Notificacao"'::regclass
          AND a.attnum > 0
          AND NOT a.attisdropped
    ) <> 34 THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" column count changed unexpectedly';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint AS con
        WHERE con.conrelid = '"Municipio"."Notificacao"'::regclass
          AND con.conname = 'Notificacao_pk'
          AND con.contype = 'p'
    ) THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" primary key changed unexpectedly';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint AS con
        WHERE con.conrelid = '"Municipio"."Notificacao"'::regclass
          AND con.conname = 'casos_unicos'
          AND con.contype = 'u'
    ) THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" unique constraint changed unexpectedly';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_indexes
        WHERE schemaname = 'Municipio'
          AND tablename = 'Notificacao'
          AND indexname IN (
              'Dengue_idx_data',
              'Notificacao_pk',
              'casos_unicos',
              'notificacao_api_city_cid10_year_date_id_idx',
              'notificacao_cid10_idx'
          )
    ) <> 5 THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" indexes changed unexpectedly';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_class AS seq
        JOIN pg_namespace AS seq_ns
          ON seq_ns.oid = seq.relnamespace
        JOIN pg_depend AS dep
          ON dep.objid = seq.oid
        WHERE seq_ns.nspname = 'Municipio'
          AND seq.relname = 'Notificacao_id_seq'
          AND seq.relkind = 'S'
          AND dep.refobjid = '"Municipio"."Notificacao"'::regclass
          AND dep.deptype = 'a'
    ) THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" owned sequence changed unexpectedly';
    END IF;

    IF (
        SELECT pg_get_expr(ad.adbin, ad.adrelid)
        FROM pg_attrdef AS ad
        JOIN pg_attribute AS a
          ON a.attrelid = ad.adrelid
         AND a.attnum = ad.adnum
        WHERE ad.adrelid = '"Municipio"."Notificacao"'::regclass
          AND a.attname = 'id'
    ) <> 'nextval(''"Municipio"."Notificacao_id_seq"''::regclass)' THEN
        RAISE EXCEPTION '"Municipio"."Notificacao".id default changed unexpectedly';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_type AS t
        JOIN pg_namespace AS n
          ON n.oid = t.typnamespace
        WHERE (n.nspname = 'public' AND t.typname = '"Municipio"."Notificacao"')
           OR (n.nspname = 'Municipio' AND t.typname IN ('Notificacao__20220806', 'Corrigido2022'))
    ) THEN
        RAISE EXCEPTION 'residual target row type remains unexpectedly';
    END IF;
END
$$;

SELECT n.nspname AS schema_name,
       c.relname AS relation_name,
       c.oid,
       c.relkind,
       pg_get_userbyid(c.relowner) AS owner,
       c.relacl,
       obj_description(c.oid, 'pg_class') AS comment,
       pg_total_relation_size(c.oid) AS total_bytes
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE n.nspname = 'Municipio'
  AND c.relname = 'Notificacao';

SELECT n.nspname,
       c.relname,
       con.conname,
       con.contype,
       pg_get_constraintdef(con.oid, true) AS definition
FROM pg_constraint AS con
JOIN pg_class AS c
  ON c.oid = con.conrelid
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE con.conrelid = '"Municipio"."Notificacao"'::regclass
ORDER BY con.contype, con.conname;

SELECT schemaname,
       tablename,
       indexname,
       indexdef
FROM pg_indexes
WHERE schemaname = 'Municipio'
  AND tablename = 'Notificacao'
ORDER BY indexname;

ROLLBACK;
