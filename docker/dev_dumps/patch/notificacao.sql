-- Table: "Municipio"."Notificacao"

-- DROP TABLE "Municipio"."Notificacao";

CREATE TABLE "Municipio"."Notificacao"
(
  id bigserial NOT NULL,
  dt_notific date,
  se_notif integer,
  ano_notif integer,
  dt_sin_pri date,
  se_sin_pri integer,
  dt_digita date,
  bairro_nome text,
  bairro_bairro_id integer,
  municipio_geocodigo integer,
  nu_notific integer,
  cid10_codigo character varying(5),
  dt_nasc date,
  cs_sexo character varying(1),
  nu_idade_n integer,
  CONSTRAINT "Notificacao_pk" PRIMARY KEY (id),
  CONSTRAINT casos_unicos UNIQUE (nu_notific, dt_notific, cid10_codigo, municipio_geocodigo)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE "Municipio"."Notificacao"
  OWNER TO administrador;
GRANT ALL ON TABLE "Municipio"."Notificacao" TO administrador;
GRANT ALL ON TABLE "Municipio"."Notificacao" TO "Dengue";
COMMENT ON TABLE "Municipio"."Notificacao"
  IS 'Casos de notificacao de dengue';

-- Index: "Municipio"."Dengue_idx_data"

-- DROP INDEX "Municipio"."Dengue_idx_data";

CREATE INDEX "Dengue_idx_data"
  ON "Municipio"."Notificacao"
  USING btree
  (dt_notific DESC, se_notif DESC);
