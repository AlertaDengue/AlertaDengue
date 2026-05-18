## 1. Generate/validate pgBackRest backup on source host

```bash
cd /opt/services/staging_AlertaDengue

makim pgbackrest.render-conf --profile staging
makim pgbackrest.stanza-create --profile staging
makim pgbackrest.backup-full --profile staging
makim pgbackrest.smoke-test --profile staging
```

Check backup:

```bash
docker exec -it infodengue-staging-pgbackrest-1 pgbackrest info
```

## 2. Find pgBackRest repo path on source

```bash
docker inspect infodengue-staging-pgbackrest-1 \
  --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
```

Use the path mounted to:

```text
/var/lib/pgbackrest
```

Example:

```text
/Storage/docker_data/volumes/infodengue-staging_pgbackrest_repo/_data
```

## 3. Send pgBackRest repo to Hetzner host

```bash
sudo rsync -aHAX --numeric-ids --delete --info=progress2 \
  -e "ssh -i /home/$USER/.ssh/id_ed25519" \
  /Storage/docker_data/volumes/infodengue-staging_pgbackrest_repo/_data/ \
  devops@[IP_ADDRESS]:/srv/workspace/infodengue/staging/pgbackrest/
```

Verify on Hetzner:

```bash
ssh devops@[IP_ADDRESS]

find /srv/workspace/infodengue/staging/pgbackrest -maxdepth 2 -type d
```

Expected:

```text
archive/staging
backup/staging
spool
```

## 4. Prepare Hetzner host paths

```bash
sudo mkdir -p /srv/workspace/infodengue/staging/pgdata
sudo mkdir -p /srv/workspace/infodengue/staging/pgbackrest

sudo chown -R devops:devops /srv/workspace/infodengue/staging
```

## 5. Ensure compose mounts the correct pgBackRest config

For staging, use:

```yaml
- ./pgbackrest/pgbackrest-staging.conf:/etc/pgbackrest/pgbackrest.conf
```

Or use an env variable:

```yaml
- ./pgbackrest/pgbackrest-${ENV}.conf:/etc/pgbackrest/pgbackrest.conf
```

with:

```env
PG_BACKREST_PROFILE=staging
```

## 6. Start pgBackRest/Postgres containers

```bash
cd /opt/services/infodengue/AlertaDengue

makim pgbackrest.render-conf --profile staging
```

Verify mounts:

```bash
docker inspect infodengue-staging-pgbackrest-1 \
  --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'

docker inspect infodengue-staging-postgres-1 \
  --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
```

Expected:

```text
/srv/workspace/infodengue/pgdata -> /var/lib/postgresql/data
...pgbackrest_repo... -> /var/lib/pgbackrest
pgbackrest-staging.conf -> /etc/pgbackrest/pgbackrest.conf
```

## 7. Copy repo into Docker pgBackRest volume if compose uses named volume

If `/var/lib/pgbackrest` is mounted from Docker volume:

```bash
sudo rsync -aHAX --numeric-ids --delete --info=progress2 \
  /srv/workspace/infodengue/staging/pgbackrest/ \
  /var/lib/docker/volumes/infodengue-staging_pgbackrest_repo/_data/
```

## 8. Restore cleanly

Stop PostgreSQL:

```bash
sugar compose-ext stop --services postgres
```

Clean PGDATA:

```bash
sudo rm -rf /srv/workspace/infodengue/pgdata/*
sudo chown -R devops:devops /srv/workspace/infodengue/pgdata
```

Restore:

```bash
makim pgbackrest.restore-latest --profile staging
```

## 9. Patch PostgreSQL memory for small Hetzner host

If the restored prod config has high memory values:

```bash
grep -E "shared_buffers|max_connections|work_mem|maintenance_work_mem|huge_pages" \
  /srv/workspace/infodengue/pgdata/postgresql.conf
```

Patch for 8 GB host:

```bash
sudo sed -i \
  -e "s/^max_connections = .*/max_connections = 100/" \
  -e "s/^shared_buffers = .*/shared_buffers = 512MB/" \
  -e "s/^maintenance_work_mem = .*/maintenance_work_mem = 128MB/" \
  -e "s/^work_mem = .*/work_mem = 8MB/" \
  -e "s/^huge_pages = .*/huge_pages = off/" \
  /srv/workspace/infodengue/pgdata/postgresql.conf
```

Recommended swap:

```bash
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 10. Start and validate PostgreSQL

```bash
docker restart infodengue-staging-postgres-1
docker logs -f infodengue-staging-postgres-1
```

Expected:

```text
database system is ready to accept connections
```

Validate DB:

```bash
docker exec -it infodengue-staging-postgres-1 bash
su postgres
psql -d dengue
```

```sql
SELECT datname, pg_size_pretty(pg_database_size(datname))
FROM pg_database
ORDER BY pg_database_size(datname) DESC;

SELECT schema_name
FROM information_schema.schemata
ORDER BY schema_name;

SELECT COUNT(*) FROM django_migrations;
```

Expected:

```text
dengue around 30-40 GB
schema includes Dengue_global
django_migrations already populated
```

## 11. Start app services

```bash
sugar compose-ext start -- -d
```

Then:

```bash
docker exec -it infodengue-staging-web-1 bash
python AlertaDengue/manage.py migrate --check
python AlertaDengue/manage.py check
```

Main rules:

```text
Never rsync live PGDATA.
Send pgBackRest repo, then restore.
Ensure stanza/config/profile match.
Ensure pgBackRest and Postgres share the same PGDATA mount.
Patch production memory settings before starting on a smaller VM.
Do not run migrations before validating the restored DB.
```
