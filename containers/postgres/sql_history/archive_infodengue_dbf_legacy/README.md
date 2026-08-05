# `infodengue` legacy DBF archive workflow

This package is exclusively for the `infodengue` database. It archives the
retired DBF side-effect tables left after commit `8922b2d5`:

- `public.dbf_dbf` (6964 rows in the supplied inventory)
- `public.dbf_dbfchunkedupload` (7635 rows)
- `public.dbf_sendtopartner` (13 rows)
- their three owned ID sequences

The archive schema is `archive_infodengue_dbf_legacy`. Nothing here applies to
the `dengue` database, Django framework objects, PostGIS/topology objects, or
active ingestion tables.

## Safety and prerequisites

Use PostgreSQL 14-compatible `psql`, `pg_dump`, and `pg_restore`. Configure the
connection outside the repository and always use `psql -X -v ON_ERROR_STOP=1`.
The scripts fail closed on a wrong database, incomplete inventory, unexpected
dependencies, or changed reviewed structure. They do not use broad destructive
shortcuts and never archive or remove with a broad dependency option.

The archive script is one-time and transactional. The validation and restore
scripts end with `ROLLBACK`; the archive script ends with `COMMIT`. The removal
script is intentionally not to be run until the package and disposable restore
have been independently verified and explicit operational approval has been
recorded.

## Workflow

Set `PGDATABASE=infodengue` (or use an approved libpq service), then:

```bash
SQL_DIR=containers/postgres/sql_history/archive_infodengue_dbf_legacy
PSQL=(psql -X -v ON_ERROR_STOP=1)
"${PSQL[@]}" -v expected_database_name=infodengue \
  -f "${SQL_DIR}/20260805_00_preflight_infodengue_dbf_legacy.sql"
```

Review the read-only output. It records exact row counts, columns/defaults,
constraints, indexes, triggers, grants/owners, sequence state and the supplied
date evidence. Then, after review approval, run the archive script:

```bash
"${PSQL[@]}" -v expected_database_name=infodengue \
  -f "${SQL_DIR}/20260805_01_archive_infodengue_dbf_legacy.sql"
```

Proceed only when it ends in `COMMIT`, then run the read-only archive validator:

```bash
"${PSQL[@]}" -v expected_database_name=infodengue \
  -f "${SQL_DIR}/20260805_02_validate_infodengue_dbf_legacy_archive.sql"
```

## Archive package and disposable restore

Export outside the worktree, `/tmp`, and PostgreSQL data directories. Do not
use cleanup, create-database, owner-stripping, or ACL-stripping dump options:

```bash
PACKAGE_DIR=/persistent/archive/path
pg_dump --format=custom --compress=9 --strict-names --lock-wait-timeout=5s \
  --schema=archive_infodengue_dbf_legacy \
  --file="${PACKAGE_DIR}/archive_infodengue_dbf_legacy.dump" infodengue
sha256sum "${PACKAGE_DIR}/archive_infodengue_dbf_legacy.dump" \
  > "${PACKAGE_DIR}/archive_infodengue_dbf_legacy.dump.sha256"
pg_restore --list "${PACKAGE_DIR}/archive_infodengue_dbf_legacy.dump" \
  > "${PACKAGE_DIR}/archive_infodengue_dbf_legacy.toc"
pg_restore --schema-only -f "${PACKAGE_DIR}/archive_infodengue_dbf_legacy.schema.sql" \
  "${PACKAGE_DIR}/archive_infodengue_dbf_legacy.dump"
```

Record UTC time, source database/OID, Git commit, exact object inventory, row
counts, sequence values and `is_called`, dependency/constraint/index/grant
results, SHA-256, TOC, and schema-only SQL. Restore the custom dump into a new
database created from `template0`, not over an active database. Validate all
six objects, counts, sequence state, defaults, ownership, constraints, indexes,
the two reviewed foreign keys to `public.auth_user(id)`, and grants where the
roles exist. Record a PASS receipt and retain the package and receipt.

## Rollback and removal

Before removal, `20260805_80_restore_infodengue_dbf_legacy.sql` moves the exact
objects back to `public` in one transaction. It is the preferred rollback
while the archive still exists.

`20260805_90_remove_infodengue_dbf_legacy.sql` requires explicit psql variables
for the verified package path, database OID, dump SHA-256, PASS status, all row
counts, and all sequence states. It also checks the current archive inventory,
dependencies, constraints, and indexes before removing the three archived
tables. It is a separate, guarded operation and is not executed by this task.

The removal receipt must include UTC time, database/OID, package path and
checksum, verification receipt, pre-removal inventory/counts/sequence states,
and the post-removal object checks. Keep the verified dump permanently.

## Supplied date evidence

`dbf_dbf.uploaded_at`: `2016-10-05` through `2026-01-20`.
`dbf_dbf.export_date`: `2015-03-23` through `2026-01-20`.
`dbf_dbfchunkedupload.created_on` and `completed_on`: `2016-11-07` through
`2026-01-20` (NULL `completed_on` values are reported separately).
`dbf_sendtopartner` has no date columns. `notification_year` is reported but
not used as a lifecycle cutoff because invalid/extreme values exist.
