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

This is a same-database metadata move:

```sql
ALTER MATERIALIZED VIEW "Municipio".historico_casos
    SET SCHEMA archive_historico_casos;
```

Because the relation itself moves schemas, PostgreSQL preserves its indexes,
ownership, comments, populated state, and ACLs. The follow-up validation
script stays bounded to catalog checks plus archived-view row/date reporting.
It does not refresh the materialized view, copy `Municipio.Notificacao`,
compare full source tables, or create a validation database in staging or
production.

Repository and catalog review on 2026-07-27 confirmed that active runtime
flows use the disease-specific `"Historico_alerta"*` tables instead of
`historico_casos`, while the retained `Historico_alerta`,
`Historico_alerta_chik`, and `Historico_alerta_zika` tables remain unchanged
and out of scope for this batch.

External usage was reviewed, no active external consumer or refresh process
was identified, and the archival was approved.

## Production preflight

Before a maintenance window, the operator must confirm:

```bash
df -h <postgres_data_mount>
df -i <postgres_data_mount>
```

Record the available bytes, available inodes, latest backup or snapshot
confirmation, PostgreSQL health, absence of recovery mode, absence of a
blocking long-running transaction, and the expected source and target schema
state.

Run these read-only PostgreSQL prechecks before the archive script:

```sql
SELECT pg_is_in_recovery();
```

```sql
SELECT
    pg_size_pretty(pg_total_relation_size(
        '"Municipio".historico_casos'::regclass
    )) AS historico_casos_size;
```

```sql
SELECT
    pid,
    usename,
    application_name,
    state,
    xact_start,
    query_start,
    wait_event_type,
    wait_event,
    left(query, 200) AS query
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid <> pg_backend_pid()
ORDER BY xact_start NULLS LAST, query_start;
```

Abort execution when the filesystem is critically low, PostgreSQL is in
recovery, the source object is not `relkind = 'm'`, the archive schema state
is unexpected, an external dependency is discovered, a long-running lock holder
is active, backup readiness is not confirmed, or any precheck fails. The
archive itself is metadata-only and should add negligible permanent storage,
but the operator must still maintain normal PostgreSQL operational headroom.

## Production execution order

1. backup or snapshot confirmation
2. disk and inode preflight
3. PostgreSQL health and lock preflight
4. archive script
5. validation script
6. application smoke tests
7. log, disk, and lock monitoring

The archive requires an `ACCESS EXCLUSIVE` lock on the materialized view.
`lock_timeout` prevents waiting indefinitely. The shared validation script is
bounded and uses `SET LOCAL temp_file_limit = '1GB'`. The prior full
content-equivalence audit belongs only in a disposable validation environment;
do not repeat that comparison in staging or production, and do not create a
production validation database. Restoration is a reviewed rollback path, not a
normal execution step.

## Recovery boundary

`20260727_90_restore_legacy_historico_casos.sql` is the reviewed reverse
operation for the same batch. It moves the materialized view back to
`"Municipio"` only when the original name is free and the dependency graph
still matches the approved batch. If `archive_historico_casos` is empty after
restoration, the script removes the empty schema so another complete archive
cycle can run cleanly without manual schema cleanup.
