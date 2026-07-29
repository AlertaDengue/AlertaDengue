-- Read-only removal preflight for the completed archive schemas.

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
    expected_relations constant text[] := ARRAY[
        'archive_alertas_regionais.alerta_mrj',
        'archive_alertas_regionais.alerta_mrj_chik',
        'archive_alertas_regionais.alerta_mrj_zika',
        'archive_alertas_regionais.alerta_regional_chik',
        'archive_alertas_regionais.alerta_regional_dengue',
        'archive_alertas_regionais.alerta_regional_zika',
        'archive_cemaden."Clima_cemaden"',
        'archive_cemaden."Estacao_cemaden"',
        'archive_copernicus.copernicus_arg',
        'archive_copernicus.copernicus_foz_do_iguacu',
        'archive_historico_casos.historico_casos',
        'archive_mosqlimate.sprint202425',
        'archive_ovitrampa."Bairro"',
        'archive_ovitrampa."Localidade"',
        'archive_ovitrampa."Ovitrampa"',
        'archive_redemet.clima_wu',
        'archive_redemet.estacao_wu',
        'archive_redemet.localidade_station_codes',
        'archive_redemet.manifest',
        'archive_redemet.parameters_station_codes',
        'archive_redemet.regional_saude_station_codes',
        'archive_tweets."Tweet"',
        'archive_upload.chunked_upload',
        'archive_upload.manifest',
        'archive_upload.sinan_chunked_upload',
        'archive_upload.sinan_upload',
        'archive_upload.sinan_upload_log_status'
    ];
    missing_schemas text[];
    unexpected_schemas text[];
    unexpected_relation_count integer;
    active_to_archive_count integer;
    protected_missing_count integer;
    bad_fk_count integer;
BEGIN
    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION 'refuse removal preflight while PostgreSQL is in recovery';
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
      INTO unexpected_relation_count
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = ANY(approved_schemas)
      AND c.relkind IN ('r', 'm')
      AND format('%I.%I', n.nspname, c.relname) <> ALL(expected_relations);

    IF unexpected_relation_count <> 0 THEN
        RAISE EXCEPTION 'unexpected relation count inside approved archive schemas: %', unexpected_relation_count;
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
        RAISE EXCEPTION 'active object depends on archive object count: %', active_to_archive_count;
    END IF;

    SELECT count(*)
      INTO bad_fk_count
    FROM pg_constraint AS con
    JOIN pg_namespace AS src_ns
      ON src_ns.oid = con.connamespace
    JOIN pg_class AS ref_cls
      ON ref_cls.oid = con.confrelid
    JOIN pg_namespace AS ref_ns
      ON ref_ns.oid = ref_cls.relnamespace
    WHERE con.contype = 'f'
      AND src_ns.nspname = ANY(approved_schemas)
      AND (
            (
                ref_ns.nspname NOT LIKE 'archive_%'
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
                )
            )
            OR (
                ref_ns.nspname LIKE 'archive_%'
                AND (
                    (con.conrelid::regclass::text, con.conname, con.confrelid::regclass::text) NOT IN (
                        VALUES
                            ('archive_ovitrampa."Bairro"'::text, 'Bairro_Localidade', 'archive_ovitrampa."Localidade"'::text),
                            ('archive_ovitrampa."Ovitrampa"'::text, 'Ovitrampa_Localidade', 'archive_ovitrampa."Localidade"'::text)
                    )
                    OR con.convalidated IS NOT TRUE
                    OR con.confdeltype <> 'a'
                    OR con.confupdtype <> 'a'
                )
            )
      );

    IF bad_fk_count <> 0 THEN
        RAISE EXCEPTION 'archive foreign-key policy mismatch count: %', bad_fk_count;
    END IF;

    SELECT count(*)
      INTO protected_missing_count
    FROM (
        VALUES
            ('Municipio', 'Notificacao'),
            ('weather', 'copernicus_bra'),
            ('Dengue_global', 'regional_saude'),
            ('Dengue_global', 'regional'),
            ('Dengue_global', 'CID10')
    ) AS protected(schema_name, relation_name)
    WHERE to_regclass(format('%I.%I', protected.schema_name, protected.relation_name)) IS NULL;

    IF protected_missing_count <> 0 THEN
        RAISE EXCEPTION 'one or more protected active objects are missing';
    END IF;
END
$$;

SELECT
    n.nspname AS schema_name,
    c.relname,
    c.relkind,
    c.oid,
    pg_get_userbyid(c.relowner) AS owner
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
