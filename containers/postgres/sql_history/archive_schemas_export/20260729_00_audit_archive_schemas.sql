-- LEGACY NINE-SCHEMA-ONLY AUDIT.
-- This historical raw SQL audit intentionally validates the original nine
-- archive schemas as one complete set. It is not the audit path for selected
-- exports. For selected schemas, use archive_schemas_workflow.sh --schemas.
-- Read-only, fails on safety mismatches.

BEGIN;

SET LOCAL statement_timeout = '60min';
SET LOCAL lock_timeout = '5s';
SET LOCAL temp_file_limit = '2GB';
SET TRANSACTION READ ONLY;

DO $$
DECLARE
    approved_schemas constant text[] := ARRAY[
        'archive_redemet',
        'archive_upload',
        'archive_ovitrampa',
        'archive_alertas_regionais',
        'archive_cemaden',
        'archive_copernicus',
        'archive_historico_casos',
        'archive_mosqlimate',
        'archive_tweets'
    ];
    missing_schemas text[];
    unexpected_schemas text[];
    unsupported_count integer;
    active_to_archive_count integer;
    fk_mismatch_count integer;
    invalid_index_count integer;
    invalid_constraint_count integer;
    unowned_sequence_count integer;
BEGIN
    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION 'refuse audit while PostgreSQL is in recovery';
    END IF;

    SELECT array_agg(s ORDER BY s)
      INTO missing_schemas
    FROM unnest(approved_schemas) AS s
    WHERE to_regnamespace(s) IS NULL;

    IF missing_schemas IS NOT NULL THEN
        RAISE EXCEPTION 'missing approved archive schemas: %', missing_schemas;
    END IF;

    SELECT array_agg(n.nspname ORDER BY n.nspname)
      INTO unexpected_schemas
    FROM pg_namespace AS n
    WHERE n.nspname LIKE 'archive_%'
      AND NOT (n.nspname = ANY(approved_schemas));

    IF unexpected_schemas IS NOT NULL THEN
        RAISE EXCEPTION 'unexpected archive schemas found: %', unexpected_schemas;
    END IF;

    SELECT count(*)
      INTO unsupported_count
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = ANY(approved_schemas)
      AND c.relkind NOT IN ('r', 'm', 'S', 'i', 't');

    IF unsupported_count <> 0 THEN
        RAISE EXCEPTION 'unsupported archive object types found: %', unsupported_count;
    END IF;

    SELECT count(*)
      INTO fk_mismatch_count
    FROM pg_constraint AS con
    JOIN pg_namespace AS src_ns
      ON src_ns.oid = con.connamespace
    JOIN pg_class AS src_cls
      ON src_cls.oid = con.conrelid
    JOIN pg_namespace AS ref_ns
      ON ref_ns.oid = (
            SELECT c.relnamespace
            FROM pg_class AS c
            WHERE c.oid = con.confrelid
      )
    WHERE con.contype = 'f'
      AND src_ns.nspname = ANY(approved_schemas)
      AND ref_ns.nspname NOT LIKE 'archive_%'
      AND (
            (con.conrelid::regclass::text, con.conname, con.confrelid::regclass::text) NOT IN (
                VALUES
                    ('archive_alertas_regionais.alerta_regional_chik'::text, 'regional_fk', '"Dengue_global".regional'::text),
                    ('archive_alertas_regionais.alerta_regional_dengue'::text, 'regional_fk', '"Dengue_global".regional'::text),
                    ('archive_alertas_regionais.alerta_regional_zika'::text, 'regional_fk', '"Dengue_global".regional'::text),
                    ('archive_tweets."Tweet"'::text, 'Tweet_CID10', '"Dengue_global"."CID10"'::text)
            )
            OR con.convalidated IS NOT TRUE
            OR con.confdeltype <> 'a'
            OR con.confupdtype <> 'a'
      );

    IF fk_mismatch_count <> 0 THEN
        RAISE EXCEPTION 'archive external foreign-key policy mismatch count: %', fk_mismatch_count;
    END IF;

    SELECT count(*)
      INTO active_to_archive_count
    FROM pg_depend AS d
    JOIN pg_class AS obj
      ON obj.oid = d.objid
    JOIN pg_namespace AS obj_ns
      ON obj_ns.oid = obj.relnamespace
    JOIN pg_class AS ref
      ON ref.oid = d.refobjid
    JOIN pg_namespace AS ref_ns
      ON ref_ns.oid = ref.relnamespace
    WHERE ref_ns.nspname = ANY(approved_schemas)
      AND obj_ns.nspname NOT LIKE 'archive_%'
      AND obj_ns.nspname <> 'pg_toast';

    IF active_to_archive_count <> 0 THEN
        RAISE EXCEPTION 'active-to-archive dependency count is not zero: %', active_to_archive_count;
    END IF;

    SELECT count(*)
      INTO invalid_index_count
    FROM pg_index AS i
    JOIN pg_class AS idx
      ON idx.oid = i.indexrelid
    JOIN pg_namespace AS idx_ns
      ON idx_ns.oid = idx.relnamespace
    WHERE idx_ns.nspname = ANY(approved_schemas)
      AND NOT i.indisvalid;

    IF invalid_index_count <> 0 THEN
        RAISE EXCEPTION 'invalid archive indexes found: %', invalid_index_count;
    END IF;

    SELECT count(*)
      INTO invalid_constraint_count
    FROM pg_constraint AS con
    JOIN pg_namespace AS n
      ON n.oid = con.connamespace
    WHERE n.nspname = ANY(approved_schemas)
      AND con.contype IN ('p', 'u', 'f', 'x')
      AND con.convalidated IS NOT TRUE;

    IF invalid_constraint_count <> 0 THEN
        RAISE EXCEPTION 'invalid or unvalidated archive constraints found: %', invalid_constraint_count;
    END IF;

    SELECT count(*)
      INTO unowned_sequence_count
    FROM pg_class AS seq
    JOIN pg_namespace AS seq_ns
      ON seq_ns.oid = seq.relnamespace
    WHERE seq_ns.nspname = ANY(approved_schemas)
      AND seq.relkind = 'S'
      AND NOT EXISTS (
            SELECT 1
            FROM pg_depend AS dep
            WHERE dep.objid = seq.oid
              AND dep.deptype IN ('a', 'i')
      )
      AND seq.relname NOT IN (
            'alerta_regional_chik_id_seq',
            'alerta_regional_dengue_id_seq',
            'alerta_regional_zika_id_seq',
            'alerta_mrj_id_seq',
            'alerta_mrj_chik_id_seq',
            'alerta_mrj_zika_id_seq',
            'Clima_cemaden_id_seq',
            'copernicus_foz_do_iguacu_index_seq',
            'sprint202425_id_seq',
            'Bairro_id_seq',
            'Ovitrampa_id_seq',
            'Tweet_id_seq'
      );

    IF unowned_sequence_count <> 0 THEN
        RAISE EXCEPTION 'unexpected unowned archive sequences found: %', unowned_sequence_count;
    END IF;
END
$$;

SELECT current_database() AS database_name, version() AS server_version;

SELECT
    n.nspname AS schema_name,
    pg_get_userbyid(n.nspowner) AS owner,
    array_to_string(n.nspacl, ',') AS acl
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
    n.nspname AS schema_name,
    c.relname,
    c.relkind,
    c.oid,
    pg_get_userbyid(c.relowner) AS owner,
    c.relacl,
    pg_total_relation_size(c.oid) AS total_bytes,
    obj_description(c.oid, 'pg_class') AS comment
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
    n.nspname AS schema_name,
    c.relname,
    c.relkind,
    CASE
        WHEN c.relkind IN ('r', 'm') THEN
            (xpath('/row/count/text()', query_to_xml(format('SELECT count(*) AS count FROM %I.%I', n.nspname, c.relname), false, true, '')))[1]::text::bigint
        ELSE NULL
    END AS exact_row_count
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
    connamespace::regnamespace::text AS schema_name,
    conrelid::regclass::text AS source_table,
    conname,
    confrelid::regclass::text AS referenced_table,
    convalidated,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE contype = 'f'
  AND connamespace::regnamespace::text IN (
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
ORDER BY schema_name, source_table, conname;

SELECT
    obj_ns.nspname AS object_schema,
    obj.relname AS object_name,
    obj.relkind AS object_kind,
    ref_ns.nspname AS depends_on_schema,
    ref.relname AS depends_on_name,
    ref.relkind AS depends_on_kind,
    d.deptype
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
ORDER BY object_schema, object_name, depends_on_schema, depends_on_name, d.deptype;

SELECT
    n.nspname AS schema_name,
    c.relname,
    c.relkind,
    c.oid,
    pg_get_userbyid(c.relowner) AS owner,
    c.relacl,
    pg_total_relation_size(c.oid) AS total_bytes,
    obj_description(c.oid, 'pg_class') AS comment
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE (n.nspname, c.relname) IN (
    ('Municipio', 'Notificacao'),
    ('weather', 'copernicus_bra'),
    ('Dengue_global', 'regional_saude'),
    ('Dengue_global', 'regional'),
    ('Dengue_global', 'CID10')
)
ORDER BY n.nspname, c.relname;

ROLLBACK;
