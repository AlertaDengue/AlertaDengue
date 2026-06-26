-- Archive django-chunked-upload data in a database without upload app tables.

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '15min';

DO $guard$
BEGIN
    IF to_regnamespace('archive_upload') IS NOT NULL THEN
        RAISE EXCEPTION 'archive_upload already exists; archive is one-time';
    END IF;

    IF to_regclass('public.chunked_upload_chunkedupload') IS NULL THEN
        RAISE EXCEPTION 'public.chunked_upload_chunkedupload is missing';
    END IF;
END
$guard$;

CREATE SCHEMA archive_upload;
REVOKE ALL ON SCHEMA archive_upload FROM PUBLIC;

CREATE TABLE archive_upload.chunked_upload AS
TABLE public.chunked_upload_chunkedupload;

CREATE TABLE archive_upload.manifest (
    archived_at timestamptz NOT NULL DEFAULT now(),
    source_table text PRIMARY KEY,
    archive_table text NOT NULL,
    row_count bigint NOT NULL
);

INSERT INTO archive_upload.manifest (source_table, archive_table, row_count)
SELECT 'public.chunked_upload_chunkedupload',
       'archive_upload.chunked_upload',
       count(*)
FROM archive_upload.chunked_upload;

COMMIT;
