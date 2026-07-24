# Ovitrampa SQL History

These scripts archive the legacy `Municipio` Ovitrampa tables by moving the
live PostgreSQL relations into the restricted `archive_ovitrampa` schema.
They are manual SQL history and are not executed automatically by Docker,
Django, or PostgreSQL bootstrap.

Run them as the database owner, or as a role with `CREATE` on the database and
ownership of the affected tables and sequences. Always execute them with
`psql -X -v ON_ERROR_STOP=1` and validate on a disposable or staging database
before any production maintenance window.

## Files and order

1. `20260724_01_archive_legacy_ovitrampa.sql`
2. `20260724_02_validate_legacy_ovitrampa.sql`
3. `20260724_90_restore_legacy_ovitrampa.sql`

Archive:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/ovitrampa/20260724_01_archive_legacy_ovitrampa.sql
```

Validate:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/ovitrampa/20260724_02_validate_legacy_ovitrampa.sql
```

Restore:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/ovitrampa/20260724_90_restore_legacy_ovitrampa.sql
```

The scripts use explicit transactions, lock timeouts, and hard catalog
preconditions. They do not use `CASCADE`. Any unexpected dependency or partial
archive state must abort the run so the operator can review it explicitly.

## Archive and validation scope

`20260724_01_archive_legacy_ovitrampa.sql` creates `archive_ovitrampa`,
revokes schema access from `PUBLIC`, and moves these relations in one
transaction:

- `"Municipio"."Localidade"`
- `"Municipio"."Bairro"`
- `"Municipio"."Ovitrampa"`
- owned sequences discovered from PostgreSQL metadata

Because the relations themselves move schemas, PostgreSQL preserves their
primary keys, foreign keys, indexes, defaults, comments, ownership, and ACLs.
The follow-up validation script checks those assumptions explicitly and reports
actual row counts and relation sizes from the tested environment.

## Recovery boundary

`20260724_90_restore_legacy_ovitrampa.sql` is the reviewed reverse operation
for the same batch. It moves the tables and owned sequences back to
`"Municipio"` only when the original names are free and the dependency graph
still matches the approved batch.
