# REST API architecture

## Legacy public API

Existing non-REST public endpoints remain in their current modules and routes
for backward compatibility. They are not refactored as part of the REST work.

## Public REST API

A future public REST contract should use a versioned route such as `/api/v1/`.
Public data may use `AllowAny` where appropriate. No public REST endpoint is
implemented by this architecture document.

## Internal REST API

Restricted endpoints for analysts, tools, and controlled external integrations
live under `/api/internal/`. They use the existing token/group API permission.
Internal services and views may live under `api.internal.*`; public REST
endpoints should not.

## Naming

Python modules, functions, and variables use `lower_snake_case`; Django
classes use `PascalCase`; and response fields use normalized English
`snake_case`. Future database identifiers use lowercase `snake_case`. Legacy
database identifiers remain confined to adapter or service internals.
