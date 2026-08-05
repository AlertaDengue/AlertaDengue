# Upload archive schema export

This workflow adapts the reviewed archive export standard to exactly two
schemas: `archive_dbf_upload` and `archive_sinan_upload`.

All libpq connection settings, including `PGDATABASE` and `PGUSER`, must be
provided by the shell or libpq service configuration. The workflow does not
set endpoints, credentials, or local defaults.

Set the persistent output location outside the repository, `/tmp`, and
PostgreSQL `data_directory`:

```bash
export ARCHIVE_EXPORT_ROOT=/opt/services/infodengue/database_exports/archive_schemas
./archive_schemas_workflow.sh export
./archive_schemas_workflow.sh verify --package /absolute/path/printed/by/export
```

Export creates a private package containing the custom-format dump, SHA-256
checksums, receipt-ready manifest, inventory, exact row counts, sequence state,
constraints, indexes, dependencies, grants, TOC, and schema-only SQL.

Verification restores into a disposable database created from `template0`,
checks all package metadata and row counts, then drops only the restored
archive tables and schemas without cascading dependencies. The current database is never
removed by verification. Live removal is intentionally disabled in this
adaptation.

Generated packages are operational evidence and must remain outside Git.
