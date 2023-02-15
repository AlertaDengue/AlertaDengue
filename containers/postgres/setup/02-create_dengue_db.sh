#!/usr/bin/env bash

set -e

PSQL_CMD="psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER""

if [[ "${ENV}" = "prod" ]]; then
    echo "[II] restore database from dump to production..."
    gunzip -c /dumps/latest_dengue.sql.gz | ${PSQL_CMD} -d ${PSQL_DB}
    gunzip -c /dumps/latest_infodengue.sql.gz | ${PSQL_CMD} -d ${PSQL_DBF}
else
    echo "[II] running script with schemas for demo database."
    psql -d ${PSQL_DB} < /schemas/schemas_dengue.sql
    echo "[II] giving access to the dev user."
    ./schemas/grant-user-readonly.sh
fi
