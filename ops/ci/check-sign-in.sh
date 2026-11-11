#!/usr/bin/env bash
# Exercise sign-in against the running Compose stack (SRS USR-1 to USR-3), the
# way a browser reaches it.
#
#   BASE       the origin to test. Default: the frontend's loopback port, whose
#              own /api forwarder stands in for the proxy.
#   CURL_OPTS  extra curl options, for example to reach a test hostname:
#              --resolve app.test:443:127.0.0.1 --insecure
#   VIA_PROXY  1 when BASE goes through the Caddy proxy: its security headers
#              are then required, and over https a Secure cookie and HSTS.
#
# Needs BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD in .env so that the
# API created a first administrator at startup.
set -Eeuo pipefail

BASE="${BASE:-http://127.0.0.1:3000}"
API="${API:-http://127.0.0.1:8000}"
CURL_OPTS="${CURL_OPTS:-}"
VIA_PROXY="${VIA_PROXY:-0}"
# Every curl call below goes through this, so CURL_OPTS applies to all of them.
# shellcheck disable=SC2086
curl() { command curl $CURL_OPTS "$@"; }
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
# The page is no use without its scripts and styles: fetch one of each.
page="$(curl -fsS "$BASE/login")"
for kind in js css; do
  asset="$(echo "$page" | grep -o "/_next/static/[^\"]*\.$kind" | head -n 1)"
  [ -n "$asset" ] || { echo "FAIL the sign-in page references no .$kind file"; exit 1; }
  expect "a .$kind file the page needs" 200 "$(status "$BASE$asset")"
done
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
# Netscape cookie file: the fourth field is TRUE for a Secure cookie.
secure="$(awk '/mfa_session/ {print $4}' "$jar")"
case "$BASE" in
  https://*) expect "session cookie is Secure over https" TRUE "$secure" ;;
  *) expect "session cookie is not marked Secure over http" FALSE "$secure" ;;
esac

if [ "$VIA_PROXY" = "1" ]; then
  headers="$(curl -s -D - -o /dev/null "$BASE/login" | tr -d '\r' | tr '[:upper:]' '[:lower:]')"
  for wanted in "x-content-type-options: nosniff" "x-frame-options: deny" "referrer-policy: same-origin" \
    "content-security-policy: default-src 'self'" "permissions-policy: camera=(self)"; do
    echo "$headers" | grep -qF "$wanted" || { echo "FAIL proxy header missing: $wanted"; exit 1; }
    echo "ok   proxy sends $wanted"
  done
  if echo "$headers" | grep -q '^server:'; then echo "FAIL proxy reveals a Server header"; exit 1; fi
  case "$BASE" in
    https://*)
      echo "$headers" | grep -q '^strict-transport-security: max-age=31536000' \
        || { echo "FAIL no Strict-Transport-Security over https"; exit 1; }
      echo "ok   proxy sends strict-transport-security over https" ;;
    *)
      if echo "$headers" | grep -q '^strict-transport-security:'; then
        echo "FAIL Strict-Transport-Security sent over plain http"; exit 1
      fi ;;
  esac
  expect "API health through the proxy" 200 "$(status "$BASE/api/health")"
fi

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
