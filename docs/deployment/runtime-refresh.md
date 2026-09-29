# Runtime refresh (issue #948)

Before invoking `makim deployment.refresh-runtime --env <env> --week YYYYWW`,
the external orchestrator must update historical alert data in PostgreSQL,
validate producer outputs, confirm that the incidence-map artifacts correspond
to the requested epidemiological week, and publish those validated artifacts
into AlertaDengue's own source directory:

```text
AlertaDengue/static/img/incidence_maps/
```

With the selected PostgreSQL and web services already running, invoke the local
deployment operation on the AlertaDengue host:

```bash
makim deployment.refresh-runtime --env prod --week 202638
```

The task delegates to `scripts/refresh_runtime.sh`, supports `dev`, `staging`,
and `prod`, and uses the same Compose files/project names as Sugar. Host Docker
Compose and `sha256sum` are required; the running web service supplies the
project's `epiweeks` dependency. Configuration comes from `.envs/.env`.

AlertaDengue owns this sequence: validate arguments and semantic week → validate
non-empty national dengue/chikungunya source maps → refresh the six retained
dashboard/count materialized views in one transaction → `collectstatic --no-input`
→ clear the configured Django cache → validate local database/static state.
Each failed command stops execution. Failed refresh or collectstatic never clears
the application cache; a failed cache-clear command never reports success.
Rerunning after correcting a failure is supported.

Both `MAX("SE")::integer` values, from `"Municipio"."Historico_alerta"` and
`public.hist_uf_dengue_materialized_view`, must equal the requested integer week.
AlertaDengue deliberately does not infer artifact epiweek from PNG contents or
producer metadata. Its local SHA256 postcondition only verifies that the
already-published source assets were collected unchanged into `STATIC_ROOT`.
Both national source PNG SHA256 values must match their collected copies under
`/opt/services/staticfiles/img/incidence_maps/country/` inside web. The homepage
uses `str(get_last_SE())` in `?v=YYYYWW` for both national map URLs.

Staging/production web bind-mount the source tree and repository `staticfiles/`
at `/opt/services/staticfiles`, served through `dj_static.Cling`. Recreate web
once to apply the mounts and ensure the directories are writable by its configured
UID/GID. Collected files then survive container recreation. On production the
checkout is `/opt/services/AlertaDengue`, so `../staticfiles/` resolves to
`/opt/services/AlertaDengue/staticfiles`, the host directory already consumed by
external nginx. Development checkouts elsewhere naturally resolve differently.

After the local operation succeeds, the external deployment/orchestrator owns
reverse-proxy cache invalidation where required, direct/public endpoint
verification, and workflow completion. AlertaDengue does not locate producer
outputs, copy artifacts, invoke a producer, or manage that external infrastructure.
