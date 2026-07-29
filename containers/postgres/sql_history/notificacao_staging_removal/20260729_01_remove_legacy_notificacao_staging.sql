-- Remove obsolete notification staging tables after successful preflight.

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30min';

DO $$
DECLARE
    active_oid oid;
    current_active_oid oid;
    target_schema text;
    target_name text;
    target_oid oid;
    target_relkind "char";
BEGIN
    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION 'refuse removal while PostgreSQL is in recovery';
    END IF;

    SELECT c.oid
      INTO active_oid
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = 'Municipio'
      AND c.relname = 'Notificacao'
      AND c.relkind = 'r';

    IF active_oid IS NULL THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" must exist as an ordinary table';
    END IF;

    FOR target_schema, target_name IN
        SELECT *
        FROM (
            VALUES
                ('public', '"Municipio"."Notificacao"'),
                ('Municipio', 'Notificacao__20220806'),
                ('Municipio', 'Corrigido2022')
        ) AS t(schema_name, relation_name)
    LOOP
        SELECT c.oid, c.relkind
          INTO target_oid, target_relkind
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = target_schema
          AND c.relname = target_name;

        IF target_oid IS NULL THEN
            CONTINUE;
        END IF;

        IF target_relkind <> 'r' THEN
            RAISE EXCEPTION
                'approved target %.% resolved to relkind % instead of ordinary table',
                target_schema, target_name, target_relkind;
        END IF;

        IF EXISTS (
            SELECT 1
            FROM pg_rewrite AS r
            JOIN pg_class AS dependent
              ON dependent.oid = r.ev_class
            JOIN pg_namespace AS dependent_ns
              ON dependent_ns.oid = dependent.relnamespace
            JOIN pg_depend AS d
              ON d.objid = r.oid
            WHERE d.refobjid = target_oid
              AND dependent.oid <> target_oid
              AND dependent_ns.nspname NOT IN ('pg_catalog', 'information_schema')
        ) THEN
            RAISE EXCEPTION
                'view or materialized-view dependency blocks removal of %.%',
                target_schema, target_name;
        END IF;

        IF EXISTS (
            SELECT 1
            FROM pg_constraint AS con
            WHERE con.contype = 'f'
              AND (con.conrelid = target_oid OR con.confrelid = target_oid)
        ) THEN
            RAISE EXCEPTION
                'constraint dependency blocks removal of %.%',
                target_schema, target_name;
        END IF;

        IF EXISTS (
            SELECT 1
            FROM pg_trigger AS t
            WHERE t.tgrelid = target_oid
              AND NOT t.tgisinternal
        ) THEN
            RAISE EXCEPTION
                'user-defined trigger blocks removal of %.%',
                target_schema, target_name;
        END IF;

        IF EXISTS (
            SELECT 1
            FROM pg_publication_rel
            WHERE prrelid = target_oid
        ) THEN
            RAISE EXCEPTION
                'publication dependency blocks removal of %.%',
                target_schema, target_name;
        END IF;

        IF EXISTS (
            SELECT 1
            FROM pg_subscription_rel
            WHERE srrelid = target_oid
        ) THEN
            RAISE EXCEPTION
                'subscription dependency blocks removal of %.%',
                target_schema, target_name;
        END IF;

        EXECUTE format('DROP TABLE %I.%I', target_schema, target_name);
    END LOOP;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE (n.nspname = 'public' AND c.relname = '"Municipio"."Notificacao"')
           OR (n.nspname = 'Municipio' AND c.relname IN ('Notificacao__20220806', 'Corrigido2022'))
    ) THEN
        RAISE EXCEPTION 'one or more approved targets still exist after removal';
    END IF;

    SELECT c.oid
      INTO current_active_oid
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = 'Municipio'
      AND c.relname = 'Notificacao'
      AND c.relkind = 'r';

    IF current_active_oid IS NULL THEN
        RAISE EXCEPTION '"Municipio"."Notificacao" disappeared during removal';
    END IF;

    IF current_active_oid <> active_oid THEN
        RAISE EXCEPTION
            '"Municipio"."Notificacao" changed OID from % to % during removal',
            active_oid, current_active_oid;
    END IF;
END
$$;

COMMIT;
