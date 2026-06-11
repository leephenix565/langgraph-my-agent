#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/dev/start_agent_tunnels.sh --server-host HOST --server-user USER [--identity-file PATH] [--use-same-ports true]

Starts SSH local forwards for the R8-12 external compute demo allowlist.
The tunnel binds only 127.0.0.1 and forwards local 100xx ports to the same
ports on the remote server. It does not store passwords or write .env files.

Options:
  --server-host HOST       SSH server host, for example 222.73.85.26.
  --server-user USER       SSH user name.
  --identity-file PATH     Optional SSH private key path.
  --use-same-ports true    Required. The current demo bridge expects same-port
                           local forwards such as 127.0.0.1:10000 -> remote
                           127.0.0.1:10000.
  -h, --help               Show this help.
USAGE
}

SERVER_HOST=""
SERVER_USER=""
IDENTITY_FILE=""
USE_SAME_PORTS="true"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-host)
      SERVER_HOST="${2:-}"
      shift 2
      ;;
    --server-user)
      SERVER_USER="${2:-}"
      shift 2
      ;;
    --identity-file)
      IDENTITY_FILE="${2:-}"
      shift 2
      ;;
    --use-same-ports)
      USE_SAME_PORTS="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$SERVER_HOST" || -z "$SERVER_USER" ]]; then
  echo "Both --server-host and --server-user are required." >&2
  usage >&2
  exit 2
fi

if [[ "$USE_SAME_PORTS" != "true" && "$USE_SAME_PORTS" != "1" ]]; then
  echo "--use-same-ports must remain true for the current demo bridge." >&2
  exit 2
fi

if [[ -n "$IDENTITY_FILE" && ! -f "$IDENTITY_FILE" ]]; then
  echo "Identity file does not exist: $IDENTITY_FILE" >&2
  exit 2
fi

PORTS=(
  10000
  10001
  10002
  10006
  10009
  10022
  10020
  10010
  10011
  10013
  10012
  10014
  10015
  10023
  10016
  10024
)

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "sport = :${port}" | tail -n +2 | grep -q .
    return $?
  fi
  if command -v netstat >/dev/null 2>&1; then
    netstat -an | grep -E "[.:]${port}[[:space:]].*LISTEN" >/dev/null 2>&1
    return $?
  fi
  return 1
}

for port in "${PORTS[@]}"; do
  if port_in_use "$port"; then
    echo "Local port 127.0.0.1:${port} is already in use. Stop that process before starting the tunnel." >&2
    exit 1
  fi
done

SSH_ARGS=(
  -N
  -T
  -o ExitOnForwardFailure=yes
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=3
)

if [[ -n "$IDENTITY_FILE" ]]; then
  SSH_ARGS+=(-i "$IDENTITY_FILE")
fi

for port in "${PORTS[@]}"; do
  SSH_ARGS+=(-L "127.0.0.1:${port}:127.0.0.1:${port}")
done

SSH_ARGS+=("${SERVER_USER}@${SERVER_HOST}")

echo "Starting R8-12 local remote-agent demo tunnel."
echo "Local bind: 127.0.0.1 only"
echo "Forwarded ports: ${PORTS[*]}"
echo "Press Ctrl+C to close the tunnel."
exec ssh "${SSH_ARGS[@]}"
