--
-- $ psql -p 25432 -d dengue -v csv_file=/dumps/mem2025_dengue_UF.csv -f /dumps/populate_parameters_uf_from_csv.sql
--

\set ON_ERROR_STOP on
\pset pager off

\if :{?csv_file}
\else
  \echo 'You must provide csv_file, for example: -v csv_file=/dumps/mem2025_dengue_UF.csv'
  \quit 1
\endif

DO $$
BEGIN
    IF current_database() <> 'dengue' THEN
        RAISE EXCEPTION 'Wrong database: %, expected dengue', current_database();
    END IF;
END
$$;

SELECT to_char(now(), 'YYYYMMDD_HH24MISS') AS ts \gset
\set bak_table parameters_uf_bak_:ts

BEGIN;

CREATE TABLE IF NOT EXISTS "Dengue_global".:"bak_table"
AS TABLE "Dengue_global"."parameters_uf";

DROP TABLE IF EXISTS tmp_parameters_uf_csv;

CREATE TEMP TABLE tmp_parameters_uf_csv (
    nome text,
    pre text,
    pos text,
    veryhigh text,
    inicio text,
    inicio_ic text,
    duracao text,
    duracao_ic text,
    quant_pos text,
    quant_epidemico text,
    mininc_pre text,
    mininc_pos text,
    mininc_epi text,
    ano_inicio text,
    ano_fim text,
    populacao text,
    cid10 text
);

SELECT format(
$cmd$
COPY tmp_parameters_uf_csv (
    nome,
    pre,
    pos,
    veryhigh,
    inicio,
    inicio_ic,
    duracao,
    duracao_ic,
    quant_pos,
    quant_epidemico,
    mininc_pre,
    mininc_pos,
    mininc_epi,
    ano_inicio,
    ano_fim,
    populacao,
    cid10
)
FROM %L
WITH (
    FORMAT csv,
    HEADER true,
    DELIMITER ',',
    QUOTE '"',
    NULL '',
    ENCODING 'UTF8'
);
$cmd$,
:'csv_file'
) \gexec

WITH state_map AS (
    SELECT *
    FROM (
        VALUES
            ('Rondônia', 11, 'RO', 'Rondônia'),
            ('Acre', 12, 'AC', 'Acre'),
            ('Amazonas', 13, 'AM', 'Amazonas'),
            ('Roraima', 14, 'RR', 'Roraima'),
            ('Pará', 15, 'PA', 'Pará'),
            ('Amapá', 16, 'AP', 'Amapá'),
            ('Tocantins', 17, 'TO', 'Tocantins'),
            ('Maranhão', 21, 'MA', 'Maranhão'),
            ('Piauí', 22, 'PI', 'Piauí'),
            ('Ceará', 23, 'CE', 'Ceará'),
            ('Rio Grande do Norte', 24, 'RN', 'Rio Grande do Norte'),
            ('Paraíba', 25, 'PB', 'Paraíba'),
            ('Pernambuco', 26, 'PE', 'Pernambuco'),
            ('Alagoas', 27, 'AL', 'Alagoas'),
            ('Sergipe', 28, 'SE', 'Sergipe'),
            ('Bahia', 29, 'BA', 'Bahia'),
            ('Minas Gerais', 31, 'MG', 'Minas Gerais'),
            ('Espírito Santo', 32, 'ES', 'Espírito Santo'),
            ('Rio de Janeiro', 33, 'RJ', 'Rio de Janeiro'),
            ('São Paulo', 35, 'SP', 'São Paulo'),
            ('Paraná', 41, 'PR', 'Paraná'),
            ('Santa Catarina', 42, 'SC', 'Santa Catarina'),
            ('Rio Grande do Sul', 43, 'RS', 'Rio Grande do Sul'),
            ('Mato Grosso do Sul', 50, 'MS', 'Mato Grosso do Sul'),
            ('Mato Grosso', 51, 'MT', 'Mato Grosso'),
            ('Goiás', 52, 'GO', 'Goiás'),
            ('Distrito Federal', 53, 'DF', 'Distrito Federal')
    ) AS t(csv_name, state_code, state_abbr, state_name)
),
csv_disease AS (
    SELECT DISTINCT btrim(cid10) AS cid10
    FROM tmp_parameters_uf_csv
),
staged AS (
    SELECT
        m.state_code,
        m.state_abbr,
        m.state_name,
        btrim(c.cid10) AS cid10,
        NULLIF(c.pre, '')::double precision AS limiar_preseason,
        NULLIF(c.pos, '')::double precision AS limiar_posseason,
        NULLIF(c.veryhigh, '')::double precision AS limiar_epidemico
    FROM tmp_parameters_uf_csv c
    JOIN state_map m
      ON btrim(c.nome) = m.csv_name
),
upserted AS (
    INSERT INTO "Dengue_global"."parameters_uf" (
        state_code,
        state_abbr,
        state_name,
        cid10,
        limiar_preseason,
        limiar_posseason,
        limiar_epidemico
    )
    SELECT
        state_code,
        state_abbr,
        state_name,
        cid10,
        limiar_preseason,
        limiar_posseason,
        limiar_epidemico
    FROM staged
    ON CONFLICT (state_code, cid10)
    DO UPDATE SET
        state_abbr = EXCLUDED.state_abbr,
        state_name = EXCLUDED.state_name,
        limiar_preseason = EXCLUDED.limiar_preseason,
        limiar_posseason = EXCLUDED.limiar_posseason,
        limiar_epidemico = EXCLUDED.limiar_epidemico
    RETURNING (xmax = 0) AS inserted
)
SELECT
    COUNT(*) FILTER (WHERE inserted) AS inserted_rows,
    COUNT(*) FILTER (WHERE NOT inserted) AS updated_rows
FROM upserted;

WITH expected AS (
    SELECT *
    FROM (
        VALUES
            (11, 'RO', 'Rondônia'),
            (12, 'AC', 'Acre'),
            (13, 'AM', 'Amazonas'),
            (14, 'RR', 'Roraima'),
            (15, 'PA', 'Pará'),
            (16, 'AP', 'Amapá'),
            (17, 'TO', 'Tocantins'),
            (21, 'MA', 'Maranhão'),
            (22, 'PI', 'Piauí'),
            (23, 'CE', 'Ceará'),
            (24, 'RN', 'Rio Grande do Norte'),
            (25, 'PB', 'Paraíba'),
            (26, 'PE', 'Pernambuco'),
            (27, 'AL', 'Alagoas'),
            (28, 'SE', 'Sergipe'),
            (29, 'BA', 'Bahia'),
            (31, 'MG', 'Minas Gerais'),
            (32, 'ES', 'Espírito Santo'),
            (33, 'RJ', 'Rio de Janeiro'),
            (35, 'SP', 'São Paulo'),
            (41, 'PR', 'Paraná'),
            (42, 'SC', 'Santa Catarina'),
            (43, 'RS', 'Rio Grande do Sul'),
            (50, 'MS', 'Mato Grosso do Sul'),
            (51, 'MT', 'Mato Grosso'),
            (52, 'GO', 'Goiás'),
            (53, 'DF', 'Distrito Federal')
    ) AS t(state_code, state_abbr, state_name)
),
missing_before_fallback AS (
    SELECT
        e.state_code,
        e.state_abbr,
        e.state_name,
        d.cid10
    FROM expected e
    CROSS JOIN (
        SELECT DISTINCT btrim(cid10) AS cid10
        FROM tmp_parameters_uf_csv
    ) d
    LEFT JOIN "Dengue_global"."parameters_uf" p
      ON p.state_code = e.state_code
     AND p.cid10 = d.cid10
    WHERE p.state_code IS NULL
)
SELECT *
FROM missing_before_fallback
ORDER BY state_code, cid10;

INSERT INTO "Dengue_global"."parameters_uf" (
    state_code,
    state_abbr,
    state_name,
    cid10,
    limiar_preseason,
    limiar_posseason,
    limiar_epidemico
)
SELECT
    32,
    'ES',
    'Espírito Santo',
    d.cid10,
    NULL,
    NULL,
    NULL
FROM (
    SELECT DISTINCT btrim(cid10) AS cid10
    FROM tmp_parameters_uf_csv
) d
WHERE NOT EXISTS (
    SELECT 1
    FROM "Dengue_global"."parameters_uf" p
    WHERE p.state_code = 32
      AND p.cid10 = d.cid10
);

WITH expected AS (
    SELECT *
    FROM (
        VALUES
            (11, 'RO', 'Rondônia'),
            (12, 'AC', 'Acre'),
            (13, 'AM', 'Amazonas'),
            (14, 'RR', 'Roraima'),
            (15, 'PA', 'Pará'),
            (16, 'AP', 'Amapá'),
            (17, 'TO', 'Tocantins'),
            (21, 'MA', 'Maranhão'),
            (22, 'PI', 'Piauí'),
            (23, 'CE', 'Ceará'),
            (24, 'RN', 'Rio Grande do Norte'),
            (25, 'PB', 'Paraíba'),
            (26, 'PE', 'Pernambuco'),
            (27, 'AL', 'Alagoas'),
            (28, 'SE', 'Sergipe'),
            (29, 'BA', 'Bahia'),
            (31, 'MG', 'Minas Gerais'),
            (32, 'ES', 'Espírito Santo'),
            (33, 'RJ', 'Rio de Janeiro'),
            (35, 'SP', 'São Paulo'),
            (41, 'PR', 'Paraná'),
            (42, 'SC', 'Santa Catarina'),
            (43, 'RS', 'Rio Grande do Sul'),
            (50, 'MS', 'Mato Grosso do Sul'),
            (51, 'MT', 'Mato Grosso'),
            (52, 'GO', 'Goiás'),
            (53, 'DF', 'Distrito Federal')
    ) AS t(state_code, state_abbr, state_name)
),
missing_after_fallback AS (
    SELECT
        e.state_code,
        e.state_abbr,
        e.state_name,
        d.cid10
    FROM expected e
    CROSS JOIN (
        SELECT DISTINCT btrim(cid10) AS cid10
        FROM tmp_parameters_uf_csv
    ) d
    LEFT JOIN "Dengue_global"."parameters_uf" p
      ON p.state_code = e.state_code
     AND p.cid10 = d.cid10
    WHERE p.state_code IS NULL
)
SELECT *
FROM missing_after_fallback
ORDER BY state_code, cid10;

DROP TABLE IF EXISTS tmp_parameters_uf_csv;

COMMIT;
