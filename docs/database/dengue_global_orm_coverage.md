# `Dengue_global` ORM coverage audit (#1107)

Audit date: 2026-09-04.  This is a read-only inventory of the live
`"Dengue_global"` schema reached through Django's `dados` alias.  It replaces
the now-stale Phase 1 proposals in `orm_inventory.md` for this schema; it does
not assign ownership to external relations or propose one model per table.

## Method and scope

The audit used `pg_class`, `information_schema.columns`, `pg_constraint`, and
`pg_index` through `connections["dados"]`.  Counts below are catalog estimates
(`pg_class.reltuples`), not unrestricted `COUNT(*)`; no rows or credentials
were read or printed.  The catalog contained 11 relations: eight ordinary
tables and three sequences.  It contained no partitioned tables or partitions,
views, materialized views, or foreign tables.

Repository evidence was searched across application Python, SQL, management
commands, tests, migrations, documentation, and operational history, excluding
dependencies and generated assets from runtime conclusions.  The relevant
runtime paths are `dados.services.dengue_global_lookups`,
`dados.services.municipality_map_metadata`, `dados.dbdata`, `dados.maps`,
`dados.tasks`, `dados.management.commands.sync_geofiles`, and `api.db`.

`DatabaseAppsRouter` maps the `dados` app to the `dados` alias
(`ad_main/settings/base.py`); it routes that app away from `default`.  The
newer bounded lookup service relies on this router, while
`municipality_map_metadata.get_city_info()` explicitly calls
`.using("dados")`.  The six externally owned adapters are unmanaged and are
represented through Django state-only operations where applicable.
`ParameterUF` is application-managed and has schema/data migration ownership.

## Physical-object and coverage matrix

| Object | Type / owner | Identity; estimate / total size | Active readers / writers | ORM model and field coverage | Alias | Classification | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `CID10` | table / `administrador` | PK `codigo`; 8,349 / 934 kB | `api.db` joins; no repository writer | `dados.models.CID10`, 2/2 columns, exact | `dados` / SQLAlchemy engine | ORM-backed application object | Retain adapter; joins remain SQL boundary. |
| `Municipio` | table / `administrador` | PK `geocodigo`; 5,570 / 18 MB | ORM search/report/map scalar reads; API/report/geofile/task SQL joins; no repository writer | `City`, 8/10 columns. `geojson` is deliberately excluded; mapped `id_regional`, `regional`, `macroregional_id`, `macroregional` are physically nullable and correctly declare `null=True` after #1112. | `dados` | application object with intentional partial ORM projection | Keep geometry/GeoJSON and joins SQL. |
| `estado` | table / `administrador` | PK `geocodigo`; 27 / 11 MB | Indirectly through retained state-history materialized-view SQL; no writer evidence | `State`, 3/5 columns. `geojson` and `regiao` are intentionally outside its lookup projection. | `dados` | application object with intentional partial ORM projection | Retain only bounded reference projection. |
| `macroregional` | table / `dengueadmin` | PK `id`; 118 / 40 kB | `Regional.macroregion` FK; no writer evidence | `MacroRegion`, 2/4 columns. `codigo` and nullable `uf` omitted intentionally. | `dados` | application object with intentional partial ORM projection | Retain relationship adapter. |
| `parameters` | table / `dengueadmin` | composite PK `(municipio_geocodigo, cid10)`; 11,064 / 1.4 MB | `RegionalParameters` compatibility facade / city reports; no writer evidence | `Parameter`, 9/10 columns with Django composite PK. Nullable thresholds match. `codmodelo` omitted from the bounded report-parameter projection. | `dados` | application object with intentional partial ORM projection | Retain; every lookup must retain both key predicates. |
| `parameters_uf` | table / `postgres` | composite PK `(state_code, cid10)`; 52 / 49 kB | managed migrations/data lifecycle; no prominent direct runtime read | `ParameterUF`, 7/7 columns, composite PK and state index match | `dados` | ORM-backed application object | Retain managed model. |
| `regional` | table / `dengueadmin` | PK `id`; FK `id_macroregional`; 451 / 123 kB | regional names/cities through ORM service; no writer evidence | `Regional`, 4/4 columns and FK match | `dados` | ORM-backed application object | Retain adapter/service. |
| `regional_saude` | table / `dengueadmin` | PK `id`; nullable unique `municipio_geocodigo`; 5,563 / 967 kB | No active repository runtime reader or writer; operational/archive documentation only | none | n/a | unused but retained | No model: safe `id` exists, but no retained application use case. Re-audit if a reader is restored. |
| `macroregional_id_seq` | sequence / `dengueadmin` | owned default for `macroregional.id`; 1 / 8 kB | table default only | n/a | n/a | intentional SQL boundary | Do not model sequences. |
| `regional_id_seq` | sequence / `dengueadmin` | owned default for `regional.id`; 1 / 8 kB | table default only | n/a | n/a | intentional SQL boundary | Do not model sequences. |
| `regional_saude_id_seq` | sequence / `dengueadmin` | owned default for `regional_saude.id`; 1 / 8 kB | table default only | n/a | n/a | intentional SQL boundary | Do not model sequences. |

The first eight rows are the complete table inventory: eight physical tables,
seven modelled tables (six unmanaged adapters and the one managed model,
`ParameterUF`), and one intentionally unmodelled table, `regional_saude`.
All eight have a catalog primary key; `regional_saude` additionally has a
nullable unique constraint, which is not relied on as identity.  No columns
are generated or identity columns.  The remaining three rows are normal serial
sequences, not application-facing objects.

## Model contract reconciliation

| Model | Table | Status | Contract finding |
| --- | --- | --- | --- |
| `dados.models.CID10` | `"Dengue_global"."CID10"` | complete | `codigo` PK and `nome` match PostgreSQL types and nullability. |
| `dados.models.City` | `"Dengue_global"."Municipio"` | partial; corrected #1112 | Uses `geocodigo` PK and deliberately omits `geojson`. Types are compatible. PostgreSQL permits NULL for the four optional regional/macroregional columns; the original audit observed zero NULL rows, and the adapter now declares `null=True`. |
| `dados.models.State` | `"Dengue_global"."estado"` | intentional projection | Correct PK and selected scalar fields; it does not expose state geometry or region label. |
| `dados.models.MacroRegion` | `"Dengue_global"."macroregional"` | intentional projection | Correct PK and selected relationship label; `codigo`/`uf` are omitted. |
| `dados.models.Regional` | `"Dengue_global"."regional"` | complete | PK, columns, and FK to `MacroRegion.id` match. |
| `dados.models.Parameter` | `"Dengue_global"."parameters"` | intentional projection | True composite PK and all report-threshold columns match; `codmodelo` is excluded intentionally. |
| `dados.models.ParameterUF` | `"Dengue_global"."parameters_uf"` | complete | Managed state, composite PK, nullability, and declared state-code index match the live table. |

There are no missing physical objects, incorrect `db_table` case/quoting, or
implicit Django `id` fields among the adapters.  The `City` nullability issue
is the sole physical-contract inconsistency found.  The deliberate projections
are safe because their services select only mapped fields and do not treat an
omitted column as model state.

## Active lookup matrix

| Caller | Object | Access method | Bounds / output | Cache | Decision |
| --- | --- | --- | --- | --- | --- |
| search-box, report views → `RegionalParameters` | `Municipio`, `regional`, `parameters` | ORM service | state/name filters; ordered city/name mappings and one two-key parameter record | regional/city lookup cache | Keep ORM. |
| city page → `get_city_info` | `Municipio` | ORM, explicit `dados` | one geocode; scalar metadata dictionary | lookup cache `city_info:<geocode>`, 24 hours; enclosing page view cached separately for 8 hours | Keep ORM. |
| `/api/*`, report/dashboard helpers → `api.db`, `dbdata` | `Municipio`, `CID10` | SQLAlchemy / Pandas SQL | joins, aggregates, DataFrame/API-shaped output | caller-specific | Keep SQL: joins/aggregations and compatibility output materially define the query. |
| map/geofile flows → `maps.py`, `sync_geofiles` | `Municipio` | SQLAlchemy | GeoJSON/geometry/file work | none | Keep SQL/PostGIS-file boundary. |
| task/report helpers → `dados.tasks`, `dbdata` | `Municipio` | SQLAlchemy | joins and result-set processing | none | Keep SQL boundary. |

`parameters_uf`, `estado`, and `macroregional` have no separate active direct
lookup that warrants migration.  `regional_saude` has no active runtime path.
There is no Ibis, Django `.raw()`, or `.extra()` use for this schema.  The
legacy/archive SQL and migrations are historical/operational evidence, not
runtime readers.

## Ownership, writers, and conclusion

Catalog ownership is shown in the matrix.  Only `parameters_uf` has
repository-managed lifecycle evidence; the other tables are externally owned
read boundaries.  No trigger, rule, function/procedure, dependent view, or
scheduled writer in this repository establishes a writer for those objects.
The catalog FK is
`regional.id_macroregional → macroregional.id`. The three sequences provide
serial defaults for their associated primary keys; they do not establish
the identity of any repository writer.  Public
state-history materialized views are downstream consumers of `estado`, but are
outside this schema and remain their documented SQL/operational boundary.

`READ_ONLY` on the six unmanaged adapters is declarative model metadata.  No
technical `save`/`delete` guard, custom manager, or router write blocker was
found.  Database routing selects the `dados` alias but neither grants nor
prevents writes; the audit does not treat routing as write protection.

Current coverage is sufficient for the planned REST API foundation: every
retained application-facing bounded lookup has an adapter, while complex,
PostGIS, analytical, DataFrame, and compatibility SQL remains deliberately
outside ORM scope.  `regional_saude` deliberately has no adapter because it
has no current application reader.  No new model or migration is justified.

## Corrected nullability

#1112 reconciles `City` with PostgreSQL for `id_regional`, `regional`,
`macroregional_id`, and `macroregional`: all four are physically nullable and
now declare `null=True`. The original audit observed zero NULL rows. This
remains an externally owned, unmanaged, read-only boundary; no physical schema
change, GeoJSON/PostGIS work, or query migration is implied.
