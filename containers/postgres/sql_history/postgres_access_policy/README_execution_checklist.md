# PostgreSQL access-policy execution checklist

1. Run the database access audit in development.
2. Run the repository role-reference audit.
3. Run the database access audit in staging.
4. Review and retain the evidence.
5. Run the role-cleanup preflight in staging.
6. Review all blockers and deployment references.
7. Run staging cleanup only after explicit approval.
8. Validate staging.
9. Prepare a production plan separately, with retained logs and an evidence review.
10. Execute production only after explicit approval and with `--confirm-production`.

`mosqlimate_dev` and `dengueadmin` are protected and are never cleanup targets.
