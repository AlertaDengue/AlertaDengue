# SINAN Ingestion Storage

This document describes the storage layout used by the SINAN ingestion workflow.

## Storage strategy

The ingestion pipeline separates transient storage from canonical storage.

| Location | Purpose | Long-term source of truth |
| --- | --- | --- |
| MinIO bucket | Temporary ingress | No |
| Incoming directory | Temporary watcher buffer | No |
| StorageBox imported path | Canonical imported files | Yes |
| PostgreSQL | Processed data and ingestion metadata | Yes |

## MinIO bucket

SINAN files are uploaded to:

```text
sinan-infodengue
```

MinIO is an ingress gateway. It should not be treated as the permanent source of truth for imported files.

## Incoming directory

The materializer copies MinIO objects into the incoming directory:

```text
/Storage/infodengue_data/sinan/incoming/
```

This directory is watched by the ingestion watcher.

Files in this directory are transient. After ingestion starts, files may be moved to canonical storage.

## Canonical imported storage

The canonical imported root is:

```text
/mnt/storagebox-infodengue/sinan/imported/
```

Once a file reaches this location, this path becomes the file-level source of truth for ingestion and recovery.

## Canonical path format

```text
{imported_root}/{country}/{file_type}/{disease}/{year}/{year}{epiweek}/{filename}
```

Example:

```text
/mnt/storagebox-infodengue/sinan/imported/br/csv/dengue/2026/202618/DenInfodengue_BR_202618.csv
```

Path components:

| Component | Example | Description |
| --- | --- | --- |
| `country` | `br` | Country scope |
| `file_type` | `csv` | Input file format |
| `disease` | `dengue` | Normalized disease folder |
| `year` | `2026` | Epidemiological year |
| `year + epiweek` | `202618` | Epidemiological year and week |
| `filename` | `DenInfodengue_BR_202618.csv` | Canonical filename |

## Filename format

```text
{prefix}_{UF}_{YYYYWW}.{ext}
```

Examples:

```text
DenInfodengue_BR_202618.csv
ChikInfodengue_BR_202618.csv
```

Prefixes:

| Disease | Prefix |
| --- | --- |
| Dengue | `DenInfodengue` |
| Chikungunya | `ChikInfodengue` |

## Versioning and duplicate handling

When a file is moved into canonical storage, the ingestion mover checks whether a file already exists for the same canonical destination.

Expected behavior:

| Condition | Behavior |
| --- | --- |
| Destination does not exist | Move file to canonical path |
| Destination exists with same identity | Skip as already available |
| Destination exists with different identity | Store using a versioned suffix |

The suffix format is implementation-defined, but follows the principle of preserving distinct file identities without overwriting existing canonical data.

## Environment variables

Relevant path variables are defined in `.envs/.env`.

Typical variables include:

```bash
DOCKER_HOST_SINAN_ROOT=/mnt/storagebox-infodengue/sinan
DOCKER_HOST_IMPORTED_FILES_DIR=${DOCKER_HOST_SINAN_ROOT}/imported
DOCKER_HOST_INCOMING_DIR=/Storage/infodengue_data/sinan/incoming
MINIO_BROWSER_REDIRECT_URL=http://localhost:9001
```

Use environment-specific values for staging and production.
