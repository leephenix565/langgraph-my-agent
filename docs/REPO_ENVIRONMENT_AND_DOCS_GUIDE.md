# Main-System Repository Environment And Documentation Guide

本文说明服务器上 `langgraph-my-agent` 主系统在 `dev`、`prod`、`sandbox`
三个目录中的职责，以及当前说明文档如何使用、哪些是当前权威、哪些是历史审计记录。

## Scope

本文只覆盖主系统仓库：

```text
/sdb/dlut/dev/langgraph-my-agent
/sdb/dlut/prod/langgraph-my-agent
/sdb/dlut/sandbox/langgraph-my-agent-r8-a-class
```

不覆盖各外部生产智能体服务目录，例如：

```text
/sdb/dlut/prod/股票指数估值智能体
/sdb/dlut/prod/综合估值智能体
```

外部智能体服务由各自 owner 维护，主系统仓库只记录协议、接入、adapter、runbook
和 readiness 证据，不把外部服务源码并入主系统。

## Directory Roles

| Directory | Role | How To Use |
| --- | --- | --- |
| `/sdb/dlut/dev/langgraph-my-agent` | 正式开发主仓库 | 主系统代码权威来源。所有要长期保留的代码、测试、文档都应在这里 commit 并 push。 |
| `/sdb/dlut/sandbox/langgraph-my-agent-r8-a-class` | 沙盒/试验场 | 用来先试大改、跑端到端 trace、验证高风险想法。成功后把需要的 diff 回填到 dev。不要把 sandbox 当长期权威仓库。 |
| `/sdb/dlut/prod/langgraph-my-agent` | 生产运行副本 | 用于部署和运行主系统。不要把 prod 当开发源头；应从 GitHub 或 dev 的稳定提交同步。 |

推荐流转：

```text
sandbox 先试验
  -> dev 整理成正式代码、测试、文档、commit、push
  -> prod 从稳定 commit 更新部署
```

通俗说：

```text
sandbox = 草稿纸
dev     = 正式文档和代码仓库
prod    = 正式运行版本
```

## Update Policy

### dev

`dev` 是唯一应该直接做主系统长期开发的目录。

更新流程：

```bash
cd /sdb/dlut/dev/langgraph-my-agent
git status --short --branch
# edit / test
.venv/bin/python scripts/quality/run_quality.py --mode static
.venv/bin/python scripts/quality/run_quality.py --mode mainline
git add -A
git commit -m "<phase scoped message>"
git push origin reset/fixed-dag-v1
```

### sandbox

`sandbox` 可以有未提交实验改动。同步前必须先备份 diff：

```bash
cd /sdb/dlut/sandbox/langgraph-my-agent-r8-a-class
git diff --binary > /tmp/lma-sandbox-before-sync.patch
```

如果实验改动已经回填到 dev 并 push，可以把 sandbox 更新到 origin 的最新分支。
更新后它仍然只是试验场，不作为主系统代码权威来源。

### prod

`prod` 只用于运行。更新 prod 时应从已 push 的稳定提交同步：

```bash
cd /sdb/dlut/prod/langgraph-my-agent
git fetch origin
git checkout reset/fixed-dag-v1
git pull --ff-only origin reset/fixed-dag-v1
```

如果生产进程正在运行，代码同步和服务重启应分开执行，并记录旧 PID、启动命令、
新 PID、验证结果和回滚方式。

## Documentation Authority

当前主系统文档分三层。

### Current Authority

这些文档是当前入口，应优先看：

| Path | Purpose |
| --- | --- |
| `README.md` | 主系统阶段摘要和关键 non-claims。 |
| `docs/INDEX.md` | 文档地图和权威入口。 |
| `docs/REPO_ENVIRONMENT_AND_DOCS_GUIDE.md` | dev/prod/sandbox 目录职责、同步方式和文档整理策略。 |
| `docs/SYSTEM_MAP.md` | 当前主系统运行拓扑。 |
| `docs/ARCHITECTURE_FIXED_DAG.md` | 固定 DAG 架构和 27-agent 结构。 |
| `docs/CONTRACTS.md` | 主系统 contract、adapter 和 public/runtime 边界。 |
| `docs/DEMO_EXTERNAL_COMPUTE_DAG_RUNBOOK.md` | default-off external compute demo 运行方式。 |
| `docs/LOCAL_REMOTE_AGENT_DEMO_RUNBOOK.md` | 本地电脑通过 SSH tunnel 访问服务器 production agent 的 demo/dev 方法。 |
| `docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` | 当前 production readiness/problem playbook。 |
| `docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md` | 面向外部智能体 owner 的修复提示词手册。 |
| `docs/CONTROLLED_READINESS_SMOKE_LOG.md` | 受控 smoke、trace、non-claims 记录。 |

### Phase Records

这些文档是阶段证据和交接记录，应保留但不作为“当前唯一入口”：

```text
docs/R8_13D_SANDBOX_L3_BACKFILL_HANDOFF.md
docs/R8_13E_PRODUCTION_L3_BACKFILL_SMOKE.md
docs/R8_13F_END_TO_END_PRODUCTION_TRACE_QA.md
docs/R8_13G_VALUE_L2_STANCE_REMEDIATION.md
docs/AGENT_READINESS_MATRIX_R8_8N.md
docs/DEPLOYED_AGENT_INVENTORY_DEFERRED.md
```

这些文件不要轻易删除，因为它们保存了具体阶段的备份路径、smoke artifact、
修改范围、non-claims 和回滚线索。

### Candidate Future Merge

后续如果文档数量继续膨胀，可以按下面方向合并，而不是直接删除：

| Candidate | Suggested Destination |
| --- | --- |
| `R8_13D/E/F/G` 阶段文档 | 摘要并入 `CONTROLLED_READINESS_SMOKE_LOG.md`，保留原文件为历史 phase record。 |
| `AGENT_READINESS_MATRIX_R8_8N.md` | 保留为 R8-8N 历史快照，当前入口指向 `AGENT_READINESS_MATRIX_FIXED_DAG.md`。 |
| `DEPLOYED_AGENT_INVENTORY_DEFERRED.md` | 如内容过期，合并摘要到 readiness matrix 的 deferred/problem section。 |
| 过长的 README 阶段流水 | 后续可把旧阶段细节迁入 `docs/INDEX.md` caveat 或 `docs/CHANGELOG.md`，README 保留最新摘要。 |

当前不建议删除任何阶段文档。更安全的做法是：

1. 更新 `docs/INDEX.md` 标明当前权威入口。
2. 在阶段文档中保留历史上下文。
3. 等生产链路稳定后，再做一次专门的 docs compaction phase。

## Non-Claims

本文只是主系统目录和文档管理说明：

- 不启用 runtime bindings。
- 不设置 `live_verified=true`。
- 不设置 `invoke_enabled_by_default=true`。
- 不调用 `/v1/agent/invoke`。
- 不证明 production readiness。
- 不把 sandbox 实验结果直接等同于 production evidence。
- 不把 prod 目录改动当作长期源码管理替代品。

