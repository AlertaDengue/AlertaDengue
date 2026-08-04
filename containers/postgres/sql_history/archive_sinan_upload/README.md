# Legacy SINAN upload archival

## Purpose

The retired SINAN upload workflow was used through epidemiological week
`202552`. The current flow is watcher/MinIO → `ingestion.run` →
`ingestion.sinan_stage` → merge, active from `202553`. The repository runtime
gate passed on commit `ce57f16ca1d62cb67924d14fe22f9d5d057fbd3b`: no active
model, endpoint, task, pipeline, or dynamic lookup depends on the legacy
objects. The database data has timestamps but no authoritative epiweek field,
so it cannot independently prove the lifecycle boundary. Operator confirmation
of the `202552` cutoff remains required.

## Exact scope

Archive exactly these tables and owned sequences:

- `public.upload_sinanchunkedupload`
- `public.upload_sinanupload`
- `public.upload_sinanuploadlogstatus`
- `public.upload_sinanchunkedupload_id_seq`
- `public.upload_sinanupload_id_seq`
- `public.upload_sinanuploadlogstatus_id_seq`

The target schema is `archive_sinan_upload`.

Out of scope: `public.dbf_dbf`, `public.dbf_dbfchunkedupload`,
`public.chunked_upload_chunkedupload`, all other `public.upload_*` objects,
`ingestion.run`, `ingestion.sinan_stage`, all active ingestion code, and every
other database object.

## Runtime dependency verification

The audit checked Django models/imports and settings, URL includes and API
routers, views, forms, serializers, Admin, signals, middleware, Celery tasks,
Beat/autodiscovery, management commands, raw and dynamic SQL, R/Python
pipelines, templates/frontend calls, repository entrypoints, and Git history.
It separately searched the current worktree and committed `HEAD`, and reviewed
transition commits `c4043d87b` and `0d1ab4b2d`. Historical migrations, SQL
history, tests, fixtures, notebooks, comments, and documentation were not
classified as active runtime paths. Archival is blocked whenever an active or
unknown reference is found.

## Requirements

- PostgreSQL 14-compatible `psql` and `pg_dump`.
- An externally configured target database, DDL privileges, and a server not
  in recovery.
- Backup/snapshot readiness and explicit external-consumer confirmation.
- An approved decision for retention of uploaded files and log files.
- Every `psql` command uses `psql -X -v ON_ERROR_STOP=1`.
- Never put a password in this README or shell history.

## Connection setup

Configure libpq outside the repository using `PG*` variables,
`~/.pg_service.conf`, or another approved secret manager. Do not use `set -u`
in the interactive shell.

```bash
: "${PGDATABASE:?PGDATABASE must be configured externally}"
: "${PGUSER:?PGUSER must be configured externally}"
# export PGSERVICE="<configured-service>"

SQL_DIR="containers/postgres/sql_history/archive_sinan_upload"
PSQL=(psql -X -v ON_ERROR_STOP=1)
```

## Step 1 — Read-only preflight

```bash
"${PSQL[@]}" \
  -v expected_database_name="${PGDATABASE}" \
  -f "${SQL_DIR}/20260804_00_preflight_sinan_upload.sql"
```

All checks must pass. The output displays exact inventory, rows, sizes,
columns/defaults, indexes, constraints, triggers, rules, grants, sequence
ownership/state, safe file prefixes, and structural FK validation. Historical
validation reports `NOT_INDEPENDENTLY_VERIFIABLE`, and the final result is
`ROLLBACK`. Stop on any error.

## Step 2 — Archive

After operator confirmation and a successful preflight, run once:

```bash
"${PSQL[@]}" \
  -v expected_database_name="${PGDATABASE}" \
  -f "${SQL_DIR}/20260804_01_archive_sinan_upload.sql"
```

The expected final result is `COMMIT`. It moves exactly three tables and their
three owned sequences to `archive_sinan_upload`; it does not delete data.
Counts, sequence `last_value`/`is_called`, ownership, defaults, constraints,
indexes, FKs, grants, and protected active objects are validated in the same
transaction. The script is deliberately one-time and non-idempotent.

## Step 3 — Post-archive verification

Run these read-only queries with the connection setup above:

```sql
SELECT to_regclass('public.upload_sinanchunkedupload'),
       to_regclass('public.upload_sinanupload'),
       to_regclass('public.upload_sinanuploadlogstatus'),
       to_regclass('public.upload_sinanchunkedupload_id_seq'),
       to_regclass('public.upload_sinanupload_id_seq'),
       to_regclass('public.upload_sinanuploadlogstatus_id_seq');

SELECT to_regclass('archive_sinan_upload.upload_sinanchunkedupload'),
       to_regclass('archive_sinan_upload.upload_sinanupload'),
       to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus'),
       to_regclass('archive_sinan_upload.upload_sinanchunkedupload_id_seq'),
       to_regclass('archive_sinan_upload.upload_sinanupload_id_seq'),
       to_regclass('archive_sinan_upload.upload_sinanuploadlogstatus_id_seq');

SELECT 'upload_sinanchunkedupload' AS object_name, count(*) AS rows
  FROM archive_sinan_upload.upload_sinanchunkedupload
UNION ALL SELECT 'upload_sinanupload', count(*) FROM archive_sinan_upload.upload_sinanupload
UNION ALL SELECT 'upload_sinanuploadlogstatus', count(*) FROM archive_sinan_upload.upload_sinanuploadlogstatus;

SELECT 'upload_sinanchunkedupload_id_seq', last_value, is_called FROM archive_sinan_upload.upload_sinanchunkedupload_id_seq
UNION ALL SELECT 'upload_sinanupload_id_seq', last_value, is_called FROM archive_sinan_upload.upload_sinanupload_id_seq
UNION ALL SELECT 'upload_sinanuploadlogstatus_id_seq', last_value, is_called FROM archive_sinan_upload.upload_sinanuploadlogstatus_id_seq;

SELECT conrelid::regclass, conname, confrelid::regclass, conkey, confkey,
       confmatchtype, confupdtype, confdeltype, condeferrable, condeferred,
       convalidated
  FROM pg_constraint
 WHERE conrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,
                   'archive_sinan_upload.upload_sinanupload'::regclass,
                   'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass);

SELECT indrelid::regclass, indexrelid::regclass, indisprimary, indisunique
  FROM pg_index
 WHERE indrelid IN ('archive_sinan_upload.upload_sinanchunkedupload'::regclass,
                   'archive_sinan_upload.upload_sinanupload'::regclass,
                   'archive_sinan_upload.upload_sinanuploadlogstatus'::regclass);
```

The six public lookups must be null, the six archive lookups must resolve, and
all recorded counts, sequence states, ownership/defaults, constraints, and
indexes must match the preflight.

## Step 4 — Export verified archive package

The PR #1038 archive/export workflow is hard-coded for its previous archive
schemas and does not select `archive_sinan_upload`; no duplicate shell wrapper
is created here. Export manually to a persistent path outside the Git
worktree, `/tmp`, and PostgreSQL data directories:

```bash
PACKAGE_DIR=/persistent/archive/path
pg_dump --format=custom --compress=9 --strict-names --lock-wait-timeout=5s \
  --schema=archive_sinan_upload \
  --file="${PACKAGE_DIR}/archive_sinan_upload.dump" "${PGDATABASE}"
sha256sum "${PACKAGE_DIR}/archive_sinan_upload.dump" > "${PACKAGE_DIR}/archive_sinan_upload.dump.sha256"
pg_restore --list "${PACKAGE_DIR}/archive_sinan_upload.dump" > "${PACKAGE_DIR}/archive_sinan_upload.toc"
pg_restore --schema-only -f "${PACKAGE_DIR}/archive_sinan_upload.schema.sql" "${PACKAGE_DIR}/archive_sinan_upload.dump"
```

Do not pass `-X` to `pg_dump`, and do not use `--clean`, `--create`,
`--no-owner`, or `--no-acl`. The package receipt and `SHA256SUMS` must record
UTC timestamp, database name/OID, Git commit, exact six-object inventory,
counts, sequence states, constraints, indexes, dependencies, grants, dump
hash, TOC, and schema-only SQL.

## Step 5 — Disposable restore validation

Create a disposable database from `template0`, install only extensions proven
necessary, and derive minimal compatible fixtures from the reviewed outbound
FKs. This archive requires `public.auth_user(id integer primary key)` populated
with the distinct referenced IDs. Restore the custom dump and validate all six
objects, exact counts, sequence values and `is_called`, ownership/defaults,
constraints, indexes, the external FK, and grants where roles exist. Record a
PASS receipt, then drop the disposable database. Do not restore over an active
database.

## Step 6 — Permanent removal

**Permanent removal is a separate operation and is not part of archival.**

`20260804_90_remove_sinan_upload.sql` requires these exact variables:

`verified_package_path`, `expected_database_oid`, `expected_dump_sha256`,
`verification_status`, `expected_sinanchunkedupload_rows`,
`expected_sinanupload_rows`, `expected_sinanuploadlogstatus_rows`,
`expected_sinanchunkedupload_id_seq_last_value`,
`expected_sinanchunkedupload_id_seq_is_called`,
`expected_sinanupload_id_seq_last_value`,
`expected_sinanupload_id_seq_is_called`,
`expected_sinanuploadlogstatus_id_seq_last_value`, and
`expected_sinanuploadlogstatus_id_seq_is_called`.

Use placeholders only until all evidence is verified:

```bash
"${PSQL[@]}" \
  -v expected_database_name="${PGDATABASE}" \
  -v verified_package_path=/persistent/archive/path/archive_sinan_upload.dump \
  -v expected_database_oid=DATABASE_OID \
  -v expected_dump_sha256=SHA256_HEX \
  -v verification_status=PASS \
  -v expected_sinanchunkedupload_rows=SINAN_CHUNKED_ROWS \
  -v expected_sinanupload_rows=SINAN_UPLOAD_ROWS \
  -v expected_sinanuploadlogstatus_rows=SINAN_LOG_STATUS_ROWS \
  -v expected_sinanchunkedupload_id_seq_last_value=CHUNK_SEQUENCE_LAST_VALUE \
  -v expected_sinanchunkedupload_id_seq_is_called=CHUNK_SEQUENCE_IS_CALLED \
  -v expected_sinanupload_id_seq_last_value=UPLOAD_SEQUENCE_LAST_VALUE \
  -v expected_sinanupload_id_seq_is_called=UPLOAD_SEQUENCE_IS_CALLED \
  -v expected_sinanuploadlogstatus_id_seq_last_value=LOG_SEQUENCE_LAST_VALUE \
  -v expected_sinanuploadlogstatus_id_seq_is_called=LOG_SEQUENCE_IS_CALLED \
  -f "${SQL_DIR}/20260804_90_remove_sinan_upload.sql"
```

Removal requires the verified persistent package and SHA-256, disposable
restore PASS, current inventory/count/state match, database name/OID match, no
new dependency, and explicit operational approval. Never guess evidence,
remove immediately after archive, or use `CASCADE`; retain packages and
receipts permanently.

## Rollback policy

Failed preflight changes nothing. A failed archive transaction rolls back.
Before removal, rollback requires a separately reviewed transaction moving the
tables back to `public`; after removal, recovery requires the verified dump.

## Re-execution behavior

The archive script is one-time and non-idempotent. After a successful
`COMMIT`, rerunning it fails closed because the public source inventory is
absent. Use post-archive verification instead. The removal script was not
executed during this task.

## Current validation status

The read-only catalog inspection matched the externally supplied expected
database identity. It found these exact legacy objects under
`archive_sinan_upload`: the three tables, their three sequences, and their
indexes. More specifically, the archive catalog contains
`upload_sinanchunkedupload`, `upload_sinanupload`,
`upload_sinanuploadlogstatus`, their three `_id_seq` objects, and eight table
indexes. It also found the protected active `ingestion.sinan_stage` table,
its sequence, and its five indexes. No SINAN-named procedures were found, and
no alternate schema or approximate table name matched the three legacy table
names. The exact six source objects are absent from `public`, so the database
archive gate is `BLOCKED`: the target inventory is already archived and the
preflight must not be weakened or rerun as an archive against unrelated
objects. The runtime gate remains PASS. Archive and removal were not executed
during this correction.
