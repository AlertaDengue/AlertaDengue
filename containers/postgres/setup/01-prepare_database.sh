#!/usr/bin/env bash

set -e

PSQL_CMD="psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER""

# PostgreSQL databases

for dbname in "${PSQL_DB}" "${PSQL_DBF}"; do
    echo "CREATE DATABASE "${dbname}"
        WITH OWNER "${PSQL_USER}"
        ENCODING 'UTF8';" | ${PSQL_CMD}
done

# PostgreSQL roles

for dbusers in "dengueadmin" "infodenguedev"; do
    echo "ALTER ROLE "${dbusers}" WITH PASSWORD '"${PSQL_PASSWORD}"';" | ${PSQL_CMD}
done
