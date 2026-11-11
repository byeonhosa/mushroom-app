#!/usr/bin/env bash
# Database backups for the Mushroom Farm App (SRS REL-2, REL-3).
#
# Runs inside the `backup` Compose service, which is built from postgres:16 so
# that pg_dump always matches the server. Dumps go to /backups, a directory
# mounted from the host outside the containers.
#
#   backup loop                 Daily dumps for as long as the container runs.
#   backup once [daily|predeploy]  One dump now.
#   backup status               Report the dumps on disk; non-zero if the newest
#                               daily dump is missing or too old.
#   backup verify               Restore the newest dump into a scratch database
#                               and compare it with the live one. Never touches
#                               the live database.
#   backup restore <file>       Replace the live database with a dump. Needs
#                               RESTORE_CONFIRM set to the database name.
#
# Connection settings come from the standard PG* variables.
set -Eeuo pipefail
umask 077

BACKUP_ROOT="${BACKUP_ROOT:-/backups}"
DAILY_KEEP="${BACKUP_DAILY_KEEP:-14}"
PREDEPLOY_KEEP="${BACKUP_PREDEPLOY_KEEP:-5}"
INTERVAL_HOURS="${BACKUP_INTERVAL_HOURS:-24}"
MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-26}"
CHECK_SECONDS="${BACKUP_CHECK_SECONDS:-600}"
DB_WAIT_SECONDS="${BACKUP_DB_WAIT_SECONDS:-120}"

log() { printf '%s backup: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

# Both directories always exist, so that a listing of an empty one is not an error.
mkdir -p "$BACKUP_ROOT/daily" "$BACKUP_ROOT/predeploy"

keep_for() {
  case "$1" in
    daily) echo "$DAILY_KEEP" ;;
    predeploy) echo "$PREDEPLOY_KEEP" ;;
    *) die "unknown backup kind '$1' (expected daily or predeploy)" ;;
  esac
}

# Newest dump in a directory, or nothing. Names sort by their UTC timestamp.
newest_in() {
  find "$1" -maxdepth 1 -type f -name 'mushroom_*.dump' 2>/dev/null | sort | tail -n 1
}

newest_overall() {
  find "$BACKUP_ROOT" -mindepth 2 -maxdepth 2 -type f -name 'mushroom_*.dump' 2>/dev/null \
    | awk -F/ '{print $NF "\t" $0}' | sort | tail -n 1 | cut -f2
}

count_in() {
  find "$1" -maxdepth 1 -type f -name 'mushroom_*.dump' 2>/dev/null | wc -l | tr -d ' '
}

age_seconds() {
  echo $(( $(date +%s) - $(stat -c %Y "$1") ))
}

wait_for_db() {
  local waited=0
  until pg_isready -q; do
    if [ "$waited" -ge "$DB_WAIT_SECONDS" ]; then
      die "database not reachable after ${DB_WAIT_SECONDS}s"
    fi
    sleep 2
    waited=$((waited + 2))
  done
}

prune() {
  local dir="$1" keep="$2"
  find "$dir" -maxdepth 1 -type f -name 'mushroom_*.dump' | sort -r | tail -n +"$((keep + 1))" \
    | while IFS= read -r old; do
        rm -f -- "$old"
        log "pruned $(basename "$old")"
      done
  # A dump interrupted part-way leaves a .partial file behind.
  find "$dir" -maxdepth 1 -type f -name '*.partial' -mmin +60 -delete
}

dump() {
  local kind="$1" keep dir final tmp
  keep="$(keep_for "$kind")"
  dir="$BACKUP_ROOT/$kind"
  mkdir -p "$dir"
  final="$dir/mushroom_$(date -u +%Y%m%d_%H%M%S).dump"
  tmp="$final.partial"

  pg_dump --format=custom --no-owner --no-privileges --file="$tmp"
  # A dump that cannot be listed cannot be restored; fail now, not on the day it is needed.
  pg_restore --list "$tmp" > /dev/null
  mv "$tmp" "$final"
  log "wrote $kind/$(basename "$final") ($(stat -c %s "$final") bytes)"
  prune "$dir" "$keep"
}

cmd_loop() {
  # As PID 1 the shell ignores SIGTERM unless it is trapped, and `docker stop`
  # would wait ten seconds and then kill it.
  trap 'log "stopping"; exit 0' TERM INT
  log "starting: daily dump every ${INTERVAL_HOURS}h, keeping ${DAILY_KEEP}"
  wait_for_db
  while true; do
    local newest
    newest="$(newest_in "$BACKUP_ROOT/daily")"
    if [ -z "$newest" ] || [ "$(age_seconds "$newest")" -ge $((INTERVAL_HOURS * 3600)) ]; then
      # set -e ends the loop on a failed dump: the container exits non-zero and
      # Docker restarts it, so a broken backup is visible in `docker compose ps`.
      wait_for_db
      dump daily
    fi
    # Sleep in the background so that the trap above runs at once.
    sleep "$CHECK_SECONDS" &
    wait $!
  done
}

cmd_once() {
  wait_for_db
  dump "${1:-daily}"
}

cmd_status() {
  local newest age_h
  for kind in daily predeploy; do
    log "$kind: $(count_in "$BACKUP_ROOT/$kind") dump(s)"
  done
  newest="$(newest_in "$BACKUP_ROOT/daily")"
  [ -n "$newest" ] || die "no daily dump exists yet"
  age_h=$(( $(age_seconds "$newest") / 3600 ))
  log "newest daily dump: $(basename "$newest"), ${age_h}h old, $(stat -c %s "$newest") bytes"
  if [ "$(age_seconds "$newest")" -gt $((MAX_AGE_HOURS * 3600)) ]; then
    die "newest daily dump is older than ${MAX_AGE_HOURS}h"
  fi
}

table_counts() {
  local db="$1" table
  psql -X -At -d "$db" -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1" \
    | while IFS= read -r table; do
        printf '%s=%s\n' "$table" "$(psql -X -At -d "$db" -c "SELECT count(*) FROM \"$table\"")"
      done
}

cmd_verify() {
  local file scratch restored live
  wait_for_db
  file="$(newest_overall)"
  [ -n "$file" ] || die "no dump to verify"
  scratch="${PGDATABASE}_restore_check"
  log "restoring $(basename "$(dirname "$file")")/$(basename "$file") into scratch database $scratch"

  dropdb --if-exists "$scratch" 2> /dev/null
  createdb "$scratch"
  # Expand the name now: the trap runs after this function's locals are gone.
  # shellcheck disable=SC2064
  trap "dropdb --if-exists '$scratch' > /dev/null 2>&1 || true" EXIT
  pg_restore --exit-on-error --no-owner --no-privileges --dbname="$scratch" "$file"

  restored="$(table_counts "$scratch")"
  live="$(table_counts "$PGDATABASE")"
  [ -n "$restored" ] || die "restored database has no tables"
  echo "$restored" | grep -q '^schema_migrations=[1-9]' || die "restored database has no applied migrations"

  log "restored $(echo "$restored" | wc -l | tr -d ' ') tables, $(echo "$restored" | awk -F= '{s += $2} END {print s + 0}') rows in total"
  log "restored: $(echo "$restored" | grep -E '^(bags|harvest_events|schema_migrations)=' | tr '\n' ' ')"
  if [ "$restored" = "$live" ]; then
    log "row counts match the live database"
  elif [ "${VERIFY_STRICT:-0}" = "1" ]; then
    diff <(echo "$live") <(echo "$restored") >&2 || true
    die "row counts differ from the live database"
  else
    log "row counts differ from the live database (expected when rows were written after the dump)"
  fi
  log "restore test passed"
}

cmd_restore() {
  local file="${1:-}"
  [ -n "$file" ] || die "usage: backup restore <file under $BACKUP_ROOT>"
  [ -f "$file" ] || file="$BACKUP_ROOT/$file"
  [ -f "$file" ] || die "dump not found: $1"
  [ "${RESTORE_CONFIRM:-}" = "$PGDATABASE" ] \
    || die "this replaces the live database. Set RESTORE_CONFIRM=$PGDATABASE to proceed"
  wait_for_db
  log "taking a safety dump before restoring"
  dump predeploy
  log "restoring $file over $PGDATABASE"
  pg_restore --clean --if-exists --exit-on-error --no-owner --no-privileges --dbname="$PGDATABASE" "$file"
  log "restore complete"
}

case "${1:-loop}" in
  loop) cmd_loop ;;
  once) shift; cmd_once "$@" ;;
  status) cmd_status ;;
  verify) cmd_verify ;;
  restore) shift; cmd_restore "$@" ;;
  *) die "unknown command '$1' (loop, once, status, verify, restore)" ;;
esac
