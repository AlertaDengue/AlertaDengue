-- Archive the legacy historico_casos materialized view by moving it into
-- archive_historico_casos.
--
-- Run as the database owner, or as a role that owns the affected relation.
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
    IF to_regnamespace('archive_historico_casos') IS NOT NULL THEN
        RAISE EXCEPTION
            'archive_historico_casos already exists; review the existing archive before rerunning';
    END IF;

    IF to_regclass('"Municipio".historico_casos') IS NULL THEN
        RAISE EXCEPTION
            '"Municipio".historico_casos must exist before archival';
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
            '"Municipio".historico_casos must be a materialized view';
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
            'the active Historico_alerta* tables must remain present as ordinary tables';
    END IF;

    IF to_regclass('archive_historico_casos.historico_casos') IS NOT NULL THEN
        RAISE EXCEPTION
            'archive_historico_casos.historico_casos already exists';
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
        WHERE d.refobjid = '"Municipio".historico_casos'::regclass
          AND dependent.oid <> '"Municipio".historico_casos'::regclass
    ) THEN
        RAISE EXCEPTION
            'unexpected external view or materialized-view dependency found for "Municipio".historico_casos';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_trigger AS t
        WHERE t.tgrelid = '"Municipio".historico_casos'::regclass
          AND NOT t.tgisinternal
    ) THEN
        RAISE EXCEPTION
            '"Municipio".historico_casos unexpectedly has user-defined triggers';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_constraint AS con
        WHERE con.conrelid = '"Municipio".historico_casos'::regclass
    ) THEN
        RAISE EXCEPTION
            '"Municipio".historico_casos unexpectedly has constraints';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = '"Municipio".historico_casos'::regclass
    ), ARRAY[]::text[]) <> expected_acl THEN
        RAISE EXCEPTION
            '"Municipio".historico_casos grants changed unexpectedly before archival';
    END IF;
END
$guard$;

CREATE SCHEMA archive_historico_casos;
REVOKE ALL ON SCHEMA archive_historico_casos FROM PUBLIC;

ALTER MATERIALIZED VIEW "Municipio".historico_casos
    SET SCHEMA archive_historico_casos;

DO $postcheck$
DECLARE
    expected_acl text[] := ARRAY[
        'dengueadmin=arwdDxt/dengueadmin',
        'infodenguedev=r/dengueadmin',
        'analista=r/dengueadmin'
    ];
BEGIN
    IF to_regclass('"Municipio".historico_casos') IS NOT NULL THEN
        RAISE EXCEPTION
            '"Municipio".historico_casos still exists after archival';
    END IF;

    IF to_regclass('archive_historico_casos.historico_casos') IS NULL THEN
        RAISE EXCEPTION
            'archive_historico_casos.historico_casos is missing after archival';
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
            'archive_historico_casos.historico_casos is not a materialized view after archival';
    END IF;

    IF (
        SELECT count(*)
        FROM pg_indexes
        WHERE schemaname = 'archive_historico_casos'
          AND tablename = 'historico_casos'
          AND indexname IN (
              'historico_casos_data_inise_idx',
              'historico_casos_municipio_geocodigo_idx'
          )
    ) <> 2 THEN
        RAISE EXCEPTION
            'archive_historico_casos.historico_casos indexes changed unexpectedly';
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
            'the active Historico_alerta* tables changed unexpectedly during archival';
    END IF;

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'archive_historico_casos.historico_casos'::regclass
    ), ARRAY[]::text[]) <> expected_acl THEN
        RAISE EXCEPTION
            'archive_historico_casos.historico_casos grants changed unexpectedly';
    END IF;
END
$postcheck$;

COMMIT;
