-- Restore the archived historico_casos materialized view back to "Municipio".
--
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DO $guard$
DECLARE
    expected_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'analista=r/dengueadmin'
    ];
BEGIN
    IF to_regclass('archive_historico_casos.historico_casos') IS NULL THEN
        RAISE EXCEPTION
            'archive_historico_casos.historico_casos is required for restoration';
    END IF;

    IF to_regclass('"Municipio".historico_casos') IS NOT NULL THEN
        RAISE EXCEPTION
            '"Municipio".historico_casos already exists; restoration would conflict';
    END IF;

    IF (
        SELECT c.relkind
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_historico_casos'
          AND c.relname = 'historico_casos'
    ) <> 'm' THEN
        RAISE EXCEPTION
            'archive_historico_casos.historico_casos must be a materialized view before restoration';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname IN (
              'Historico_alerta',
              'Historico_alerta_chik',
              'Historico_alerta_zika'
          )
          AND c.relkind = 'r'
    ) <> 3 THEN
        RAISE EXCEPTION
            'the active Historico_alerta* tables must remain present during restoration';
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
        WHERE d.refobjid = 'archive_historico_casos.historico_casos'::regclass
          AND dependent.oid <> 'archive_historico_casos.historico_casos'::regclass
          AND dependent_ns.nspname <> 'archive_historico_casos'
    ) THEN
        RAISE EXCEPTION
            'unexpected external view or materialized-view dependency blocks restoration';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'archive_historico_casos.historico_casos'::regclass
    ), ARRAY[]::text[]) <> expected_acl THEN
        RAISE EXCEPTION
            'archive_historico_casos.historico_casos grants changed unexpectedly before restoration';
    END IF;
END
$guard$;

ALTER MATERIALIZED VIEW archive_historico_casos.historico_casos
    SET SCHEMA "Municipio";

DO $postcheck$
DECLARE
    expected_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'analista=r/dengueadmin'
    ];
BEGIN
    IF to_regclass('"Municipio".historico_casos') IS NULL THEN
        RAISE EXCEPTION
            '"Municipio".historico_casos is missing after restoration';
    END IF;

    IF (
        SELECT c.relkind
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname = 'historico_casos'
    ) <> 'm' THEN
        RAISE EXCEPTION
            '"Municipio".historico_casos is not a materialized view after restoration';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_indexes
        WHERE schemaname = 'Municipio'
          AND tablename = 'historico_casos'
          AND indexname IN (
              'historico_casos_data_inise_idx',
              'historico_casos_municipio_geocodigo_idx'
          )
    ) <> 2 THEN
        RAISE EXCEPTION
            '"Municipio".historico_casos indexes changed unexpectedly after restoration';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = '"Municipio".historico_casos'::regclass
    ), ARRAY[]::text[]) <> expected_acl THEN
        RAISE EXCEPTION
            '"Municipio".historico_casos grants changed unexpectedly after restoration';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname IN (
              'Historico_alerta',
              'Historico_alerta_chik',
              'Historico_alerta_zika'
          )
          AND c.relkind = 'r'
    ) <> 3 THEN
        RAISE EXCEPTION
            'the active Historico_alerta* tables changed unexpectedly during restoration';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'archive_historico_casos'
          AND c.relname = 'historico_casos'
    ) THEN
        RAISE EXCEPTION
            'archive_historico_casos still contains historico_casos after restoration';
    END IF;
END
$postcheck$;

DO $cleanup$
BEGIN
    IF to_regnamespace('archive_historico_casos') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM pg_class AS c
           JOIN pg_namespace AS n
             ON n.oid = c.relnamespace
           WHERE n.nspname = 'archive_historico_casos'
             AND c.relkind IN ('r', 'S', 'v', 'm', 'f', 'p')
       ) THEN
        DROP SCHEMA archive_historico_casos;
    END IF;
END
$cleanup$;

COMMIT;
