#!/usr/bin/env bash
set -euo pipefail

STANZA="${PG_STANZA:-${ENV:-prod}}"
ARCHIVE_MODE="${PG_ARCHIVE_MODE:-on}"
PGBACKREST_CONFIG="/etc/pgbackrest/pgbackrest.conf"
DEFAULT_ARCHIVE_COMMAND="pgbackrest --config=${PGBACKREST_CONFIG} --stanza=${STANZA} archive-push %p"
DEFAULT_RESTORE_COMMAND="pgbackrest --config=${PGBACKREST_CONFIG} --stanza=${STANZA} archive-get %f \"%p\""
ARCHIVE_COMMAND="${PG_ARCHIVE_COMMAND:-${DEFAULT_ARCHIVE_COMMAND}}"
RESTORE_COMMAND="${PG_RESTORE_COMMAND:-${DEFAULT_RESTORE_COMMAND}}"


guard_pg18_initialization() {
  local data_dir="${PGDATA:-/var/lib/postgresql/18/docker}"
  local postgres_root
  postgres_root="$(dirname "$(dirname "$data_dir")")"

  if [ -e "${postgres_root}/PG_VERSION" ]; then
    echo "Refusing PostgreSQL 18 startup: conflicting PG_VERSION at ${postgres_root}." >&2
    exit 1
  fi
  if [ -e "${data_dir}/PG_VERSION" ]; then
    if [ "$(tr -d '[:space:]' < "${data_dir}/PG_VERSION")" != "18" ]; then
      echo "Refusing PostgreSQL 18 startup: ${data_dir}/PG_VERSION is not 18." >&2
      exit 1
    fi
    return
  fi
  if [ -d "$data_dir" ] && find "$data_dir" -mindepth 1 -print -quit | grep -q .; then
    echo "Refusing PostgreSQL 18 startup: ${data_dir} is not an empty PG18 directory." >&2
    exit 1
  fi
  if [ "${ALLOW_PG18_INITIALIZATION:-0}" != "1" ]; then
    echo "Refusing to initialize empty PG18 data directory ${data_dir}. Set ALLOW_PG18_INITIALIZATION=1 for one-time initialization, then unset it." >&2
    exit 1
  fi
}
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
  guard_pg18_initialization
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
