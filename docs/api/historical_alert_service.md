# Historical alert service layer

Issue #1064 adds an internal REST/API service layer for historical alerts in
`api.internal.historical_alerts`. It reuses the #1063 unmanaged ORM adapters
and hides legacy table routing behind normalized Python-facing functions.

Issue #1066 exposes that service as the restricted internal endpoint
`GET /api/internal/historical-alerts/`. It uses the existing token/group API
permission and accepts the required `disease` parameter (`dengue`, `chik`,
`chikungunya`, or `zika`) and optional `municipality_geocode`,
`epidemiological_week`, `start_week`, `end_week`, `start_date`, `end_date`,
`alert_level`, `limit`, `offset`, and allowlisted `ordering`. Invalid or unsafe
input returns HTTP 400 for authorized requests.

Responses have a bounded `count` and `results` list. Each result is serialized
by the service layer with normalized English `snake_case` fields only.

```json
{
  "count": 1,
  "results": [{"disease": "dengue", "municipality_geocode": 3304557}]
}
```

The API-facing fields use English `snake_case`. The retained
`Historico_alerta`, `Historico_alerta_chik`, and `Historico_alerta_zika` tables
remain separate and unmanaged. The #1042 physical merge remains deferred.

The service deliberately leaves dashboard and report raw SQL unchanged until
those paths are benchmarked. It introduces no migrations, production database
connections, SQL writes, or physical database changes.
