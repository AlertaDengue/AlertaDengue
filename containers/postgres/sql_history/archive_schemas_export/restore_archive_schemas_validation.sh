#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
[[ "${ARCHIVE_WORKFLOW_INTERNAL:-0}" == 1 ]] || { printf 'Direct execution is not supported. Use archive_schemas_workflow.sh verify.\n' >&2; exit 1; }
[[ -n "${PGDATABASE:-}" && -n "${PGUSER:-}" ]] || { printf 'PGDATABASE and PGUSER must be configured externally\n' >&2; exit 1; }

fatal() { printf '%s\n' "$1" >&2; exit 1; }
sha_file() { sha256sum "$1" | awk '{print $1}'; }
assert_file() { [[ -f "$1" && ! -L "$1" && -s "$1" ]] || fatal "missing or empty package file: $1"; }

PACKAGE_DIR=""
RESTORE_DB="archive_schemas_restore_validation_$$"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --package) PACKAGE_DIR="$2"; shift 2 ;;
    --restore-db) RESTORE_DB="$2"; shift 2 ;;
    *) fatal "unknown option: $1" ;;
  esac
done
[[ -n "$PACKAGE_DIR" ]] || fatal 'restore validation requires --package'
PACKAGE_DIR="$(realpath "$PACKAGE_DIR")"
[[ "$PACKAGE_DIR" != /tmp/* && "$PACKAGE_DIR" != "$REPO_ROOT"/* ]] || fatal 'package path is unsafe'
assert_file "${PACKAGE_DIR}/dengue_archive_schemas.dump"
assert_file "${PACKAGE_DIR}/archive_inventory.tsv"
assert_file "${PACKAGE_DIR}/archive_row_counts.tsv"
assert_file "${PACKAGE_DIR}/archive_dependencies.tsv"
assert_file "${PACKAGE_DIR}/archive_constraints.tsv"
assert_file "${PACKAGE_DIR}/archive_indexes.tsv"
assert_file "${PACKAGE_DIR}/archive_grants.tsv"

tmp_dir="$(mktemp -d)"
cleanup() { dropdb --if-exists "$RESTORE_DB" >/dev/null 2>&1 || true; rm -rf "$tmp_dir"; }
trap cleanup EXIT
dropdb --if-exists "$RESTORE_DB" >/dev/null 2>&1 || true
createdb -T template0 "$RESTORE_DB"

pg_restore --exit-on-error --section=pre-data --dbname="$RESTORE_DB" "${PACKAGE_DIR}/dengue_archive_schemas.dump"
pg_restore --exit-on-error --section=data --dbname="$RESTORE_DB" "${PACKAGE_DIR}/dengue_archive_schemas.dump"

# SINAN/DBF archives may retain FKs to auth_user. Create only the minimal
# disposable fixture required by restored archive rows before post-data FKs.
PGDATABASE="$RESTORE_DB" psql -X -v ON_ERROR_STOP=1 -f - <<'SQL'
CREATE TABLE IF NOT EXISTS public.auth_user (id integer PRIMARY KEY);
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT table_schema, table_name FROM information_schema.columns
           WHERE column_name = 'user_id' AND table_schema IN ('archive_dbf_upload','archive_sinan_upload')
  LOOP
    EXECUTE format('INSERT INTO public.auth_user(id) SELECT DISTINCT user_id FROM %I.%I WHERE user_id IS NOT NULL ON CONFLICT DO NOTHING', r.table_schema, r.table_name);
  END LOOP;
END $$;
SQL
pg_restore --exit-on-error --section=post-data --dbname="$RESTORE_DB" "${PACKAGE_DIR}/dengue_archive_schemas.dump"

PGDATABASE="$RESTORE_DB" psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 -f - > "${tmp_dir}/inventory.tsv" <<'SQL'
SELECT n.nspname,c.relname,c.relkind,pg_get_userbyid(c.relowner),COALESCE(obj_description(c.oid,'pg_class'),''),COALESCE(array_to_string(c.relacl,','),'')
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname IN ('archive_dbf_upload','archive_sinan_upload') AND c.relkind IN ('r','m','S','i') ORDER BY 1,2,3;
SQL
PGDATABASE="$RESTORE_DB" psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 -f - > "${tmp_dir}/row_counts.tsv" <<'SQL'
SELECT n.nspname,c.relname,c.relkind,'', (xpath('/row/count/text()',query_to_xml(format('SELECT count(*) AS count FROM %I.%I',n.nspname,c.relname),false,true,'')))[1]::text
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('archive_dbf_upload','archive_sinan_upload') AND c.relkind IN ('r','m') ORDER BY 1,2;
SQL
cmp -s "${PACKAGE_DIR}/archive_row_counts.tsv" "${tmp_dir}/row_counts.tsv" || fatal 'restored row counts differ from source'

PGDATABASE="$RESTORE_DB" psql -X -v ON_ERROR_STOP=1 -f - > "${PACKAGE_DIR}/removal_test.tsv" <<'SQL'
BEGIN;
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname IN ('archive_dbf_upload','archive_sinan_upload') AND c.relkind IN ('r','m') ORDER BY 1,2
  LOOP EXECUTE format('DROP TABLE %I.%I',r.nspname,r.relname); END LOOP;
  EXECUTE 'DROP SCHEMA archive_dbf_upload';
  EXECUTE 'DROP SCHEMA archive_sinan_upload';
END $$;
SELECT 'disposable_removal' AS check, CASE WHEN NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname IN ('archive_dbf_upload','archive_sinan_upload')) THEN 'PASS' ELSE 'FAIL' END AS status;
COMMIT;
SQL
grep -q $'disposable_removal\tPASS' "${PACKAGE_DIR}/removal_test.tsv" || fatal 'disposable removal test failed'
printf 'check\tstatus\tdetail\nrestore_database\tPASS\t%s\nrow_count_hash_match\tPASS\t%s\ndisposable_removal\tPASS\t%s\n' "$RESTORE_DB" "$RESTORE_DB" "$RESTORE_DB" > "${PACKAGE_DIR}/restore_validation.tsv"
sha256sum "${PACKAGE_DIR}/restore_validation.tsv" > "${PACKAGE_DIR}/restore_validation.tsv.sha256"
