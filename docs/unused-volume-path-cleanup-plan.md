# Unused Volume and Path Cleanup Plan

Issue: https://github.com/AlertaDengue/AlertaDengue/issues/950

This plan maps the path and volume variables that were commented as unused in `.envs/.env`, correlates their references, and tracks the phased cleanup. The GitHub issue page was not accessible from this environment, so this inventory is based on the checked-out repository state.

## Scope

Primary source:

- `.envs/.env` lines 68-91

Correlated surfaces:

- Docker Compose files under `containers/`
- Django settings under `AlertaDengue/ad_main/settings/`
- SINAN upload and ingestion code under `AlertaDengue/upload/` and `AlertaDengue/ingestion/`
- Documentation under `docs/` and `README_MAPSERVER.md`
- `.envs/.env.tpl`

Excluded from the correlation:

- `.git/`
- `node_modules/`

## Current Summary

The cleanup does not delete every commented path blindly. The variables fall into three groups:

| Group | Variables | Recommendation |
| --- | --- | --- |
| Removed residual cleanup | `MEDIA_ROOT`, `IMPORTED_FILES`, `TEMP_FILES_DIR`, `STORAGE`, `DOCKER_HOST_DBF_SINAN`, `DOCKER_HOST_PQDIR`, `DOCKER_HOST_INCIDENCE_MAPS`, `DOCKER_HOST_STATIC`, `DOCKER_HOST_MEDIA_ROOT` | Removed from tracked env template and stale settings. Also removed from the local untracked `.envs/.env` used by this staging checkout. |
| Resolved compose risk | `DOCKER_HOST_UPLOADED_FILES_DIR`, `DOCKER_HOST_TEMP_PARQUET_DIR` | `DOCKER_HOST_UPLOADED_FILES_DIR` is active because ingestion collision checks use uploaded storage. `DOCKER_HOST_TEMP_PARQUET_DIR` compose mounts were removed because only compose referenced the host bind mount. |
| Strong dependencies, not cleanup candidates | `DBF_SINAN`, `DOCKER_HOST_SINAN_ROOT`, `DOCKER_HOST_IMPORTED_FILES_DIR`, `DOCKER_HOST_INCOMING_DIR`, `SHAPEFILE_PATH`, `DOCKER_HOST_SHAPEFILES_DIR` | Keep until the owning workflow is migrated. These paths are active application, ingestion, MinIO, or GIS dependencies. |

## Execution Tracker

| Phase | Status | Summary | Semantic commit message |
| --- | --- | --- | --- |
| Phase 1: Make Compose Deterministic | Complete | Keep `DOCKER_HOST_UPLOADED_FILES_DIR` active because ingestion collision checks use uploaded storage; remove active `DOCKER_HOST_TEMP_PARQUET_DIR` compose mounts because no active code references the bind-mounted parquet temp path. | `fix(compose): make SINAN storage mounts deterministic` |
| Phase 2: Remove Safe Residual Env Entries | Complete | Remove stale commented env entries and prune unused legacy variables from `.envs/.env.tpl`. | `chore(env): remove legacy storage path variables` |
| Phase 3: Clean Stale Code Comments | Complete | Remove commented legacy storage settings and define the active container-facing `IMPORTED_FILES_DIR` setting. | `chore(settings): drop legacy storage comments` |
| Phase 4: Align Ingestion Path Naming | Complete | Add `IMPORTED_FILES_DIR` as the container-facing imported storage path, separate from host-side `DOCKER_HOST_IMPORTED_FILES_DIR`, and remove the undocumented `/IMPORTED_FILES` fallback. | `fix(ingestion): define imported files container path` |
| Phase 5: Remove Host Residual Directories | In progress | Added a host-audit script for retired directories. Actual deletion remains a separate ops step after backup/snapshot confirmation. | `ops(storage): prepare retired host path cleanup` |

## Original Commented Path Inventory

| Variable | Original commented value in `.envs/.env` | Current result | Dependency strength | Removal advice |
| --- | --- | --- | --- | --- |
| `MEDIA_ROOT` | `/MEDIA_ROOT` | Removed from settings/template. | Weak residual. | Complete. |
| `IMPORTED_FILES` | `/IMPORTED_FILES` | Removed and replaced by `IMPORTED_FILES_DIR` for container-facing imported storage. | Medium naming residual. | Complete. |
| `TEMP_FILES_DIR` | `/tmp` | Removed from settings/template. | Weak residual. | Complete. |
| `STORAGE` | `/Storage` | Removed from settings/template. | Weak residual. | Complete. |
| `DOCKER_HOST_DBF_SINAN` | `/opt/data/staging/sftp2/alertadengue` | Removed from template and local env. | Weak residual. | Complete, with `DBF_SINAN` retained as the app storage setting. |
| `DOCKER_HOST_UPLOADED_FILES_DIR` | `${DOCKER_HOST_SINAN_ROOT}/uploaded` | Restored as active because `mover_sinan_data.py` uses uploaded storage for collision checks. | Strong current dependency. | Keep. |
| `DOCKER_HOST_TEMP_PARQUET_DIR` | `/opt/data/staging/tmp/dbfs_parquet` | Removed from active compose mounts and template. | Compose-only dependency. | Complete. |
| `DOCKER_HOST_PQDIR` | `/opt/data/staging/sftp2/alertadengue/dbfs_parquet` | Removed from local env. | Weak residual. | Complete. |
| `DOCKER_HOST_INCIDENCE_MAPS` | `/opt/data/staging/img/incidence_maps` | Removed from template and local env. | Weak residual. | Complete. |
| `DOCKER_HOST_STATIC` | `/opt/services/staging_AlertaDengue/staticfiles` | Removed from template and local env. | Weak residual. | Complete. |
| `DOCKER_HOST_MEDIA_ROOT` | `/opt/data/staging/sftp2/alertadengue/uploaded` | Removed from local env. | Weak residual. | Complete. |

## Strong Dependency Paths

These are adjacent to the commented variables and should be treated as live dependencies, not cleanup candidates.

| Variable | Active use | Why it is strong |
| --- | --- | --- |
| `DBF_SINAN` | `AlertaDengue/upload/models.py` builds upload and log paths from `settings.DBF_SINAN`. | Upload logs and imported upload paths depend on it. Removing it breaks upload models unless the storage backend is migrated. |
| `DOCKER_HOST_SINAN_ROOT` | Mounted in `containers/compose-base.yaml` to `/opt/services/ingestion/sinan`. | It is the top-level SINAN storage root for the app container. |
| `DOCKER_HOST_IMPORTED_FILES_DIR` | Mounted in `base`, `celery`, and `celery-beat`; documented as canonical imported storage; used by `mover_sinan_data.py`. | This is the canonical imported-file source of truth. Keep. |
| `DOCKER_HOST_INCOMING_DIR` | Mounted by `containers/compose-minio.yaml` materializer to `/incoming`. | MinIO materialization and ingestion watcher flow depend on it. |
| `SHAPEFILE_PATH` | Used by GIS mapfile/geotiff code. | Required for map generation and shapefile access. |
| `DOCKER_HOST_SHAPEFILES_DIR` | Active env variable and documented in `README_MAPSERVER.md`; only compose mount is currently commented. | Keep until GIS/mapserver volume layout is explicitly simplified. |

## Correlation Notes

### SINAN Storage

Current intended flow:

1. MinIO bucket receives SINAN files.
2. `minio-materializer` mirrors the bucket into `${DOCKER_HOST_INCOMING_DIR}`.
3. Ingestion moves files into `${DOCKER_HOST_IMPORTED_FILES_DIR}`.
4. Imported files become canonical storage.

Relevant references:

- `containers/compose-minio.yaml` mounts `${DOCKER_HOST_INCOMING_DIR}:/incoming`.
- `containers/compose-base.yaml` mounts `${DOCKER_HOST_IMPORTED_FILES_DIR}` into `base`, `celery`, and `celery-beat`.
- `docs/ingestion/sinan-storage.md` documents `DOCKER_HOST_SINAN_ROOT`, `DOCKER_HOST_IMPORTED_FILES_DIR`, and `DOCKER_HOST_INCOMING_DIR`.
- `mover_sinan_data.py` defaults `--imported-base` from `DOCKER_HOST_IMPORTED_FILES_DIR`.

Main issue resolution:

- `DOCKER_HOST_UPLOADED_FILES_DIR` is now active because uploaded storage is still used for ingestion collision checks.
- `DOCKER_HOST_TEMP_PARQUET_DIR` no longer appears in compose mounts.

This removes the empty-source bind mount failure that compose produced before Phase 1.

### Legacy Django Path Settings

`MEDIA_ROOT`, `IMPORTED_FILES`, `TEMP_FILES_DIR`, and `STORAGE` were leftovers from older storage wiring and have been removed from active settings/template surfaces.

`IMPORTED_FILES_DIR` is now the container-facing imported-files setting. It is intentionally separate from host-side `DOCKER_HOST_IMPORTED_FILES_DIR`:

- Prefer `DOCKER_HOST_IMPORTED_FILES_DIR` for host paths.
- Prefer a container-facing setting such as `/opt/services/ingestion/sinan/imported` for paths used inside containers.
- Avoid reintroducing `IMPORTED_FILES` unless there is a documented compatibility need.

## Removal Plan

### Phase 1: Make Compose Deterministic

Goal: solve the immediate broken/ambiguous compose issue.

1. Decide the replacement for `DOCKER_HOST_UPLOADED_FILES_DIR`.
   - Option A: restore it as an active variable derived from `${DOCKER_HOST_SINAN_ROOT}/uploaded` if uploaded storage is still required.
   - Option B: remove the uploaded mounts from `base`, `celery`, and `celery-beat` if upload collision checks and old uploaded storage are retired.
   - Option C: inline a compose default, for example `${DOCKER_HOST_UPLOADED_FILES_DIR:-${DOCKER_HOST_SINAN_ROOT}/uploaded}`, only if nested interpolation is verified with the project compose version.

2. Decide whether `/tmp/dbf_parquet` is still needed.
   - If yes, restore `DOCKER_HOST_TEMP_PARQUET_DIR` as an active variable.
   - If no, remove the `DOCKER_HOST_TEMP_PARQUET_DIR:/tmp/dbf_parquet` mounts from `celery` and `celery-beat`, and keep temporary parquet work inside container-local `/tmp`.

3. Validate compose resolution:
   - `docker compose --env-file .envs/.env -f containers/compose-base.yaml config`
   - Include any environment-specific compose overlays used by staging/prod.

### Phase 2: Remove Safe Residual Env Entries

Remove these commented entries from `.envs/.env` after Phase 1:

- `MEDIA_ROOT`
- `IMPORTED_FILES`
- `TEMP_FILES_DIR`
- `STORAGE`
- `DOCKER_HOST_DBF_SINAN`
- `DOCKER_HOST_PQDIR`
- `DOCKER_HOST_INCIDENCE_MAPS`
- `DOCKER_HOST_STATIC`
- `DOCKER_HOST_MEDIA_ROOT`

Then remove matching unused template entries from `.envs/.env.tpl`:

- `MEDIA_ROOT`
- `IMPORTED_FILES`
- `TEMP_FILES_DIR`
- `STORAGE`
- `DOCKER_HOST_DBF_SINAN`
- `DOCKER_HOST_PQDIR` if added or present in other branches/templates
- `DOCKER_HOST_INCIDENCE_MAPS`
- `DOCKER_HOST_STATIC`
- `DOCKER_HOST_MEDIA_ROOT` if added or present in other branches/templates

Keep these template entries:

- `DBF_SINAN`
- `DOCKER_HOST_IMPORTED_FILES_DIR`
- `DOCKER_HOST_UPLOADED_FILES_DIR` only if Phase 1 keeps it active
- `DOCKER_HOST_SHAPEFILES_DIR`
- `DOCKER_HOST_TIFFS_DIR`

### Phase 3: Clean Stale Code Comments

Remove stale commented settings from `AlertaDengue/ad_main/settings/base.py` once the env cleanup is merged:

- `# MEDIA_ROOT = os.getenv("MEDIA_ROOT")`
- `# IMPORTED_FILES = os.getenv("IMPORTED_FILES")`
- `# TEMP_FILES_DIR = os.getenv("TEMP_FILES_DIR")`
- `# DATA_DIR = PROJECT_ROOT.parent.parent / os.getenv("STORAGE", "")`

Do not remove `DBF_SINAN` without replacing upload storage and log paths.

### Phase 4: Align Ingestion Path Naming

Recommended follow-up:

1. Add an explicit container-facing setting for imported files, for example:
   - `IMPORTED_FILES_DIR=/opt/services/ingestion/sinan/imported`
2. Update `.envs/.env.tpl` and docs to distinguish:
   - Host path: `DOCKER_HOST_IMPORTED_FILES_DIR`
   - Container path: `IMPORTED_FILES_DIR`
3. Update `AlertaDengue/ingestion/services.py` to avoid the undocumented fallback path.

This avoids confusing the removed legacy `IMPORTED_FILES` variable with the active ingestion setting.

### Phase 5: Remove Host Residual Directories

Only after a deployed release has run successfully with the cleaned compose configuration:

1. Snapshot or list each candidate directory before deletion.
2. Confirm no systemd units, cron jobs, or deployment scripts outside this repository reference the path.
3. Remove retired host directories in a maintenance window.

Repo-side helper:

- `scripts/audit-retired-storage-paths.sh`
- Purpose: list candidate and protected paths, show local disk usage when present, scan repo and common system locations for references, and print manual removal commands without executing them.

Candidate host directories from commented variables:

- `/opt/data/staging/sftp2/alertadengue`
- `/opt/data/staging/sftp2/alertadengue/dbfs_parquet`
- `/opt/data/staging/img/incidence_maps`
- `/opt/services/staging_AlertaDengue/staticfiles`
- `/opt/data/staging/sftp2/alertadengue/uploaded`

Do not remove these without explicit migration/backup confirmation:

- `/mnt/storagebox-staging/sinan`
- `/mnt/storagebox-staging/sinan/imported`
- `/opt/data/staging/sinan/incoming/`
- `/opt/data/staging/shapefiles`
- `/opt/data/staging/tiffs`
- `/opt/data/staging/episcanner`
- `${HOST_PGDATA}`

## Verification Checklist

- `rg --glob '!node_modules/**' --glob '!.git/**' --glob '!docs/unused-volume-path-cleanup-plan.md' 'MEDIA_ROOT|IMPORTED_FILES\\b|TEMP_FILES_DIR|STORAGE|DOCKER_HOST_DBF_SINAN|DOCKER_HOST_PQDIR|DOCKER_HOST_INCIDENCE_MAPS|DOCKER_HOST_STATIC|DOCKER_HOST_MEDIA_ROOT|DOCKER_HOST_TEMP_PARQUET_DIR|/IMPORTED_FILES' .envs containers AlertaDengue docs README_MAPSERVER.md`
- `docker compose --env-file .envs/.env -f containers/compose-base.yaml config`
- `docker compose --env-file .envs/.env -f containers/compose-base.yaml -f containers/compose-staging.yaml config`
- `bash scripts/audit-retired-storage-paths.sh`
- Run ingestion unit tests that cover source-path resolution and mover behavior.
- Run upload tests or a manual upload smoke test if `DBF_SINAN` or uploaded-path mounts are changed.
- Run a MinIO materializer smoke test if incoming storage is changed.

## Recommended First Change Set

The smallest safe change set for issue 950 is:

1. Fix `DOCKER_HOST_UPLOADED_FILES_DIR` and `DOCKER_HOST_TEMP_PARQUET_DIR` so compose no longer references commented or undefined variables.
2. Remove only variables proven to be residual from `.envs/.env` and `.envs/.env.tpl`.
3. Remove stale commented Django settings.
4. Leave strong dependency paths intact.
