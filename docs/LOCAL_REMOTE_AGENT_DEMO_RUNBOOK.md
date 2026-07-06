# Local Remote Agent Demo Runbook

本手册用于 R8-12B：在本地电脑修改和运行主系统代码，同时通过 SSH
tunnel 安全访问服务器上的 production agent。它只服务 demo/dev，不是生产默认
接入方案。

## 适用场景

- 主系统代码已经 clone 到你的电脑，需要本地开发或演示 Web。
- 外部 agent 仍运行在服务器 production 端口，例如 `10000`、`10001`、
  `10015`。
- 你希望本地主系统继续只访问 `127.0.0.1:100xx`，由 SSH tunnel 把请求安全
  转发到服务器本机的 production agent。

## 前置条件

- 你有服务器 SSH 权限。
- 服务器上的 16 个 R8-12 demo allowlist production agent 已监听对应
  `100xx` 端口。
- 你的本地电脑没有占用这些端口：
  `10000`, `10001`, `10002`, `10006`, `10009`, `10022`, `10020`,
  `10010`, `10011`, `10013`, `10012`, `10014`, `10015`, `10023`,
  `10016`, `10024`。
- 你已经 clone 或 pull 最新 `frontend-ui-refinements` 代码。
- 本地已安装 `ssh`、Python 环境和 Web 前端依赖。

## 启动 SSH Tunnel

Linux/macOS/Git Bash:

```bash
scripts/dev/start_agent_tunnels.sh \
  --server-host 222.73.85.26 \
  --server-user <your_ssh_user> \
  --identity-file ~/.ssh/id_rsa
```

如果你使用默认 SSH key，可以省略 `--identity-file`。

Windows PowerShell:

```powershell
.\scripts\dev\start_agent_tunnels.ps1 `
  -ServerHost 222.73.85.26 `
  -ServerUser <your_ssh_user> `
  -IdentityFile $HOME\.ssh\id_rsa
```

脚本只绑定本地 `127.0.0.1`，不会绑定 `0.0.0.0`，也不会把 production
`100xx` 端口公开到公网。脚本使用 `ExitOnForwardFailure=yes`，只要任一端口
转发失败就退出。

## 启动本地 API

在 repo 根目录运行：

```bash
ENABLE_EXTERNAL_COMPUTE_DEMO=1 \
EXTERNAL_COMPUTE_DEMO_ALLOWLIST=value_traditional_valuation,value_ml_valuation,value_meta_valuation,value_research_synthesis,market_stock_technical,market_capital_flow_chip,sentiment_company_radar,risk_identification,risk_compliance_review,risk_financial_fraud,risk_crash,macro_analysis,value_composite,market_composite,risk_composite,macro_composite \
EXTERNAL_COMPUTE_DEMO_TIMEOUT_SECONDS=20 \
.venv/bin/python -m uvicorn react_agent.public_api:app --host 127.0.0.1 --port 8212
```

当前 bridge 读取 env allowlist 和内置 same-port demo registry。
`config/fixed_dag/external_compute_demo_allowlist.local.example.json` 是本地
tunnel 配置样例和交接文档，不会替代 `runtime_bindings.json`，也不是 live
配置。

## 启动本地 Web

另开一个终端：

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8212 \
npm --prefix apps/web run dev -- --host 127.0.0.1 --port 8213
```

浏览器打开：

```text
http://127.0.0.1:8213
```

建议 demo 问题：

```text
请从估值、市场、风险和宏观角度分析贵州茅台 600519.SH 当前是否值得关注。
```

## 安全边界

- SSH tunnel 只用于 demo/dev。
- 只绑定本地 `127.0.0.1`。
- 不暴露 production `100xx` 端口到公网。
- 不写 `.env`，不保存 SSH 密码。
- 不修改 `config/fixed_dag/runtime_bindings.json`。
- 不设置 `live_verified=true`。
- 不设置 `invoke_enabled_by_default=true`。
- 不调用 `/v1/agent/invoke`。
- R8-12 demo bridge 只调用 allowlist production `/v1/agent/compute`。
- `sentiment_company_radar` 只作为 market agent，不允许路由到 risk。

## 常见问题

### Tunnel 启动后立即退出

通常是本地端口被占用，或远端 SSH 连接失败。先关闭占用端口的本地进程，再重启
tunnel。脚本会在启动前检查本地端口并给出具体端口号。

### 本地端口被占用

不要改成 `0.0.0.0` 或随机公网端口。当前 bridge 期望同端口
`127.0.0.1:100xx`。停止本地占用进程后再启动 tunnel。

### Web 能打开但报告没有外部结果

检查 API 终端是否设置了：

```text
ENABLE_EXTERNAL_COMPUTE_DEMO=1
EXTERNAL_COMPUTE_DEMO_ALLOWLIST=...
```

也要确认 SSH tunnel 仍在运行。bridge 失败会 fail-soft 回 deterministic
placeholder，所以页面仍可能正常出报告，但外部 compute 摘要会缺失。

### Agent timeout

确认 tunnel 没断，服务器 production agent 仍在对应 `100xx` 端口监听。可以适当
提高 `EXTERNAL_COMPUTE_DEMO_TIMEOUT_SECONDS`，但不要把未 ready 服务加入
allowlist。

### Chromium 截图缺失

Web demo 不依赖截图。截图工具需要本机安装 Chromium/Chrome 或 Playwright
浏览器二进制；缺失时只能手动浏览页面或补装浏览器后再截图。

### Windows PowerShell execution policy

如果 PowerShell 拦截脚本执行，可以在当前终端临时放宽：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

不要把 SSH 密码写进脚本或 `.env`。

## 如何关闭

- 在 SSH tunnel 终端按 `Ctrl+C`。
- 在 API 终端按 `Ctrl+C`。
- 在 Web 终端按 `Ctrl+C`。
- 如需检查端口是否释放，可运行：

```bash
ss -ltnp | grep -E ':10000|:10001|:10002|:10006|:10009|:10022|:10020|:10010|:10011|:10013|:10012|:10014|:10015|:10023|:10016|:10024' || true
```

Windows 可用：

```powershell
Get-NetTCPConnection -LocalAddress 127.0.0.1 -State Listen |
  Where-Object { $_.LocalPort -in 10000,10001,10002,10006,10009,10022,10020,10010,10011,10013,10012,10014,10015,10023,10016,10024 }
```
