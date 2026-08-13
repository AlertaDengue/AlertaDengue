# PostgreSQL access policy

Issue reference: #1040.

## Current purpose and audit-first policy

This policy documents the audit-first review and completed production cleanup of obsolete PostgreSQL roles after separating development, staging, and production. Future role, ownership, or privilege changes still require explicit approval, an evidence package, confirmation of the expected database name, and retained logs.

The canonical scripts live in `containers/postgres/sql_history/postgres_access_policy/`. Development-only credentials must not exist in production. Applications should not use `dengueadmin` unless that use is explicitly justified, documented, and evidenced.

Role outcomes:

- `infodenguedev` and `analista`: production cleanup completed on 2026-08-13. Both roles are absent after production validation.
- `mosqlimate_dev`: keep and protect as the least-privilege Mosqlimate role. It is not a cleanup target.
- `dengueadmin`: keep and protect. It still requires a separate review of current admin/application usage; do not revoke or drop it in this workflow.

Production cleanup evidence was retained outside version control:

- Pre-removal evidence: `/opt/services/infodengue/database_audits/postgres_access_policy_production_pre_removal_20260813T100741Z.tar.gz` (SHA-256 `a1ea13f4e899035bcfa73494a3af491f25e387dbf4b6b3b4e971a77bfc6639c8`).
- Final evidence: `/opt/services/infodengue/database_audits/postgres_role_cleanup_production_final_20260813T100901Z.tar.gz` (SHA-256 `709db1a54a67f274e1398433a2b7f56a39010bf60a2257f2baae86862eaaa2eb`).
- Post-cleanup audit: `/opt/services/infodengue/database_audits/postgres_access_policy_production_20260813T101032Z`.

`managed = False` in Django models does not grant or revoke PostgreSQL privileges; PostgreSQL ACLs remain controlled by the database.

Both the access audit and guarded cleanup workflow use PostgreSQL catalog ACLs as the canonical grant model. Generated TSV counts are environment evidence; do not treat a prior `information_schema` count as an expected grant total. Catalog ACLs can include relation privileges on views and materialized views that `information_schema` does not expose the same way.

## Access matrix template

| environment | service/process | database | role | login_allowed | privilege_level | owner | status | evidence | decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | _TBD_ | dengue / infodengue | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _audit path_ | _TBD_ |

Audit evidence paths:

- Development: `_TBD_`
- Staging: `_TBD_`
- Production: `_TBD_`
- Repository-reference audit: `_TBD_`

## Requirements before a removal proposal

A later cleanup PR may remove a role only after evidence confirms all of the following:

- no active sessions;
- no object ownership;
- no explicit privileges;
- no default privileges;
- no role memberships;
- no references in deployment configuration;
- staging validation; and
- explicit production SQL reviewed and approved.

The audit tooling is intentionally read-only. It does not contain cleanup statements.
