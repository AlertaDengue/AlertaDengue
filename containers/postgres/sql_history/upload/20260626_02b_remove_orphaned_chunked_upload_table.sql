-- Remove an archived django-chunked-upload table without upload app tables.

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DO $guard$
BEGIN
    IF to_regclass('archive_upload.manifest') IS NULL THEN
        RAISE EXCEPTION 'archive_upload.manifest is required';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM archive_upload.manifest
        WHERE source_table = 'public.chunked_upload_chunkedupload'
    ) THEN
        RAISE EXCEPTION 'chunked upload archive validation is missing';
    END IF;

    IF to_regclass('public.chunked_upload_chunkedupload') IS NULL THEN
        RAISE EXCEPTION 'public.chunked_upload_chunkedupload is missing';
    END IF;
END
$guard$;

-- Deliberately omit CASCADE. Unknown dependencies must stop this release.
DROP TABLE public.chunked_upload_chunkedupload;

COMMIT;
