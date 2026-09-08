# `Municipio` ORM coverage audit

Audit date: 2026-09-08. This is a read-only, audit-only reconciliation of the
physical PostgreSQL `Municipio` schema, repository access paths, Django model
metadata, routing, and external writer evidence. It introduces no model,
migration, SQL, API, routing, or database change.

## Methodology and safety

The supported disposable PostgreSQL service was inspected through catalog
queries only. The service is PostgreSQL 14.24. Its `dengue` database contains
the `Municipio` schema; the separate `infodengue` database in the same service
contains no `Municipio` relations. This distinction is recorded because the
repository settings use `PSQL_DB` for the `dados` alias and `PSQL_DBF` for the
separate database. Catalog estimates (`pg_class.reltuples`) and relation sizes
were used; no unrestricted row scan or notification row was read. No DDL,
DML, migration, refresh, or maintenance command was run.

Repository searches covered Python, SQL, migrations, tests, shell/Makim,
Docker/Compose, documentation, JavaScript, and tracked R files. Generated
assets, dependencies, caches, and `.git` were excluded from runtime
conclusions. SQL history, migrations, and external checkouts were retained as
historical or operational evidence rather than counted as active readers.

## Complete physical-object inventory

The catalog contains 22 relations in `Municipio`: four ordinary tables, four
sequences, and fourteen indexes. There are no partitioned tables or
partitions, views, materialized views, or foreign tables in this schema. There
are no user-defined triggers or rules. Downstream materialized-view dependencies were catalog-confirmed: `public.city_count_by_uf_dengue_materialized_view`, `public.hist_uf_dengue_materialized_view`, `public.uf_total_view`, `public.city_count_by_uf_chikungunya_materialized_view`, `public.hist_uf_chik_materialized_view`, `public.uf_total_chik_view`, `public.city_count_by_uf_zika_materialized_view`, `public.hist_uf_zika_materialized_view`, `public.uf_total_zika_view`, and `public.epiyear_summary_materialized_view`. One function, `public.calculate_digit(integer)`, contains the string
`Municipio` in its stored definition, but has no catalog dependency on a
`Municipio` relation; it is not treated as a reader.

| Object | Type | Owner | Identity | Size/estimate | Model | Access | Active readers | Active writers | Classification | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `"Municipio"."Historico_alerta"` | table | `administrador` | PK `id`; unique `("SE", municipio_geocodigo, "Localidade_id")` | 1,318,420,480 bytes / 4,823,903 | `LegacyHistoricalAlertDengue` | unmanaged; `dados` | historical service, city report, legacy API, dashboards, EpiScanner, geofile sync | AlertTools/operational backfill evidence | intentional adapter plus retained SQL | Keep adapter; resolve writer deployment before tweet removal |
| `"Municipio"."Historico_alerta_chik"` | table | `administrador` | PK `id`; unique `("SE", municipio_geocodigo, "Localidade_id")` | 1,318,010,880 bytes / 4,823,913 | `LegacyHistoricalAlertChikungunya` | unmanaged; `dados` | same disease-routed readers | AlertTools/operational backfill evidence | intentional adapter plus retained SQL | Same as dengue |
| `"Municipio"."Historico_alerta_zika"` | table | `postgres` | PK `id`; unique `("SE", municipio_geocodigo, "Localidade_id")` | 1,097,089,024 bytes / 4,099,637 | `LegacyHistoricalAlertZika` | unmanaged; `dados` | historical service, city report, legacy API, dashboards, EpiScanner | no current repository writer confirmed | intentional adapter plus retained SQL | Confirm external lifecycle |
| `"Municipio"."Notificacao"` | table | `administrador` | PK `id`; unique `(nu_notific, dt_notific, cid10_codigo, municipio_geocodigo)` | 10,404,151,296 bytes / 43,334,424 | `Notification` | unmanaged; `dados` | internal notification list; CSV/report/analytics; rollback | SINAN ingestion and rollback workflows | application-write adapter with external physical ownership | Keep bounded list ORM; retain ingestion SQL |
| `"Municipio"."Historico_alerta_id_seq"` | sequence | `administrador` | owned by `Historico_alerta.id` default | 8,192 bytes / 1 | — | default dependency | table default | external writer path | physical sequence | Do not model |
| `"Municipio"."Historico_alerta_chik_id_seq"` | sequence | `administrador` | owned by `Historico_alerta_chik.id` default | 8,192 bytes / 1 | — | default dependency | table default | external writer path | physical sequence | Do not model |
| `"Municipio"."Historico_alerta_zika_id_seq"` | sequence | `postgres` | owned by `Historico_alerta_zika.id` default | 8,192 bytes / 1 | — | default dependency | table default | external lifecycle | physical sequence | Do not model |
| `"Municipio"."Notificacao_id_seq"` | sequence | `administrador` | owned by `Notificacao.id` default | 8,192 bytes / 1 | — | default dependency | table default | ingestion | physical sequence | Do not model |
| `"Municipio"."Alerta_idx_data"` | index | `administrador` | `data_iniSE DESC` | 33 MB / 4,823,903 | — | supporting index | historical SQL | external writer maintenance | retained supporting index | Preserve |
| `"Municipio"."Historico_alerta_pk"` | unique index | `administrador` | `id` | 103 MB / 4,823,903 | — | PK backing index | ORM and SQL | external writer maintenance | identity support | Preserve |
| `"Municipio".alertas_unicos` | unique index | `administrador` | `"SE", municipio_geocodigo, "Localidade_id"` | 145 MB / 4,823,903 | — | deduplication | AlertTools/backfill | AlertTools/backfill | transactional UPSERT boundary | Preserve |
| `"Municipio"."Alerta_chik_idx_data"` | index | `administrador` | `data_iniSE DESC` | 33 MB / 4,823,913 | — | supporting index | historical SQL | external writer maintenance | retained supporting index | Preserve |
| `"Municipio"."Historico_alerta_chik_pk"` | unique index | `administrador` | `id` | 103 MB / 4,823,913 | — | PK backing index | ORM and SQL | external writer maintenance | identity support | Preserve |
| `"Municipio".alertas_unicos_chik` | unique index | `administrador` | `"SE", municipio_geocodigo, "Localidade_id"` | 145 MB / 4,823,913 | — | deduplication | AlertTools/backfill | AlertTools/backfill | transactional UPSERT boundary | Preserve |
| `"Municipio"."Alerta_zika_idx_data"` | index | `postgres` | `data_iniSE DESC` | 28 MB / 4,099,637 | — | supporting index | historical SQL | no current repository writer confirmed | retained supporting index | Preserve |
| `"Municipio"."Historico_alerta_zika_pk"` | unique index | `postgres` | `id` | 88 MB / 4,099,637 | — | PK backing index | ORM and SQL | no current repository writer confirmed | identity support | Preserve |
| `"Municipio".alertas_unicos_zika` | unique index | `postgres` | `"SE", municipio_geocodigo, "Localidade_id"` | 123 MB / 4,099,637 | — | deduplication | AlertTools/backfill | no current repository writer confirmed | transactional UPSERT boundary | Preserve |
| `"Municipio"."Dengue_idx_data"` | index | `administrador` | `dt_notific DESC, se_notif DESC` | 289 MB / 43,334,424 | — | date/week lookup | CSV/report/analytics | ingestion | retained supporting index | Preserve |
| `"Municipio"."Notificacao_pk"` | unique index | `administrador` | `id` | 928 MB / 43,334,424 | — | PK backing index | ORM and SQL | ingestion | identity support | Preserve |
| `"Municipio".casos_unicos` | unique index | `administrador` | `nu_notific, dt_notific, cid10_codigo, municipio_geocodigo` | 1,342 MB / 43,334,424 | — | deduplication | ingestion/rollback | ingestion/rollback | transactional UPSERT boundary | Preserve |
| `"Municipio".notificacao_api_city_cid10_year_date_id_idx` | index | `administrador` | `municipio_geocodigo, cid10_codigo, ano_notif, dt_notific DESC, id DESC` | 1,719 MB / 43,334,424 | — | bounded internal API | internal notification service | none in repository | ORM query support | Preserve |
| `"Municipio".notificacao_cid10_idx` | index | `administrador` | `cid10_codigo` | 286 MB / 43,334,424 | — | disease lookup | CSV/report/analytics | ingestion | retained supporting index | Preserve |

### Column-level reconciliation

The three historical tables have the same 31 physical columns in the inspected
database. In ordinal order they are:

`data_iniSE date NOT NULL`, `SE integer NOT NULL`, `casos_est real NULL`,
`casos_est_min integer NULL`, `casos_est_max integer NULL`, `casos integer
NULL`, `municipio_geocodigo integer NOT NULL`, `p_rt1 real NULL`, `p_inc100k
real NULL`, `Localidade_id integer NULL`, `nivel smallint NULL`, `id bigint NOT
NULL DEFAULT nextval(<disease>_id_seq)`, `versao_modelo varchar(40) NULL`,
`municipio_nome varchar(128) NULL`, `tweet numeric(5,0) NULL DEFAULT NULL`,
`Rt real NULL DEFAULT NULL`, `pop numeric NULL`, `tempmin numeric NULL`,
`umidmax numeric NULL`, `receptivo smallint NULL`, `transmissao smallint NULL`,
`nivel_inc smallint NULL`, `umidmed numeric NULL`, `umidmin numeric NULL`,
`tempmed numeric NULL`, `tempmax numeric NULL`, `casprov integer NULL`,
`casprov_est real NULL`, `casprov_est_min integer NULL`, `casprov_est_max integer
NULL`, `casconf integer NULL`. No column is generated or identity.

The repository adapter intentionally maps 30 fields and omits `tweet`. The
initial development-VPS audit found `dados.0008_remove_historical_alert_tweet_column`
marked applied while the physical `tweet` column remained on all three history
tables. The development database was subsequently reconciled by dropping only
`tweet` from `Historico_alerta`, `Historico_alerta_chik`, and
`Historico_alerta_zika`. A subsequent catalog check confirmed zero `tweet`
columns. The historical migration-state/physical-schema drift is therefore
resolved in the development VPS; it remains an operational finding in the
audit record.

`Notificacao` has 34 nullable business columns plus non-null `id`: `id bigint
DEFAULT nextval`, `dt_notific date`, `se_notif integer`, `ano_notif integer`,
`dt_sin_pri date`, `se_sin_pri integer`, `dt_digita date`,
`municipio_geocodigo integer`, `nu_notific integer`, `cid10_codigo varchar(5)`,
`dt_nasc date`, `cs_sexo varchar(1)`, `nu_idade_n integer`, `resul_pcr numeric`,
`criterio numeric`, `classi_fin numeric`, `dt_chik_s1 date`, `dt_chik_s2 date`,
`dt_prnt date`, `res_chiks1 varchar(255)`, `res_chiks2 varchar(255)`,
`resul_prnt varchar(255)`, `dt_soro date`, `resul_soro varchar(255)`,
`dt_ns1 date`, `resul_ns1 varchar(255)`, `dt_viral date`, `resul_vi_n
varchar(255)`, `dt_pcr date`, `sorotipo varchar(255)`, `id_distrit numeric`,
`id_bairro numeric`, `nm_bairro varchar(255)`, and `id_unidade numeric`.

`Notification` is a documented projection: its service uses only the fields
needed for the bounded internal response. The physical identity is safe
(`id`), but several physical numeric/integer and length details differ from
the adapter because the API performs explicit casts and does not expose every
column. This is not a write model and must not be used for ingestion writes.

## Model-to-table reconciliation

| Model | Physical object | Management | Identity/fields | Finding |
| --- | --- | --- | --- | --- |
| `dados.models.LegacyHistoricalAlertDengue` | `Historico_alerta` | `managed=False` | explicit `id`; normalized mappings for all service fields; no model `tweet` | intentional projection; physical tweet discrepancy remains |
| `dados.models.LegacyHistoricalAlertChikungunya` | `Historico_alerta_chik` | `managed=False` | same contract | intentional projection; physical tweet discrepancy remains |
| `dados.models.LegacyHistoricalAlertZika` | `Historico_alerta_zika` | `managed=False` | same contract | intentional projection; physical tweet discrepancy remains |
| `dados.models.Notification` | `Notificacao` | `managed=False` | explicit `id`; bounded API projection | complete for internal list; not a global schema model |

No implicit Django `id` is introduced. All four adapters use schema-qualified
quoted `db_table` names, and all have declarative read/write policy metadata.
`READ_ONLY`, `READ_WRITE_EXTERNAL`, and `READ_WRITE_APPLICATION` are metadata,
not technical database write guards.

## Active reader/writer matrix and path classification

| Entry point/caller | Object/access | Alias | Classification and decision |
| --- | --- | --- | --- |
| `/api/internal/historical-alerts/` → `api.internal.historical_alerts` | disease-selected history; ORM filters, ordering, bounded limit | `dados` | existing ORM path complete |
| `/api/v1/alert-city/` → `api.v1.services` | normalized historical projection | `dados` | existing ORM path complete |
| `/api/alertcity/` → `api.db.AlertCity` | disease allowlist, compatibility response, window accumulation/DataFrame | SQLAlchemy/`PSQL_DB` | legacy compatibility SQL |
| city reports → `ReportCity.read_disease_data` | bounded history, climate projection; ORM service | `dados` | existing bounded ORM path; 200-row contract |
| state reports/dashboard → `ReportState`, `dados.dbdata` | latest-per-city, joins, windows, aggregates, DataFrames | SQLAlchemy/`PSQL_DB` | aggregation/window query |
| homepage state history/city counts | public materialized views and cross-schema joins | SQLAlchemy/`PSQL_DB` | materialized-view/DataFrame boundary; ten downstream materialized-view dependencies are catalog-confirmed |
| `/api/notifications-reduced/` and exports | notification joins, CASE expressions, aggregation/DataFrame output | SQLAlchemy/`PSQL_DB` | DataFrame/report SQL |
| `/api/internal/notifications/` → `list_notifications` | filtered ordered page, optional count, limit/offset | `dados` | existing ORM path complete; supporting index verified |
| `ingestion` SINAN stage/merge | notification bulk insert/delete/UPSERT and deduplication | SQLAlchemy/psycopg2 | ingestion or bulk-write SQL; retain |
| rollback preview/execute | notification locks, anti-joins, drift guards, update/delete | `default` plus SQL path | transactional UPSERT/deduplication and recovery SQL; retain |
| `dados.tasks` EpiScanner input | historical joins and pandas extraction | SQLAlchemy/`PSQL_DB` | analytical/DataFrame SQL |
| `sync_geofiles` | distinct active cities/history plus filesystem output | SQLAlchemy/`PSQL_DB` | PostGIS/geofile and operational boundary |
| `backfill_casprov` | allowlisted history update, temporary stage/COPY | `default` | operational maintenance SQL |

The legacy endpoint and broad reports are not ORM candidates merely because
they select rows. Their stable contracts require windows, joins, aggregation,
DataFrame shaping, bulk mechanics, locking, dynamic disease routing, or
compatibility fields. The four bounded ORM adapters are already in place.

## Database routing

`DatabaseAppsRouter` maps app label `dados` to alias `dados` for both reads and
writes. The historical service and notification service also call
`.using("dados")` explicitly. Existing regression tests capture queries and
assert no corresponding read reaches `default`. The router does not grant or
prevent writes, and migration routing is separate from runtime routing.

Write-capable notification ingestion uses direct SQL and owns its transaction;
the unmanaged `Notification` adapter is not the ingestion owner. Historical
writers are external/operational and may use a PostgreSQL connection outside
Django. Migration `0005_create_notification_api_group` can be marked applied
while its group row is absent; that is deployment/data drift, not evidence of a
`Municipio` schema defect.

## Migration-state and external ownership findings

The repository contains `0008_remove_historical_alert_tweet_column`, and Django
marked it applied in the development VPS with no pending plan. The initial
catalog check nevertheless found all three physical `tweet` columns. After a
development-only reconciliation that dropped only those three columns, a
subsequent catalog check confirmed zero `tweet` columns. No production
operation is implied or authorized by this audit.

The active development `AlertaDengueAnalise` environment uses AlertTools
1.1.0 at RemoteSha
`9199ac34e066a5617985ce5b73003b47056bcd6d`. In that active runtime package,
`tabela_historico()` and `write_alerta()` contain no `tweet` reference. The
stale external checkout inspected earlier was not the active runtime package.
This writer evidence and the column reconciliation are limited to the
development VPS; they do not establish production state.

## Deliberate SQL boundaries

Retain SQL for legacy compatibility APIs, analytical/state reports, materialized
views, DataFrame contracts, PostGIS/geofile processing, notification ingestion,
COPY, bulk operations, UPSERT/deduplication, lock-sensitive rollback, dynamic
disease table selection, and operational backfills. A router or `READ_ONLY`
attribute is not a substitute for database permissions or a write guard.

## Bounded ORM candidates

No additional bounded `Municipio` ORM candidate remains. The existing
historical-alert adapters/service, public v1 reads, bounded city-report history,
map scalar metadata, and internal notification pagination are complete.
Remaining compatibility, analytical, bulk, transactional, and geofile paths are
deliberate SQL boundaries.

## Unresolved risks and separate follow-ups

The historical migration drift and tweet-free writer validation are resolved for
the development VPS. Any production verification or operation is explicitly
outside this audit and must not be inferred from the development reconciliation.

1. **Confirm external history lifecycle.** Evidence: table owners differ and
   active writes are not fully observable from this repository. Scope: owner,
   scheduled writer, permissions, and retention for the three history tables.
   Exclude speculative model or DDL changes. Acceptance: documented owner and
   writer contract for each table. Dependency/risk: external operations.

## Conclusion

The complete inspected `Municipio` denominator is 4 physical tables, 4
sequences, and 14 indexes (22 relations total). Four tables have adapters: 4
unmanaged models, 0 managed `Municipio` models, and 0 intentionally unmodelled
tables in this schema. The adapters have safe explicit identities and correct
`dados` routing for their bounded contracts. Remaining raw SQL is justified by
compatibility, analytics, bulk, transactional, spatial, or operational
requirements. No production-code ORM refactor is justified by this audit.

The development VPS catalog now confirms zero `tweet` columns after the
development-only reconciliation, while the historical drift remains documented
as an operational finding. No production state or operation is implied.
