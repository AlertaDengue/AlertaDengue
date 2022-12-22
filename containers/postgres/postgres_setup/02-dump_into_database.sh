#!/bin/bash
set -e

gunzip -c /dumps/latest_infodengue.sql.gz | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="$PSQL_DBF"
gunzip -c /dumps/latest_dengue.sql.gz | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="$PSQL_DB"
