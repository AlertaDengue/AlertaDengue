# Internal Notifications API

The Internal Notifications API provides authenticated access to selected records from the `Municipio.Notificacao` table.

This endpoint is intended for internal InfoDengue research, validation, and technical analysis workflows.

## Endpoint

```http
GET /api/internal/notifications/
````

Example staging URL:

```text
http://s2.dengue.mat.br/api/internal/notifications/
```

## Authentication

This API requires token authentication.

Each authorized user or service must have its own Django user and API token.

Use the token in the request header:

```http
Authorization: Token <YOUR_TOKEN>
```

Example:

```bash
curl \
  -H "Authorization: Token <YOUR_TOKEN>" \
  "http://s2.dengue.mat.br/api/internal/notifications/?municipio_geocodigo=3304557&cid10=A90&year=2026&limit=10&offset=0"
```

Do not share tokens or commit them to the repository.

## Requesting access

To request access, contact the InfoDengue technical team at:
[**infodengue.team**](mailto:infodengue.team@gmail.com)


Include:

* full name;
* institution or team;
* reason for access;
* expected use case;
* whether the token is for a person or an automated service.

The technical team will create a Django user, assign the proper access group, and generate an individual API token.

## Query parameters

| Parameter             | Description                    | Example           |
| --------------------- | ------------------------------ | ----------------- |
| `municipio_geocodigo` | Municipality geocode           | `3304557`         |
| `cid10`               | Disease CID-10 code            | `A90`             |
| `year`                | Notification year              | `2026`            |
| `epiweek_start`       | Initial epidemiological week   | `1`               |
| `epiweek_end`         | Final epidemiological week     | `20`              |
| `date_start`          | Initial notification date      | `2026-01-01`      |
| `date_end`            | Final notification date        | `2026-04-30`      |
| `limit`               | Number of returned records     | `1000`            |
| `offset`              | Pagination offset              | `0`               |
| `include_count`       | Include total matching records | `true` or `false` |

## Pagination

Use `limit` and `offset`:

```bash
curl \
  -H "Authorization: Token <YOUR_TOKEN>" \
  "http://s2.dengue.mat.br/api/internal/notifications/?municipio_geocodigo=3304557&cid10=A90&year=2026&limit=1000&offset=0"
```

Second page:

```bash
curl \
  -H "Authorization: Token <YOUR_TOKEN>" \
  "http://s2.dengue.mat.br/api/internal/notifications/?municipio_geocodigo=3304557&cid10=A90&year=2026&limit=1000&offset=1000"
```

## Count

By default, the API does not return `count` because counting can be expensive on large tables.

Use `include_count=true` only when needed:

```bash
curl \
  -H "Authorization: Token <YOUR_TOKEN>" \
  "http://s2.dengue.mat.br/api/internal/notifications/?municipio_geocodigo=3304557&cid10=A90&year=2026&limit=10&offset=0&include_count=true"
```

## Example response

```json
{
  "limit": 10,
  "offset": 0,
  "results": [
    {
      "id": 1547540300,
      "municipio_geocodigo": 3304557,
      "dt_notific": "2026-04-11",
      "dt_sin_pri": "2026-04-10",
      "dt_digita": "2026-04-13",
      "se_notif": 14,
      "ano_notif": 2026,
      "classi_fin": 0.0,
      "criterio": 0.0,
      "cid10_codigo": "A90",
      "id_distrit": 148.0,
      "id_bairro": 151.0,
      "nm_bairro": "GUARATIBA",
      "nu_notific": 6515721
    }
  ]
}
```

## Example notebooks

Example notebooks are available for Python and R usage:

* [Python notebook](../notebooks/internal_notifications_api_python.ipynb)
* [R notebook](../notebooks/internal_notifications_api_r.ipynb)

Recommended environment variables:

```bash
export NOTIFICATION_API_TOKEN="<YOUR_TOKEN>"
export NOTIFICATION_API_BASE_URL="http://s2.dengue.mat.br"
```

## Security notes

* Use one token per user or service.
* Do not share tokens.
* Do not commit tokens to Git.
* Prefer environment variables in notebooks and scripts.
* Revoke and regenerate exposed tokens.
* Disable users that no longer need access.

## Usage notes

This endpoint exposes row-level notification data for authorized internal use.

Prefer filtered requests using municipality, disease, year, date range, or epidemiological week range. Avoid broad unfiltered queries against the full notification table.
