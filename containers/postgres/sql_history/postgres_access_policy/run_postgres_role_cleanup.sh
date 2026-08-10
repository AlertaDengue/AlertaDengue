#!/usr/bin/env bash
# Guarded, parameterized PostgreSQL role cleanup for issue #1040.
set -euo pipefail

readonly approval_token='REMOVE_APPROVED_POSTGRES_ROLE_CLEANUP'
readonly audit_root_default='/opt/services/infodengue/database_audits'

usage() {
  cat <<'EOF'
Usage: run_postgres_role_cleanup.sh <preflight|remove|validate> --label LABEL --roles ROLE[,ROLE...] [--databases DB[,DB...]] [--approval REMOVE_APPROVED_POSTGRES_ROLE_CLEANUP] [--confirm-production]

Roles are required. Databases default to dengue,infodengue.
EOF
}

die() { echo "ERROR: $*" >&2; exit 64; }

parse_csv() {
  local value=$1 item
  IFS=',' read -r -a parsed <<< "$value"
  ((${#parsed[@]})) || die 'CSV value may not be empty.'
  for item in "${parsed[@]}"; do
    [[ $item =~ ^[A-Za-z_][A-Za-z0-9_$]*$ ]] || die "Invalid PostgreSQL identifier: $item"
  done
}

contains() { local needle=$1 item; shift; for item in "$@"; do [[ $item == "$needle" ]] && return 0; done; return 1; }

write_header() { printf '%s\n' "$2" > "$1"; }
run_tsv() { local db=$1 out=$2 sql=$3; psql -X -v ON_ERROR_STOP=1 -d "$db" -At -F $'\t' -c "$sql" >> "$out"; }
run_sql() { local db=$1 sql=$2; psql -X -v ON_ERROR_STOP=1 -d "$db" -c "$sql"; }

action=${1:-}
[[ $action == preflight || $action == remove || $action == validate ]] || { usage >&2; exit 64; }
shift
label= roles_csv= databases_csv='dengue,infodengue' approval= confirm_production=false
while (($#)); do
  case $1 in
    --label) label=${2:-}; shift 2 ;;
    --roles) roles_csv=${2:-}; shift 2 ;;
    --databases) databases_csv=${2:-}; shift 2 ;;
    --approval) approval=${2:-}; shift 2 ;;
    --confirm-production) confirm_production=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown or incomplete option: $1" ;;
  esac
done
[[ $label =~ ^[A-Za-z0-9._-]+$ ]] || die 'A safe --label is required.'
[[ -n $roles_csv ]] || die '--roles is required.'
parse_csv "$roles_csv"; roles=("${parsed[@]}")
parse_csv "$databases_csv"; databases=("${parsed[@]}")
command -v psql >/dev/null || die 'psql is required.'

current_user=$(psql -X -At -v ON_ERROR_STOP=1 -d "${databases[0]}" -c 'SELECT current_user')
protected=(postgres dengueadmin mosqlimate_dev "$current_user")
for role in "${roles[@]}"; do
  contains "$role" "${protected[@]}" && die "Protected role may not be selected: $role"
done
if [[ $action == remove ]]; then
  [[ $approval == "$approval_token" ]] || die 'Removal requires the exact --approval token.'
  [[ ${label,,} != production || $confirm_production == true ]] || die 'Removal with --label production requires --confirm-production.'
fi

if [[ $action == preflight || $action == validate ]]; then
  export PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=10min'
else
  export PGOPTIONS='-c statement_timeout=10min'
fi

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
audit_root=${POSTGRES_ROLE_CLEANUP_ROOT:-$audit_root_default}
output_dir="$audit_root/postgres_role_cleanup_${label}_${timestamp}"
mkdir -p "$output_dir"
roles_values=$(printf "('%s')," "${roles[@]}"); roles_values=${roles_values%,}
roles_in=$(printf "'%s'," "${roles[@]}"); roles_in=${roles_in%,}

write_header "$output_dir/command_context.tsv" $'action\tlabel\troles\tdatabases\tutc_timestamp\toutput_dir'
printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$action" "$label" "$roles_csv" "$databases_csv" "$timestamp" "$output_dir" >> "$output_dir/command_context.tsv"

cluster_db=${databases[0]}
write_header "$output_dir/cluster_candidate_roles.tsv" $'role_name\trole_exists'
run_tsv "$cluster_db" "$output_dir/cluster_candidate_roles.tsv" "WITH candidates(role_name) AS (VALUES $roles_values) SELECT c.role_name, (r.oid IS NOT NULL) FROM candidates c LEFT JOIN pg_roles r ON r.rolname=c.role_name ORDER BY c.role_name;"
write_header "$output_dir/cluster_candidate_sessions.tsv" $'datname\tusename\tapplication_name\tclient_addr\tbackend_type\tstate\tbackend_start'
run_tsv "$cluster_db" "$output_dir/cluster_candidate_sessions.tsv" "SELECT COALESCE(datname,''), usename, COALESCE(application_name,''), COALESCE(client_addr::text,''), COALESCE(backend_type,''), COALESCE(state,''), COALESCE(backend_start::text,'') FROM pg_stat_activity WHERE usename IN ($roles_in) ORDER BY datname, usename, backend_start;"
write_header "$output_dir/cluster_candidate_memberships.tsv" $'member_role\tgranted_role\tgrantor_role\tadmin_option'
run_tsv "$cluster_db" "$output_dir/cluster_candidate_memberships.tsv" "SELECT member.rolname, granted.rolname, grantor.rolname, m.admin_option FROM pg_auth_members m JOIN pg_roles member ON member.oid=m.member JOIN pg_roles granted ON granted.oid=m.roleid JOIN pg_roles grantor ON grantor.oid=m.grantor WHERE member.rolname IN ($roles_in) OR granted.rolname IN ($roles_in) ORDER BY 1,2;"
write_header "$output_dir/cluster_database_ownership.tsv" $'database_name\towner_name'
run_tsv "$cluster_db" "$output_dir/cluster_database_ownership.tsv" "SELECT d.datname, r.rolname FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba WHERE r.rolname IN ($roles_in) ORDER BY d.datname;"

collect_database_reports() {
  local db=$1 prefix="$output_dir/$1"
  write_header "${prefix}_candidate_owned_objects.tsv" $'schema_name\tobject_name\tobject_type\towner_name'
  run_tsv "$db" "${prefix}_candidate_owned_objects.tsv" "SELECT * FROM (SELECT n.nspname AS schema_name, c.relname AS object_name, CASE c.relkind WHEN 'r' THEN 'table' WHEN 'p' THEN 'partitioned_table' WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized_view' WHEN 'S' THEN 'sequence' END AS object_type, r.rolname AS owner_name FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.oid=c.relowner WHERE c.relkind IN ('r','p','v','m','S') UNION ALL SELECT n.nspname AS schema_name, p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')' AS object_name, 'routine' AS object_type, r.rolname AS owner_name FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner UNION ALL SELECT n.nspname AS schema_name, t.typname AS object_name, 'type' AS object_type, r.rolname AS owner_name FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace JOIN pg_roles r ON r.oid=t.typowner) owned WHERE owner_name IN ($roles_in) ORDER BY 1,2,3;"
  write_header "${prefix}_candidate_table_grants.tsv" $'grantee\tgrantor\ttable_schema\ttable_name\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_table_grants.tsv" "SELECT grantee, grantor, table_schema, table_name, privilege_type, is_grantable FROM information_schema.role_table_grants WHERE grantee IN ($roles_in) ORDER BY 3,4,1,5;"
  write_header "${prefix}_candidate_sequence_grants.tsv" $'grantee\tgrantor\tobject_schema\tobject_name\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_sequence_grants.tsv" "SELECT grantee, grantor, object_schema, object_name, privilege_type, is_grantable FROM information_schema.role_usage_grants WHERE object_type='SEQUENCE' AND grantee IN ($roles_in) ORDER BY 3,4,1,5;"
  write_header "${prefix}_candidate_schema_grants.tsv" $'schema_name\tgrantee\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_schema_grants.tsv" "SELECT n.nspname, r.rolname, x.privilege_type, x.is_grantable FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) ORDER BY 1,2,3;"
  write_header "${prefix}_candidate_routine_grants.tsv" $'routine_schema\troutine_name\tgrantee\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_routine_grants.tsv" "SELECT n.nspname, p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')', r.rolname, x.privilege_type, x.is_grantable FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN LATERAL aclexplode(p.proacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) ORDER BY 1,2,3,4;"
  write_header "${prefix}_candidate_type_grants.tsv" $'type_schema\ttype_name\tgrantee\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_type_grants.tsv" "SELECT n.nspname, t.typname, r.rolname, x.privilege_type, x.is_grantable FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace CROSS JOIN LATERAL aclexplode(t.typacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) ORDER BY 1,2,3,4;"
  write_header "${prefix}_candidate_database_grants.tsv" $'database_name\tgrantee\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_database_grants.tsv" "SELECT d.datname, r.rolname, x.privilege_type, x.is_grantable FROM pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) ORDER BY 1,2,3;"
  write_header "${prefix}_candidate_default_privileges.tsv" $'definer_role\ttarget_schema\tobject_type\tgrantee\tprivilege_type'
  run_tsv "$db" "${prefix}_candidate_default_privileges.tsv" "SELECT definer.rolname, COALESCE(n.nspname,''), d.defaclobjtype, grantee.rolname, x.privilege_type FROM pg_default_acl d JOIN pg_roles definer ON definer.oid=d.defaclrole LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace CROSS JOIN LATERAL aclexplode(d.defaclacl) x JOIN pg_roles grantee ON grantee.oid=x.grantee WHERE definer.rolname IN ($roles_in) OR grantee.rolname IN ($roles_in) ORDER BY 1,2,3,4,5;"
  write_header "${prefix}_candidate_summary.tsv" $'role_name\towned_objects\texplicit_grants\tdefault_privileges'
  run_tsv "$db" "${prefix}_candidate_summary.tsv" "WITH candidates(role_name) AS (VALUES $roles_values), owned AS (SELECT r.rolname role_name,count(*) n FROM pg_roles r JOIN (SELECT relowner owner_oid FROM pg_class UNION ALL SELECT proowner FROM pg_proc UNION ALL SELECT typowner FROM pg_type) o ON o.owner_oid=r.oid GROUP BY 1), grants AS (SELECT r.rolname role_name,count(*) n FROM (SELECT x.grantee FROM pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) x UNION ALL SELECT x.grantee FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x UNION ALL SELECT x.grantee FROM pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) x UNION ALL SELECT x.grantee FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) x UNION ALL SELECT x.grantee FROM pg_type t CROSS JOIN LATERAL aclexplode(t.typacl) x) a JOIN pg_roles r ON r.oid=a.grantee GROUP BY 1), defaults AS (SELECT r.rolname role_name,count(*) n FROM pg_default_acl d CROSS JOIN LATERAL aclexplode(d.defaclacl) x JOIN pg_roles r ON r.oid=x.grantee GROUP BY 1) SELECT c.role_name,COALESCE(o.n,0),COALESCE(g.n,0),COALESCE(df.n,0) FROM candidates c LEFT JOIN owned o USING(role_name) LEFT JOIN grants g USING(role_name) LEFT JOIN defaults df USING(role_name) ORDER BY 1;"
}

for database in "${databases[@]}"; do collect_database_reports "$database"; done

check_no_dependencies() {
  local failures=0 file
  [[ $(awk -F $'\t' 'NR > 1 && $2 != "t" { count++ } END { print count + 0 }' "$output_dir/cluster_candidate_roles.tsv") -eq 0 ]] || failures=1
  for file in "$output_dir/cluster_candidate_sessions.tsv" "$output_dir/cluster_candidate_memberships.tsv" "$output_dir/cluster_database_ownership.tsv"; do
    [[ $(wc -l < "$file") -eq 1 ]] || failures=1
  done
  for database in "${databases[@]}"; do
    for file in "$output_dir/${database}_candidate_owned_objects.tsv" "$output_dir/${database}_candidate_default_privileges.tsv"; do
      [[ $(wc -l < "$file") -eq 1 ]] || failures=1
    done
  done
  return "$failures"
}

if [[ $action == remove ]]; then
  check_no_dependencies || { echo 'Dependency checks failed; no changes made.' >&2; exit 1; }
  for database in "${databases[@]}"; do
    run_sql "$database" "BEGIN; SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.postgres_role_cleanup')); DO \$\$ BEGIN IF current_database() <> '$database' THEN RAISE EXCEPTION 'wrong database'; END IF; IF pg_is_in_recovery() THEN RAISE EXCEPTION 'server is in recovery'; END IF; IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_roles r ON r.oid=c.relowner WHERE r.rolname IN ($roles_in) UNION ALL SELECT 1 FROM pg_proc p JOIN pg_roles r ON r.oid=p.proowner WHERE r.rolname IN ($roles_in) UNION ALL SELECT 1 FROM pg_type t JOIN pg_roles r ON r.oid=t.typowner WHERE r.rolname IN ($roles_in)) THEN RAISE EXCEPTION 'selected role owns objects'; END IF; IF EXISTS (SELECT 1 FROM pg_default_acl d LEFT JOIN pg_roles owner ON owner.oid=d.defaclrole LEFT JOIN LATERAL aclexplode(d.defaclacl) x ON true LEFT JOIN pg_roles grantee ON grantee.oid=x.grantee WHERE owner.rolname IN ($roles_in) OR grantee.rolname IN ($roles_in)) THEN RAISE EXCEPTION 'selected role has default privileges'; END IF; END \$\$; DO \$\$ DECLARE v record; BEGIN FOR v IN SELECT d.datname,r.rolname,x.privilege_type FROM pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) LOOP EXECUTE format('REVOKE %s ON DATABASE %I FROM %I',v.privilege_type,v.datname,v.rolname); END LOOP; FOR v IN SELECT n.nspname,r.rolname,x.privilege_type FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) LOOP EXECUTE format('REVOKE %s ON SCHEMA %I FROM %I',v.privilege_type,v.nspname,v.rolname); END LOOP; FOR v IN SELECT n.nspname,c.relname,r.rolname,x.privilege_type FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN LATERAL aclexplode(c.relacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) LOOP EXECUTE format('REVOKE %s ON TABLE %I.%I FROM %I',v.privilege_type,v.nspname,v.relname,v.rolname); END LOOP; FOR v IN SELECT n.nspname,p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')',r.rolname,x.privilege_type FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN LATERAL aclexplode(p.proacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) LOOP EXECUTE format('REVOKE %s ON FUNCTION %I.%s FROM %I',v.privilege_type,v.nspname,v.proname,v.rolname); END LOOP; FOR v IN SELECT n.nspname,t.typname,r.rolname,x.privilege_type FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace CROSS JOIN LATERAL aclexplode(t.typacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) LOOP EXECUTE format('REVOKE %s ON TYPE %I.%I FROM %I',v.privilege_type,v.nspname,v.typname,v.rolname); END LOOP; END \$\$; DO \$\$ BEGIN IF EXISTS (SELECT 1 FROM (SELECT x.grantee FROM pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) x UNION ALL SELECT x.grantee FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x UNION ALL SELECT x.grantee FROM pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) x UNION ALL SELECT x.grantee FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) x UNION ALL SELECT x.grantee FROM pg_type t CROSS JOIN LATERAL aclexplode(t.typacl) x) a JOIN pg_roles r ON r.oid=a.grantee WHERE r.rolname IN ($roles_in)) THEN RAISE EXCEPTION 'explicit grants remain'; END IF; END \$\$; COMMIT;"
  done
  for database in "${databases[@]}"; do collect_database_reports "$database"; done
  check_no_dependencies || { echo 'Post-revoke checks failed; roles not dropped.' >&2; exit 1; }
  for role in "${roles[@]}"; do run_sql "$cluster_db" "DROP ROLE \"$role\""; done
fi

write_header "$output_dir/final_status.tsv" $'action\tstatus\tdetail'
if [[ $action == validate ]]; then
  absent=$(psql -X -At -v ON_ERROR_STOP=1 -d "$cluster_db" -c "SELECT count(*) FROM pg_roles WHERE rolname IN ($roles_in)")
  protected_present=$(psql -X -At -v ON_ERROR_STOP=1 -d "$cluster_db" -c "SELECT count(*) FROM pg_roles WHERE rolname IN ('dengueadmin','mosqlimate_dev')")
  mosqlimate_grants=$(psql -X -At -v ON_ERROR_STOP=1 -d dengue -c "SELECT count(*) FROM (SELECT x.grantee FROM pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) x UNION ALL SELECT x.grantee FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x UNION ALL SELECT x.grantee FROM pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) x UNION ALL SELECT x.grantee FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) x UNION ALL SELECT x.grantee FROM pg_type t CROSS JOIN LATERAL aclexplode(t.typacl) x) grants JOIN pg_roles r ON r.oid=grants.grantee WHERE r.rolname='mosqlimate_dev'")
  remaining=0
  for database in "${databases[@]}"; do remaining=$((remaining + $(tail -n +2 "$output_dir/${database}_candidate_table_grants.tsv" | wc -l) + $(tail -n +2 "$output_dir/${database}_candidate_sequence_grants.tsv" | wc -l) + $(tail -n +2 "$output_dir/${database}_candidate_schema_grants.tsv" | wc -l) + $(tail -n +2 "$output_dir/${database}_candidate_routine_grants.tsv" | wc -l) + $(tail -n +2 "$output_dir/${database}_candidate_type_grants.tsv" | wc -l) + $(tail -n +2 "$output_dir/${database}_candidate_database_grants.tsv" | wc -l) )); done
  if [[ $absent -eq 0 && $protected_present -eq 2 && $mosqlimate_grants -gt 0 && $remaining -eq 0 && $(wc -l < "$output_dir/cluster_candidate_sessions.tsv") -eq 1 ]]; then printf 'validate\tPASS\tSelected roles absent; protected roles present; Mosqlimate grants retained; no selected-role grants remain.\n' >> "$output_dir/final_status.tsv"; else printf 'validate\tFAIL\tReview role, session, protected-role, Mosqlimate, and grant reports.\n' >> "$output_dir/final_status.tsv"; exit 1; fi
else
  if [[ $action == remove ]]; then
    printf 'remove\tPASS\tDropped roles: %s\n' "$roles_csv" >> "$output_dir/final_status.tsv"
  elif check_no_dependencies; then
    printf '%s\tPASS\tNo blocking sessions, memberships, ownership, or default privileges found.\n' "$action" >> "$output_dir/final_status.tsv"
  else
    printf '%s\tFAIL\tBlocking dependencies found; review reports.\n' "$action" >> "$output_dir/final_status.tsv"
    [[ $action == preflight ]] && exit 1
  fi
fi
printf '%s complete: %s\n' "$action" "$output_dir"
