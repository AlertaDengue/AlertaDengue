# REDEMET database removal history

This directory records the manual database operations used to archive and
remove the legacy REDEMET/Weather Underground airport-station structures.
These files are SQL history and are not run automatically by Docker, Django,
or PostgreSQL setup.

## Files and order

The filenames use `YYYYMMDD_NN_action_subject.sql`, where the date records when
the operation was prepared and `NN` records the required execution order.

1. `20260612_01_archive_legacy_redemet.sql`
2. Validate the archive and confirm that no reader or writer still uses the
   legacy structures.
3. `20260612_02_remove_legacy_redemet.sql`

Run each file separately as the database owner. Do not run both files in one
transaction or deployment step.

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/redemet/20260612_01_archive_legacy_redemet.sql
```

After validation and an observation window:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/redemet/20260612_02_remove_legacy_redemet.sql
```

`ON_ERROR_STOP=1` is required so `psql` exits immediately when a statement
fails. Both scripts also use transactions, so a failure rolls back that
script's changes.

## Archive script

`20260612_01_archive_legacy_redemet.sql` creates the restricted
`archive_redemet` schema and preserves:

- the complete `"Municipio"."Clima_wu"` table;
- the complete `"Municipio"."Estacao_wu"` table;
- station-code values from `"Dengue_global".parameters`;
- station-code values from `"Dengue_global".regional_saude`;
- station-code values from `"Municipio"."Localidade"`;
- a manifest containing archive table names and row counts.

The full legacy tables are copied with `LIKE ... INCLUDING ALL`. PostgreSQL
also copies column defaults with that option. The script therefore removes the
copied `archive_redemet.clima_wu.id` default so the archive does not depend on
the active `"Municipio"."Clima_wu_id_seq"` sequence.

The archive uses fixed table names and is intentionally a one-time operation.
Do not rerun it after a successful archive without a reviewed recovery plan.

## Validation before removal

Before running the removal script:

- compare every source and archive row count;
- compare relevant date ranges and checksums where practical;
- test that the archive can be read by the intended restricted role;
- confirm normal application roles cannot modify the archive;
- confirm database dependencies and query logs show no remaining readers;
- stop any external station-data writer;
- retain a full database backup through the agreed retention period.

The manifest is evidence that the archive step completed, but it is not a
substitute for these checks.

## Removal script

`20260612_02_remove_legacy_redemet.sql`:

- requires the archive manifest and its `Clima_wu` record;
- detaches the copied archive default if the archive came from the original
  version of the archive script;
- drops `codigo_estacao_wu` and `estacao_wu_sec` from the applicable active
  tables;
- drops `"Municipio"."Clima_wu"` and `"Municipio"."Estacao_wu"`;
- allows PostgreSQL to drop the sequence owned by `Clima_wu.id`;
- uses short lock and statement timeouts to avoid blocking production.

The table drops deliberately omit `CASCADE`. If an unknown database object
still depends on a legacy table, PostgreSQL aborts and rolls back the removal
instead of silently deleting that object.

## Recovery

Recovery means recreating the removed structures from the restricted archive
and a retained database backup. It is not an automatic reverse migration.
Review and test the recovery procedure before applying the removal in
production.
