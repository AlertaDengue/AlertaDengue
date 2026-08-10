# Guarded PostgreSQL role cleanup

This is the generic, guarded cleanup workflow for issue #1040. The initial intended staging roles are `analista` and `infodenguedev`; roles are always supplied with `--roles`, never hard-coded in the cleanup logic.

`mosqlimate_dev` is intentionally protected as the least-privilege Mosqlimate development role and must never be passed for removal. `dengueadmin` is also protected. The script also rejects `postgres` and the role identified by the active PostgreSQL connection.

## Run order

1. Run `preflight` and review its evidence.
2. Run `remove` in staging only, with the exact approval token.
3. Run `validate` in staging.
4. Only later, after separate approval, prepare any production execution. Adding this script does not authorize production cleanup.

```bash
containers/postgres/sql_history/postgres_role_cleanup/run_postgres_role_cleanup.sh preflight \
  --label staging --roles analista,infodenguedev --databases dengue,infodengue

containers/postgres/sql_history/postgres_role_cleanup/run_postgres_role_cleanup.sh remove \
  --label staging --roles analista,infodenguedev --databases dengue,infodengue \
  --approval REMOVE_APPROVED_POSTGRES_ROLE_CLEANUP

containers/postgres/sql_history/postgres_role_cleanup/run_postgres_role_cleanup.sh validate \
  --label staging --roles analista,infodenguedev --databases dengue,infodengue
```

The default databases are `dengue,infodengue`. Preflight and validate are read-only. Every action writes TSV evidence below `/opt/services/infodengue/database_audits/postgres_role_cleanup_<label>_<UTC_TIMESTAMP>/`; use `POSTGRES_ROLE_CLEANUP_ROOT` only when that location is unsuitable. Do not put passwords on the command line or commit generated evidence.

The workflow refuses removal unless selected roles have no sessions, role memberships, database ownership, object ownership, or default privileges. It revokes only explicit grants before attempting role removal. It never uses `DROP OWNED`, `REASSIGN OWNED`, `CASCADE`, or `TRUNCATE`.
