#!/usr/bin/env bash
set -euo pipefail

STACK_DIR="${LMA_DEMO_STACK_DIR:-/tmp/lma-demo-stack}"
API_PORT="${LMA_DEMO_API_PORT:-8210}"
WEB_PORT="${LMA_DEMO_WEB_PORT:-8200}"
INCLUDE_EXTERNAL=false

if [[ "${1:-}" == "--include-external" ]]; then
  INCLUDE_EXTERNAL=true
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--include-external]" >&2
  exit 2
fi

port_listening() {
  local port="$1"
  python3 - "$port" <<'PY' >/dev/null 2>&1
import socket
import sys

sock = socket.socket()
sock.settimeout(0.5)
try:
    sock.connect(("127.0.0.1", int(sys.argv[1])))
except OSError:
    raise SystemExit(1)
else:
    raise SystemExit(0)
finally:
    sock.close()
PY
}

read_pid() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 0
  local pid
  pid="$(tr -d '[:space:]' <"$pid_file" 2>/dev/null || true)"
  if [[ "$pid" =~ ^[0-9]+$ ]]; then
    echo "$pid"
  fi
}

pid_alive() {
  local pid="${1:-}"
  [[ "$pid" =~ ^[0-9]+$ ]] && [[ -d "/proc/$pid" ]]
}

stop_pid_file() {
  local label="$1"
  local pid_file="$2"
  local port="${3:-}"
  if [[ ! -f "$pid_file" ]]; then
    echo "$label: no pid file"
    if [[ -n "$port" ]] && port_listening "$port"; then
      echo "$label: skipped untracked listener on port $port"
    fi
    return 0
  fi
  local pid
  pid="$(read_pid "$pid_file")"
  if [[ -z "$pid" ]]; then
    echo "$label: removed invalid pid file"
    rm -f "$pid_file"
    if [[ -n "$port" ]] && port_listening "$port"; then
      echo "$label: skipped untracked listener on port $port"
    fi
    return 0
  fi
  if pid_alive "$pid"; then
    kill "$pid"
    echo "$label: stopped tracked pid=$pid"
    for _ in {1..20}; do
      pid_alive "$pid" || break
      sleep 0.2
    done
    if pid_alive "$pid"; then
      echo "$label: tracked pid=$pid still alive after SIGTERM"
    fi
  else
    echo "$label: removed stale pid file pid=$pid"
  fi
  rm -f "$pid_file"
  if [[ -n "$port" ]] && port_listening "$port"; then
    echo "$label: skipped remaining listener on port $port because it is not tracked by $pid_file"
  fi
}

echo "== Stop main demo services =="
stop_pid_file "web-${WEB_PORT}" "$STACK_DIR/web-${WEB_PORT}.pid" "$WEB_PORT"
stop_pid_file "public-api-${API_PORT}" "$STACK_DIR/public-api-${API_PORT}.pid" "$API_PORT"

if [[ "$INCLUDE_EXTERNAL" != true ]]; then
  echo "External services were not stopped. Pass --include-external to stop only script-started external agents."
  exit 0
fi

echo "== Stop script-started external agents =="
shopt -s nullglob
for marker_file in "$STACK_DIR"/*.external.started; do
  agent_id="$(basename "$marker_file" .external.started)"
  pid_file="$STACK_DIR/${agent_id}.pid"
  stop_pid_file "$agent_id" "$pid_file"
  rm -f "$marker_file"
done
