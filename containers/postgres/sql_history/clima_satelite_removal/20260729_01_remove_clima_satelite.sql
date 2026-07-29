-- Remove the empty legacy table "Municipio"."Clima_Satelite".
-- The owned sequence must disappear with the table drop.

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '10min';

DO $$
DECLARE
    target_schema text := 'Municipio';
    target_name text := 'Clima_Satelite';
    target_oid oid;
    target_owner text;
    target_relkind "char";
    target_row_count bigint;
    target_sequence_oid oid;
    target_sequence_owner text;
    target_sequence_relkind "char";
BEGIN
    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION 'refuse removal while PostgreSQL is in recovery';
    END IF;

    SELECT c.oid, c.relkind, pg_get_userbyid(c.relowner)
      INTO target_oid, target_relkind, target_owner
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = target_schema
      AND c.relname = target_name;

    IF target_oid IS NULL THEN
        RAISE EXCEPTION 'expected table %.% was not found', target_schema, target_name;
    END IF;

    IF target_relkind <> 'r' THEN
        RAISE EXCEPTION
            'approved target %.% resolved to relkind % instead of ordinary table',
            target_schema, target_name, target_relkind;
    END IF;

    IF target_owner <> 'administrador' THEN
        RAISE EXCEPTION
            'approved target %.% owner changed from administrador to %',
            target_schema, target_name, target_owner;
    END IF;

    EXECUTE format('SELECT count(*) FROM %I.%I', target_schema, target_name)
      INTO target_row_count;

    IF target_row_count <> 0 THEN
        RAISE EXCEPTION
            'approved target %.% must be empty, found % rows',
            target_schema, target_name, target_row_count;
    END IF;

    SELECT c.oid, c.relkind, pg_get_userbyid(c.relowner)
      INTO target_sequence_oid, target_sequence_relkind, target_sequence_owner
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = target_schema
      AND c.relname = 'Clima_Satelite_id_seq';

    IF target_sequence_oid IS NULL THEN
        RAISE EXCEPTION
            'expected sequence "Municipio"."Clima_Satelite_id_seq" was not found';
    END IF;

    IF target_sequence_relkind <> 'S' THEN
        RAISE EXCEPTION
            '"Municipio"."Clima_Satelite_id_seq" resolved to relkind % instead of sequence',
            target_sequence_relkind;
    END IF;

    IF target_sequence_owner <> 'administrador' THEN
        RAISE EXCEPTION
            '"Municipio"."Clima_Satelite_id_seq" owner changed from administrador to %',
            target_sequence_owner;
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
          AND seq_ns.nspname = target_schema
          AND seq.relname = 'Clima_Satelite_id_seq'
          AND tbl_ns.nspname = target_schema
          AND tbl.relname = target_name
          AND att.attname = 'id'
    ) THEN
        RAISE EXCEPTION
            '"Municipio"."Clima_Satelite_id_seq" is not owned by "Municipio"."Clima_Satelite".id';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_constraint AS con
        WHERE con.contype = 'f'
          AND (con.conrelid = target_oid OR con.confrelid = target_oid)
    ) THEN
        RAISE EXCEPTION 'foreign-key dependency blocks removal of %.%', target_schema, target_name;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_trigger AS trg
        WHERE trg.tgrelid = target_oid
          AND NOT trg.tgisinternal
    ) THEN
        RAISE EXCEPTION 'user-defined trigger blocks removal of %.%', target_schema, target_name;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_rewrite AS rw
        JOIN pg_depend AS dep
          ON dep.objid = rw.oid
        JOIN pg_class AS dependent
          ON dependent.oid = rw.ev_class
        WHERE dep.refobjid = target_oid
          AND dependent.oid <> target_oid
    ) THEN
        RAISE EXCEPTION
            'view or materialized-view dependency blocks removal of %.%',
            target_schema, target_name;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_publication_rel
        WHERE prrelid = target_oid
    ) THEN
        RAISE EXCEPTION 'publication dependency blocks removal of %.%', target_schema, target_name;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_subscription_rel
        WHERE srrelid = target_oid
    ) THEN
        RAISE EXCEPTION 'subscription dependency blocks removal of %.%', target_schema, target_name;
    END IF;

    EXECUTE format(
        'DROP TABLE %I.%I',
        target_schema,
        target_name
    );

    IF to_regclass('"Municipio"."Clima_Satelite"') IS NOT NULL THEN
        RAISE EXCEPTION '"Municipio"."Clima_Satelite" still exists after DROP TABLE';
    END IF;

    IF to_regclass('"Municipio"."Clima_Satelite_id_seq"') IS NOT NULL THEN
        RAISE EXCEPTION
            '"Municipio"."Clima_Satelite_id_seq" still exists after DROP TABLE';
    END IF;
END
$$;

COMMIT;
