#!/usr/bin/env bash
set -euo pipefail

MODE="${1:?mode is required (ready|recovery-complete)}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"
SLEEP_SECONDS="${SLEEP_SECONDS:-1}"

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

pg_probe_ready() {
  if [ -n "${PG_ISREADY_CMD:-}" ]; then
    bash -lc "$PG_ISREADY_CMD"
    return
  fi

  pg_isready --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" >/dev/null 2>&1
}

pg_probe_recovery_complete() {
  if [ -n "${PG_IN_RECOVERY_CMD:-}" ]; then
    result="$(bash -lc "$PG_IN_RECOVERY_CMD")"
  else
    result="$(
      psql -tA -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -c "SELECT pg_is_in_recovery();"
    )"
  fi

  [ "$(printf '%s' "$result" | tr -d '[:space:]')" = "f" ]
}

wait_for_ready() {
  local ready=0

  for _ in $(seq 1 "$TIMEOUT_SECONDS"); do
    if pg_probe_ready; then
      ready=1
      break
    fi
    sleep "$SLEEP_SECONDS"
  done

  if [ "$ready" -ne 1 ]; then
    echo "[EE] PostgreSQL did not become ready in time." >&2
    exit 1
  fi
}

wait_for_recovery_complete() {
  local ready=0

  for _ in $(seq 1 "$TIMEOUT_SECONDS"); do
    if pg_probe_recovery_complete; then
      ready=1
      break
    fi
    sleep "$SLEEP_SECONDS"
  done

  if [ "$ready" -ne 1 ]; then
    echo "[EE] PostgreSQL recovery did not complete in time." >&2
    exit 1
  fi
}

case "$MODE" in
  ready)
    wait_for_ready
    ;;
  recovery-complete)
    wait_for_recovery_complete
    ;;
  *)
    echo "[EE] Unsupported wait mode: $MODE" >&2
    exit 2
    ;;
esac
