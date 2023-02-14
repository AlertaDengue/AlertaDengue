#!/usr/bin/env bash

source containers/postgres/common/load-dotenv.sh

export PSQL_CMD_NO_DBNAME="PGPASSWORD=${POSTGRES_PASSWORD} psql -U ${POSTGRES_USER} --host localhost --port 5432"
export PSQL_CMD="${PSQL_CMD_NO_DBNAME} --dbname dengue"
