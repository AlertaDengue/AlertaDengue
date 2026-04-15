# pgBackRest Backup System — AlertaDengue

This document describes how to manage PostgreSQL backups in **AlertaDengue** using:

* **pgBackRest**
* **Makim**
* **containers-sugar**
* **Docker (named volumes)**

---

## Architecture

We use a **sidecar pattern**:

| Service      | Responsibility                         |
| ------------ | -------------------------------------- |
| `postgres`   | Runs PostgreSQL                        |
| `pgbackrest` | Executes backup and restore operations |

### Shared resources

| Path                       | Type                              | Description       |
| -------------------------- | --------------------------------- | ----------------- |
| `/var/lib/postgresql/data` | bind mount                        | Live database     |
| `/var/run/postgresql`      | Docker volume (`pgsocket`)        | Unix socket       |
| `/var/lib/pgbackrest`      | Docker volume (`pgbackrest_repo`) | Backup repository |
| `/var/log/pgbackrest`      | Docker volume (`pgbackrest_logs`) | Logs              |

---

## Storage Model (Important)

* `pgbackrest_repo` → **Docker-managed volume**
* `pgbackrest_logs` → **Docker-managed volume**
* NOT host paths

---

## Initialization (Bootstrap)

```bash
makim pgbackrest.bootstrap --profile dev
```

### What it does

* Starts containers via **containers-sugar**
* Renders `pgbackrest.conf`
* Injects config into `pgbackrest`
* Creates stanza
* Runs `pgbackrest check`

---

## Manual Backup

```bash
makim pgbackrest.backup-full --profile dev
```

Includes:

* Full backup
* Retention cleanup

---

## Restore

```bash
makim pgbackrest.restore-latest --profile dev
```

### Flow

1. Stop PostgreSQL
2. Wipe `PGDATA`
3. Restore latest backup
4. Start PostgreSQL

---

## Validation (Smoke Test)

```bash
makim pgbackrest.smoke-test --profile dev
```

Checks:

* DB is running
* Not in recovery mode
* Writable

---

## Scheduling Backups

### Add schedule

```bash
makim pgbackrest.backup-schedule-add \
  --profile dev \
  --on_calendar "*-*-* 03:00:00"
```

Multiple schedules:

```bash
"--on_calendar *-*-* 07:00:00;*-*-* 12:00:00"
```

---

### List schedules

```bash
makim pgbackrest.backup-schedule-list
```

---

### Logs

```bash
makim pgbackrest.backup-schedule-logs --profile dev
```

---

### Cleanup schedules

```bash
makim pgbackrest.backup-schedule-clean
```

---

## Inspect Backup Repository

Find volume:

```bash
docker volume ls | grep pgbackrest
```

Access it:

```bash
docker run --rm -it \
  -v infodengue-dev_pgbackrest_repo:/repo \
  alpine sh
```

---

## Export Backup

Create archive from Docker volume:

```bash
docker run --rm \
  -v infodengue-dev_pgbackrest_repo:/source:ro \
  -v $(pwd):/backup \
  alpine sh -c "cd /source && tar -czf /backup/pgbackrest-repo-dev.tar.gz ."
```

---

## Transfer Backup

```bash
scp pgbackrest-repo-dev.tar.gz user@target:/tmp/
```

---

## Import Backup (Correct)

```bash
docker run --rm \
  -v infodengue-dev_pgbackrest_repo:/target \
  -v /tmp:/backup \
  alpine sh -c "ls -lah /backup && cd /target && tar -xzf /backup/pgbackrest-repo-dev.tar.gz"
```

### Debug tip

```bash
ls -lah /tmp
```

---

## Streaming Transfer (Recommended)

Avoid temp files:

```bash
docker run --rm \
  -v infodengue-dev_pgbackrest_repo:/source:ro \
  alpine sh -c "cd /source && tar -czf - ." \
  | ssh user@target 'cat > /tmp/pgbackrest-repo-dev.tar.gz'
```

---

## Restore on Target

```bash
makim pgbackrest.bootstrap --profile dev
makim pgbackrest.restore-latest --profile dev
makim pgbackrest.smoke-test --profile dev
```

---

## Configuration

File:

```
containers/pgbackrest/pgbackrest-dev.conf
```

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

---

## Apply Config Changes

```bash
makim pgbackrest.bootstrap --profile dev
```

---

## Typical Workflow

```bash
makim pgbackrest.bootstrap --profile dev
makim pgbackrest.backup-full --profile dev
makim pgbackrest.backup-schedule-add --profile dev --on_calendar "*-*-* 03:00:00"
makim pgbackrest.restore-latest --profile dev
makim pgbackrest.smoke-test --profile dev
```

---

## Troubleshooting

### Container logs

```bash
docker logs infodengue-dev-postgres-1
docker logs infodengue-dev-pgbackrest-1
```

### Scheduled job logs

```bash
makim pgbackrest.backup-schedule-logs --profile dev
```

---

## Key Concepts

* **Stanza** → environment-specific backup config (`dev`, `staging`, `prod`)
* **WAL Archiving** → continuous backup
* **Retention** → controlled by `repo1-retention-full`
* **Sidecar model** → backup logic isolated from DB

---

## Best Practices

* Never manipulate `pgbackrest_repo` directly on host
* Always use `docker run -v volume:/path`
* Prefer streaming backups for migrations
* Always run `smoke-test` after restore
* Clean systemd timers when updating schedules

---

## Summary

| Task      | Command                                |
| --------- | -------------------------------------- |
| Bootstrap | `makim pgbackrest.bootstrap`           |
| Backup    | `makim pgbackrest.backup-full`         |
| Restore   | `makim pgbackrest.restore-latest`      |
| Validate  | `makim pgbackrest.smoke-test`          |
| Schedule  | `makim pgbackrest.backup-schedule-add` |

---
