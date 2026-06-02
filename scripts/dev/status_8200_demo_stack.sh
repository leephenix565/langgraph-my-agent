#!/usr/bin/env bash
set -euo pipefail

STACK_DIR="${LMA_DEMO_STACK_DIR:-/tmp/lma-demo-stack}"
PUBLIC_HOST="${LMA_DEMO_PUBLIC_HOST:-222.73.85.26}"
API_PORT="${LMA_DEMO_API_PORT:-8210}"
WEB_PORT="${LMA_DEMO_WEB_PORT:-8200}"

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

pid_status() {
  local label="$1"
  local pid_file="$2"
  if [[ ! -f "$pid_file" ]]; then
    echo "$label: no pid file"
    return
  fi
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "$label: running pid=$pid"
  else
    echo "$label: not running pid=${pid:-unknown}"
  fi
}

echo "== Main demo services =="
pid_status "public-api-${API_PORT}" "$STACK_DIR/public-api-${API_PORT}.pid"
pid_status "web-${WEB_PORT}" "$STACK_DIR/web-${WEB_PORT}.pid"
if port_listening "$API_PORT"; then
  echo "port $API_PORT: listening"
else
  echo "port $API_PORT: not listening"
fi
if port_listening "$WEB_PORT"; then
  echo "port $WEB_PORT: listening"
else
  echo "port $WEB_PORT: not listening"
fi
echo "demo_url=http://${PUBLIC_HOST}:${WEB_PORT}"
echo

echo "== Public API proxy readiness =="
python3 - "$STACK_DIR/public-api-${API_PORT}.pid" "$PUBLIC_HOST" <<'PY'
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

pid_file = Path(sys.argv[1])
public_host = sys.argv[2]


def summarize_proxy(value: str | None) -> str:
    if not value:
        return "unset"
    parsed = urlparse(value)
    host = parsed.hostname or ""
    port = parsed.port or ""
    return f"set host={host or '-'} port={port or '-'}"


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def contains_host(value: str | None, host: str) -> bool:
    items = [item.strip() for item in str(value or "").split(",") if item.strip()]
    return host in items


if not pid_file.exists():
    print("public_api_pid: missing")
    print("HTTP_PROXY: unknown")
    print("HTTPS_PROXY: unknown")
    print(f"NO_PROXY contains {public_host}: unknown")
    print(f"no_proxy contains {public_host}: unknown")
    print("external wrapper trust_env effective: false")
    raise SystemExit(0)

pid = pid_file.read_text(encoding="utf-8", errors="replace").strip()
print(f"public_api_pid: {pid or 'missing'}")
env: dict[str, str] = {}
if pid:
    environ_path = Path(f"/proc/{pid}/environ")
    if environ_path.exists():
        for item in environ_path.read_bytes().split(b"\0"):
            if b"=" in item:
                key, value = item.split(b"=", 1)
                env[key.decode(errors="replace")] = value.decode(errors="replace")
    else:
        print("public_api_env: unavailable")

print(f"HTTP_PROXY: {summarize_proxy(env.get('HTTP_PROXY') or env.get('http_proxy'))}")
print(f"HTTPS_PROXY: {summarize_proxy(env.get('HTTPS_PROXY') or env.get('https_proxy'))}")
print(f"NO_PROXY contains {public_host}: {'yes' if contains_host(env.get('NO_PROXY'), public_host) else 'no'}")
print(f"no_proxy contains {public_host}: {'yes' if contains_host(env.get('no_proxy'), public_host) else 'no'}")
print(
    "external wrapper trust_env effective: "
    f"{'true' if truthy(env.get('EXTERNAL_AGENT_TRUST_ENV')) else 'false'}"
)
PY
echo

echo "== External wrapper health =="
python3 - <<'PY'
import json
import socket
import time
import urllib.error
import urllib.request

AGENTS = [
    ("a03_macro_industry_research", "宏观分析智能体", 10014, "macro_analysis"),
    ("a04_commodity_hedging", "商品定价分析智能体", 10004, "price_influence_agent"),
    ("a06_financial_statement_analysis", "企业财务分析智能体", 10005, "financial_report_agent"),
    ("a10_stock_technical_analysis", "个股技术分析智能体", 10009, "technical_stock"),
    ("a11_index_technical_analysis", "股票指数估值智能体", 10003, "valuation_index"),
    ("a12_research_synthesis", "分析师研报与观点集成智能体", 10006, "analyst_research"),
    ("a14_ipo_investor_behavior", "IPO投资者构成与行为分析智能体", 10008, "ipo_investor_behavior"),
    ("a16_ml_valuation", "机器学习企业估值智能体", 10001, "valuation_ml"),
    ("a17_traditional_valuation", "传统企业估值智能体", 10000, "valuation_traditional"),
    ("a18_meta_valuation", "元学习企业估值智能体", 10002, "valuation_meta"),
    ("a22_financial_data_service", "金融数据服务智能体", 11000, "financial_data_service"),
    ("a23_crash_risk", "股价崩盘风险智能体", 10012, "crash_risk"),
    ("a26_composite_valuation", "综合估值智能体", 10015, "composite_valuation"),
]


def port_open(port: int) -> bool:
    sock = socket.socket()
    sock.settimeout(0.5)
    try:
        sock.connect(("127.0.0.1", port))
    except OSError:
        return False
    finally:
        sock.close()
    return True


def fetch(url: str):
    request = urllib.request.Request(url, method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    start = time.time()
    try:
        with opener.open(request, timeout=3) as response:
            body = response.read(4096)
            return response.status, response.headers.get("content-type", ""), body, round((time.time() - start) * 1000)
    except urllib.error.HTTPError as exc:
        body = exc.read(512)
        return exc.code, exc.headers.get("content-type", ""), body, round((time.time() - start) * 1000)
    except Exception as exc:  # noqa: BLE001 - status output must be fail-soft.
        return "ERR", type(exc).__name__, b"", round((time.time() - start) * 1000)


def classify(status, content_type, body, expected_agent_id, is_open):
    observed_agent_id = ""
    schema_version = ""
    if status == "ERR":
        return ("PORT_LISTENING_HEALTH_TIMEOUT" if is_open else "NOT_RUNNING_CAN_START", observed_agent_id, schema_version)
    if status != 200:
        return ("RUNNING_SCHEMA_ISSUE", observed_agent_id, schema_version)
    if "html" in content_type.lower() or body.lstrip().lower().startswith(b"<!doctype html"):
        return ("WRONG_SERVICE_OR_HTML", observed_agent_id, schema_version)
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return ("RUNNING_SCHEMA_ISSUE", observed_agent_id, schema_version)
    if not isinstance(payload, dict):
        return ("RUNNING_SCHEMA_ISSUE", observed_agent_id, schema_version)
    observed_agent_id = str(payload.get("agent_id") or payload.get("external_agent_id") or "")
    schema_version = str(payload.get("schema_version") or "")
    if observed_agent_id == expected_agent_id:
        return ("READY_RUNNING_HEALTH_OK", observed_agent_id, schema_version)
    return ("RUNNING_SCHEMA_ISSUE", observed_agent_id, schema_version)


print("agent_id | name | port | port_open | health_status | observed_agent_id | schema_version | classification")
for agent_id, name, port, expected_agent_id in AGENTS:
    is_open = port_open(port)
    status, content_type, body, latency_ms = fetch(f"http://127.0.0.1:{port}/health")
    classification, observed_agent_id, schema_version = classify(status, content_type, body, expected_agent_id, is_open)
    note = f"{status}/{content_type}/{latency_ms}ms"
    print(f"{agent_id} | {name} | {port} | {is_open} | {note} | {observed_agent_id or '-'} | {schema_version or '-'} | {classification}")
    if agent_id == "a22_financial_data_service":
        api_status, api_content_type, api_body, api_latency_ms = fetch(f"http://127.0.0.1:{port}/api/health")
        api_shape = "json_object" if api_body.lstrip().startswith(b"{") else "non_json"
        print(f"a22_api_health | {name} | {port} | {is_open} | {api_status}/{api_content_type}/{api_latency_ms}ms | - | {api_shape} | COMPAT_OBSERVATION_ONLY")
PY
echo

echo "== Transitional internal placeholder agents =="
echo "a07_macro_sentiment a08_industry_hotspot a09_company_sentiment_radar a13_fund_manager_behavior a15_entity_relation_extraction a19_risk_identification a20_compliance_review a24_financial_fraud_risk a27_risk_constraint a28_composite_sentiment"
echo "These are not owner-provided external HTTP services yet."
