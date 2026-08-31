# Historical-alert `tweet` removal runbook

Migration `dados.0008_remove_historical_alert_tweet_column` removes the
retired nullable numeric `tweet` column from the three historical-alert tables.
It is atomic and irreversible. It does not use `CASCADE`, refresh materialized
views, or change Django model state.

## Before staging

1. Confirm the deployed AlertTools build is revision
   `9199ac34e066a5617985ce5b73003b47056bcd6d` and that its
   `tabela_historico()` and `write_alerta()` implementations do not emit or
   reference the historical-alert `tweet` field.
2. Verify the archived Tweet data exists and is recoverable. Record the archive
   identifier or path, creation date, archive verification result, and
   responsible operator. Do not record credentials in this runbook or ticket.
3. Verify a current, tested, restorable PostgreSQL backup. Record the backup
   ID, timestamp, successful restore-check result, and responsible operator.
4. Immediately before migration, query and record total, non-null, and NULL
   `tweet` counts for every target table. The local audit baseline is:

   | Table | Total | Non-null | NULL |
   | --- | ---: | ---: | ---: |
   | `Historico_alerta` | 4,823,903 | 3,909,767 | 914,136 |
   | `Historico_alerta_chik` | 4,823,913 | 3,910,577 | 913,336 |
   | `Historico_alerta_zika` | 4,099,637 | 4,099,637 | 0 |

   Staging and production must be queried again immediately before migration;
   do not assume these local values apply there.
5. Check there are no long-running transactions or conflicting table locks:

   ```sql
   SELECT pid, usename, state, query_start, wait_event_type, wait_event,
          query
   FROM pg_stat_activity
   WHERE datname = current_database()
     AND state <> 'idle'
   ORDER BY query_start;

   SELECT relation::regclass, mode, granted, pid
   FROM pg_locks
   WHERE relation IN (
       '"Municipio"."Historico_alerta"'::regclass,
       '"Municipio"."Historico_alerta_chik"'::regclass,
       '"Municipio"."Historico_alerta_zika"'::regclass
   )
   ORDER BY relation, granted DESC, mode;
   ```

6. Confirm the pre-flight schema: each table has a nullable `numeric` `tweet`
   column with default `NULL`, and re-run the dependency audit for views,
   materialized views, functions, triggers, constraints, and indexes.

## Apply in staging

1. Put writers that could use an older AlertTools build into maintenance mode.
2. The normal `makim django.migrate` task runs `python manage.py migrate
   --no-input` without `--database`; it targets `default`. The database router
   rejects the `dados` app on `default`, so do not use that task for this
   migration. Run the following explicit `dados` commands instead:

   ```bash
   python AlertaDengue/manage.py showmigrations dados --database=dados

   python AlertaDengue/manage.py migrate \
     dados 0008_remove_historical_alert_tweet_column \
     --plan \
     --database=dados

   python AlertaDengue/manage.py migrate \
     dados 0008_remove_historical_alert_tweet_column \
     --database=dados
   ```

3. Review that the plan contains only `dados.0008`. Do not add `CASCADE`,
   `IF EXISTS`, manual DDL, or a materialized-view refresh.
4. Record the migration output and elapsed time. A lock timeout means stop and
   resolve the conflicting session; do not retry against an unknown writer.

## Verify

1. Check all three tables no longer have `tweet` and that their row counts are
   unchanged from the pre-flight record.
2. Query `/api/alertcity/` for dengue, chikungunya, and Zika: each response must
   be HTTP 200, retain its normal fields, and omit `tweet`.
3. Smoke-test `/api/v1/alert-city/` and `/api/internal/historical-alerts/` to
   confirm their existing response contracts remain unchanged.
4. Inspect application, Celery, and PostgreSQL logs for missing-column or
   writer errors.

Recovery is a database restore from the verified pre-flight backup; the Django
migration intentionally has no reverse operation.
