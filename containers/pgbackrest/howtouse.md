````md
# pgBackRest Management Guide for AlertaDengue

This guide explains how to manage PostgreSQL backups in AlertaDengue using **pgBackRest**, **Makim**, and **Docker Compose**.

The current design uses a dedicated **`pgbackrest` sidecar container** that shares:

- the live PostgreSQL data directory
- the PostgreSQL Unix socket
- a Docker-managed backup repository volume
- a Docker-managed log volume

This allows pgBackRest to run **outside** the database container while still accessing PostgreSQL locally through the shared socket.

---

## Architecture Overview

### Services

- **`postgres`**
  Runs the PostgreSQL server and owns the live database cluster.

- **`pgbackrest`**
  Runs pgBackRest commands such as:
  - `stanza-create`
  - `check`
  - `backup`
  - `restore`

### Shared storage

The Compose setup uses:

- **Bind mount**
  - `${HOST_PGDATA}:/var/lib/postgresql/data`
  - this is the live PostgreSQL cluster directory
  - it is shared between `postgres` and `pgbackrest`

- **Named Docker volumes**
  - `pgsocket:/var/run/postgresql`
  - `pgbackrest_repo:/var/lib/pgbackrest`
  - `pgbackrest_logs:/var/log/pgbackrest`

Important:
- `pgbackrest_repo` and `pgbackrest_logs` are **Docker volumes**, managed by Docker
- they are **not** regular host paths from `.env`
- if you want to inspect or copy them, use `docker volume inspect` or a helper container

---

## Initialization (Bootstrap)

Before taking backups, initialize the backup system.

```bash
makim pgbackrest.bootstrap --profile <profile>
````

Example:

```bash
makim pgbackrest.bootstrap --profile dev
```

### What bootstrap does

1. Starts `postgres` and `pgbackrest`
2. Renders `pgbackrest.conf`
3. Copies the config into the **`pgbackrest` container**
4. Creates the stanza
5. Runs `pgbackrest check`

### Supported profiles

* `dev`
* `staging`
* `prod`

---

## Manual Backup

To run a full backup manually:

```bash
makim pgbackrest.backup-full --profile <profile>
```

Example:

```bash
makim pgbackrest.backup-full --profile prod
```

This performs:

1. bootstrap pre-checks
2. a full backup
3. expiration according to retention settings

---

## Restore

To restore the latest backup for an environment:

```bash
makim pgbackrest.restore-latest --profile <profile>
```

Example:

```bash
makim pgbackrest.restore-latest --profile dev
```

### What restore does

1. Stops PostgreSQL
2. Removes current contents of `PGDATA`
3. Restores the latest backup from the pgBackRest repository
4. Starts PostgreSQL again

---

## Post-Restore Validation

After restore, validate that the database is writable and no longer in recovery mode:

```bash
makim pgbackrest.smoke-test --profile <profile>
```

Example:

```bash
makim pgbackrest.smoke-test --profile dev
```

This smoke test:

* waits for PostgreSQL to become ready
* checks `pg_is_in_recovery()`
* creates a small test table
* inserts a row
* verifies the row count

---

## Scheduling Backups

Scheduled backups are managed with **systemd user timers** on the host.

### Add a schedule

```bash
makim pgbackrest.backup-schedule-add \
  --profile <profile> \
  --on_calendar "<expression>"
```

Example:

```bash
makim pgbackrest.backup-schedule-add \
  --profile prod \
  --on_calendar "*-*-* 03:00:00"
```

You can also pass multiple schedules separated by semicolons:

```bash
makim pgbackrest.backup-schedule-add \
  --profile dev \
  --on_calendar "*-*-* 07:00:00;*-*-* 12:00:00;*-*-* 19:00:00"
```

### List timers

```bash
makim pgbackrest.backup-schedule-list
```

### Show logs

```bash
makim pgbackrest.backup-schedule-logs --profile <profile>
```

Example:

```bash
makim pgbackrest.backup-schedule-logs --profile dev
```

### Clean timers and unit files

```bash
makim pgbackrest.backup-schedule-clean
```

This removes:

* pgBackRest timer unit files
* template service files
* stale failed timer state

---

## Configuration Files

Environment-specific pgBackRest config files live here:

* `containers/pgbackrest/pgbackrest-dev.conf`
* `containers/pgbackrest/pgbackrest-staging.conf`
* `containers/pgbackrest/pgbackrest-prod.conf`

Example:

```ini
[global]
repo1-path=/var/lib/pgbackrest
log-path=/var/log/pgbackrest
spool-path=/var/lib/pgbackrest/spool
lock-path=/var/lib/pgbackrest/spool
repo1-retention-full=2
repo1-retention-full-type=count
start-fast=y
process-max=2

[dev]
pg1-path=/var/lib/postgresql/data
pg1-socket-path=/var/run/postgresql
pg1-user=postgres
```

### Apply configuration changes

After editing a config file, rerun bootstrap:

```bash
makim pgbackrest.bootstrap --profile <profile>
```

---

## Storage Layout

### Live database

The live PostgreSQL data directory is shared via bind mount:

```yaml
${HOST_PGDATA}:/var/lib/postgresql/data
```

This is the active cluster, not the backup repository.

### Backup repository

The backup repository is stored in the Docker-managed named volume:

```yaml
pgbackrest_repo:/var/lib/pgbackrest
```

### Backup logs

Logs are stored in the Docker-managed named volume:

```yaml
pgbackrest_logs:/var/log/pgbackrest
```

### PostgreSQL socket

The PostgreSQL Unix socket is shared using:

```yaml
pgsocket:/var/run/postgresql
```

This is what allows the sidecar to connect to PostgreSQL without TCP or SSH.

---

## Inspect Docker Volumes

To inspect the pgBackRest repository volume:

```bash
docker volume inspect infodengue-dev_pgbackrest_repo
```

To inspect the log volume:

```bash
docker volume inspect infodengue-dev_pgbackrest_logs
```

To browse the repository contents using a temporary container:

```bash
docker run --rm -it \
  -v infodengue-dev_pgbackrest_repo:/repo \
  alpine sh
```

Inside that container:

```bash
ls -lah /repo
find /repo -maxdepth 3 -type d | sort
```

To browse logs:

```bash
docker run --rm -it \
  -v infodengue-dev_pgbackrest_logs:/logs \
  alpine sh
```

Inside:

```bash
ls -lah /logs
```

---

## Export the Backup Repository to Another Server

Because the backup repository is stored in a **Docker named volume**, the correct way to export it is to archive the volume contents through a helper container.

### 1. Create a tarball from the Docker volume

Example for `dev`:

```bash
docker run --rm \
  -v infodengue-dev_pgbackrest_repo:/source:ro \
  -v "$PWD":/backup \
  alpine sh -lc 'cd /source && tar -czf /backup/pgbackrest-repo-dev.tar.gz .'
```

Optionally export logs too:

```bash
docker run --rm \
  -v infodengue-dev_pgbackrest_logs:/source:ro \
  -v "$PWD":/backup \
  alpine sh -lc 'cd /source && tar -czf /backup/pgbackrest-logs-dev.tar.gz .'
```

### 2. Transfer the archive to another server

```bash
scp pgbackrest-repo-dev.tar.gz user@target-server:/tmp/
```

If needed:

```bash
scp pgbackrest-logs-dev.tar.gz user@target-server:/tmp/
```

---

## Import the Backup Repository on Another Server

### 1. Ensure the destination stack exists

Bring up the target environment at least once so Docker creates the volumes and containers.

Example:

```bash
docker compose \
  --env-file .envs/.env \
  --file containers/compose-base.yaml \
  --file containers/compose-prod.yaml \
  --file containers/compose-pgbackrest.yaml \
  --project-name infodengue-prod \
  up -d postgres pgbackrest
```

### 2. Inspect the target volume name

Example:

```bash
docker volume inspect infodengue-prod_pgbackrest_repo
```

### 3. Extract the archive into the target Docker volume

```bash
docker run --rm \
  -v infodengue-prod_pgbackrest_repo:/target \
  -v /tmp:/backup \
  alpine sh -lc 'cd /target && tar -xzf /backup/pgbackrest-repo-dev.tar.gz'
```

If you also transferred logs:

```bash
docker run --rm \
  -v infodengue-prod_pgbackrest_logs:/target \
  -v /tmp:/backup \
  alpine sh -lc 'cd /target && tar -xzf /backup/pgbackrest-logs-dev.tar.gz'
```

### 4. Re-run bootstrap on the target environment

```bash
makim pgbackrest.bootstrap --profile prod
```

### 5. Restore from the transferred repository

```bash
makim pgbackrest.restore-latest --profile prod
```

### 6. Validate the restore

```bash
makim pgbackrest.smoke-test --profile prod
```

---

## Safer Remote Copy Alternative

If you want to stream directly to another host without keeping a local archive:

```bash
docker run --rm \
  -v infodengue-dev_pgbackrest_repo:/source:ro \
  alpine sh -lc 'cd /source && tar -czf - .' \
  | ssh user@target-server 'cat > /tmp/pgbackrest-repo-dev.tar.gz'
```

Then, on the target server:

```bash
docker run --rm \
  -v infodengue-prod_pgbackrest_repo:/target \
  -v /tmp:/backup \
  alpine sh -lc 'cd /target && tar -xzf /backup/pgbackrest-repo-dev.tar.gz'
```

---

## Recommended Operational Flow

### First-time setup

```bash
makim pgbackrest.bootstrap --profile dev
```

### Run a manual backup

```bash
makim pgbackrest.backup-full --profile dev
```

### Add a daily timer

```bash
makim pgbackrest.backup-schedule-add \
  --profile dev \
  --on_calendar "*-*-* 03:00:00"
```

### List timers

```bash
makim pgbackrest.backup-schedule-list
```

### Inspect logs

```bash
makim pgbackrest.backup-schedule-logs --profile dev
```

### Restore latest backup

```bash
makim pgbackrest.restore-latest --profile dev
makim pgbackrest.smoke-test --profile dev
```

---

## Notes

* `pgbackrest_repo` and `pgbackrest_logs` are Docker volumes, not normal host directories.
* `HOST_PGDATA` is the live database bind mount and must be handled carefully during restore.
* scheduled backups rely on systemd user timers, so stale timer files may need cleanup if the task implementation changes.
* after changing pgBackRest config files, rerun bootstrap.

---
````  
