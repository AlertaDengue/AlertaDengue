-- Table: "Municipio"."Historico_alerta_zika"

-- DROP TABLE "Municipio"."Historico_alerta_zika";

CREATE TABLE IF NOT EXISTS "Municipio"."Historico_alerta_zika"
(
  "data_iniSE" date NOT NULL,
  "SE" integer NOT NULL,
  casos_est real,
  casos_est_min integer,
  casos_est_max integer,
  casos integer,
  municipio_geocodigo integer NOT NULL,
  p_rt1 real,
  p_inc100k real,
  "Localidade_id" integer,
  nivel smallint,
  id bigserial NOT NULL,
  versao_modelo character varying(40),
  municipio_nome character varying(128),
  CONSTRAINT "Historico_alerta_zika_pk" PRIMARY KEY (id),
  CONSTRAINT alertas_unicos_zika UNIQUE ("SE", municipio_geocodigo, "Localidade_id")
)
