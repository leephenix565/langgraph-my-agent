#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STACK_DIR="${LMA_DEMO_STACK_DIR:-/tmp/lma-demo-stack}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
API_PORT="${LMA_DEMO_API_PORT:-8210}"
WEB_PORT="${LMA_DEMO_WEB_PORT:-8200}"
PUBLIC_HOST="${LMA_DEMO_PUBLIC_HOST:-222.73.85.26}"
API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:${API_PORT}}"

mkdir -p "$STACK_DIR"

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

start_process() {
  local label="$1"
  local workdir="$2"
  local command="$3"
  local log_file="$4"
  local pid_file="$5"

  if [[ ! -d "$workdir" ]]; then
    echo "WARN $label: workdir missing: $workdir"
    return 1
  fi

  (
    cd "$workdir"
    nohup bash -lc "$command" >"$log_file" 2>&1 &
    echo $! >"$pid_file"
  )
  echo "started $label pid=$(cat "$pid_file") log=$log_file"
}

start_external_agent_if_needed() {
  local row="$1"
  local agent_id name port workdir command note
  IFS='|' read -r agent_id name port workdir command note <<<"$row"

  if port_listening "$port"; then
    echo "external $agent_id ($name): existing_process on port $port; not starting"
    return 0
  fi

  if [[ -z "$command" ]]; then
    echo "external $agent_id ($name): missing_start_command for port $port ($note)"
    return 0
  fi

  if [[ ! -d "$workdir" ]]; then
    echo "external $agent_id ($name): missing_start_directory $workdir"
    return 0
  fi

  local log_file="$STACK_DIR/${agent_id}.log"
  local pid_file="$STACK_DIR/${agent_id}.pid"
  local marker_file="$STACK_DIR/${agent_id}.external.started"
  if start_process "$agent_id" "$workdir" "$command" "$log_file" "$pid_file"; then
    touch "$marker_file"
  else
    echo "external $agent_id ($name): start_failed; see $log_file"
  fi
}

probe_url() {
  local label="$1"
  local url="$2"
  local method="${3:-GET}"
  local args=(-sS --noproxy '*' -m 5 -o /dev/null -w '%{http_code} %{content_type} %{time_total}')
  local result
  if [[ "$method" == "HEAD" ]]; then
    result="$(curl -I "${args[@]}" "$url" 2>/dev/null || true)"
  else
    result="$(curl "${args[@]}" "$url" 2>/dev/null || true)"
  fi
  if [[ -z "$result" ]]; then
    result="unreachable"
  fi
  echo "$label $url => $result"
}

EXTERNAL_AGENTS=(
  "a03_macro_industry_research|宏观分析智能体|10014|/sdb/dlut/dev/宏观分析智能体|python3 -m uvicorn service:app --host 0.0.0.0 --port 10014|"
  "a04_commodity_hedging|商品定价分析智能体|10004|/sdb/dlut/dev/商品定价分析智能体/agent协议|python3 -m uvicorn service:app --host 0.0.0.0 --port 10004|"
  "a06_financial_statement_analysis|企业财务分析智能体|10005|/sdb/dlut/dev/企业财务分析智能体/agent协议|python3 -m uvicorn service:app --host 0.0.0.0 --port 10005|"
  "a10_stock_technical_analysis|个股技术分析智能体|10009|/sdb/dlut/dev/个股技术分析智能体|python3 -m uvicorn service:app --host 0.0.0.0 --port 10009|"
  "a11_index_technical_analysis|股票指数估值智能体|10003|/sdb/dlut/dev/股票指数估值智能体|python3 -m uvicorn service:app --host 0.0.0.0 --port 10003|"
  "a12_research_synthesis|分析师研报与观点集成智能体|10006|/sdb/dlut/dev/分析师研报与观点集成智能体|python3 -m uvicorn service:app --host 0.0.0.0 --port 10006|"
  "a14_ipo_investor_behavior|IPO投资者构成与行为分析智能体|10008|/sdb/dlut/dev/IPO投资者行为智能体/external_agent_scaffold|python3 -m uvicorn service:app --host 0.0.0.0 --port 10008|health may timeout on existing deployments"
  "a16_ml_valuation|机器学习企业估值智能体|10001|/sdb/dlut/dev/机器学习企业估值智能体|python3 -m uvicorn service:app --host 0.0.0.0 --port 10001|"
  "a17_traditional_valuation|传统企业估值智能体|10000|/sdb/dlut/dev/传统企业估值智能体|python3 -m uvicorn service:app --host 0.0.0.0 --port 10000|"
  "a18_meta_valuation|元学习企业估值智能体|10002|/sdb/dlut/dev/元学习企业估值智能体|python3 -m uvicorn service:app --host 0.0.0.0 --port 10002|"
  "a22_financial_data_service|金融数据服务智能体|11000|/sdb/dlut/dev/金融数据服务智能体||/health currently returns an HTML app shell; do not auto-start"
  "a23_crash_risk|股价崩盘风险智能体|10012|/sdb/dlut/dev/股价崩盘风险智能体/agent协议|python3 -m uvicorn service:app --host 0.0.0.0 --port 10012|"
  "a26_composite_valuation|综合估值智能体|10015|/sdb/dlut/prod/综合估值智能体|./start.sh 10015|formal port is 10015; status flags health agent_id drift"
)

echo "== langgraph-my-agent 8200 dev demo stack =="
echo "repo=$ROOT_DIR"
echo "stack_dir=$STACK_DIR"
echo "web=http://${PUBLIC_HOST}:${WEB_PORT}"
echo "api=http://127.0.0.1:${API_PORT}"
echo

echo "== External wrapper services =="
for row in "${EXTERNAL_AGENTS[@]}"; do
  start_external_agent_if_needed "$row" || true
done
echo

echo "== Public API =="
if port_listening "$API_PORT"; then
  echo "public API: existing_process on port $API_PORT; not starting"
elif [[ ! -x "$PYTHON_BIN" ]]; then
  echo "public API: python not executable: $PYTHON_BIN"
else
  start_process \
    "public-api-${API_PORT}" \
    "$ROOT_DIR" \
    "\"$PYTHON_BIN\" -m uvicorn react_agent.public_api:app --host 127.0.0.1 --port \"$API_PORT\" --env-file .env" \
    "$STACK_DIR/public-api-${API_PORT}.log" \
    "$STACK_DIR/public-api-${API_PORT}.pid" || true
fi
echo

echo "== Web =="
if port_listening "$WEB_PORT"; then
  echo "web: existing_process on port $WEB_PORT; not starting"
elif ! command -v npm >/dev/null 2>&1; then
  echo "web: npm not found"
else
  start_process \
    "web-${WEB_PORT}" \
    "$ROOT_DIR" \
    "VITE_API_PROXY_TARGET=\"$API_PROXY_TARGET\" npm --prefix apps/web run dev -- --host 0.0.0.0 --port \"$WEB_PORT\"" \
    "$STACK_DIR/web-${WEB_PORT}.log" \
    "$STACK_DIR/web-${WEB_PORT}.pid" || true
fi
echo

echo "== Read-only health checks =="
sleep 2
probe_url "api local health" "http://127.0.0.1:${API_PORT}/api/health"
probe_url "web local root" "http://127.0.0.1:${WEB_PORT}/" "HEAD"
probe_url "web local api health" "http://127.0.0.1:${WEB_PORT}/api/health"
probe_url "web public root" "http://${PUBLIC_HOST}:${WEB_PORT}/" "HEAD"
probe_url "web public api health" "http://${PUBLIC_HOST}:${WEB_PORT}/api/health"
echo

"$ROOT_DIR/scripts/dev/status_8200_demo_stack.sh" || true

echo
echo "Demo URL: http://${PUBLIC_HOST}:${WEB_PORT}"
echo "Logs and PID files: $STACK_DIR"
echo "Stop main web/API: $ROOT_DIR/scripts/dev/stop_8200_demo_stack.sh"
echo "Stop script-started external agents too: $ROOT_DIR/scripts/dev/stop_8200_demo_stack.sh --include-external"
