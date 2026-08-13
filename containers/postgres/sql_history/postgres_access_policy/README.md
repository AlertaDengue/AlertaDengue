# PostgreSQL access policy workflow

This is the only canonical database-history directory for issue #1040. It contains the read-only database and repository audits plus the guarded, parameterized role-cleanup workflow.

| Role | Decision | Notes |
| --- | --- | --- |
| `mosqlimate_dev` | KEEP / protected | Least-privilege development access for Mosqlimate/Ana Juamaro. It is never revoked or dropped here. |
| `dengueadmin` | KEEP / protected | Current admin/application use needs review; it is never revoked or dropped here. |
| `analista` | REMOVED from production | Production cleanup completed and validation confirmed the role is absent. |
| `infodenguedev` | REMOVED from production | Production cleanup completed and validation confirmed the role is absent. |

The protected-role denylist is `postgres`, `dengueadmin`, `mosqlimate_dev`, and the current PostgreSQL connection role. `managed = False` in Django models only controls Django schema management; it neither grants nor revokes PostgreSQL ACLs.

The audit and cleanup workflows both use PostgreSQL catalog ACLs, not mixed `information_schema` queries. Catalog ACLs may report more grants than `information_schema`, including relation ACLs on views and materialized views that are not exposed the same way. Treat generated TSV counts as environment evidence rather than hardcoded expectations.

## Production cleanup record

Production cleanup for `analista` and `infodenguedev` was completed and validated on 2026-08-13. Preflight found no active sessions, memberships, ownership, database ownership, or blocking default privileges; selected-role explicit grants and revocable default privileges were removed; and `DROP ROLE` completed. Post-cleanup validation and audit confirmed both roles are absent, while production services remained healthy and no active sessions remained for either role.

Retained evidence outside version control:

- Pre-removal: `/opt/services/infodengue/database_audits/postgres_access_policy_production_pre_removal_20260813T100741Z.tar.gz` (SHA-256 `a1ea13f4e899035bcfa73494a3af491f25e387dbf4b6b3b4e971a77bfc6639c8`).
- Final: `/opt/services/infodengue/database_audits/postgres_role_cleanup_production_final_20260813T100901Z.tar.gz` (SHA-256 `709db1a54a67f274e1398433a2b7f56a39010bf60a2257f2baae86862eaaa2eb`).
- Post-cleanup audit: `/opt/services/infodengue/database_audits/postgres_access_policy_production_20260813T101032Z`.

`mosqlimate_dev` remains the protected least-privilege Mosqlimate role. `dengueadmin` remains protected and requires a separate admin-usage review.

## Staging-first usage

```bash
SQL_DIR=containers/postgres/sql_history/postgres_access_policy

"$SQL_DIR/run_postgres_access_audit.sh" staging
"$SQL_DIR/run_repo_role_reference_audit.sh" staging

"$SQL_DIR/run_postgres_role_cleanup.sh" preflight \
  --label staging --roles analista,infodenguedev --databases dengue,infodengue

# Only after evidence review and approval, in staging.
"$SQL_DIR/run_postgres_role_cleanup.sh" remove \
  --label staging --roles analista,infodenguedev --databases dengue,infodengue \
  --approval REMOVE_APPROVED_POSTGRES_ROLE_CLEANUP

"$SQL_DIR/run_postgres_role_cleanup.sh" validate \
  --label staging --roles analista,infodenguedev --databases dengue,infodengue
```

Production cleanup is not authorized by this workflow. It requires explicit approval, retained evidence, and `--confirm-production`:

```bash
"$SQL_DIR/run_postgres_role_cleanup.sh" remove \
  --label production --roles analista,infodenguedev --databases dengue,infodengue \
  --approval REMOVE_APPROVED_POSTGRES_ROLE_CLEANUP --confirm-production
```

Do not perform ad hoc production cleanup or put credentials on the command line. The scripts write evidence under `/opt/services/infodengue/database_audits`; generated evidence must stay out of version control.

## Execution checklist

1. Run the database access audit in development.
2. Run the repository role-reference audit in development.
3. Review and retain development evidence.
4. Run the database access audit in staging.
5. Run the repository role-reference audit in staging.
6. Review and retain staging evidence.
7. Run the role-cleanup preflight in staging.
8. Review all blockers and deployment references.
9. Run staging cleanup only after explicit approval.
10. Validate staging.
11. Prepare a production plan separately, with retained logs and an evidence review.
12. Execute production only after explicit approval and with `--confirm-production`.

`mosqlimate_dev` and `dengueadmin` are protected and are never cleanup targets.

## Default privileges

Default privileges granted to a selected role are revocable cleanup targets. During a guarded removal, the workflow revokes those grants before revoking explicit grants and dropping the selected role, so obsolete access is not recreated for future objects.

Default privileges defined by a selected role are blockers. The workflow does not remove that role automatically, because its default-privilege policy must be reviewed and transferred or removed separately. `dengueadmin` and `mosqlimate_dev` remain protected even when one appears in default-privilege evidence.
