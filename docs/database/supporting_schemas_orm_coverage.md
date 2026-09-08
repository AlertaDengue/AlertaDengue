# Supporting schemas ORM coverage

Audit date: 2026-09-08

## Scope and evidence

This audit covers `episcanner`, `vegetation_indices`, and `weather`. It
excludes DDL, migrations, data writes, model changes, and speculative adapters. Searches covered Django runtime code, tasks, services,
SQL helpers, SQL history, scripts, tests, documentation, settings, and the database router.

Catalog-confirmed facts below were obtained through the repository's read-only
database verification path. No exact `COUNT(*)` was run for large weather
tables; approximate row counts use PostgreSQL catalog estimates and relation
sizes use `pg_total_relation_size`. Repository-search findings and unresolved
operational ownership are identified separately.

## Catalog-confirmed facts

## Relation inventory

| Schema | Relation | Kind | Rows / size | Identity | Django model |
| --- | --- | --- | --- | --- | --- |
| `episcanner` | `sir_params` | table | 32,770 / 6,905,856 bytes | `id` PK; unique `(cid10, geocode, year)` | `dados.models.EpiscannerSirParams` |
| `episcanner` | `sir_params_id_seq` | sequence | 8,192 bytes | sequence for `sir_params.id` | none |
| `vegetation_indices` | `vegetation_index_metrics` | table | 3,297,440 / 535,633,920 bytes | PK `(date, geocode, collection, attribute)` | none |
| `weather` | `copernicus_bra` | table | 54,191,956 / 10,249,068,544 bytes | unique `(date, geocode)`; no PK | none |
| `weather` | `copernicus_bra_precip_tot_fixed` | table | 54,451,104 / 7,638,327,296 bytes | unique `(date, geocode)`; no PK | none |

The verified catalog inventory contains 4 ordinary tables, 1 sequence, and 9
indexes across the three schemas; no partitioned table, view, materialized
view, or foreign table was found. All verified relations are owned by the
catalog owner, have no table comments, no user-defined triggers, and no
dependent views, materialized views, or functions. Weather relations remain
part of the operational weather lifecycle; this reference does not prescribe
archival or retention changes.

Live columns: `sir_params` has `id integer NOT NULL` (identity `d`), `cid10
varchar(10) NOT NULL`, `year integer NOT NULL`, `ep_ini varchar(20) NULL`,
`ep_pw varchar(20) NOT NULL`, `ep_end varchar(20) NULL`, `ep_dur integer NULL`,
`peak_week`, `beta`, `gamma`, `r0`, `total_cases`, `alpha`, and `sum_res` all
`double precision NOT NULL`, `t_ini integer NULL`, `t_end integer NULL`, and
`geocode integer NOT NULL`. `vegetation_index_metrics` has `date date NOT
NULL`, `geocode integer NOT NULL`, `collection varchar(255) NOT NULL`,
`attribute varchar(50) NOT NULL`, and nullable `double precision` columns
`mean`, `std`, `median`, `q25`, `q75`, `min`, and `max`.

`copernicus_bra` has `date timestamp without time zone NOT NULL`, `geocode
integer NOT NULL`, `temp_max`, `precip_max`, `umid_max`, `pressao_max`, `temp_med`,
`precip_med`, `umid_med`, `pressao_med`, `temp_min`, `precip_min`, `umid_min`,
`pressao_min`, and `precip_tot` as `double precision NOT NULL`, plus `epiweek
integer NOT NULL`. The additional table has `date date NOT NULL`, `geocode text
NOT NULL`, and nullable `double precision` columns `precip_tot`, `precip_min`,
`precip_med`, and `precip_max`.

Catalog-confirmed index names are `sir_params_geocode_e198a8ac`,
`sir_params_pkey`, `uq_sir_params_cid10_geocode_year`,
`vegetation_index_metrics_pkey`, `copernicus_bra_unique_date_geocode`,
`copernicus_bra_precip_tot_fixed_date_geocode_key`,
`idx_copernicus_bra_precip_tot_fixed_date`,
`idx_copernicus_bra_precip_tot_fixed_date_geocode`, and
`idx_copernicus_bra_precip_tot_fixed_geocode`. EpiScanner also has the catalog-confirmed foreign key to `Dengue_global.Municipio(geocodigo)`.

## Repository-search findings

## Model coverage and routing

`EpiscannerSirParams` maps to `"episcanner"."sir_params"`, is managed, uses
the physical `id` primary key, and declares `(cid10, geocode, year)` unique.
`dados.tasks._save_sir_params` writes with `update_or_create()`. The router
maps both reads and writes for app `dados` to alias `dados`. `managed=True`
controls Django lifecycle management; routing is not write prevention.

There are no adapters for the vegetation or weather relations. No arbitrary
primary key, implicit `id`, or synthetic composite identity is proposed.

## Readers, writers, and ownership

The active EpiScanner flow is `episcanner_all_states` →
`episcanner_scan_state` → `_fetch_alert_data` (SQLAlchemy/DataFrame read from
historical alert tables) → EpiScanner calculation → `_save_sir_params` (ORM
write). The source read is a state/year window but has an analytical
DataFrame contract; persistence is already ORM-backed.

No vegetation reader or writer was found in this checkout. That means no
repository writer was found, not that no external writer exists. Ownership is
unresolved between analytics, ingestion, and external operation.

Weather relations contain external geographic/time-series data. Repository
evidence includes an R helper with a weather time-series read, while no active
Django runtime reader or writer was found. Consumers may be analytical,
ingestion, operational, or archival workflows; external writer, retention,
date-range, and column contracts need owner confirmation.

| Schema | Read path | Write path | Classification |
| --- | --- | --- | --- |
| `episcanner` | ORM result access; analytical SQL input remains SQL/DataFrame | `_save_sir_params` ORM upsert | already ORM-backed / analytical boundary |
| `vegetation_indices` | none found in repository | none found in repository | unresolved external/analytics/ingestion |
| `weather` | external/R time-series reads | none found in repository | retained SQL/external boundary |

## Operational boundary assumptions

The catalog snapshot describes physical relations at verification time.
External analytical, ingestion, operational, and archival owners may maintain
relations or consumers outside this repository.

## ORM decision

No safe bounded ORM candidate was confirmed. Weather paths are large
time-series/DataFrame reads and lack confirmed Django identity. Vegetation
usage and identity are unresolved. EpiScanner persistence already uses ORM.
Retain SQL for time-series, analytics, DataFrame shaping, external consumers,
ingestion, bulk operations, and database-specific or spatial behavior.

No separate implementation issue should be created for a speculative model. No
additional ORM refactor is currently justified.

## Follow-up questions

1. Preserve this catalog snapshot as verification evidence; repeat the
   read-only probe only when the physical database changes.
2. Confirm owner/writer/lifecycle for vegetation and all weather relations.
3. Reassess only if an enforced-identity, active bounded metadata lookup is
   found; large weather and analytical paths remain SQL.
