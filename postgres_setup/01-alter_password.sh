#!/bin/bash
set -e
echo "ALTER ROLE administrador WITH PASSWORD '""$POSTGRES_PASSWORD""';" | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER"
