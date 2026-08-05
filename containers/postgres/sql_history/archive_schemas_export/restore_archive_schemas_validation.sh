#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
[[ "${ARCHIVE_WORKFLOW_INTERNAL:-0}" == 1 ]] || { printf 'Direct execution is not supported. Use archive_schemas_workflow.sh verify.\n' >&2; exit 1; }
[[ -n "${PGDATABASE:-}" && -n "${PGUSER:-}" ]] || { printf 'PGDATABASE and PGUSER must be configured externally\n' >&2; exit 1; }

readonly APPROVED_SCHEMAS=(
  archive_redemet archive_upload archive_ovitrampa archive_alertas_regionais
  archive_cemaden archive_copernicus archive_historico_casos archive_mosqlimate
  archive_tweets archive_dbf_upload archive_sinan_upload
)
fatal() { printf '%s\n' "$1" >&2; exit 1; }
sha_file() { sha256sum "$1" | awk '{print $1}'; }
assert_file() { [[ -f "$1" && ! -L "$1" && -s "$1" ]] || fatal "missing or empty package file: $1"; }
is_approved() { local x="$1" s; for s in "${APPROVED_SCHEMAS[@]}"; do [[ "$x" == "$s" ]] && return 0; done; return 1; }

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
assert_file "${PACKAGE_DIR}/selected_schemas.tsv"
assert_file "${PACKAGE_DIR}/dengue_archive_schemas.dump"
assert_file "${PACKAGE_DIR}/archive_inventory.tsv"
assert_file "${PACKAGE_DIR}/archive_row_counts.tsv"
assert_file "${PACKAGE_DIR}/archive_sequences.tsv"
assert_file "${PACKAGE_DIR}/archive_dependencies.tsv"
assert_file "${PACKAGE_DIR}/archive_constraints.tsv"
assert_file "${PACKAGE_DIR}/archive_indexes.tsv"
assert_file "${PACKAGE_DIR}/archive_grants.tsv"

mapfile -t SELECTED_SCHEMAS < "${PACKAGE_DIR}/selected_schemas.tsv"
(( ${#SELECTED_SCHEMAS[@]} > 0 )) || fatal 'selected_schemas.tsv is empty'
declare -A SEEN=()
for schema in "${SELECTED_SCHEMAS[@]}"; do
  [[ "$schema" =~ ^[a-z_][a-z0-9_]*$ ]] || fatal "invalid selected schema: $schema"
  is_approved "$schema" || fatal "selected schema is not allowlisted: $schema"
  [[ -z "${SEEN[$schema]:-}" ]] || fatal "duplicate selected schema: $schema"
  SEEN[$schema]=1
done
SELECTED_CSV="$(printf "'%s'," "${SELECTED_SCHEMAS[@]}" | sed 's/,$//')"

tmp_dir="$(mktemp -d)"
cleanup() { if [[ "${KEEP_VALIDATION_DB:-0}" != 1 ]]; then dropdb --if-exists "$RESTORE_DB" >/dev/null 2>&1 || true; fi; rm -rf "$tmp_dir"; }
trap cleanup EXIT
dropdb --if-exists "$RESTORE_DB" >/dev/null 2>&1 || true
createdb -T template0 "$RESTORE_DB"

schema_sql="${PACKAGE_DIR}/dengue_archive_schemas.schema.sql"
unknown_external_fk="$(grep -E 'REFERENCES ' "$schema_sql" | grep -Ev 'archive_|auth_user|Dengue_global|Municipio|weather\.copernicus_bra' || true)"
[[ -z "$unknown_external_fk" ]] || fatal 'selected package contains an external FK without a reviewed restore fixture'
needs_auth=0
grep -Eq 'REFERENCES (public\.)?auth_user' "$schema_sql" && needs_auth=1 || true
needs_historico=0
grep -q 'archive_historico_casos' "$schema_sql" && needs_historico=1 || true

PGDATABASE="$RESTORE_DB" psql -X -v ON_ERROR_STOP=1 -f - <<SQL
$(if (( needs_auth )); then cat <<'EOF'
CREATE SCHEMA IF NOT EXISTS public;
CREATE TABLE IF NOT EXISTS public.auth_user (id integer PRIMARY KEY);
EOF
fi)
$(if (( needs_historico )); then cat <<'EOF'
CREATE SCHEMA IF NOT EXISTS "Municipio";
CREATE TABLE "Municipio"."Historico_alerta" ("data_iniSE" date, "SE" integer, casos_est real, casos_est_min integer, casos_est_max integer, casos integer, municipio_geocodigo integer);
CREATE TABLE "Municipio"."Historico_alerta_chik" ("data_iniSE" date, "SE" integer, casos_est real, casos_est_min integer, casos_est_max integer, casos integer, municipio_geocodigo integer);
EOF
fi)
$(if grep -q '"Dengue_global"\.regional' "$schema_sql"; then cat <<'EOF'
CREATE SCHEMA IF NOT EXISTS "Dengue_global";
CREATE TABLE "Dengue_global".regional (id integer PRIMARY KEY);
EOF
fi)
$(if grep -q '"Dengue_global"\."CID10"' "$schema_sql"; then cat <<'EOF'
CREATE SCHEMA IF NOT EXISTS "Dengue_global";
CREATE TABLE "Dengue_global"."CID10" (codigo varchar(20) PRIMARY KEY);
EOF
fi)
$(if grep -q '"Dengue_global"\.regional_saude' "$schema_sql"; then cat <<'EOF'
CREATE SCHEMA IF NOT EXISTS "Dengue_global";
CREATE TABLE "Dengue_global".regional_saude (id integer PRIMARY KEY, municipio_geocodigo integer UNIQUE);
EOF
fi)
$(if grep -q 'weather\.copernicus_bra' "$schema_sql"; then cat <<'EOF'
CREATE SCHEMA IF NOT EXISTS weather;
CREATE TABLE weather.copernicus_bra (date date, geocode bigint);
EOF
fi)
SQL

pg_restore --exit-on-error --section=pre-data --dbname="$RESTORE_DB" "${PACKAGE_DIR}/dengue_archive_schemas.dump"
pg_restore --exit-on-error --section=data --dbname="$RESTORE_DB" "${PACKAGE_DIR}/dengue_archive_schemas.dump"

if (( needs_auth )); then
  PGDATABASE="$RESTORE_DB" psql -X -v ON_ERROR_STOP=1 -f - <<'SQL'
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT table_schema, table_name FROM information_schema.columns WHERE column_name='user_id' AND table_schema IN (SELECT unnest(ARRAY['archive_dbf_upload','archive_sinan_upload']))
  LOOP EXECUTE format('INSERT INTO public.auth_user(id) SELECT DISTINCT user_id FROM %I.%I WHERE user_id IS NOT NULL ON CONFLICT DO NOTHING',r.table_schema,r.table_name); END LOOP;
END $$;
SQL
fi

if (( needs_historico )) && [[ -n "${SOURCE_DATABASE:-$PGDATABASE}" ]]; then
  source_db="${SOURCE_DATABASE:-$PGDATABASE}"
  PGDATABASE="$source_db" psql -X -v ON_ERROR_STOP=1 -c '\copy (SELECT "data_iniSE", "SE", casos_est, casos_est_min, casos_est_max, casos, municipio_geocodigo FROM "Municipio"."Historico_alerta") TO STDOUT WITH (FORMAT csv, DELIMITER E'"'"'\t'"'"')' |
    PGDATABASE="$RESTORE_DB" psql -X -v ON_ERROR_STOP=1 -c '\copy "Municipio"."Historico_alerta" FROM STDIN WITH (FORMAT csv, DELIMITER E'"'"'\t'"'"')'
  PGDATABASE="$source_db" psql -X -v ON_ERROR_STOP=1 -c '\copy (SELECT "data_iniSE", "SE", casos_est, casos_est_min, casos_est_max, casos, municipio_geocodigo FROM "Municipio"."Historico_alerta_chik") TO STDOUT WITH (FORMAT csv, DELIMITER E'"'"'\t'"'"')' |
    PGDATABASE="$RESTORE_DB" psql -X -v ON_ERROR_STOP=1 -c '\copy "Municipio"."Historico_alerta_chik" FROM STDIN WITH (FORMAT csv, DELIMITER E'"'"'\t'"'"')'
fi

PGDATABASE="$RESTORE_DB" psql -X -v ON_ERROR_STOP=1 -f - <<SQL
$(if grep -q '"Dengue_global"\.regional' "$schema_sql"; then cat <<'EOF'
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT table_schema,table_name FROM information_schema.columns WHERE column_name='id_regional' AND table_schema IN (SELECT unnest(ARRAY['archive_alertas_regionais']))
  LOOP EXECUTE format('INSERT INTO "Dengue_global".regional(id) SELECT DISTINCT id_regional FROM %I.%I WHERE id_regional IS NOT NULL ON CONFLICT DO NOTHING',r.table_schema,r.table_name); END LOOP;
END $$;
EOF
fi)
$(if grep -q '"Dengue_global"\."CID10"' "$schema_sql"; then cat <<'EOF'
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT table_schema,table_name FROM information_schema.columns WHERE column_name='CID10_codigo' AND table_schema IN (SELECT unnest(ARRAY['archive_tweets']))
  LOOP EXECUTE format('INSERT INTO "Dengue_global"."CID10"(codigo) SELECT DISTINCT "CID10_codigo" FROM %I.%I WHERE "CID10_codigo" IS NOT NULL ON CONFLICT DO NOTHING',r.table_schema,r.table_name); END LOOP;
END $$;
EOF
fi)
SQL

pg_restore --exit-on-error --section=post-data --dbname="$RESTORE_DB" "${PACKAGE_DIR}/dengue_archive_schemas.dump"

capture_inventory() { PGDATABASE="$RESTORE_DB" psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 -f -; }
capture_inventory > "${tmp_dir}/inventory.tsv" <<SQL
SELECT n.nspname,c.relname,c.relkind,c.oid,pg_get_userbyid(c.relowner),COALESCE(obj_description(c.oid,'pg_class'),''),COALESCE(array_to_string(c.relacl,','),'') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname = ANY(ARRAY[${SELECTED_CSV}]) AND c.relkind IN ('r','m','S','i') ORDER BY 1,2,3;
SQL
capture_inventory > "${tmp_dir}/row_counts.tsv" <<SQL
SELECT n.nspname,c.relname,c.relkind,CASE WHEN c.relkind='m' THEN (SELECT CASE WHEN ispopulated THEN 't' ELSE 'f' END FROM pg_matviews WHERE schemaname=n.nspname AND matviewname=c.relname) ELSE '' END,(xpath('/row/count/text()',query_to_xml(format('SELECT count(*) AS count FROM %I.%I',n.nspname,c.relname),false,true,'')))[1]::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname = ANY(ARRAY[${SELECTED_CSV}]) AND c.relkind IN ('r','m') ORDER BY 1,2;
SQL
capture_inventory > "${tmp_dir}/sequences.tsv" <<SQL
SELECT n.nspname,c.relname,(xpath('/row/last_value/text()',query_to_xml(format('SELECT last_value FROM %I.%I',n.nspname,c.relname),false,true,'')))[1]::text,(xpath('/row/is_called/text()',query_to_xml(format('SELECT is_called FROM %I.%I',n.nspname,c.relname),false,true,'')))[1]::text,pg_get_userbyid(c.relowner) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname = ANY(ARRAY[${SELECTED_CSV}]) AND c.relkind='S' ORDER BY 1,2;
SQL
PGDATABASE="$RESTORE_DB" psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 -f - > "${tmp_dir}/constraints.tsv" <<SQL
SELECT con.conrelid::regclass::text,con.conname,con.contype,pg_get_constraintdef(con.oid) FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname = ANY(ARRAY[${SELECTED_CSV}]) ORDER BY 1,2;
SQL
PGDATABASE="$RESTORE_DB" psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 -f - > "${tmp_dir}/indexes.tsv" <<SQL
SELECT x.indrelid::regclass::text,i.relname,pg_get_indexdef(i.oid) FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_class t ON t.oid=x.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname = ANY(ARRAY[${SELECTED_CSV}]) ORDER BY 1,2;
SQL
PGDATABASE="$RESTORE_DB" psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 -f - > "${tmp_dir}/grants.tsv" <<SQL
SELECT c.oid::regclass::text,pg_get_userbyid(c.relowner),COALESCE(array_to_string(c.relacl,','),'') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname = ANY(ARRAY[${SELECTED_CSV}]) ORDER BY 1;
SQL
PGDATABASE="$RESTORE_DB" psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 -f - > "${tmp_dir}/dependencies.tsv" <<SQL
SELECT obj_ns.nspname,obj.relname,obj.relkind,ref_ns.nspname,ref.relname,ref.relkind,d.deptype FROM pg_depend d JOIN pg_class obj ON obj.oid=d.objid JOIN pg_namespace obj_ns ON obj_ns.oid=obj.relnamespace JOIN pg_class ref ON ref.oid=d.refobjid JOIN pg_namespace ref_ns ON ref_ns.oid=ref.relnamespace WHERE obj_ns.nspname = ANY(ARRAY[${SELECTED_CSV}]) OR ref_ns.nspname = ANY(ARRAY[${SELECTED_CSV}]) ORDER BY 1,2,4,5,7;
SQL
PGDATABASE="$RESTORE_DB" psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 -f - > "${tmp_dir}/external_fks.tsv" <<SQL
SELECT con.conrelid::regclass::text,con.conname,con.confrelid::regclass::text,con.convalidated,con.confdeltype,con.confupdtype FROM pg_constraint con JOIN pg_namespace src_ns ON src_ns.oid=con.connamespace JOIN pg_class ref_cls ON ref_cls.oid=con.confrelid JOIN pg_namespace ref_ns ON ref_ns.oid=ref_cls.relnamespace WHERE con.contype='f' AND src_ns.nspname = ANY(ARRAY[${SELECTED_CSV}]) AND ref_ns.nspname !~ '^archive_' ORDER BY 1,2,3;
SQL
PGDATABASE="$RESTORE_DB" psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 -f - > "${tmp_dir}/internal_fks.tsv" <<SQL
SELECT con.conrelid::regclass::text,con.conname,con.confrelid::regclass::text,con.convalidated,con.confdeltype,con.confupdtype FROM pg_constraint con JOIN pg_namespace src_ns ON src_ns.oid=con.connamespace JOIN pg_class ref_cls ON ref_cls.oid=con.confrelid JOIN pg_namespace ref_ns ON ref_ns.oid=ref_cls.relnamespace WHERE con.contype='f' AND src_ns.nspname = ANY(ARRAY[${SELECTED_CSV}]) AND ref_ns.nspname ~ '^archive_' ORDER BY 1,2,3;
SQL

normalize_inventory() { awk -F $'\t' 'BEGIN{OFS="\t"}{print $1,$2,$3,$5,$6}' "$1" | sort; }
normalize_deps() { awk -F $'\t' '$1 != "pg_toast" && $4 != "pg_toast"' "$1" | sort; }
[[ "$(normalize_inventory "${PACKAGE_DIR}/archive_inventory.tsv")" == "$(normalize_inventory "${tmp_dir}/inventory.tsv")" ]] || fatal 'restored inventory differs'
[[ "$(sha_file "${PACKAGE_DIR}/archive_row_counts.tsv")" == "$(sha_file "${tmp_dir}/row_counts.tsv")" ]] || fatal 'restored row counts differ'
[[ "$(sha_file "${PACKAGE_DIR}/archive_sequences.tsv")" == "$(sha_file "${tmp_dir}/sequences.tsv")" ]] || fatal 'restored sequence state differs'
[[ "$(sha_file "${PACKAGE_DIR}/archive_constraints.tsv")" == "$(sha_file "${tmp_dir}/constraints.tsv")" ]] || fatal 'restored constraints differ'
[[ "$(sha_file "${PACKAGE_DIR}/archive_indexes.tsv")" == "$(sha_file "${tmp_dir}/indexes.tsv")" ]] || fatal 'restored indexes differ'
[[ "$(sha_file "${PACKAGE_DIR}/archive_grants.tsv")" == "$(sha_file "${tmp_dir}/grants.tsv")" ]] || fatal 'restored grants differ'
[[ "$(normalize_deps "${PACKAGE_DIR}/archive_dependencies.tsv")" == "$(normalize_deps "${tmp_dir}/dependencies.tsv")" ]] || fatal 'restored dependencies differ'
[[ "$(sha_file "${PACKAGE_DIR}/archive_external_fks.tsv")" == "$(sha_file "${tmp_dir}/external_fks.tsv")" ]] || fatal 'restored external foreign keys differ'
[[ "$(sha_file "${PACKAGE_DIR}/archive_internal_fks.tsv")" == "$(sha_file "${tmp_dir}/internal_fks.tsv")" ]] || fatal 'restored internal foreign keys differ'

PGDATABASE="$RESTORE_DB" psql -X -A -t -F $'\t' -v ON_ERROR_STOP=1 -f - > "${PACKAGE_DIR}/removal_test.tsv" <<SQL
BEGIN;
DO \$\$ DECLARE r record; BEGIN
  FOR r IN SELECT n.nspname,c.relname,con.conname FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname = ANY(ARRAY[${SELECTED_CSV}]) AND con.contype='f' ORDER BY 1,2,3
  LOOP EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT %I',r.nspname,r.relname,r.conname); END LOOP;
  FOR r IN SELECT n.nspname,c.relname,c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname = ANY(ARRAY[${SELECTED_CSV}]) AND c.relkind IN ('r','m') ORDER BY 1,2 DESC
  LOOP IF r.relkind='m' THEN EXECUTE format('DROP MATERIALIZED VIEW %I.%I',r.nspname,r.relname); ELSE EXECUTE format('DROP TABLE %I.%I',r.nspname,r.relname); END IF; END LOOP;
  FOR r IN SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname = ANY(ARRAY[${SELECTED_CSV}]) AND c.relkind='S' ORDER BY 1,2
  LOOP EXECUTE format('DROP SEQUENCE %I.%I',r.nspname,r.relname); END LOOP;
  FOR r IN SELECT nspname FROM pg_namespace WHERE nspname = ANY(ARRAY[${SELECTED_CSV}]) ORDER BY 1
  LOOP EXECUTE format('DROP SCHEMA %I',r.nspname); END LOOP;
END \$\$;
SELECT 'disposable_removal' AS check, CASE WHEN NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = ANY(ARRAY[${SELECTED_CSV}])) THEN 'PASS' ELSE 'FAIL' END;
COMMIT;
SQL
grep -q $'disposable_removal\tPASS' "${PACKAGE_DIR}/removal_test.tsv" || fatal 'disposable removal test failed'
printf 'check\tstatus\tdetail\nrestore_database\tPASS\t%s\nselected_schemas\tPASS\t%s\ndisposable_removal\tPASS\t%s\n' "$RESTORE_DB" "$(paste -sd, "${PACKAGE_DIR}/selected_schemas.tsv")" "$RESTORE_DB" > "${PACKAGE_DIR}/restore_validation.tsv"
sha256sum "${PACKAGE_DIR}/restore_validation.tsv" > "${PACKAGE_DIR}/restore_validation.tsv.sha256"
