# ORM Inventory for EPIC #1008 Phase 1

Date: 2026-07-21

Scope: `Dengue_global`, `Municipio`, `forecast`, `weather`, `episcanner`

This document is a Phase 1 inventory for ORM planning only. It does not
implement models, migrations, or schema changes.

## Method

- Django connection probe used:
  `poetry run python AlertaDengue/manage.py shell -c "from django.db import connection; connection.ensure_connection(); print(connection.vendor)"`
- Resolved application connection on 2026-07-21:
  PostgreSQL via `AlertaDengue/manage.py shell`, host `localhost`, port
  `25432`, database `dengue`.
- Live catalog inspection succeeded through the Django-configured connection.
- Catalog coverage came from `pg_catalog` and `information_schema` for ordinary
  tables, partitioned tables, foreign tables, views, and materialized views in
  the five target schemas.
- Catalog row counts are PostgreSQL estimates from system catalogs; relation
  sizes are live PostgreSQL relation sizes at inspection time.
- Runtime usage evidence was searched narrowly in current Python application
  code under `AlertaDengue/api`, `AlertaDengue/dados`, and
  `AlertaDengue/ingestion`, excluding migrations and tests from active/runtime
  claims.
- Requested GitHub references could not be inspected live in this workspace:
  `gh auth status` succeeded, but `gh issue view ...` and `gh pr view ...`
  failed with `error connecting to api.github.com`. Those references are kept
  as unresolved context, not treated as absent.

## Summary Counts

| Metric | Count |
| --- | ---: |
| Total catalog objects | 31 |
| Active | 11 |
| Indirectly used | 2 |
| Research-only | 0 |
| Unused | 0 |
| Legacy | 1 |
| Temporary | 1 |
| Backup | 0 |
| Unknown | 16 |
| Existing managed models | 2 |
| Existing unmanaged models | 2 |
| New unmanaged ORM candidates | 6 |
| Pending ORM decisions | 3 |
| Do not map | 18 |

## Live Catalog vs Repository Dump

- Live catalog object counts:
  - `Dengue_global`: 11
  - `Municipio`: 16
  - `forecast`: 0
  - `weather`: 3
  - `episcanner`: 1
- `containers/postgres/schemas/schemas_dengue.sql` matches the live object
  names for the target schemas in this workspace.
- No target-schema objects were found only in the live catalog.
- No target-schema objects were found only in the repository dump.
- The previous pass incorrectly listed `forecast.chunked_upload_chunkedupload`.
  On 2026-07-21 it exists in neither the live catalog nor the current schema
  dump; local evidence for it is only a planning note in
  `docs/plans/remove-upload-app.md`.

## Objects Omitted by the Previous Pass

- `Dengue_global.alerta_regional_chik`
- `Dengue_global.alerta_regional_dengue`
- `Dengue_global.alerta_regional_zika`
- `Dengue_global.estado`
- `Dengue_global.macroregional`
- `Municipio.Bairro`
- `Municipio.Clima_Satelite`
- `Municipio.Clima_cemaden`
- `Municipio.Estacao_cemaden`
- `Municipio.Localidade`
- `Municipio.Ovitrampa`
- `Municipio.Tweet`
- `Municipio.alerta_mrj`
- `Municipio.alerta_mrj_chik`
- `Municipio.alerta_mrj_zika`
- `Municipio.sprint202425`

## Classification Rules Used Here

- `Database owner` records the live relation owner role from PostgreSQL.
- `Django ownership` distinguishes migration ownership only:
  `managed`, `unmanaged`, or `none`.
- `Current query mechanism` records how current code reaches the object now:
  unmanaged model, Django ORM, raw SQL, mixed, indirect dependency, or no
  runtime evidence found.
- `ORM status` is not a statement about current raw SQL usage. Objects can be
  `map-unmanaged` and still be queried today through raw SQL.

## Schema `Dengue_global`

| Object | Type | Usage | Retention | ORM status | Access | Database owner | Django ownership | Current query mechanism | Catalog summary | Evidence and notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `CID10` | table | active | retain | existing-unmanaged | read-only | `administrador` | unmanaged | mixed: unmanaged model and raw SQL | PK `codigo`; approx. rows `8349`; size `933888` bytes | Queried in `api/db.py` joins and backed by `dados.models.CID10`. Retain as current read-only lookup. |
| `Municipio` | table | active | retain | existing-unmanaged | read-only | `administrador` | unmanaged | mixed: unmanaged model and raw SQL | PK `geocodigo`; approx. rows `5570`; size `24002560` bytes | Used by `dados/maps.py`, `dados/dbdata.py`, `dados/tasks.py`, `api/db.py`, and `sync_geofiles.py`. Live table still contains `geojson` and `populacao`, confirming the current unmanaged model is incomplete. |
| `alerta_regional_chik` | table | unknown | pending-decision | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; FK `id_regional -> Dengue_global.regional(id)`; size `8192` bytes | Present live and in dump, but no current Python runtime reference was found in this repository. External ownership and any consumers outside this workspace remain unverified. |
| `alerta_regional_dengue` | table | unknown | pending-decision | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; FK `id_regional -> Dengue_global.regional(id)`; size `8192` bytes | Same decision basis as `alerta_regional_chik`: repository absence alone does not prove retirement or archival. |
| `alerta_regional_zika` | table | unknown | pending-decision | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; FK `id_regional -> Dengue_global.regional(id)`; size `8192` bytes | Same decision basis as the dengue and chikungunya regional alert tables. |
| `estado` | table | indirectly-used | retain | pending-decision | read-only | `administrador` | none | indirect dependency only | PK `geocodigo`; approx. rows `27`; size `11165696` bytes | No direct current repository query to `Dengue_global.estado` was found. Live `pg_catalog` dependencies show `public.hist_uf_dengue_materialized_view`, `public.hist_uf_chik_materialized_view`, and `public.hist_uf_zika_materialized_view` depend on this table; all three are used by current runtime code in `dados/dbdata.py` for state-history queries. |
| `macroregional` | table | indirectly-used | retain | pending-decision | read-only | `dengueadmin` | none | indirect dependency only | PK `id`; approx. rows `118`; size `40960` bytes | Required by live FK `regional.id_macroregional -> macroregional.id`. Added here per task correction. Current code does not query it directly, but retained regional selection logic depends on `regional`, which depends on this table. |
| `parameters` | table | active | retain | map-unmanaged | read-only | `dengueadmin` | none | raw SQL | PK `(municipio_geocodigo, cid10)`; approx. rows `11091`; size `2416640` bytes | Queried by `RegionalParameters` in `dados/dbdata.py` for current report and selection flows. Composite PK is real in the live catalog. No current Django model exists for this table. |
| `parameters_uf` | table | active | retain | existing-managed | read-write-application | `postgres` | managed | Django-managed table plus data migrations | PK `(state_code, cid10)`; approx. rows `52`; size `49152` bytes | Live catalog confirms the composite PK exists today. Current codebase keeps the managed model in `dados.models.ParameterUF`; direct runtime reads are not prominent, but the object is current application-owned state introduced by issues `#897` and `#903`. |
| `regional` | table | active | retain | map-unmanaged | read-only | `dengueadmin` | none | raw SQL | PK `id`; FK `id_macroregional -> Dengue_global.macroregional(id)`; approx. rows `451`; size `131072` bytes | Directly queried by `RegionalParameters.get_regional_names()` and `get_cities()` in `dados/dbdata.py`. No current Django model exists for this table; it remains a Phase 2 unmanaged mapping candidate. |
| `regional_saude` | table | legacy | archive | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; unique `municipio_geocodigo`; approx. rows `5563`; size `1015808` bytes | Current evidence is historical SQL plus 2026-06-12 Redemet archive/remove scripts. No active Python runtime reference was found. |

## Schema `Municipio`

| Object | Type | Usage | Retention | ORM status | Access | Database owner | Django ownership | Current query mechanism | Catalog summary | Evidence and notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Bairro` | table | unknown | pending-decision | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `id`; FK `Localidade_id -> Municipio.Localidade(id)`; approx. rows `184`; size `40960` bytes | Live object omitted by the previous pass. No current Python runtime reference was found in this repository, but that is not enough to classify it as retired. |
| `Clima_Satelite` | table | unknown | pending-decision | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `id`; size `16384` bytes | Live object omitted by the previous pass. External weather workflows or manual processes were not inspected in this run. |
| `Clima_cemaden` | table | unknown | pending-decision | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `id`; approx. rows `36515064`; size `4429135872` bytes | Large live table with no current Python runtime reference in this repository. Ownership by external ETL, research, or manual processes remains unverified. |
| `Estacao_cemaden` | table | unknown | pending-decision | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `codestacao`; approx. rows `645`; size `131072` bytes | Live object omitted by the previous pass. External weather workflows were not inspected in this run. |
| `Historico_alerta` | table | active | retain | map-unmanaged | read-write-external | `administrador` | none | raw SQL | PK `id`; unique `("SE", municipio_geocodigo, "Localidade_id")`; approx. rows `4786759`; size `2484256768` bytes | Directly read by `dados/tasks.py`, `dados/dbdata.py`, and `sync_geofiles.py`. Live dependents include `Municipio.historico_casos` and public materialized views. No current Django model exists for this table. |
| `Historico_alerta_chik` | table | active | retain | map-unmanaged | read-write-external | `administrador` | none | raw SQL | PK `id`; unique `("SE", municipio_geocodigo, "Localidade_id")`; approx. rows `4532807`; size `2495504384` bytes | Read through disease-suffix SQL and written by `backfill_casprov.py`. No current Django model exists for this table. |
| `Historico_alerta_zika` | table | active | retain | map-unmanaged | read-write-external | `postgres` | none | raw SQL | PK `id`; unique `("SE", municipio_geocodigo, "Localidade_id")`; approx. rows `4057247`; size `1328365568` bytes | Read through disease-suffix SQL in current code. No current Django model exists for this table. |
| `Localidade` | table | unknown | pending-decision | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `id`; approx. rows `10`; size `1400832` bytes | Live object omitted by the previous pass. Historical Redemet scripts treat it as a station-code source, but current ownership outside this repository remains unverified. |
| `Notificacao` | table | active | retain | map-unmanaged | read-write-application | `administrador` | none | raw SQL and ingestion UPSERT | PK `id`; unique `(nu_notific, dt_notific, cid10_codigo, municipio_geocodigo)`; approx. rows `37097472`; size `13733748736` bytes | Queried by `api/internal/services.py` and `api/db.py`; written by `ingestion/tasks.py` merge logic. No current Django model exists for this table, so intended ORM work remains separate from current ownership. |
| `Ovitrampa` | table | unknown | pending-decision | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `id`; FK `Localidade_id -> Municipio.Localidade(id)`; approx. rows `0`; size `8192` bytes | Live object omitted by the previous pass. Only template/documentation remnants were found in this repository; external consumers were not inspected. |
| `Tweet` | table | unknown | pending-decision | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `id`; FK `CID10_codigo -> Dengue_global.CID10(codigo)`; approx. rows `3879263`; size `317546496` bytes | The table contains data, but external use was not inspected in this run. It may still have external or historical consumers that must be verified before any archival decision. |
| `alerta_mrj` | table | unknown | pending-decision | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; unique `(aps, se)`; approx. rows `6274`; size `1114112` bytes | Live object omitted by the previous pass. Repository absence alone does not establish retirement. |
| `alerta_mrj_chik` | table | unknown | pending-decision | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; unique `(aps, se)`; approx. rows `6270`; size `1114112` bytes | Live object omitted by the previous pass. Repository absence alone does not establish retirement. |
| `alerta_mrj_zika` | table | unknown | pending-decision | do-not-map | unknown | `postgres` | none | no runtime evidence found | PK `id`; unique `(aps, se)`; size `24576` bytes | Live object omitted by the previous pass. Repository absence alone does not establish retirement. |
| `historico_casos` | materialized view | active | retain | pending-decision | read-only | `dengueadmin` | none | raw SQL | no PK; approx. rows `4796063`; size `358580224` bytes | Queried in `dados/dbdata.py` for recent city history. Per task correction: active, retain, `access: read-only`, ORM decision pending until a stable unique combination is proven. |
| `sprint202425` | table | temporary | pending-decision | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; approx. rows `4187433`; size `655433728` bytes | `temporary` is inferred from the table name and lack of current runtime references. Retention stays `pending-decision` until explicit operational evidence confirms archival or removal. |

## Schema `forecast`

No live objects were found in `forecast`, and no target-schema objects from
`forecast` were present in `containers/postgres/schemas/schemas_dengue.sql`.

## Schema `weather`

| Object | Type | Usage | Retention | ORM status | Access | Database owner | Django ownership | Current query mechanism | Catalog summary | Evidence and notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `copernicus_arg` | table | unknown | pending-decision | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | no PK; approx. rows `4420298`; size `729317376` bytes | Present live and in the dump, but no current Python runtime reference was found. |
| `copernicus_bra` | table | unknown | pending-decision | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | no PK; unique `(date, geocode)`; approx. rows `51006972`; size `10261078016` bytes | Present live and in the dump, but no current Python runtime reference was found. |
| `copernicus_foz_do_iguacu` | table | unknown | pending-decision | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `index`; approx. rows `86496`; size `8462336` bytes | Present live and in the dump, but no current Python runtime reference was found. |

## Schema `episcanner`

| Object | Type | Usage | Retention | ORM status | Access | Database owner | Django ownership | Current query mechanism | Catalog summary | Evidence and notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `sir_params` | table | active | retain | existing-managed | read-write-application | `dengueadmin` | managed | Django ORM | PK `id`; unique `(cid10, geocode, year)`; size `49152` bytes | The current repository treats this table as migration-managed through `EpiscannerSirParams` and migration `0006_episcanner_sir_params`. The live table and unique constraint match that repository definition, and current code uses `EpiscannerSirParams.objects.update_or_create()` in `dados/tasks.py`. |

## Unmanaged ORM Candidates

- Existing unmanaged models:
  - `Dengue_global.CID10`
  - `Dengue_global.Municipio`
- New unmanaged mapping candidates supported by current usage:
  - `Dengue_global.parameters`
  - `Dengue_global.regional`
  - `Municipio.Notificacao`
  - `Municipio.Historico_alerta`
  - `Municipio.Historico_alerta_chik`
  - `Municipio.Historico_alerta_zika`
- Pending unique-key decision before any mapping:
  - `Municipio.historico_casos`

## Phase 1 Conclusion

### Ready for Phase 2

- review existing `CID10`
- review and complete existing `City`
- map `parameters`
- map `regional`
- map `Notificacao`
- map `Historico_alerta`
- map `Historico_alerta_chik`
- map `Historico_alerta_zika`

### Pending decisions

- `historico_casos` stable unique key
- indirect mapping need for `estado` and `macroregional`
- ownership of weather objects
- ownership of tables without current repository usage
- external consumers not covered by this repository

## Corrected Decisions from the Previous Pass

- `Municipio.Notificacao`
  - corrected to `usage: active`, `retention: retain`,
    `orm_status: map-unmanaged`
- `Municipio.Historico_alerta`
  - corrected to `usage: active`, `retention: retain`,
    `orm_status: map-unmanaged`
- `Municipio.Historico_alerta_chik`
  - corrected to `usage: active`, `retention: retain`,
    `orm_status: map-unmanaged`
- `Municipio.Historico_alerta_zika`
  - corrected to `usage: active`, `retention: retain`,
    `orm_status: map-unmanaged`
- `Municipio.historico_casos`
  - corrected to `usage: active`, `retention: retain`,
    `orm_status: pending-decision`, `access: read-only`
- `Dengue_global.macroregional`
  - added; retained as an indirectly required dependency of `regional`
- `Dengue_global.estado`
  - added; retained as an indirectly used dependency through live state summary
    materialized views
- `episcanner.sir_params`
  - corrected from uncertain ownership to live-confirmed
    `existing-managed`
- `forecast.chunked_upload_chunkedupload`
  - removed from the inventory because it is not present in the live catalog or
    current schema dump

## Unresolved Decisions

- `Dengue_global.estado`
  - no direct current repository query was found; current evidence is indirect
    dependency only
- `Dengue_global.macroregional`
  - required by retained `regional`, but not directly queried by current code
- `Municipio.historico_casos`
  - active and retained, but a stable unique mapping key still needs proof
- `Dengue_global.alerta_regional_*`
  - current runtime ownership and whether they can be archived remains open
- `Municipio.alerta_mrj*`
  - current runtime ownership remains open
- `Municipio.Tweet`
  - table contains data, but external or historical consumers were not
    verified in this run
- `Municipio.Bairro`, `Municipio.Clima_Satelite`,
  `Municipio.Clima_cemaden`, `Municipio.Estacao_cemaden`,
  `Municipio.Localidade`, `Municipio.Ovitrampa`
  - present live with no current Python runtime evidence
- `weather.copernicus_arg`, `weather.copernicus_bra`,
  `weather.copernicus_foz_do_iguacu`
  - present live with no current Python runtime evidence
- Requested GitHub issue and PR context:
  `#1008`, `#817`, `#872`, `#922`, `PR #674`, `PR #739`, `PR #994`
  - `gh` is authenticated, but live API access was unavailable in this
    workspace on 2026-07-21
