# PostgreSQL access-policy audit

This directory provides the first, safe phase of issue #1040: a read-only audit of PostgreSQL roles and access. Validate it separately in **development** and **staging**, against the `dengue` and `infodengue` databases, before any production execution.

The candidate roles are `infodenguedev`, `analista`, `mosqlimate_dev`, and `dengueadmin`. The audit requires ordinary catalog visibility only; it does not require superuser operations, change PostgreSQL state, inspect environment files, or expose credentials. The database script sets `default_transaction_read_only=on` and a ten-minute statement timeout for every `psql` connection.

## Run

Use the normal, preconfigured PostgreSQL connection for each environment; do not put a password on the command line:

```bash
containers/postgres/sql_history/postgres_access_policy_audit/run_postgres_access_audit.sh development
containers/postgres/sql_history/postgres_access_policy_audit/run_repo_role_reference_audit.sh development
```

Set `POSTGRES_ACCESS_AUDIT_ROOT` if `/opt/services/infodengue/database_audits` is not appropriate. Both reports are written below `/opt/services/infodengue/database_audits/postgres_access_policy_<label>_<UTC_TIMESTAMP>/` by default. Keep audit output out of version control.

`PASS` means the evidence supports the stated expectation, `WARN` means the evidence needs operational attention, and `REVIEW` means a person must assess the evidence before any decision. The generated role summaries use more specific decision labels such as `CANDIDATE_REMOVE`, `PRIVILEGES_REVIEW`, and `ADMIN_USAGE_REVIEW`; none of them authorizes a change by itself.

Review the outputs with the execution checklist and record the evidence in the access matrix. Production execution requires explicit approval, an evidence package, confirmation of the expected database name, and retained logs. Do not run ad hoc production cleanup. Cleanup, privilege changes, or role removal must be handled in a separate, approved PR after the evidence has been reviewed.
