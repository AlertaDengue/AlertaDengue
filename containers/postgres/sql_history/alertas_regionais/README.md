# Regional Alerts SQL History

These scripts archive the retired regional-alert tables by moving the live
PostgreSQL relations into the restricted `archive_alertas_regionais` schema.
They are manual SQL history and are not executed automatically by Docker,
Django, or PostgreSQL bootstrap.

Run them as the database owner, or as a role with `CREATE` on the database and
ownership of the affected tables and sequences. Always execute them with
`psql -X -v ON_ERROR_STOP=1` and validate on a disposable or staging database
before any production maintenance window.

## Files and order

1. `20260724_01_archive_legacy_alertas_regionais.sql`
2. `20260724_02_validate_legacy_alertas_regionais.sql`
3. `20260724_90_restore_legacy_alertas_regionais.sql`

Archive:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/alertas_regionais/20260724_01_archive_legacy_alertas_regionais.sql
```

Validate:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/alertas_regionais/20260724_02_validate_legacy_alertas_regionais.sql
```

Restore:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/alertas_regionais/20260724_90_restore_legacy_alertas_regionais.sql
```

The scripts use explicit transactions, lock timeouts, and hard catalog
preconditions. They do not use `CASCADE`. Any unexpected dependency or partial
archive state must abort the run so the operator can review it explicitly.

## Archive and validation scope

`20260724_01_archive_legacy_alertas_regionais.sql` creates
`archive_alertas_regionais`, revokes schema access from `PUBLIC`, and moves
these relations in one transaction:

- `"Dengue_global".alerta_regional_dengue`
- `"Dengue_global".alerta_regional_chik`
- `"Dengue_global".alerta_regional_zika`
- `"Municipio".alerta_mrj`
- `"Municipio".alerta_mrj_chik`
- `"Municipio".alerta_mrj_zika`
- owned sequences discovered from PostgreSQL metadata

`"Dengue_global"."regional_saude"` remains active and is validated explicitly
before and after the move. The three regional-alert foreign keys to
`"Dengue_global".regional(id)` remain live across schemas, while the Rio
municipal-alert tables keep their original unique constraints, defaults,
comments, ownership, and ACLs.

## Recovery boundary

`20260724_90_restore_legacy_alertas_regionais.sql` is the reviewed reverse
operation for the same batch. It moves the tables and owned sequences back to
their original schemas only when the original names are free and the dependency
graph still matches the approved batch.
