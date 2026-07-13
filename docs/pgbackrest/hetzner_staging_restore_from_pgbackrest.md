# Refresh staging from a production pgBackRest backup

This workflow restores a `prod` backup into staging without copying live
`PGDATA`. The restore uses stanza `prod` only while recovering the cloned
cluster. After recovery completes, staging gets a new empty repository and a
separate `staging` stanza.

Stanza names do not change database contents. Restoring `prod` into staging
produces a PostgreSQL cluster with production data; it only becomes the staging
database after recovery completes and you switch back to the normal staging
repository.

The transferred production repository is temporary and must stay read-only for
the full refresh. The permanent staging repository starts empty.

## 1. Create and validate a full production backup

Run on the production host:

```bash
cd /opt/services/infodengue

makim pgbackrest.bootstrap --profile prod
makim pgbackrest.backup-full --profile prod
```

Inspect the backup and choose an explicit backup label:

```bash
docker compose \
  --env-file .envs/.env \
  --file containers/compose-base.yaml \
  --file containers/compose-prod.yaml \
  --file containers/compose-pgbackrest.yaml \
  --project-name infodengue-prod \
  exec -T pgbackrest pgbackrest --stanza=prod info
```

## 2. Transfer the complete production repository

Copy the full repository, not live `PGDATA`:

```bash
sudo rsync -aHAX --numeric-ids --delete --info=progress2 \
  /var/lib/docker/volumes/infodengue-prod_pgbackrest_repo/_data/ \
  devops@<staging-host>:/srv/backups/pgbackrest-prod-repo/
```

## 3. Validate the transferred repository

Run on the staging host:

```bash
test -f /srv/backups/pgbackrest-prod-repo/backup/prod/backup.info
test -f /srv/backups/pgbackrest-prod-repo/archive/prod/archive.info
find /srv/backups/pgbackrest-prod-repo/backup/prod -maxdepth 1 -mindepth 1 -type d
```

The restore task requires both `backup/prod` and `archive/prod`, and it
requires an explicit backup-set directory under `backup/prod/`.

## 4. Run the guarded staging refresh task

The staging `.envs/.env` must resolve to `ENV=staging`.

```bash
cd /opt/services/infodengue

makim pgbackrest.refresh-staging-from-prod \
  --source-repo /srv/backups/pgbackrest-prod-repo \
  --backup-set <prod-backup-label> \
  --confirm REFRESH-STAGING-FROM-PROD
```

The task does this:

1. Stops only staging PostgreSQL and pgBackRest.
2. Validates the guarded staging `HOST_PGDATA` path.
3. Cleans staging `PGDATA`.
4. Removes only the `infodengue-staging_pgbackrest_repo` volume.
5. Renders `.runtime/pgbackrest/pgbackrest-restore-prod-to-staging.conf`.
6. Mounts the transferred production repository read-only at `/var/lib/pgbackrest-source`.
7. Restores `--stanza=prod --set=<prod-backup-label> --archive-mode=off`.
8. Waits for recovery to finish.
9. Validates the cloned database.
10. Stops restore-mode containers.
11. Renders the normal staging config.
12. Creates a fresh staging stanza and full staging backup.

## 5. Validate the restored database

The task already checks these queries:

```sql
SELECT pg_is_in_recovery();
SELECT current_setting('data_directory');
SELECT pg_database_size(current_database());
SELECT to_regclass('"Dengue_global"."Municipio"');
```

Run a manual check if needed:

```bash
docker compose \
  --env-file .envs/.env \
  --file containers/compose-base.yaml \
  --file containers/compose-staging.yaml \
  --file containers/compose-pgbackrest.yaml \
  --project-name infodengue-staging \
  exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT pg_is_in_recovery(), current_setting('data_directory'), to_regclass('\"Dengue_global\".\"Municipio\"');"
```

Compare the restored database size against the source backup before starting any
application service.

## 6. Create and validate the new staging backup

The refresh task ends by creating and validating a fresh staging backup in the
new staging repository. Confirm the result:

```bash
docker compose \
  --env-file .envs/.env \
  --file containers/compose-base.yaml \
  --file containers/compose-staging.yaml \
  --file containers/compose-pgbackrest.yaml \
  --project-name infodengue-staging \
  exec -T pgbackrest pgbackrest --stanza=staging info
```

## 7. Start application services only after database validation

Do not run migrations before restore validation.

```bash
docker compose \
  --env-file .envs/.env \
  --file containers/compose-base.yaml \
  --file containers/compose-staging.yaml \
  --project-name infodengue-staging \
  up -d web celery celery-beat
```

## Troubleshooting

`missing stanza path`
Diagnosis: the rendered config points `repo1-path` at the wrong repository or the wrong config file is mounted.
Safe actions: re-run `makim pgbackrest.render-conf --profile staging` or `makim pgbackrest.render-restore-conf`, then inspect `docker compose config`.

`backup and archive info do not match database`
Diagnosis: the copied repository is incomplete or backup and archive data came from different transfers.
Safe actions: copy the complete production repository again and verify both `backup/prod` and `archive/prod` before retrying.

`role postgres does not exist`
Diagnosis: this cluster uses `PSQL_USER` from `.envs/.env`, not a hardcoded `postgres` role.
Safe actions: connect with `POSTGRES_USER` or `PSQL_USER`, then re-run the validation query.

`permission denied`
Diagnosis: the host path, Docker bind mount, or generated runtime config has incompatible ownership or mode.
Safe actions: verify numeric `HOST_UID` and `HOST_GID`, ensure `.runtime/pgbackrest/*.conf` is readable, and check the source repository path permissions.

`unable to find valid repository`
Diagnosis: restore mode started without the read-only production repository mounted at `/var/lib/pgbackrest-source`.
Safe actions: confirm `PGBACKREST_SOURCE_REPO` is absolute, exists, and appears in `docker compose config`.

`could not locate required checkpoint record`
Diagnosis: the selected backup set is incomplete or required WAL is missing from `archive/prod`.
Safe actions: choose a valid explicit backup label, verify the copied archive, and repeat the repository transfer if needed.

`nested PGDATA`
Diagnosis: the staging bind mount contains an unexpected nested data directory after a previous manual restore attempt.
Safe actions: inspect `current_setting('data_directory')`, remove only the guarded contents of `HOST_PGDATA`, and rerun the guarded refresh task.

`stale Docker network endpoint`
Diagnosis: Docker kept an endpoint after a failed stop/remove cycle.
Safe actions: stop only the staging `postgres` and `pgbackrest` services again, remove those service containers, then rerun the refresh task.
