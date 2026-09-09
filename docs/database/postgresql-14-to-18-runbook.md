# PostgreSQL 14 to 18 logical migration runbook

This runbook is for a separately approved maintenance window. It has been
rehearsed only with synthetic disposable databases. Never point these commands
at staging or production without an approved change.

## Storage safeguards

PostgreSQL 14 and 18 must use separate sibling directories. Set
`PG14_HOST_PGDATA` to the preserved PostgreSQL 14 cluster and
`PG18_HOST_PGDATA` to a newly provisioned PostgreSQL 18 target. Verify the
source has `PG_VERSION` 14 and the target is empty before initialization (or
has only `PG_VERSION` 18). Never nest either path below the other.

Configure the two variables only in each deployment environment; do not commit
absolute host paths to this generic runbook.

The target image uses `PGDATA=/var/lib/postgresql/18/docker` and mounts the
host directory at `/var/lib/postgresql`.

WARNING: changing the image and PGDATA without provisioning and restoring the
separate PostgreSQL 18 target directory starts an empty cluster.

Rollback before PostgreSQL 18 accepts writes means restoring the previous
Compose variable and starting PostgreSQL 14 against `PG14_HOST_PGDATA`. Retain
the PostgreSQL 14 directory and backups until acceptance.

## Compatibility matrix

| Component | Source | Target |
|---|---|---|
| Server/client | PostgreSQL 14 | PostgreSQL 18.6 |
| Image | PostgreSQL 14-compatible | `postgres:18.6-bookworm` |
| Container data path | image default | `/var/lib/postgresql/18/docker` |
| Volume mount | source host directory | `/var/lib/postgresql` |
| PostGIS | 3.4.x fixture | 3.6.4, PostgreSQL 18 compatible |
| PL/Python | source inventory | `postgresql-plpython3-18` |
| pgBackRest | existing chain | reviewed PostgreSQL 18 path/stanza |

The target image is built by `containers/postgres/Dockerfile`. A no-cache build
must verify PostgreSQL 18 PostGIS and scripts, PL/Python, and pgBackRest
packages.

## Preconditions and rollback

1. Confirm source major 14 and a newly initialized target major 18 cluster.
   Keep PostgreSQL 14 and its volume intact.
2. Stop application writers. Record encoding, locale/collation, extensions,
   roles, grants, and free space. Budget dump size + target size + 5 GiB.
3. Verify an approved, restorable PostgreSQL 14 backup and maintenance window.
4. Before PostgreSQL 18 accepts new writes, rollback means stopping the app and
   switching connectivity back to the preserved PostgreSQL 14 cluster. After
   new writes, reconciliation needs a separately designed procedure; this is
   never a physical PostgreSQL 18-to-14 downgrade.

## Logical migration

Use the PostgreSQL 18 client from the new image. Keep passwords in the operator
environment or secret store. Every preflight and dump invocation must include
the two explicit host paths and the exact container PGDATA value.

```sh
python3 containers/postgres/migration.py preflight \
  --source-host <source-host> --source-port <source-port> \
  --source-database <source-db> --source-user <source-user> \
  --target-host <target-host> --target-port <target-port> \
  --target-database <target-db> --target-user <target-user> \
  --source-path "$PG14_HOST_PGDATA" --target-path "$PG18_HOST_PGDATA" \
  --container-pgdata /var/lib/postgresql/18/docker \
  --required-bytes <bytes> --disk-path <dump-filesystem>

python3 containers/postgres/migration.py dump \
  --source-host <source-host> --source-port <source-port> \
  --source-database <source-db> --source-user <source-user> \
  --target-host <target-host> --target-port <target-port> \
  --target-database <target-db> --target-user <target-user> \
  --source-path "$PG14_HOST_PGDATA" --target-path "$PG18_HOST_PGDATA" \
  --container-pgdata /var/lib/postgresql/18/docker \
  --output-dir <timestamped-output-dir> --disk-path <dump-filesystem>

python3 containers/postgres/migration.py restore \
  --source-host <source-host> --source-port <source-port> \
  --source-database <source-db> --source-user <source-user> \
  --target-host <target-host> --target-port <target-port> \
  --target-database <target-db> --target-user <target-user> \
  --globals <globals.sql> --archive <database.dump>

python3 containers/postgres/migration.py validate \
  --source-host <source-host> --source-port <source-port> \
  --source-database <source-db> --source-user <source-user> \
  --target-host <target-host> --target-port <target-port> \
  --target-database <target-db> --target-user <target-user>
```

The dump phase uses `pg_dumpall --globals-only --no-role-passwords` and a
quoted custom `pg_dump`, verifies nonempty files, and runs `pg_restore --list`.
Restore uses `ON_ERROR_STOP` and `--exit-on-error`, never drops a target
database, and omits only the initdb-provided `postgres` role from globals.

## Acceptance

Compare encoding/locale/collation, schemas, tables, columns/types, nullability,
defaults, constraints, indexes, views, materialized views, extension names and
versions, roles/grants, bounded row counts and deterministic aggregates,
sequences, and populated materialized views. Check spatial values/indexes and
ensure historical-alert tables have no retired tweet column.

Run the Django migration plans and checks from the web container:

```sh
python AlertaDengue/manage.py migrate --plan --database=default
python AlertaDengue/manage.py migrate --plan --database=dados
python AlertaDengue/manage.py check
```

Run focused router, unmanaged-model, migration, API, report, ingestion,
EpiScanner, PostGIS, and materialized-view tests. Inspect logs for `ERROR`,
`FATAL`, `PANIC`, `UndefinedColumn`, `DatabaseError`, `Traceback`,
extension-loading, collation, and data-directory messages.

## pgBackRest and cutover

Do not reuse the PostgreSQL 14 production stanza for rehearsal. For an approved
cutover update `pg1-path` to `/var/lib/postgresql/18/docker` (or create the
approved replacement stanza), run `pgbackrest check`, create a new full
PostgreSQL 18 backup, run `info`, and perform isolated restore verification.
Retain the PostgreSQL 14 backup chain until acceptance.

Start the application only after checks pass, then smoke-test dengue,
chikungunya, and Zika APIs, lookups, reports, dashboards, notifications, and a
safe managed-model write.

## Cleanup

Before cleanup print exact named disposable containers, volumes, and dump
directory. Remove only those named resources after acceptance. Never use broad
filters, delete repository paths, or remove persistent environment volumes.
