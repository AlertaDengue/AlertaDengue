# Audit execution checklist

- Run the audit in development.
- Review development outputs.
- Run the audit in staging.
- Review staging outputs.
- Obtain explicit approval for production execution.
- Confirm the expected production database name and retain the evidence package and logs.
- Run the read-only audit in production.
- Compare roles across environments.
- Draft the access matrix and attach evidence paths.
- Only then prepare a separate, approved cleanup PR; do not run ad hoc production cleanup.

No cleanup SQL belongs in this audit directory.
