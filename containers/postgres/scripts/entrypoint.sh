#!/usr/bin/env bash
set -euo pipefail

STANZA="${PG_STANZA:-${ENV:-prod}}"

mkdir -p /backups

if [ "${1:-}" = "postgres" ]; then
  shift
  exec docker-entrypoint.sh postgres \
    -c archive_mode=on \
    -c archive_command="pgbackrest --config=/etc/pgbackrest/pgbackrest.conf --stanza=${STANZA} archive-push %p" \
    -c restore_command="pgbackrest --config=/etc/pgbackrest/pgbackrest.conf --stanza=${STANZA} archive-get %f %p" \
    -c archive_timeout=60s \
    -c wal_level=replica \
    -c max_wal_senders=3 \
    "$@"

else
  exec docker-entrypoint.sh "$@"
fi
