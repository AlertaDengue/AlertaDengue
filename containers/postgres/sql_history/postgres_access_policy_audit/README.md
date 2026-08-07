# PostgreSQL access-policy audit

This directory provides the first, safe phase of issue #1040: a read-only audit of PostgreSQL roles and access. Run it separately in **development**, **staging**, and **production**, against the `dengue` and `infodengue` databases, before proposing any cleanup.

The candidate roles are `infodenguedev`, `analista`, `mosqlimate_dev`, and `dengueadmin`. The audit requires ordinary catalog visibility only; it does not require superuser operations, change PostgreSQL state, inspect environment files, or expose credentials. The database script sets `default_transaction_read_only=on` and a ten-minute statement timeout for every `psql` connection.

## Run

Use the normal, preconfigured PostgreSQL connection for each environment; do not put a password on the command line:

```bash
containers/postgres/sql_history/postgres_access_policy_audit/run_postgres_access_audit.sh development
containers/postgres/sql_history/postgres_access_policy_audit/run_repo_role_reference_audit.sh
```

Set `POSTGRES_ACCESS_AUDIT_ROOT` if `/opt/services/infodengue/database_audits` is not appropriate. Database results are written below `postgres_access_policy_<label>_<UTC_TIMESTAMP>/`; the repository-reference report is written to `database_audits/repo_role_references_<UTC_TIMESTAMP>.tsv`. Keep audit output out of version control.

`PASS` means the evidence supports the stated expectation, `WARN` means the evidence needs operational attention, and `REVIEW` means a person must assess the evidence before any decision. The generated role summaries use more specific decision labels such as `CANDIDATE_REMOVE`, `PRIVILEGES_REVIEW`, and `ADMIN_USAGE_REVIEW`; none of them authorizes a change by itself.

Review the outputs with the execution checklist and record the evidence in the access matrix. Cleanup, privilege changes, or role removal must be handled in a separate PR after development, staging, and production audit evidence has been reviewed.
