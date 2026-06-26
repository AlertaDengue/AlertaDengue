# Upload App SQL History

These scripts retire the Django `upload` app and its
`django-chunked-upload` dependency. They are one-time, production-maintenance
scripts, not PostgreSQL bootstrap input.

Run them against each target database with `psql` and fail fast on errors:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/upload/20260626_01_archive_upload_app.sql
```

Validate the archive, apply the final Django `upload` migration, deploy the
application without the app, and then run:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/upload/20260626_02_remove_chunked_upload_table.sql
```

The scripts use transactions and explicit preconditions. The removal script
does not use `CASCADE`; an unknown database dependency must abort the removal.
See `docs/plans/remove-upload-app.md` for the complete release procedure,
validation queries, and recovery boundaries.
