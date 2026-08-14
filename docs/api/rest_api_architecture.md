# REST API architecture

## Legacy public API

Existing non-REST public endpoints remain in their current modules and routes
for backward compatibility. They are not refactored as part of the REST work.

## Public REST API

The public REST base route is `/api/v1/`. Its versioned contract uses
normalized English `snake_case` responses so future public consumers are not
broken by later API evolution. Public read-only data may use `AllowAny` where
appropriate. Future endpoint migrations will happen one endpoint at a time;
legacy public endpoints remain unchanged until then.

## Internal REST API

Restricted endpoints for analysts, tools, and controlled external integrations
live under `/api/internal/`. They use the existing token/group API permission.
Internal services and views may live under `api.internal.*`; public REST
endpoints should not live under `api.internal.*`. Internal API routes are not
versioned now because their clients are controlled and restricted.

## Naming

Python modules, functions, and variables use `lower_snake_case`; Django
classes use `PascalCase`; and response fields use normalized English
`snake_case`. Future database identifiers use lowercase `snake_case`. Legacy
database identifiers remain confined to adapter or service internals.
