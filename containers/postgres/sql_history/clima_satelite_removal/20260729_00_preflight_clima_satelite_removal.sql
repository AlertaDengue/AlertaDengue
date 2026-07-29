-- Preflight for removing the empty legacy table "Municipio"."Clima_Satelite".
-- Read-only: confirms the exact object contract and refuses non-empty or
-- externally dependent fixtures.

BEGIN;

SET LOCAL statement_timeout = '10min';
SET LOCAL lock_timeout = '5s';
SET LOCAL temp_file_limit = '256MB';
SET TRANSACTION READ ONLY;

DO $$
DECLARE
    target_table_oid oid;
    target_sequence_oid oid;
    target_row_count bigint;
    target_owner text;
    target_relkind "char";
    sequence_relkind "char";
    sequence_owner text;
BEGIN
    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION 'refuse preflight while PostgreSQL is in recovery';
    END IF;

    SELECT c.oid, c.relkind, pg_get_userbyid(c.relowner)
      INTO target_table_oid, target_relkind, target_owner
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = 'Municipio'
      AND c.relname = 'Clima_Satelite';

    IF target_table_oid IS NULL THEN
        RAISE EXCEPTION 'expected table "Municipio"."Clima_Satelite" was not found';
    END IF;

    IF target_relkind <> 'r' THEN
        RAISE EXCEPTION
            '"Municipio"."Clima_Satelite" resolved to relkind % instead of ordinary table',
            target_relkind;
    END IF;

    IF target_owner <> 'administrador' THEN
        RAISE EXCEPTION
            '"Municipio"."Clima_Satelite" owner changed from administrador to %',
            target_owner;
    END IF;

    SELECT c.oid, c.relkind, pg_get_userbyid(c.relowner)
      INTO target_sequence_oid, sequence_relkind, sequence_owner
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = 'Municipio'
      AND c.relname = 'Clima_Satelite_id_seq';

    IF target_sequence_oid IS NULL THEN
        RAISE EXCEPTION
            'expected sequence "Municipio"."Clima_Satelite_id_seq" was not found';
    END IF;

    IF sequence_relkind <> 'S' THEN
        RAISE EXCEPTION
            '"Municipio"."Clima_Satelite_id_seq" resolved to relkind % instead of sequence',
            sequence_relkind;
    END IF;

    IF sequence_owner <> 'administrador' THEN
        RAISE EXCEPTION
            '"Municipio"."Clima_Satelite_id_seq" owner changed from administrador to %',
            sequence_owner;
    END IF;

    EXECUTE 'SELECT count(*) FROM "Municipio"."Clima_Satelite"'
      INTO target_row_count;

    IF target_row_count <> 0 THEN
        RAISE EXCEPTION
            '"Municipio"."Clima_Satelite" must be empty, found % rows',
            target_row_count;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_depend AS dep
        JOIN pg_class AS seq
          ON seq.oid = dep.objid
        JOIN pg_namespace AS seq_ns
          ON seq_ns.oid = seq.relnamespace
        JOIN pg_class AS tbl
          ON tbl.oid = dep.refobjid
        JOIN pg_namespace AS tbl_ns
          ON tbl_ns.oid = tbl.relnamespace
        JOIN pg_attribute AS att
          ON att.attrelid = tbl.oid
         AND att.attnum = dep.refobjsubid
        WHERE dep.deptype IN ('a', 'i')
          AND seq_ns.nspname = 'Municipio'
          AND seq.relname = 'Clima_Satelite_id_seq'
          AND tbl_ns.nspname = 'Municipio'
          AND tbl.relname = 'Clima_Satelite'
          AND att.attname = 'id'
    ) THEN
        RAISE EXCEPTION
            '"Municipio"."Clima_Satelite_id_seq" is not owned by "Municipio"."Clima_Satelite".id';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_constraint AS con
        WHERE con.contype = 'f'
          AND (con.conrelid = target_table_oid OR con.confrelid = target_table_oid)
    ) THEN
        RAISE EXCEPTION
            'foreign-key dependency blocks removal of "Municipio"."Clima_Satelite"';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_trigger AS trg
        WHERE trg.tgrelid = target_table_oid
          AND NOT trg.tgisinternal
    ) THEN
        RAISE EXCEPTION
            'user-defined trigger blocks removal of "Municipio"."Clima_Satelite"';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_rewrite AS rw
        JOIN pg_depend AS dep
          ON dep.objid = rw.oid
        JOIN pg_class AS dependent
          ON dependent.oid = rw.ev_class
        WHERE dep.refobjid = target_table_oid
          AND dependent.oid <> target_table_oid
    ) THEN
        RAISE EXCEPTION
            'view or materialized-view dependency blocks removal of "Municipio"."Clima_Satelite"';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_publication_rel
        WHERE prrelid = target_table_oid
    ) THEN
        RAISE EXCEPTION
            'publication dependency blocks removal of "Municipio"."Clima_Satelite"';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_subscription_rel
        WHERE srrelid = target_table_oid
    ) THEN
        RAISE EXCEPTION
            'subscription dependency blocks removal of "Municipio"."Clima_Satelite"';
    END IF;
END
$$;

SELECT
    n.nspname AS schema_name,
    c.relname AS relation_name,
    c.oid,
    c.relkind,
    pg_get_userbyid(c.relowner) AS owner,
    c.relacl,
    pg_total_relation_size(c.oid) AS total_bytes,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    obj_description(c.oid, 'pg_class') AS comment
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE n.nspname = 'Municipio'
  AND c.relname IN ('Clima_Satelite', 'Clima_Satelite_id_seq')
ORDER BY c.relname;

SELECT
    a.attnum,
    a.attname,
    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
    a.attnotnull,
    pg_get_expr(ad.adbin, ad.adrelid) AS default_expression
FROM pg_attribute AS a
LEFT JOIN pg_attrdef AS ad
  ON ad.adrelid = a.attrelid
 AND ad.adnum = a.attnum
WHERE a.attrelid = '"Municipio"."Clima_Satelite"'::regclass
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY a.attnum;

SELECT
    conname,
    contype,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = '"Municipio"."Clima_Satelite"'::regclass
ORDER BY contype, conname;

SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'Municipio'
  AND tablename = 'Clima_Satelite'
ORDER BY indexname;

SELECT
    grantee,
    privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'Municipio'
  AND table_name = 'Clima_Satelite'
ORDER BY grantee, privilege_type;

SELECT
    seq_ns.nspname AS sequence_schema,
    seq.relname AS sequence_name,
    tbl_ns.nspname AS table_schema,
    tbl.relname AS table_name,
    att.attname AS column_name
FROM pg_class AS seq
JOIN pg_namespace AS seq_ns
  ON seq_ns.oid = seq.relnamespace
JOIN pg_depend AS dep
  ON dep.objid = seq.oid
 AND dep.deptype IN ('a', 'i')
JOIN pg_class AS tbl
  ON tbl.oid = dep.refobjid
JOIN pg_namespace AS tbl_ns
  ON tbl_ns.oid = tbl.relnamespace
JOIN pg_attribute AS att
  ON att.attrelid = tbl.oid
 AND att.attnum = dep.refobjsubid
WHERE seq_ns.nspname = 'Municipio'
  AND seq.relname = 'Clima_Satelite_id_seq';

SELECT
    d.deptype,
    pg_describe_object(d.classid, d.objid, d.objsubid) AS object,
    pg_describe_object(d.refclassid, d.refobjid, d.refobjsubid) AS depends_on
FROM pg_depend AS d
WHERE d.objid = '"Municipio"."Clima_Satelite"'::regclass
   OR d.refobjid = '"Municipio"."Clima_Satelite"'::regclass
ORDER BY d.deptype, object, depends_on;

ROLLBACK;
