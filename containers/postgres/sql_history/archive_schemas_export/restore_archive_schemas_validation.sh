#!/usr/bin/env bash
set -Eeuo pipefail

readonly APPROVED_SCHEMAS=(
  archive_redemet
  archive_upload
  archive_ovitrampa
  archive_alertas_regionais
  archive_cemaden
  archive_copernicus
  archive_historico_casos
  archive_mosqlimate
  archive_tweets
)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'missing required command: %s\n' "$1" >&2
    exit 1
  }
}

for cmd in awk cmp createdb dropdb mktemp pg_restore psql realpath rm sha256sum; do
  require_cmd "$cmd"
done

export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-25432}"
export PGDATABASE="${PGDATABASE:-dengue}"
export PGUSER="${PGUSER:-dengueadmin}"
export RESTORE_TABLESPACE="${RESTORE_TABLESPACE:-}"
export SOURCE_DATABASE="${SOURCE_DATABASE:-${PGDATABASE}}"
export LOAD_HISTORICO_FROM_SOURCE="${LOAD_HISTORICO_FROM_SOURCE:-0}"

fatal() {
  printf '%s\n' "$1" >&2
  exit 1
}

validate_package_path() {
  local package_dir
  package_dir="$(realpath "$1")"
  [[ -d "$package_dir" ]] || fatal "package directory does not exist: $package_dir"
  [[ "$package_dir" != /tmp && "$package_dir" != /tmp/* ]] || fatal 'package path under /tmp is rejected'
  [[ "$package_dir" != /var/tmp && "$package_dir" != /var/tmp/* ]] || fatal 'package path under /var/tmp is rejected'
  [[ "$package_dir" != "$REPO_ROOT" && "$package_dir" != "$REPO_ROOT"/* ]] || fatal 'package path inside the git worktree is rejected'
  local data_directory
  data_directory="$(psql -X -At -v ON_ERROR_STOP=1 -c 'SHOW data_directory')"
  if [[ -e "$data_directory" ]]; then
    data_directory="$(realpath "$data_directory")"
  fi
  [[ "$package_dir" != "$data_directory" && "$package_dir" != "$data_directory"/* ]] || fatal 'package path inside PostgreSQL data_directory is rejected'
  printf '%s\n' "$package_dir"
}

sha_file() {
  sha256sum "$1" | awk '{print $1}'
}

normalized_inventory_sha() {
  awk -F $'\t' 'BEGIN {OFS = "\t"} {print $1, $2, $3, $5, $6, $7}' "$1" | sha256sum | awk '{print $1}'
}

normalized_dependency_sha() {
  awk -F $'\t' '$1 != "pg_toast" && $4 != "pg_toast"' "$1" | sha256sum | awk '{print $1}'
}

assert_regular_file() {
  [[ -f "$1" ]] || fatal "required file is missing: $1"
  [[ ! -L "$1" ]] || fatal "symlinks are not allowed: $1"
}

assert_nonempty_file() {
  assert_regular_file "$1"
  [[ -s "$1" ]] || fatal "required file is empty: $1"
}

psql_capture_db() {
  local db="$1"
  shift
  PGDATABASE="$db" psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 "$@"
}

write_archive_inventory_db() {
  local db="$1"
  local target="$2"
  psql_capture_db "$db" -f - > "$target" <<'SQL'
SELECT n.nspname, c.relname, c.relkind, c.oid, pg_get_userbyid(c.relowner) AS owner_name,
       COALESCE(obj_description(c.oid, 'pg_class'), '') AS comment,
       COALESCE(array_to_string(c.relacl, ','), '') AS rel_acl
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN (
  'archive_redemet',
  'archive_upload',
  'archive_ovitrampa',
  'archive_alertas_regionais',
  'archive_cemaden',
  'archive_copernicus',
  'archive_historico_casos',
  'archive_mosqlimate',
  'archive_tweets'
)
  AND c.relkind IN ('r', 'm', 'S', 'i')
ORDER BY 1, 2, 3;
SQL
}

write_archive_row_counts_db() {
  local db="$1"
  local target="$2"
  psql_capture_db "$db" -f - > "$target" <<'SQL'
SELECT n.nspname, c.relname, c.relkind,
       CASE
         WHEN c.relkind = 'm'
           THEN (SELECT CASE WHEN ispopulated THEN 't' ELSE 'f' END
                 FROM pg_matviews mv
                 WHERE mv.schemaname = n.nspname AND mv.matviewname = c.relname)
         ELSE ''
       END AS matview_populated,
       (xpath('/row/count/text()',
              query_to_xml(format('SELECT count(*) AS count FROM %I.%I', n.nspname, c.relname), false, true, '')))[1]::text
         AS exact_row_count
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN (
  'archive_redemet',
  'archive_upload',
  'archive_ovitrampa',
  'archive_alertas_regionais',
  'archive_cemaden',
  'archive_copernicus',
  'archive_historico_casos',
  'archive_mosqlimate',
  'archive_tweets'
)
  AND c.relkind IN ('r', 'm')
ORDER BY 1, 2;
SQL
}

write_archive_dependencies_db() {
  local db="$1"
  local target="$2"
  psql_capture_db "$db" -f - > "$target" <<'SQL'
SELECT obj_ns.nspname, obj.relname, obj.relkind,
       ref_ns.nspname, ref.relname, ref.relkind, d.deptype
FROM pg_depend d
JOIN pg_class obj ON obj.oid = d.objid
JOIN pg_namespace obj_ns ON obj_ns.oid = obj.relnamespace
JOIN pg_class ref ON ref.oid = d.refobjid
JOIN pg_namespace ref_ns ON ref_ns.oid = ref.relnamespace
WHERE obj_ns.nspname IN (
        'archive_redemet',
        'archive_upload',
        'archive_ovitrampa',
        'archive_alertas_regionais',
        'archive_cemaden',
        'archive_copernicus',
        'archive_historico_casos',
        'archive_mosqlimate',
        'archive_tweets'
      )
   OR ref_ns.nspname IN (
        'archive_redemet',
        'archive_upload',
        'archive_ovitrampa',
        'archive_alertas_regionais',
        'archive_cemaden',
        'archive_copernicus',
        'archive_historico_casos',
        'archive_mosqlimate',
        'archive_tweets'
      )
ORDER BY 1, 2, 4, 5, 7;
SQL
}

write_archive_external_fks_db() {
  local db="$1"
  local target="$2"
  psql_capture_db "$db" -f - > "$target" <<'SQL'
SELECT con.conrelid::regclass::text,
       con.conname,
       con.confrelid::regclass::text,
       con.convalidated,
       con.confdeltype,
       con.confupdtype
FROM pg_constraint con
JOIN pg_namespace src_ns ON src_ns.oid = con.connamespace
JOIN pg_class ref_cls ON ref_cls.oid = con.confrelid
JOIN pg_namespace ref_ns ON ref_ns.oid = ref_cls.relnamespace
WHERE con.contype = 'f'
  AND src_ns.nspname IN (
    'archive_redemet',
    'archive_upload',
    'archive_ovitrampa',
    'archive_alertas_regionais',
    'archive_cemaden',
    'archive_copernicus',
    'archive_historico_casos',
    'archive_mosqlimate',
    'archive_tweets'
  )
  AND ref_ns.nspname !~ '^archive_'
ORDER BY 1, 2, 3;
SQL
}

write_archive_internal_fks_db() {
  local db="$1"
  local target="$2"
  psql_capture_db "$db" -f - > "$target" <<'SQL'
SELECT con.conrelid::regclass::text,
       con.conname,
       con.confrelid::regclass::text,
       con.convalidated,
       con.confdeltype,
       con.confupdtype
FROM pg_constraint con
JOIN pg_namespace src_ns ON src_ns.oid = con.connamespace
JOIN pg_class ref_cls ON ref_cls.oid = con.confrelid
JOIN pg_namespace ref_ns ON ref_ns.oid = ref_cls.relnamespace
WHERE con.contype = 'f'
  AND src_ns.nspname IN (
    'archive_redemet',
    'archive_upload',
    'archive_ovitrampa',
    'archive_alertas_regionais',
    'archive_cemaden',
    'archive_copernicus',
    'archive_historico_casos',
    'archive_mosqlimate',
    'archive_tweets'
  )
  AND ref_ns.nspname ~ '^archive_'
ORDER BY 1, 2, 3;
SQL
}

assert_external_fk_contract_file() {
  local fk_file="$1"
  local expected_file="$2"
  cat > "$expected_file" <<'EOF'
archive_alertas_regionais.alerta_regional_chik	regional_fk	"Dengue_global".regional	t	a	a
archive_alertas_regionais.alerta_regional_dengue	regional_fk	"Dengue_global".regional	t	a	a
archive_alertas_regionais.alerta_regional_zika	regional_fk	"Dengue_global".regional	t	a	a
archive_tweets."Tweet"	Tweet_CID10	"Dengue_global"."CID10"	t	a	a
EOF
  cmp -s "$fk_file" "$expected_file" || fatal 'external archive foreign keys differ from the approved contract'
}

assert_no_active_to_archive_dependency_file() {
  local dep_file="$1"
  awk -F $'\t' '$1 !~ /^(archive_|pg_toast$|pg_catalog$|information_schema$)/ && $4 ~ /^archive_/ {exit 1}' "$dep_file" || fatal 'active-to-archive dependency exists in restored catalog'
}

tmp_dir=""
cleanup() {
  if [[ "${KEEP_VALIDATION_DB:-0}" != "1" && -n "${RESTORE_DB:-}" ]]; then
    dropdb --if-exists "${RESTORE_DB}" >/dev/null 2>&1 || true
  fi
  if [[ -n "$tmp_dir" && -d "$tmp_dir" ]]; then
    rm -rf "$tmp_dir"
  fi
}
trap cleanup EXIT

[[ "${ARCHIVE_WORKFLOW_INTERNAL:-0}" == "1" ]] || fatal 'Direct execution is not supported. Use archive_schemas_workflow.sh verify.'

PACKAGE_DIR=""
RESTORE_DB="archive_schemas_restore_validation"
REGIONAL_KEYS_FILE=""
CID10_KEYS_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --package)
      PACKAGE_DIR="$2"
      shift 2
      ;;
    --restore-db)
      RESTORE_DB="$2"
      shift 2
      ;;
    --regional-keys)
      REGIONAL_KEYS_FILE="$2"
      shift 2
      ;;
    --cid10-keys)
      CID10_KEYS_FILE="$2"
      shift 2
      ;;
    *)
      fatal "unknown option: $1"
      ;;
  esac
done

[[ -n "$PACKAGE_DIR" ]] || fatal 'usage: restore_archive_schemas_validation.sh --package /absolute/path/to/archive_schemas_<...>'
[[ -n "$REGIONAL_KEYS_FILE" ]] || fatal 'restore validation requires --regional-keys'
[[ -n "$CID10_KEYS_FILE" ]] || fatal 'restore validation requires --cid10-keys'

PACKAGE_DIR="$(validate_package_path "$PACKAGE_DIR")"
assert_nonempty_file "${PACKAGE_DIR}/dengue_archive_schemas.dump"
assert_nonempty_file "${PACKAGE_DIR}/archive_inventory.tsv"
assert_nonempty_file "${PACKAGE_DIR}/archive_row_counts.tsv"
assert_nonempty_file "${PACKAGE_DIR}/archive_dependencies.tsv"
assert_nonempty_file "${PACKAGE_DIR}/archive_external_fks.tsv"
assert_nonempty_file "${PACKAGE_DIR}/archive_internal_fks.tsv"
assert_nonempty_file "${PACKAGE_DIR}/dengue_archive_schemas.schema.sql"
assert_regular_file "$REGIONAL_KEYS_FILE"
assert_regular_file "$CID10_KEYS_FILE"

tmp_dir="$(mktemp -d)"

dropdb --if-exists "${RESTORE_DB}" >/dev/null 2>&1 || true
if [[ -n "${RESTORE_TABLESPACE}" ]]; then
  createdb -T template0 -D "${RESTORE_TABLESPACE}" "${RESTORE_DB}"
else
  createdb -T template0 "${RESTORE_DB}"
fi

psql -X -v ON_ERROR_STOP=1 -d "${RESTORE_DB}" <<'SQL'
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
SQL

psql -X -v ON_ERROR_STOP=1 -d "${RESTORE_DB}" -c "\copy \"Dengue_global\".regional (id) FROM '${REGIONAL_KEYS_FILE}' WITH (FORMAT csv, DELIMITER E'\t')"
psql -X -v ON_ERROR_STOP=1 -d "${RESTORE_DB}" -c "\copy \"Dengue_global\".\"CID10\" (codigo) FROM '${CID10_KEYS_FILE}' WITH (FORMAT csv, DELIMITER E'\t')"

if grep -q '"Municipio"\."Historico_alerta"' "${PACKAGE_DIR}/dengue_archive_schemas.schema.sql"; then
  if [[ "${LOAD_HISTORICO_FROM_SOURCE}" != "1" ]]; then
    fatal 'restore validation requires LOAD_HISTORICO_FROM_SOURCE=1 for the archived historico_casos materialized view'
  fi

  psql -X -v ON_ERROR_STOP=1 -d "${SOURCE_DATABASE}" -c \
    "\copy (SELECT \"data_iniSE\", \"SE\", casos_est, casos_est_min, casos_est_max, casos, municipio_geocodigo FROM \"Municipio\".\"Historico_alerta\") TO STDOUT WITH (FORMAT csv, DELIMITER E'\t')" \
    | psql -X -v ON_ERROR_STOP=1 -d "${RESTORE_DB}" -c \
        "\copy \"Municipio\".\"Historico_alerta\" (\"data_iniSE\", \"SE\", casos_est, casos_est_min, casos_est_max, casos, municipio_geocodigo) FROM STDIN WITH (FORMAT csv, DELIMITER E'\t')"

  psql -X -v ON_ERROR_STOP=1 -d "${SOURCE_DATABASE}" -c \
    "\copy (SELECT \"data_iniSE\", \"SE\", casos_est, casos_est_min, casos_est_max, casos, municipio_geocodigo FROM \"Municipio\".\"Historico_alerta_chik\") TO STDOUT WITH (FORMAT csv, DELIMITER E'\t')" \
    | psql -X -v ON_ERROR_STOP=1 -d "${RESTORE_DB}" -c \
        "\copy \"Municipio\".\"Historico_alerta_chik\" (\"data_iniSE\", \"SE\", casos_est, casos_est_min, casos_est_max, casos, municipio_geocodigo) FROM STDIN WITH (FORMAT csv, DELIMITER E'\t')"
fi

pg_restore --exit-on-error --verbose --dbname="${RESTORE_DB}" "${PACKAGE_DIR}/dengue_archive_schemas.dump"

write_archive_inventory_db "${RESTORE_DB}" "${tmp_dir}/archive_inventory.tsv"
write_archive_row_counts_db "${RESTORE_DB}" "${tmp_dir}/archive_row_counts.tsv"
write_archive_dependencies_db "${RESTORE_DB}" "${tmp_dir}/archive_dependencies.tsv"
write_archive_external_fks_db "${RESTORE_DB}" "${tmp_dir}/archive_external_fks.tsv"
write_archive_internal_fks_db "${RESTORE_DB}" "${tmp_dir}/archive_internal_fks.tsv"

assert_external_fk_contract_file "${tmp_dir}/archive_external_fks.tsv" "${tmp_dir}/expected_external_fks.tsv"
assert_no_active_to_archive_dependency_file "${tmp_dir}/archive_dependencies.tsv"

inventory_status=FAIL
row_counts_status=FAIL
dependencies_status=FAIL
external_fk_status=FAIL
internal_fk_status=FAIL

[[ "$(normalized_inventory_sha "${PACKAGE_DIR}/archive_inventory.tsv")" == "$(normalized_inventory_sha "${tmp_dir}/archive_inventory.tsv")" ]] && inventory_status=PASS
[[ "$(sha_file "${PACKAGE_DIR}/archive_row_counts.tsv")" == "$(sha_file "${tmp_dir}/archive_row_counts.tsv")" ]] && row_counts_status=PASS
[[ "$(normalized_dependency_sha "${PACKAGE_DIR}/archive_dependencies.tsv")" == "$(normalized_dependency_sha "${tmp_dir}/archive_dependencies.tsv")" ]] && dependencies_status=PASS
[[ "$(sha_file "${PACKAGE_DIR}/archive_external_fks.tsv")" == "$(sha_file "${tmp_dir}/archive_external_fks.tsv")" ]] && external_fk_status=PASS
[[ "$(sha_file "${PACKAGE_DIR}/archive_internal_fks.tsv")" == "$(sha_file "${tmp_dir}/archive_internal_fks.tsv")" ]] && internal_fk_status=PASS

{
  printf 'check\tstatus\tdetail\n'
  printf 'restore_database\tPASS\t%s\n' "${RESTORE_DB}"
  printf 'inventory_hash_match\t%s\t%s\n' "${inventory_status}" "${RESTORE_DB}"
  printf 'row_count_hash_match\t%s\t%s\n' "${row_counts_status}" "${RESTORE_DB}"
  printf 'dependency_hash_match\t%s\t%s\n' "${dependencies_status}" "${RESTORE_DB}"
  printf 'external_fk_hash_match\t%s\t%s\n' "${external_fk_status}" "${RESTORE_DB}"
  printf 'internal_fk_hash_match\t%s\t%s\n' "${internal_fk_status}" "${RESTORE_DB}"
  printf 'materialized_view_populated\t%s\t%s\n' \
    "$(
      if psql_capture_db "${RESTORE_DB}" -c "SELECT ispopulated::text FROM pg_matviews WHERE schemaname = 'archive_historico_casos' AND matviewname = 'historico_casos'" | grep -Eq '^(t|true)$'; then
        printf PASS
      else
        printf FAIL
      fi
    )" \
    "${RESTORE_DB}"
} > "${PACKAGE_DIR}/restore_validation.tsv"

if grep -q $'\tFAIL\t' "${PACKAGE_DIR}/restore_validation.tsv"; then
  fatal 'restore validation failed'
fi
