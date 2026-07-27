# Copernicus SQL History

These scripts archive the retired legacy Copernicus weather tables by moving
the live PostgreSQL relations into the restricted `archive_copernicus` schema.
They are manual SQL history and are not executed automatically by Docker,
Django, or PostgreSQL bootstrap.

Run them as the database owner, or as a role with `CREATE` on the database and
ownership of the affected tables and sequences. Always execute them with
`psql -X -v ON_ERROR_STOP=1` and validate on a disposable or staging database
before any production maintenance window.

## Files and order

1. `20260727_01_archive_legacy_copernicus.sql`
2. `20260727_02_validate_legacy_copernicus.sql`
3. `20260727_90_restore_legacy_copernicus.sql`

Archive:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/copernicus/20260727_01_archive_legacy_copernicus.sql
```

Validate:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/copernicus/20260727_02_validate_legacy_copernicus.sql
```

Restore:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/copernicus/20260727_90_restore_legacy_copernicus.sql
```

The scripts use explicit transactions, lock timeouts, and hard catalog
preconditions. They do not use `CASCADE`. Any unexpected dependency or partial
archive state must abort the run so the operator can review it explicitly.

## Archive and validation scope

`20260727_01_archive_legacy_copernicus.sql` creates `archive_copernicus`,
revokes schema access from `PUBLIC`, and moves these relations in one
transaction:

- `weather.copernicus_arg`
- `weather.copernicus_foz_do_iguacu`
- owned sequences discovered from PostgreSQL metadata

The active dataset `weather.copernicus_bra` is explicitly out of scope and
must remain under `weather` with its existing owner, grants, and unique
constraint.

Because the relations themselves move schemas, PostgreSQL preserves their
existing constraints, indexes, defaults, ownership, and ACLs. The follow-up
validation script checks those assumptions explicitly and reports actual row
counts and relation sizes from the tested environment.

Maintainer approval recorded on 2026-07-27 confirmed that no active external
producer or consumer still depends on `weather.copernicus_arg` or
`weather.copernicus_foz_do_iguacu`, while `weather.copernicus_bra` remains
active and externally accessible.

## Recovery boundary

`20260727_90_restore_legacy_copernicus.sql` is the reviewed reverse operation
for the same batch. It moves the tables and owned sequences back to `weather`
only when the original names are free and the dependency graph still matches
the approved batch.
