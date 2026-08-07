# PostgreSQL access policy

Issue reference: #1040.

## Current purpose and audit-first policy

This policy documents an audit-first review of PostgreSQL roles after separating development, staging, and production. It does not authorize a role, ownership, or privilege change. Development and staging validation are required before production execution. Production execution requires explicit approval, an evidence package, confirmation of the expected database name, and retained logs. Assess service usage and deployment references, and make any cleanup proposal in a separate, approved PR with explicit production SQL; do not run ad hoc production cleanup.

Development-only credentials must not exist in production. Applications should not use `dengueadmin` unless that use is explicitly justified, documented, and evidenced.

Candidate roles and expected outcomes:

- `infodenguedev`: document its development use; outside development, review it and consider removal only after evidence shows no use.
- `analista`: consider removal only when it has no sessions, ownership, grants, defaults, memberships, or deployment references.
- `mosqlimate_dev`: review privileges when present; only consider removal after the same evidence checks.
- `dengueadmin`: retain and document unless its application usage has been explicitly assessed; never recommend removal from this audit alone.

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
