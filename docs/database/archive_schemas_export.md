# Upload archive schema export

The reviewed archive export/remove standard is adapted for the legacy upload
schemas `archive_dbf_upload` and `archive_sinan_upload` only. The allowlist is
deliberately exact; no other archive schema is exported or removed.

Connection settings are external. Configure libpq in the shell or its service
file before invoking the workflow; repository files contain no host, port,
user, password, DSN, or local endpoint defaults.

```bash
export ARCHIVE_EXPORT_ROOT=/opt/services/infodengue/database_exports/archive_schemas
containers/postgres/sql_history/archive_schemas_export/archive_schemas_workflow.sh export
containers/postgres/sql_history/archive_schemas_export/archive_schemas_workflow.sh verify --package /absolute/package/path
```

The package includes the dump and checksum, receipt inputs, inventory, exact
row counts, sequence state, constraints, indexes, dependencies, grants,
`pg_restore --list`, and schema-only SQL. Verification creates a disposable
database from `template0`, restores the package, validates row-count parity,
and tests explicit schema removal there without cascading dependencies. It never removes the
current local database schemas.

The active replacement objects `ingestion.run` and `ingestion.sinan_stage`
remain outside this archive allowlist and must remain present.
