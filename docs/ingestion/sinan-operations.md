# SINAN Ingestion Operations

This document describes operational commands for running, monitoring, and recovering the SINAN ingestion workflow.

## Environment

From the repository root:

```bash
cd /opt/services/AlertaDengue
mamba activate alertadengue
```

Create or update the environment when needed:

```bash
mamba env create -f conda/base.yaml
```

Validate Django before running ingestion commands:

```bash
python AlertaDengue/manage.py check
```

## Materialization services

The MinIO materializer mirrors files from the `sinan-infodengue` bucket into the incoming directory.

Restart the materialization services with Sugar:

```bash
sugar --profile staging compose-ext restart \
  --services minio minio-init minio-materializer \
  -- -d
```

## Watcher

Start the ingestion watcher:

```bash
makim ingestion.watch-start --env staging --include-existing --requeue
```

Check whether the ingestion watcher is running:

```bash
makim ingestion.watch-ps --env staging
```

The watcher should monitor:

```text
/opt/data/staging/sinan/incoming/
```

The watcher log is written to:

```text
/opt/data/staging/logs/ingestion_watch.log
```

## Manual ingestion

Run ingestion for a single file:

```bash
makim ingestion.run \
  --paths /opt/data/staging/sinan/incoming/DENGUE_202617.csv \
  --include-existing \
  --requeue
```

Run ingestion for all files available in the incoming directory:

```bash
makim ingestion.run \
  --paths /opt/data/staging/sinan/incoming \
  --include-existing \
  --requeue
```

## Recovery

Use recovery when ingestion was interrupted after a file was detected, moved, or partially enqueued.

The standard recovery sequence is:

```bash
cd /opt/services/AlertaDengue
mamba activate alertadengue

python AlertaDengue/manage.py check

makim ingestion.watch-start --env staging --include-existing --requeue
makim ingestion.watch-ps --env staging

makim ingestion.run \
  --paths /opt/data/staging/sinan/incoming \
  --include-existing \
  --requeue
```

## Targeted run rollback

A completed SINAN run can be rolled back from its Django admin detail page.
The workflow first presents a preview against the immediately previous
completed run with the same UF and disease. It requires an explicit
confirmation before making changes.

Only the latest completed run for a UF and disease can be rolled back. A
newer failed or staged run does not prevent it. Rollback also requires all
four natural-key values to be non-null in both stage histories. The production
`casos_unicos` constraint is a standard PostgreSQL `UNIQUE` constraint, whose
NULL values are distinct; rejecting nullable keys avoids treating separately
merged records as a single rollback target.

Rollback compares retained `ingestion.sinan_stage` rows using the SINAN
natural key: `nu_notific`, `dt_notific`, `cid10_codigo`, and
`municipio_geocodigo`. It deletes final-table rows that exist only in the
current run and restores changed rows from the selected previous run. Rows
that are old-only or unchanged are not touched. It does not replace an entire
disease dataset.

Every attempt is recorded in `ingestion.run_rollback`, including the preview
counts, rows deleted/restored, status, metadata, and any error. A successfully
rolled-back run cannot be rolled back again.

Rollback never deletes canonical files, `Run` records, or `SinanStage`
history, and it never queues ingestion. It depends on stage history for both
runs; an operation cannot be previewed or executed when that history has been
removed.

After a successful rollback, inspect the `RunRollback` audit record and the
affected `Municipio.Notificacao` rows. If the final table no longer matches
the current run's retained stage values, rollback aborts instead of replacing
data that may have been changed by a later operation.

## Recovery flags

`--include-existing` allows the ingestion command to reuse files that were already moved to canonical storage.

`--requeue` allows an existing ingestion run to be queued again.

These flags are useful when Phase 1 succeeded but enqueueing or Celery processing failed.

## Expected recovery message

During recovery, this message is expected:

```text
SKIP: ... (SKIP (already exists))
Found existing at /mnt/storagebox-infodengue/sinan/imported/..., adding to manifest.
```

This is not an error. It means the canonical file already exists and will be used to rebuild the manifest and enqueue processing.

Recovery and collision handling use the canonical imported root only. The workflow does not depend on a separate `uploaded_base` path.

## Empty incoming directory

If the incoming directory is empty, the file may already have been moved to canonical storage.

Check the canonical imported root:

```text
/mnt/storagebox-infodengue/sinan/imported/
```

If the canonical file exists, rerun the standard recovery command with `--include-existing`.

## Makim succeeded but Celery did not finish

If Makim reports:

```text
DONE: enqueued=1 failed=0
```

but Celery does not complete:

```text
ingestion.sinan_stage_run
ingestion.sinan_merge_run
```

check the worker services using the project operational tasks, then rerun the standard recovery command.

## Success criteria

A recovered ingestion is complete when:

```text
DONE: enqueued=1 failed=0
Task ingestion.sinan_stage_run[...] succeeded
Task ingestion.sinan_merge_run[...] succeeded
```
