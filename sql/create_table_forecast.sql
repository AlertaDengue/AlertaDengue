CREATE TABLE IF NOT EXISTS "Municipio".forecast (
    epiweek INT NOT NULL,
    geoid INT NOT NULL,
    cases INT NOT NULL,
    model_id VARCHAR(128) NOT NULL,
    commit_id CHAR(7) NOT NULL,
    PRIMARY KEY (epiweek, geoid)
)