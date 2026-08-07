#!/usr/bin/env bash
# Read-only PostgreSQL role and privilege audit for issue #1040.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <development|staging|production>" >&2
  exit 64
fi

environment_label=$1
if [[ ! $environment_label =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Environment label may contain only letters, numbers, dot, underscore, and hyphen." >&2
  exit 64
fi

command -v psql >/dev/null || { echo "psql is required." >&2; exit 69; }

# Enforce read-only statements even when a connection defaults to read-write.
export PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=10min"

audit_root=${POSTGRES_ACCESS_AUDIT_ROOT:-/opt/services/infodengue/database_audits}
audited_utc=$(date -u +%Y%m%dT%H%M%SZ)
output_dir="${audit_root}/postgres_access_policy_${environment_label}_${audited_utc}"
mkdir -p "$output_dir"

candidate_roles_sql="'infodenguedev', 'analista', 'mosqlimate_dev', 'dengueadmin'"
databases=(dengue infodengue)

write_header() {
  printf '%s\n' "$2" > "$1"
}

run_tsv() {
  local database=$1 output=$2 sql=$3
  psql -X -v ON_ERROR_STOP=1 -d "$database" -At -F $'\t' -c "$sql" >> "$output"
}

cluster_database=${databases[0]}
write_header "$output_dir/server_identity.tsv" \
  $'environment_label\tcurrent_database\tdatabase_oid\tcurrent_user\tinet_server_addr\tinet_server_port\tpg_is_in_recovery\tserver_version\taudited_utc'
run_tsv "$cluster_database" "$output_dir/server_identity.tsv" "
  SELECT '${environment_label}', current_database(), (SELECT oid FROM pg_database WHERE datname = current_database()),
         current_user, COALESCE(inet_server_addr()::text, ''), COALESCE(inet_server_port()::text, ''),
         pg_is_in_recovery(), version(), '${audited_utc}';"

write_header "$output_dir/roles.tsv" \
  $'rolname\trolcanlogin\trolsuper\trolcreatedb\trolcreaterole\trolreplication\trolbypassrls\trolconnlimit\trolvaliduntil'
run_tsv "$cluster_database" "$output_dir/roles.tsv" "
  SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, rolconnlimit,
         COALESCE(rolvaliduntil::text, '')
  FROM pg_roles ORDER BY rolname;"

write_header "$output_dir/candidate_roles.tsv" \
  $'role_name\trole_exists\trolcanlogin\trolsuper\trolcreatedb\trolcreaterole\trolreplication\trolbypassrls\trolvaliduntil'
run_tsv "$cluster_database" "$output_dir/candidate_roles.tsv" "
  WITH candidates(role_name) AS (VALUES ('infodenguedev'), ('analista'), ('mosqlimate_dev'), ('dengueadmin'))
  SELECT c.role_name, r.oid IS NOT NULL, COALESCE(r.rolcanlogin::text, ''), COALESCE(r.rolsuper::text, ''),
         COALESCE(r.rolcreatedb::text, ''), COALESCE(r.rolcreaterole::text, ''), COALESCE(r.rolreplication::text, ''),
         COALESCE(r.rolbypassrls::text, ''), COALESCE(r.rolvaliduntil::text, '')
  FROM candidates c LEFT JOIN pg_roles r ON r.rolname = c.role_name ORDER BY c.role_name;"

write_header "$output_dir/role_memberships.tsv" $'member_role\tgranted_role\tgrantor_role\tadmin_option'
run_tsv "$cluster_database" "$output_dir/role_memberships.tsv" "
  SELECT member.rolname, granted.rolname, grantor.rolname, m.admin_option
  FROM pg_auth_members m JOIN pg_roles member ON member.oid = m.member
       JOIN pg_roles granted ON granted.oid = m.roleid JOIN pg_roles grantor ON grantor.oid = m.grantor
  ORDER BY member.rolname, granted.rolname;"

for sessions_file in active_sessions candidate_active_sessions; do
  write_header "$output_dir/${sessions_file}.tsv" \
    $'datname\tusename\tapplication_name\tclient_addr\tbackend_type\tstate\tbackend_start\txact_start\tquery_start\twait_event_type\twait_event'
done
run_tsv "$cluster_database" "$output_dir/active_sessions.tsv" "
  SELECT COALESCE(datname, ''), COALESCE(usename, ''), COALESCE(application_name, ''), COALESCE(client_addr::text, ''),
         COALESCE(backend_type, ''), COALESCE(state, ''), COALESCE(backend_start::text, ''), COALESCE(xact_start::text, ''),
         COALESCE(query_start::text, ''), COALESCE(wait_event_type, ''), COALESCE(wait_event, '')
  FROM pg_stat_activity ORDER BY datname, usename, backend_start;"
run_tsv "$cluster_database" "$output_dir/candidate_active_sessions.tsv" "
  SELECT COALESCE(datname, ''), COALESCE(usename, ''), COALESCE(application_name, ''), COALESCE(client_addr::text, ''),
         COALESCE(backend_type, ''), COALESCE(state, ''), COALESCE(backend_start::text, ''), COALESCE(xact_start::text, ''),
         COALESCE(query_start::text, ''), COALESCE(wait_event_type, ''), COALESCE(wait_event, '')
  FROM pg_stat_activity WHERE usename IN (${candidate_roles_sql}) ORDER BY datname, usename, backend_start;"

write_header "$output_dir/database_ownership.tsv" $'database_name\towner_name'
run_tsv "$cluster_database" "$output_dir/database_ownership.tsv" "
  SELECT d.datname, r.rolname FROM pg_database d JOIN pg_roles r ON r.oid = d.datdba ORDER BY d.datname;"

for database in "${databases[@]}"; do
  prefix="$output_dir/${database}"
  write_header "${prefix}_schemas.tsv" $'schema_name\towner_name'
  run_tsv "$database" "${prefix}_schemas.tsv" "
    SELECT n.nspname, r.rolname FROM pg_namespace n JOIN pg_roles r ON r.oid = n.nspowner
    WHERE n.nspname NOT LIKE 'pg_toast%' AND n.nspname NOT LIKE 'pg_temp_%' ORDER BY n.nspname;"

  write_header "${prefix}_object_ownership.tsv" $'schema_name\tobject_name\tobject_type\towner_name\ttotal_bytes'
  run_tsv "$database" "${prefix}_object_ownership.tsv" "
    SELECT n.nspname, c.relname,
           CASE c.relkind WHEN 'r' THEN 'table' WHEN 'p' THEN 'partitioned_table' WHEN 'v' THEN 'view'
                          WHEN 'm' THEN 'materialized_view' WHEN 'S' THEN 'sequence' END,
           r.rolname, CASE WHEN c.relkind IN ('r', 'p', 'm') THEN pg_total_relation_size(c.oid)::text ELSE '' END
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace JOIN pg_roles r ON r.oid = c.relowner
    WHERE c.relkind IN ('r', 'p', 'v', 'm', 'S') AND n.nspname NOT IN ('pg_catalog', 'information_schema')
    UNION ALL
    SELECT n.nspname, p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')', 'function', r.rolname, ''
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace JOIN pg_roles r ON r.oid = p.proowner
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
    UNION ALL
    SELECT n.nspname, t.typname, 'type', r.rolname, ''
    FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace JOIN pg_roles r ON r.oid = t.typowner
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema') AND t.typtype IN ('b', 'c', 'd', 'e', 'r')
    ORDER BY 1, 2, 3;"

  write_header "${prefix}_candidate_owned_objects.tsv" $'schema_name\tobject_name\tobject_type\towner_name\ttotal_bytes'
  run_tsv "$database" "${prefix}_candidate_owned_objects.tsv" "
    SELECT * FROM (
      SELECT n.nspname, c.relname, CASE c.relkind WHEN 'r' THEN 'table' WHEN 'p' THEN 'partitioned_table' WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized_view' WHEN 'S' THEN 'sequence' END, r.rolname, CASE WHEN c.relkind IN ('r', 'p', 'm') THEN pg_total_relation_size(c.oid)::text ELSE '' END
      FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace JOIN pg_roles r ON r.oid = c.relowner
      WHERE c.relkind IN ('r', 'p', 'v', 'm', 'S') AND n.nspname NOT IN ('pg_catalog', 'information_schema')
      UNION ALL SELECT n.nspname, p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')', 'function', r.rolname, '' FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace JOIN pg_roles r ON r.oid = p.proowner WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      UNION ALL SELECT n.nspname, t.typname, 'type', r.rolname, '' FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace JOIN pg_roles r ON r.oid = t.typowner WHERE n.nspname NOT IN ('pg_catalog', 'information_schema') AND t.typtype IN ('b', 'c', 'd', 'e', 'r')
    ) owned WHERE owner_name IN (${candidate_roles_sql}) ORDER BY 1, 2, 3;"

  write_header "${prefix}_table_grants.tsv" $'grantee\tgrantor\ttable_schema\ttable_name\tprivilege_type\tis_grantable'
  run_tsv "$database" "${prefix}_table_grants.tsv" "SELECT grantee, grantor, table_schema, table_name, privilege_type, is_grantable FROM information_schema.role_table_grants ORDER BY table_schema, table_name, grantee, privilege_type;"
  write_header "${prefix}_sequence_grants.tsv" $'grantee\tgrantor\tobject_schema\tobject_name\tprivilege_type\tis_grantable'
  run_tsv "$database" "${prefix}_sequence_grants.tsv" "SELECT grantee, grantor, object_schema, object_name, privilege_type, is_grantable FROM information_schema.role_usage_grants WHERE object_type = 'SEQUENCE' ORDER BY object_schema, object_name, grantee, privilege_type;"
  write_header "${prefix}_schema_grants.tsv" $'schema_name\tgrantee\tprivilege_type\tis_grantable'
  run_tsv "$database" "${prefix}_schema_grants.tsv" "
    SELECT n.nspname, COALESCE(grantee.rolname, 'PUBLIC'), x.privilege_type, x.is_grantable
    FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x LEFT JOIN pg_roles grantee ON grantee.oid = x.grantee
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY n.nspname, grantee.rolname, x.privilege_type;"

  write_header "${prefix}_default_privileges.tsv" $'definer_role\ttarget_schema\tobject_type\tgrantee\tprivilege_type'
  run_tsv "$database" "${prefix}_default_privileges.tsv" "
    SELECT definer.rolname, COALESCE(n.nspname, ''), d.defaclobjtype, COALESCE(grantee.rolname, 'PUBLIC'), x.privilege_type
    FROM pg_default_acl d JOIN pg_roles definer ON definer.oid = d.defaclrole
         LEFT JOIN pg_namespace n ON n.oid = d.defaclnamespace
         CROSS JOIN LATERAL aclexplode(d.defaclacl) x LEFT JOIN pg_roles grantee ON grantee.oid = x.grantee
    ORDER BY definer.rolname, n.nspname, d.defaclobjtype, grantee.rolname, x.privilege_type;"

  write_header "${prefix}_candidate_grants.tsv" $'grant_scope\tgrantee\tgrantor\tobject_schema\tobject_name\tprivilege_type\tis_grantable'
  run_tsv "$database" "${prefix}_candidate_grants.tsv" "
    SELECT 'table', grantee, grantor, table_schema, table_name, privilege_type, is_grantable FROM information_schema.role_table_grants WHERE grantee IN (${candidate_roles_sql})
    UNION ALL SELECT 'sequence', grantee, grantor, object_schema, object_name, privilege_type, is_grantable FROM information_schema.role_usage_grants WHERE object_type = 'SEQUENCE' AND grantee IN (${candidate_roles_sql})
    UNION ALL SELECT 'schema', COALESCE(grantee.rolname, 'PUBLIC'), '', n.nspname, '', x.privilege_type, x.is_grantable FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x LEFT JOIN pg_roles grantee ON grantee.oid = x.grantee WHERE COALESCE(grantee.rolname, 'PUBLIC') IN (${candidate_roles_sql})
    ORDER BY 1, 4, 5, 2, 6;"

  write_header "${prefix}_foreign_server_user_mappings.tsv" $'server_name\tuser_name\toptions_redacted'
  run_tsv "$database" "${prefix}_foreign_server_user_mappings.tsv" "
    SELECT COALESCE(s.srvname, ''), COALESCE(r.rolname, ''),
           CASE WHEN m.umoptions IS NULL THEN '' ELSE array_to_string(ARRAY(SELECT split_part(option, '=', 1) || '=REDACTED' FROM unnest(m.umoptions) option), ',') END
    FROM pg_user_mapping m JOIN pg_foreign_server s ON s.oid = m.umserver LEFT JOIN pg_roles r ON r.oid = m.umuser ORDER BY s.srvname, r.rolname;"
  write_header "${prefix}_extensions.tsv" $'extension_name\tversion\tschema_name'
  run_tsv "$database" "${prefix}_extensions.tsv" "SELECT e.extname, e.extversion, n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace ORDER BY e.extname;"

  write_header "${prefix}_summary.tsv" $'role_name\trole_exists\tcan_login\tactive_sessions_count\towned_objects_count\texplicit_grants_count\tdefault_privileges_count\tmembership_count\trecommended_status'
  run_tsv "$database" "${prefix}_summary.tsv" "
    WITH candidates(role_name) AS (VALUES ('infodenguedev'), ('analista'), ('mosqlimate_dev'), ('dengueadmin')),
    owned AS (SELECT r.rolname role_name, count(*) count FROM pg_roles r JOIN (SELECT relowner owner_oid FROM pg_class WHERE relkind IN ('r','p','v','m','S') UNION ALL SELECT proowner FROM pg_proc UNION ALL SELECT typowner FROM pg_type) o ON o.owner_oid = r.oid GROUP BY r.rolname),
    grants AS (SELECT grantee role_name, count(*) count FROM (SELECT grantee FROM information_schema.role_table_grants UNION ALL SELECT grantee FROM information_schema.role_usage_grants WHERE object_type = 'SEQUENCE' UNION ALL SELECT COALESCE(r.rolname, 'PUBLIC') FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x LEFT JOIN pg_roles r ON r.oid = x.grantee) all_grants GROUP BY grantee),
    defaults AS (SELECT grantee.rolname role_name, count(*) count FROM pg_default_acl d CROSS JOIN LATERAL aclexplode(d.defaclacl) x JOIN pg_roles grantee ON grantee.oid = x.grantee GROUP BY grantee.rolname),
    memberships AS (SELECT member.rolname role_name, count(*) count FROM pg_auth_members m JOIN pg_roles member ON member.oid = m.member GROUP BY member.rolname),
    sessions AS (SELECT usename role_name, count(*) count FROM pg_stat_activity GROUP BY usename)
    SELECT c.role_name, (r.oid IS NOT NULL), COALESCE(r.rolcanlogin::text, ''), COALESCE(s.count, 0), COALESCE(o.count, 0), COALESCE(g.count, 0), COALESCE(d.count, 0), COALESCE(m.count, 0),
      CASE WHEN c.role_name = 'dengueadmin' AND COALESCE(s.count, 0) > 0 THEN 'ADMIN_USAGE_REVIEW'
           WHEN c.role_name = 'dengueadmin' THEN 'KEEP_DOCUMENT'
           WHEN c.role_name = 'infodenguedev' AND COALESCE(s.count, 0) > 0 THEN 'REVIEW'
           WHEN c.role_name = 'infodenguedev' AND lower('${environment_label}') = 'production' AND r.oid IS NOT NULL AND COALESCE(o.count, 0) = 0 AND COALESCE(g.count, 0) = 0 THEN 'CANDIDATE_REMOVE'
           WHEN c.role_name = 'infodenguedev' AND lower('${environment_label}') <> 'development' THEN 'REVIEW'
           WHEN c.role_name = 'analista' AND COALESCE(s.count, 0) = 0 AND COALESCE(o.count, 0) = 0 AND COALESCE(g.count, 0) = 0 THEN 'CANDIDATE_REMOVE'
           WHEN c.role_name = 'mosqlimate_dev' AND COALESCE(g.count, 0) > 0 THEN 'PRIVILEGES_REVIEW'
           WHEN c.role_name = 'mosqlimate_dev' AND COALESCE(s.count, 0) = 0 AND COALESCE(o.count, 0) = 0 THEN CASE WHEN lower('${environment_label}') = 'production' THEN 'CANDIDATE_REMOVE' ELSE 'REVIEW' END
           ELSE 'REVIEW' END
    FROM candidates c LEFT JOIN pg_roles r ON r.rolname = c.role_name LEFT JOIN owned o ON o.role_name = c.role_name LEFT JOIN grants g ON g.role_name = c.role_name LEFT JOIN defaults d ON d.role_name = c.role_name LEFT JOIN memberships m ON m.role_name = c.role_name LEFT JOIN sessions s ON s.role_name = c.role_name ORDER BY c.role_name;"
done

printf 'Audit complete: %s\n' "$output_dir"
