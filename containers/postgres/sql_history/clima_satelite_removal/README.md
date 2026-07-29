# Remove Empty Legacy `Municipio.Clima_Satelite`

This batch removes the empty legacy table `"Municipio"."Clima_Satelite"` and
its owned sequence `"Municipio"."Clima_Satelite_id_seq"` from the active
schema.

Removal decision: `APPROVED`

Archive implementation: `NOT APPLICABLE`

## Historical purpose

Historical purpose:

```text
Precipitation, temperature, and vegetation-index satellite data.
```

The historical table comment must be preserved as-is when referenced:

```text
Precipitação, temperatura e NVDI
(Normalized Difference Vegetation Index)
```

## Removal reason

- The July 29, 2026 audit found exactly zero rows.
- No active repository dependency was found outside schema/documentation
  references.
- No active local database dependency was found.
- The historical ingestion path is retired.
- Archiving would preserve no data, so physical removal was approved.

## Scope

Only these objects are approved for removal:

```text
"Municipio"."Clima_Satelite"
"Municipio"."Clima_Satelite_id_seq"
```

## Safety

- Exact catalog resolution is required before any `DROP TABLE`.
- The table must be present as `relkind = 'r'`.
- The owned sequence must be present as `relkind = 'S'`.
- A hard zero-row gate blocks removal when any row exists.
- Sequence ownership must still point to `"Municipio"."Clima_Satelite".id`.
- No `CASCADE` is allowed.
- No archive schema is created.
- Unrelated climate tables must remain untouched.
- A schema-only backup and restore proof is required before removal.

## Shared-environment order

1. backup/snapshot readiness
2. preflight
3. schema-only dump
4. checksum
5. `pg_restore -l` inspection
6. disposable restore proof
7. lock/activity preflight
8. removal
9. validation
10. application/worker monitoring

## Rollback

Rollback uses the verified schema-only dump created before removal.

No row-data restore is required because the table is approved for removal only
when it is empty.

## Files

- `20260729_00_preflight_clima_satelite_removal.sql`
- `20260729_01_remove_clima_satelite.sql`
- `20260729_02_validate_clima_satelite_removal.sql`
