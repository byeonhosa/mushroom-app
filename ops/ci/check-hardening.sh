#!/usr/bin/env bash
# Assert the properties the running Compose stack must have (SRS REL-1, SEC-2):
# every container restarts by itself, rotates its logs, and publishes ports on
# the loopback interface only. Run from the repository root with the stack up.
set -Eeuo pipefail

fail=0
containers="$(docker compose ps -q)"
[ -n "$containers" ] || { echo "no running containers"; exit 1; }

for c in $containers; do
  name="$(docker inspect -f '{{.Name}}' "$c")"
  policy="$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$c")"
  max_size="$(docker inspect -f '{{index .HostConfig.LogConfig.Config "max-size"}}' "$c")"
  host_ips="$(docker inspect -f '{{range $port, $bindings := .HostConfig.PortBindings}}{{range $bindings}}{{.HostIp}} {{end}}{{end}}' "$c")"

  echo "$name restart=$policy log-max-size=${max_size:-none} published-on=${host_ips:-nothing}"
  if [ "$policy" != "unless-stopped" ]; then
    echo "  FAIL: restart policy is '$policy', expected unless-stopped"; fail=1
  fi
  if [ -z "$max_size" ]; then
    echo "  FAIL: no log rotation"; fail=1
  fi
  for ip in $host_ips; do
    if [ "$ip" != "127.0.0.1" ]; then
      echo "  FAIL: a port is published on '$ip', expected 127.0.0.1 only"; fail=1
    fi
  done
  # An empty HostIp means all interfaces. The loop above cannot see it.
  if docker inspect -f '{{range $port, $bindings := .HostConfig.PortBindings}}{{range $bindings}}[{{.HostIp}}]{{end}}{{end}}' "$c" | grep -q '\[\]'; then
    echo "  FAIL: a port is published on all interfaces"; fail=1
  fi
done

exit "$fail"
