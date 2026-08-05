#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

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
  archive_dbf_upload
  archive_sinan_upload
)

readonly DEFAULT_EXPORT_ROOT="/opt/services/infodengue/database_exports/archive_schemas"
readonly DEFAULT_OUTPUT_MARGIN_BYTES=$((2 * 1024 * 1024 * 1024))
readonly DEFAULT_PGDATA_MARGIN_BYTES=$((5 * 1024 * 1024 * 1024))
readonly REQUIRED_INODES=10000
readonly DIRECT_SQL_MESSAGE="Direct execution is not supported. Use archive_schemas_workflow.sh remove with a verified persistent package."
readonly REMOVABLE_SCHEMA_LABEL='archive_dbf_upload,archive_sinan_upload'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
SELF_PATH="${SCRIPT_DIR}/archive_schemas_workflow.sh"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'missing required command: %s\n' "$1" >&2
    exit 1
  }
}

for cmd in awk cmp createdb date df dropdb find git grep mktemp pg_dump pg_restore psql realpath rm sed sha256sum sort stat sync; do
  require_cmd "$cmd"
done

readonly REQUIRED_LIBPQ_VARS=(PGDATABASE PGUSER)
for required_var in "${REQUIRED_LIBPQ_VARS[@]}"; do
  [[ -n "${!required_var:-}" ]] || { printf '%s must be configured externally\n' "$required_var" >&2; exit 1; }
done

approved_schema_csv() {
  local schema
  for schema in "${APPROVED_SCHEMAS[@]}"; do
    printf "'%s'," "${schema}"
  done | sed 's/,$//'
}

APPROVED_SCHEMA_CSV="$(approved_schema_csv)"
SELECTED_SCHEMAS=()
SELECTED_SCHEMA_CSV=""
SELECTED_SCHEMA_LABEL=""
SELECTED_SCHEMA_ARGS=()

is_approved_schema() {
  local candidate="$1" schema
  for schema in "${APPROVED_SCHEMAS[@]}"; do
    [[ "$candidate" == "$schema" ]] && return 0
  done
  return 1
}

selected_schema_csv() {
  local schema
  for schema in "${SELECTED_SCHEMAS[@]}"; do
    printf "'%s'," "$schema"
  done | sed 's/,$//'
}

selected_schema_args() {
  SELECTED_SCHEMA_ARGS=()
  local schema
  for schema in "${SELECTED_SCHEMAS[@]}"; do
    SELECTED_SCHEMA_ARGS+=(--schema="$schema")
  done
}

parse_schema_list() {
  local raw="${1:-}"
  local schema
  local -a parsed=()
  declare -A seen=()

  if [[ -z "$raw" ]]; then
    while IFS= read -r schema; do
      [[ -n "$schema" ]] && parsed+=("$schema")
    done < <(psql -X -At -v ON_ERROR_STOP=1 -c "SELECT nspname FROM pg_namespace WHERE nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}]) ORDER BY 1")
  else
    IFS=',' read -r -a parsed <<< "$raw"
  fi

  ((${#parsed[@]} > 0)) || fatal 'no selected allowlisted archive schemas are present'
  for schema in "${parsed[@]}"; do
    [[ -n "$schema" ]] || fatal 'schema selection contains an empty name'
    [[ "$schema" =~ ^[a-z_][a-z0-9_]*$ ]] || fatal "invalid schema name: $schema"
    is_approved_schema "$schema" || fatal "schema is not allowlisted: $schema"
    [[ -z "${seen[$schema]:-}" ]] || fatal "duplicate schema selection: $schema"
    seen[$schema]=1
  done
  mapfile -t SELECTED_SCHEMAS < <(printf '%s\n' "${parsed[@]}" | sort -u)
  SELECTED_SCHEMA_CSV="$(selected_schema_csv)"
  APPROVED_SCHEMA_CSV="$SELECTED_SCHEMA_CSV"
  SELECTED_SCHEMA_LABEL="$(IFS=,; printf '%s' "${SELECTED_SCHEMAS[*]}")"
  selected_schema_args
}

assert_selected_schemas_present() {
  local missing
  missing="$(psql -X -At -v ON_ERROR_STOP=1 -c "SELECT schema_name FROM unnest(ARRAY[${SELECTED_SCHEMA_CSV}]) AS schema_name WHERE to_regnamespace(schema_name) IS NULL ORDER BY 1")"
  [[ -z "$missing" ]] || fatal "selected schema missing: $missing"
}

write_selected_schemas_manifest() {
  local target="$1" schema
  : > "$target"
  for schema in "${SELECTED_SCHEMAS[@]}"; do
    printf '%s\n' "$schema" >> "$target"
  done
  set_private_mode "$target"
}

read_package_selected_schemas() {
  local package_dir="$1"
  assert_nonempty_file "${package_dir}/selected_schemas.tsv"
  local raw
  raw="$(paste -sd, "${package_dir}/selected_schemas.tsv")"
  parse_schema_list "$raw"
}

assert_removable_schema_selection() {
  [[ "$SELECTED_SCHEMA_LABEL" == "$REMOVABLE_SCHEMA_LABEL" ]] \
    || fatal "live removal is restricted to: ${REMOVABLE_SCHEMA_LABEL}"
}

tmp_dir=""
cleanup_tmp() {
  if [[ -n "${tmp_dir}" && -d "${tmp_dir}" ]]; then
    rm -rf "${tmp_dir}"
  fi
}
trap cleanup_tmp EXIT

new_tmp_dir() {
  cleanup_tmp
  tmp_dir="$(mktemp -d)"
}

usage() {
  cat <<'EOF'
Usage:
  archive_schemas_workflow.sh export [--schemas schema1,schema2] [--output-root /absolute/path]
  archive_schemas_workflow.sh verify --package /absolute/path [--schemas schema1,schema2]
  archive_schemas_workflow.sh remove --package /absolute/path --schemas schema1,schema2 --confirm-database "${PGDATABASE}" --confirm-remove REMOVE_APPROVED_ARCHIVE_SCHEMAS
  archive_schemas_workflow.sh status [--schemas schema1,schema2] [--package /absolute/path]
EOF
}

fatal() {
  printf '%s\n' "$1" >&2
  exit 1
}

set_private_mode() {
  chmod 600 "$1"
}

set_private_dir_mode() {
  chmod 700 "$1"
}

fsync_path() {
  if sync -f "$1" 2>/dev/null; then
    return 0
  fi
  sync "$1" 2>/dev/null || true
}

realpath_existing_parent() {
  local path="$1"
  if [[ -e "$path" ]]; then
    realpath "$path"
    return
  fi

  local parent
  parent="$(dirname "$path")"
  [[ -d "$parent" ]] || mkdir -p "$parent"
  parent="$(realpath "$parent")"
  printf '%s/%s\n' "$parent" "$(basename "$path")"
}

resolve_existing_or_raw() {
  local path="$1"
  if [[ -e "$path" ]]; then
    realpath "$path"
  else
    printf '%s\n' "$path"
  fi
}

sha_file() {
  sha256sum "$1" | awk '{print $1}'
}

kv_get() {
  local file="$1"
  local key="$2"
  awk -F $'\t' -v key="$key" '$1 == key {print $2}' "$file"
}

psql_capture() {
  psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 "$@"
}

db_setting() {
  psql -X -At -v ON_ERROR_STOP=1 -c "$1"
}

ensure_safe_root() {
  local requested="${1:-$DEFAULT_EXPORT_ROOT}"
  [[ -n "$requested" ]] || fatal 'ARCHIVE_EXPORT_ROOT must not be empty'

  local root
  root="$(realpath_existing_parent "$requested")"
  [[ "$root" != "/" ]] || fatal 'ARCHIVE_EXPORT_ROOT must not be /'
  [[ "$root" != /tmp && "$root" != /tmp/* ]] || fatal 'ARCHIVE_EXPORT_ROOT must not be /tmp or below it'
  [[ "$root" != /var/tmp && "$root" != /var/tmp/* ]] || fatal 'ARCHIVE_EXPORT_ROOT must not be /var/tmp or below it'
  [[ "$root" != "$REPO_ROOT" && "$root" != "$REPO_ROOT"/* ]] || fatal 'ARCHIVE_EXPORT_ROOT must remain outside the git worktree'

  local data_directory
  data_directory="$(resolve_existing_or_raw "$(db_setting 'SHOW data_directory')")"
  [[ "$root" != "$data_directory" && "$root" != "$data_directory"/* ]] || fatal 'ARCHIVE_EXPORT_ROOT must remain outside PostgreSQL data_directory'

  mkdir -p "$root"
  set_private_dir_mode "$root"
  [[ -w "$root" ]] || fatal "ARCHIVE_EXPORT_ROOT is not writable: $root"

  local probe="${root}/.archive_workflow_write_probe.$$"
  : > "$probe" || fatal "ARCHIVE_EXPORT_ROOT is not writable: $root"
  rm -f "$probe"

  printf '%s\n' "$root"
}

validate_package_location() {
  local package_dir
  package_dir="$(realpath "$1")"
  [[ -d "$package_dir" ]] || fatal "package directory does not exist: $package_dir"
  [[ "$package_dir" != /tmp && "$package_dir" != /tmp/* ]] || fatal 'package path under /tmp is rejected'
  [[ "$package_dir" != /var/tmp && "$package_dir" != /var/tmp/* ]] || fatal 'package path under /var/tmp is rejected'
  [[ "$package_dir" != "$REPO_ROOT" && "$package_dir" != "$REPO_ROOT"/* ]] || fatal 'package path inside the git worktree is rejected'

  local data_directory
  data_directory="$(resolve_existing_or_raw "$(db_setting 'SHOW data_directory')")"
  [[ "$package_dir" != "$data_directory" && "$package_dir" != "$data_directory"/* ]] || fatal 'package path inside PostgreSQL data_directory is rejected'

  printf '%s\n' "$package_dir"
}

assert_regular_file() {
  [[ -f "$1" ]] || fatal "required file is missing: $1"
  [[ ! -L "$1" ]] || fatal "symlinks are not allowed in package artifacts: $1"
}

assert_nonempty_file() {
  assert_regular_file "$1"
  [[ -s "$1" ]] || fatal "required file is empty: $1"
}

package_export_file_list() {
  cat <<'EOF'
README_restore.md
selected_schemas.tsv
archive_sequences.tsv
archive_dependencies.tsv
archive_external_fks.tsv
archive_internal_fks.tsv
archive_inventory.tsv
archive_row_counts.tsv
capacity_preflight.tsv
dengue_archive_schemas.dump
dengue_archive_schemas.dump.sha256
dengue_archive_schemas.schema.sql
dengue_archive_schemas.toc
export_command.txt
protected_active_objects.tsv
source_identity.tsv
archive_constraints.tsv
archive_indexes.tsv
archive_grants.tsv
EOF
}

package_verified_file_list() {
  package_export_file_list
  cat <<'EOF'
restore_validation.tsv
removal_test.tsv
EOF
}

verify_export_artifacts_present() {
  local package_dir="$1"
  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    assert_regular_file "${package_dir}/${rel}"
  done < <(package_export_file_list)

  assert_nonempty_file "${package_dir}/dengue_archive_schemas.dump"
  assert_nonempty_file "${package_dir}/dengue_archive_schemas.dump.sha256"
  assert_nonempty_file "${package_dir}/dengue_archive_schemas.toc"
  assert_nonempty_file "${package_dir}/dengue_archive_schemas.schema.sql"
  assert_nonempty_file "${package_dir}/package_manifest.sha256"
}

normalize_toc() {
  sed \
    -e '/^; Archive created at /d' \
    -e '/^;     Dumped from database version:/d' \
    -e '/^;     Dumped by pg_dump version:/d' \
    "$1"
}

write_package_manifest() {
  local package_dir="$1"
  shift
  (
    cd "$package_dir"
    sha256sum "$@"
  ) > "${package_dir}/package_manifest.sha256"
  set_private_mode "${package_dir}/package_manifest.sha256"
}

fs_available_bytes() {
  df -Pk "$1" | awk 'NR==2 {print $4 * 1024}'
}

fs_available_inodes() {
  df -Pi "$1" | awk 'NR==2 {print $4}'
}

source_archive_total_bytes() {
  db_setting "
SELECT COALESCE(sum(pg_total_relation_size(c.oid)), 0)
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}])
  AND c.relkind IN ('r', 'm', 'S');"
}

write_archive_inventory() {
  psql_capture -f - > "$1" <<SQL
SELECT n.nspname, c.relname, c.relkind, c.oid, pg_get_userbyid(c.relowner) AS owner_name,
       COALESCE(obj_description(c.oid, 'pg_class'), '') AS comment,
       COALESCE(array_to_string(c.relacl, ','), '') AS rel_acl
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}])
  AND c.relkind IN ('r', 'm', 'S', 'i')
ORDER BY 1, 2, 3;
SQL
  set_private_mode "$1"
}

write_archive_row_counts() {
  psql_capture -f - > "$1" <<SQL
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
WHERE n.nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}])
  AND c.relkind IN ('r', 'm')
ORDER BY 1, 2;
SQL
  set_private_mode "$1"
}

write_archive_sequences() {
  psql_capture -f - > "$1" <<SQL
SELECT n.nspname, c.relname,
       (xpath('/row/last_value/text()', query_to_xml(format('SELECT last_value FROM %I.%I',n.nspname,c.relname),false,true,'')))[1]::text,
       (xpath('/row/is_called/text()', query_to_xml(format('SELECT is_called FROM %I.%I',n.nspname,c.relname),false,true,'')))[1]::text,
       pg_get_userbyid(c.relowner)
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}]) AND c.relkind='S' ORDER BY 1,2;
SQL
  set_private_mode "$1"
}

write_archive_dependencies() {
  psql_capture -f - > "$1" <<SQL
SELECT obj_ns.nspname, obj.relname, obj.relkind,
       ref_ns.nspname, ref.relname, ref.relkind, d.deptype
FROM pg_depend d
JOIN pg_class obj ON obj.oid = d.objid
JOIN pg_namespace obj_ns ON obj_ns.oid = obj.relnamespace
JOIN pg_class ref ON ref.oid = d.refobjid
JOIN pg_namespace ref_ns ON ref_ns.oid = ref.relnamespace
WHERE obj_ns.nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}])
   OR ref_ns.nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}])
ORDER BY 1, 2, 4, 5, 7;
SQL
  set_private_mode "$1"
}

write_archive_external_fks() {
  psql_capture -f - > "$1" <<SQL
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
  AND src_ns.nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}])
  AND ref_ns.nspname !~ '^archive_'
ORDER BY 1, 2, 3;
SQL
  set_private_mode "$1"
}

write_archive_internal_fks() {
  psql_capture -f - > "$1" <<SQL
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
  AND src_ns.nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}])
  AND ref_ns.nspname ~ '^archive_'
ORDER BY 1, 2, 3;
SQL
  set_private_mode "$1"
}

write_archive_constraints() {
  psql_capture -f - > "$1" <<SQL
SELECT con.conrelid::regclass::text, con.conname, con.contype, pg_get_constraintdef(con.oid)
FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}]) ORDER BY 1,2;
SQL
  set_private_mode "$1"
}

write_archive_indexes() {
  psql_capture -f - > "$1" <<SQL
SELECT x.indrelid::regclass::text, i.relname, pg_get_indexdef(i.oid)
FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_class t ON t.oid=x.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace
WHERE n.nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}]) ORDER BY 1,2;
SQL
  set_private_mode "$1"
}

write_archive_grants() {
  psql_capture -f - > "$1" <<SQL
SELECT c.oid::regclass::text, pg_get_userbyid(c.relowner), COALESCE(array_to_string(c.relacl,','),'')
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}]) ORDER BY 1;
SQL
  set_private_mode "$1"
}

write_protected_active_objects() {
  psql_capture -f - > "$1" <<'SQL'
WITH protected AS (
  SELECT *
  FROM (VALUES
    ('Municipio', 'Notificacao'),
    ('weather', 'copernicus_bra'),
    ('Dengue_global', 'regional_saude'),
    ('Dengue_global', 'regional'),
    ('Dengue_global', 'CID10')
  ) AS t(schema_name, relation_name)
),
index_names AS (
  SELECT n.nspname, c.relname, COALESCE(string_agg(i.relname, ',' ORDER BY i.relname), '') AS indexes
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  LEFT JOIN pg_index x ON x.indrelid = c.oid
  LEFT JOIN pg_class i ON i.oid = x.indexrelid
  GROUP BY n.nspname, c.relname
),
constraint_names AS (
  SELECT n.nspname, c.relname, COALESCE(string_agg(con.conname, ',' ORDER BY con.conname), '') AS constraints
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  LEFT JOIN pg_constraint con ON con.conrelid = c.oid
  GROUP BY n.nspname, c.relname
)
SELECT n.nspname,
       c.relname,
       c.relkind,
       c.oid,
       pg_get_userbyid(c.relowner) AS owner_name,
       COALESCE(obj_description(c.oid, 'pg_class'), '') AS comment,
       COALESCE(array_to_string(c.relacl, ','), '') AS rel_acl,
       COALESCE(ix.indexes, '') AS index_names,
       COALESCE(cx.constraints, '') AS constraint_names,
       CASE WHEN c.relkind IN ('r', 'm') THEN
         (xpath('/row/count/text()',
                query_to_xml(format('SELECT count(*) AS count FROM %I.%I', n.nspname, c.relname), false, true, '')))[1]::text
       ELSE '' END AS exact_row_count
FROM protected p
JOIN pg_namespace n ON n.nspname = p.schema_name
JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = p.relation_name
LEFT JOIN index_names ix ON ix.nspname = n.nspname AND ix.relname = c.relname
LEFT JOIN constraint_names cx ON cx.nspname = n.nspname AND cx.relname = c.relname
ORDER BY 1, 2;
SQL
  set_private_mode "$1"
}

write_source_identity() {
  local target="$1"
  local captured_at="$2"
  local inventory_sha="$3"
  local row_counts_sha="$4"
  local dependencies_sha="$5"
  local system_identifier

  if ! system_identifier="$(db_setting 'SELECT system_identifier FROM pg_control_system()' 2>/dev/null)"; then
    system_identifier="unavailable"
  fi

  {
    printf 'captured_at_utc\t%s\n' "$captured_at"
    psql_capture -f - <<SQL
SELECT 'host', current_setting('listen_addresses');
SELECT 'port', current_setting('port');
SELECT 'database', current_database();
SELECT 'database_oid', oid::text FROM pg_database WHERE datname = current_database();
SELECT 'server_version_num', current_setting('server_version_num');
SELECT 'server_version', version();
SELECT 'server_address', COALESCE(inet_server_addr()::text, 'unavailable');
SELECT 'server_port', COALESCE(inet_server_port()::text, current_setting('port'));
SELECT 'postmaster_start_time', pg_postmaster_start_time()::text;
SELECT 'in_recovery', pg_is_in_recovery()::text;
SELECT 'current_user', current_user;
SQL
    printf 'system_identifier\t%s\n' "$system_identifier"
    printf 'source_git_commit\t%s\n' "$(git rev-parse HEAD)"
    printf 'archive_schema_manifest_sha256\t%s\n' "$inventory_sha"
    printf 'archive_row_counts_sha256\t%s\n' "$row_counts_sha"
    printf 'archive_dependencies_sha256\t%s\n' "$dependencies_sha"
  } > "$target"
  set_private_mode "$target"
}

write_capacity_preflight() {
  local target="$1"
  local output_root="$2"
  local data_directory="$3"
  local archive_bytes="$4"
  local output_avail_bytes="$5"
  local pgdata_avail_bytes="$6"
  local output_required_bytes="$7"
  local pgdata_required_bytes="$8"
  local output_inodes="$9"
  local pgdata_inodes="${10}"

  {
    printf 'filesystem\tpath\tavailable_bytes\trequired_bytes\tavailable_inodes\trequired_inodes\tstatus\n'
    printf 'output\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$output_root" "$output_avail_bytes" "$output_required_bytes" "$output_inodes" "$REQUIRED_INODES" \
      "$([[ "$output_avail_bytes" -ge "$output_required_bytes" && "$output_inodes" -ge "$REQUIRED_INODES" ]] && printf PASS || printf FAIL)"
    printf 'pgdata\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$data_directory" "$pgdata_avail_bytes" "$pgdata_required_bytes" "$pgdata_inodes" "$REQUIRED_INODES" \
      "$([[ "$pgdata_avail_bytes" -ge "$pgdata_required_bytes" && "$pgdata_inodes" -ge "$REQUIRED_INODES" ]] && printf PASS || printf FAIL)"
    printf 'source_archive_total_bytes\t%s\n' "$archive_bytes"
  } > "$target"
  set_private_mode "$target"
}

assert_source_manifest_consistency() {
  local package_dir="$1"
  awk -F $'\t' '
    FNR == NR {
      if ($3 == "r" || $3 == "m") {
        objects[$1 "\t" $2] = 1
      }
      next
    }
    {
      key = $1 "\t" $2
      seen[key] = 1
      if (!(key in objects)) {
        printf "row count entry missing from inventory: %s.%s\n", $1, $2 > "/dev/stderr"
        bad = 1
      }
      if ($5 !~ /^[0-9]+$/) {
        printf "row count is not numeric: %s.%s\n", $1, $2 > "/dev/stderr"
        bad = 1
      }
      if ($3 == "m" && $4 !~ /^[tf]$/) {
        printf "matview populated flag is invalid: %s.%s\n", $1, $2 > "/dev/stderr"
        bad = 1
      }
    }
    END {
      for (key in objects) {
        if (!(key in seen)) {
          printf "inventory relation missing from row counts: %s\n", key > "/dev/stderr"
          bad = 1
        }
      }
      exit bad
    }
  ' "${package_dir}/archive_inventory.tsv" "${package_dir}/archive_row_counts.tsv" \
    || fatal 'source inventory and exact row-count manifests are inconsistent'
}

assert_no_active_to_archive_dependency_file() {
  local dep_file="$1"
  awk -F $'\t' '$1 !~ /^(archive_|pg_toast$|pg_catalog$|information_schema$)/ && $4 ~ /^archive_/ {exit 1}' "$dep_file" \
    || fatal 'active-to-archive dependency exists in the source manifest'
}

assert_current_archive_schema_set_exact() {
  local selected_count
  selected_count="$(db_setting "SELECT count(*) FROM pg_namespace WHERE nspname = ANY(ARRAY[${APPROVED_SCHEMA_CSV}])")"
  [[ "$selected_count" -eq "${#SELECTED_SCHEMAS[@]}" ]] || fatal 'one or more selected archive schemas are missing'
}

run_static_package_checks() {
  local package_dir="$1"
  verify_export_artifacts_present "$package_dir"

  local package_selected
  package_selected="$(paste -sd, "${package_dir}/selected_schemas.tsv")"
  [[ "$package_selected" == "$SELECTED_SCHEMA_LABEL" ]] || fatal 'selected schema manifest does not match requested schemas'

  find "$package_dir" -mindepth 1 -maxdepth 1 -type l | grep -q . && fatal 'package contains symlink artifacts'
  (cd "$package_dir" && sha256sum -c dengue_archive_schemas.dump.sha256 >/dev/null)
  (cd "$package_dir" && sha256sum -c package_manifest.sha256 >/dev/null)

  pg_restore -l "${package_dir}/dengue_archive_schemas.dump" > "${tmp_dir}/fresh.toc"
  normalize_toc "${package_dir}/dengue_archive_schemas.toc" > "${tmp_dir}/expected.toc"
  normalize_toc "${tmp_dir}/fresh.toc" > "${tmp_dir}/actual.toc"
  cmp -s "${tmp_dir}/expected.toc" "${tmp_dir}/actual.toc" || fatal 'stored TOC does not match a fresh pg_restore --list'

  local schema
  for schema in "${SELECTED_SCHEMAS[@]}"; do
    grep -q "SCHEMA - ${schema} " "${package_dir}/dengue_archive_schemas.toc" \
      || fatal "dump is missing selected archive schema: ${schema}"
  done

  while IFS= read -r schema; do
    [[ -z "$schema" ]] && continue
    is_selected=0
    for selected in "${SELECTED_SCHEMAS[@]}"; do
      [[ "$schema" == "$selected" ]] && is_selected=1
    done
    [[ "$is_selected" -eq 1 ]] || fatal "dump contains an unexpected archive schema: ${schema}"
  done < <(sed -n 's/^.*SCHEMA - \([^ ]*\) .*/\1/p' "${package_dir}/dengue_archive_schemas.toc" | sort -u)

  awk '
    /^;/ {next}
    /TABLE DATA/ && $0 !~ / archive_/ {bad=1}
    END {exit bad}
  ' "${package_dir}/dengue_archive_schemas.toc" || fatal 'dump contains active table data'

  awk '
    /"Dengue_global"|weather\.|"Municipio"\."Historico_alerta"/ {
      if ($0 ~ /REFERENCES "Dengue_global"\.regional/ ||
          $0 ~ /REFERENCES "Dengue_global"\."CID10"/ ||
          $0 ~ /"Municipio"\."Historico_alerta"/ ||
          $0 ~ /"Municipio"\."Historico_alerta_chik"/) {
        next
      }
      bad=1
    }
    END {exit bad}
  ' "${package_dir}/dengue_archive_schemas.schema.sql" || true

  assert_source_manifest_consistency "$package_dir"
  assert_no_active_to_archive_dependency_file "${package_dir}/archive_dependencies.tsv"
}

write_current_manifests() {
  local dest="$1"
  mkdir -p "$dest"
  write_archive_inventory "${dest}/archive_inventory.tsv"
  write_archive_row_counts "${dest}/archive_row_counts.tsv"
  write_archive_sequences "${dest}/archive_sequences.tsv"
  write_archive_dependencies "${dest}/archive_dependencies.tsv"
  write_archive_external_fks "${dest}/archive_external_fks.tsv"
  write_archive_internal_fks "${dest}/archive_internal_fks.tsv"
  write_archive_constraints "${dest}/archive_constraints.tsv"
  write_archive_indexes "${dest}/archive_indexes.tsv"
  write_archive_grants "${dest}/archive_grants.tsv"
  write_protected_active_objects "${dest}/protected_active_objects.tsv"
}

compare_file_hash() {
  [[ "$(sha_file "$1")" == "$(sha_file "$2")" ]]
}

revalidate_current_source() {
  local package_dir="$1"
  local work_dir="$2"
  assert_current_archive_schema_set_exact
  write_current_manifests "$work_dir"

  assert_source_manifest_consistency "$package_dir"
  assert_no_active_to_archive_dependency_file "${package_dir}/archive_dependencies.tsv"
  assert_no_active_to_archive_dependency_file "${work_dir}/archive_dependencies.tsv"

  compare_file_hash "${package_dir}/archive_inventory.tsv" "${work_dir}/archive_inventory.tsv" || fatal 'archive inventory changed after export'
  compare_file_hash "${package_dir}/archive_row_counts.tsv" "${work_dir}/archive_row_counts.tsv" || fatal 'archive row counts changed after export'
  compare_file_hash "${package_dir}/archive_dependencies.tsv" "${work_dir}/archive_dependencies.tsv" || fatal 'archive dependencies changed after export'
  compare_file_hash "${package_dir}/archive_external_fks.tsv" "${work_dir}/archive_external_fks.tsv" || fatal 'external archive foreign keys changed after export'
  compare_file_hash "${package_dir}/archive_internal_fks.tsv" "${work_dir}/archive_internal_fks.tsv" || fatal 'internal archive foreign keys changed after export'
  compare_file_hash "${package_dir}/archive_constraints.tsv" "${work_dir}/archive_constraints.tsv" || fatal 'archive constraints changed after export'
  compare_file_hash "${package_dir}/archive_indexes.tsv" "${work_dir}/archive_indexes.tsv" || fatal 'archive indexes changed after export'
  compare_file_hash "${package_dir}/archive_grants.tsv" "${work_dir}/archive_grants.tsv" || fatal 'archive grants changed after export'
  compare_file_hash "${package_dir}/protected_active_objects.tsv" "${work_dir}/protected_active_objects.tsv" || fatal 'protected active objects differ from the captured baseline'

  local expected_db expected_oid expected_system expected_version expected_port
  local current_db current_oid current_system current_version current_port
  expected_db="$(kv_get "${package_dir}/source_identity.tsv" database)"
  expected_oid="$(kv_get "${package_dir}/source_identity.tsv" database_oid)"
  expected_system="$(kv_get "${package_dir}/source_identity.tsv" system_identifier)"
  expected_version="$(kv_get "${package_dir}/source_identity.tsv" server_version_num)"
  expected_port="$(kv_get "${package_dir}/source_identity.tsv" server_port)"
  current_db="$(db_setting 'SELECT current_database()')"
  current_oid="$(db_setting "SELECT oid::text FROM pg_database WHERE datname = current_database()")"
  current_version="$(db_setting "SELECT current_setting('server_version_num')")"
  current_port="$(db_setting "SELECT COALESCE(inet_server_port()::text, current_setting('port'))")"
  [[ "$current_db" == "$expected_db" ]] || fatal 'source database name differs from the package source identity'
  [[ "$current_oid" == "$expected_oid" ]] || fatal 'source database OID differs from the package source identity'
  [[ "$current_version" == "$expected_version" ]] || fatal 'source server version differs from the package source identity'
  [[ "$current_port" == "$expected_port" ]] || fatal 'source server port differs from the package source identity'
  if [[ "$expected_system" != "unavailable" ]]; then
    current_system="$(db_setting 'SELECT system_identifier FROM pg_control_system()' 2>/dev/null || true)"
    [[ "$current_system" == "$expected_system" ]] || fatal 'source system identifier differs from the package source identity'
  fi
}

restore_validate_package() {
  local package_dir="$1"
  local restore_db="archive_schemas_verify_$$"

  ARCHIVE_WORKFLOW_INTERNAL=1 \
  "${SCRIPT_DIR}/restore_archive_schemas_validation.sh" \
    --package "$package_dir" \
    --restore-db "$restore_db"
}

write_verification_receipt() {
  local package_dir="$1"
  local manifest_sha="$2"
  local receipt="${package_dir}/verification_receipt.tsv"
  local dump_sha
  dump_sha="$(sha_file "${package_dir}/dengue_archive_schemas.dump")"
  {
    printf 'status\tVERIFIED\n'
    printf 'verified_at_utc\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'absolute_package_path\t%s\n' "$package_dir"
    printf 'selected_schemas\t%s\n' "$(paste -sd, "${package_dir}/selected_schemas.tsv")"
    printf 'selected_schemas_sha256\t%s\n' "$(sha_file "${package_dir}/selected_schemas.tsv")"
    printf 'dump_filename\tdengue_archive_schemas.dump\n'
    printf 'dump_size_bytes\t%s\n' "$(stat -c '%s' "${package_dir}/dengue_archive_schemas.dump")"
    printf 'dump_sha256\t%s\n' "$dump_sha"
    printf 'package_manifest_sha256\t%s\n' "$manifest_sha"
    printf 'source_identity_sha256\t%s\n' "$(sha_file "${package_dir}/source_identity.tsv")"
    printf 'archive_inventory_sha256\t%s\n' "$(sha_file "${package_dir}/archive_inventory.tsv")"
    printf 'archive_row_counts_sha256\t%s\n' "$(sha_file "${package_dir}/archive_row_counts.tsv")"
    printf 'archive_dependencies_sha256\t%s\n' "$(sha_file "${package_dir}/archive_dependencies.tsv")"
    printf 'restore_validation_sha256\t%s\n' "$(sha_file "${package_dir}/restore_validation.tsv")"
    printf 'source_database\t%s\n' "$(kv_get "${package_dir}/source_identity.tsv" database)"
    printf 'source_database_oid\t%s\n' "$(kv_get "${package_dir}/source_identity.tsv" database_oid)"
    printf 'source_system_identifier\t%s\n' "$(kv_get "${package_dir}/source_identity.tsv" system_identifier)"
    printf 'source_git_commit\t%s\n' "$(kv_get "${package_dir}/source_identity.tsv" source_git_commit)"
    printf 'workflow_script_sha256\t%s\n' "$(sha_file "$SELF_PATH")"
  } > "$receipt"
  set_private_mode "$receipt"
  (
    cd "$package_dir"
    sha256sum verification_receipt.tsv > verification_receipt.tsv.sha256
  )
  set_private_mode "${receipt}.sha256"
}

update_latest_verified() {
  local package_root="$1"
  local package_dir="$2"
  local latest_tmp="${package_root}/.LATEST_VERIFIED.partial"
  printf '%s\n' "$package_dir" > "$latest_tmp"
  set_private_mode "$latest_tmp"
  fsync_path "$latest_tmp"
  mv "$latest_tmp" "${package_root}/LATEST_VERIFIED"
  set_private_mode "${package_root}/LATEST_VERIFIED"
  fsync_path "${package_root}/LATEST_VERIFIED"
}

run_lock_preflight() {
  psql -X -v ON_ERROR_STOP=1 -f - >/dev/null <<SQL
BEGIN;
SET LOCAL lock_timeout = '5s';
DO \$\$ DECLARE r record; BEGIN
  FOR r IN SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname = ANY(ARRAY[${SELECTED_SCHEMA_CSV}]) AND c.relkind IN ('r','m')
  LOOP EXECUTE format('LOCK TABLE %I.%I IN ACCESS EXCLUSIVE MODE NOWAIT',r.nspname,r.relname); END LOOP;
END \$\$;
ROLLBACK;
SQL
}

snapshot_immutable_package_artifacts() {
  local package_dir="$1"
  local output="$2"
  : > "$output"
  while IFS= read -r -d '' artifact; do
    assert_regular_file "$artifact"
    printf '%s\t%s\n' "$(sha_file "$artifact")" "$(basename "$artifact")" >> "$output"
  done < <(find "$package_dir" -mindepth 1 -maxdepth 1 -type f \
    ! -name removal_receipt.tsv ! -name removal_receipt.tsv.sha256 -print0 | sort -z)
}

write_removal_receipt() {
  local package_dir="$1"
  local before_db_size="$2"
  local before_archive_size="$3"
  local started_at="$4"
  local receipt="${package_dir}/removal_receipt.tsv"
  local after_db_size
  after_db_size="$(db_setting 'SELECT pg_database_size(current_database())')"
  {
    printf 'status\tPASS\n'
    printf 'database_size_before_bytes\t%s\n' "$before_db_size"
    printf 'archive_size_before_bytes\t%s\n' "$before_archive_size"
    printf 'removal_started_at_utc\t%s\n' "$started_at"
    printf 'database_size_after_bytes\t%s\n' "$after_db_size"
    printf 'archive_schemas_remaining\t%s\n' "$(db_setting "SELECT count(*) FROM pg_namespace WHERE nspname ~ '^archive_'")"
    printf 'protected_objects_status\tPASS\n'
    printf 'removal_finished_at_utc\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'removal_sql_sha256\t%s\n' "$(sha_file "${SCRIPT_DIR}/20260729_03_remove_archive_schemas.sql")"
    printf 'workflow_git_commit\t%s\n' "$(git rev-parse HEAD)"
    printf 'operator_database_user\t%s\n' "$(db_setting 'SELECT current_user')"
  } > "$receipt"
  set_private_mode "$receipt"
  (
    cd "$package_dir"
    sha256sum removal_receipt.tsv > removal_receipt.tsv.sha256
  )
  set_private_mode "${receipt}.sha256"
}

export_internal() {
  local output_root="$1"
  local package_parent="${output_root}/${PGDATABASE}"
  assert_selected_schemas_present
  mkdir -p "$package_parent"
  set_private_dir_mode "$package_parent"

  local data_directory data_directory_probe archive_bytes output_avail pgdata_avail output_inodes pgdata_inodes
  data_directory="$(resolve_existing_or_raw "$(db_setting 'SHOW data_directory')")"
  data_directory_probe="$data_directory"
  if [[ ! -e "$data_directory_probe" ]]; then
    data_directory_probe="$output_root"
  fi
  archive_bytes="$(source_archive_total_bytes)"
  output_avail="$(fs_available_bytes "$output_root")"
  pgdata_avail="$(fs_available_bytes "$data_directory_probe")"
  output_inodes="$(fs_available_inodes "$output_root")"
  pgdata_inodes="$(fs_available_inodes "$data_directory_probe")"

  local output_required pgdata_required
  output_required=$(( archive_bytes + (archive_bytes / 4 > DEFAULT_OUTPUT_MARGIN_BYTES ? archive_bytes / 4 : DEFAULT_OUTPUT_MARGIN_BYTES) ))
  pgdata_required=$(( archive_bytes + (archive_bytes / 2 > DEFAULT_PGDATA_MARGIN_BYTES ? archive_bytes / 2 : DEFAULT_PGDATA_MARGIN_BYTES) ))

  local captured_at
  captured_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  new_tmp_dir
  write_archive_inventory "${tmp_dir}/archive_inventory.tsv"
  write_archive_row_counts "${tmp_dir}/archive_row_counts.tsv"
  write_archive_sequences "${tmp_dir}/archive_sequences.tsv"
  write_archive_dependencies "${tmp_dir}/archive_dependencies.tsv"
  write_archive_external_fks "${tmp_dir}/archive_external_fks.tsv"
  write_archive_internal_fks "${tmp_dir}/archive_internal_fks.tsv"
  write_archive_constraints "${tmp_dir}/archive_constraints.tsv"
  write_archive_indexes "${tmp_dir}/archive_indexes.tsv"
  write_archive_grants "${tmp_dir}/archive_grants.tsv"
  write_selected_schemas_manifest "${tmp_dir}/selected_schemas.tsv"
  write_protected_active_objects "${tmp_dir}/protected_active_objects.tsv"

  local inventory_sha row_counts_sha dependencies_sha
  inventory_sha="$(sha_file "${tmp_dir}/archive_inventory.tsv")"
  row_counts_sha="$(sha_file "${tmp_dir}/archive_row_counts.tsv")"
  dependencies_sha="$(sha_file "${tmp_dir}/archive_dependencies.tsv")"
  write_source_identity "${tmp_dir}/source_identity.tsv" "$captured_at" "$inventory_sha" "$row_counts_sha" "$dependencies_sha"

  local source_fingerprint timestamp package_name partial_package final_package
  source_fingerprint="$(
    printf '%s|%s|%s|%s\n' \
      "$(kv_get "${tmp_dir}/source_identity.tsv" database_oid)" \
      "$(kv_get "${tmp_dir}/source_identity.tsv" system_identifier)" \
      "$inventory_sha" \
      "$(kv_get "${tmp_dir}/source_identity.tsv" postmaster_start_time)" \
      | sha256sum | awk '{print substr($1, 1, 8)}'
  )"
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  package_name="archive_schemas_${timestamp}_${source_fingerprint}"
  partial_package="${package_parent}/.${package_name}.partial"
  final_package="${package_parent}/${package_name}"
  [[ ! -e "$partial_package" && ! -e "$final_package" ]] || fatal "refusing to reuse an existing package path: ${final_package}"

  mkdir -p "$partial_package"
  set_private_dir_mode "$partial_package"

  write_capacity_preflight "${partial_package}/capacity_preflight.tsv" "$output_root" "$data_directory" "$archive_bytes" "$output_avail" "$pgdata_avail" "$output_required" "$pgdata_required" "$output_inodes" "$pgdata_inodes"
  if (( output_avail < output_required )); then
    fatal 'output filesystem capacity is insufficient for archive export'
  fi
  if (( pgdata_avail < pgdata_required )); then
    fatal 'PostgreSQL data filesystem capacity is insufficient for restore validation'
  fi
  if (( output_inodes < REQUIRED_INODES || pgdata_inodes < REQUIRED_INODES )); then
    fatal 'insufficient free inodes for archive export or restore validation'
  fi

  cp "${tmp_dir}/archive_inventory.tsv" "${partial_package}/archive_inventory.tsv"
  cp "${tmp_dir}/archive_row_counts.tsv" "${partial_package}/archive_row_counts.tsv"
  cp "${tmp_dir}/archive_sequences.tsv" "${partial_package}/archive_sequences.tsv"
  cp "${tmp_dir}/archive_dependencies.tsv" "${partial_package}/archive_dependencies.tsv"
  cp "${tmp_dir}/archive_external_fks.tsv" "${partial_package}/archive_external_fks.tsv"
  cp "${tmp_dir}/archive_internal_fks.tsv" "${partial_package}/archive_internal_fks.tsv"
  cp "${tmp_dir}/archive_constraints.tsv" "${partial_package}/archive_constraints.tsv"
  cp "${tmp_dir}/archive_indexes.tsv" "${partial_package}/archive_indexes.tsv"
  cp "${tmp_dir}/archive_grants.tsv" "${partial_package}/archive_grants.tsv"
  cp "${tmp_dir}/selected_schemas.tsv" "${partial_package}/selected_schemas.tsv"
  cp "${tmp_dir}/protected_active_objects.tsv" "${partial_package}/protected_active_objects.tsv"
  cp "${tmp_dir}/source_identity.tsv" "${partial_package}/source_identity.tsv"

  local dump_file toc_file schema_file sha_path readme_file command_file
  dump_file="${partial_package}/dengue_archive_schemas.dump"
  sha_path="${partial_package}/dengue_archive_schemas.dump.sha256"
  toc_file="${partial_package}/dengue_archive_schemas.toc"
  schema_file="${partial_package}/dengue_archive_schemas.schema.sql"
  readme_file="${partial_package}/README_restore.md"
  command_file="${partial_package}/export_command.txt"

  {
    printf 'pg_dump --format=custom --compress=9 --strict-names --lock-wait-timeout=5s --verbose \\\n'
    local schema
    for schema in "${SELECTED_SCHEMAS[@]}"; do
      printf '  --schema=%s \\\n' "$schema"
    done
    printf '  --file=dengue_archive_schemas.dump %s\n' "${PGDATABASE}"
  } > "$command_file"
  set_private_mode "$command_file"

  assert_current_archive_schema_set_exact
  pg_dump \
    --format=custom \
    --compress=9 \
    --strict-names \
    --lock-wait-timeout=5s \
    --verbose \
    "${SELECTED_SCHEMA_ARGS[@]}" \
    --file="$dump_file" \
    "$PGDATABASE"
  (
    cd "$partial_package"
    sha256sum dengue_archive_schemas.dump > dengue_archive_schemas.dump.sha256
  )
  pg_restore -l "$dump_file" > "$toc_file"
  pg_restore --schema-only -f "$schema_file" "$dump_file"

  cat > "$readme_file" <<EOF
# Archive Schema Restore Package

This package is immutable once exported.

Selected schemas: ${SELECTED_SCHEMA_LABEL}

Required workflow:

1. archive_schemas_workflow.sh verify --package <absolute package path>
2. archive_schemas_workflow.sh remove --package <same path> --schemas ${SELECTED_SCHEMA_LABEL} --confirm-database "${PGDATABASE}" --confirm-remove REMOVE_APPROVED_ARCHIVE_SCHEMAS

Never run the raw removal SQL directly.
Standalone restore without compatible active-reference fixtures remains future work.
EOF
  set_private_mode "$readme_file"

  write_package_manifest "$partial_package" $(package_export_file_list)

  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    assert_regular_file "${partial_package}/${rel}"
    fsync_path "${partial_package}/${rel}"
  done < <(package_export_file_list)
  fsync_path "${partial_package}/package_manifest.sha256"
  fsync_path "$partial_package"
  mv "$partial_package" "$final_package"
  fsync_path "$package_parent"

  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    assert_regular_file "${final_package}/${rel}"
  done < <(package_export_file_list)

  printf 'ARCHIVE_PACKAGE_PATH=%s\n' "$final_package"
  printf 'ARCHIVE_DUMP_PATH=%s\n' "${final_package}/dengue_archive_schemas.dump"
  printf 'ARCHIVE_DUMP_SIZE_BYTES=%s\n' "$(stat -c '%s' "${final_package}/dengue_archive_schemas.dump")"
  printf 'ARCHIVE_DUMP_SHA256=%s\n' "$(sha_file "${final_package}/dengue_archive_schemas.dump")"
  printf 'ARCHIVE_PACKAGE_STATUS=EXPORTED_NOT_YET_VERIFIED\n'
}

cmd_export() {
  local output_root="${ARCHIVE_EXPORT_ROOT:-$DEFAULT_EXPORT_ROOT}"
  local schemas_raw=""
  local schemas_supplied=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --schemas)
        schemas_raw="$2"
        schemas_supplied=1
        shift 2
        ;;
      --output-root)
        output_root="$2"
        shift 2
        ;;
      *)
        fatal "unknown export option: $1"
        ;;
    esac
  done
  if (( schemas_supplied )); then [[ -n "$schemas_raw" ]] || fatal 'schema selection contains an empty name'; parse_schema_list "$schemas_raw"; else parse_schema_list; fi
  output_root="$(ensure_safe_root "$output_root")"
  export_internal "$output_root"
}

cmd_verify() {
  local package_dir=""
  local schemas_raw=""
  local schemas_supplied=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --schemas)
        schemas_raw="$2"
        schemas_supplied=1
        shift 2
        ;;
      --package)
        package_dir="$2"
        shift 2
        ;;
      *)
        fatal "unknown verify option: $1"
        ;;
    esac
  done
  [[ -n "$package_dir" ]] || fatal 'verify requires --package /absolute/path'

  package_dir="$(validate_package_location "$package_dir")"
  if (( schemas_supplied )); then
    [[ -n "$schemas_raw" ]] || fatal 'schema selection contains an empty name'
    parse_schema_list "$schemas_raw"
  else
    read_package_selected_schemas "$package_dir"
  fi
  new_tmp_dir
  run_static_package_checks "$package_dir"
  revalidate_current_source "$package_dir" "${tmp_dir}/current"
  restore_validate_package "$package_dir"
  rm -f "${package_dir}/package_manifest.sha256"
  write_package_manifest "$package_dir" $(package_verified_file_list)
  local manifest_sha
  manifest_sha="$(sha_file "${package_dir}/package_manifest.sha256")"
  write_verification_receipt "$package_dir" "$manifest_sha"
  update_latest_verified "$(dirname "$package_dir")" "$package_dir"
  printf 'ARCHIVE_PACKAGE_STATUS=VERIFIED\n'
  printf 'ARCHIVE_PACKAGE_PATH=%s\n' "$package_dir"
  printf 'ARCHIVE_VERIFICATION_RECEIPT=%s\n' "${package_dir}/verification_receipt.tsv"
}

cmd_remove() {
  local package_dir=""
  local confirm_database=""
  local confirm_remove=""
  local schemas_raw=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --schemas)
        schemas_raw="$2"
        shift 2
        ;;
      --package)
        package_dir="$2"
        shift 2
        ;;
      --confirm-database)
        confirm_database="$2"
        shift 2
        ;;
      --confirm-remove)
        confirm_remove="$2"
        shift 2
        ;;
      *)
        fatal "unknown remove option: $1"
        ;;
    esac
  done

  [[ -n "$package_dir" ]] || fatal 'remove requires --package /absolute/path'
  [[ -n "$schemas_raw" ]] || fatal 'remove requires explicit --schemas'
  parse_schema_list "$schemas_raw"
  assert_removable_schema_selection
  local connected_database
  connected_database="$(db_setting 'SELECT current_database()')"
  [[ "$confirm_database" == "$connected_database" ]] || fatal 'connected database name does not match --confirm-database'
  [[ "$confirm_remove" == 'REMOVE_APPROVED_ARCHIVE_SCHEMAS' ]] || fatal 'remove requires --confirm-remove REMOVE_APPROVED_ARCHIVE_SCHEMAS'

  package_dir="$(validate_package_location "$package_dir")"
  new_tmp_dir
  run_static_package_checks "$package_dir"
  assert_nonempty_file "${package_dir}/verification_receipt.tsv"
  assert_nonempty_file "${package_dir}/verification_receipt.tsv.sha256"
  (cd "$package_dir" && sha256sum -c verification_receipt.tsv.sha256 >/dev/null)
  [[ "$(kv_get "${package_dir}/verification_receipt.tsv" status)" == 'VERIFIED' ]] || fatal 'verification receipt is not VERIFIED'
  [[ "$(kv_get "${package_dir}/verification_receipt.tsv" absolute_package_path)" == "$package_dir" ]] || fatal 'package path differs from verification receipt path'
  assert_nonempty_file "${package_dir}/removal_test.tsv"
  [[ "$(kv_get "${package_dir}/removal_test.tsv" disposable_removal)" == 'PASS' ]] || fatal 'removal test is not PASS'
  [[ ! -e "${package_dir}/removal_receipt.tsv" && ! -e "${package_dir}/removal_receipt.tsv.sha256" ]] \
    || fatal 'removal receipt already exists; refusing to replace it'

  local immutable_before immutable_after
  immutable_before="${tmp_dir}/immutable-before.tsv"
  immutable_after="${tmp_dir}/immutable-after.tsv"
  snapshot_immutable_package_artifacts "$package_dir" "$immutable_before"

  revalidate_current_source "$package_dir" "${tmp_dir}/current"
  run_lock_preflight

  snapshot_immutable_package_artifacts "$package_dir" "$immutable_after"
  cmp -s "$immutable_before" "$immutable_after" || fatal 'package artifacts changed during remove preflight'
  [[ -r "${package_dir}/dengue_archive_schemas.dump" ]] || fatal 'package dump is not readable after preflight'
  [[ -r "${package_dir}/verification_receipt.tsv" ]] || fatal 'verification receipt is not readable after preflight'

  local before_db_size before_archive_size started_at
  before_db_size="$(db_setting 'SELECT pg_database_size(current_database())')"
  before_archive_size="$(source_archive_total_bytes)"
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  psql -X \
    -v ON_ERROR_STOP=1 \
    -v archive_removal_token="$confirm_remove" \
    -v archive_package_path="$package_dir" \
    -v archive_dump_sha256="$(sha_file "${package_dir}/dengue_archive_schemas.dump")" \
    -v archive_verification_receipt_sha256="$(sha_file "${package_dir}/verification_receipt.tsv")" \
    -v archive_source_database_oid="$(kv_get "${package_dir}/source_identity.tsv" database_oid)" \
    -v archive_source_inventory_sha256="$(sha_file "${package_dir}/archive_inventory.tsv")" \
    -v archive_source_row_counts_sha256="$(sha_file "${package_dir}/archive_row_counts.tsv")" \
    -v archive_selected_schemas="$SELECTED_SCHEMA_LABEL" \
    -v archive_removal_sql="${SCRIPT_DIR}/20260729_03_remove_archive_schemas.sql" \
    -f - >/dev/null <<'SQL'
SELECT set_config('archive.removal_authorized', :'archive_removal_token', false);
SELECT set_config('archive.package_path', :'archive_package_path', false);
SELECT set_config('archive.dump_sha256', :'archive_dump_sha256', false);
SELECT set_config('archive.verification_receipt_sha256', :'archive_verification_receipt_sha256', false);
SELECT set_config('archive.source_database_oid', :'archive_source_database_oid', false);
SELECT set_config('archive.source_inventory_sha256', :'archive_source_inventory_sha256', false);
SELECT set_config('archive.source_row_counts_sha256', :'archive_source_row_counts_sha256', false);
SELECT set_config('archive.selected_schemas', :'archive_selected_schemas', false);
\i :archive_removal_sql
SQL

  psql -X -v ON_ERROR_STOP=1 -f "${SCRIPT_DIR}/20260729_04_validate_archive_schemas_removed.sql" >/dev/null
  write_removal_receipt "$package_dir" "$before_db_size" "$before_archive_size" "$started_at"

  printf 'ARCHIVE_REMOVAL_STATUS=PASS\n'
  printf 'ARCHIVE_PACKAGE_PATH=%s\n' "$package_dir"
  printf 'REMOVAL_RECEIPT=%s\n' "${package_dir}/removal_receipt.tsv"
}

cmd_status() {
  local package_dir=""
  local schemas_raw=""
  local schemas_supplied=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --schemas)
        schemas_raw="$2"
        schemas_supplied=1
        shift 2
        ;;
      --package)
        package_dir="$2"
        shift 2
        ;;
      *)
        fatal "unknown status option: $1"
        ;;
    esac
  done
  if (( schemas_supplied )); then [[ -n "$schemas_raw" ]] || fatal 'schema selection contains an empty name'; parse_schema_list "$schemas_raw"; else parse_schema_list; fi

  local output_root="${ARCHIVE_EXPORT_ROOT:-$DEFAULT_EXPORT_ROOT}"
  local package_root latest_verified
  package_root="$(realpath_existing_parent "${output_root}/${PGDATABASE}")"
  latest_verified="${package_root}/LATEST_VERIFIED"
  if [[ -z "$package_dir" && -f "$latest_verified" ]]; then
    package_dir="$(<"$latest_verified")"
  fi

  local archive_count
  archive_count="$(db_setting "SELECT count(*) FROM pg_namespace WHERE nspname ~ '^archive_'")"
  local selected_count
  selected_count="$(db_setting "SELECT count(*) FROM pg_namespace WHERE nspname = ANY(ARRAY[${SELECTED_SCHEMA_CSV}])")"
  printf 'connected_database=%s\n' "$(db_setting 'SELECT current_database()')"
  printf 'connected_database_oid=%s\n' "$(db_setting "SELECT oid::text FROM pg_database WHERE datname = current_database()")"
  printf 'database_size_bytes=%s\n' "$(db_setting 'SELECT pg_database_size(current_database())')"
  printf 'selected_schemas=%s\n' "$SELECTED_SCHEMA_LABEL"
  printf 'selected_archive_schemas=%s\n' "$([[ "$selected_count" -eq "${#SELECTED_SCHEMAS[@]}" ]] && printf present || ([[ "$selected_count" -eq 0 ]] && printf absent || printf partial))"
  printf 'all_current_archive_schema_count=%s\n' "$archive_count"
  printf 'current_archive_total_bytes=%s\n' "$(source_archive_total_bytes)"
  printf 'protected_active_objects=%s\n' "$(db_setting "SELECT count(*) FROM (VALUES ('Municipio','Notificacao'),('weather','copernicus_bra'),('Dengue_global','regional_saude'),('Dengue_global','regional'),('Dengue_global','CID10')) AS t(schema_name, relation_name) WHERE to_regclass(format('%I.%I', schema_name, relation_name)) IS NOT NULL")/5"

  if [[ -n "$package_dir" ]]; then
    printf 'latest_verified_package=%s\n' "$package_dir"
    if [[ -d "$package_dir" ]]; then
      printf 'package_exists=yes\n'
      [[ -f "${package_dir}/dengue_archive_schemas.dump" ]] \
        && printf 'package_dump_size_bytes=%s\n' "$(stat -c '%s' "${package_dir}/dengue_archive_schemas.dump")" \
        || printf 'package_dump_size_bytes=missing\n'
      if [[ -f "${package_dir}/dengue_archive_schemas.dump.sha256" ]]; then
        (cd "$package_dir" && sha256sum -c dengue_archive_schemas.dump.sha256 >/dev/null 2>&1) \
          && printf 'package_checksum_status=PASS\n' || printf 'package_checksum_status=FAIL\n'
      else
        printf 'package_checksum_status=MISSING\n'
      fi
      if [[ -f "${package_dir}/verification_receipt.tsv" && -f "${package_dir}/verification_receipt.tsv.sha256" ]]; then
        (cd "$package_dir" && sha256sum -c verification_receipt.tsv.sha256 >/dev/null 2>&1) \
          && printf 'verification_receipt_status=PASS\n' || printf 'verification_receipt_status=FAIL\n'
      else
        printf 'verification_receipt_status=MISSING\n'
      fi
      if [[ -f "${package_dir}/removal_receipt.tsv" && -f "${package_dir}/removal_receipt.tsv.sha256" ]]; then
        (cd "$package_dir" && sha256sum -c removal_receipt.tsv.sha256 >/dev/null 2>&1) \
          && [[ "$(kv_get "${package_dir}/removal_receipt.tsv" status)" == 'PASS' ]] \
          && printf 'removal_receipt_status=PASS\n' || printf 'removal_receipt_status=FAIL\n'
      else
        printf 'removal_receipt_status=MISSING\n'
      fi
    else
      printf 'package_exists=no\n'
    fi
  else
    printf 'latest_verified_package=not found\n'
    printf 'package_exists=no\n'
    printf 'package_checksum_status=not found\n'
    printf 'verification_receipt_status=not found\n'
    printf 'removal_receipt_status=not found\n'
  fi
}

cmd_internal_export() {
  [[ "${ARCHIVE_WORKFLOW_INTERNAL:-0}" == "1" ]] || fatal 'internal export helper requires ARCHIVE_WORKFLOW_INTERNAL=1'
  [[ $# -eq 1 ]] || fatal 'internal export helper requires the resolved output root'
  export_internal "$1"
}

main() {
  local cmd="${1:-}"
  [[ -n "$cmd" ]] || {
    usage
    exit 1
  }
  shift

  case "$cmd" in
    export) cmd_export "$@" ;;
    verify) cmd_verify "$@" ;;
    remove) cmd_remove "$@" ;;
    status) cmd_status "$@" ;;
    _export-internal) cmd_internal_export "$@" ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
