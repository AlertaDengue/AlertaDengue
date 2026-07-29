-- Audit the legacy public."""Municipio"".""Notificacao""" table without
-- modifying data or metadata.
--
-- Execute with:
-- psql -X -v ON_ERROR_STOP=1 \
--   -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
--   -f containers/postgres/sql_history/public_municipio_notificacao/20260729_00_audit_public_municipio_notificacao.sql

BEGIN;

SET LOCAL statement_timeout = '30min';
SET LOCAL lock_timeout = '5s';
SET LOCAL temp_file_limit = '1GB';
SET LOCAL work_mem = '64MB';
SET TRANSACTION READ ONLY;

WITH relations AS (
    SELECT c.oid,
           n.nspname,
           c.relname,
           c.relkind,
           c.relpersistence,
           c.relispopulated,
           pg_get_userbyid(c.relowner) AS owner,
           c.relacl,
           c.reltuples::bigint AS estimated_rows,
           pg_total_relation_size(c.oid) AS total_bytes,
           pg_relation_size(c.oid) AS table_bytes,
           pg_indexes_size(c.oid) AS index_bytes,
           pg_total_relation_size(c.oid)
               - pg_relation_size(c.oid)
               - pg_indexes_size(c.oid) AS toast_bytes,
           pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
           obj_description(c.oid, 'pg_class') AS comment
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE c.oid IN (
        'public."""Municipio"".""Notificacao"""'::regclass,
        '"Municipio"."Notificacao"'::regclass
    )
)
SELECT *
FROM relations
ORDER BY nspname, relname;

SELECT n.nspname,
       c.relname,
       a.attnum,
       a.attname,
       pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
       a.attnotnull,
       pg_get_expr(ad.adbin, ad.adrelid) AS default_expression,
       a.attidentity,
       a.attgenerated
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
JOIN pg_attribute AS a
  ON a.attrelid = c.oid
LEFT JOIN pg_attrdef AS ad
  ON ad.adrelid = a.attrelid
 AND ad.adnum = a.attnum
WHERE c.oid IN (
    'public."""Municipio"".""Notificacao"""'::regclass,
    '"Municipio"."Notificacao"'::regclass
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
WHERE con.conrelid IN (
    'public."""Municipio"".""Notificacao"""'::regclass,
    '"Municipio"."Notificacao"'::regclass
)
ORDER BY n.nspname, c.relname, con.contype, con.conname;

SELECT schemaname,
       tablename,
       indexname,
       indexdef
FROM pg_indexes
WHERE (schemaname = 'public' AND tablename = '"Municipio"."Notificacao"')
   OR (schemaname = 'Municipio' AND tablename = 'Notificacao')
ORDER BY schemaname, tablename, indexname;

SELECT table_schema,
       table_name,
       grantee,
       privilege_type
FROM information_schema.role_table_grants
WHERE (table_schema = 'public' AND table_name = '"Municipio"."Notificacao"')
   OR (table_schema = 'Municipio' AND table_name = 'Notificacao')
ORDER BY table_schema, table_name, grantee, privilege_type;

SELECT c.oid::regclass AS relation,
       c.relrowsecurity,
       c.relforcerowsecurity,
       c.reloptions
FROM pg_class AS c
WHERE c.oid IN (
    'public."""Municipio"".""Notificacao"""'::regclass,
    '"Municipio"."Notificacao"'::regclass
)
ORDER BY 1;

SELECT n.nspname,
       c.relname,
       t.tgname,
       t.tgenabled,
       t.tgisinternal,
       pg_get_triggerdef(t.oid, true) AS triggerdef
FROM pg_trigger AS t
JOIN pg_class AS c
  ON c.oid = t.tgrelid
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE t.tgrelid IN (
    'public."""Municipio"".""Notificacao"""'::regclass,
    '"Municipio"."Notificacao"'::regclass
)
ORDER BY n.nspname, c.relname, t.tgname;

SELECT pg_describe_object(d.classid, d.objid, d.objsubid) AS object,
       pg_describe_object(d.refclassid, d.refobjid, d.refobjsubid) AS depends_on,
       d.deptype
FROM pg_depend AS d
WHERE d.objid = 'public."""Municipio"".""Notificacao"""'::regclass
   OR d.refobjid = 'public."""Municipio"".""Notificacao"""'::regclass
ORDER BY 1, 2;

SELECT schemaname,
       relname,
       seq_scan,
       seq_tup_read,
       idx_scan,
       idx_tup_fetch,
       n_tup_ins,
       n_tup_upd,
       n_tup_del,
       last_vacuum,
       last_autovacuum,
       last_analyze,
       last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'public'
  AND relname = '"Municipio"."Notificacao"';

SELECT pub.pubname,
       c.oid::regclass AS relation
FROM pg_publication_rel AS pr
JOIN pg_publication AS pub
  ON pub.oid = pr.prpubid
JOIN pg_class AS c
  ON c.oid = pr.prrelid
WHERE pr.prrelid = 'public."""Municipio"".""Notificacao"""'::regclass;

SELECT sub.subname,
       sr.srrelid::regclass AS relation,
       sr.srsubstate
FROM pg_subscription_rel AS sr
JOIN pg_subscription AS sub
  ON sub.oid = sr.srsubid
WHERE sr.srrelid = 'public."""Municipio"".""Notificacao"""'::regclass;

SELECT 'views' AS source,
       schemaname,
       viewname AS object_name
FROM pg_views
WHERE definition ILIKE '%public."""Municipio"".""Notificacao"""%'
UNION ALL
SELECT 'matviews' AS source,
       schemaname,
       matviewname AS object_name
FROM pg_matviews
WHERE definition ILIKE '%public."""Municipio"".""Notificacao"""%'
ORDER BY 1, 2, 3;

SELECT COUNT(*) AS row_count,
       COUNT(DISTINCT "ID_MUNICIP") AS distinct_municipalities,
       MIN(to_date("DT_NOTIFIC", 'YYYYMMDD')) AS min_notification_date,
       MAX(to_date("DT_NOTIFIC", 'YYYYMMDD')) AS max_notification_date,
       MIN(to_date("DT_SIN_PRI", 'YYYYMMDD')) AS min_symptom_date,
       MAX(to_date("DT_SIN_PRI", 'YYYYMMDD')) AS max_symptom_date,
       MIN("SEM_NOT"::integer) AS min_epiweek,
       MAX("SEM_NOT"::integer) AS max_epiweek,
       COUNT(*) FILTER (
           WHERE "NU_NOTIFIC" IS NULL OR btrim("NU_NOTIFIC") = ''
       ) AS null_nu_notific,
       COUNT(*) FILTER (
           WHERE "DT_NOTIFIC" IS NULL OR "DT_NOTIFIC" !~ '^[0-9]{8}$'
       ) AS invalid_dt_notific,
       COUNT(*) FILTER (
           WHERE "DT_SIN_PRI" IS NULL OR "DT_SIN_PRI" !~ '^[0-9]{8}$'
       ) AS invalid_dt_sin_pri,
       COUNT(*) FILTER (
           WHERE "NU_ANO" !~ '^[0-9]{4}$'
       ) AS invalid_year,
       COUNT(*) FILTER (
           WHERE "SEM_NOT" !~ '^[0-9]{6}$'
              OR substring("SEM_NOT" from 5 for 2)::integer NOT BETWEEN 1 AND 53
       ) AS invalid_week,
       COUNT(*) FILTER (
           WHERE "ID_MUNICIP" IS NULL OR "ID_MUNICIP" !~ '^[0-9]+$'
       ) AS invalid_municipio,
       COUNT(*) FILTER (
           WHERE "ID_AGRAVO" IS NULL OR btrim("ID_AGRAVO") = ''
       ) AS null_disease
FROM public."""Municipio"".""Notificacao""";

SELECT COUNT(*) AS duplicate_key_rows
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

SELECT btrim("ID_AGRAVO") AS disease_code,
       COUNT(*) AS row_count,
       MIN(to_date("DT_NOTIFIC", 'YYYYMMDD')) AS min_notification_date,
       MAX(to_date("DT_NOTIFIC", 'YYYYMMDD')) AS max_notification_date,
       MIN("SEM_NOT"::integer) AS min_epiweek,
       MAX("SEM_NOT"::integer) AS max_epiweek,
       COUNT(DISTINCT "ID_MUNICIP") AS distinct_municipalities,
       COUNT(*) FILTER (
           WHERE "NU_NOTIFIC" IS NULL
              OR "DT_NOTIFIC" IS NULL
              OR "ID_MUNICIP" IS NULL
       ) AS null_key_rows
FROM public."""Municipio"".""Notificacao"""
GROUP BY 1
ORDER BY 1;

SELECT "NU_ANO" AS year,
       btrim("ID_AGRAVO") AS disease_code,
       COUNT(*) AS row_count,
       COUNT(DISTINCT "ID_MUNICIP") AS distinct_municipalities,
       MIN(to_date("DT_NOTIFIC", 'YYYYMMDD')) AS min_date,
       MAX(to_date("DT_NOTIFIC", 'YYYYMMDD')) AS max_date
FROM public."""Municipio"".""Notificacao"""
GROUP BY 1, 2
ORDER BY 1, 2;

WITH latest AS (
    SELECT MAX(to_date("DT_NOTIFIC", 'YYYYMMDD')) AS latest_notification_date,
           MAX(to_date("DT_SIN_PRI", 'YYYYMMDD')) AS latest_symptom_date,
           MAX("SEM_NOT"::integer) AS latest_epiweek
    FROM public."""Municipio"".""Notificacao"""
)
SELECT latest_notification_date,
       latest_symptom_date,
       latest_epiweek,
       (
           SELECT COUNT(*)
           FROM public."""Municipio"".""Notificacao""" AS c
           WHERE to_date(c."DT_NOTIFIC", 'YYYYMMDD') = latest.latest_notification_date
       ) AS rows_in_latest_notification_date,
       (
           SELECT COUNT(DISTINCT btrim(c."ID_AGRAVO"))
           FROM public."""Municipio"".""Notificacao""" AS c
           WHERE to_date(c."DT_NOTIFIC", 'YYYYMMDD') = latest.latest_notification_date
       ) AS diseases_in_latest_notification_date,
       (
           SELECT COUNT(DISTINCT c."ID_MUNICIP")
           FROM public."""Municipio"".""Notificacao""" AS c
           WHERE to_date(c."DT_NOTIFIC", 'YYYYMMDD') = latest.latest_notification_date
       ) AS municipalities_in_latest_notification_date
FROM latest;

SELECT btrim("ID_AGRAVO") AS disease_code,
       COUNT(*) AS row_count
FROM public."""Municipio"".""Notificacao"""
WHERE to_date("DT_NOTIFIC", 'YYYYMMDD') = (
    SELECT MAX(to_date("DT_NOTIFIC", 'YYYYMMDD'))
    FROM public."""Municipio"".""Notificacao"""
)
GROUP BY 1
ORDER BY 1;

EXPLAIN
WITH candidate_buckets AS (
    SELECT btrim("ID_AGRAVO") AS disease_code,
           "SEM_NOT"::integer AS full_epiweek,
           "ID_MUNICIP"::integer AS municipio_geocodigo_base,
           COUNT(*) AS candidate_count
    FROM public."""Municipio"".""Notificacao"""
    GROUP BY 1, 2, 3
),
active_buckets AS (
    SELECT cid10_codigo AS disease_code,
           (ano_notif * 100) + se_notif AS full_epiweek,
           (municipio_geocodigo / 10) AS municipio_geocodigo_base,
           COUNT(*) AS active_count
    FROM "Municipio"."Notificacao"
    WHERE cid10_codigo = 'A90'
      AND ano_notif = 2022
    GROUP BY 1, 2, 3
)
SELECT COUNT(*)
FROM candidate_buckets AS c
FULL OUTER JOIN active_buckets AS a
  ON a.disease_code = c.disease_code
 AND a.full_epiweek = c.full_epiweek
 AND a.municipio_geocodigo_base = c.municipio_geocodigo_base
WHERE COALESCE(c.candidate_count, 0) <> COALESCE(a.active_count, 0);

WITH candidate AS (
    SELECT "NU_NOTIFIC"::bigint AS nu_notific,
           to_date("DT_NOTIFIC", 'YYYYMMDD') AS dt_notific,
           btrim("ID_AGRAVO") AS disease_code,
           "ID_MUNICIP"::integer AS municipio_geocodigo_base,
           NULLIF(btrim("CLASSI_FIN"), '')::numeric AS classi_fin,
           NULLIF(btrim("CRITERIO"), '')::numeric AS criterio
    FROM public."""Municipio"".""Notificacao"""
),
active AS (
    SELECT id,
           nu_notific,
           dt_notific,
           cid10_codigo AS disease_code,
           (municipio_geocodigo / 10) AS municipio_geocodigo_base,
           classi_fin,
           criterio
    FROM "Municipio"."Notificacao"
)
SELECT COUNT(*) AS candidate_rows,
       COUNT(a.*) AS matched_active_rows,
       COUNT(*) FILTER (WHERE a.id IS NULL) AS candidate_only_rows,
       COUNT(*) FILTER (
           WHERE a.id IS NOT NULL
             AND (
                 a.classi_fin IS DISTINCT FROM c.classi_fin
                 OR a.criterio IS DISTINCT FROM c.criterio
             )
       ) AS matched_rows_with_diff_columns
FROM candidate AS c
LEFT JOIN active AS a
  ON a.nu_notific = c.nu_notific
 AND a.dt_notific = c.dt_notific
 AND a.disease_code = c.disease_code
 AND a.municipio_geocodigo_base = c.municipio_geocodigo_base;

WITH candidate_municipios AS (
    SELECT DISTINCT "ID_MUNICIP"::integer AS municipio_geocodigo_base
    FROM public."""Municipio"".""Notificacao"""
),
candidate_keys AS (
    SELECT "NU_NOTIFIC"::bigint AS nu_notific,
           to_date("DT_NOTIFIC", 'YYYYMMDD') AS dt_notific,
           btrim("ID_AGRAVO") AS disease_code,
           "ID_MUNICIP"::integer AS municipio_geocodigo_base
    FROM public."""Municipio"".""Notificacao"""
),
active_scope AS (
    SELECT a.nu_notific,
           a.dt_notific,
           a.cid10_codigo AS disease_code,
           (a.municipio_geocodigo / 10) AS municipio_geocodigo_base
    FROM "Municipio"."Notificacao" AS a
    JOIN candidate_municipios AS cm
      ON (a.municipio_geocodigo / 10) = cm.municipio_geocodigo_base
    WHERE a.cid10_codigo = 'A90'
      AND a.ano_notif = 2022
)
SELECT COUNT(*) AS active_rows_in_candidate_municipios,
       COUNT(*) FILTER (WHERE ck.nu_notific IS NULL)
           AS active_only_rows_against_candidate_key
FROM active_scope AS a
LEFT JOIN candidate_keys AS ck
  ON ck.nu_notific = a.nu_notific
 AND ck.dt_notific = a.dt_notific
 AND ck.disease_code = a.disease_code
 AND ck.municipio_geocodigo_base = a.municipio_geocodigo_base;

WITH candidate_buckets AS (
    SELECT btrim("ID_AGRAVO") AS disease_code,
           "SEM_NOT"::integer AS full_epiweek,
           "ID_MUNICIP"::integer AS municipio_geocodigo_base,
           COUNT(*) AS candidate_count
    FROM public."""Municipio"".""Notificacao"""
    GROUP BY 1, 2, 3
),
active_buckets AS (
    SELECT cid10_codigo AS disease_code,
           (ano_notif * 100) + se_notif AS full_epiweek,
           (municipio_geocodigo / 10) AS municipio_geocodigo_base,
           COUNT(*) AS active_count
    FROM "Municipio"."Notificacao"
    WHERE cid10_codigo = 'A90'
      AND ano_notif = 2022
    GROUP BY 1, 2, 3
)
SELECT COUNT(*) FILTER (WHERE c.candidate_count = a.active_count)
           AS exact_matching_buckets,
       COUNT(*) FILTER (WHERE c.candidate_count IS DISTINCT FROM a.active_count)
           AS differing_buckets,
       COUNT(*) FILTER (
           WHERE c.candidate_count IS NOT NULL
             AND a.active_count IS NULL
             AND c.candidate_count > 0
       ) AS candidate_only_nonzero_buckets,
       COUNT(*) FILTER (
           WHERE a.active_count IS NOT NULL
             AND c.candidate_count IS NULL
             AND a.active_count > 0
       ) AS active_only_nonzero_buckets,
       COALESCE(SUM(c.candidate_count), 0) AS candidate_total,
       COALESCE(SUM(a.active_count), 0) AS aligned_active_total,
       COALESCE(SUM(a.active_count), 0) - COALESCE(SUM(c.candidate_count), 0)
           AS delta
FROM candidate_buckets AS c
FULL OUTER JOIN active_buckets AS a
  ON a.disease_code = c.disease_code
 AND a.full_epiweek = c.full_epiweek
 AND a.municipio_geocodigo_base = c.municipio_geocodigo_base;

COMMIT;
