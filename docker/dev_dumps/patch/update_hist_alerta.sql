-- Tables:


-- "Municipio"."Historico_alerta"
ALTER TABLE "Municipio"."Historico_alerta" ADD COLUMN Rt numeric(5,0) default NULL::numeric;
ALTER TABLE "Municipio"."Historico_alerta" ADD COLUMN pop numeric(7,0) default NULL::numeric;
ALTER TABLE "Municipio"."Historico_alerta" ADD COLUMN tempmin numeric(4,0) default NULL::numeric;
ALTER TABLE "Municipio"."Historico_alerta" ADD COLUMN umidmax numeric(4,0) default NULL::numeric;
-- "Municipio"."Historico_alerta_chik"
ALTER TABLE "Municipio"."Historico_alerta_chik" ADD COLUMN Rt numeric(5,0) default NULL::numeric;
ALTER TABLE "Municipio"."Historico_alerta_chik" ADD COLUMN pop numeric(7,0) default NULL::numeric;
ALTER TABLE "Municipio"."Historico_alerta_chik" ADD COLUMN tempmin numeric(4,0) default NULL::numeric;
ALTER TABLE "Municipio"."Historico_alerta_chik" ADD COLUMN umidmax numeric(4,0) default NULL::numeric;
-- "Municipio"."Historico_alerta_zika"
ALTER TABLE "Municipio"."Historico_alerta_zika" ADD COLUMN Rt numeric(5,0) default NULL::numeric;
ALTER TABLE "Municipio"."Historico_alerta_zika" ADD COLUMN pop numeric(7,0) default NULL::numeric;
ALTER TABLE "Municipio"."Historico_alerta_zika" ADD COLUMN tempmin numeric(4,0) default NULL::numeric;
ALTER TABLE "Municipio"."Historico_alerta_zika" ADD COLUMN umidmax numeric(4,0) default NULL::numeric;
