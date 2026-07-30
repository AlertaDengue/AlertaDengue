-- Remove the completed archive schemas after verified export and restore.
-- Explicit manifest only. No CASCADE.

DO $$
BEGIN
    IF current_setting('archive.removal_authorized', true) IS DISTINCT FROM '1'
       OR current_setting('archive.package_path', true) IS NULL
       OR current_setting('archive.dump_sha256', true) IS NULL
       OR current_setting('archive.verification_receipt_sha256', true) IS NULL
       OR current_setting('archive.source_database_oid', true) IS NULL
       OR current_setting('archive.source_inventory_sha256', true) IS NULL
       OR current_setting('archive.source_row_counts_sha256', true) IS NULL THEN
        RAISE EXCEPTION 'Direct execution is not supported. Use archive_schemas_workflow.sh remove with a verified persistent package.';
    END IF;
END
$$;

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60min';

DO $$
DECLARE
    protected_before record;
    protected_after record;
BEGIN
    IF current_setting('archive.removal_authorized', true) IS DISTINCT FROM '1'
       OR current_setting('archive.package_path', true) IS NULL
       OR current_setting('archive.dump_sha256', true) IS NULL
       OR current_setting('archive.verification_receipt_sha256', true) IS NULL
       OR current_setting('archive.source_database_oid', true) IS NULL
       OR current_setting('archive.source_inventory_sha256', true) IS NULL
       OR current_setting('archive.source_row_counts_sha256', true) IS NULL THEN
        RAISE EXCEPTION 'Direct execution is not supported. Use archive_schemas_workflow.sh remove with a verified persistent package.';
    END IF;

    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION 'refuse archive schema removal while PostgreSQL is in recovery';
    END IF;

    CREATE TEMP TABLE protected_snapshot (
        schema_name text,
        relation_name text,
        oid oid,
        owner_name text
    ) ON COMMIT DROP;

    INSERT INTO protected_snapshot (schema_name, relation_name, oid, owner_name)
    SELECT
        n.nspname,
        c.relname,
        c.oid,
        pg_get_userbyid(c.relowner)
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE (n.nspname, c.relname) IN (
        ('Municipio', 'Notificacao'),
        ('weather', 'copernicus_bra'),
        ('Dengue_global', 'regional_saude'),
        ('Dengue_global', 'regional'),
        ('Dengue_global', 'CID10')
    );

    IF (SELECT count(*) FROM protected_snapshot) <> 5 THEN
        RAISE EXCEPTION 'protected active object snapshot is incomplete';
    END IF;

    -- alertas regionais
    DROP TABLE archive_alertas_regionais.alerta_mrj;
    DROP TABLE archive_alertas_regionais.alerta_mrj_chik;
    DROP TABLE archive_alertas_regionais.alerta_mrj_zika;
    DROP TABLE archive_alertas_regionais.alerta_regional_chik;
    DROP TABLE archive_alertas_regionais.alerta_regional_dengue;
    DROP TABLE archive_alertas_regionais.alerta_regional_zika;
    DROP SCHEMA archive_alertas_regionais;

    -- cemaden
    DROP TABLE archive_cemaden."Clima_cemaden";
    DROP TABLE archive_cemaden."Estacao_cemaden";
    DROP SCHEMA archive_cemaden;

    -- copernicus
    DROP TABLE archive_copernicus.copernicus_arg;
    DROP TABLE archive_copernicus.copernicus_foz_do_iguacu;
    DROP SCHEMA archive_copernicus;

    -- historico_casos
    DROP MATERIALIZED VIEW archive_historico_casos.historico_casos;
    DROP SCHEMA archive_historico_casos;

    -- mosqlimate
    DROP TABLE archive_mosqlimate.sprint202425;
    DROP SCHEMA archive_mosqlimate;

    -- ovitrampa
    DROP TABLE archive_ovitrampa."Bairro";
    DROP TABLE archive_ovitrampa."Ovitrampa";
    DROP TABLE archive_ovitrampa."Localidade";
    DROP SCHEMA archive_ovitrampa;

    -- redemet
    DROP TABLE archive_redemet.clima_wu;
    DROP TABLE archive_redemet.estacao_wu;
    DROP TABLE archive_redemet.localidade_station_codes;
    DROP TABLE archive_redemet.manifest;
    DROP TABLE archive_redemet.parameters_station_codes;
    DROP TABLE archive_redemet.regional_saude_station_codes;
    DROP SCHEMA archive_redemet;

    -- tweets
    DROP TABLE archive_tweets."Tweet";
    DROP SCHEMA archive_tweets;

    -- upload
    DROP TABLE archive_upload.chunked_upload;
    DROP TABLE archive_upload.manifest;
    DROP TABLE archive_upload.sinan_chunked_upload;
    DROP TABLE archive_upload.sinan_upload;
    DROP TABLE archive_upload.sinan_upload_log_status;
    DROP SCHEMA archive_upload;

    FOR protected_before IN
        SELECT * FROM protected_snapshot ORDER BY schema_name, relation_name
    LOOP
        SELECT
            c.oid AS oid,
            pg_get_userbyid(c.relowner) AS owner_name
          INTO protected_after
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = protected_before.schema_name
          AND c.relname = protected_before.relation_name;

        IF protected_after.oid IS NULL THEN
            RAISE EXCEPTION 'protected object %.% disappeared during removal',
                protected_before.schema_name, protected_before.relation_name;
        END IF;

        IF protected_after.oid <> protected_before.oid THEN
            RAISE EXCEPTION 'protected object %.% changed OID from % to %',
                protected_before.schema_name, protected_before.relation_name,
                protected_before.oid, protected_after.oid;
        END IF;

        IF protected_after.owner_name <> protected_before.owner_name THEN
            RAISE EXCEPTION 'protected object %.% changed owner from % to %',
                protected_before.schema_name, protected_before.relation_name,
                protected_before.owner_name, protected_after.owner_name;
        END IF;
    END LOOP;

    IF EXISTS (
        SELECT 1
        FROM pg_namespace
        WHERE nspname IN (
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
    ) THEN
        RAISE EXCEPTION 'one or more archive schemas remain after removal';
    END IF;
END
$$;

COMMIT;
