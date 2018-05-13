-- EXAMPLE
-- SELECT
--     epiweek2date(201801),
--     epiweek2date(201801, 0) as A
CREATE OR REPLACE FUNCTION epiweek2date(IN epi_year_week int, IN weekday int=0) RETURNS DATE
AS $$

DECLARE epiyear INTEGER;
DECLARE epiweek INTEGER;
DECLARE date_1 DATE;

BEGIN
    IF (epi_year_week < 190000 THEN
      RAISE EXCEPTION 'INVALID epi_year_week value.'
    END IF;
    
    epiyear = epi_year_week/100;
    epiweek = CAST((epi_year_week/100.0) % 1 * 100 AS INT);
    date_1 = CAST(epiyear::varchar || '-01-01' AS DATE)
    RETURN NOW()
END;
$$
LANGUAGE plpgsql;
