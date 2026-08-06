\set ON_ERROR_STOP on
\pset pager off
\if :{?expected_database_name}
\else
  DO $$ BEGIN RAISE EXCEPTION 'expected_database_name is required'; END $$;
\endif
SELECT current_database() = :'expected_database_name' AS database_name_matches \gset
\if :database_name_matches
\else
  DO $$ BEGIN RAISE EXCEPTION 'connected database does not match expected_database_name'; END $$;
\endif
BEGIN;
SET TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '60s';

DO $validate$
BEGIN
  IF current_database() <> 'infodengue' THEN RAISE EXCEPTION 'wrong database'; END IF;
  IF to_regclass('public.chunked_upload_chunkedupload') IS NOT NULL THEN RAISE EXCEPTION 'candidate table remains'; END IF;
  IF to_regclass('public.chunked_upload_chunkedupload_id_seq') IS NOT NULL THEN RAISE EXCEPTION 'owned sequence remains'; END IF;
END $validate$;

SELECT object_name, 'absent' AS expected_state,
       CASE WHEN to_regclass(object_name) IS NULL THEN 'absent' ELSE 'present' END AS actual_state
  FROM (VALUES
    ('public.chunked_upload_chunkedupload'::text),
    ('public.chunked_upload_chunkedupload_id_seq'::text)
  ) AS candidate(object_name)
 ORDER BY object_name;

SELECT object_name, 'present' AS expected_state,
       CASE WHEN to_regclass(object_name) IS NULL THEN 'absent' ELSE 'present' END AS actual_state
  FROM (VALUES
    ('public.auth_user'::text),
    ('public.django_migrations'::text),
    ('public.django_session'::text),
    ('public.spatial_ref_sys'::text),
    ('topology.topology'::text),
    ('topology.layer'::text)
  ) AS protected(object_name)
 ORDER BY object_name;

DO $protected$
DECLARE
  protected record;
BEGIN
  FOR protected IN
    SELECT object_name, to_regclass(object_name) AS actual_relation
      FROM (VALUES
        ('public.auth_user'::text),
        ('public.django_migrations'::text),
        ('public.django_session'::text),
        ('public.spatial_ref_sys'::text),
        ('topology.topology'::text),
        ('topology.layer'::text)
      ) AS protected_objects(object_name)
  LOOP
    IF protected.actual_relation IS NULL THEN
      RAISE EXCEPTION 'protected object assertion failed: object_name=%, expected_state=present, actual_state=absent', protected.object_name;
    END IF;
  END LOOP;
END $protected$;

ROLLBACK;
