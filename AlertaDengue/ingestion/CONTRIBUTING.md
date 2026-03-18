# Contributing to Ingestion

Technical details and operational procedures for maintaining the SINAN ingestion pipeline.

## Environment Configuration

All environment variables should be defined in `.envs/.env`. Key variables for the ingestion pipeline:

```bash
# StorageBox Root (Host-side mount point)
DOCKER_HOST_SINAN_ROOT=/mnt/storagebox-staging/sinan

# Derived paths for the containerized services
DOCKER_HOST_IMPORTED_FILES_DIR=${DOCKER_HOST_SINAN_ROOT}/raw_data/imported
DOCKER_HOST_UPLOADED_FILES_DIR=${DOCKER_HOST_SINAN_ROOT}/raw_data/uploaded

# Local transient ingress directory
DOCKER_HOST_INCOMING_DIR=/Storage/staging_data/sinan/incoming
```

## System Dependencies

The ingestion system depends on several key Python libraries and external tools:
- **`watchdog`**: For the `PollingObserver` file-system watcher (essential for Docker compatibility).
- **`loguru`**: For structured, high-visibility logging.
- **`pandas` & `dbfread`**: For parsing CSV and DBF files.
- **`minio/mc`**: Used in the `minio-materializer` container for S3 mirroring.
- **`shlex`**: For secure shell command quoting (guards against filenames with special characters).

## Database & Migrations

The ingestion app uses dedicated models (`Run`, `SourceFormat`, etc.) to track processing history.

### Creating Migrations
If you modify `ingestion/models.py`, generate new migrations using:
```bash
python manage.py makemigrations ingestion
```

### Applying Migrations
Apply migrations to your target environment (ensure your `.env` is correctly configured):
```bash
python manage.py migrate
```

## Setup & Infrastructure

### 1. StorageBox Mount (/etc/fstab)
The operational source of truth is the Hetzner StorageBox mounted at the path defined by `DOCKER_HOST_SINAN_ROOT` (e.g., `/mnt/storagebox-staging/`).

#### Recommended: CIFS/SMB (System-level)
To mount the StorageBox sub-account `u364312-sub1` securely:

1. **Install dependencies**: `sudo apt-get install cifs-utils`
2. **Create credentials file**: Create `/etc/storagebox.creds` with:
   ```text
   username=uXXXXX-sub1
   password=YOUR_PASSWORD_HERE
   domain=YOUR_DOMAIN_IF_ANY
   ```
   *Set permissions: `sudo chmod 600 /etc/storagebox.creds`*
3. **Mount Point**: `sudo mkdir -p /mnt/storagebox-staging`
4. **fstab Entry**:
   ```text
   # /etc/fstab
   //uxxxxx-sub1.your-storagebox.de/uxxxxx-sub1 /mnt/storagebox-staging cifs iocharset=utf8,rw,credentials=/etc/storagebox.creds,file_mode=0660,dir_mode=0770,uid=1000,gid=1000,_netdev 0 0
   ```
5. **Reload**: `sudo mount -a`

#### Alternative: SSHFS
```text
# /etc/fstab
u364312-sub1@u364312-sub1.your-storagebox.de:/ /Storage2 fuse.sshfs _netdev,allow_other,IdentityFile=/root/.ssh/id_rsa,port=23 0 0
```

### 2. MinIO Deployment (Sugar)
Deploy the MinIO server and materializer (materializer) using **Sugar**:
```bash
sugar --profile staging compose-ext start --services minio -- -d
```

## Makim Operational Tasks

The ingestion watcher should be kept running for automated processing.

### Start/Restart Watcher
```bash
makim watch-start --env staging --replace
```

### Monitoring Process Status
```bash
makim watch-ps
```

### Stop Watcher
```bash
makim watch-stop --env staging
```

---
For a high-level overview of the data flow and Django Admin features, see [README.md](./README.md).
