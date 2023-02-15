#!/usr/bin/env bash

set -e

PSQL_CMD="psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER""

# PostgreSQL databases

for dbname in "${PSQL_DB}" "${PSQL_DBF}"; do
    # CREATE DATABASE dengue WITH OWNER dengueadmin ENCODING 'utf-8';
    echo "SELECT 'CREATE DATABASE "${dbname}" WITH OWNER "${PSQL_USER}"' WHERE NOT EXISTS (
      SELECT FROM pg_database WHERE datname = '"${dbname}"')\gexec" | ${PSQL_CMD}
done

# PostgreSQL roles

for dbusers in "dengueadmin" "infodenguedev"; do
    echo "ALTER ROLE "${dbusers}" WITH PASSWORD '"${PSQL_PASSWORD}"';" | ${PSQL_CMD}
done
