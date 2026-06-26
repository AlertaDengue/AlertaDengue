-- Remove the django-chunked-upload table after the upload app is removed.
--
-- Run only after the final Django migration has dropped the three
-- public.upload_* tables and after archive validation has been recorded.

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DO $guard$
BEGIN
    IF to_regclass('archive_upload.manifest') IS NULL THEN
        RAISE EXCEPTION 'archive_upload.manifest is required';
    END IF;

    IF (SELECT count(*) FROM archive_upload.manifest) <> 4 THEN
        RAISE EXCEPTION 'archive_upload.manifest is incomplete';
    END IF;

    IF to_regclass('public.upload_sinanchunkedupload') IS NOT NULL
       OR to_regclass('public.upload_sinanupload') IS NOT NULL
       OR to_regclass('public.upload_sinanuploadlogstatus') IS NOT NULL THEN
        RAISE EXCEPTION 'apply the final upload Django migration first';
    END IF;

    IF to_regclass('public.chunked_upload_chunkedupload') IS NULL THEN
        RAISE EXCEPTION 'public.chunked_upload_chunkedupload is missing';
    END IF;
END
$guard$;

-- Deliberately omit CASCADE. Unknown dependencies must stop this release.
DROP TABLE public.chunked_upload_chunkedupload;

COMMIT;
