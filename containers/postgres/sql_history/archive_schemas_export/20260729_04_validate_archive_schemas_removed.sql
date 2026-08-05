-- Validate only the selected upload archive schemas are absent and protected
-- active objects remain present.

BEGIN;

SET LOCAL statement_timeout = '60min';
SET LOCAL lock_timeout = '5s';
SET LOCAL temp_file_limit = '2GB';
SET TRANSACTION READ ONLY;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_namespace
        WHERE nspname IN ('archive_dbf_upload', 'archive_sinan_upload')
    ) THEN
        RAISE EXCEPTION 'archive schemas still exist after removal';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname IN ('archive_dbf_upload', 'archive_sinan_upload')
    ) THEN
        RAISE EXCEPTION 'archive-owned residual relations still exist';
    END IF;

    IF to_regclass('"Municipio"."Notificacao"') IS NULL
       OR to_regclass('weather.copernicus_bra') IS NULL
       OR to_regclass('"Dengue_global".regional_saude') IS NULL
       OR to_regclass('"Dengue_global".regional') IS NULL
       OR to_regclass('"Dengue_global"."CID10"') IS NULL THEN
        RAISE EXCEPTION 'one or more protected active objects are missing after removal';
    END IF;

    IF to_regclass('public."""Municipio"".""Notificacao"""') IS NOT NULL
       OR to_regclass('"Municipio"."Notificacao__20220806"') IS NOT NULL
       OR to_regclass('"Municipio"."Corrigido2022"') IS NOT NULL
       OR to_regclass('"Municipio"."Clima_Satelite"') IS NOT NULL
       OR to_regclass('"Municipio"."Clima_Satelite_id_seq"') IS NOT NULL THEN
        RAISE EXCEPTION 'completed cleanup objects unexpectedly reappeared';
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
