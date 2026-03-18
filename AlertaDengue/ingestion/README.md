# SINAN Ingestion System

This application manages the multi-stage ingestion of SINAN (Sistema de Informação de Agravos de Notificação) data files into the AlertaDengue database. It is designed for high reliability, data integrity, and auditable processing.

## Architecture Overview

The ingestion process follows a structured path through several storage layers, prioritizing data correctness and recoverability.

| Layer | Type | Role |
| :--- | :--- | :--- |
| **MinIO** | Object Store | Ingress Gateway (Transient ingress) |
| **Incoming** | Local SSD | Watcher Buffer (Transient trigger) |
| **StorageBox** | Remote NAS | Canonical Repository (Permanent Hub) |
| **PostgreSQL**| Database | Final Data and Operations Metadata |

### Data Lifecycle Diagram

```mermaid
sequenceDiagram
    participant User
    participant MinIO as MinIO (S3 Bucket)
    participant Materializer as MinIO Materializer (Container)
    participant Host as Host FS (/incoming)
    participant Watcher as Ingestion Watcher (Worker)
    participant Mover as Mover Command (Phase 1)
    participant StoragePath as StorageBox (Canonical)
    participant Celery as Celery (Staging & Merge)
    participant DB as Postgres

    Note over User, MinIO: 1. Input Data
    User->>MinIO: Uploads file.dbf to bucket 'sinan-infodengue'

    Note over Materializer, Host: 2. Materialization
    Materializer->>MinIO: mc mirror --watch
    Materializer->>Host: Mirrors object to /incoming

    Note over Watcher, Host: 3. Detection
    Watcher->>Host: Polling detect 'file.dbf' settles
    Watcher->>Mover: triggers makim ingestion.run

    Note over Mover, StoragePath: 4. Analysis & Rename (Phase 1)
    Mover->>Host: Extracts Disease, UF, Epiweek
    Mover->>Mover: Renames to Prefix_UF_YYYYWW.dbf
    Mover->>StoragePath: Moves file to StorageBox (Canonical)

    Note over Mover, Celery: 5. Enqueueing (Phase 2)
    Mover->>Celery: manage.py ingestion_enqueue_manifest
    Celery->>DB: Creates 'Run' record (status: QUEUED)

    Note over Celery, DB: 6. Processing (Phase 3)
    Celery->>StoragePath: Reads from Canonical Storage
    Celery->>DB: SQL UPSERT into Notificacao
    Celery->>DB: Updates 'Run' record (SUCCESS)
```

## Detailed Process

### 1. The Gateway (MinIO)
Data enters via MinIO. The `minio-materializer` container mirrors objects to a local `/incoming` folder. This bridge allows the filesystem watcher to work reliably on Docker-mounted volumes.

### 2. The Filter (Watcher & Moving)
The `ingestion_watcher.py` triggers the `mover_sinan_data.py` script. This is where file names become "official":
- **Canonical Naming**: Files are renamed based on **content** (Disease, UF, and Max Epiweek).
- **Collision & Versioning**: If a file for the same week already exists:
    - Same SHA256 Identity -> **Skip** (already processed).
    - Different Identity -> **Version** (e.g., `_01.dbf`, `_02.dbf`).
- **Canonical Destination**: Files are moved permanently to the **StorageBox** (mount point defined by `DOCKER_HOST_SINAN_ROOT`).

**Path Example**: `/mnt/storagebox-staging/sinan/raw_data/imported/es/dbf/dengue/2026/202611/DenInfodengue_ES_202611.dbf`

#### Binary Data Naming & Collision Logic

When a file is moved from `/incoming` to the StorageBox, the system applies a content-driven naming rule.

```mermaid
flowchart TD
    Start([1. Start Move]) --> Extract[2. Extract UF, Disease, Epiweek]
    Extract --> BuildBase[3. Build Canonical Name: Prefix_UF_YYYYWW.ext]
    BuildBase --> CheckRoots{4. Exists in Any Base?}
    
    CheckRoots -- No --> Move((Move File))
    CheckRoots -- Yes --> HashCheck{5. SHA256 Match?}
    HashCheck -- Yes --> Skip[6. SKIP: Already Processed]
    HashCheck -- No --> Suffix[7. Apply Numeric Suffix: _01, _02...]
    Suffix --> CheckRoots
```

### 3. The Processor (Celery & Database)
The system creates a **Run** record for auditing and dispatches a Celery task.
- **Staging**: Data is bulk-inserted into a temporary `sinan_stage` table.
- **Merge**: Records are merged into `"Municipio"."Notificacao"` using an **UPSERT** logic to protect database consistency.

## Metadata & Auditing
Every ingestion is tracked in the **Django Admin** under the `Run` model:
- **Fingerprint**: SHA256 checksum prevents redundant work.
- **Metadata Blob**: Stores detected date formats, column mappings, and epidemiological week ranges.
- **Record Stats**: Counts of rows read, parsed, inserted, and updated are visible in real-time.

---
For technical setup, environment variables, and deployment via `sugar` or `makim`, see [CONTRIBUTING.md](./CONTRIBUTING.md).
