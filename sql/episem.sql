-- EXAMPLE
-- SELECT
--     epi_week(NOW()::DATE),
--     epi_week(NOW()::DATE-7*3) as A,
--     epi_week(NOW()::DATE-7*52) AS B,
--     epi_week(NOW()::DATE-7*55) AS C;
CREATE OR REPLACE FUNCTION epi_week(IN dt date) RETURNS INTEGER
AS $$

DECLARE epiyear INTEGER;
DECLARE epiend DATE;
DECLARE epistart DATE;
DECLARE epi_dow INTEGER;
DECLARE epiweek INTEGER;

BEGIN
    epiyear = EXTRACT(YEAR FROM dt);
    epiend = CONCAT(CAST(epiyear AS VARCHAR), '-12-31')::DATE;
    epi_dow = EXTRACT(DOW FROM epiend);

    -- Last epiday
    IF epi_dow < 3 THEN
        epiend = epiend - CAST(CAST(epi_dow+1 AS VARCHAR) || ' DAY' AS INTERVAL);
    ELSE
        epiend = epiend + CAST(CAST(6-epi_dow AS VARCHAR) || ' DAY' AS INTERVAL);
    END IF;

    IF dt > epiend THEN
        epiyear = epiyear + 1;
        RETURN epiyear*100 + 01;
    END IF;

    -- First epiday
    epistart = CONCAT(CAST(epiyear AS VARCHAR), '-01-01')::DATE;
    epi_dow = EXTRACT(DOW FROM epistart);

    IF epi_dow < 4 THEN
        epistart = epistart - CAST(CAST(epi_dow AS VARCHAR) || ' DAY' AS INTERVAL);
    ELSE
        epistart = epistart + CAST(CAST(7-epi_dow AS VARCHAR) || ' DAY' AS INTERVAL);
    END IF;

    -- If current date is before its year first epiweek,
    -- then our base year is the previous one
    IF dt < epistart THEN
    epiyear = epiyear-1;

    epistart = CONCAT(CAST(epiyear AS VARCHAR), '-01-01')::DATE;
        epi_dow = EXTRACT(DOW FROM epistart);

        -- First epiday
        IF epi_dow < 4 THEN
        epistart = epistart - CAST(CAST(epi_dow AS VARCHAR) || ' DAY' AS INTERVAL);
        ELSE
            epistart = epistart + CAST(CAST(7-epi_dow AS VARCHAR) || ' DAY' AS INTERVAL);
        END IF;
    END IF;
    --epiweek = int(((x - epistart)/7).days) + 1
    epiweek = ((dt - epistart)/7)+1;
    --raise notice '%', ((dt - epistart)/7)+1;

    RETURN epiyear*100 + epiweek;
END;
$$
LANGUAGE plpgsql;
