#!/bin/bash

set -e

# PostgreSQL databases
echo "CREATE DATABASE ""$PSQL_DB"" WITH OWNER '""$PSQL_USER""';" | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER"
echo "CREATE DATABASE ""$PSQL_DBF"" WITH OWNER '""$PSQL_USER""';" | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER"

# PostgreSQL roles
echo "ALTER ROLE ""$PSQL_USER"" WITH PASSWORD '""$PSQL_PASSWORD""';" | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER"
echo "ALTER ROLE administrador WITH PASSWORD '""$PSQL_PASSWORD""';" | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER"
echo "ALTER ROLE forecast WITH PASSWORD '""$PSQL_PASSWORD""';" | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER"
