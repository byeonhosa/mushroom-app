#!/usr/bin/env bash
# Set KEY=VALUE in an env file without printing the file.
#
#   set-env.sh <file> <KEY> <VALUE>
#
# Used by the deploy workflow to keep the non-secret keys of the droplet's
# .env in step with the repository. Idempotent: an existing key is replaced in
# place, a missing key is appended, every other line is left as it is. The
# value must not contain a newline. Nothing from the file is written to stdout.
set -Eeuo pipefail

file="${1:?usage: set-env.sh <file> <KEY> <VALUE>}"
key="${2:?usage: set-env.sh <file> <KEY> <VALUE>}"
value="${3-}"

case "$key" in
  *[!A-Za-z0-9_]*|"") echo "set-env: invalid key" >&2; exit 2 ;;
esac
case "$value" in
  *$'\n'*) echo "set-env: value for $key contains a newline" >&2; exit 2 ;;
esac

touch "$file"
chmod 600 "$file"

tmp="$(mktemp "${file}.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
chmod 600 "$tmp"

found=0
while IFS= read -r line || [ -n "$line" ]; do
  if [ "${line%%=*}" = "$key" ] && [ "$line" != "${line#*=}" ]; then
    if [ "$found" -eq 0 ]; then
      printf '%s=%s\n' "$key" "$value" >> "$tmp"
      found=1
    fi
  else
    printf '%s\n' "$line" >> "$tmp"
  fi
done < "$file"
if [ "$found" -eq 0 ]; then
  printf '%s=%s\n' "$key" "$value" >> "$tmp"
fi

if cmp -s "$tmp" "$file"; then
  echo "set-env: $key unchanged"
else
  mv "$tmp" "$file"
  trap - EXIT
  echo "set-env: $key set"
fi
