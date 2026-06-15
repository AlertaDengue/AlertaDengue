-- Archive legacy airport-station data before removal.
-- Run as the database owner after auditing external varclimate loaders.

BEGIN;

CREATE SCHEMA IF NOT EXISTS archive_redemet;
REVOKE ALL ON SCHEMA archive_redemet FROM PUBLIC;

DO $archive$
BEGIN
    IF to_regclass('"Municipio"."Clima_wu"') IS NOT NULL THEN
        CREATE TABLE archive_redemet.clima_wu
            (LIKE "Municipio"."Clima_wu" INCLUDING ALL);
        ALTER TABLE archive_redemet.clima_wu
            ALTER COLUMN id DROP DEFAULT;
        INSERT INTO archive_redemet.clima_wu
        SELECT * FROM "Municipio"."Clima_wu";
    END IF;

    IF to_regclass('"Municipio"."Estacao_wu"') IS NOT NULL THEN
        CREATE TABLE archive_redemet.estacao_wu
            (LIKE "Municipio"."Estacao_wu" INCLUDING ALL);
        INSERT INTO archive_redemet.estacao_wu
        SELECT * FROM "Municipio"."Estacao_wu";
    END IF;
END
$archive$;

CREATE TABLE archive_redemet.parameters_station_codes AS
SELECT municipio_geocodigo, cid10, codigo_estacao_wu, estacao_wu_sec
FROM "Dengue_global".parameters
WHERE codigo_estacao_wu IS NOT NULL OR estacao_wu_sec IS NOT NULL;

CREATE TABLE archive_redemet.regional_saude_station_codes AS
SELECT municipio_geocodigo, codigo_estacao_wu, estacao_wu_sec
FROM "Dengue_global".regional_saude
WHERE codigo_estacao_wu IS NOT NULL OR estacao_wu_sec IS NOT NULL;

CREATE TABLE archive_redemet.localidade_station_codes AS
SELECT id, "Municipio_geocodigo", codigo_estacao_wu
FROM "Municipio"."Localidade"
WHERE codigo_estacao_wu IS NOT NULL;

CREATE TABLE archive_redemet.manifest (
    archived_at timestamptz NOT NULL DEFAULT now(),
    source_table text NOT NULL,
    archive_table text NOT NULL,
    row_count bigint NOT NULL
);

INSERT INTO archive_redemet.manifest (source_table, archive_table, row_count)
SELECT 'Municipio.Clima_wu', 'archive_redemet.clima_wu', count(*)
FROM archive_redemet.clima_wu
UNION ALL
SELECT 'Municipio.Estacao_wu', 'archive_redemet.estacao_wu', count(*)
FROM archive_redemet.estacao_wu
UNION ALL
SELECT 'Dengue_global.parameters station codes',
       'archive_redemet.parameters_station_codes', count(*)
FROM archive_redemet.parameters_station_codes
UNION ALL
SELECT 'Dengue_global.regional_saude station codes',
       'archive_redemet.regional_saude_station_codes', count(*)
FROM archive_redemet.regional_saude_station_codes
UNION ALL
SELECT 'Municipio.Localidade station codes',
       'archive_redemet.localidade_station_codes', count(*)
FROM archive_redemet.localidade_station_codes;

COMMIT;
