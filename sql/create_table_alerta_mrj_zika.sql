-- Table: "Municipio".alerta_mrj_zika

-- DROP TABLE "Municipio".alerta_mrj_zika;

CREATE TABLE IF NOT EXISTS "Municipio".alerta_mrj_zika
(
  id bigserial NOT NULL,
  aps character varying(6) NOT NULL,
  se integer NOT NULL,
  data date NOT NULL,
  tweets integer,
  casos integer,
  casos_est real,
  casos_estmin real,
  casos_estmax real,
  tmin real,
  rt real,
  prt1 real,
  inc real,
  nivel integer,
  CONSTRAINT alerta_mrj_zika_pk PRIMARY KEY (id),
  CONSTRAINT previsao_zika UNIQUE (aps, se),
  CONSTRAINT unique_zika_aps_se UNIQUE (se, aps)
)
