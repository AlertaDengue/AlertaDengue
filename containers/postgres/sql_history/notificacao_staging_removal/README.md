# Legacy Notificacao Staging Removal

These scripts remove obsolete notification staging and import tables after a
completed read-only audit and disposable backup or restore validation.

## Exact Scope

The approved targets are only:

```text
public."""Municipio"".""Notificacao"""
"Municipio"."Notificacao__20220806"
"Municipio"."Corrigido2022"
```

The active application table is out of scope:

```text
"Municipio"."Notificacao"
```

## Active-Table Protection

`"Municipio"."Notificacao"` must never be dropped or modified.

Every script in this batch verifies that the active table exists as an
ordinary table. The guarded removal script records its OID before any target
drop and refuses to commit if the active OID changes.

## Why the Public Name Is Dangerous

The first approved target is dangerous because:

- its schema is `public`;
- its literal relation name contains quotes and a dot;
- static handwritten quoting is error-prone and can be confused with the
  active `"Municipio"."Notificacao"` table;
- exact catalog resolution plus `format('%I.%I', schema_name, relation_name)`
  is mandatory.

The removal SQL therefore resolves every target through `pg_namespace` and
`pg_class` before generating `DROP TABLE`.

## Accepted Audit Result

The preserved audit artifact in
`containers/postgres/sql_history/public_municipio_notificacao/` established
that the public literal-name table contains:

- `30000` rows;
- disease `A90` only;
- year `2022` only;
- notification dates from `2022-01-02` through `2022-12-31`;
- symptom dates from `2022-01-02` through `2022-12-29`;
- `579` municipalities;
- zero duplicate audited keys.

The audited relationship with `"Municipio"."Notificacao"` is:

```text
STRICT SUBSET OF ACTIVE
```

No active repository or database dependency was found, so physical removal is
approved when the reviewed batch is executed in an approved environment.

## Present or Absent Semantics

Present targets are:

1. backed up with object-level dumps;
2. restored in a disposable database;
3. removed with the guarded SQL;
4. validated afterward.

Already-absent targets are reported explicitly and are not falsely claimed as
deleted.

## Files and Order

1. `20260729_00_preflight_legacy_notificacao_staging.sql`
2. `20260729_01_remove_legacy_notificacao_staging.sql`
3. `20260729_02_validate_legacy_notificacao_staging_removal.sql`

Preflight:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/notificacao_staging_removal/20260729_00_preflight_legacy_notificacao_staging.sql
```

Removal:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/notificacao_staging_removal/20260729_01_remove_legacy_notificacao_staging.sql
```

Validation:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/notificacao_staging_removal/20260729_02_validate_legacy_notificacao_staging_removal.sql
```

## Execution Order

1. snapshot or backup readiness
2. preflight SQL
3. object-level dumps
4. checksums
5. `pg_restore -l` inspection
6. disposable restore verification
7. lock and activity preflight
8. removal SQL
9. validation SQL
10. application or ingestion smoke test
11. monitoring

## Rollback

Rollback after committed deletion uses the verified object-level dumps.

The SQL transaction itself rolls back automatically on any failure before
commit.

## Abort Conditions

Stop immediately when:

- PostgreSQL is in recovery;
- the active table is missing or is not `relkind = 'r'`;
- any approved target resolves to a non-table object;
- the public literal-name table no longer matches the accepted audit baseline;
- any view, materialized view, function, trigger, FK, publication,
  subscription, or other unresolved dependency appears;
- dump isolation for the public literal-name table cannot be proven exactly;
- the active table OID changes inside a disposable removal run;
- disposable restore proof fails;
- the worktree contains unrelated user changes;
- disk headroom is below the required local safety floor.

## Scope Boundary

This batch does not:

- touch staging;
- touch production;
- push Git commits;
- remove any object outside the three approved targets;
- archive objects instead of deleting them;
- modify application code.
