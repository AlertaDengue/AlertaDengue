#!/bin/bash

set -e

PSQL_CMD="psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER""

if [[ "${PG_RESTORE_STAGING}" = "dumps" ]]
then
    echo "[II] restore database from ${PG_RESTORE_STAGING} to production..."
    gunzip -c /"${PG_RESTORE_STAGING}"/latest_dengue.sql.gz | ${PSQL_CMD} -d ${PSQL_DB}
    gunzip -c /"${PG_RESTORE_STAGING}"/latest_infodengue.sql.gz | ${PSQL_CMD} -d ${PSQL_DBF}
elif [[ "${PG_RESTORE_STAGING}" = "schemas" ]]
then
    echo "[II] creating ${PG_RESTORE_STAGING} for the demo database."
    psql -d ${PSQL_DB} < /"${PG_RESTORE_STAGING}"/schemas_dengue.sql
else
    echo "[ERR]: ${PG_RESTORE_STAGING} is not a valid dump file! You have to choose between schemas or dumps"
fi
