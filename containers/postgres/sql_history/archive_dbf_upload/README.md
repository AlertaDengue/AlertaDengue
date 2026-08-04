# Legacy DBF upload archival

## Purpose

The legacy DBF upload flow covers data through epidemiological week `202552`.
The new `ingestion` structure is active from epiweek `202553`. The database
tables do not contain an epiweek column capable of independently proving that
boundary, so the operator must confirm the lifecycle decision before archival.

The repository runtime audit found no active DBF code path. External consumers
still require operator confirmation.

## Exact scope

Archive only:

- `public.dbf_dbf`;
- `public.dbf_dbfchunkedupload`;
- `public.dbf_dbf_id_seq`;
- `public.dbf_dbfchunkedupload_id_seq`.

The target schema is `archive_dbf_upload`.

Out of scope:

- `public.chunked_upload_chunkedupload`;
- all `public.upload_sinan*` objects;
- `ingestion.run`;
- `ingestion.sinan_stage`;
- every other database object.

The reviewed outbound FKs are `dbf_dbf.uploaded_by_id` and
`dbf_dbfchunkedupload.user_id`, both referencing `public.auth_user(id)`.

## Requirements

- Use a PostgreSQL client compatible with PostgreSQL 14.
- Execute against database `dengue` with a role having the required catalog
  and DDL privileges.
- PostgreSQL must not be in recovery.
- Confirm backup/snapshot readiness before archival.
- No password may be written in this README or command history.
- Use `-X` and `ON_ERROR_STOP=1` for every command.
- No script has been executed against production.

## Connection setup

The following is the local validation environment, not a production template:

```bash
export PGHOST=127.0.0.1
export PGPORT=25432
export PGDATABASE=dengue
export PGUSER=dengueadmin

SQL_DIR="containers/postgres/sql_history/archive_dbf_upload"
PSQL=(psql -X -v ON_ERROR_STOP=1)
```

## Step 1 — Read-only preflight

Run:

```bash
"${PSQL[@]}" \
  -f "${SQL_DIR}/20260803_00_preflight_dbf_upload.sql"
```

All checks must pass. The output displays the exact object inventory, row
counts, sequence ownership, and the two structurally validated outbound FKs
to `public.auth_user(id)`. Historical-period validation must report
`NOT_INDEPENDENTLY_VERIFIABLE`. The final command is `ROLLBACK`; no database
object is modified.

Stop when the preflight returns any error.

## Step 2 — Archive

Run only after the lifecycle decision and preflight have been confirmed:

```bash
"${PSQL[@]}" \
  -f "${SQL_DIR}/20260803_01_archive_dbf_upload.sql"
```

Expected result:

- the transaction finishes with `COMMIT`;
- the two source tables and their two owned sequences disappear from `public`;
- all four objects exist under `archive_dbf_upload`;
- row counts remain unchanged;
- sequence `last_value` and `is_called` remain unchanged;
- sequence ownership and column defaults remain valid;
- both FKs to `public.auth_user(id)` remain valid;
- protected active objects remain present.

This is a schema move, not permanent deletion. Stop immediately if the command
does not finish with `COMMIT`; do not continue to export or removal after a
failed archive.

## Step 3 — Post-archive verification

Use a read-only `psql` session with `-X -v ON_ERROR_STOP=1` and run:

```sql
SELECT
    to_regclass('public.dbf_dbf') AS public_dbf,
    to_regclass('public.dbf_dbfchunkedupload') AS public_chunk,
    to_regclass('archive_dbf_upload.dbf_dbf') AS archived_dbf,
    to_regclass(
        'archive_dbf_upload.dbf_dbfchunkedupload'
    ) AS archived_chunk,
    to_regclass(
        'archive_dbf_upload.dbf_dbf_id_seq'
    ) AS archived_dbf_sequence,
    to_regclass(
        'archive_dbf_upload.dbf_dbfchunkedupload_id_seq'
    ) AS archived_chunk_sequence;
```

The two public columns must be null and all four archive columns must resolve.
Verify row counts with:

```sql
SELECT
    'archive_dbf_upload.dbf_dbf' AS object_name,
    count(*) AS rows
FROM archive_dbf_upload.dbf_dbf

UNION ALL

SELECT
    'archive_dbf_upload.dbf_dbfchunkedupload',
    count(*)
FROM archive_dbf_upload.dbf_dbfchunkedupload;
```

Also retain the archive SQL output showing sequence states, ownership,
defaults, constraints, indexes, and protected objects.

## Step 4 — Export verified archive package

PR #1038 introduced `archive_schemas_workflow.sh`,
`export_archive_schemas.sh`, and `restore_archive_schemas_validation.sh` for
the nine-schema archive workflow. Inspect that workflow before use. Its
approved schema list is hard-coded to nine schemas, so it cannot be called
directly for this DBF-only package. Do not claim that a DBF shell script exists.

For this package, use the equivalent manual command with a persistent package
path outside the Git worktree, `/tmp`, PostgreSQL data directories, and
`PGDATA`:

```bash
PACKAGE_DIR=/persistent/archive/path

pg_dump \
  -X \
  --format=custom \
  --compress=9 \
  --strict-names \
  --lock-wait-timeout=5s \
  --schema=archive_dbf_upload \
  --file="${PACKAGE_DIR}/dengue_archive_dbf_upload.dump" \
  dengue

sha256sum "${PACKAGE_DIR}/dengue_archive_dbf_upload.dump" \
  > "${PACKAGE_DIR}/dengue_archive_dbf_upload.dump.sha256"
pg_restore -l "${PACKAGE_DIR}/dengue_archive_dbf_upload.dump" \
  > "${PACKAGE_DIR}/dengue_archive_dbf_upload.toc"
pg_restore --schema-only \
  -f "${PACKAGE_DIR}/dengue_archive_dbf_upload.schema.sql" \
  "${PACKAGE_DIR}/dengue_archive_dbf_upload.dump"
```

Record the source database name and OID, exact object inventory, row counts,
sequence states, dependencies, Git commit, and UTC timestamp with the package.
Do not use `--clean`, `--create`, `--no-owner`, or `--no-acl`.

## Step 5 — Disposable restore validation

Permanent removal is forbidden until the dump has been restored into a
disposable database created from `template0`. Because the archive retains two
FKs to `public.auth_user(id)`, create only a minimal compatible fixture:
`public.auth_user(id integer primary key)`, populated with the distinct IDs
referenced by `archive_dbf_upload.dbf_dbf.uploaded_by_id` and
`archive_dbf_upload.dbf_dbfchunkedupload.user_id`.

After restore, validate:

- all four archive objects;
- exact row counts;
- sequence `last_value` and `is_called`;
- sequence ownership and defaults;
- indexes and constraints;
- both external FKs;
- owners and grants where roles exist.

Drop the disposable database after validation. Record a verification receipt
with status `PASS` only when every check succeeds.

## Step 6 — Permanent removal

**Permanent removal is a separate operation and is not part of archival.**

Inspect `20260803_90_remove_dbf_upload.sql`. It requires these exact psql
variables:

- `verified_package_path`;
- `expected_database_oid`;
- `expected_dump_sha256`;
- `verification_status`;
- `expected_dbf_rows`;
- `expected_dbfchunkedupload_rows`;
- `expected_dbf_id_seq_last_value`;
- `expected_dbf_id_seq_is_called`;
- `expected_dbfchunkedupload_id_seq_last_value`;
- `expected_dbfchunkedupload_id_seq_is_called`.

Use placeholders until verified evidence exists:

```bash
"${PSQL[@]}" \
  -v verified_package_path=/persistent/archive/path/dengue_archive_dbf_upload.dump \
  -v expected_database_oid=DATABASE_OID \
  -v expected_dump_sha256=SHA256_HEX \
  -v verification_status=PASS \
  -v expected_dbf_rows=DBF_ROW_COUNT \
  -v expected_dbfchunkedupload_rows=CHUNKED_UPLOAD_ROW_COUNT \
  -v expected_dbf_id_seq_last_value=DBF_SEQUENCE_LAST_VALUE \
  -v expected_dbf_id_seq_is_called=DBF_SEQUENCE_IS_CALLED \
  -v expected_dbfchunkedupload_id_seq_last_value=CHUNKED_SEQUENCE_LAST_VALUE \
  -v expected_dbfchunkedupload_id_seq_is_called=CHUNKED_SEQUENCE_IS_CALLED \
  -f "${SQL_DIR}/20260803_90_remove_dbf_upload.sql"
```

Run removal only after package export, SHA-256 verification, disposable
restore validation, inventory and row-count matching, database name/OID
matching, no-new-dependency checks, and explicit operational approval. Never
run it with guessed variables, never use `CASCADE`, never remove directly
after archival, and retain the verified package and removal evidence
permanently.

## Rollback policy

- A failed preflight changes nothing.
- A failed archive transaction rolls back automatically.
- Before permanent removal, rollback means moving the archived tables back to
  `public` through a separately reviewed transaction.
- After permanent removal, recovery requires the verified dump.
- Restoration must never overwrite an active database without a separate
  approved recovery plan.

## Current validation status

- PostgreSQL server tested: 14.23.
- The preflight passed locally and ended with `ROLLBACK`.
- The initial archive test exposed an unsupported `is_called` lookup in the
  sequence catalog view; the archive SQL now reads sequence state directly
  from the sequence relations.
- The corrected archive committed locally: public DBF objects are absent,
  archive row counts are `65` and `74`, and both archived sequences retain
  `is_called = true` with `last_value` values `65` and `74`.
- Removal has not been executed.
- Production has not been modified.

Schema snapshot files are generated and remain unchanged.
