# Retained database objects and ORM boundaries

This is the maintained reference for retained database objects relevant to
Django refactors. It records application-facing models and stable SQL
boundaries; it does not assign Django ownership to external objects. Legacy
quoted identifiers remain only in db_table and db_column mappings.

## Retained schema overview

| Schema | Responsibility | Ownership | Refactor status |
| --- | --- | --- | --- |
| Dengue_global | Municipality, disease, regional and parameter lookups | Retained external/read-only | Search/report lookup boundary complete |
| Municipio | Historical alerts and notifications | Alerts external; notifications application-written through ingestion | Historical API complete |
| ingestion | SINAN run, stage and rollback control | Django-managed | Current model boundary retained |
| episcanner | Scan-result parameters | Django-managed | Current model boundary retained |
| public | Derived report/dashboard materialized views | External/operational ownership unresolved | Retain SQL boundary |

## Retained object inventory

### Dengue_global

| Object | Type | Django model | Management | Access | Current responsibility | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| Municipio | table | dados.models.City | Unmanaged | Read-only | Municipality search/report lookup and bounded scalar map metadata | Search/report reads and `dados.maps.get_city_info` use ORM services; retain GeoJSON/geofile SQL boundaries |
| CID10 | table | dados.models.CID10 | Unmanaged | Read-only | Disease-code lookup | Retain adapter |
| "Dengue_global"."estado" | table | dados.models.State | Unmanaged | Read-only | State-history dependency | Keep in lookup review |
| "Dengue_global"."macroregional" | table | dados.models.MacroRegion | Unmanaged | Read-only | Regional relationship | Keep in lookup review |
| regional | table | dados.models.Regional | Unmanaged | Read-only | Regional search/report lookup | Shared ORM lookup service |
| parameters | table | dados.models.Parameter | Unmanaged | Read-only | City/disease report thresholds; logical key (municipio_geocodigo, cid10) | Shared ORM lookup service; every parameter read filters both key components; no surrogate key |
| "Dengue_global"."parameters_uf" | table | dados.models.ParameterUF | Managed | Django migration-owned | UF-level thresholds | Retain current model |

### Municipio

| Object | Type | Django model | Management | Access | Current responsibility | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| Historico_alerta | table | dados.models.LegacyHistoricalAlertDengue | Unmanaged | Externally maintained; application reads and operational workflows write | Dengue historical alerts | Retain adapter/service; benchmark reports separately |
| Historico_alerta_chik | table | dados.models.LegacyHistoricalAlertChikungunya | Unmanaged | Externally maintained; application reads and operational workflows write | Chikungunya historical alerts | Retain adapter/service; benchmark reports separately |
| Historico_alerta_zika | table | dados.models.LegacyHistoricalAlertZika | Unmanaged | Externally maintained; application reads; no confirmed operational write | Zika historical alerts | Retain adapter/service; benchmark reports separately |
| Notificacao | table | dados.models.Notification | Unmanaged | Application write; external physical ownership | SINAN notification records | Internal bounded list uses the ORM adapter; retain ingestion SQL |

### ingestion and episcanner

| Object | Type | Django model | Management | Access | Current responsibility | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| ingestion.run | table | ingestion.models.Run | Managed | Application read/write | Ingestion lifecycle | Retain model and SQL boundary |
| ingestion.sinan_stage | table | ingestion.models.SinanStage | Managed | Application read/write | Chunked SINAN stage | Retain bulk SQL |
| ingestion.run_rollback | table | ingestion.models.RunRollback | Managed | Application read/write | Rollback audit | Retain transactional design |
| episcanner.sir_params | table | dados.models.EpiscannerSirParams | Managed | Application read/write | EpiScanner results | Retain current model |

### public

| Object | Type | Django model | Management | Access | Current responsibility | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| public.hist_uf_dengue_materialized_view, public.hist_uf_chik_materialized_view, public.hist_uf_zika_materialized_view | materialized views | None | External | Read-only | State history dashboard data | Keep SQL; establish owner, refresh process and safe identity |
| public.city_count_by_uf_dengue_materialized_view, public.city_count_by_uf_chikungunya_materialized_view, public.city_count_by_uf_zika_materialized_view | materialized views | None | External | Read-only | Monitored-city counts | Keep SQL pending identity/ownership evidence |
| public.epiyear_summary_materialized_view | materialized view | None | External | Read-only | Legacy weekly summaries | Keep SQL pending ownership/refresh evidence |

## Completed refactors

The three Municipio.Historico_alerta tables have normalized unmanaged adapters.
They remain separate physical tables; no merge or physical ownership change is
implied. The historical-alert service is their canonical application boundary.

`ReportCity.read_disease_data` now uses that service for its bounded,
municipality-and-epidemiological-week city-report projection. It explicitly
uses the `dados` alias and retains the legacy 200-row limit and output
DataFrame contract. State reports, dashboard aggregates, compatibility APIs,
exports, and alert-generation SQL remain intentional SQL boundaries.

The public /api/v1/alert-city/ endpoint now uses that service and preserves its
normalized response contract. The legacy /api/alertcity/ endpoint remains an
explicit SQL compatibility path and is not a target of this sequence.

The bounded internal /api/internal/notifications/ list uses the Notification
adapter for filtered, ordered pagination on the dados database alias. Ingestion
and writes, CSV and bulk exports, reports and analytics, aggregations, and
operational processing remain explicit SQL boundaries.

## Next schema-group refactors

1. **Dengue_global.Municipio map/geofile metadata beyond scalar lookups.**
   Retain GeoJSON, geometry, shapefile, and geofile workflows as SQL/file
   boundaries pending separate evidence and design.

## Explicit SQL boundaries

Keep these SQL unless separately benchmarked or redesigned:

- complex reports, dashboards and DataFrame compatibility paths;
- public materialized views and their refresh lifecycle;
- PostGIS-heavy and geofile operations;
- COPY, bulk SINAN staging, deduplication and UPSERT;
- rollback comparison, locking and drift protection; and
- operational data backfills.

## Unresolved metadata and ownership

- `City` maps the verified scalar metadata fields `geocodigo` (integer PK),
  `nome` (varchar(128)), `populacao` (bigint), and `uf` (varchar(20)).
  `dados.maps.get_city_info` reads those fields through the explicit `dados`
  alias. Physical ownership and the authoritative population source remain
  external/unresolved; Django does not write this unmanaged table.
- Confirm retained Dengue_global.Municipio geometry/GeoJSON fields and their
  authoritative writer before expanding the adapter.
- Establish owner, refresh mechanism, indexes and safe identity for every
  retained public materialized view before proposing a model.
- Confirm lifecycle and access expectations for external historical tables
  before expanding write-capable application behavior.

Do not introduce surrogate keys for composite-key objects merely to fit an ORM
model. Do not recommend managed=True for retained external tables.
