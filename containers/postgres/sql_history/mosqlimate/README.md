# Mosqlimate SQL History

These scripts archive the frozen `Municipio.sprint202425` Mosqlimate dataset by
moving the live PostgreSQL relation into the restricted `archive_mosqlimate`
schema. They are manual SQL history and are not executed automatically by
Docker, Django, or PostgreSQL bootstrap.

Run them as the database owner, or as a role with `CREATE` on the database and
ownership of the affected table and owned sequence. Always execute them with
`psql -X -v ON_ERROR_STOP=1` and validate on a disposable or staging database
before any production maintenance window.

## Files and order

1. `20260728_01_archive_mosqlimate_sprint202425.sql`
2. `20260728_02_validate_mosqlimate_sprint202425.sql`
3. `20260728_90_restore_mosqlimate_sprint202425.sql`

Archive:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/mosqlimate/20260728_01_archive_mosqlimate_sprint202425.sql
```

Validate:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/mosqlimate/20260728_02_validate_mosqlimate_sprint202425.sql
```

Restore:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/mosqlimate/20260728_90_restore_mosqlimate_sprint202425.sql
```

The scripts use explicit transactions, lock timeouts, and hard catalog
preconditions. They do not use `CASCADE`, `DROP TABLE`, `TRUNCATE`,
`CREATE TABLE AS`, or `INSERT ... SELECT`. Any unexpected dependency or partial
archive state aborts the run so the operator can review it explicitly.

## Archive and validation scope

`20260728_01_archive_mosqlimate_sprint202425.sql` creates
`archive_mosqlimate`, revokes schema access from `PUBLIC`, and moves this
relation in one transaction:

- `"Municipio".sprint202425`
- the owned sequence discovered from PostgreSQL metadata

The dataset is a metadata-only, same-database move:

```sql
ALTER TABLE "Municipio".sprint202425
    SET SCHEMA archive_mosqlimate;
```

`Municipio.sprint202425` is a frozen historical dataset prepared for the
Mosqlimate event held in 2025. It contains modeling-specific training and
target fields and is not a backup of `Municipio.Notificacao`. The dataset is
retained in `archive_mosqlimate` for reproducibility and historical reference.

Because the relation itself moves schemas, PostgreSQL preserves its rows,
table OID, primary key, primary-key index, defaults, ownership, ACLs, and
owned sequence relationship. The follow-up validation script is bounded to
catalog checks plus exact count and date/epiweek reporting. It does not copy
the `625 MB` relation, does not copy `Municipio.Notificacao`, and does not
repeat the expensive logical comparison with active notifications.

The absent relations `Municipio.Notificacao__20220806` and
`Municipio.Corrigido2022` were not present in the audited catalog and are
explicitly out of scope for this batch.

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
        '"Municipio".sprint202425'::regclass
    )) AS sprint202425_size;
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

Abort execution when PostgreSQL is in recovery, the source object is not
`relkind = 'r'`, the archive schema state is unexpected, an external consumer
still requires the old qualified name, a blocking lock holder is active,
filesystem headroom is critically low, backup readiness is not confirmed, or
any precheck fails.

## Production execution order

1. backup or snapshot confirmation
2. disk and inode preflight
3. PostgreSQL health and lock preflight
4. external raw-SQL and consumer verification for `"Municipio".sprint202425`
5. archive script
6. validation script
7. application and external-consumer smoke checks
8. log, disk, and lock monitoring

The archive requires an `ACCESS EXCLUSIVE` lock on `sprint202425`.
`lock_timeout` prevents waiting indefinitely. Validation is read-only and
bounded. The operation is atomic and metadata-only, so it does not reclaim
disk space and should not materially increase storage use beyond normal
transactional overhead. Restore is a reviewed rollback path, not a normal
production step.

## Recovery boundary

`20260728_90_restore_mosqlimate_sprint202425.sql` is the reviewed reverse
operation for the same batch. It moves the table and owned sequence back to
`"Municipio"` only when the original names are free and the dependency graph
still matches the approved batch. If `archive_mosqlimate` is empty after
restoration, the script removes the empty schema so another complete archive
cycle can run cleanly without manual cleanup.
