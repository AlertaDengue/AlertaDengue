#!/bin/bash
set -e
echo "ALTER ROLE administrador WITH PASSWORD '""$PSQL_PASSWORD""';" | psql -v ON_ERROR_STOP=1 --username "$PSQL_USER"
echo "ALTER ROLE forecast WITH PASSWORD '""$PSQL_PASSWORD""';" | psql -v ON_ERROR_STOP=1 --username "$PSQL_USER"
echo "ALTER ROLE dengue WITH PASSWORD '""$PSQL_PASSWORD""';" | psql -v ON_ERROR_STOP=1 --username "$PSQL_USER"
