-- Remove archived legacy airport-station objects.
-- Run after 20260612_01_archive_legacy_redemet.sql and archive validation.

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DO $guard$
BEGIN
    IF to_regclass('archive_redemet.manifest') IS NULL THEN
        RAISE EXCEPTION 'archive_redemet.manifest is required';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM archive_redemet.manifest
        WHERE source_table = 'Municipio.Clima_wu'
    ) THEN
        RAISE EXCEPTION 'Clima_wu archive validation is missing';
    END IF;
END
$guard$;

-- INCLUDING ALL copied source sequence defaults into archives made by the
-- original archive script. Detach them before dropping the source tables.
ALTER TABLE archive_redemet.clima_wu
    ALTER COLUMN id DROP DEFAULT;

ALTER TABLE "Dengue_global".parameters
    DROP COLUMN IF EXISTS codigo_estacao_wu,
    DROP COLUMN IF EXISTS estacao_wu_sec;

ALTER TABLE "Dengue_global".regional_saude
    DROP COLUMN IF EXISTS codigo_estacao_wu,
    DROP COLUMN IF EXISTS estacao_wu_sec;

ALTER TABLE "Municipio"."Localidade"
    DROP COLUMN IF EXISTS codigo_estacao_wu;

-- Deliberately omit CASCADE: unknown database dependencies must stop removal.
DROP TABLE IF EXISTS "Municipio"."Clima_wu";
DROP TABLE IF EXISTS "Municipio"."Estacao_wu";

COMMIT;
