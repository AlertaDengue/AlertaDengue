# PostgreSQL backup and restore with pgBackRest

This repository uses PostgreSQL 14 and pgBackRest with a sidecar container.
The committed pgBackRest configuration is a secret-free template. Runtime
configs are rendered under `.runtime/pgbackrest/` and are not committed.

Both `postgres` and `pgbackrest` mount the same rendered config at
`/etc/pgbackrest/pgbackrest.conf`. `pg1-path` must match PostgreSQL
`data_directory`, which is `/var/lib/postgresql/data` in these compose files.

## Steady-state backups

Bootstrap a repository for an existing cluster:

```bash
makim pgbackrest.bootstrap --profile dev
```

Run a full backup:

```bash
makim pgbackrest.backup-full --profile dev
```

Inspect the repository:

```bash
docker compose \
  --env-file .envs/.env \
  --file containers/compose-base.yaml \
  --file containers/compose-dev.yaml \
  --file containers/compose-pgbackrest.yaml \
  --project-name infodengue-dev \
  exec -T pgbackrest pgbackrest --stanza=dev info
```

`bootstrap` is only idempotent for the same PostgreSQL cluster and repository.
If the PostgreSQL system identifier changes, create a fresh repository instead
of reusing the old one.

## Runtime configuration

Render a normal config:

```bash
makim pgbackrest.render-conf --profile staging
```

Render the restore-only config used to refresh staging from production:

```bash
makim pgbackrest.render-restore-conf
```

Generated files:

```text
.runtime/pgbackrest/pgbackrest-dev.conf
.runtime/pgbackrest/pgbackrest-staging.conf
.runtime/pgbackrest/pgbackrest-prod.conf
.runtime/pgbackrest/pgbackrest-restore-prod-to-staging.conf
```

The renderer uses `PSQL_USER` from `.envs/.env`. It rejects invalid stanza
names, empty PostgreSQL users, and relative repository paths. Generated files
are written atomically with mode `0640`.

If pgBackRest secrets are introduced later, pass them through Docker secrets or
another file-based secret source. Do not commit secrets into the template.

## Container model

Shared paths:

```text
/var/lib/postgresql/data
/var/run/postgresql
/var/lib/pgbackrest
/var/log/pgbackrest
```

Normal mode:

1. PostgreSQL archives WAL with `archive_mode=on`.
2. pgBackRest stores backups and WAL in the environment repository.

Restore mode for production-to-staging refresh:

1. The transferred production repository is mounted read-only at `/var/lib/pgbackrest-source`.
2. The restore config points `repo1-path` at `/var/lib/pgbackrest-source`.
3. PostgreSQL starts with `PG_STANZA=prod` and `PG_ARCHIVE_MODE=off`.
4. Recovery still requires archived WAL from `archive/prod`, even after a full backup.
5. After validation, restore-mode containers stop and staging returns to its own empty repository.

Do not keep `backup/prod` and `backup/staging` in the same permanent
repository.

## Restore workflows

`makim pgbackrest.restore-profile-backup --profile <profile> --backup-set <full-backup-label> --confirm RESTORE-PROFILE-BACKUP`
restores an explicit full backup inside one environment. It runs a read-only
repository preflight, validates and canonicalizes `HOST_PGDATA`, prints the
deletion target before cleanup, and never uses unguarded `rm -rf`.

Production-to-staging refresh is a separate workflow. It uses a transferred
production repository, restore-only config, and the dedicated task:

```bash
makim pgbackrest.refresh-staging-from-prod \
  --source-repo /srv/backups/pgbackrest-prod-repo \
  --backup-set <prod-backup-label> \
  --confirm REFRESH-STAGING-FROM-PROD
```

`restore-profile-backup` reads and restores from the selected environment's own
repository and stanza. `refresh-staging-from-prod` reads from a transferred
production repository mounted read-only, restores stanza `prod` into staging,
validates the database, then creates a new `staging` stanza and full staging
backup in a separate repository.

Do not:

1. Copy live `PGDATA`.
2. Run cross-environment restores without an explicit backup label.
3. Remove `backup_label` or `recovery.signal` manually.
4. Run migrations before restore validation.

## Validation

After restore, validate PostgreSQL before starting application services:

```sql
SELECT pg_is_in_recovery();
SELECT current_setting('data_directory');
SELECT pg_database_size(current_database());
SELECT to_regclass('"Dengue_global"."Municipio"');
```

Compare database size with the source backup or the source environment; do not
rely on one hardcoded expected size.

The smoke test uses a temporary table inside a transaction so it does not leave
permanent objects behind.

## UID and GID requirements

Both PostgreSQL and pgBackRest images align the container `postgres` user with
host numeric IDs from `HOST_UID` and `HOST_GID`. The host paths and Docker
volumes used for `PGDATA` and runtime configs must be readable and writable by
those numeric IDs.
```

> **Incremental Backup Warning**: pgBackRest incrementals depend on prior full backups + WAL archive. Always transfer the **entire repository**, not individual files.

---

## Troubleshooting (Dev)

### `gosu: operation not permitted`

**Cause**: Container lacks privileges to switch users via `gosu`.

**Fix**: Update `.makim.yaml` to use `su` instead:
```yaml
# Replace in stanza-create, backup-full, restore-profile-backup tasks:
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

# If recovery does not complete, inspect pgBackRest logs and the selected
# backup/archive metadata instead of removing signal files manually.
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
makim pgbackrest.restore-profile-backup \
  --profile dev \
  --backup-set 20260711-123456F \
  --confirm RESTORE-PROFILE-BACKUP
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
makim pgbackrest.restore-profile-backup \
  --profile dev \
  --backup-set 20260711-123456F \
  --confirm RESTORE-PROFILE-BACKUP
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
