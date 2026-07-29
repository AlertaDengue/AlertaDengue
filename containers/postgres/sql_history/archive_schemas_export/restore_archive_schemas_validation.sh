#!/usr/bin/env bash
set -Eeuo pipefail

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'missing required command: %s\n' "$1" >&2
    exit 1
  }
}

require_cmd psql
require_cmd pg_restore
require_cmd dropdb
require_cmd createdb

export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-25432}"
export PGDATABASE="${PGDATABASE:-dengue}"
export PGUSER="${PGUSER:-dengueadmin}"
export RESTORE_TABLESPACE="${RESTORE_TABLESPACE:-}"
export SOURCE_DATABASE="${SOURCE_DATABASE:-${PGDATABASE}}"
export LOAD_HISTORICO_FROM_SOURCE="${LOAD_HISTORICO_FROM_SOURCE:-0}"

DUMP_FILE="${1:-}"
RESTORE_DB="${2:-archive_schemas_restore_validation}"
REGIONAL_KEYS_FILE="${3:-}"
CID10_KEYS_FILE="${4:-}"

if [[ -z "${DUMP_FILE}" || -z "${REGIONAL_KEYS_FILE}" || -z "${CID10_KEYS_FILE}" ]]; then
  printf 'usage: %s <dump-file> <restore-db> <regional-keys.tsv> <cid10-keys.tsv>\n' "${0##*/}" >&2
  exit 1
fi

dropdb --if-exists "${RESTORE_DB}"
if [[ -n "${RESTORE_TABLESPACE}" ]]; then
  createdb -T template0 -D "${RESTORE_TABLESPACE}" "${RESTORE_DB}"
else
  createdb -T template0 "${RESTORE_DB}"
fi

psql -X -v ON_ERROR_STOP=1 -d "${RESTORE_DB}" <<'EOF'
CREATE SCHEMA IF NOT EXISTS "Dengue_global";
CREATE SCHEMA IF NOT EXISTS "Municipio";
CREATE SCHEMA IF NOT EXISTS weather;

CREATE TABLE "Dengue_global".regional (
    id integer PRIMARY KEY
);

CREATE TABLE "Dengue_global"."CID10" (
    codigo character varying(4) PRIMARY KEY
);

CREATE TABLE "Dengue_global".regional_saude (
    id integer PRIMARY KEY,
    municipio_geocodigo integer UNIQUE
);

CREATE TABLE "Municipio"."Historico_alerta" (
    "data_iniSE" date,
    "SE" integer,
    casos_est real,
    casos_est_min integer,
    casos_est_max integer,
    casos integer,
    municipio_geocodigo integer
);

CREATE TABLE "Municipio"."Historico_alerta_chik" (
    "data_iniSE" date,
    "SE" integer,
    casos_est real,
    casos_est_min integer,
    casos_est_max integer,
    casos integer,
    municipio_geocodigo integer
);

CREATE TABLE "Municipio"."Notificacao" (
    id bigint PRIMARY KEY
);

CREATE TABLE weather.copernicus_bra (
    date date,
    geocode bigint
);
EOF

if [[ "${LOAD_HISTORICO_FROM_SOURCE}" == "1" ]]; then
  # pg_restore rebuilds the archived materialized view from its retained
  # sources, so local validation preloads only the required columns here.
  psql -X -v ON_ERROR_STOP=1 -d "${SOURCE_DATABASE}" -c \
    "\copy (SELECT \"data_iniSE\", \"SE\", casos_est, casos_est_min, casos_est_max, casos, municipio_geocodigo FROM \"Municipio\".\"Historico_alerta\") TO STDOUT WITH (FORMAT csv, DELIMITER E'\t')" \
    | psql -X -v ON_ERROR_STOP=1 -d "${RESTORE_DB}" -c \
        "\copy \"Municipio\".\"Historico_alerta\" (\"data_iniSE\", \"SE\", casos_est, casos_est_min, casos_est_max, casos, municipio_geocodigo) FROM STDIN WITH (FORMAT csv, DELIMITER E'\t')"

  psql -X -v ON_ERROR_STOP=1 -d "${SOURCE_DATABASE}" -c \
    "\copy (SELECT \"data_iniSE\", \"SE\", casos_est, casos_est_min, casos_est_max, casos, municipio_geocodigo FROM \"Municipio\".\"Historico_alerta_chik\") TO STDOUT WITH (FORMAT csv, DELIMITER E'\t')" \
    | psql -X -v ON_ERROR_STOP=1 -d "${RESTORE_DB}" -c \
        "\copy \"Municipio\".\"Historico_alerta_chik\" (\"data_iniSE\", \"SE\", casos_est, casos_est_min, casos_est_max, casos, municipio_geocodigo) FROM STDIN WITH (FORMAT csv, DELIMITER E'\t')"
fi

psql -X -v ON_ERROR_STOP=1 -d "${RESTORE_DB}" -c "\copy \"Dengue_global\".regional (id) FROM '${REGIONAL_KEYS_FILE}' WITH (FORMAT csv, DELIMITER E'\t')"
psql -X -v ON_ERROR_STOP=1 -d "${RESTORE_DB}" -c "\copy \"Dengue_global\".\"CID10\" (codigo) FROM '${CID10_KEYS_FILE}' WITH (FORMAT csv, DELIMITER E'\t')"

pg_restore --exit-on-error --verbose --dbname="${RESTORE_DB}" "${DUMP_FILE}"
