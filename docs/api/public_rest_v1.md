# Public REST API v1

The public REST base route is `/api/v1/`. Its implementation package is
`api/v1/`, which currently provides only `GET /api/v1/`. The root response
identifies the public API, its `v1` version, status, and an empty route map.

Public v1 endpoints use `AllowAny` only when their data is suitable for public
read-only access. Reusable response helpers return either
`{"data": ..., "meta": ...}` success payloads or
`{"detail": ..., "code": ...}` error payloads, with optional keys omitted.

Legacy public endpoints remain in place for compatibility. Future migrations
to public v1 will move one endpoint at a time, preserving explicit contracts
and normalized English `snake_case` response fields.
