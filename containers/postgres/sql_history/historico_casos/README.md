# Historico Casos SQL History

These scripts archive the legacy `historico_casos` materialized view by moving
the live PostgreSQL relation into the restricted `archive_historico_casos`
schema. They are manual SQL history and are not executed automatically by
Docker, Django, or PostgreSQL bootstrap.

Run them as the database owner, or as a role with `CREATE` on the database and
ownership of the affected relation. Always execute them with
`psql -X -v ON_ERROR_STOP=1` and validate on a disposable or staging database
before any production maintenance window.

## Files and order

1. `20260727_01_archive_legacy_historico_casos.sql`
2. `20260727_02_validate_legacy_historico_casos.sql`
3. `20260727_90_restore_legacy_historico_casos.sql`

Archive:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/historico_casos/20260727_01_archive_legacy_historico_casos.sql
```

Validate:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/historico_casos/20260727_02_validate_legacy_historico_casos.sql
```

Restore:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/historico_casos/20260727_90_restore_legacy_historico_casos.sql
```

The scripts use explicit transactions, lock timeouts, and hard catalog
preconditions. They do not use `CASCADE`. Any unexpected dependency or partial
archive state must abort the run so the operator can review it explicitly.

## Archive and validation scope

`20260727_01_archive_legacy_historico_casos.sql` creates
`archive_historico_casos`, revokes schema access from `PUBLIC`, and moves this
relation in one transaction:

- `"Municipio".historico_casos`

Because the relation itself moves schemas, PostgreSQL preserves its indexes,
ownership, comments, and ACLs. The follow-up validation script checks those
assumptions explicitly and reports actual row counts, latest data dates, and
relation sizes from the tested environment.

Repository and catalog review on 2026-07-27 confirmed that active runtime
flows use the disease-specific `"Historico_alerta"*` tables instead of
`historico_casos`, while the retained `Historico_alerta`,
`Historico_alerta_chik`, and `Historico_alerta_zika` tables remain unchanged
and out of scope for this batch.

## Recovery boundary

`20260727_90_restore_legacy_historico_casos.sql` is the reviewed reverse
operation for the same batch. It moves the materialized view back to
`"Municipio"` only when the original name is free and the dependency graph
still matches the approved batch. If `archive_historico_casos` is empty after
restoration, the script removes the empty schema so another complete archive
cycle can run cleanly.
