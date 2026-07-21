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

### Usage totals

| Metric | Count |
| --- | ---: |
| Total catalog objects | 31 |
| Active | 10 |
| Indirectly used | 2 |
| External access | 2 |
| Research-only | 0 |
| Unused | 0 |
| Legacy | 16 |
| Temporary | 1 |
| Backup | 0 |
| Unknown | 0 |

### Retention totals

| Metric | Count |
| --- | ---: |
| Total catalog objects | 31 |
| Retain | 13 |
| Archive | 17 |
| Pending retention decisions | 1 |

### ORM totals

| Metric | Count |
| --- | ---: |
| Total catalog objects | 31 |
| Existing managed models | 2 |
| Existing unmanaged models | 2 |
| New unmanaged ORM candidates | 9 |
| Pending ORM decisions | 0 |
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
- `map-unmanaged` records intended future unmanaged ORM mapping only. It does
  not imply a current Django model already exists.
- `do-not-map` records an ORM decision only. It does not imply that the object
  has already been deleted or physically archived.
- `archive` records an approved future lifecycle action only. No table or
  materialized view is modified by this document.
- `usage`, `retention`, and `ORM status` are independent classifications.
- Valid `usage` classifications in this inventory are `active`,
  `indirectly-used`, `external-access`, `research-only`, `unused`, `legacy`,
  `temporary`, `backup`, and `unknown`.
- Current code references are documented even when maintainers have approved an
  object for legacy/archive handling.

## Schema `Dengue_global`

| Object | Type | Usage | Retention | ORM status | Access | Database owner | Django ownership | Current query mechanism | Catalog summary | Evidence and notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `CID10` | table | active | retain | existing-unmanaged | read-only | `administrador` | unmanaged | mixed: unmanaged model and raw SQL | PK `codigo`; approx. rows `8349`; size `933888` bytes | Queried in `api/db.py` joins and backed by `dados.models.CID10`. Retain as current read-only lookup. |
| `Municipio` | table | active | retain | existing-unmanaged | read-only | `administrador` | unmanaged | mixed: unmanaged model and raw SQL | PK `geocodigo`; approx. rows `5570`; size `24002560` bytes | Used by `dados/maps.py`, `dados/dbdata.py`, `dados/tasks.py`, `api/db.py`, and `sync_geofiles.py`. Live table still contains `geojson` and `populacao`, confirming the current unmanaged model is incomplete. |
| `alerta_regional_chik` | table | legacy | archive | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; FK `id_regional -> Dengue_global.regional(id)`; size `8192` bytes | Maintainers approved archival and no ORM mapping. This table belongs to a retired reporting workflow. This PR records lifecycle and ORM decisions only. |
| `alerta_regional_dengue` | table | legacy | archive | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; FK `id_regional -> Dengue_global.regional(id)`; size `8192` bytes | Maintainers approved archival and no ORM mapping. This table belongs to a retired reporting workflow. This PR records lifecycle and ORM decisions only. |
| `alerta_regional_zika` | table | legacy | archive | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; FK `id_regional -> Dengue_global.regional(id)`; size `8192` bytes | Maintainers approved archival and no ORM mapping. This table belongs to a retired reporting workflow. This PR records lifecycle and ORM decisions only. |
| `estado` | table | indirectly-used | retain | map-unmanaged | read-only | `administrador` | none | indirect dependency only | PK `geocodigo`; approx. rows `27`; size `11165696` bytes | No direct current repository query to `Dengue_global.estado` was found. Live `pg_catalog` dependencies show `public.hist_uf_dengue_materialized_view`, `public.hist_uf_chik_materialized_view`, and `public.hist_uf_zika_materialized_view` depend on this table; all three are used by current runtime code in `dados/dbdata.py` for state-history queries. Suggested model: `State` with natural primary key `geocodigo`. |
| `macroregional` | table | indirectly-used | retain | map-unmanaged | read-only | `dengueadmin` | none | indirect dependency only | PK `id`; approx. rows `118`; size `40960` bytes | `Dengue_global.regional.id_macroregional` has a live FK to `Dengue_global.macroregional.id`. `regional` is retained and is a confirmed ORM candidate, so `macroregional` must also be retained and mapped. The ORM relationship must reflect the real database FK. Suggested model: `Macroregion` with primary key `id`. |
| `parameters` | table | active | retain | map-unmanaged | read-only | `dengueadmin` | none | raw SQL | PK `(municipio_geocodigo, cid10)`; approx. rows `11091`; size `2416640` bytes | Queried by `RegionalParameters` in `dados/dbdata.py` for current report and selection flows. Composite PK is real in the live catalog. No current Django model exists for this table. |
| `parameters_uf` | table | active | retain | existing-managed | read-write-application | `postgres` | managed | Django-managed table plus data migrations | PK `(state_code, cid10)`; approx. rows `52`; size `49152` bytes | Live catalog confirms the composite PK exists today. Current codebase keeps the managed model in `dados.models.ParameterUF`; direct runtime reads are not prominent, but the object is current application-owned state introduced by issues `#897` and `#903`. |
| `regional` | table | active | retain | map-unmanaged | read-only | `dengueadmin` | none | raw SQL | PK `id`; FK `id_macroregional -> Dengue_global.macroregional(id)`; approx. rows `451`; size `131072` bytes | Directly queried by `RegionalParameters.get_regional_names()` and `get_cities()` in `dados/dbdata.py`. No current Django model exists for this table; it remains a Phase 2 unmanaged mapping candidate. |
| `regional_saude` | table | legacy | archive | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; unique `municipio_geocodigo`; approx. rows `5563`; size `1015808` bytes | This table belonged to the legacy Redemet workflow. It remains approved for archival and no ORM mapping. This PR records lifecycle and ORM decisions only. |

## Schema `Municipio`

| Object | Type | Usage | Retention | ORM status | Access | Database owner | Django ownership | Current query mechanism | Catalog summary | Evidence and notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Bairro` | table | legacy | archive | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `id`; FK `Localidade_id -> Municipio.Localidade(id)`; approx. rows `184`; size `40960` bytes | `Bairro` belonged to the legacy satellite/Cemaden climate workflow. Maintainers approved archival and no ORM mapping. This PR records lifecycle and ORM decisions only. |
| `Clima_Satelite` | table | legacy | archive | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `id`; size `16384` bytes | This table belongs to a retired climate ingestion path. Maintainers approved archival and no ORM mapping. This PR records lifecycle and ORM decisions only. |
| `Clima_cemaden` | table | legacy | archive | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `id`; approx. rows `36515064`; size `4429135872` bytes | This table belongs to a retired climate ingestion path. Maintainers approved archival and no ORM mapping. This PR records lifecycle and ORM decisions only. |
| `Estacao_cemaden` | table | legacy | archive | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `codestacao`; approx. rows `645`; size `131072` bytes | This table belongs to a retired climate ingestion path. Maintainers approved archival and no ORM mapping. This PR records lifecycle and ORM decisions only. |
| `Historico_alerta` | table | active | retain | map-unmanaged | read-write-external | `administrador` | none | raw SQL | PK `id`; unique `("SE", municipio_geocodigo, "Localidade_id")`; approx. rows `4786759`; size `2484256768` bytes | Directly read by `dados/tasks.py`, `dados/dbdata.py`, and `sync_geofiles.py`. Live dependents include `Municipio.historico_casos` and public materialized views. No current Django model exists for this table. |
| `Historico_alerta_chik` | table | active | retain | map-unmanaged | read-write-external | `administrador` | none | raw SQL | PK `id`; unique `("SE", municipio_geocodigo, "Localidade_id")`; approx. rows `4532807`; size `2495504384` bytes | Read through disease-suffix SQL and written by `backfill_casprov.py`. No current Django model exists for this table. |
| `Historico_alerta_zika` | table | active | retain | map-unmanaged | read-write-external | `postgres` | none | raw SQL | PK `id`; unique `("SE", municipio_geocodigo, "Localidade_id")`; approx. rows `4057247`; size `1328365568` bytes | Read through disease-suffix SQL in current code. No current Django model exists for this table. |
| `Localidade` | table | legacy | archive | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `id`; approx. rows `10`; size `1400832` bytes | `Localidade` belonged to the legacy Redemet workflow. Maintainers approved archival and no ORM mapping. Physical archival requires a separate reviewed database change after the `Ovitrampa.Localidade_id` dependency is resolved. |
| `Notificacao` | table | active | retain | map-unmanaged | read-write-application | `administrador` | none | raw SQL and ingestion UPSERT | PK `id`; unique `(nu_notific, dt_notific, cid10_codigo, municipio_geocodigo)`; approx. rows `37097472`; size `13733748736` bytes | Queried by `api/internal/services.py` and `api/db.py`; written by `ingestion/tasks.py` merge logic. No current Django model exists for this table, so intended ORM work remains separate from current ownership. |
| `Ovitrampa` | table | external-access | retain | map-unmanaged | unknown | `administrador` | none | no runtime evidence found | PK `id`; FK `Localidade_id -> Municipio.Localidade(id)`; approx. rows `0`; size `8192` bytes | The table is retained for confirmed external access and future unmanaged ORM mapping. Suggested model: `Ovitrap` with primary key `id`. `Localidade_id` currently references `Municipio.Localidade(id)`, but `Localidade` is approved for archival and must not receive an ORM model. The `Ovitrap` model must not require a mapped `Localidade` model; the legacy FK column may need to be represented through its raw database column or another explicitly reviewed strategy. Access policy remains unresolved in current evidence. Physical archival of `Localidade` requires a separate reviewed database change that resolves this dependency first. |
| `Tweet` | table | legacy | archive | do-not-map | unknown | `administrador` | none | no runtime evidence found | PK `id`; FK `CID10_codigo -> Dengue_global.CID10(codigo)`; approx. rows `3879263`; size `317546496` bytes | `Tweet` contains historical data but must not receive an ORM model. Maintainers approved archival and no ORM mapping. This PR records lifecycle and ORM decisions only. |
| `alerta_mrj` | table | legacy | archive | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; unique `(aps, se)`; approx. rows `6274`; size `1114112` bytes | This table belongs to a retired reporting workflow. Maintainers approved archival and no ORM mapping. This PR records lifecycle and ORM decisions only. |
| `alerta_mrj_chik` | table | legacy | archive | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; unique `(aps, se)`; approx. rows `6270`; size `1114112` bytes | This table belongs to a retired reporting workflow. Maintainers approved archival and no ORM mapping. This PR records lifecycle and ORM decisions only. |
| `alerta_mrj_zika` | table | legacy | archive | do-not-map | unknown | `postgres` | none | no runtime evidence found | PK `id`; unique `(aps, se)`; size `24576` bytes | This table belongs to a retired reporting workflow. Maintainers approved archival and no ORM mapping. This PR records lifecycle and ORM decisions only. |
| `historico_casos` | materialized view | legacy | archive | do-not-map | read-only | `dengueadmin` | none | raw SQL | no PK; approx. rows `4796063`; size `358580224` bytes | The materialized view is queried only by `NotificationResume.tail_estimated_cases()` in `dados/dbdata.py`. That method is currently called by `AlertaStateView` in `dados/views.py`, and `AlertaStateView` is currently registered for `/alerta/<state>/<disease>`. Maintainers have classified this flow as legacy. Physical archival of this materialized view requires a separate code change that removes or replaces this call path first. This PR records lifecycle and ORM decisions only. |
| `sprint202425` | table | temporary | archive | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `id`; approx. rows `4187433`; size `655433728` bytes | Time-bounded working table. Maintainers approved archival and no ORM mapping. This PR records lifecycle and ORM decisions only. |

## Schema `forecast`

No live objects were found in `forecast`, and no target-schema objects from
`forecast` were present in `containers/postgres/schemas/schemas_dengue.sql`.

## Schema `weather`

| Object | Type | Usage | Retention | ORM status | Access | Database owner | Django ownership | Current query mechanism | Catalog summary | Evidence and notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `copernicus_arg` | table | legacy | archive | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | no PK; approx. rows `4420298`; size `729317376` bytes | `copernicus_arg` is approved for archival and must not receive an ORM model. This PR records lifecycle and ORM decisions only. |
| `copernicus_bra` | table | external-access | pending-decision | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | no PK; unique `(date, geocode)`; approx. rows `51006972`; size `10261078016` bytes | Present live and in the dump. Confirmed external consumers exist outside the AlertaDengue application, but retention and access policy still require a separate decision. |
| `copernicus_foz_do_iguacu` | table | legacy | archive | do-not-map | unknown | `dengueadmin` | none | no runtime evidence found | PK `index`; approx. rows `86496`; size `8462336` bytes | `copernicus_foz_do_iguacu` is approved for archival and must not receive an ORM model. This PR records lifecycle and ORM decisions only. |

## Schema `episcanner`

| Object | Type | Usage | Retention | ORM status | Access | Database owner | Django ownership | Current query mechanism | Catalog summary | Evidence and notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `sir_params` | table | active | retain | existing-managed | read-write-application | `dengueadmin` | managed | Django ORM | PK `id`; unique `(cid10, geocode, year)`; size `49152` bytes | The current repository treats this table as migration-managed through `EpiscannerSirParams` and migration `0006_episcanner_sir_params`. The live table and unique constraint match that repository definition, and current code uses `EpiscannerSirParams.objects.update_or_create()` in `dados/tasks.py`. |

## Unmanaged ORM Candidates

### Existing unmanaged models to review

- `Dengue_global.CID10`
- `Dengue_global.Municipio`

### New unmanaged ORM candidates

- `Dengue_global.estado`
- `Dengue_global.macroregional`
- `Dengue_global.parameters`
- `Dengue_global.regional`
- `Municipio.Notificacao`
- `Municipio.Historico_alerta`
- `Municipio.Historico_alerta_chik`
- `Municipio.Historico_alerta_zika`
- `Municipio.Ovitrampa`

### Pending ORM decisions

- None. Maintainer decisions in this PR reduce pending ORM decisions to zero.

## Phase 1 Conclusion

### Ready for Phase 2

- review `CID10`
- review and complete `City`
- map `State`
- map `Macroregion`
- map `parameters`
- map `regional`
- map `Notificacao`
- map `Historico_alerta`
- map `Historico_alerta_chik`
- map `Historico_alerta_zika`
- map `Ovitrap`

### Pending decisions

- retention and access policy for `weather.copernicus_bra`
- write policy for `Municipio.Ovitrampa`
- handling of the legacy `Ovitrampa.Localidade_id` relationship
- code removal or replacement required before archiving
  `Municipio.historico_casos`
- database foreign-key handling required before archiving
  `Municipio.Localidade`
- external consumers not covered by this repository

## Approved for archival, not ORM mapping

This PR records approved lifecycle decisions only. No table or materialized
view is modified by this PR. Actual archival requires a separate reviewed
issue and database change.

### `Dengue_global`

- `alerta_regional_chik`
- `alerta_regional_dengue`
- `alerta_regional_zika`
- `regional_saude`

### `Municipio`

- `Bairro`
- `Clima_Satelite`
- `Clima_cemaden`
- `Estacao_cemaden`
- `Localidade`
- `Tweet`
- `alerta_mrj`
- `alerta_mrj_chik`
- `alerta_mrj_zika`
- `historico_casos`
- `sprint202425`

### `weather`

- `copernicus_arg`
- `copernicus_foz_do_iguacu`

Additional constraints:

- `historico_casos` must not be archived until its current application call
  path is removed or replaced.
- `Localidade` must not be archived until the
  `Ovitrampa.Localidade_id` dependency is resolved.

## Remaining Blockers

- `weather.copernicus_bra`
  - remains `usage: external-access`, `retention: pending-decision`,
    `orm_status: do-not-map`, `access: unknown`, `django ownership: none`
- `Municipio.Ovitrampa`
  - remains `usage: external-access`, `retention: retain`,
    `orm_status: map-unmanaged`, `access: unknown`, `django ownership: none`
  - write policy remains unverified in current repository evidence
- `Municipio.Ovitrampa` and `Municipio.Localidade`
  - the legacy `Localidade_id` foreign-key relationship needs an explicitly
    reviewed ORM and database strategy before `Localidade` can be archived
- `Municipio.historico_casos`
  - current legacy application call path must be removed or replaced before
    archival
- External consumers not covered by this repository
  - still unverified where relevant
