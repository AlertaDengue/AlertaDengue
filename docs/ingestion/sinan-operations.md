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

Check whether the ingestion watcher is running:

```bash
makim ingestion.watch-ps --env staging
```

The watcher should monitor:

```text
/Storage/staging_data/sinan/incoming/
```

For production recovery safety, the watcher should run with:

```text
--include-existing --requeue
```

## Manual ingestion

Run ingestion for a single file:

```bash
makim ingestion.run \
  --paths /Storage/staging_data/sinan/incoming/DENGUE_202617.csv \
  --include-existing \
  --requeue
```

Run ingestion for all files available in the incoming directory:

```bash
makim ingestion.run \
  --paths /Storage/infodengue_data/sinan/incoming \
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

makim ingestion.watch-ps --env prod

makim ingestion.run \
  --paths /Storage/infodengue_data/sinan/incoming \
  --include-existing \
  --requeue
```

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

Recovery and collision handling use the canonical imported root only. The workflow does not depend on a separate uploaded-base path.

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
