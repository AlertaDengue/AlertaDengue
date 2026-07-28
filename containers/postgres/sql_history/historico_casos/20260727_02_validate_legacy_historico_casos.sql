-- Validate the archive_historico_casos batch after running 20260727_01.
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
    IF to_regclass('"Municipio".historico_casos') IS NOT NULL THEN
        RAISE EXCEPTION
            '"Municipio".historico_casos still exists; archive_historico_casos validation expects it to be moved';
    END IF;

    IF to_regclass('archive_historico_casos.historico_casos') IS NULL THEN
        RAISE EXCEPTION
            'archive_historico_casos.historico_casos is missing';
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
            'archive_historico_casos.historico_casos must remain a materialized view';
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
            'the active Historico_alerta* tables must remain in "Municipio"';
    END IF;

    IF to_regclass('"Municipio"."Notificacao"') IS NULL THEN
        RAISE EXCEPTION
            '"Municipio"."Notificacao" must remain present';
    END IF;

    IF (
        SELECT c.relkind
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname = 'Notificacao'
    ) <> 'r' THEN
        RAISE EXCEPTION
            '"Municipio"."Notificacao" must remain an ordinary table';
    END IF;

    IF to_regclass('public.epiyear_summary_materialized_view') IS NULL THEN
        RAISE EXCEPTION
            'public.epiyear_summary_materialized_view must remain present';
    END IF;

    IF (
        SELECT c.relkind
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'epiyear_summary_materialized_view'
    ) <> 'm' THEN
        RAISE EXCEPTION
            'public.epiyear_summary_materialized_view must remain a materialized view';
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
            'unexpected external view or materialized-view dependency remains on archive_historico_casos.historico_casos';
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

    IF COALESCE((
        SELECT c.relacl::text[]
        FROM pg_class AS c
        WHERE c.oid = 'archive_historico_casos.historico_casos'::regclass
    ), ARRAY[]::text[]) <> expected_acl THEN
        RAISE EXCEPTION
            'archive_historico_casos.historico_casos grants changed unexpectedly';
    END IF;
END
$guard$;

SELECT n.nspname AS schema_name,
       c.relname AS object_name,
       c.relkind,
       pg_get_userbyid(c.relowner) AS owner,
       pg_total_relation_size(c.oid) AS total_size,
       obj_description(c.oid, 'pg_class') AS relation_comment,
       CASE
           WHEN c.relkind = 'm' THEN c.relispopulated
           ELSE NULL
       END AS is_populated
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE (n.nspname = 'archive_historico_casos'
       AND c.relname = 'historico_casos')
   OR (n.nspname = 'Municipio'
       AND c.relname IN (
           'Historico_alerta',
           'Historico_alerta_chik',
           'Historico_alerta_zika',
           'Notificacao'
       ))
   OR (n.nspname = 'public'
       AND c.relname = 'epiyear_summary_materialized_view')
ORDER BY n.nspname, c.relname;

SELECT 'archive_historico_casos.historico_casos' AS object_name,
       COUNT(*) AS row_count,
       MIN("data_iniSE") AS earliest_data_inise,
       MAX("data_iniSE") AS latest_data_inise
FROM archive_historico_casos.historico_casos
UNION ALL
SELECT '"Municipio"."Historico_alerta"',
       COUNT(*),
       MIN("data_iniSE"),
       MAX("data_iniSE")
FROM "Municipio"."Historico_alerta"
UNION ALL
SELECT '"Municipio"."Historico_alerta_chik"',
       COUNT(*),
       MIN("data_iniSE"),
       MAX("data_iniSE")
FROM "Municipio"."Historico_alerta_chik"
UNION ALL
SELECT '"Municipio"."Historico_alerta_zika"',
       COUNT(*),
       MIN("data_iniSE"),
       MAX("data_iniSE")
FROM "Municipio"."Historico_alerta_zika";

SELECT c.oid::regclass AS relation_name,
       coalesce(array_to_string(c.relacl, ','), '') AS acl
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE (n.nspname = 'archive_historico_casos'
       AND c.relname = 'historico_casos')
   OR (n.nspname = 'Municipio'
       AND c.relname IN (
           'Historico_alerta',
           'Historico_alerta_chik',
           'Historico_alerta_zika',
           'Notificacao'
       ))
   OR (n.nspname = 'public'
       AND c.relname = 'epiyear_summary_materialized_view')
ORDER BY 1;

SELECT schemaname,
       tablename,
       indexname,
       indexdef
FROM pg_indexes
WHERE (schemaname = 'archive_historico_casos'
       AND tablename = 'historico_casos')
   OR (schemaname = 'Municipio'
       AND tablename IN (
           'Historico_alerta',
           'Historico_alerta_chik',
           'Historico_alerta_zika'
       ))
ORDER BY schemaname, tablename, indexname;

SELECT pg_get_viewdef('archive_historico_casos.historico_casos'::regclass, true)
    AS materialized_view_definition;

SELECT src_ns.nspname AS source_schema,
       src.relname AS source_relation,
       src.relkind AS source_relkind
FROM pg_depend AS d
JOIN pg_rewrite AS r
  ON r.oid = d.objid
JOIN pg_class AS mv
  ON mv.oid = r.ev_class
JOIN pg_class AS src
  ON src.oid = d.refobjid
JOIN pg_namespace AS src_ns
  ON src_ns.oid = src.relnamespace
WHERE mv.oid = 'archive_historico_casos.historico_casos'::regclass
  AND src.oid <> mv.oid
ORDER BY src_ns.nspname, src.relname;

SELECT pg_describe_object(d.classid, d.objid, d.objsubid) AS object,
       pg_describe_object(d.refclassid, d.refobjid, d.refobjsubid) AS depends_on,
       d.deptype
FROM pg_depend AS d
WHERE d.objid = 'archive_historico_casos.historico_casos'::regclass
   OR d.refobjid = 'archive_historico_casos.historico_casos'::regclass
ORDER BY 1, 2;

COMMIT;
