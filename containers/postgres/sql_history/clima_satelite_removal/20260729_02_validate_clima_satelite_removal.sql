-- Validate that "Municipio"."Clima_Satelite" was removed without touching
-- unrelated climate objects.

BEGIN;

SET LOCAL statement_timeout = '10min';
SET LOCAL lock_timeout = '5s';
SET LOCAL temp_file_limit = '256MB';
SET TRANSACTION READ ONLY;

DO $$
DECLARE
    keep_table_oid oid;
    keep_table_rows bigint;
    keep_weather_oid oid;
    keep_weather_rows bigint;
BEGIN
    IF to_regclass('"Municipio"."Clima_Satelite"') IS NOT NULL THEN
        RAISE EXCEPTION '"Municipio"."Clima_Satelite" still exists';
    END IF;

    IF to_regclass('"Municipio"."Clima_Satelite_id_seq"') IS NOT NULL THEN
        RAISE EXCEPTION '"Municipio"."Clima_Satelite_id_seq" still exists';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname IN (
              'Clima_Satelite_pk',
              'Clima_Satelite_idx_data',
              'Clima_Satelite_id_seq'
          )
    ) THEN
        RAISE EXCEPTION 'residual Clima_Satelite relation remains after removal';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_type AS t
        JOIN pg_namespace AS n
          ON n.oid = t.typnamespace
        WHERE n.nspname = 'Municipio'
          AND t.typname = 'Clima_Satelite'
    ) THEN
        RAISE EXCEPTION 'residual row type Municipio.Clima_Satelite remains after removal';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_trigger AS trg
        JOIN pg_class AS c
          ON c.oid = trg.tgrelid
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname = 'Clima_Satelite'
          AND NOT trg.tgisinternal
    ) THEN
        RAISE EXCEPTION 'residual trigger remains for Municipio.Clima_Satelite';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_rewrite AS rw
        JOIN pg_class AS c
          ON c.oid = rw.ev_class
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'Municipio'
          AND c.relname = 'Clima_Satelite'
    ) THEN
        RAISE EXCEPTION 'residual rule remains for Municipio.Clima_Satelite';
    END IF;

    SELECT c.oid
      INTO keep_table_oid
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = 'Municipio'
      AND c.relname = 'Clima_Keep'
      AND c.relkind = 'r';

    IF keep_table_oid IS NULL THEN
        RAISE EXCEPTION 'fixture "Municipio"."Clima_Keep" is required for safety validation';
    END IF;

    EXECUTE 'SELECT count(*) FROM "Municipio"."Clima_Keep"' INTO keep_table_rows;

    IF keep_table_rows <> 1 THEN
        RAISE EXCEPTION
            'fixture "Municipio"."Clima_Keep" row count changed from expected 1 to %',
            keep_table_rows;
    END IF;

    SELECT c.oid
      INTO keep_weather_oid
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = 'weather'
      AND c.relname = 'climate_keep'
      AND c.relkind = 'r';

    IF keep_weather_oid IS NULL THEN
        RAISE EXCEPTION 'fixture weather.climate_keep is required for safety validation';
    END IF;

    EXECUTE 'SELECT count(*) FROM weather.climate_keep' INTO keep_weather_rows;

    IF keep_weather_rows <> 1 THEN
        RAISE EXCEPTION
            'fixture weather.climate_keep row count changed from expected 1 to %',
            keep_weather_rows;
    END IF;
END
$$;

SELECT
    n.nspname AS schema_name,
    c.relname,
    c.oid,
    c.relkind,
    pg_get_userbyid(c.relowner) AS owner,
    pg_total_relation_size(c.oid) AS total_bytes
FROM pg_class AS c
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE (n.nspname = 'Municipio' AND c.relname = 'Clima_Keep')
   OR (n.nspname = 'weather' AND c.relname = 'climate_keep')
ORDER BY n.nspname, c.relname;

ROLLBACK;
