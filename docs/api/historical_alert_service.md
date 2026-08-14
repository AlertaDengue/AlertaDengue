# Historical alert service layer

Issue #1064 adds an internal REST/API service layer for historical alerts in
`api.internal.historical_alerts`. It reuses the #1063 unmanaged ORM adapters
and hides legacy table routing behind normalized Python-facing functions.

The API-facing fields use English `snake_case`. The retained
`Historico_alerta`, `Historico_alerta_chik`, and `Historico_alerta_zika` tables
remain separate and unmanaged. The #1042 physical merge remains deferred.

The service deliberately leaves dashboard and report raw SQL unchanged until
those paths are benchmarked. It introduces no migrations, production database
connections, SQL writes, or physical database changes.
