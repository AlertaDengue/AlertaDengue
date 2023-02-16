#!/usr/bin/env bash

set -e

PSQL_CMD="psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER""

if [[ "${DATABASE}" = "dumps" ]]; then
    echo "[II] restore database from ${DATABASE} to production..."
    gunzip -c /PG_RESTORE/latest_dengue.sql.gz | ${PSQL_CMD} -d ${PSQL_DB}
    gunzip -c /PG_RESTORE/latest_infodengue.sql.gz | ${PSQL_CMD} -d ${PSQL_DBF}
else
    echo "[II] creating ${DATABASE} for the demo database."
    psql -d ${PSQL_DB} < /PG_RESTORE/schemas_dengue.sql
    echo "[II] giving access to the dev user."
    ./PG_RESTORE/grant-user-readonly.sh
fi
