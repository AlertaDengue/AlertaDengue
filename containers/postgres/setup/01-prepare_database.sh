#!/usr/bin/env bash

set -e


PROJECT_PATH="$(pwd |grep -wo ".*\/AlertaDengue")"

PSQL_CMD="psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER""

# PostgreSQL databases
for dbname in "${PSQL_DB}" "${PSQL_DBF}"; do

    echo "SELECT 'CREATE DATABASE "${dbname}" WITH OWNER "${PSQL_USER}"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '"${dbname}"')\gexec" | ${PSQL_CMD}

done

# PostgreSQL roles
for dbusers in "dengueadmin" "administrador" "forecast" "infodenguedev"; do

    echo "ALTER ROLE "${dbusers}" WITH PASSWORD '"${PSQL_PASSWORD}"';" | ${PSQL_CMD}
 
done

# PostgreSQL dump
if [ $ENV == "dev" ]; then    
  cp ${PROJECT_PATH}/containers/postgres/schema/* /postgres/sql/;
  else
  cp ${PROJECT_PATH}/containers/postgres/dumps/* /postgres/sql/;
fi
