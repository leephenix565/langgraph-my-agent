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

stop_pid_file() {
  local label="$1"
  local pid_file="$2"
  if [[ ! -f "$pid_file" ]]; then
    echo "$label: no pid file"
    return 0
  fi
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    echo "$label: empty pid file"
    rm -f "$pid_file"
    return 0
  fi
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "$label: stopped pid=$pid"
  else
    echo "$label: pid=$pid not running"
  fi
  rm -f "$pid_file"
}

echo "== Stop main demo services =="
stop_pid_file "web-${WEB_PORT}" "$STACK_DIR/web-${WEB_PORT}.pid"
stop_pid_file "public-api-${API_PORT}" "$STACK_DIR/public-api-${API_PORT}.pid"

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
