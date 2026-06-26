-- Archive data owned by the retired Django ``upload`` application.
--
-- Run once as the database owner before applying the final upload migration.
-- The archive is data-only. Retain a full pg_dump for schema-level recovery.

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '15min';

DO $guard$
BEGIN
    IF to_regnamespace('archive_upload') IS NOT NULL THEN
        RAISE EXCEPTION 'archive_upload already exists; archive is one-time';
    END IF;

    IF to_regclass('public.upload_sinanchunkedupload') IS NULL
       OR to_regclass('public.upload_sinanupload') IS NULL
       OR to_regclass('public.upload_sinanuploadlogstatus') IS NULL
       OR to_regclass('public.chunked_upload_chunkedupload') IS NULL THEN
        RAISE EXCEPTION 'expected upload tables are missing from public schema';
    END IF;
END
$guard$;

CREATE SCHEMA archive_upload;
REVOKE ALL ON SCHEMA archive_upload FROM PUBLIC;

-- ``AS TABLE`` intentionally excludes defaults and foreign keys. The archive
-- must not depend on source sequences or tables that will be removed.
CREATE TABLE archive_upload.sinan_chunked_upload AS
TABLE public.upload_sinanchunkedupload;

CREATE TABLE archive_upload.sinan_upload AS
TABLE public.upload_sinanupload;

CREATE TABLE archive_upload.sinan_upload_log_status AS
TABLE public.upload_sinanuploadlogstatus;

-- This is the table supplied by django-chunked-upload. Archive all rows
-- because its ownership cannot be inferred after the dependency is removed.
CREATE TABLE archive_upload.chunked_upload AS
TABLE public.chunked_upload_chunkedupload;

CREATE TABLE archive_upload.manifest (
    archived_at timestamptz NOT NULL DEFAULT now(),
    source_table text PRIMARY KEY,
    archive_table text NOT NULL,
    row_count bigint NOT NULL
);

INSERT INTO archive_upload.manifest (source_table, archive_table, row_count)
SELECT 'public.upload_sinanchunkedupload',
       'archive_upload.sinan_chunked_upload',
       count(*)
FROM archive_upload.sinan_chunked_upload
UNION ALL
SELECT 'public.upload_sinanupload',
       'archive_upload.sinan_upload',
       count(*)
FROM archive_upload.sinan_upload
UNION ALL
SELECT 'public.upload_sinanuploadlogstatus',
       'archive_upload.sinan_upload_log_status',
       count(*)
FROM archive_upload.sinan_upload_log_status
UNION ALL
SELECT 'public.chunked_upload_chunkedupload',
       'archive_upload.chunked_upload',
       count(*)
FROM archive_upload.chunked_upload;

COMMIT;
