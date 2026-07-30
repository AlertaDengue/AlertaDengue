## Archive Schema Export And Guarded Removal

The repository now documents one supported operational path for the completed
archive schemas:

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

## Operational Gate

- The raw removal SQL must not be executed directly.
- Export and disposable restore validation are mandatory before removal.
- The final package path must be persistent and outside the Git worktree,
  `/tmp`, `/var/tmp`, and PostgreSQL `data_directory`.
- `LATEST_VERIFIED` points to the latest immutable package that completed
  checksum, TOC, restore, and receipt validation.
- Removal is refused when the current source database no longer matches the
  verified package identity, inventory, exact row counts, FK manifests, or
  dependencies.

The default persistent output root is:

```text
/opt/services/infodengue/database_exports/archive_schemas
```

Each package is written to:

```text
${ARCHIVE_EXPORT_ROOT}/${PGDATABASE}/archive_schemas_<UTC_TIMESTAMP>_<SOURCE_FINGERPRINT>/
```

and is created first as `.<package-name>.partial`, then atomically renamed only
after all export artifacts are durable on disk.

## Package Evidence

The immutable package contains:

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

## Dependency Notes

The archive package intentionally retains four validated foreign keys to active
lookup tables:

- `archive_alertas_regionais.alerta_regional_chik.regional_fk`
- `archive_alertas_regionais.alerta_regional_dengue.regional_fk`
- `archive_alertas_regionais.alerta_regional_zika.regional_fk`
- `archive_tweets."Tweet"."Tweet_CID10"`

All use `ON DELETE NO ACTION` and `ON UPDATE NO ACTION`.

The exported archive also retains the populated materialized view
`archive_historico_casos.historico_casos`. Full restore therefore requires
compatible active-reference structures for `Dengue_global.regional`,
`Dengue_global.CID10`, `Municipio.Historico_alerta`, and
`Municipio.Historico_alerta_chik`. Standalone restore without those compatible
fixtures remains future work.

## Staging Note

Current staging already has the approved archive schemas absent and has no
confirmed persistent archive package artifact in the reviewed operator paths.
It is therefore not a valid source for re-export. Recovery for any future
staging investigation must use a pre-removal backup or another environment
where the nine archive schemas still exist, without overwriting current
staging.
