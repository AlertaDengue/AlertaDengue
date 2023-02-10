#!/usr/bin/env bash

set -e

DB_NAME="$PSQL_DB"
PSQL_CMD="psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER""
DB_USER="$PSQL_USER"

echo "ALTER ROLE "${DB_USER}" WITH PASSWORD 'infodenguedev';" | ${PSQL_CMD}

for schema in '"Dengue_global"' '"Municipio"' forecast public; do

    echo "GRANT USAGE ON SCHEMA "${schema}" TO "${DB_USER}";" | ${PSQL_CMD} -d ${DB_NAME}
    echo "GRANT SELECT ON ALL TABLES IN SCHEMA "${schema}" TO "${DB_USER}";" | ${PSQL_CMD} -d ${DB_NAME}
 
done
