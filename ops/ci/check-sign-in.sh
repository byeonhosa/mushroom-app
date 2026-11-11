#!/usr/bin/env bash
# Exercise sign-in against the running Compose stack (SRS USR-1 to USR-3),
# through the frontend's /api forwarder, the way a browser reaches it.
#
# Needs BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD in .env so that the
# API created a first administrator at startup. BASE is the origin to test.
set -Eeuo pipefail

BASE="${BASE:-http://127.0.0.1:3000}"
API="${API:-http://127.0.0.1:8000}"
email="$(grep '^BOOTSTRAP_ADMIN_EMAIL=' .env | cut -d= -f2-)"
password="$(grep '^BOOTSTRAP_ADMIN_PASSWORD=' .env | cut -d= -f2-)"
jar="$(mktemp)"
trap 'rm -f "$jar"' EXIT

status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
expect() {  # expect <description> <wanted> <got>
  if [ "$2" = "$3" ]; then echo "ok   $1 ($3)"; else echo "FAIL $1: wanted $2, got $3"; exit 1; fi
}

expect "health without a session" 200 "$(status "$API/api/health")"
for path in /api/bags /api/species /api/dashboard/overview /api/reports/production /api/users /api/auth/me; do
  expect "$path without a session" 401 "$(status "$BASE$path")"
done
expect "sign-in page" 200 "$(status "$BASE/login")"
expect "setup complete" '{"setup_required":false}' "$(curl -fsS "$BASE/api/auth/status")"

login_body() { python3 -c 'import json,sys; print(json.dumps({"email": sys.argv[1], "password": sys.argv[2]}))' "$1" "$2"; }

expect "wrong password" 401 "$(status -X POST -H 'Content-Type: application/json' -H "Origin: $BASE" \
  -d "$(login_body "$email" 'not the password')" "$BASE/api/auth/login")"
expect "sign-in from another site" 403 "$(status -X POST -H 'Content-Type: application/json' -H 'Origin: https://evil.example' \
  -d "$(login_body "$email" "$password")" "$BASE/api/auth/login")"
expect "sign-in with no origin" 403 "$(status -X POST -H 'Content-Type: application/json' \
  -d "$(login_body "$email" "$password")" "$BASE/api/auth/login")"

expect "sign-in" 200 "$(status -c "$jar" -X POST -H 'Content-Type: application/json' -H "Origin: $BASE" \
  -d "$(login_body "$email" "$password")" "$BASE/api/auth/login")"
grep -q '#HttpOnly_' "$jar" || { echo "FAIL session cookie is not HttpOnly"; exit 1; }
echo "ok   session cookie is HttpOnly"

expect "who am I" '"admin"' "$(curl -fsS -b "$jar" "$BASE/api/auth/me" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["role"]))')"
expect "dashboard with a session" 200 "$(status -b "$jar" "$BASE/api/dashboard/overview")"
expect "write from another site with the cookie" 403 "$(status -b "$jar" -X POST -H 'Content-Type: application/json' \
  -H 'Origin: https://evil.example' -d '{"name":"x"}' "$BASE/api/grain-types")"

expect "sign-out" 204 "$(status -b "$jar" -X POST -H "Origin: $BASE" "$BASE/api/auth/logout")"
expect "the old cookie after sign-out" 401 "$(status -b "$jar" "$BASE/api/auth/me")"

# The deploy workflow's own check: a short session made on the server.
token="$(docker compose exec -T api python -m app.manage smoke-session)"
expect "server-made session" 200 "$(status -H "Cookie: mfa_session=$token" "$BASE/api/auth/me")"
echo "sign-in checks passed"
