# Remove the Upload Application

## Scope

This plan retires `AlertaDengue/upload`, the `/upload/sinan/` HTTP workflow,
its Celery tasks, and the `django-chunked-upload` dependency. It does not
replace the current MinIO-based ingestion workflow. The previously retained
`DBF_SINAN` storage setting becomes removable only after this plan is complete
and no other consumer is found.

The development database inspected on 2026-06-26 contains these relations:

| Relation | Owner | Removal method |
| --- | --- | --- |
| `public.upload_sinanchunkedupload` | `upload.SINANChunkedUpload` | Final Django migration |
| `public.upload_sinanupload` | `upload.SINANUpload` | Final Django migration |
| `public.upload_sinanuploadlogstatus` | `upload.SINANUploadLogStatus` | Final Django migration |
| `public.chunked_upload_chunkedupload` | `django-chunked-upload` | Guarded SQL after app migration |

The first three tables are app-owned concrete tables. The fourth belongs to
the third-party dependency, so all of its rows are archived before it is
dropped. Do not infer table existence from the checked-in schema dumps: they
are stale for `upload_*` and must be regenerated after the removal.

## Migration Policy

Do not delete rows from `django_migrations`. Applied migration rows are the
historical record of a deployed schema. A final `upload` migration must be
created while `upload` is still in `INSTALLED_APPS`; use the next migration
number after `0024_alter_sinanuploadlogstatus_status`.

The final migration should use `SeparateDatabaseAndState`: ordered irreversible
`RunSQL` table drops without `CASCADE`, plus these `DeleteModel` state
operations in this order:

1. `SINANUpload`
2. `SINANChunkedUpload`
3. `SINANUploadLogStatus`

This order first removes foreign keys from `SINANUpload` to the other two
tables. The database operations must not use `CASCADE`, and the migration must
not edit migration history. Review the emitted SQL before use.

Keep the migration source and app package through the release that runs
`migrate`. Remove the application package and its migrations only in the next
release, after every supported database has applied the final migration. A
fresh database will then start without the retired app or its tables.

## Release Procedure

1. Inventory every target database and confirm all four relations in the
   table above exist in the intended schema. Take and retain a full,
   restorable `pg_dump` before maintenance.
2. Stop admission of new `/upload/sinan/` requests, drain Celery tasks named
   `upload.tasks.*`, and stop workers before changing the schema. Preserve
   `DBF_SINAN` files and log files until the retention decision is approved.
3. Run `20260626_01_archive_upload_app.sql` from
   `containers/postgres/sql_history/upload/` with `psql -X -v
   ON_ERROR_STOP=1`. It creates a data-only `archive_upload` schema and
   manifest. The archive deliberately has no source foreign keys or sequence
   defaults.
4. Validate source and archive counts while the source tables still exist:

   ```sql
   SELECT m.source_table,
          m.row_count AS archived_rows,
          CASE m.source_table
              WHEN 'public.upload_sinanchunkedupload' THEN
                  (SELECT count(*) FROM public.upload_sinanchunkedupload)
              WHEN 'public.upload_sinanupload' THEN
                  (SELECT count(*) FROM public.upload_sinanupload)
              WHEN 'public.upload_sinanuploadlogstatus' THEN
                  (SELECT count(*) FROM public.upload_sinanuploadlogstatus)
              WHEN 'public.chunked_upload_chunkedupload' THEN
                  (SELECT count(*) FROM public.chunked_upload_chunkedupload)
          END AS source_rows
   FROM archive_upload.manifest AS m
   ORDER BY m.source_table;
   ```

   Every `archived_rows` value must equal `source_rows`. Also inspect a sample
   of file paths and log paths, verify archive access is restricted to the
   approved database role, and record the validation result in the release
   ticket.
5. In release A, remove the route in `ad_main/urls.py` and the explicit
   `upload.tasks` Celery include, create and apply the final migration, then
   run `python AlertaDengue/manage.py migrate --plan` and `migrate` against
   every supported database. Keep the app installed only for this release so
   Django can discover and apply its final migration.
6. In release B, remove the `upload` package, its templates and tests,
   `upload` and `chunked_upload` from Django settings, chunked-upload storage
   settings, the dependency from `pyproject.toml` and `poetry.lock`, and the
   `TYPE_CHECKING` import/type annotation in `ingestion/utils.py`. Replace
   type-only coupling with a local protocol or a neutral data type only if the
   helper remains useful outside the removed workflow.
7. Regenerate the PostgreSQL bootstrap dumps from a clean post-removal
   database. Remove only `public.chunked_upload_chunkedupload` from this
   application database; retain `forecast.chunked_upload_chunkedupload` until
   its owner is independently audited.
8. Run `20260626_02_remove_chunked_upload_table.sql`. It refuses to run while
   any `upload_*` table remains and deliberately omits `CASCADE`.
9. Restart workers, verify `/status/`, run migration consistency checks, and
   monitor for unknown task names, import errors, or requests to `/upload/`.

## Code Changes and Tests

The release-B dependency removal must include `poetry.lock`; do not modify
`conda/base.yaml` because it does not declare `django-chunked-upload`.
Remove `CHUNKED_UPLOAD_PATH`, `CHUNKED_UPLOAD_STORAGE_CLASS`, and
`DBFSINANStorage` only after confirming they have no consumer. Then evaluate
whether `DBF_SINAN` is unused with a repository-wide search before deleting
its environment configuration and operational documentation.

No auxiliary function is needed for the removal itself. If a type-only helper
is retained from `ingestion/utils.py`, add full type annotations and a
numpydoc-style docstring where required by the project standards.

Before each release, run:

```bash
python AlertaDengue/manage.py check
python AlertaDengue/manage.py makemigrations --check --dry-run
python AlertaDengue/manage.py migrate --plan
poetry run mypy AlertaDengue
poetry run ruff check AlertaDengue
makim tests.unit
```

Add focused tests that prove the retired URLs are absent, no Celery task
imports `upload`, settings no longer list either removed app, and a clean test
database migrates successfully. Do not run the production archive or removal
scripts as part of the test suite.

## Recovery and Retention

The SQL archive is a data archive, not a rollback migration. Recovery requires
the retained full database backup plus a reviewed restoration procedure for
the archived data and any referenced files under `DBF_SINAN`. Do not drop
`archive_upload` or delete stored files until the agreed retention period has
expired and the archive has been tested by the authorized recovery process.

## Execution Status

Development execution completed on 2026-06-26. The schema-only backup is
`20260626_00_upload_app_schema.sql`. `archive_upload` preserves 3,026 chunk
rows, 3,884 upload rows, 3,884 log-status rows, and zero generic chunked-upload
rows in `dengue`; `infodengue` has a separate zero-row generic-table archive.

The terminal migration was applied before the package was removed. Both
development bootstrap schemas were regenerated without `archive_upload` or the
retired `chunked_upload_chunkedupload` table. Production remains pending: run
the matching archive scripts, validate their manifests, apply the migration,
and retain the full database and file backups for the agreed period.
