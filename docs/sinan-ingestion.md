# SINAN Ingestion

This document describes the SINAN ingestion workflow used by AlertaDengue.

## Overview

SINAN files are uploaded to MinIO and materialized into the local incoming directory. The ingestion watcher detects new files, runs the Makim ingestion task, moves each file to its canonical storage path, and enqueues the processing pipeline through Celery.

```text
MinIO bucket
  -> incoming directory
  -> ingestion watcher
  -> canonical imported path
  -> Celery stage
  -> Celery merge
  -> Postgres
```

## Locations

MinIO bucket:

```text
sinan-infodengue
```

Incoming directory:

```text
/Storage/infodengue_data/sinan/incoming/
```

Canonical imported storage:

```text
/mnt/storagebox-infodengue/sinan/imported/
```

## Canonical path format

Imported files are organized by country, file type, disease, year, and epidemiological week.

```text
/mnt/storagebox-infodengue/sinan/imported/{country}/{file_type}/{disease}/{year}/{year}{epiweek}/{filename}
```

Examples:

```text
/mnt/storagebox-infodengue/sinan/imported/br/csv/dengue/2026/202618/DenInfodengue_BR_202618.csv
/mnt/storagebox-infodengue/sinan/imported/br/csv/chik/2026/202618/ChikInfodengue_BR_202618.csv
```

Disease folders:

```text
dengue
chik
```

Disease codes:

```text
A90 = Dengue
A92 = Chikungunya
```

Canonical filenames:

```text
DenInfodengue_{UF}_{YYYYWW}.csv
ChikInfodengue_{UF}_{YYYYWW}.csv
```

The final `{YYYYWW}` is derived from the file content, not necessarily from the original uploaded filename.

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

Validate the Django environment before rerunning ingestion:

```bash
python AlertaDengue/manage.py check
```

## Materialization

The MinIO materializer mirrors objects from:

```text
sinan-infodengue
```

into:

```text
/Storage/infodengue_data/sinan/incoming/
```

Restart the MinIO materialization services when needed:

```bash
sugar --profile prod compose-ext restart \
  --services minio minio-init minio-materializer \
  -- -d
```

## Watcher

Check whether the ingestion watcher is running:

```bash
makim ingestion.watch-ps --env prod
```

The watcher should monitor:

```text
/Storage/infodengue_data/sinan/incoming/
```

For recovery-safe operation, it should run with:

```text
--include-existing --requeue
```

## Manual ingestion

Run ingestion for a single file:

```bash
makim ingestion.run \
  --paths /Storage/infodengue_data/sinan/incoming/DENGUE_202617.csv \
  --include-existing \
  --requeue
```

Run ingestion for all files currently available in the incoming directory:

```bash
makim ingestion.run \
  --paths /Storage/infodengue_data/sinan/incoming \
  --include-existing \
  --requeue
```

## Successful output

Makim should finish with:

```text
DONE: enqueued=1 failed=0
```

Celery should complete the stage and merge tasks:

```text
Task ingestion.sinan_stage_run[...] succeeded
Task ingestion.sinan_merge_run[...] succeeded: {'inserted': ..., 'updated': ..., 'deleted': ...}
```

## Recovery

Use this section when ingestion was interrupted or failed after the file was already detected.

### Standard recovery

1. Validate the environment:

```bash
cd /opt/services/AlertaDengue
conda activate alertadengue
python AlertaDengue/manage.py check
```

2. Check the watcher:

```bash
makim ingestion.watch-ps --env prod
```

3. Requeue ingestion:

```bash
makim ingestion.run \
  --paths /Storage/infodengue_data/sinan/incoming \
  --include-existing \
  --requeue
```

### Important flags

`--include-existing` allows Makim to rebuild the manifest using files that were already moved to the canonical imported path.

`--requeue` allows an existing ingestion run to be queued again.

These flags are useful when Phase 1 succeeded but enqueueing or Celery processing failed.

### Expected recovery message

During recovery, this message is expected:

```text
SKIP: ... (SKIP (already exists))
Found existing at /mnt/storagebox-infodengue/sinan/imported/..., adding to manifest.
```

This is not an error. It means the canonical file already exists and will be used for enqueueing.

### Empty incoming directory

If the incoming directory is empty, the file may already have been moved to canonical storage:

```text
/mnt/storagebox-infodengue/sinan/imported/
```

In that case, run the standard recovery command with `--include-existing`.

### Makim succeeded but Celery did not finish

If Makim reports:

```text
DONE: enqueued=1 failed=0
```

but Celery does not complete `sinan_stage_run` and `sinan_merge_run`, check the worker services through the project operational tasks and then requeue using the standard recovery command.
