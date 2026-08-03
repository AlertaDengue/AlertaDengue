\set ON_ERROR_STOP on
\pset pager off
\if :{?verified_package_path}
\else \echo 'verified_package_path is required' \quit 3
\endif
\if :{?expected_database_oid}
\else \echo 'expected_database_oid is required' \quit 3
\endif
\if :{?expected_dump_sha256}
\else \echo 'expected_dump_sha256 is required' \quit 3
\endif
\if :{?verification_status}
\else \echo 'verification_status is required' \quit 3
\endif
\if :{?expected_dbf_rows}
\else \echo 'expected_dbf_rows is required' \quit 3
\endif
\if :{?expected_dbfchunkedupload_rows}
\else \echo 'expected_dbfchunkedupload_rows is required' \quit 3
\endif
\if :{?expected_dbf_id_seq_last_value}
\else \echo 'expected_dbf_id_seq_last_value is required' \quit 3
\endif
\if :{?expected_dbf_id_seq_is_called}
\else \echo 'expected_dbf_id_seq_is_called is required' \quit 3
\endif
\if :{?expected_dbfchunkedupload_id_seq_last_value}
\else \echo 'expected_dbfchunkedupload_id_seq_last_value is required' \quit 3
\endif
\if :{?expected_dbfchunkedupload_id_seq_is_called}
\else \echo 'expected_dbfchunkedupload_id_seq_is_called is required' \quit 3
\endif
SET statement_timeout = '5min';
SET lock_timeout = '5s';
BEGIN;
SELECT pg_advisory_xact_lock(hashtext('AlertaDengue.archive_dbf_upload'));
DO $$
DECLARE n integer;
BEGIN
  IF :'verification_status' <> 'PASS' THEN RAISE EXCEPTION 'verified restore status must be PASS'; END IF;
  IF :'verified_package_path' = '' OR :'expected_dump_sha256' !~ '^[0-9a-fA-F]{64}$' THEN RAISE EXCEPTION 'invalid verified package evidence'; END IF;
  IF current_database() <> 'dengue' THEN RAISE EXCEPTION 'wrong database'; END IF;
  IF (SELECT oid::text FROM pg_database WHERE datname=current_database()) <> :'expected_database_oid' THEN RAISE EXCEPTION 'database OID mismatch'; END IF;
  SELECT count(*) INTO n FROM pg_class c JOIN pg_namespace ns ON ns.oid=c.relnamespace
  WHERE ns.nspname='archive_dbf_upload' AND c.relname IN ('dbf_dbf','dbf_dbfchunkedupload','dbf_dbf_id_seq','dbf_dbfchunkedupload_id_seq');
  IF n <> 4 OR EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace ns ON ns.oid=c.relnamespace
                       WHERE ns.nspname='archive_dbf_upload' AND c.relname NOT IN ('dbf_dbf','dbf_dbfchunkedupload','dbf_dbf_id_seq','dbf_dbfchunkedupload_id_seq'))
  THEN RAISE EXCEPTION 'archive inventory is not exact'; END IF;
  IF (xpath('/row/count/text()', query_to_xml('SELECT count(*) AS count FROM archive_dbf_upload.dbf_dbf',false,true,'')))[1]::text::bigint <> :'expected_dbf_rows'::bigint
     OR (xpath('/row/count/text()', query_to_xml('SELECT count(*) AS count FROM archive_dbf_upload.dbf_dbfchunkedupload',false,true,'')))[1]::text::bigint <> :'expected_dbfchunkedupload_rows'::bigint
  THEN RAISE EXCEPTION 'row count mismatch'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname='archive_dbf_upload' AND sequencename='dbf_dbf_id_seq' AND last_value IS NOT DISTINCT FROM :'expected_dbf_id_seq_last_value'::bigint AND is_called = :'expected_dbf_id_seq_is_called'::boolean)
     OR NOT EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname='archive_dbf_upload' AND sequencename='dbf_dbfchunkedupload_id_seq' AND last_value IS NOT DISTINCT FROM :'expected_dbfchunkedupload_id_seq_last_value'::bigint AND is_called = :'expected_dbfchunkedupload_id_seq_is_called'::boolean)
  THEN RAISE EXCEPTION 'sequence value mismatch'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.deptype='a' AND d.objid='archive_dbf_upload.dbf_dbf_id_seq'::regclass AND d.refobjid='archive_dbf_upload.dbf_dbf'::regclass AND d.refobjsubid=1)
     OR NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.deptype='a' AND d.objid='archive_dbf_upload.dbf_dbfchunkedupload_id_seq'::regclass AND d.refobjid='archive_dbf_upload.dbf_dbfchunkedupload'::regclass AND d.refobjsubid=1)
  THEN RAISE EXCEPTION 'sequence ownership mismatch'; END IF;
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid IN ('archive_dbf_upload.dbf_dbf'::regclass,'archive_dbf_upload.dbf_dbfchunkedupload'::regclass) AND conrelid NOT IN ('archive_dbf_upload.dbf_dbf'::regclass,'archive_dbf_upload.dbf_dbfchunkedupload'::regclass))
     OR EXISTS (SELECT 1 FROM pg_depend d JOIN pg_rewrite r ON r.oid=d.objid WHERE d.refobjid IN ('archive_dbf_upload.dbf_dbf'::regclass,'archive_dbf_upload.dbf_dbfchunkedupload'::regclass))
  THEN RAISE EXCEPTION 'new inbound dependency exists'; END IF;
  IF (SELECT count(*) FROM pg_constraint WHERE contype='f' AND conrelid IN ('archive_dbf_upload.dbf_dbf'::regclass,'archive_dbf_upload.dbf_dbfchunkedupload'::regclass) AND confrelid='public.auth_user'::regclass) <> 2 THEN RAISE EXCEPTION 'outbound FK inventory mismatch'; END IF;
  IF EXISTS (SELECT 1 FROM (VALUES ('Dengue_global','CID10'),('Dengue_global','Municipio'),('Dengue_global','parameters_uf'),('Dengue_global','regional'),('Dengue_global','regional_saude'),('Municipio','Notificacao'),('Municipio','Historico_alerta'),('Municipio','Historico_alerta_chik'),('Municipio','Historico_alerta_zika'),('episcanner','sir_params'),('ingestion','run'),('ingestion','sinan_stage'),('vegetation_indices','vegetation_index_metrics'),('weather','copernicus_bra'),('public','auth_user')) AS p(s,r) WHERE to_regclass(format('%I.%I',p.s,p.r)) IS NULL) THEN RAISE EXCEPTION 'protected active object missing'; END IF;
END $$;
DROP TABLE archive_dbf_upload.dbf_dbfchunkedupload;
DROP TABLE archive_dbf_upload.dbf_dbf;
DO $$
BEGIN
  IF to_regclass('archive_dbf_upload.dbf_dbf_id_seq') IS NOT NULL OR to_regclass('archive_dbf_upload.dbf_dbfchunkedupload_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'owned sequences did not disappear with tables'; END IF;
  IF to_regclass('archive_dbf_upload.dbf_dbf') IS NOT NULL OR to_regclass('archive_dbf_upload.dbf_dbfchunkedupload') IS NOT NULL THEN RAISE EXCEPTION 'archived tables remain'; END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace ns ON ns.oid=c.relnamespace WHERE ns.nspname='archive_dbf_upload') THEN RAISE EXCEPTION 'archive schema is not empty'; END IF;
END $$;
DROP SCHEMA archive_dbf_upload;
DO $$
BEGIN
  IF to_regclass('archive_dbf_upload.dbf_dbf') IS NOT NULL OR to_regclass('archive_dbf_upload.dbf_dbfchunkedupload') IS NOT NULL OR to_regclass('archive_dbf_upload.dbf_dbf_id_seq') IS NOT NULL OR to_regclass('archive_dbf_upload.dbf_dbfchunkedupload_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'DBF objects remain after removal'; END IF;
END $$;
COMMIT;
