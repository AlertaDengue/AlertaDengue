#!/usr/bin/env bash

set -e

if [[ "${ENV}" = "prod" ]]; then
    echo "[II] restore from dump to production..."
    gunzip -c /dumps/latest_dengue.sql.gz | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname=dengue
    gunzip -c /dumps/latest_infodengue.sql.gz | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname=infodengue
else
    echo "[II] running script with schemas for demo database"
    psql -d dengue < /schemas/02-dengue_schema.sql
    ./schemas/03-grant-user-readonly.sh
fi
