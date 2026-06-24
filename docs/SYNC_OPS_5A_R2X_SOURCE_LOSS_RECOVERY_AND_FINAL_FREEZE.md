# SYNC-OPS-5A-R2X Source-Loss Recovery And Final Freeze

SYNC-OPS-5A-R2X hardens the R1X source-recovery plan before any real
production execution. It does not write prod, active sandbox, baseline pointers,
owner-dev repositories, endpoints, processes, or machine approvals.

## Source-Loss Semantics

`risk_financial_fraud` is an irreversible source-loss incident:
`source_deleted_process_still_alive`.

The current process can still listen on port `10013`, but its current prod cwd
has no source-bearing files. Once that in-memory process is stopped, the old
runtime cannot be restored by writing an empty tree back. Recovery therefore
uses `verified_roll_forward`, not ordinary file rollback.

The R1X recovery plan is superseded because it planned in-place writes into the
current cwd and described empty-tree backup restore as rollback. The R1X P2S
projection is also superseded because it retained placeholder paths and lacked
a complete physical materialization manifest.

## Recovery V2

The V2 contract requires:

- materialize the verified 67-file source package into a sibling candidate;
- keep the incumbent process running until offline tests and a shadow canary
  pass;
- run shadow canary only on loopback with an alternate approved port;
- compare incumbent and canary at contract level without persisting raw bodies;
- require explicit irreversible source-loss cutover acknowledgement;
- cut over by rolling forward to the verified candidate;
- preserve source-loss evidence and fail closed to manual intervention if
  roll-forward cannot settle.

## Launch Authority

The source package integrity audit passes, but current launch authority is
blocked. The process is not owned by a discovered systemd/supervisor unit, the
registry still names scaffold `service.py`, live argv is `python3 -u -m
app.main`, and the live `0.0.0.0:10013` bind depends on environment state that
R2X did not read or reproduce.

The current acceptance is therefore `blocked_source_loss_launch_authority`.
The next safe step is to create a durable launch authority contract: exact
launcher, cwd, environment source references, required variable names, stop
method, startup timeout, log path, and process ownership. Environment values
remain out of artifacts.

## P2S And Candidate

R2X defines the full P2S rebase shape: concrete stage/candidate/archive paths,
26 Agent dispositions, full materialization manifest, recovered risk-fraud file
count `67`, and stage/activation approval split.

For the first user change after recovery, `market_capital_flow_chip` contract
test material is the selected low-risk candidate. It is classified
`A_docs_tests_material` with no process, live, or delete requirement. The
previous `financial_data_service` candidate remains superseded as a runtime
wrapper change.

## Non-Claims

R2X does not execute recovery, P2S rebase, experiment materialization, first
cycle, process actions, endpoint calls, or approvals.
