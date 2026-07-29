-- Read-only preflight for removing obsolete notification staging tables.
--
-- Execute with:
-- psql -X -v ON_ERROR_STOP=1 \
--   -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
--   -f containers/postgres/sql_history/notificacao_staging_removal/20260729_00_preflight_legacy_notificacao_staging.sql

BEGIN;

SET LOCAL statement_timeout = '30min';
SET LOCAL lock_timeout = '5s';
SET LOCAL temp_file_limit = '1GB';
SET LOCAL work_mem = '64MB';
SET TRANSACTION READ ONLY;

DO $guard$
DECLARE
    active_oid oid;
    target_oid oid;
    target_schema text;
    target_name text;
    target_relkind "char";
    duplicate_rows bigint;
    row_count bigint;
    municipality_count bigint;
    min_notification_date date;
    max_notification_date date;
    min_symptom_date date;
    max_symptom_date date;
    min_epiweek integer;
    max_epiweek integer;
BEGIN
    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION 'refuse preflight while PostgreSQL is in recovery';
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
    END LOOP;

    IF to_regclass('public."""Municipio"".""Notificacao"""') IS NOT NULL THEN
        SELECT COUNT(*),
               COUNT(DISTINCT "ID_MUNICIP"),
               MIN(to_date("DT_NOTIFIC", 'YYYYMMDD')),
               MAX(to_date("DT_NOTIFIC", 'YYYYMMDD')),
               MIN(to_date("DT_SIN_PRI", 'YYYYMMDD')),
               MAX(to_date("DT_SIN_PRI", 'YYYYMMDD')),
               MIN("SEM_NOT"::integer),
               MAX("SEM_NOT"::integer)
          INTO row_count,
               municipality_count,
               min_notification_date,
               max_notification_date,
               min_symptom_date,
               max_symptom_date,
               min_epiweek,
               max_epiweek
        FROM public."""Municipio"".""Notificacao""";

        SELECT COUNT(*)
          INTO duplicate_rows
        FROM (
            SELECT "NU_NOTIFIC",
                   "DT_NOTIFIC",
                   btrim("ID_AGRAVO") AS disease_code,
                   "ID_MUNICIP",
                   COUNT(*)
            FROM public."""Municipio"".""Notificacao"""
            GROUP BY 1, 2, 3, 4
            HAVING COUNT(*) > 1
        ) AS dup;

        IF row_count <> 30000 THEN
            RAISE EXCEPTION 'public literal-name candidate row count drifted from audited baseline';
        END IF;

        IF (
            SELECT COUNT(DISTINCT btrim("ID_AGRAVO"))
            FROM public."""Municipio"".""Notificacao"""
        ) <> 1
           OR (
                SELECT MIN(btrim("ID_AGRAVO"))
                FROM public."""Municipio"".""Notificacao"""
           ) <> 'A90' THEN
            RAISE EXCEPTION 'public literal-name candidate disease baseline changed';
        END IF;

        IF (
            SELECT COUNT(DISTINCT "NU_ANO")
            FROM public."""Municipio"".""Notificacao"""
        ) <> 1
           OR (
                SELECT MIN("NU_ANO")
                FROM public."""Municipio"".""Notificacao"""
           ) <> '2022' THEN
            RAISE EXCEPTION 'public literal-name candidate year baseline changed';
        END IF;

        IF min_notification_date <> DATE '2022-01-02'
           OR max_notification_date <> DATE '2022-12-31' THEN
            RAISE EXCEPTION 'public literal-name candidate notification-date baseline changed';
        END IF;

        IF min_symptom_date <> DATE '2022-01-02'
           OR max_symptom_date <> DATE '2022-12-29' THEN
            RAISE EXCEPTION 'public literal-name candidate symptom-date baseline changed';
        END IF;

        IF min_epiweek <> 202201
           OR max_epiweek <> 202252 THEN
            RAISE EXCEPTION 'public literal-name candidate epiweek baseline changed';
        END IF;

        IF municipality_count <> 579 THEN
            RAISE EXCEPTION 'public literal-name candidate municipality baseline changed';
        END IF;

        RAISE NOTICE
            'public literal-name candidate baseline ok: rows=%, municipalities=%, notification=%..%, symptom=%..%, epiweek=%..%',
            row_count,
            municipality_count,
            min_notification_date,
            max_notification_date,
            min_symptom_date,
            max_symptom_date,
            min_epiweek,
            max_epiweek;

        IF COALESCE(duplicate_rows, 0) <> 0 THEN
            RAISE EXCEPTION 'public literal-name candidate duplicate-key baseline changed';
        END IF;
    END IF;
END
$guard$;

WITH targets AS (
    SELECT 'public'::text AS schema_name,
           '"Municipio"."Notificacao"'::text AS relation_name
    UNION ALL
    SELECT 'Municipio', 'Notificacao__20220806'
    UNION ALL
    SELECT 'Municipio', 'Corrigido2022'
    UNION ALL
    SELECT 'Municipio', 'Notificacao'
),
resolved AS (
    SELECT t.schema_name,
           t.relation_name,
           c.oid,
           c.relkind,
           pg_get_userbyid(c.relowner) AS owner,
           c.relacl,
           pg_total_relation_size(c.oid) AS total_bytes,
           pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
           obj_description(c.oid, 'pg_class') AS comment
    FROM targets AS t
    LEFT JOIN pg_namespace AS n
      ON n.nspname = t.schema_name
    LEFT JOIN pg_class AS c
      ON c.relnamespace = n.oid
     AND c.relname = t.relation_name
)
SELECT schema_name,
       relation_name,
       CASE WHEN oid IS NULL THEN 'absent' ELSE 'present' END AS status,
       oid,
       relkind,
       owner,
       relacl,
       total_bytes,
       total_size,
       comment
FROM resolved
ORDER BY schema_name, relation_name;

SELECT n.nspname,
       c.relname,
       a.attnum,
       a.attname,
       pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
       a.attnotnull,
       pg_get_expr(ad.adbin, ad.adrelid) AS default_expression
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
JOIN pg_attribute AS a
  ON a.attrelid = c.oid
LEFT JOIN pg_attrdef AS ad
  ON ad.adrelid = a.attrelid
 AND ad.adnum = a.attnum
WHERE (
        (n.nspname = 'public'
         AND c.relname = '"Municipio"."Notificacao"')
     OR (n.nspname = 'Municipio'
         AND c.relname IN (
             'Notificacao',
             'Notificacao__20220806',
             'Corrigido2022'
         ))
      )
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY n.nspname, c.relname, a.attnum;

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
WHERE (
        n.nspname = 'public'
        AND c.relname = '"Municipio"."Notificacao"'
      )
   OR (
        n.nspname = 'Municipio'
        AND c.relname IN (
            'Notificacao',
            'Notificacao__20220806',
            'Corrigido2022'
        )
      )
ORDER BY n.nspname, c.relname, con.contype, con.conname;

SELECT schemaname,
       tablename,
       indexname,
       indexdef
FROM pg_indexes
WHERE (schemaname = 'public' AND tablename = '"Municipio"."Notificacao"')
   OR (schemaname = 'Municipio' AND tablename IN (
            'Notificacao',
            'Notificacao__20220806',
            'Corrigido2022'
       ))
ORDER BY schemaname, tablename, indexname;

SELECT table_schema,
       table_name,
       grantee,
       privilege_type
FROM information_schema.role_table_grants
WHERE (table_schema = 'public' AND table_name = '"Municipio"."Notificacao"')
   OR (table_schema = 'Municipio' AND table_name IN (
            'Notificacao',
            'Notificacao__20220806',
            'Corrigido2022'
       ))
ORDER BY table_schema, table_name, grantee, privilege_type;

SELECT pg_describe_object(d.classid, d.objid, d.objsubid) AS object,
       pg_describe_object(d.refclassid, d.refobjid, d.refobjsubid) AS depends_on,
       d.deptype
FROM pg_depend AS d
WHERE d.objid IN (
        'public."""Municipio"".""Notificacao"""'::regclass,
        '"Municipio"."Notificacao"'::regclass
      )
   OR d.refobjid IN (
        'public."""Municipio"".""Notificacao"""'::regclass,
        '"Municipio"."Notificacao"'::regclass
      )
ORDER BY 1, 2;

ROLLBACK;
