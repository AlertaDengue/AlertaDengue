# PostgreSQL 14 to 18 logical migration

This is a deliberate, operator-run logical migration. It has four commands:
`preflight`, `dump`, `restore`, and `validate`. It never restores a PostgreSQL
14 physical pgBackRest backup into PostgreSQL 18. pgBackRest is initialized
again for PostgreSQL 18 after cutover.

## Environment

The PostgreSQL 14 archive may contain the legacy `adminpack` extension and its
extension comment. PostgreSQL 18 does not provide `adminpack`; the restore
command filters only those two TOC entries and neither installs nor replaces
that extension. After validation, the required extensions are `postgis`,
`hstore`, `plpython3u`, and `postgres_fdw`, and `adminpack` must be absent.

Staging:

```sh
export PG14_HOST_PGDATA=/opt/data/staging/pg_data_dengue_staging
export PG18_HOST_PGDATA=/opt/data/staging/pg_data_dengue_staging_18
```

Production:

```sh
export PG14_HOST_PGDATA=/Storage/infodengue_data/pg_data_dengue_prod
export PG18_HOST_PGDATA=/Storage/infodengue_data/pg_data_dengue_prod_18
```

The target parent is mounted at `/var/lib/postgresql`, and PostgreSQL 18 uses
`PGDATA=/var/lib/postgresql/18/docker`. Set `PG18_POSTGRES_IMAGE` to the image
built for this deployment. Store connection credentials in a protected
`PGPASSFILE` or the existing secret mechanism, never in a command argument.

## Before the migration

1. Confirm the running source is PostgreSQL 14 and confirm free disk space.
2. Create and verify a fresh PostgreSQL 14 pgBackRest backup.
3. Record extensions, baseline counts, and this read-only role inventory:

   ```sql
   SELECT rolname FROM pg_roles WHERE rolname NOT LIKE 'pg_%' ORDER BY 1;
   SELECT datname, pg_get_userbyid(datdba) FROM pg_database ORDER BY 1;
   SELECT nspname, pg_get_userbyid(nspowner) FROM pg_namespace ORDER BY 1;
   SELECT n.nspname, c.relname, pg_get_userbyid(c.relowner)
   FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname NOT IN ('pg_catalog', 'information_schema') ORDER BY 1, 2;
   SELECT table_schema, table_name, grantee, privilege_type, is_grantable
   FROM information_schema.role_table_grants ORDER BY 1, 2, 3, 4;
   SELECT member::regrole, roleid::regrole, admin_option FROM pg_auth_members;
   ```

4. Stop web, Celery, Celery Beat, and every other database writer.

## Logical migration

Set non-secret endpoint variables, using `PGPASSFILE` for authentication:

```sh
export SOURCE_HOST=pg14.example.internal SOURCE_PORT=5432
export SOURCE_DB=alertadengue SOURCE_USER=alertadengue
export TARGET_HOST=127.0.0.1 TARGET_PORT=5432
export TARGET_DB=alertadengue TARGET_USER=alertadengue
export DUMP_ROOT=/secure/postgresql-18-migration
export REQUIRED_BYTES=107374182400
```

Run the read-only preflight before initializing PostgreSQL 18. The target path
must already exist and be completely empty.

```sh
python containers/postgres/migration.py preflight \
  --source-host "$SOURCE_HOST" --source-port "$SOURCE_PORT" \
  --source-database "$SOURCE_DB" --source-user "$SOURCE_USER" \
  --source-path "$PG14_HOST_PGDATA" --target-path "$PG18_HOST_PGDATA" \
  --disk-path "$DUMP_ROOT" --required-bytes "$REQUIRED_BYTES"
```

Create the private custom archive outside the repository. The command creates
its output directory and `database.dump` with mode 0600, so choose a new name.

```sh
python containers/postgres/migration.py dump \
  --source-host "$SOURCE_HOST" --source-port "$SOURCE_PORT" \
  --source-database "$SOURCE_DB" --source-user "$SOURCE_USER" \
  --output-dir "$DUMP_ROOT/$(date +%Y%m%d-%H%M%S)"
export ARCHIVE="$DUMP_ROOT/<the-new-directory>/database.dump"
```

Initialize the empty PostgreSQL 18 directory once. This explicit flag permits
only the official PostgreSQL initialization path; unset it immediately after
that first start.

```sh
ALLOW_PG18_INITIALIZATION=1 PG_ARCHIVE_MODE=off sugar --profile staging compose-ext start --services postgres --options -d
# wait for readiness, then stop PostgreSQL if the target role/database setup
# requires an operator maintenance step
unset ALLOW_PG18_INITIALIZATION
PG_ARCHIVE_MODE=off sugar --profile staging compose-ext start --services postgres --options -d

```
Create or verify the target application database and `PSQL_USER` through the
normal initialization mechanism. The archive is restored as `PSQL_USER`:
owners and ACLs in the source are intentionally not replayed. Recreate only
reviewed external/read-only roles and grants (for example Mosqlimate) after
this application restore.

```sh
python containers/postgres/migration.py restore \
  --target-host "$TARGET_HOST" --target-port "$TARGET_PORT" \
  --target-database "$TARGET_DB" --target-user "$TARGET_USER" \
  --archive "$ARCHIVE"
```

The restore rejects a non-18 server or a nonempty target database and invokes
`pg_restore --exit-on-error --single-transaction --no-owner --no-acl` with
`--role="$TARGET_USER"`. It does not drop a database, clean either data
directory, or modify PostgreSQL 14.

Validate before allowing writers back:

```sh
python containers/postgres/migration.py validate \
  --source-host "$SOURCE_HOST" --source-port "$SOURCE_PORT" \
  --source-database "$SOURCE_DB" --source-user "$SOURCE_USER" \
  --target-host "$TARGET_HOST" --target-port "$TARGET_PORT" \
  --target-database "$TARGET_DB" --target-user "$TARGET_USER"
```

Validation confirms source 14, target 18, distinct endpoints, an application
connection, required extensions, application schemas, key relations, Django
migration rows, retired `tweet` columns, and serial/identity sequence values.
Then start application services, run API/report smoke tests, initialize a new
PostgreSQL 18 pgBackRest stanza, and create and verify a PostgreSQL 18 full
backup. Retain PG14 unchanged through the agreed observation window.

## Rollback

Before PostgreSQL 18 accepts writes, stop application services, restore the
PG14 Compose/path configuration, start PG14, and validate the application.

After PostgreSQL 18 accepts writes, stop writers and decide explicitly how to
reconcile data written only to PG18. This procedure does not provide automatic
or transparent rollback.

## Staging gate

Run this procedure in staging first using the real PostgreSQL 14/PostGIS 3.3.2
source. Staging is the compatibility rehearsal; production proceeds only after
that rehearsal passes and staging remains stable for the agreed observation
period. A disposable local rehearsal may use an available PostGIS 3.3.x image;
do not depend on an unavailable exact-version image tag.
