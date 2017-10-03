CREATE TABLE IF NOT EXISTS "Municipio".forecast_model (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    total_weeks SMALLINT NOT NULL,
    commit_id CHAR(7) NOT NULL,
    active BOOL NOT NULL
);

CREATE TABLE IF NOT EXISTS "Municipio".forecast (
    epiweek INT NOT NULL,
    geoid INT NOT NULL,
    cid10 character varying(5) NOT NULL,
    forecast_model_id INT,
    published_date date NOT NULL,
    init_date_epiweek date NOT NULL,
    cases INT NOT NULL,

    PRIMARY KEY (
      epiweek, geoid, cid10, forecast_model_id, published_date
    ),
    FOREIGN KEY(forecast_model_id)
      REFERENCES "Municipio".forecast_model(id),
    FOREIGN KEY(geoid)
      REFERENCES "Dengue_global"."Municipio"(geocodigo),
    FOREIGN KEY(cid10) REFERENCES "Dengue_global"."CID10"(codigo)
);

CREATE TABLE IF NOT EXISTS "Municipio".forecast_city (
    id SERIAL PRIMARY KEY,
    geoid INT NOT NULL,
    forecast_model_id INT,
    active BOOL NOT NULL,
    UNIQUE (geoid, forecast_model_id),
    FOREIGN KEY(forecast_model_id) REFERENCES "Municipio".forecast_model(id),
    FOREIGN KEY(geoid) REFERENCES "Dengue_global"."Municipio"(geocodigo)
);