# Public Municipio Notificacao Audit

This directory contains a read-only audit for the legacy PostgreSQL relation
stored as:

```text
public."""Municipio"".""Notificacao"""
```

That object is a plain table in schema `public` whose literal relation name is
`"Municipio"."Notificacao"`. It is distinct from the active application table:

```text
"Municipio"."Notificacao"
```

## Purpose

Determine whether the `public` object is active, archival-only, or a removal
candidate without moving, renaming, truncating, or dropping it.

## Execution

Run only against a disposable or approved local audit environment:

```bash
psql -X -v ON_ERROR_STOP=1 \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f containers/postgres/sql_history/public_municipio_notificacao/20260729_00_audit_public_municipio_notificacao.sql
```

The SQL uses:

- `SET TRANSACTION READ ONLY`
- `statement_timeout = '30min'`
- `lock_timeout = '5s'`
- `temp_file_limit = '1GB'`
- `work_mem = '64MB'`

## Audit Summary

The reviewed local database on 2026-07-29 showed:

- exact candidate: `public."""Municipio"".""Notificacao"""`
- `relkind = 'r'`
- owner `dengueadmin`
- size about `26 MB`
- estimated rows about `30000`
- no PK, unique constraints, indexes, triggers, publications, subscriptions,
  dependent views, or dependent materialized views
- owner-only table privileges

The candidate stores raw SINAN-style columns as `text`, including:

- `NU_NOTIFIC`
- `ID_AGRAVO`
- `DT_NOTIFIC`
- `SEM_NOT`
- `NU_ANO`
- `ID_MUNICIP`
- `CLASSI_FIN`
- `CRITERIO`

The active table remains the typed, indexed relation:

```text
"Municipio"."Notificacao"
```

## Data Summary

The audited candidate data profile was:

- exact row count `30000`
- disease set limited to `A90`
- year limited to `2022`
- notification dates from `2022-01-02` through `2022-12-31`
- symptom dates from `2022-01-02` through `2022-12-29`
- epidemiological weeks from `202201` through `202252`
- `579` distinct municipalities
- no invalid date, week, municipality, or disease-code rows
- no duplicate rows on
  `("NU_NOTIFIC", "DT_NOTIFIC", "ID_AGRAVO", "ID_MUNICIP")`

Latest trustworthy period:

- latest notification date `2022-12-31`
- latest symptom date `2022-12-29`
- latest epiweek `202252`

## Relationship With Active Notifications

Comparison against `"Municipio"."Notificacao"` used a normalized municipality
join:

```text
active.municipio_geocodigo / 10 = candidate.ID_MUNICIP::integer
```

That local audit found:

- all `30000` candidate rows matched active rows on
  `(nu_notific, dt_notific, cid10_codigo, normalized municipality)`
- no matched rows differed on `classi_fin` or `criterio`
- the candidate contributed no candidate-only key rows
- active `A90` data for 2022 contained substantially more rows than the
  candidate, including many additional rows within the candidate municipality
  set

Relationship classification:

```text
STRICT SUBSET OF ACTIVE
```

## Probable Origin

Current evidence supports a legacy import or staging-snapshot origin rather
than an active application table:

- the candidate name is a literal quoted schema-qualified string
- the structure is raw all-`text` SINAN-style data
- no current repository code references it
- no current database object depends on it
- the first confirmed repository appearance is in the schema dump during the
  2026-06-26 upload-removal series

No explicit Django model or migration creating this exact table name was found.

## Retention Decision

Current audit decision:

```text
CANDIDATE FOR DELETION AFTER SEPARATE APPROVAL
```

This task does not provide deletion SQL and does not authorize deletion by
itself.

## Unresolved Questions

- Whether any external operator workflow still reads this `public` table
  outside the repository
- Whether the table was created by a one-off restore, a manual import, or a
  retired upload-side snapshot process

Until external usage is reviewed, do not drop the object.
