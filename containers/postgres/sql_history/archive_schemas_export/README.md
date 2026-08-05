# Archive schema export

`archive_schemas_workflow.sh` accepts a comma-separated selection from this
explicit allowlist only:

`archive_redemet`, `archive_upload`, `archive_ovitrampa`,
`archive_alertas_regionais`, `archive_cemaden`, `archive_copernicus`,
`archive_historico_casos`, `archive_mosqlimate`, `archive_tweets`,
`archive_dbf_upload`, `archive_sinan_upload`.

When `--schemas` is omitted, export and status select all allowlisted schemas
currently present. Verify reads the selected schemas from the package. An
explicit selection is always validated for empty, duplicate, malformed, and
non-allowlisted names.

Examples:

```bash
archive_schemas_workflow.sh export --schemas archive_dbf_upload,archive_sinan_upload
archive_schemas_workflow.sh export --schemas archive_tweets
archive_schemas_workflow.sh export --schemas archive_tweets,archive_dbf_upload,archive_sinan_upload
archive_schemas_workflow.sh verify --package /absolute/path/to/package --schemas archive_dbf_upload,archive_sinan_upload
archive_schemas_workflow.sh status --schemas archive_dbf_upload,archive_sinan_upload
```

All libpq settings must come from the shell or libpq service configuration.
Never place connection values or credentials in the repository.

Every package records `selected_schemas.tsv`, a custom-format dump, checksums,
source and Git metadata, inventory, exact row counts, sequences, constraints,
indexes, dependencies, external/internal FKs, grants, protected objects,
`pg_restore --list`, schema-only SQL, and receipts.

Verify restores into a disposable `template0` database and tests removal only
there. Restore validation must pass before any removal consideration. Live
removal remains disabled in this workflow; never remove current local schemas.
