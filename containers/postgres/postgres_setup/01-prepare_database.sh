#!/usr/bin/env bash

set -e


PSQL_CMD="psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER""

# PostgreSQL databases
for dbname in "$PSQL_DBF"; do

    echo "CREATE DATABASE "${dbname}" WITH OWNER '""$PSQL_USER""';" | ${PSQL_CMD}
 
done

# PostgreSQL roles
for dbusers in "$DB_ROLES"; do

    echo "ALTER ROLE ""$PSQL_USER"" WITH PASSWORD '""$PSQL_PASSWORD""';" | ${PSQL_CMD}
 
done
