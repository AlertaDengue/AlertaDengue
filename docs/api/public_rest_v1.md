# Public REST API v1

The public REST v1 routes are `GET /api/v1/`, `GET /api/v1/alert-city/`,
`GET /api/v1/epi-year-week/`, and
`GET /api/v1/notifications/reduced.csv`. Their implementation package is
`api/v1/`. The root response identifies the public API, its `v1` version,
status, and an empty route map.

Public v1 endpoints use `AllowAny` only when their data is suitable for public
read-only access. Reusable response helpers return either
`{"data": ..., "meta": ...}` success payloads or
`{"detail": ..., "code": ...}` error payloads, with optional keys omitted.

Legacy public endpoints remain in place for compatibility. Future migrations
to public v1 will move one endpoint at a time, preserving explicit contracts
and normalized English `snake_case` response fields.

The JSON endpoints use the response helpers; the reduced-notification endpoint
intentionally remains CSV. Their legacy `/api/` routes remain available, while
`/api/internal/` stays separate and restricted.

## Alert-city response fields

`GET /api/v1/alert-city/` returns `{"data": [...]}`. Each record includes only
the following normalized public v1 fields when available from the query result:

| Field | JSON type | Description |
| --- | --- | --- |
| `epidemiological_week_start_date` | string or null | Epidemiological-week start; currently an ISO datetime string, not date-only |
| `epidemiological_week` | integer or null | Epidemiological week |
| `estimated_cases` | number or null | Estimated cases |
| `estimated_cases_min` | number or null | Lower estimated-cases bound |
| `estimated_cases_max` | number or null | Upper estimated-cases bound |
| `cases` | integer or null | Reported cases |
| `municipality_geocode` | integer or null | Municipality geocode |
| `municipality_name` | string or null | Municipality name |
| `rt1_probability` | number or null | Rt probability indicator |
| `incidence_100k_probability` | number or null | Incidence-per-100k probability indicator |
| `locality_id` | integer or null | Locality identifier |
| `alert_level` | integer or null | Alert level |
| `id` | integer or null | Record identifier |
| `model_version` | string or null | Model version |
| `reproduction_number` | number or null | Reproduction number |
| `population` | integer or null | Population |
| `temperature_min` | number or null | Minimum temperature |
| `temperature_mean` | number or null | Mean temperature |
| `temperature_max` | number or null | Maximum temperature |
| `humidity_min` | number or null | Minimum humidity |
| `humidity_mean` | number or null | Mean humidity |
| `humidity_max` | number or null | Maximum humidity |
| `receptive` | integer or null | Receptivity indicator |
| `transmission` | integer or null | Transmission indicator |
| `incidence_level` | integer or null | Incidence level |
| `probable_cases` | integer or null | Probable cases |
| `estimated_probable_cases` | number or null | Estimated probable cases |
| `estimated_probable_cases_min` | number or null | Lower estimated-probable-cases bound |
| `estimated_probable_cases_max` | number or null | Upper estimated-probable-cases bound |
| `confirmed_cases` | integer or null | Confirmed cases |
| `notifications_accumulated_year` | integer or null | Notifications accumulated in the year |

`tweet` is not part of the public v1 contract. Fields outside the documented
contract are omitted. Fields in the contract with a missing, `NaN`, or `NaT`
source value may be returned as `null`. Physical database columns are unchanged;
normalization occurs in the dedicated public v1 alert-city service boundary.
That service reads the retained Municipio historical-alert tables through the
historical-alert service and unmanaged ORM adapters. The normalized public v1
response contract is unchanged, while legacy `/api/alertcity/` remains on its
existing compatibility implementation. No physical database schema change was
introduced. `notifications_accumulated_year` remains in the public v1 contract,
but is `null` on the ORM-backed path because `notif_accum_year` is absent from
the retained Municipio historical-alert tables.
