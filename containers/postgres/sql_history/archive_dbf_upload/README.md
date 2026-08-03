# Legacy DBF upload archive

The legacy DBF upload workflow covers the historical period through
epidemiological week `202552`. The new `ingestion` workflow is active from
week `202553`; its DBF file parsing writes `ingestion.run` and
`ingestion.sinan_stage`, not the retired upload tables. No active runtime DBF
model, URL, view, form, serializer, task, command, Admin registration, or raw
SQL reference was found.

The exact archive scope is:

- `public.dbf_dbf`;
- `public.dbf_dbfchunkedupload`;
- `public.dbf_dbf_id_seq`;
- `public.dbf_dbfchunkedupload_id_seq`.

The archive schema is `archive_dbf_upload`. Out of scope are
`public.chunked_upload_chunkedupload`, all `public.upload_sinan*` objects,
and every `ingestion.*` object. The reviewed outbound foreign keys from both
DBF tables to `public.auth_user(id)` must remain intact. Any inbound
dependency or unexpected outbound dependency blocks the operation.

The schema definitions in `schemas_infodengue.sql` and ACLs in
`schemas_dengue.sql` are generated snapshots used by optional schema-fixture
setup, not canonical migrations. They remain unchanged in this branch.

## Execution order

1. Run `20260803_00_preflight_dbf_upload.sql` read-only with
   `psql -X -v ON_ERROR_STOP=1` and obtain operator confirmation of the
   functional `202552` cutoff.
2. Run `20260803_01_archive_dbf_upload.sql` as one guarded transaction.
   It moves exactly the two tables and validates the four archive objects,
   row counts, sequence values and ownership, foreign keys, and protected
   active objects before commit.
3. Reuse the existing repository export and disposable restore-validation
   workflow established by PR #1038, targeting only `archive_dbf_upload`.
   The dump must be custom-format and its verification receipt must have
   status `PASS` before removal.
4. Only after that evidence exists, run
   `20260803_90_remove_dbf_upload.sql` with explicit `psql` variables for the
   verified package path, expected database OID, dump SHA-256, verification
   status, row counts, and sequence values.

The archive and permanent removal operations remain separate. Removal relies
on verified `OWNED BY` dependencies so PostgreSQL removes the owned sequences
with their tables, then drops `archive_dbf_upload` only when empty. `CASCADE`
is prohibited. No script has been executed against production, staging, or a
shared database.
