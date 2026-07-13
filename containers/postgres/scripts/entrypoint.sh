#!/usr/bin/env bash
set -euo pipefail

STANZA="${PG_STANZA:-${ENV:-prod}}"
ARCHIVE_MODE="${PG_ARCHIVE_MODE:-on}"
PGBACKREST_CONFIG="/etc/pgbackrest/pgbackrest.conf"
DEFAULT_ARCHIVE_COMMAND="pgbackrest --config=${PGBACKREST_CONFIG} --stanza=${STANZA} archive-push %p"
DEFAULT_RESTORE_COMMAND="pgbackrest --config=${PGBACKREST_CONFIG} --stanza=${STANZA} archive-get %f \"%p\""
ARCHIVE_COMMAND="${PG_ARCHIVE_COMMAND:-${DEFAULT_ARCHIVE_COMMAND}}"
RESTORE_COMMAND="${PG_RESTORE_COMMAND:-${DEFAULT_RESTORE_COMMAND}}"

mkdir -p /backups

if [ "${1:-}" = "postgres" ]; then
  if [ ! -r "${PGBACKREST_CONFIG}" ]; then
    echo "pgBackRest config is missing or unreadable: ${PGBACKREST_CONFIG}" >&2
    exit 1
  fi

  case "${ARCHIVE_MODE}" in
    off|on|always) ;;
    *)
      echo "Invalid PG_ARCHIVE_MODE '${ARCHIVE_MODE}' (use off|on|always)." >&2
      exit 1
      ;;
  esac

  shift
  exec docker-entrypoint.sh postgres \
    -c "archive_mode=${ARCHIVE_MODE}" \
    -c "archive_command=${ARCHIVE_COMMAND}" \
    -c "restore_command=${RESTORE_COMMAND}" \
    -c archive_timeout=60s \
    -c wal_level=replica \
    -c max_wal_senders=3 \
    "$@"
else
  exec docker-entrypoint.sh "$@"
fi
