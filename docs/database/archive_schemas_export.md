# Archive schema export

The workflow supports only the following selected archive schemas:

- `archive_redemet`
- `archive_upload`
- `archive_ovitrampa`
- `archive_alertas_regionais`
- `archive_cemaden`
- `archive_copernicus`
- `archive_historico_casos`
- `archive_mosqlimate`
- `archive_tweets`
- `archive_dbf_upload`
- `archive_sinan_upload`

This is an allowlisted selection, not arbitrary `archive_*` input. If
`--schemas` is omitted, export/status use all allowlisted schemas currently
present; verify uses the package’s `selected_schemas.tsv`.

```bash
archive_schemas_workflow.sh export \
  --schemas archive_dbf_upload,archive_sinan_upload
archive_schemas_workflow.sh export --schemas archive_tweets
archive_schemas_workflow.sh export \
  --schemas archive_tweets,archive_dbf_upload,archive_sinan_upload
archive_schemas_workflow.sh verify \
  --package /absolute/path/to/package \
  --schemas archive_dbf_upload,archive_sinan_upload
archive_schemas_workflow.sh status \
  --schemas archive_dbf_upload,archive_sinan_upload
```

External libpq configuration is required. Do not put production values,
credentials, DSNs, or connection details in repository files.

The raw `20260729_00_audit_archive_schemas.sql` file is legacy and
nine-schema-only by design. Selected exports must use
`archive_schemas_workflow.sh --schemas`; the wrapper performs selected-schema
validation and does not invoke that raw audit.

Export records selected schemas, dump and SHA-256, receipts, source database
metadata, Git metadata, inventory, exact row counts, sequence state,
constraints, indexes, dependencies, external/internal FKs, owners/grants,
protected objects, TOC, and schema-only SQL. Restore validation creates only
the minimal fixtures required by reviewed foreign keys, restores into a
disposable database from `template0`, validates selected manifests, and tests
removal only in that disposable database. Live removal remains disabled.
