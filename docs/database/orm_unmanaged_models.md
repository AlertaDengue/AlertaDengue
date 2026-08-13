# Retained unmanaged ORM adapters

These adapters describe retained, application-facing database objects without
owning their physical schema. Every adapter in this document has
`managed = False`; no migration in this work creates, changes, or drops a
database object.

## Allowlist

| Schema | Adapter | Relation | Policy |
| --- | --- | --- | --- |
| `Dengue_global` | `CID10`, `City`, `State`, `MacroRegion`, `Regional`, `Parameter` | retained lookup, state-history dependency, and report parameters | `READ_ONLY` |
| `Municipio` | `Notification` | `Notificacao` | `READ_WRITE_APPLICATION` |
| `Municipio` | `LegacyHistoricalAlertDengue`, `LegacyHistoricalAlertChikungunya`, `LegacyHistoricalAlertZika` | the three separate `Historico_alerta*` tables | `READ_WRITE_EXTERNAL` |

`ParameterUF` and `EpiscannerSirParams` remain existing Django-managed models;
their ownership was not changed.

The historical tables are legacy adapters only. They are not merged, no
unified physical historical-alert table exists, and #1042's physical merge is
deferred. Raw SQL remains in the heavy dashboard, report, and analytical paths
until an EXPLAIN/benchmark-backed migration is separately approved.

## Excluded objects

Archived, removed, temporary, backup, validation-only, framework, and
SQL-history-only objects are not mapped. This includes `regional_saude`,
`Bairro`, `Localidade`, `Clima_Satelite`, `Clima_cemaden`, `Estacao_cemaden`,
legacy upload objects, `historico_casos`, archive schemas, and all `forecast`
objects. `weather.copernicus_bra` remains unmapped because it has no current
in-repository runtime use and its retention decision is pending. Public views
are also unmapped: the active candidates do not have a documented safe ORM
primary key, so no identity was invented.

## Naming and ownership boundary

Legacy quoted/case-sensitive identifiers occur only in adapter `db_table` and
`db_column` metadata. Python-facing fields use normalized English
`lower_snake_case`; service code exposes canonical disease keys. Future
Django-owned physical objects must use lowercase `snake_case` identifiers:
no uppercase schemas, CamelCase tables, quoted mixed-case identifiers, or new
Portuguese legacy physical names.
