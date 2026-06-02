#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STACK_DIR="${LMA_DEMO_STACK_DIR:-/tmp/lma-demo-stack}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
API_PORT="${LMA_DEMO_API_PORT:-8210}"
WEB_PORT="${LMA_DEMO_WEB_PORT:-8200}"
PUBLIC_HOST="${LMA_DEMO_PUBLIC_HOST:-222.73.85.26}"
API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:${API_PORT}}"
EXTERNAL_NO_PROXY_HOSTS=("localhost" "127.0.0.1" "::1" "$PUBLIC_HOST")
API_PID_FILE="$STACK_DIR/public-api-${API_PORT}.pid"
WEB_PID_FILE="$STACK_DIR/web-${WEB_PORT}.pid"
API_LOG_FILE="$STACK_DIR/public-api-${API_PORT}.log"
WEB_LOG_FILE="$STACK_DIR/web-${WEB_PORT}.log"
API_LOCAL_HEALTH="http://127.0.0.1:${API_PORT}/api/health"
WEB_LOCAL_ROOT="http://127.0.0.1:${WEB_PORT}/"
WEB_LOCAL_API_HEALTH="http://127.0.0.1:${WEB_PORT}/api/health"
WEB_PUBLIC_ROOT="http://${PUBLIC_HOST}:${WEB_PORT}/"
WEB_PUBLIC_API_HEALTH="http://${PUBLIC_HOST}:${WEB_PORT}/api/health"

mkdir -p "$STACK_DIR"

list_contains_item() {
  local list="$1"
  local item="$2"
  [[ ",$list," == *",$item,"* ]]
}

append_no_proxy_item() {
  local var_name="$1"
  local item="$2"
  local current="${!var_name:-}"
  if [[ -z "$current" ]]; then
    printf -v "$var_name" '%s' "$item"
  elif ! list_contains_item "$current" "$item"; then
    printf -v "$var_name" '%s,%s' "$current" "$item"
  fi
  export "$var_name"
}

ensure_external_no_proxy() {
  local host
  for host in "${EXTERNAL_NO_PROXY_HOSTS[@]}"; do
    append_no_proxy_item "NO_PROXY" "$host"
    append_no_proxy_item "no_proxy" "$host"
  done
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

tracked_process_alive() {
  local pid_file="$1"
  local pid
  pid="$(read_pid "$pid_file")"
  [[ -n "$pid" ]] && pid_alive "$pid"
}

cleanup_stale_pid() {
  local label="$1"
  local pid_file="$2"
  [[ -f "$pid_file" ]] || return 0
  local pid
  pid="$(read_pid "$pid_file")"
  if [[ -z "$pid" ]]; then
    echo "$label: removed invalid pid file $pid_file"
    rm -f "$pid_file"
    return 0
  fi
  if ! pid_alive "$pid"; then
    echo "$label: removed stale pid file $pid_file pid=$pid"
    rm -f "$pid_file"
  fi
}

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

http_status() {
  local url="$1"
  curl --noproxy '*' -sS -m 5 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true
}

url_healthy() {
  local url="$1"
  [[ "$(http_status "$url")" == "200" ]]
}

wait_for_url() {
  local label="$1"
  local url="$2"
  local seconds="$3"
  local elapsed=0
  while (( elapsed < seconds )); do
    if url_healthy "$url"; then
      echo "$label: healthy url=$url"
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  echo "$label: unhealthy url=$url status=$(http_status "$url")"
  return 1
}

safe_tail_log() {
  local label="$1"
  local log_file="$2"
  if [[ ! -f "$log_file" ]]; then
    echo "$label: log missing: $log_file"
    return 0
  fi
  echo "== tail $label ($log_file) =="
  tail -n 60 "$log_file" \
    | sed -E 's#(api[_-]?key|token|password|secret)([=:][^[:space:]]+)#\1=***#Ig; s#(Authorization: Bearer )[A-Za-z0-9._~+/-]+#\1***#Ig'
}

assert_url_healthy() {
  local label="$1"
  local url="$2"
  local status
  status="$(http_status "$url")"
  echo "$label $url => $status"
  [[ "$status" == "200" ]]
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
    if command -v setsid >/dev/null 2>&1; then
      nohup setsid bash -lc "$command" >"$log_file" 2>&1 < /dev/null &
    else
      nohup bash -lc "$command" >"$log_file" 2>&1 < /dev/null &
    fi
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

cleanup_stale_pid "public-api-${API_PORT}" "$API_PID_FILE"
cleanup_stale_pid "web-${WEB_PORT}" "$WEB_PID_FILE"

echo "== External wrapper services =="
for row in "${EXTERNAL_AGENTS[@]}"; do
  start_external_agent_if_needed "$row" || true
done
echo

echo "== Public API =="
ensure_external_no_proxy
echo "public API NO_PROXY includes ${PUBLIC_HOST}: $(list_contains_item "${NO_PROXY:-}" "$PUBLIC_HOST" && echo yes || echo no)"
echo "public API no_proxy includes ${PUBLIC_HOST}: $(list_contains_item "${no_proxy:-}" "$PUBLIC_HOST" && echo yes || echo no)"
if port_listening "$API_PORT"; then
  if tracked_process_alive "$API_PID_FILE"; then
    echo "public API: tracked existing process on port $API_PORT; not starting"
  else
    echo "public API: untracked existing process on port $API_PORT; not starting or killing"
  fi
  if ! wait_for_url "public API" "$API_LOCAL_HEALTH" 8; then
    echo "BLOCKER: port $API_PORT is occupied but ${API_LOCAL_HEALTH} is not healthy. Not killing an existing process."
    safe_tail_log "public API" "$API_LOG_FILE"
    exit 1
  fi
elif [[ ! -x "$PYTHON_BIN" ]]; then
  echo "public API: python not executable: $PYTHON_BIN"
  exit 1
else
  public_api_command="NO_PROXY=\"$NO_PROXY\" no_proxy=\"$no_proxy\" exec \"$PYTHON_BIN\" -m dotenv run --no-override -- \"$PYTHON_BIN\" -m uvicorn react_agent.public_api:app --host 127.0.0.1 --port \"$API_PORT\""
  start_process \
    "public-api-${API_PORT}" \
    "$ROOT_DIR" \
    "$public_api_command" \
    "$API_LOG_FILE" \
    "$API_PID_FILE"
  if ! wait_for_url "public API" "$API_LOCAL_HEALTH" 30; then
    safe_tail_log "public API" "$API_LOG_FILE"
    exit 1
  fi
  if ! tracked_process_alive "$API_PID_FILE"; then
    echo "BLOCKER: public API process exited after startup."
    safe_tail_log "public API" "$API_LOG_FILE"
    exit 1
  fi
fi
echo

echo "== Web =="
if port_listening "$WEB_PORT"; then
  if tracked_process_alive "$WEB_PID_FILE"; then
    echo "web: tracked existing process on port $WEB_PORT; not starting"
  else
    echo "web: untracked existing process on port $WEB_PORT; not starting or killing"
  fi
  if ! wait_for_url "web root" "$WEB_LOCAL_ROOT" 8; then
    echo "BLOCKER: port $WEB_PORT is occupied but ${WEB_LOCAL_ROOT} is not healthy. Not killing an existing process."
    safe_tail_log "web" "$WEB_LOG_FILE"
    exit 1
  fi
  if ! wait_for_url "web API proxy" "$WEB_LOCAL_API_HEALTH" 8; then
    echo "BLOCKER: 8200 is occupied by an existing process and /api proxy is unhealthy. 8200 may be pointing at a dead 8210 API."
    echo "public API health status: $(http_status "$API_LOCAL_HEALTH")"
    safe_tail_log "web" "$WEB_LOG_FILE"
    exit 1
  fi
elif ! command -v npm >/dev/null 2>&1; then
  echo "web: npm not found"
  exit 1
else
  start_process \
    "web-${WEB_PORT}" \
    "$ROOT_DIR" \
    "VITE_API_PROXY_TARGET=\"$API_PROXY_TARGET\" exec npm --prefix apps/web run dev -- --host 0.0.0.0 --port \"$WEB_PORT\"" \
    "$WEB_LOG_FILE" \
    "$WEB_PID_FILE"
  if ! wait_for_url "web root" "$WEB_LOCAL_ROOT" 30; then
    safe_tail_log "web" "$WEB_LOG_FILE"
    exit 1
  fi
  if ! wait_for_url "web API proxy" "$WEB_LOCAL_API_HEALTH" 30; then
    safe_tail_log "web" "$WEB_LOG_FILE"
    exit 1
  fi
  if ! tracked_process_alive "$WEB_PID_FILE"; then
    echo "BLOCKER: web process exited after startup."
    safe_tail_log "web" "$WEB_LOG_FILE"
    exit 1
  fi
fi
echo

echo "== Read-only health checks =="
final_ok=true
assert_url_healthy "api local health" "$API_LOCAL_HEALTH" || final_ok=false
assert_url_healthy "web local root" "$WEB_LOCAL_ROOT" || final_ok=false
assert_url_healthy "web local api health" "$WEB_LOCAL_API_HEALTH" || final_ok=false
assert_url_healthy "web public root" "$WEB_PUBLIC_ROOT" || final_ok=false
assert_url_healthy "web public api health" "$WEB_PUBLIC_API_HEALTH" || final_ok=false
if [[ "$final_ok" != true ]]; then
  echo "BLOCKER: demo stack did not pass required 8200/8210 health assertions."
  safe_tail_log "public API" "$API_LOG_FILE"
  safe_tail_log "web" "$WEB_LOG_FILE"
  exit 1
fi
echo

echo "== Short stability check =="
sleep 5
stability_ok=true
assert_url_healthy "api local health after stability wait" "$API_LOCAL_HEALTH" || stability_ok=false
assert_url_healthy "web local api health after stability wait" "$WEB_LOCAL_API_HEALTH" || stability_ok=false
if [[ -f "$API_PID_FILE" ]]; then
  if ! tracked_process_alive "$API_PID_FILE"; then
    echo "BLOCKER: tracked public API pid exited during stability check."
    stability_ok=false
  fi
fi
if [[ -f "$WEB_PID_FILE" ]]; then
  if ! tracked_process_alive "$WEB_PID_FILE"; then
    echo "BLOCKER: tracked web pid exited during stability check."
    stability_ok=false
  fi
fi
if [[ "$stability_ok" != true ]]; then
  safe_tail_log "public API" "$API_LOG_FILE"
  safe_tail_log "web" "$WEB_LOG_FILE"
  exit 1
fi
echo

"$ROOT_DIR/scripts/dev/status_8200_demo_stack.sh" || true

echo
echo "Demo URL: http://${PUBLIC_HOST}:${WEB_PORT}"
echo "Logs and PID files: $STACK_DIR"
echo "Stop main web/API: $ROOT_DIR/scripts/dev/stop_8200_demo_stack.sh"
echo "Stop script-started external agents too: $ROOT_DIR/scripts/dev/stop_8200_demo_stack.sh --include-external"
