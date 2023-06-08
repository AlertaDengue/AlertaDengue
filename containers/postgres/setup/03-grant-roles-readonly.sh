#!/usr/bin/env bash

set -e

PSQL_CMD="psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER""

for schema in '"Dengue_global"' '"Municipio"' forecast public weather; do
    echo "GRANT USAGE ON SCHEMA "${schema}" TO "${PSQL_DEV_USER}";" | ${PSQL_CMD} -d ${PSQL_DB}
    echo "GRANT SELECT ON ALL TABLES IN SCHEMA "${schema}" TO "${PSQL_DEV_PASSWORD}";" | ${PSQL_CMD} -d ${PSQL_DB}
done
