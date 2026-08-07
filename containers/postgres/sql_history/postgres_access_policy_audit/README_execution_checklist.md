# Audit execution checklist

- Run the audit in development.
- Review development outputs.
- Run the audit in staging.
- Review staging outputs.
- Run the audit in production.
- Compare roles across environments.
- Draft the access matrix and attach evidence paths.
- Only then prepare a separate cleanup PR.

No cleanup SQL belongs in this audit directory.
