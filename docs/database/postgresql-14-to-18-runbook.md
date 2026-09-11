# PostgreSQL 14 to 18 logical migration

This is an operator-run logical migration. It does not restore a PostgreSQL 14
pgBackRest backup into PostgreSQL 18. pgBackRest is configured anew after a
successful PostgreSQL 18 cutover.

## Environment

Staging:

```sh
PG14_HOST_PGDATA=/opt/data/staging/pg_data_dengue_staging
PG18_HOST_PGDATA=/opt/data/staging/pg_data_dengue_staging_18
```

Production:

```sh
PG14_HOST_PGDATA=/Storage/infodengue_data/pg_data_dengue_prod
PG18_HOST_PGDATA=/Storage/infodengue_data/pg_data_dengue_prod_18
```

The target is mounted at `/var/lib/postgresql`; PostgreSQL 18 uses
`PGDATA=/var/lib/postgresql/18/docker`. Keep the PG14 directory unchanged.

## Operator workflow

1. Verify the current server is PostgreSQL 14 and make a fresh PG14 backup.
2. Stop application writers.
3. Run `migration.py preflight` with both endpoints, both host paths, and a
   dump filesystem. It requires separate absolute paths, a PG14 marker, an
   empty target, free space, and PostgreSQL client commands.
4. Run `migration.py dump --output-dir /secure/migration-YYYYMMDD`. It writes
   `globals.sql` and `database.dump` mode 0600 outside the repository.
5. Initialize the empty PG18 target with the PostgreSQL 18 Compose service.
6. Run `migration.py restore --globals ... --archive ...`. Review bootstrap
   role conflicts first; the command fails on globals or archive errors and
   preserves dumped owners and ACLs.
7. Run `migration.py validate`. It checks PostgreSQL 18, required extensions,
   Django migration records, and the application database connection.
8. Start the application against PG18, smoke test, create a new PG18 pgBackRest
   stanza and full backup, and retain PG14 unchanged.

## Rollback

Before PG18 accepts new writes, stop PG18 application services, point the stack
back to PG14, restart, and verify. After PG18 accepts writes, rollback requires
an explicit data reconciliation decision; this runbook does not imply a
transparent rollback.
