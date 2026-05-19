# PostgreSQL Backup & Restore with pgBackRest — AlertaDengue

> **Production-ready backup orchestration** using pgBackRest + Makim + Docker sidecar architecture.  
> **Environment-agnostic**: same workflow for `dev`, `staging`, `prod` via dynamic configuration.

---

## Quick Start (Dev Environment)

```bash
# 1. Bootstrap: render config + create stanza + validate
makim pgbackrest.bootstrap --profile dev

# 2. Run a full backup
makim pgbackrest.backup-full --profile dev

# 3. Verify backup status
docker exec infodengue-dev-postgres-1 \
  su - postgres -c "pgbackrest --stanza=dev info"

# 4. Test restore workflow (optional, destructive)
makim pgbackrest.restore-latest --profile dev
makim pgbackrest.smoke-test --profile dev
```

All commands use `--profile dev` by default. Replace with `staging` or `prod` for other environments.

---

## Architecture

### Sidecar Pattern

```
┌─────────────────┐     ┌─────────────────┐
│   postgres      │────▶│   pgbackrest    │
│   (PostgreSQL)  │ WAL │   (backup mgr)  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐ ┌─────────────────┐
│ pgsocket        │ │ pgbackrest_repo │
│ (shared socket) │ │ (Docker volume) │
└─────────────────┘ └─────────────────┘
```

### Shared Resources

| Resource | Type | Purpose |
|----------|------|---------|
| `/var/lib/postgresql/data` | bind mount | Live PostgreSQL data |
| `/var/run/postgresql` | Docker volume (`pgsocket`) | Unix socket for local connections |
| `/var/lib/pgbackrest` | Docker volume (`pgbackrest_repo`) | Backup repository (WAL + backups) |
| `/var/log/pgbackrest` | Docker volume (`pgbackrest_logs`) | pgBackRest operation logs |

> **Storage Model**: All pgBackRest data lives in **Docker-managed volumes**, not host paths. Never manipulate these volumes directly on the host.

---

## Requirements

| Dependency | Minimum Version | Purpose |
|------------|----------------|---------|
| Docker / Docker Compose | v20.10+ | Container orchestration |
| `containers-sugar` | latest | AlertaDengue compose wrapper |
| Makim | ≥ 1.29.0 | Task automation with Jinja templating |
| PostgreSQL | 15+ | Database engine (pgBackRest compatible) |

### Environment Setup

```bash
# Activate your conda environment (provides sugar + makim)
conda activate alertadengue-dev

# Verify tools are available
which makim sugar docker
```

---

## Configuration

### Dynamic Configuration Engine

The `render-conf` task generates `pgbackrest.conf` on-the-fly using profile-aware templating:

```python
# Internal logic (simplified)
profile = os.environ.get("PROFILE", "dev")  # dev | staging | prod
cfg = f"""
[global]
repo1-path=/var/lib/pgbackrest
repo1-retention-full=2

[{profile}]  # ← Dynamic stanza name
pg1-path=/var/lib/postgresql/data
pg1-socket-path=/var/run/postgresql
pg1-user=postgres
"""
```

**Benefit**: No hardcoded environments. One config template serves all profiles without leakage.

### PostgreSQL Settings (Required)

Ensure these are set in your PostgreSQL configuration (`postgresql.conf` or via env):

```ini
archive_mode = on
archive_command = 'pgbackrest --config=/etc/pgbackrest/pgbackrest.conf --stanza=${PROFILE} archive-push %p'
wal_level = replica
```

> The `${PROFILE}` variable is injected at runtime by the Makim task.

---

## Makim Tasks Reference (Dev-Focused)

### Core Workflow

| Task | Command | Description |
|------|---------|-------------|
| **Bootstrap** | `makim pgbackrest.bootstrap --profile dev` | Render config + create stanza + validate (one-time setup) |
| **Backup** | `makim pgbackrest.backup-full --profile dev` | Execute full backup + apply retention policy |
| **Restore** | `makim pgbackrest.restore-latest --profile dev` | Stop DB → wipe PGDATA → restore latest backup → start DB |
| **Validate** | `makim pgbackrest.smoke-test --profile dev` | Post-restore check: DB writable, not in recovery mode |

### Configuration Management

| Task | Command | Description |
|------|---------|-------------|
| Render config (container) | `makim pgbackrest.render-conf --profile dev --target container` | Generate and inject `pgbackrest.conf` into pgbackrest container |
| Render config (host) | `makim pgbackrest.render-conf --profile dev --target host --src ./pgbackrest.conf` | Output config to host filesystem for inspection |

### Scheduling (systemd user timers)

| Task | Command | Description |
|------|---------|-------------|
| Add schedule | `makim pgbackrest.backup-schedule-add --profile dev --on-calendar "*-*-* 03:00:00"` | Create systemd timer for automated backups |
| Multiple schedules | `--on-calendar "*-*-* 02:00:00;*-*-* 14:00:00"` | Semicolon-separated OnCalendar expressions |
| List timers | `makim pgbackrest.backup-schedule-list` | Show active pgBackRest timers |
| View logs | `makim pgbackrest.backup-schedule-logs --profile dev` | Show recent journalctl logs for scheduled jobs |

### Utility

| Task | Command | Description |
|------|---------|-------------|
| Stanza create | `makim pgbackrest.stanza-create --profile dev` | Initialize backup namespace (normally called via bootstrap) |
| Inspect repo | `docker exec infodengue-dev-postgres-1 su - postgres -c "pgbackrest --stanza=dev info"` | View backup sets, WAL status, retention |

---

## Typical Dev Workflow

```bash
# Initial setup (run once)
makim pgbackrest.bootstrap --profile dev

# Daily operation
makim pgbackrest.backup-full --profile dev

# Verify backups exist
docker exec infodengue-dev-postgres-1 \
  su - postgres -c "pgbackrest --stanza=dev info"

# Test restore (optional, wipes PGDATA)
makim pgbackrest.restore-latest --profile dev
makim pgbackrest.smoke-test --profile dev

# Automate: schedule daily 3AM backups
makim pgbackrest.backup-schedule-add \
  --profile dev \
  --on-calendar "*-*-* 03:00:00"
```

---

## Backup Transfer & Migration

### Export Repository (Source Server)

```bash
docker run --rm \
  -v infodengue-dev_pgbackrest_repo:/source:ro \
  -v "$PWD":/backup \
  alpine sh -c "cd /source && tar -czf /backup/pgbackrest-repo-dev.tar.gz ."
```

### Transfer to Target

```bash
# Option A: SCP (simple)
scp pgbackrest-repo-dev.tar.gz user@target:/tmp/

# Option B: Streaming (no temp file, recommended)
docker run --rm \
  -v infodengue-dev_pgbackrest_repo:/source:ro \
  alpine sh -c "cd /source && tar -czf - ." \
  | ssh user@target 'cat > /tmp/pgbackrest-repo-dev.tar.gz'
```

### Import on Target Server

```bash
docker run --rm \
  -v infodengue-dev_pgbackrest_repo:/target \
  -v /tmp:/backup \
  alpine sh -c "cd /target && tar -xzf /backup/pgbackrest-repo-dev.tar.gz"
```

### Post-Import Setup (Target)

```bash
# Bootstrap the target environment
makim pgbackrest.bootstrap --profile dev

# Restore and validate
makim pgbackrest.restore-latest --profile dev
makim pgbackrest.smoke-test --profile dev
```

> **Incremental Backup Warning**: pgBackRest incrementals depend on prior full backups + WAL archive. Always transfer the **entire repository**, not individual files.

---

## Troubleshooting (Dev)

### `gosu: operation not permitted`

**Cause**: Container lacks privileges to switch users via `gosu`.

**Fix**: Update `.makim.yaml` to use `su` instead:
```yaml
# Replace in stanza-create, backup-full, restore-latest tasks:
# FROM: gosu postgres pgbackrest ...
# TO:
su - postgres -c "pgbackrest --stanza=$PROFILE ..."
```

Or patch inline:
```bash
sed -i 's/gosu postgres pgbackrest/su - postgres -c "pgbackrest/g; s/;$/";/g' .makim.yaml
```

### WAL Archiving Not Working

```bash
# Check PostgreSQL logs
docker logs infodengue-dev-postgres-1 2>&1 | grep -i archive

# Verify pgbackrest binary exists in postgres container
docker exec infodengue-dev-postgres-1 which pgbackrest

# Test archive command manually
docker exec infodengue-dev-postgres-1 \
  su - postgres -c "pgbackrest --stanza=dev check"
```

If logs show `Permission denied` for files such as
`/var/lib/pgbackrest/archive/prod/archive.info` or `backup.info`, verify that
the repository is owned by the PostgreSQL runtime user:

```bash
docker exec infodengue-prod-postgres-1 \
  find /var/lib/pgbackrest ! -user postgres -o ! -group postgres
```

The pgBackRest sidecar must run as the same `HOST_UID:HOST_GID` used by the
postgres container. If an older root-run sidecar already created repository
files, stop backup activity and repair ownership once:

```bash
docker exec -u root infodengue-prod-postgres-1 \
  chown -R postgres:postgres /var/lib/pgbackrest /var/log/pgbackrest

docker exec infodengue-prod-postgres-1 \
  su - postgres -c "pgbackrest --stanza=prod check"
```

### Backup Repository Empty / "no valid backups"

```bash
# Force a new full backup
makim pgbackrest.backup-full --profile dev

# Verify retention settings in config
docker exec infodengue-dev-postgres-1 \
  cat /etc/pgbackrest/pgbackrest.conf | grep retention
```

### Restore Stuck in Recovery Mode

```bash
# Check if PostgreSQL is still in recovery
docker exec infodengue-dev-postgres-1 \
  psql -U postgres -c "SELECT pg_is_in_recovery();"

# If true, check for recovery signals
docker exec infodengue-dev-postgres-1 \
  ls -la /var/lib/postgresql/data/ | grep -E "signal|conf"

# Remove recovery signals if restore is complete (dev only)
docker exec infodengue-dev-postgres-1 \
  bash -c 'rm -f /var/lib/postgresql/data/standby.signal /var/lib/postgresql/data/recovery.signal'
```

### systemd Timer Not Firing

```bash
# List user timers
systemctl --user list-timers | grep alertadengue-pgbackrest

# Check timer status
systemctl --user status alertadengue-pgbackrest-backup@dev.service

# View job logs
makim pgbackrest.backup-schedule-logs --profile dev
```

---

## Validation Checklist (Dev)

```bash
# Config rendered correctly
docker exec infodengue-dev-postgres-1 \
  grep -A4 "\[dev\]" /etc/pgbackrest/pgbackrest.conf

# Stanza is valid
docker exec infodengue-dev-postgres-1 \
  su - postgres -c "pgbackrest --stanza=dev check" && echo "✓ Stanza OK"

# Backup completed
docker exec infodengue-dev-postgres-1 \
  su - postgres -c "pgbackrest --stanza=dev info" | grep -q "backup set" && echo "✓ Backup exists"

# Restore + smoke test passed
makim pgbackrest.restore-latest --profile dev
makim pgbackrest.smoke-test --profile dev && echo "✓ Smoke test passed"
```

---

## Best Practices

| Practice | Rationale |
|----------|-----------|
| **Always use `--profile`** | Prevents cross-environment config leakage |
| **Test restores regularly** | Backup without restore validation is not a backup |
| **Keep `repo1-retention-full=2` minimum** | Ensures at least one fallback backup if latest is corrupted |
| **Never edit Docker volumes directly** | Use `docker run -v` or pgBackRest commands for integrity |
| **Run `smoke-test` after every restore** | Confirms DB is writable and application-ready |
| **Document custom systemd timers** | `backup-schedule-add` creates user timers; track them in runbooks |
| **Use streaming transfers for migrations** | Avoids temp files and reduces transfer time |

---

## Quick Reference Card

```bash
# SETUP
makim pgbackrest.bootstrap --profile dev

# BACKUP
makim pgbackrest.backup-full --profile dev
docker exec infodengue-dev-postgres-1 su - postgres -c "pgbackrest --stanza=dev info"

# RESTORE + VALIDATE
makim pgbackrest.restore-latest --profile dev
makim pgbackrest.smoke-test --profile dev

# SCHEDULE
makim pgbackrest.backup-schedule-add --profile dev --on-calendar "*-*-* 03:00:00"
makim pgbackrest.backup-schedule-list
makim pgbackrest.backup-schedule-logs --profile dev

# INSPECT
docker exec infodengue-dev-postgres-1 su - postgres -c "pgbackrest --stanza=dev check"
```

---

## Updating Configuration

When you modify `pgbackrest.conf` template or retention policies:

```bash
# Re-render and re-bootstrap (dev)
makim pgbackrest.bootstrap --profile dev

# Verify new settings applied
docker exec infodengue-dev-postgres-1 \
  cat /etc/pgbackrest/pgbackrest.conf | grep -E "retention|process-max"
```

> The `bootstrap` task is idempotent: safe to run multiple times.

---

*This workflow is environment-agnostic: replace `--profile dev` with `staging` or `prod` to apply the same commands across your infrastructure.*
