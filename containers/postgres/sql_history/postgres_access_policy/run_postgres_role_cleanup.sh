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
  write_header "${prefix}_candidate_table_grants.tsv" $'grantee\tgrantor\trelation_schema\trelation_name\trelation_kind\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_table_grants.tsv" "SELECT grantee.rolname, grantor.rolname, n.nspname, c.relname, c.relkind, x.privilege_type, x.is_grantable FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN LATERAL aclexplode(c.relacl) x JOIN pg_roles grantee ON grantee.oid=x.grantee JOIN pg_roles grantor ON grantor.oid=x.grantor WHERE c.relkind IN ('r','p','v','m','f') AND grantee.rolname IN ($roles_in) ORDER BY 3,4,1,6;"
  write_header "${prefix}_candidate_sequence_grants.tsv" $'grantee\tgrantor\tsequence_schema\tsequence_name\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_sequence_grants.tsv" "SELECT grantee.rolname, grantor.rolname, n.nspname, c.relname, x.privilege_type, x.is_grantable FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN LATERAL aclexplode(c.relacl) x JOIN pg_roles grantee ON grantee.oid=x.grantee JOIN pg_roles grantor ON grantor.oid=x.grantor WHERE c.relkind='S' AND grantee.rolname IN ($roles_in) ORDER BY 3,4,1,5;"
  write_header "${prefix}_candidate_schema_grants.tsv" $'schema_name\tgrantee\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_schema_grants.tsv" "SELECT n.nspname, r.rolname, x.privilege_type, x.is_grantable FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) ORDER BY 1,2,3;"
  write_header "${prefix}_candidate_routine_grants.tsv" $'routine_schema\troutine_name\tgrantee\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_routine_grants.tsv" "SELECT n.nspname, p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')', r.rolname, x.privilege_type, x.is_grantable FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN LATERAL aclexplode(p.proacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) ORDER BY 1,2,3,4;"
  write_header "${prefix}_candidate_type_grants.tsv" $'type_schema\ttype_name\tgrantee\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_type_grants.tsv" "SELECT n.nspname, t.typname, r.rolname, x.privilege_type, x.is_grantable FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace CROSS JOIN LATERAL aclexplode(t.typacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) ORDER BY 1,2,3,4;"
  write_header "${prefix}_candidate_database_grants.tsv" $'database_name\tgrantee\tprivilege_type\tis_grantable'
  run_tsv "$db" "${prefix}_candidate_database_grants.tsv" "SELECT d.datname, r.rolname, x.privilege_type, x.is_grantable FROM pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) ORDER BY 1,2,3;"
  write_header "${prefix}_candidate_default_privileges.tsv" $'definer_role\ttarget_schema\tobject_type\tobject_type_name\tgrantee\tprivilege_type\tcleanup_class'
  run_tsv "$db" "${prefix}_candidate_default_privileges.tsv" "SELECT definer.rolname, COALESCE(n.nspname,''), d.defaclobjtype, CASE d.defaclobjtype WHEN 'r' THEN 'TABLES' WHEN 'S' THEN 'SEQUENCES' WHEN 'f' THEN 'FUNCTIONS' WHEN 'T' THEN 'TYPES' WHEN 'n' THEN 'SCHEMAS' END, COALESCE(grantee.rolname,''), COALESCE(x.privilege_type,''), CASE WHEN definer.rolname IN ($roles_in) THEN 'BLOCKING_DEFINER_DEFAULT_PRIVILEGE' WHEN grantee.rolname IN ($roles_in) THEN 'REVOCABLE_GRANTEE_DEFAULT_PRIVILEGE' END FROM pg_default_acl d JOIN pg_roles definer ON definer.oid=d.defaclrole LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace LEFT JOIN LATERAL aclexplode(d.defaclacl) x ON true LEFT JOIN pg_roles grantee ON grantee.oid=x.grantee WHERE definer.rolname IN ($roles_in) OR grantee.rolname IN ($roles_in) ORDER BY 1,2,3,5,6;"
  write_header "${prefix}_candidate_summary.tsv" $'role_name\towned_objects\tdatabase_grants\tschema_grants\trelation_grants\tsequence_grants\troutine_grants\ttype_grants\texplicit_grants\tdefault_privileges_as_grantee\tdefault_privileges_as_definer\trevocable_default_privileges\tblocking_default_privileges'
  run_tsv "$db" "${prefix}_candidate_summary.tsv" "WITH candidates(role_name) AS (VALUES $roles_values), owned AS (SELECT r.rolname role_name,count(*) n FROM pg_roles r JOIN (SELECT relowner owner_oid FROM pg_class WHERE relkind IN ('r','p','v','m','f','S') UNION ALL SELECT proowner FROM pg_proc UNION ALL SELECT typowner FROM pg_type) o ON o.owner_oid=r.oid GROUP BY 1), acl_grants AS (SELECT r.rolname role_name,'database' scope FROM pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) x JOIN pg_roles r ON r.oid=x.grantee UNION ALL SELECT r.rolname,'schema' FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x JOIN pg_roles r ON r.oid=x.grantee UNION ALL SELECT r.rolname,'relation' FROM pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE c.relkind IN ('r','p','v','m','f') UNION ALL SELECT r.rolname,'sequence' FROM pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE c.relkind='S' UNION ALL SELECT r.rolname,'routine' FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) x JOIN pg_roles r ON r.oid=x.grantee UNION ALL SELECT r.rolname,'type' FROM pg_type t CROSS JOIN LATERAL aclexplode(t.typacl) x JOIN pg_roles r ON r.oid=x.grantee), grant_counts AS (SELECT role_name,count(*) FILTER (WHERE scope='database') database_grants,count(*) FILTER (WHERE scope='schema') schema_grants,count(*) FILTER (WHERE scope='relation') relation_grants,count(*) FILTER (WHERE scope='sequence') sequence_grants,count(*) FILTER (WHERE scope='routine') routine_grants,count(*) FILTER (WHERE scope='type') type_grants FROM acl_grants GROUP BY 1), defaults_as_grantee AS (SELECT r.rolname role_name,count(*) n FROM pg_default_acl d CROSS JOIN LATERAL aclexplode(d.defaclacl) x JOIN pg_roles r ON r.oid=x.grantee GROUP BY 1), defaults_as_definer AS (SELECT r.rolname role_name,count(*) n FROM pg_default_acl d JOIN pg_roles r ON r.oid=d.defaclrole GROUP BY 1) SELECT c.role_name,COALESCE(o.n,0),COALESCE(g.database_grants,0),COALESCE(g.schema_grants,0),COALESCE(g.relation_grants,0),COALESCE(g.sequence_grants,0),COALESCE(g.routine_grants,0),COALESCE(g.type_grants,0),COALESCE(g.database_grants,0)+COALESCE(g.schema_grants,0)+COALESCE(g.relation_grants,0)+COALESCE(g.sequence_grants,0)+COALESCE(g.routine_grants,0)+COALESCE(g.type_grants,0),COALESCE(dg.n,0),COALESCE(dd.n,0),COALESCE(dg.n,0),COALESCE(dd.n,0) FROM candidates c LEFT JOIN owned o USING(role_name) LEFT JOIN grant_counts g USING(role_name) LEFT JOIN defaults_as_grantee dg USING(role_name) LEFT JOIN defaults_as_definer dd USING(role_name) ORDER BY 1;"
}

for database in "${databases[@]}"; do collect_database_reports "$database"; done

check_no_dependencies() {
  local failures=0 file
  [[ $(awk -F $'\t' 'NR > 1 && $2 != "t" { count++ } END { print count + 0 }' "$output_dir/cluster_candidate_roles.tsv") -eq 0 ]] || failures=1
  for file in "$output_dir/cluster_candidate_sessions.tsv" "$output_dir/cluster_candidate_memberships.tsv" "$output_dir/cluster_database_ownership.tsv"; do
    [[ $(wc -l < "$file") -eq 1 ]] || failures=1
  done
  for database in "${databases[@]}"; do
    [[ $(wc -l < "$output_dir/${database}_candidate_owned_objects.tsv") -eq 1 ]] || failures=1
    [[ $(awk -F $'\t' 'NR > 1 && $7 == "BLOCKING_DEFINER_DEFAULT_PRIVILEGE" { count++ } END { print count + 0 }' "$output_dir/${database}_candidate_default_privileges.tsv") -eq 0 ]] || failures=1
  done
  return "$failures"
}

assert_no_catalog_acl_grants() {
  local db=$1
  run_sql "$db" "DO \$\$ BEGIN IF EXISTS (SELECT 1 FROM (SELECT x.grantee FROM pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) x UNION ALL SELECT x.grantee FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x UNION ALL SELECT x.grantee FROM pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) x WHERE c.relkind IN ('r','p','v','m','f','S') UNION ALL SELECT x.grantee FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) x UNION ALL SELECT x.grantee FROM pg_type t CROSS JOIN LATERAL aclexplode(t.typacl) x) catalog_acl JOIN pg_roles r ON r.oid=catalog_acl.grantee WHERE r.rolname IN ($roles_in)) THEN RAISE EXCEPTION 'catalog ACL grants remain for selected roles'; END IF; END \$\$;"
}

if [[ $action == remove ]]; then
  check_no_dependencies || { echo 'Dependency checks failed; no changes made.' >&2; exit 1; }
  for database in "${databases[@]}"; do
    run_sql "$database" "BEGIN; SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.postgres_role_cleanup')); DO \$\$ BEGIN IF current_database() <> '$database' THEN RAISE EXCEPTION 'wrong database'; END IF; IF pg_is_in_recovery() THEN RAISE EXCEPTION 'server is in recovery'; END IF; IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_roles r ON r.oid=c.relowner WHERE r.rolname IN ($roles_in) UNION ALL SELECT 1 FROM pg_proc p JOIN pg_roles r ON r.oid=p.proowner WHERE r.rolname IN ($roles_in) UNION ALL SELECT 1 FROM pg_type t JOIN pg_roles r ON r.oid=t.typowner WHERE r.rolname IN ($roles_in)) THEN RAISE EXCEPTION 'selected role owns objects'; END IF; IF EXISTS (SELECT 1 FROM pg_default_acl d JOIN pg_roles definer ON definer.oid=d.defaclrole WHERE definer.rolname IN ($roles_in)) THEN RAISE EXCEPTION 'selected role defines default privileges'; END IF; END \$\$; DO \$\$ DECLARE v record; BEGIN FOR v IN SELECT definer.rolname AS definer_role,n.nspname AS target_schema,CASE d.defaclobjtype WHEN 'r' THEN 'TABLES' WHEN 'S' THEN 'SEQUENCES' WHEN 'f' THEN 'FUNCTIONS' WHEN 'T' THEN 'TYPES' WHEN 'n' THEN 'SCHEMAS' END AS object_type_name,grantee.rolname AS grantee,x.privilege_type FROM pg_default_acl d JOIN pg_roles definer ON definer.oid=d.defaclrole LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace CROSS JOIN LATERAL aclexplode(d.defaclacl) x JOIN pg_roles grantee ON grantee.oid=x.grantee WHERE grantee.rolname IN ($roles_in) AND grantee.rolname NOT IN ('dengueadmin','mosqlimate_dev') LOOP IF v.target_schema IS NULL THEN EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I REVOKE %s ON %s FROM %I',v.definer_role,v.privilege_type,v.object_type_name,v.grantee); ELSE EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I REVOKE %s ON %s FROM %I',v.definer_role,v.target_schema,v.privilege_type,v.object_type_name,v.grantee); END IF; END LOOP; IF EXISTS (SELECT 1 FROM pg_default_acl d CROSS JOIN LATERAL aclexplode(d.defaclacl) x JOIN pg_roles grantee ON grantee.oid=x.grantee WHERE grantee.rolname IN ($roles_in)) THEN RAISE EXCEPTION 'default privilege grants remain for selected roles'; END IF; IF EXISTS (SELECT 1 FROM pg_default_acl d JOIN pg_roles definer ON definer.oid=d.defaclrole WHERE definer.rolname IN ($roles_in)) THEN RAISE EXCEPTION 'selected role still defines default privileges'; END IF; FOR v IN SELECT d.datname,r.rolname,x.privilege_type FROM pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) LOOP EXECUTE format('REVOKE %s ON DATABASE %I FROM %I',v.privilege_type,v.datname,v.rolname); END LOOP; FOR v IN SELECT n.nspname,r.rolname,x.privilege_type FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) LOOP EXECUTE format('REVOKE %s ON SCHEMA %I FROM %I',v.privilege_type,v.nspname,v.rolname); END LOOP; FOR v IN SELECT n.nspname,c.relname,r.rolname,x.privilege_type FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN LATERAL aclexplode(c.relacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) LOOP EXECUTE format('REVOKE %s ON TABLE %I.%I FROM %I',v.privilege_type,v.nspname,v.relname,v.rolname); END LOOP; FOR v IN SELECT n.nspname,p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')',r.rolname,x.privilege_type FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN LATERAL aclexplode(p.proacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) LOOP EXECUTE format('REVOKE %s ON FUNCTION %I.%s FROM %I',v.privilege_type,v.nspname,v.proname,v.rolname); END LOOP; FOR v IN SELECT n.nspname,t.typname,r.rolname,x.privilege_type FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace CROSS JOIN LATERAL aclexplode(t.typacl) x JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname IN ($roles_in) LOOP EXECUTE format('REVOKE %s ON TYPE %I.%I FROM %I',v.privilege_type,v.nspname,v.typname,v.rolname); END LOOP; END \$\$; DO \$\$ BEGIN IF EXISTS (SELECT 1 FROM (SELECT x.grantee FROM pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) x UNION ALL SELECT x.grantee FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x UNION ALL SELECT x.grantee FROM pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) x UNION ALL SELECT x.grantee FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) x UNION ALL SELECT x.grantee FROM pg_type t CROSS JOIN LATERAL aclexplode(t.typacl) x) a JOIN pg_roles r ON r.oid=a.grantee WHERE r.rolname IN ($roles_in)) THEN RAISE EXCEPTION 'explicit grants remain'; END IF; END \$\$; COMMIT;"
    assert_no_catalog_acl_grants "$database"
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
  remaining_explicit_grants=0 remaining_default_privileges=0
  for database in "${databases[@]}"; do
    remaining_explicit_grants=$((remaining_explicit_grants + $(tail -n +2 "$output_dir/${database}_candidate_table_grants.tsv" | wc -l) + $(tail -n +2 "$output_dir/${database}_candidate_sequence_grants.tsv" | wc -l) + $(tail -n +2 "$output_dir/${database}_candidate_schema_grants.tsv" | wc -l) + $(tail -n +2 "$output_dir/${database}_candidate_routine_grants.tsv" | wc -l) + $(tail -n +2 "$output_dir/${database}_candidate_type_grants.tsv" | wc -l) + $(tail -n +2 "$output_dir/${database}_candidate_database_grants.tsv" | wc -l) ))
    remaining_default_privileges=$((remaining_default_privileges + $(tail -n +2 "$output_dir/${database}_candidate_default_privileges.tsv" | wc -l) ))
  done
  if [[ $absent -eq 0 && $protected_present -eq 2 && $mosqlimate_grants -gt 0 && $remaining_explicit_grants -eq 0 && $remaining_default_privileges -eq 0 && $(wc -l < "$output_dir/cluster_candidate_sessions.tsv") -eq 1 ]]; then printf 'validate\tPASS\tSelected roles absent; protected roles present; Mosqlimate grants retained; no selected-role explicit or default privileges remain.\n' >> "$output_dir/final_status.tsv"; else printf 'validate\tFAIL\tReview role, session, protected-role, Mosqlimate, explicit-grant, and default-privilege reports.\n' >> "$output_dir/final_status.tsv"; exit 1; fi
else
  if [[ $action == remove ]]; then
    printf 'remove\tPASS\tDropped roles: %s\n' "$roles_csv" >> "$output_dir/final_status.tsv"
  elif check_no_dependencies; then
    printf '%s\tPASS\tNo blocking sessions, memberships, ownership, or default privileges defined by selected roles found; default privileges granted to selected roles are revocable.\n' "$action" >> "$output_dir/final_status.tsv"
  else
    printf '%s\tFAIL\tBlocking dependencies found; review reports.\n' "$action" >> "$output_dir/final_status.tsv"
    [[ $action == preflight ]] && exit 1
  fi
fi
printf '%s complete: %s\n' "$action" "$output_dir"
