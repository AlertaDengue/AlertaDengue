-- Machine-readable preflight inventory for archive export packaging.

BEGIN;

SET LOCAL statement_timeout = '60min';
SET LOCAL lock_timeout = '5s';
SET LOCAL temp_file_limit = '2GB';
SET TRANSACTION READ ONLY;

SELECT
    'SCHEMA' AS record_type,
    n.nspname AS schema_name,
    pg_get_userbyid(n.nspowner) AS owner,
    coalesce(array_to_string(n.nspacl, ','), '') AS acl,
    '' AS extra_1,
    '' AS extra_2
FROM pg_namespace AS n
WHERE n.nspname IN (
    'archive_redemet',
    'archive_upload',
    'archive_ovitrampa',
    'archive_alertas_regionais',
    'archive_cemaden',
    'archive_copernicus',
    'archive_historico_casos',
    'archive_mosqlimate',
    'archive_tweets'
)
ORDER BY n.nspname;

SELECT
    'OBJECT' AS record_type,
    n.nspname AS schema_name,
    c.relname AS object_name,
    c.relkind::text AS relkind,
    pg_get_userbyid(c.relowner) AS owner,
    pg_total_relation_size(c.oid)::text AS total_bytes
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE n.nspname IN (
    'archive_redemet',
    'archive_upload',
    'archive_ovitrampa',
    'archive_alertas_regionais',
    'archive_cemaden',
    'archive_copernicus',
    'archive_historico_casos',
    'archive_mosqlimate',
    'archive_tweets'
)
ORDER BY n.nspname, c.relkind, c.relname;

SELECT
    'ROWCOUNT' AS record_type,
    n.nspname AS schema_name,
    c.relname AS object_name,
    c.relkind::text AS relkind,
    (xpath('/row/count/text()', query_to_xml(format('SELECT count(*) AS count FROM %I.%I', n.nspname, c.relname), false, true, '')))[1]::text AS exact_row_count,
    '' AS extra_1
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE n.nspname IN (
    'archive_redemet',
    'archive_upload',
    'archive_ovitrampa',
    'archive_alertas_regionais',
    'archive_cemaden',
    'archive_copernicus',
    'archive_historico_casos',
    'archive_mosqlimate',
    'archive_tweets'
)
  AND c.relkind IN ('r', 'm')
ORDER BY n.nspname, c.relname;

SELECT
    'DEPENDENCY' AS record_type,
    obj_ns.nspname AS object_schema,
    obj.relname AS object_name,
    ref_ns.nspname AS depends_on_schema,
    ref.relname AS depends_on_name,
    d.deptype::text AS deptype
FROM pg_depend AS d
JOIN pg_class AS obj
  ON obj.oid = d.objid
JOIN pg_namespace AS obj_ns
  ON obj_ns.oid = obj.relnamespace
JOIN pg_class AS ref
  ON ref.oid = d.refobjid
JOIN pg_namespace AS ref_ns
  ON ref_ns.oid = ref.relnamespace
WHERE obj_ns.nspname IN (
    'archive_redemet',
    'archive_upload',
    'archive_ovitrampa',
    'archive_alertas_regionais',
    'archive_cemaden',
    'archive_copernicus',
    'archive_historico_casos',
    'archive_mosqlimate',
    'archive_tweets'
)
   OR ref_ns.nspname IN (
    'archive_redemet',
    'archive_upload',
    'archive_ovitrampa',
    'archive_alertas_regionais',
    'archive_cemaden',
    'archive_copernicus',
    'archive_historico_casos',
    'archive_mosqlimate',
    'archive_tweets'
)
ORDER BY object_schema, object_name, depends_on_schema, depends_on_name, deptype;

ROLLBACK;
