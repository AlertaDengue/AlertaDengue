# Export And Remove Completed Archive Schemas

`archive_schemas_workflow.sh` is the only supported operational entrypoint for
the reviewed archive export and removal flow.

## Scope

Approved archive schemas:

- `archive_redemet`
- `archive_upload`
- `archive_ovitrampa`
- `archive_alertas_regionais`
- `archive_cemaden`
- `archive_copernicus`
- `archive_historico_casos`
- `archive_mosqlimate`
- `archive_tweets`

Protected active objects that must remain unchanged:

- `"Municipio"."Notificacao"`
- `weather.copernicus_bra`
- `"Dengue_global".regional_saude`
- `"Dengue_global".regional`
- `"Dengue_global"."CID10"`

Retained external archive foreign keys:

- `archive_alertas_regionais.alerta_regional_chik.regional_fk`
- `archive_alertas_regionais.alerta_regional_dengue.regional_fk`
- `archive_alertas_regionais.alerta_regional_zika.regional_fk`
- `archive_tweets."Tweet"."Tweet_CID10"`

All four remain validated with `ON DELETE NO ACTION` and `ON UPDATE NO ACTION`.

## Required Workflow

Use a persistent output root outside the Git worktree, `/tmp`, `/var/tmp`, and
PostgreSQL `data_directory`:

```bash
export ARCHIVE_EXPORT_ROOT=/opt/services/infodengue/database_exports/archive_schemas

./containers/postgres/sql_history/archive_schemas_export/archive_schemas_workflow.sh export

./containers/postgres/sql_history/archive_schemas_export/archive_schemas_workflow.sh verify \
  --package /absolute/path/printed/by/export

./containers/postgres/sql_history/archive_schemas_export/archive_schemas_workflow.sh remove \
  --package /same/absolute/path \
  --confirm-database dengue \
  --confirm-remove REMOVE_NINE_ARCHIVE_SCHEMAS

./containers/postgres/sql_history/archive_schemas_export/archive_schemas_workflow.sh status
```

The immutable package path format is:

```text
${ARCHIVE_EXPORT_ROOT}/${PGDATABASE}/archive_schemas_<UTC_TIMESTAMP>_<SOURCE_FINGERPRINT>/
```

`LATEST_VERIFIED` is updated only after the disposable restore and verification
receipt pass.

## Safety Rules

- Never run `20260729_03_remove_archive_schemas.sql` directly.
- Export and restore validation are mandatory before removal.
- Removal is blocked if checksum, TOC, source identity, inventory, exact row
  counts, FK manifests, dependencies, or the verification receipt differ after
  export.
- The final package must remain outside Git, `/tmp`, `/var/tmp`, and `PGDATA`.
- No `CASCADE`.
- No `TRUNCATE`.
- No active object definitions or data in the archive dump.

## Package Contents

Exported package files:

- `dengue_archive_schemas.dump`
- `dengue_archive_schemas.dump.sha256`
- `dengue_archive_schemas.toc`
- `dengue_archive_schemas.schema.sql`
- `archive_inventory.tsv`
- `archive_row_counts.tsv`
- `archive_dependencies.tsv`
- `archive_external_fks.tsv`
- `archive_internal_fks.tsv`
- `protected_active_objects.tsv`
- `source_identity.tsv`
- `export_command.txt`
- `capacity_preflight.tsv`
- `package_manifest.sha256`
- `README_restore.md`

Verification adds:

- `restore_validation.tsv`
- `verification_receipt.tsv`
- `verification_receipt.sha256`

Removal adds:

- `removal_receipt.tsv`
- `removal_receipt.sha256`

## Restore Notes

The package intentionally keeps the four validated foreign keys to active
lookup tables.

The exported archive also retains the materialized-view definition for
`archive_historico_casos.historico_casos`. Full restore validation therefore
requires compatible `Municipio.Historico_alerta` and
`Municipio.Historico_alerta_chik` source structures and rows so PostgreSQL can
repopulate the archived materialized view during `MATERIALIZED VIEW DATA`
restore.

Standalone restore without those compatible active-reference fixtures remains
future work.
