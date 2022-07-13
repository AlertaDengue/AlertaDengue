#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$PSQL_USER" <<-EOSQL
    CREATE DATABASE dengue WITH OWNER dengueadmin ENCODING 'utf-8';
EOSQL

gunzip -c /dumps/latest_dengue.sql.gz | psql -v ON_ERROR_STOP=1 --username "$PSQL_USER" --dbname=dengue
