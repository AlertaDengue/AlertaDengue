-- EXAMPLE
-- SELECT
--     epiweek2date(201801),
--     epiweek2date(201801, 0) as A
CREATE OR REPLACE FUNCTION epiweek2date(IN epi_year_week int, IN weekday int=0) 
RETURNS DATE AS $$

DECLARE epiyear INTEGER;
DECLARE epiweek INTEGER;
DECLARE date_1 DATE;
DECLARE date_1_w INTEGER;
DECLARE epiweek_day_1 DATE;
DECLARE epi_interval INTERVAL;

BEGIN
    IF epi_year_week < 190000 THEN
        RAISE EXCEPTION 'INVALID epi_year_week value.';
    END IF;
    
    epiyear = epi_year_week/100;
    epiweek = CAST((epi_year_week/100.0) % 1 * 100 AS INT);
    date_1 = CAST(epiyear::varchar || '-01-01' AS DATE);
    date_1_w = EXTRACT(DOW FROM date_1);

    IF date_1_w <=3 THEN
	epi_interval = (date_1_w::varchar || ' days')::interval;
        epiweek_day_1 = date_1 - epi_interval;
    ELSE
        epi_interval = ((7-date_1_w)::varchar || ' days')::interval;
	epiweek_day_1 = date_1 + epi_interval;
    END IF; 
    
    epi_interval = ((7 * (epiweek-1) + weekday) || ' days')::interval;
    RETURN epiweek_day_1 + epi_interval;
END;
$$
LANGUAGE plpgsql;
