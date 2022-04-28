DELETE FROM "Dengue_global".regional_saude WHERE id=1746;

ALTER TABLE "Dengue_global".regional_saude
ADD CONSTRAINT regional_saude_uq_municipio_geocodigo UNIQUE (municipio_geocodigo);

ALTER TABLE "Dengue_global".regional_saude
ADD COLUMN varcli VARCHAR(10) NULL;

ALTER TABLE "Dengue_global".regional_saude
ADD COLUMN tcrit DOUBLE PRECISION NULL;

ALTER TABLE "Dengue_global".regional_saude
ADD COLUMN ucrit DOUBLE PRECISION NULL;
