-- Remove only the verified DBF and SINAN upload archive schemas.
-- The workflow sets the session evidence immediately before this script runs.

DO $$
BEGIN
    IF current_setting('archive.removal_authorized', true) IS DISTINCT FROM '1'
       OR current_setting('archive.package_path', true) IS NULL
       OR current_setting('archive.dump_sha256', true) IS NULL
       OR current_setting('archive.verification_receipt_sha256', true) IS NULL
       OR current_setting('archive.source_database_oid', true) IS NULL
       OR current_setting('archive.source_inventory_sha256', true) IS NULL
       OR current_setting('archive.source_row_counts_sha256', true) IS NULL
       OR current_setting('archive.selected_schemas', true) IS DISTINCT FROM
          'archive_dbf_upload,archive_sinan_upload' THEN
        RAISE EXCEPTION 'Direct execution is not supported. Use archive_schemas_workflow.sh remove with a verified persistent package.';
    END IF;
END
$$;

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60min';

DO $$
DECLARE
    protected_before record;
    protected_after record;
BEGIN
    IF current_setting('archive.removal_authorized', true) IS DISTINCT FROM '1'
       OR current_setting('archive.package_path', true) IS NULL
       OR current_setting('archive.dump_sha256', true) IS NULL
       OR current_setting('archive.verification_receipt_sha256', true) IS NULL
       OR current_setting('archive.source_database_oid', true) IS NULL
       OR current_setting('archive.source_inventory_sha256', true) IS NULL
       OR current_setting('archive.source_row_counts_sha256', true) IS NULL
       OR current_setting('archive.selected_schemas', true) IS DISTINCT FROM
          'archive_dbf_upload,archive_sinan_upload' THEN
        RAISE EXCEPTION 'Direct execution is not supported. Use archive_schemas_workflow.sh remove with a verified persistent package.';
    END IF;

    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION 'refuse archive schema removal while PostgreSQL is in recovery';
    END IF;

    CREATE TEMP TABLE protected_snapshot (
        schema_name text,
        relation_name text,
        oid oid,
        owner_name text
    ) ON COMMIT DROP;

    INSERT INTO protected_snapshot (schema_name, relation_name, oid, owner_name)
    SELECT
        n.nspname,
        c.relname,
        c.oid,
        pg_get_userbyid(c.relowner)
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE (n.nspname, c.relname) IN (
        ('Municipio', 'Notificacao'),
        ('weather', 'copernicus_bra'),
        ('Dengue_global', 'regional_saude'),
        ('Dengue_global', 'regional'),
        ('Dengue_global', 'CID10')
    );

    IF (SELECT count(*) FROM protected_snapshot) <> 5 THEN
        RAISE EXCEPTION 'protected active object snapshot is incomplete';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_depend AS d
        JOIN pg_class AS dependent ON dependent.oid = d.objid
        JOIN pg_namespace AS dependent_ns ON dependent_ns.oid = dependent.relnamespace
        JOIN pg_class AS referenced ON referenced.oid = d.refobjid
        JOIN pg_namespace AS referenced_ns ON referenced_ns.oid = referenced.relnamespace
        WHERE referenced_ns.nspname IN ('archive_dbf_upload', 'archive_sinan_upload')
          AND dependent_ns.nspname NOT IN ('archive_dbf_upload', 'archive_sinan_upload', 'pg_toast')
    ) THEN
        RAISE EXCEPTION 'an object outside the selected archive schemas depends on a removal target';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('archive_dbf_upload', 'archive_sinan_upload')
          AND c.relkind NOT IN ('i', 't')
          AND (n.nspname, c.relname, c.relkind) NOT IN (
              ('archive_dbf_upload', 'dbf_dbf', 'r'),
              ('archive_dbf_upload', 'dbf_dbfchunkedupload', 'r'),
              ('archive_dbf_upload', 'dbf_dbf_id_seq', 'S'),
              ('archive_dbf_upload', 'dbf_dbfchunkedupload_id_seq', 'S'),
              ('archive_sinan_upload', 'upload_sinanupload', 'r'),
              ('archive_sinan_upload', 'upload_sinanchunkedupload', 'r'),
              ('archive_sinan_upload', 'upload_sinanuploadlogstatus', 'r'),
              ('archive_sinan_upload', 'upload_sinanupload_id_seq', 'S'),
              ('archive_sinan_upload', 'upload_sinanchunkedupload_id_seq', 'S'),
              ('archive_sinan_upload', 'upload_sinanuploadlogstatus_id_seq', 'S')
          )
    ) THEN
        RAISE EXCEPTION 'selected archive schemas contain an unexpected object';
    END IF;

    -- Detach owned sequences so each object is removed by an explicit statement.
    ALTER SEQUENCE archive_dbf_upload.dbf_dbf_id_seq OWNED BY NONE;
    ALTER SEQUENCE archive_dbf_upload.dbf_dbfchunkedupload_id_seq OWNED BY NONE;
    ALTER SEQUENCE archive_sinan_upload.upload_sinanupload_id_seq OWNED BY NONE;
    ALTER SEQUENCE archive_sinan_upload.upload_sinanchunkedupload_id_seq OWNED BY NONE;
    ALTER SEQUENCE archive_sinan_upload.upload_sinanuploadlogstatus_id_seq OWNED BY NONE;

    -- Drop referencing tables before their referenced tables.
    DROP TABLE archive_sinan_upload.upload_sinanupload;
    DROP TABLE archive_sinan_upload.upload_sinanuploadlogstatus;
    DROP TABLE archive_sinan_upload.upload_sinanchunkedupload;
    DROP TABLE archive_dbf_upload.dbf_dbf;
    DROP TABLE archive_dbf_upload.dbf_dbfchunkedupload;

    DROP SEQUENCE archive_sinan_upload.upload_sinanupload_id_seq;
    DROP SEQUENCE archive_sinan_upload.upload_sinanuploadlogstatus_id_seq;
    DROP SEQUENCE archive_sinan_upload.upload_sinanchunkedupload_id_seq;
    DROP SEQUENCE archive_dbf_upload.dbf_dbf_id_seq;
    DROP SEQUENCE archive_dbf_upload.dbf_dbfchunkedupload_id_seq;
    DROP SCHEMA archive_sinan_upload;
    DROP SCHEMA archive_dbf_upload;

    FOR protected_before IN
        SELECT * FROM protected_snapshot ORDER BY schema_name, relation_name
    LOOP
        SELECT
            c.oid AS oid,
            pg_get_userbyid(c.relowner) AS owner_name
          INTO protected_after
        FROM pg_class AS c
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        WHERE n.nspname = protected_before.schema_name
          AND c.relname = protected_before.relation_name;

        IF protected_after.oid IS NULL THEN
            RAISE EXCEPTION 'protected object %.% disappeared during removal',
                protected_before.schema_name, protected_before.relation_name;
        END IF;

        IF protected_after.oid <> protected_before.oid THEN
            RAISE EXCEPTION 'protected object %.% changed OID from % to %',
                protected_before.schema_name, protected_before.relation_name,
                protected_before.oid, protected_after.oid;
        END IF;

        IF protected_after.owner_name <> protected_before.owner_name THEN
            RAISE EXCEPTION 'protected object %.% changed owner from % to %',
                protected_before.schema_name, protected_before.relation_name,
                protected_before.owner_name, protected_after.owner_name;
        END IF;
    END LOOP;

    IF EXISTS (
        SELECT 1
        FROM pg_namespace
        WHERE nspname IN (
            'archive_dbf_upload',
            'archive_sinan_upload'
        )
    ) THEN
        RAISE EXCEPTION 'one or more archive schemas remain after removal';
    END IF;
END
$$;

COMMIT;
