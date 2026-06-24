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

## External Agent Repository Ownership

主系统目录规则不能直接套用到其他外部 agent 仓库：

- `/sdb/dlut/dev/langgraph-my-agent` 是主系统 dev 权威目录。
- `/sdb/dlut/dev/*` 下的其他 agent 仓库由对应开发者自己开发、修改和维护；
  主系统维护者不能默认把这些仓库当作可随意改写的工作区。
- `/sdb/dlut/sandbox/*` 是用户可自由试验、大改和验证的区域；如果用户在
  sandbox 中修改了 agent，可以由用户按需要把验证后的改动同步到对应 prod 运行目录。
- `/sdb/dlut/prod/*` 是运行目录。用户从 sandbox 同步到 prod 的 agent 改动，
  和其他同学从各自 dev agent 仓库同步到 prod 的改动，是两条不同来源的流程。
- 其他开发者在自己 dev agent 仓库中的修改，应由对应开发者按其服务流程同步到 prod；
  主系统文档只记录协议、证据和交接要求，不替代外部 agent owner 的源码管理。

因此，后续处理外部 agent 时必须先确认来源：这是用户的 sandbox 实验、用户要同步
到 prod 的运行改动，还是其他开发者拥有的 dev agent 仓库改动。

CS1-C3X adds a durability rule for prod-only wrapper work: a successful
production smoke is not the same as owner-source acceptance. When a production
service runtime copy is patched before its owner-dev repository is updated, the
phase must leave a reviewable handoff patch outside the main-system repo. The
current handoff root is:

```text
/sdb/dlut/prod/backups/cs1c3x_20260622T103501Z/owner_handoffs
```

Those handoffs do not modify owner-dev repos. They are inputs for service
owners to review, apply, test, or reject in their own repositories.

CS1-C3R adds a portable copy of the same handoff material under:

```text
/tmp/lma-cs1c3r-evidence-durability-20260622T121352Z/portable_owner_patches
```

This portable bundle is easier to move off-server for owner review. It still
does not modify owner-dev repos and does not imply owner acceptance.

BF-COMPLETE-X records a separate sandbox-to-prod backfill rule: if a
current-relevant integration fix was formed and validated in sandbox service
work, production may satisfy it by exact, semantically equivalent, or stricter
verified behavior. Owner-dev durability remains recorded separately and is not
part of the sandbox-to-prod completion denominator.

POST-BF-B1X continues that separation. It applies scoped production wrapper
readiness and latency fixes for runtime services while leaving owner-dev repos
untouched. These prod runtime changes require backup, hash, restart, smoke, and
owner handoff records; they do not make owner-dev durability complete and do not
change the main-system default runtime.

POST-BF-B2X changes only the main-system production orchestration and release
documentation. It does not modify owner-dev repositories or external service
source trees, and it does not make excluded data/source/semantic agents part of
the default path. Prod main should receive the pushed dev commit by ff-only
deployment; rollback uses `DISABLE_NON_L4_EXTERNAL_COMPUTE_DEFAULT=1` rather
than editing runtime bindings.

P2S-BASELINE-X adds a separate external-agent sandbox baseline refresh rule.
After backfill and release closure, external-agent experiments may need a fresh
starting point from current production runtime roots. That flow is
`prod external-agent runtime source -> versioned sandbox baseline` only. It
does not apply to the main-system repository, does not make production an
owner-dev authority, and must not copy secrets, logs, caches, `.git`, model
weights, datasets, or runtime artifacts. If any production source-bearing file
contains credential-like inline content, the current sandbox path must not be
switched until that source is resolved by exact safe copy, sandbox-only
sanitized derivative, or proven-unreachable omission. P2S-CLOSE-R1 applied that
rule, switched `/sdb/dlut/sandbox/r8-13a/services/prod` to the refreshed
26-agent baseline, and preserved the previous sandbox tree for rollback and
experiment review.

SYNC-OPS-1 adds a read-only control-plane layer for future external-agent
synchronization. The main-system repo now owns stable sync metadata under
`config/ops/` and read-only planner code under `src/react_agent/ops/`. That
metadata records candidate prod, sandbox, owner-dev, service-unit, and contract
facts; it does not make prod an owner source authority and does not imply
owner-dev acceptance. Future write phases must use immutable plans, hash-bound
file approvals, target-before hashes, and per-Agent transactions. The active
external-agent sandbox baseline remains immutable; experiments must fork from
it rather than editing it in place.

SYNC-OPS-3X adds the executable sandbox-to-prod control plane. External-agent
experiments still fork from the immutable sandbox baseline, but only explicit
change units can become future prod actions. The control plane preserves
prod-only and owner-dev provenance by default, blocks sanitized derivatives
unless they become reviewed prod-safe refactors, and separates file apply,
process action, live smoke, rollback, owner handoff, and publish-and-rebase
approvals. The real 3X rehearsal is zero-action only and does not modify prod,
active sandbox, owner-dev, endpoints, or processes.

SYNC-OPS-4X productizes the bidirectional workflow as a one-command
publish-and-rebase cycle. Cycle plans bind S2P, projected prod after-state, and
precomputed P2S evidence; no-op cycle evidence may be written to the durable
artifact store, but real non-zero cycles still require an exact machine
approval bundle.

SYNC-OPS-5A adds the first non-zero qualification gate. A normal Agent whose
current prod, baseline, or experiment inventory is empty cannot be treated as a
successful noop unless it is explicitly registered as an empty tree. If the
baseline is incomplete, generate a repair request before creating a non-zero
experiment cycle.

SYNC-OPS-5A-R1X tightens that repair rule for missing production source. A
historical sandbox baseline is evidence only; it is not current production
source authority by itself. If a registered prod root is empty while the
service should still exist, the next executable artifact must be a prod source
recovery plan with backup, offline tests, process/live approval requirements,
rollback, and crash recovery. Only after recovery settles may P2S create a full
new baseline; a one-Agent partial stage is not a valid active-baseline repair.

SYNC-OPS-5A-R2X further distinguishes deleted-source live processes from normal
file recovery. If the only live runtime is an in-memory process whose cwd is an
empty source tree, restarting that service is irreversible unless launch
authority is complete. The safe plan uses a sibling candidate, shadow canary,
contract-level incumbent/canary comparison, and verified roll-forward; it must
not write files into the current cwd or call an empty-tree restore rollback.

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

上面流程只描述主系统仓库。外部 agent 的运行同步另按 owner 和来源区分：

```text
用户 sandbox agent 实验
  -> 用户按需同步到对应 prod agent 运行目录

其他开发者 dev agent 仓库
  -> 对应开发者按服务流程同步到 prod agent 运行目录
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
| `docs/PRE_BACKFILL_AUDIT_FIXED_DAG.md` | Backfill 前总账：说明主系统已合入内容、sandbox agent 实验、prod 运行目录状态、L4 compute-default runtime 和后续回填边界。 |
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

- 不额外启用 runtime bindings。R8-13Q 已批准的两个 L4
  `external_compute_default` 行是当前事实，不代表本文又启用了新 runtime。
- 不额外设置 `live_verified=true`。当前两个 L4 live flag 只表示
  `/v1/agent/compute` default runtime smoke。
- 不设置 `invoke_enabled_by_default=true`。
- 不调用 `/v1/agent/invoke`。
- 不证明 production readiness。
- 不把 sandbox 实验结果直接等同于 production evidence。
- 不把 prod 目录改动当作长期源码管理替代品。
- 不把其他开发者维护的 dev agent 仓库当作主系统可直接改写的权威目录。

## Sync Planner Boundary

After P2S-CLOSE-R1, `/sdb/dlut/sandbox/r8-13a/services/prod` is the active
production-derived external-agent baseline. It is not an experiment workspace.
Future experiments should fork a versioned baseline, carry an experiment
manifest, and use the read-only `agent-sync` planner to produce an immutable
P2S/S2P/cycle plan before any approved write phase.

SYNC-OPS-1R further requires P2S to materialize a new versioned stage before
activation. Observed diff rows are review evidence only; they are not file
actions. Sanitized derivatives and sandbox-local secret-requirement metadata
must remain explicitly modeled and must not be treated as raw production
source.

SYNC-OPS-1R2 adds recursive source/support-root coverage and parity checks.
The active sandbox is still immutable input; temp reconstruction is allowed only
under repo-external `/tmp` and is used to prove the planned safe tree, not to
create the real sandbox stage.

SYNC-OPS-2A adds writer primitives but keeps execution in temporary fixtures.
Real P2S stage, activate, and rollback require a separate machine approval,
matching environment snapshot, locks, and approved artifact-store root. The
configured durable artifact root remains `/sdb/dlut/ops-artifacts/agent-sync`,
but SYNC-OPS-2A does not create or write it.

SYNC-OPS-2A-R1 closes source selection before any real P2S execution. Local
tool metadata, backups, generated outputs/results/reports, data/model assets,
runtime noise, sensitive files, and unknown files are not copied into a new
sandbox baseline by default. The actual current P2S plan must pass full-scale
stage/verify/activate/rollback rehearsal under repo-external `/tmp`; the real
active sandbox and pointer remain immutable inputs until a later approved
execution phase.

SYNC-OPS-2A-R2 freezes the executable plan contract and approval split. A real
stage/verify run requires a stage-only machine approval, but it no longer
initializes the durable artifact store. SYNC-OPS-2A-R3 makes
`/sdb/dlut/ops-artifacts/agent-sync` a separate one-time bootstrap target with
its own plan, environment hash, approval request, and `STORE_METADATA.json`.
Activation and rollback are a separate later approval bound to the real stage
run and digest; stage-only approval cannot switch the active sandbox or update
the pointer. SYNC-OPS-2A-R4 tightens bootstrap rollback: store metadata records
an ownership ledger, blocked rollback is a true zero-mutation no-op, and
approval requests are not machine approvals. SYNC-OPS-2B0 attempted the first
real bootstrap but stopped before approval because the current environment
snapshot drifted from the approved snapshot. SYNC-OPS-2A-R5 replaces that
volatile snapshot boundary with stable approval binding, execution
constraints, and diagnostic observations. SYNC-OPS-2B0-R1 then created the
durable artifact store and metadata. SYNC-OPS-2B1 created and verified the
versioned P2S stage while leaving the active sandbox and pointer unchanged. The
next write approval boundary is activation/rollback; it must bind the real
stage run id, artifact index SHA, stage digest, stage validation SHA, current
active pointer SHA, and current active tree SHA before any sandbox switch.
SYNC-OPS-2B2X completes that boundary: first activation, controlled rollback
restoration, separate post-rollback reactivation approval, final reactivation,
and P2S topic closure are complete. The active sandbox now points to baseline
`20260624T060045Z`, while production sources, owner-dev repositories,
endpoints, process state, and S2P remain out of scope.
