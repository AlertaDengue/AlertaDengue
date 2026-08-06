# Empty generic chunked-upload table in `infodengue`

This workflow addresses issue #1051 and is exclusively for a development or
staging `infodengue` database. It removes the reviewed empty generic table and
its table-owned sequence:

- `public.chunked_upload_chunkedupload`
- `public.chunked_upload_chunkedupload_id_seq`

The application dependency was retired by the historical upload-app workflow.
Repository references are limited to historical SQL in
`containers/postgres/sql_history/upload/` and a tracked notebook’s historical
table listing. There are no active Django settings, models, routes, tasks,
management commands, tests, container scripts, migrations, or bootstrap/schema
references for this app/table.

## Safety

Use only a reviewed development/staging connection. Never use a production
connection. Configure libpq credentials outside the repository:

```bash
SQL_DIR=containers/postgres/sql_history/remove_empty_infodengue_chunked_upload
PSQL=(psql -X -v ON_ERROR_STOP=1)
```

The preflight and validator are read-only transactions ending with `ROLLBACK`.
The removal script requires the exact database name, an explicit approval
token, an advisory transaction lock, a zero-row recheck, dependency checks, and
proof that the sequence is owned by the target table’s `id` column. It drops
only the one named table and relies on PostgreSQL’s ownership dependency to
remove the owned sequence.

## Step 1 — Read-only preflight

```bash
"${PSQL[@]}" -v expected_database_name=infodengue \
  -f "${SQL_DIR}/20260806_00_preflight_empty_infodengue_chunked_upload.sql"
```

Review the exact row count, size, columns, constraints, indexes, triggers,
rules, sequence owner/state, ownership dependency, and dependency inventory.
The script must finish with `ROLLBACK`. Any row or unexpected inbound
foreign-key/view/rule dependency is a hard failure.

## Step 2 — Explicit removal after review

Do not run removal as part of ordinary validation. After separate review and
development/staging confirmation, invoke it with the exact token:

```bash
"${PSQL[@]}" \
  -v expected_database_name=infodengue \
  -v removal_approval=REMOVE_APPROVED_EMPTY_INFODENGUE_CHUNKED_UPLOAD \
  -f "${SQL_DIR}/20260806_90_remove_empty_infodengue_chunked_upload.sql"
```

The transaction commits only after the table and owned sequence are absent.
Retain the command output as the removal receipt. No separate sequence drop is
issued.

## Step 3 — Read-only post-removal validation

```bash
"${PSQL[@]}" -v expected_database_name=infodengue \
  -f "${SQL_DIR}/20260806_91_validate_empty_infodengue_chunked_upload_removed.sql"
```

The validator must finish with `ROLLBACK`, confirm both target objects are
absent, and confirm these protected objects remain:

- `public.auth_user`
- `public.django_migrations`
- `public.django_session`
- `public.spatial_ref_sys`
- `topology.topology`
- `topology.layer`

DBF objects and historical `Dengue_*` objects are intentionally not required;
they belong to separate cleanup issues.

## Current evidence and checks

The reviewed development/staging audit found exact row count zero. The generic
table is not in the current `schemas_infodengue.sql`; its old upload-app SQL
history is retained as historical evidence and is not bootstrap input. No live
preflight was run while preparing this package because no local PostgreSQL
endpoint was available. Removal is not authorized by this commit.
