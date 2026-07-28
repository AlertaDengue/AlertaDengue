# Tweet SQL History

These scripts archive the frozen historical `Municipio.Tweet` dataset by moving
the live PostgreSQL relation into the restricted `archive_tweets` schema. They
are manual SQL history and are not executed automatically by Docker, Django, or
PostgreSQL bootstrap.

Run them as the database owner, or as a role with `CREATE` on the database and
ownership of the affected table and owned sequence. Always execute them with
`psql -X -v ON_ERROR_STOP=1` and validate on a disposable or staging database
before any production maintenance window.

## Files and order

1. `20260728_01_archive_legacy_tweets.sql`
2. `20260728_02_validate_legacy_tweets.sql`
3. `20260728_90_restore_legacy_tweets.sql`

Archive:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/tweets/20260728_01_archive_legacy_tweets.sql
```

Validate:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/tweets/20260728_02_validate_legacy_tweets.sql
```

Restore:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/tweets/20260728_90_restore_legacy_tweets.sql
```

The scripts use explicit transactions, lock timeouts, and hard catalog
preconditions. They do not use `CASCADE`, `DROP TABLE`, `TRUNCATE`,
`CREATE TABLE AS`, or `INSERT ... SELECT`. Any unexpected dependency or partial
archive state aborts the run so the operator can review it explicitly.

## Archive and validation scope

`20260728_01_archive_legacy_tweets.sql` creates `archive_tweets`, revokes
schema access from `PUBLIC`, and moves:

- `"Municipio"."Tweet"`
- `"Municipio"."Tweet_id_seq"`

Tweet collection stopped in 2022. The table stores daily aggregated dengue
tweet counts, not raw tweet content. The frozen dataset covers `2012-08-01`
through `2022-09-05`, contains only `CID10 = A90`, and is retained under
`archive_tweets` for historical reproducibility.

The archive is a same-database metadata move:

```sql
ALTER TABLE "Municipio"."Tweet"
    SET SCHEMA archive_tweets;
```

Because the relation itself moves schemas, PostgreSQL preserves its rows, table
OID, primary key, indexes, default, foreign key, ownership, ACLs, comment, and
owned sequence relationship. Permanent storage growth should be negligible; the
move does not create another `303 MB` copy of the dataset.

The follow-up validation script is read-only and bounded to catalog checks plus
exact row-count and profile reporting. It does not copy unrelated large tables,
does not compare against `Municipio.Notificacao`, and does not rebuild any
relation.

For disposable fixture validation, operators may set session-scoped
`archive_tweets.expected_*` parameters before executing the archive and
validation scripts so the same SQL can enforce the fixture's tiny expected
row-count and date/profile values without changing the checked-in production
baseline.

The active `AlertaDengueAnalise` pipeline does not consume the dataset, and no
current external consumer is known. `AlertaDengue` has no active runtime
dependency on `Municipio.Tweet`, and `pipe_infodengue()` retains only
`casoscli$tweet <- NA` for historical output shape.

## Minimal disposable validation

Use a disposable database created from `template0` or schema-only SQL. Do not
copy the full tweet table. Insert only a small fixture with:

- at least two municipalities
- multiple dates across two epidemiological weeks
- `A90` only
- zero and non-zero `numero`

Run this cycle:

1. archive
2. validate
3. restore
4. archive
5. validate

The second archive must succeed without manual cleanup.

## Production preflight

Before a maintenance window, the operator must confirm:

```bash
df -h <postgres_data_mount>
df -i <postgres_data_mount>
```

Run these read-only PostgreSQL prechecks:

```sql
SELECT pg_is_in_recovery();
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

Abort when PostgreSQL is in recovery, the source object metadata differs from
the audited baseline, the archive schema state is unexpected, a blocking lock
holder is active, backup readiness is not confirmed, or any precheck fails.

## Recovery boundary

`20260728_90_restore_legacy_tweets.sql` is the reviewed reverse operation for
the same batch. It moves the table and owned sequence back to `"Municipio"`
only when the original names are free and the dependency graph still matches
the approved batch. If `archive_tweets` is empty after restoration, the script
removes the empty schema so another complete archive cycle can run cleanly
without manual cleanup.
