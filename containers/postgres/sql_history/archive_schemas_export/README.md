# Export And Remove Completed Archive Schemas

This workflow externalizes the completed archive schemas from the active
`dengue` database without touching live local, staging, or production data
during repository validation.

## Scope

Exact schemas:

- `archive_redemet`
- `archive_upload`
- `archive_ovitrampa`
- `archive_alertas_regionais`
- `archive_cemaden`
- `archive_copernicus`
- `archive_historico_casos`
- `archive_mosqlimate`
- `archive_tweets`

## External foreign keys retained

The archive dump intentionally keeps four validated foreign keys to active
lookup tables:

- `archive_alertas_regionais.alerta_regional_chik.regional_fk`
- `archive_alertas_regionais.alerta_regional_dengue.regional_fk`
- `archive_alertas_regionais.alerta_regional_zika.regional_fk`
- `archive_tweets."Tweet"."Tweet_CID10"`

All use `ON DELETE NO ACTION` and `ON UPDATE NO ACTION`.

## Shared-environment order

1. backup/snapshot readiness
2. run `20260729_00_audit_archive_schemas.sql`
3. run `20260729_01_preflight_archive_schemas_export.sql`
4. generate the custom-format dump and checksum with `export_archive_schemas.sh`
5. inspect TOC and extracted schema SQL
6. restore into a disposable database with minimal lookup fixtures and the
   retained `Historico_alerta*` sources required by
   `archive_historico_casos.historico_casos`
7. validate restored objects, row counts, and FK policy
8. run `20260729_02_preflight_archive_schemas_removal.sql`
9. execute `20260729_03_remove_archive_schemas.sql` in the maintenance window
10. run `20260729_04_validate_archive_schemas_removed.sql`
11. monitor application and worker activity

## Safety rules

- no `CASCADE`
- no `DROP SCHEMA ... CASCADE`
- no live local removal during repository validation
- no staging or production execution in this repository task
- explicit checked-in manifest only
- protected active lookup tables stay in place:
  - `"Municipio"."Notificacao"`
  - `weather.copernicus_bra`
  - `"Dengue_global".regional_saude`
  - `"Dengue_global".regional`
  - `"Dengue_global"."CID10"`

## Rollback

Rollback uses the verified archive dump plus minimal restore fixtures for
`"Dengue_global".regional(id)` and `"Dengue_global"."CID10"(codigo)`.
Repopulating `archive_historico_casos.historico_casos` also requires
compatible `"Municipio"."Historico_alerta"` and
`"Municipio"."Historico_alerta_chik"` source data because PostgreSQL restores
the materialized view contents through the retained view definition.
