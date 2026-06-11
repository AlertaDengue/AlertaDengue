# REDEMET Dependency Analysis and Secure Removal Plan

## Context

- Issue: [#884 - Remove REDMET ref in the platform](https://github.com/AlertaDengue/AlertaDengue/issues/884)
- Analysis date: 2026-06-10
- Analyzed revision: `2b992c44` (`remove-redemet`, based on `upstream/main`)
- Issue goals:
  - remove website code and references related to meteorological stations;
  - verify that the old station-data update task is inactive;
  - remove station references from production tables;
  - preserve the old data separately if it may be useful later.

The issue title says `REDMET`, while the README names `REDEMET`. Most code and
database objects use the older Weather Underground (`wu`) naming instead of
explicitly naming REDEMET. Before production removal, the team must confirm
whether `Clima_wu`, `Estacao_wu`, and the station-code columns are the complete
set of data that the issue intends to retire.

## Varclimate Preservation Contract

No R source or R dependency exists in this repository, and issue #884 does not
link an R script. Treat the current loader as an external integration until its
owner and source are confirmed.

This removal must preserve:

- `varcli`, `clicrit`, `varcli2`, and `clicrit2` in
  `"Dengue_global"."parameters"`;
- climate columns in `"Municipio"."Historico_alerta*"`;
- current varclimate validation, chart rendering, disease thresholds, and
  dengue fallback behavior.

Before production cleanup, confirm that the external loader does not read or
write any proposed-for-removal station object or column.

## Executive Summary

REDEMET/station removal must be split into application and database phases.
There is no REDEMET client library, API call, credential, or updater task in
this repository. However, the application still selects
`codigo_estacao_wu` from the active `"Dengue_global"."parameters"` table as
part of city-report parameter loading.

The station identifier itself is not used to load climate data in the current
city-report path. City reports read climate values from
`"Municipio"."Historico_alerta*"` columns. The active `varcli`, `clicrit`,
`varcli2`, and `clicrit2` parameter columns choose climate variables and their
thresholds for report tables and charts. Those columns must not be removed
merely because they are stored beside `codigo_estacao_wu`.

The secure sequence is:

1. confirm production writers and external readers;
2. remove station references from the application and website;
3. archive the legacy station tables and columns with validation;
4. observe production after application deployment;
5. drop only confirmed-unused station objects;
6. retain active Copernicus-derived climate fields and thresholds.

## Dependency Findings

### 1. Direct REDEMET and airport-station website references

| Location | Finding | Action |
| --- | --- | --- |
| `README.md:43` | States that weather and climate data come from REDEMET airport stations. This is inconsistent with the current Copernicus/Mosqlimate description. | Replace with the current source or remove the bullet. |
| `AlertaDengue/dados/templates/about.html:193-195` | Public website preserves a historical link to airport meteorological stations. | Remove the historical station sentence/link per issue scope. |
| `AlertaDengue/locale/en/LC_MESSAGES/django.po:423-424` | Active translation entry for airport weather stations. | Regenerate message catalogs after template removal. |
| `AlertaDengue/locale/es/LC_MESSAGES/django.po:424` | Active translation entry for airport weather stations. | Regenerate message catalogs after template removal. |
| `AlertaDengue/locale/pt_BR/LC_MESSAGES/django.po:353` and `AlertaDengue/locale/pt/LC_MESSAGES/django.po:415` | Obsolete translation entries contain the old `estacoes.dengue.mat.br` link. | Remove obsolete entries when catalogs are regenerated/cleaned. |

The current About page already identifies Mosqlimate and Copernicus ERA5 as
the current source. Removing the historical airport-station sentence will not
remove the current attribution.

### 2. Runtime application dependency

| Location | Finding | Impact |
| --- | --- | --- |
| `AlertaDengue/dados/dbdata.py:210-242` | `RegionalParameters.get_var_climate_info()` selects `(codigo_estacao_wu, varcli)`. | No non-test caller was found. It can likely be deleted after confirming external imports are not supported. |
| `AlertaDengue/dados/dbdata.py:316-346` | `RegionalParameters.get_station_data()` selects station code, climate-variable thresholds, and epidemiological thresholds from `"Dengue_global"."parameters"`. | Active runtime dependency because `ReportCityView` calls it. |
| `AlertaDengue/dados/views.py:855-937` | City report code consumes a positional tuple returned by `get_station_data()`. It does not use index `2` (`codigo_estacao_wu`), but climate fields at indexes `3-6` and epidemiological thresholds at indexes `7-9` are active. | Removing the database column before changing this query will break reports. Removing all adjacent climate columns will regress report charts. |
| `AlertaDengue/dados/views.py:994-1094` | City reports render climate charts and tables using selected climate variables and thresholds. | Preserve this behavior during station removal. |
| `AlertaDengue/dados/charts/cities.py:220-345` | Climate chart rendering requires `varcli`/`clicrit` pairs. | These are active Copernicus-era report configuration, not station dependencies. |
| `AlertaDengue/dados/dbdata.py:957-1016` | City reports read climate values from `Historico_alerta`, `Historico_alerta_chik`, and `Historico_alerta_zika`, not from `Clima_wu`. | Strong evidence that `Clima_wu` is not in the current web report read path. |

Recommended application refactor:

- Rename `get_station_data()` to a source-neutral name such as
  `get_report_parameters()`.
- Return a named structure or mapping rather than a positional tuple.
- Remove `codigo_estacao_wu` from its query and result.
- Keep `varcli`, `clicrit`, `varcli2`, `clicrit2`, `limiar_preseason`,
  `limiar_posseason`, and `limiar_epidemico`.
- Delete `get_var_climate_info()` if a final caller audit confirms it is dead.

### 3. Database objects represented in the repository

The bootstrap schema dump at `containers/postgres/schemas/schemas_dengue.sql`
contains these confirmed station-related objects:

| Object | Station-related content | Proposed disposition |
| --- | --- | --- |
| `"Municipio"."Clima_wu"` | Daily legacy climate series keyed by `Estacao_wu_estacao_id`. | Archive, validate, then drop from active schema. |
| `"Municipio"."Clima_wu_id_seq"` | Sequence owned by `Clima_wu.id`. | Drop with the active table after archival validation. |
| `"Municipio"."WU_idx_data"` | Index on `Clima_wu.data_dia`. | Drop with the active table. |
| `"Municipio"."Estacao_wu"` | Legacy station metadata. | Archive, validate, then drop from active schema. |
| `"Dengue_global"."parameters".codigo_estacao_wu` | Station code in an active report-parameter table. | Archive column values, then drop only after application query is deployed without it. |
| `"Dengue_global"."parameters".estacao_wu_sec` | Secondary station reference in the active parameter table. | Archive and drop after confirming no external reader. |
| `"Dengue_global"."regional_saude".codigo_estacao_wu` | Station code in an apparently legacy table. | Confirm production status; archive/drop with the table or column. |
| `"Dengue_global"."regional_saude".estacao_wu_sec` | Secondary station reference in an apparently legacy table. | Confirm production status; archive/drop with the table or column. |
| `"Municipio"."Localidade".codigo_estacao_wu` | Station code attached to a locality. | Confirm external use; archive and drop if unused. |

Important cautions:

- `"Dengue_global"."parameters"` is actively queried by the application.
- The checked-in schema dump shows a primary key on only
  `municipio_geocodigo`, while current tests describe a composite
  `(municipio_geocodigo, cid10)` key. Production schema must be inspected
  directly; the dump is not authoritative.
- These legacy tables are unmanaged by current Django models/migrations.
  Production removal needs an explicit DBA migration/runbook, followed by an
  update to the bootstrap schema.
- ACLs/grants for archived objects must be intentionally restricted. Do not
  automatically reproduce broad write grants on the archive.

### 4. Objects that must remain

Do not remove the following as part of station cleanup:

- `varcli`, `clicrit`, `varcli2`, and `clicrit2` from
  `"Dengue_global"."parameters"` until the report-threshold design is
  intentionally replaced;
- climate columns in `"Municipio"."Historico_alerta*"`;
- `weather.copernicus_bra` and its sequence/indexes;
- Copernicus/Mosqlimate attribution on the About page;
- generic meteorological raster/mapserver features without separate evidence
  that they depend on REDEMET stations;
- CEMADEN tables, which represent a different source.

### 5. Tests and historical artifacts

| Location | Finding | Action |
| --- | --- | --- |
| `AlertaDengue/tests/dados/dbdata/conftest.py:117-121,161` | Current parameter fixture includes `codigo_estacao_wu`. | Remove station fixture data when the runtime query is refactored. |
| `AlertaDengue/tests/dados/dbdata/test_regional_parameters.py` | Tests assert station identifiers and the positional station-data result shape. | Replace with tests for source-neutral report parameters and retained thresholds. |
| `AlertaDengue/tests/dados/test_views.py` | Tests duplicate positional climate-parameter extraction logic. | Update indexes or, preferably, test the named parameter structure. |
| `AlertaDengue/dados/tests/legacy.py` and `AlertaDengue/dados/tests/test_dbdata.py:14` | Legacy test helper directly reads `Clima_wu` by station ID. | Remove if this legacy suite is no longer supported, or move to archived-data tooling. |
| `notebooks/Ibis-ReportState-*.ipynb`, `notebooks/DB_DEMO.ipynb`, and `notebooks/Essay.ipynb` | Historical notebooks reference `Clima_wu`, `Estacao_wu`, and station IDs. | Mark as historical or update/remove them; do not treat notebooks as production consumers without execution evidence. |
| `containers/postgres/sql_history/167-*regional_saude.sql` | Historical SQL manages old climate/station configuration. | Retain as immutable history unless repository policy requires removal; document it as non-runtime. |

### 6. Updater and scheduler finding

No REDEMET/WU-specific updater was found in:

- Django/Celery task modules;
- checked-in management commands;
- checked-in host cron configuration;
- Compose service commands;
- GitHub Actions workflows;
- Python package dependencies.

The repository's checked-in cron job only runs `manage.py send_mail`. Its
Celery tasks concern uploads and SINAN ingestion. This does **not** prove that
the old weather updater is inactive in production. It may be configured in
`django_celery_beat`, host cron, systemd, `pg_cron`, another repository,
Airflow, or other infrastructure.

## Production Audit Before Removal

Record command/query outputs in the deployment ticket. Run all checks against
production and any independent analytics/ETL environments.

### Writers and recent data

```sql
SELECT min(data_dia), max(data_dia), count(*)
FROM "Municipio"."Clima_wu";

SELECT count(*) FROM "Municipio"."Estacao_wu";

SELECT count(*) FILTER (WHERE codigo_estacao_wu IS NOT NULL) AS station_codes,
       count(*) FILTER (WHERE estacao_wu_sec IS NOT NULL) AS secondary_codes
FROM "Dengue_global"."parameters";

SELECT count(*) FILTER (WHERE codigo_estacao_wu IS NOT NULL) AS station_codes
FROM "Municipio"."Localidade";
```

Check database activity/audit logs for `INSERT`, `UPDATE`, `COPY`, and `DELETE`
against the candidate objects. A stale `max(data_dia)` is evidence, but not
proof, that no writer remains.

### Database dependencies and consumers

```sql
SELECT dependent_ns.nspname AS dependent_schema,
       dependent.relname AS dependent_object,
       dependent.relkind
FROM pg_depend d
JOIN pg_class referenced ON referenced.oid = d.refobjid
JOIN pg_class dependent ON dependent.oid = d.objid
JOIN pg_namespace dependent_ns ON dependent_ns.oid = dependent.relnamespace
WHERE referenced.oid IN (
  '"Municipio"."Clima_wu"'::regclass,
  '"Municipio"."Estacao_wu"'::regclass
);

SELECT schemaname, viewname, definition
FROM pg_views
WHERE definition ILIKE ANY (
  ARRAY['%Clima_wu%', '%Estacao_wu%', '%codigo_estacao_wu%', '%estacao_wu_sec%']
);
```

Also inspect materialized views, functions/procedures, triggers, foreign keys,
BI dashboards, notebooks run outside this repository, and read-only users.

### Schedulers and external writers

- Query `django_celery_beat_periodictask` for names, task paths, args, and
  enabled entries containing `weather`, `climate`, `station`, `wu`, `redemet`,
  or related terms.
- Inspect Celery worker/beat logs for the same terms.
- Inspect every application/ETL host's user and system crontabs.
- Inspect systemd timers and services.
- Inspect `cron.job` if `pg_cron` is installed.
- Inspect external orchestration and repositories, especially the pipeline
  that currently loads Copernicus/Mosqlimate-derived data.
- Disable any confirmed legacy writer and observe at least one expected update
  interval before database removal.

## Secure Removal Plan

## Registered Tasks

Deliver each important change as a focused semantic commit:

1. `docs(redemet): register removal plan`
2. `refactor(reports): remove legacy station dependency`
3. `docs(redemet): remove legacy station references`
4. `test(redemet): remove legacy station helpers`
5. `chore(database): add secure REDEMET cleanup`
6. `chore(redemet): verify dependency removal`

### Phase 0: Confirm scope and ownership

- [ ] Confirm that all `wu` objects and station-code columns represent the
  REDEMET/airport-station dependency intended by issue #884.
- [ ] Obtain and inspect the external varclimate loader and record its owner,
  source repository, schedule, and database contract.
- [ ] Identify the owner of the current Copernicus/Mosqlimate ingestion
  pipeline and document where it writes data used by `Historico_alerta*`.
- [ ] Inventory production row counts, date ranges, storage sizes, grants,
  dependencies, readers, and writers.
- [ ] Decide the archive retention period, owner, access policy, and deletion
  date.
- [ ] Take and verify a normal production backup before schema changes.

Exit criterion: every candidate object is classified as `retain`, `archive
then remove`, or `unknown`; no `unknown` object proceeds to removal.

### Phase 1: Remove application and website coupling

- [ ] Replace the README REDEMET statement with the current data-source
  description.
- [ ] Remove the public historical airport-station sentence/link from the
  About page.
- [ ] Regenerate and review translation catalogs.
- [ ] Replace `get_station_data()` with a source-neutral report-parameter
  method that does not select `codigo_estacao_wu`.
- [ ] Replace positional tuple handling with a named structure/mapping.
- [ ] Remove dead `get_var_climate_info()` after confirming no supported
  external caller.
- [ ] Keep climate-variable and threshold behavior unchanged.
- [ ] Update focused unit/integration tests.

Exit criterion: repository search finds no active application/UI station
reference, and city reports render incidence and climate charts correctly
without selecting a station column.

### Phase 2: Create a restricted archive

Use a dedicated schema rather than leaving misleading active tables in
`Municipio`. Use a dated, immutable migration reviewed by a DBA. Example
shape, to be adapted after inspecting the real production schema:

```sql
BEGIN;

CREATE SCHEMA IF NOT EXISTS archive_redemet;
REVOKE ALL ON SCHEMA archive_redemet FROM PUBLIC;

CREATE TABLE archive_redemet.clima_wu_20260610
  (LIKE "Municipio"."Clima_wu" INCLUDING ALL);
INSERT INTO archive_redemet.clima_wu_20260610
SELECT * FROM "Municipio"."Clima_wu";

CREATE TABLE archive_redemet.estacao_wu_20260610
  (LIKE "Municipio"."Estacao_wu" INCLUDING ALL);
INSERT INTO archive_redemet.estacao_wu_20260610
SELECT * FROM "Municipio"."Estacao_wu";

CREATE TABLE archive_redemet.parameters_station_codes_20260610 AS
SELECT municipio_geocodigo, cid10, codigo_estacao_wu, estacao_wu_sec
FROM "Dengue_global"."parameters"
WHERE codigo_estacao_wu IS NOT NULL OR estacao_wu_sec IS NOT NULL;

CREATE TABLE archive_redemet.localidade_station_codes_20260610 AS
SELECT id, "Municipio_geocodigo", codigo_estacao_wu
FROM "Municipio"."Localidade"
WHERE codigo_estacao_wu IS NOT NULL;

COMMIT;
```

Archive validation must include:

- [ ] source and archive row counts match;
- [ ] source and archive date ranges match;
- [ ] deterministic aggregate hashes/checksums match where practical;
- [ ] archive restore/read test succeeds using a restricted archive-reader
  role;
- [ ] archive tables are read-only to normal application roles;
- [ ] archive manifest records source object, schema, row count, checksum,
  creation time, owner, retention, and issue/deployment reference.

Do not drop source objects in the same transaction/runbook step that first
creates the archive. Allow independent validation and rollback review.

### Phase 3: Deploy application decoupling and observe

- [ ] Deploy Phase 1 before dropping columns/tables.
- [ ] Monitor report endpoints, errors, slow queries, and climate-chart
  rendering.
- [ ] Confirm database query logs show no application reads from station
  objects/columns.
- [ ] Confirm no legacy writer runs during the agreed observation window.
- [ ] Re-run dependency and scheduler audits immediately before removal.

Exit criterion: no confirmed reader or writer remains, and the application
operates without station fields.

### Phase 4: Remove active database objects

Apply narrow, reviewed DDL. The exact DDL depends on production inspection,
but the intended set is:

- [ ] drop `codigo_estacao_wu` and `estacao_wu_sec` from
  `"Dengue_global"."parameters"`;
- [ ] drop confirmed-unused station columns from
  `"Dengue_global"."regional_saude"` and `"Municipio"."Localidade"`;
- [ ] drop `"Municipio"."Clima_wu"` and its owned sequence/index;
- [ ] drop `"Municipio"."Estacao_wu"`;
- [ ] remove obsolete grants/ACL declarations;
- [ ] update `containers/postgres/schemas/schemas_dengue.sql` so new
  environments do not recreate retired objects.

Operational safeguards:

- use short `lock_timeout` and `statement_timeout` values;
- measure table size and expected lock behavior first;
- schedule DDL during a low-traffic window;
- stop on lock timeout rather than blocking production;
- keep the archive and full backup through the retention window;
- document rollback as restoring columns/tables from the archive, not as an
  untested reverse migration.

### Phase 5: Remove historical code artifacts

- [ ] Remove or isolate `AlertaDengue/dados/tests/legacy.py` station queries.
- [ ] Remove station-only constants and fixture data.
- [ ] Decide whether station notebooks are historical records or supported
  examples; mark or update them accordingly.
- [ ] Keep immutable SQL history if required by repository policy, but clearly
  document that it is non-runtime.
- [ ] Run a final repository search for direct and indirect station terms.

## Verification Checklist

### Repository

```bash
rg -n -i --hidden --glob '!.git/**' --glob '!node_modules/**' \
  'redemet|redmet|aer\.mil|estacoes\.dengue\.mat\.br|airport weather stations'

rg -n --hidden --glob '!.git/**' --glob '!node_modules/**' \
  'Clima_wu|Estacao_wu|codigo_estacao_wu|estacao_wu_sec'
```

Remaining matches must be intentionally documented historical artifacts or
the restricted archive/runbook.

### Application behavior

- city report loads for dengue, chikungunya, and zika;
- incidence thresholds remain disease-specific;
- climate chart displays the configured climate variables and thresholds;
- report HTML includes the expected climate columns;
- About page attributes current data sources and contains no airport-station
  reference;
- no SQL error references removed station columns/tables.

### Database

- active schemas contain no approved-for-removal station object/column;
- archive counts/checksums and restore test remain valid;
- no scheduler or writer attempts to update removed objects;
- new development/test database creation does not recreate retired objects.

## Recommended Test Scope

- `AlertaDengue/tests/dados/dbdata/test_regional_parameters.py`
- `AlertaDengue/tests/dados/dbdata/test_report_city.py`
- `AlertaDengue/tests/dados/test_views.py`
- city report view integration tests for all supported diseases;
- template/i18n checks after message regeneration;
- database bootstrap test using the updated
  `containers/postgres/schemas/schemas_dengue.sql`;
- staging smoke test with a production-like schema after archive/drop DDL.

## Definition of Done

- No active website or README reference claims that REDEMET/airport stations
  are a current or historical platform dependency.
- The application does not select or expose station identifiers.
- Current climate charts and thresholds continue to work from the existing
  Copernicus-era data path.
- Production audits prove that no station updater or external reader remains.
- Legacy station data is preserved in a validated, restricted, documented
  archive.
- Approved station tables, sequences, indexes, ACLs, and columns are removed
  from active production schemas and bootstrap schemas.
- Tests, staging smoke checks, monitoring, and rollback/restore procedures are
  complete.
