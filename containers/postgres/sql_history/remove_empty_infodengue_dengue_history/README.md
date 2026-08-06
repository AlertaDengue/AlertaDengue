# Empty historical dengue tables in `infodengue`

This workflow addresses issue #1050 and is exclusively for the development or
staging `infodengue` database. It removes only these five reviewed empty
side-effect tables:

- `public."Dengue_2010"`
- `public."Dengue_2011"`
- `public."Dengue_2012"`
- `public."Dengue_2013"`
- `public."DengueConfirmados_2013"`

The authoritative historical data was handled separately in the `dengue`
database workflow. This package does not touch DBF tables, Django framework
tables, PostGIS, topology, authentication, session, or migration objects.

## Reference review

The five names have no active Python, Django model, Admin, view, URL, Celery,
management-command, R, SQL, or migration references. Their only repository
definitions were bootstrap DDL in `schemas_infodengue.sql`, which was removed
in this change. A tracked notebook contains historical tabular output listing
the names; it is documentation/analysis output and was not changed.

## Safety

Use only a reviewed development/staging connection. Never use a production
connection. Configure libpq credentials outside the repository and use:

```bash
SQL_DIR=containers/postgres/sql_history/remove_empty_infodengue_dengue_history
PSQL=(psql -X -v ON_ERROR_STOP=1)
```

The preflight and post-removal validator are read-only transactions ending in
`ROLLBACK`. The removal script is guarded by the exact database name,
zero-row checks, dependency checks, an advisory transaction lock, and an
explicit approval token. It issues only the five named table removals and
commits only after post-removal and protected-object assertions pass.

## Step 1 — Read-only preflight

Run and review all output:

```bash
"${PSQL[@]}" -v expected_database_name=infodengue \
  -f "${SQL_DIR}/20260806_00_preflight_empty_infodengue_dengue_history.sql"
```

The preflight must end with `ROLLBACK`. It confirms the exact five-table
inventory, zero rows, columns, constraints, indexes, triggers, rules, sizes,
and dependency inventory. Any row or unexpected dependent object is a hard
failure.

## Step 2 — Explicit removal after review

Do not run this command as part of ordinary validation. After separate review,
development/staging confirmation, and approval, invoke the guarded script with
the exact token:

```bash
"${PSQL[@]}" \
  -v expected_database_name=infodengue \
  -v removal_approval=REMOVE_APPROVED_EMPTY_INFODENGUE_DENGUE_HISTORY \
  -f "${SQL_DIR}/20260806_90_remove_empty_infodengue_dengue_history.sql"
```

Retain the command output as the removal receipt. It records the database,
timestamp, pre-removal zero-row inventory, and post-removal protected-object
checks.

## Step 3 — Read-only post-removal validation

```bash
"${PSQL[@]}" -v expected_database_name=infodengue \
  -f "${SQL_DIR}/20260806_91_validate_empty_infodengue_dengue_history_removed.sql"
```

The validator must end with `ROLLBACK`, confirm all five candidates are absent,
and confirm the DBF tables, `public.auth_user`, `public.django_migrations`,
`public.spatial_ref_sys`, `topology.topology`, and `topology.layer` remain.

## Current evidence and repository checks

The reviewed development/staging audit found exact row count zero for all five
candidate tables. No live preflight was run while preparing this package unless
the operator supplies an available non-production `infodengue` connection.
No removal is authorized by this commit.

Run `git diff --check`, the repository’s forbidden-operation scan, the exact
reference search from issue #1050, and pre-commit checks limited to changed
files before committing.
