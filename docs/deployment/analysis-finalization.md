# Post-analysis finalization (issue #948)

AlertaDengueAnalise remains an independent producer. After its SQL has been
loaded and its country/state PNG artifacts are complete, run on the deployment
host with the selected PostgreSQL and web services already running:

```bash
makim deployment.finalize-analysis \
  --env prod \
  --week 202638 \
  --maps-source /opt/services/AlertaDengueAnalise/artifacts/incidence_maps
```

The task delegates to `scripts/finalize_analysis_run.sh`; it supports `dev`,
`staging`, and `prod`, using the same Compose files/project as Sugar. It requires
host `rsync`, `sha256sum`, Docker Compose and, for production, `curl`. The running
web service supplies the project's `epiweeks` dependency for semantic input
validation before any refresh or publishing. Configuration comes from
`.envs/.env` and exported deployment variables.

Contract: analysis/load → refresh six retained dashboard/count materialized
views → publish maps with `rsync -a --delete` → `collectstatic --no-input` →
invalidate the configured Django cache → optional external nginx cache
invalidation → postcondition validation. Each failure stops execution;
failed collectstatic never clears caches. Refreshes run in one transaction.
Rerunning after a corrected failure is supported.

Staging and production bind-mount repository `staticfiles/` at
`/opt/services/staticfiles`, which Gunicorn serves through `dj_static.Cling`.
Recreate web once to apply the new mounts and ensure both the source/staticfiles
directories are writable by its configured UID/GID. Collected files then survive
container recreation. Staging also mounts the source tree so published maps are
visible to collectstatic. No nginx deployment configuration is changed.
On production the checkout is `/opt/services/AlertaDengue`, so the relative bind
resolves to `/opt/services/AlertaDengue/staticfiles`, the same host directory
already mounted by external nginx. A development checkout elsewhere naturally
renders a different host path.

For production, configure `INFODENGUE_WEB_ORIGIN` (the direct Gunicorn HTTP URL,
including its published port) and `INFODENGUE_WEB_HOST` (the application Host
header). For the validated production deployment, configure:

```bash
INFODENGUE_WEB_ORIGIN=http://65.21.204.98:8000
INFODENGUE_WEB_HOST=info.dengue.mat.br
```

The origin must use HTTP and an explicit port matching the published web port
(`docker compose port web 8000`). Public application hostnames, HTTPS, and ports
80/443 are rejected. Curl bypasses environment proxies. Both national maps are
checked against the actual origin response using their weekly URLs.

Optionally configure both `INFODENGUE_NGINX_CONTAINER` and
`INFODENGUE_NGINX_CACHE_PATH` (an absolute non-root directory in that container).
Only cached files are deleted; nginx is never restarted/reloaded. Database weeks,
production origin hashes, and source/published/collected map SHA256 values must
match before success. If nginx variables are absent, origin validation still
runs and the finalizer prints a skip message.

The homepage uses the latest retained dengue alert week in `?v=YYYYWW` for both
national PNG URLs. Requested finalization week must equal both
`MAX("SE")` in `"Municipio"."Historico_alerta"` and the dengue state materialized
view, compared as integers by one PostgreSQL query. All postconditions run after
optional nginx invalidation. This finalizer does not run analysis or load SQL,
and gives Django/Celery no Docker socket access.
