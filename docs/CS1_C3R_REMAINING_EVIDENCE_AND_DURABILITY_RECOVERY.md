# CS1-C3R Remaining Evidence And Durability Recovery

Phase CS1-C3R is a controlled follow-up to CS1-C3X. It corrects artifact
integrity and L3 evidence projection gaps, hardens cross-L3 contributor
semantics, updates portable owner handoff artifacts, and records blockers for
remaining source-authority paths.

## Scope

- Main-system changes:
  - `src/react_agent/fixed_dag_external_adapter.py`
  - `src/react_agent/fixed_dag_contracts.py`
  - `scripts/dev/run_r8_13a_e2e_smoke.py`
  - `scripts/quality/phase_artifact_integrity.py`
  - focused unit tests.
- Production service changes:
  - `market_composite` wrapper/test files only.
- Artifact root:
  - `/tmp/lma-cs1c3r-evidence-durability-20260622T121352Z`
- Portable owner patches:
  - `/tmp/lma-cs1c3r-evidence-durability-20260622T121352Z/portable_owner_patches`

## C3X Integrity Correction

C3X `sha256sum -c` is reproducibly inconsistent for
`cs1c3x_validation.txt` only:

- manifest hash:
  `e6082a04da3b67b2b6e54b55cbb2c5ae4c0c09325dbd972c6db6a5d04ae3c326`
- archived actual hash:
  `6e61f8c95dcdd3fb45a8fd44ea074080f76171ad4c527d107ab888458996d4c7`

The correction is not to mutate C3X artifacts. CS1-C3R adds a reusable phase
artifact helper that finalizes primary artifacts and validation first, then
writes a relative-path `sha256sums.txt`, then writes `sha256sum -c` output to a
detached verification file.

## Real Contributor Rule

L3 formal member slots can remain visible as coverage slots, but a member is a
real contributor only when it is a formal dimension member from the current
run, has complete/partial usable status, has confidence above zero, and has
bounded business material such as evidence, research points, drivers, a
summary, a stance, or a risk score.

Pending, error, zero-confidence, no-evidence, deterministic placeholder, or
failure-fallback slots:

- must have weight `0`;
- must not enter `contributing_agents`;
- must not emit `evidence_refs`;
- must not be described as a main member in public report text;
- may appear only as missing coverage or limitations.

The adapter now fails closed with bounded reasons such as
`positive_weight_pending_member`, `positive_weight_error_member`,
`positive_weight_no_evidence_member`,
`contributing_agent_not_real_contributor`, and
`evidence_ref_from_non_contributor`.

## Market Composite

Before CS1-C3R, C3X artifacts showed `sentiment_company_radar` and
`market_fund_manager_behavior` as `partial`, zero-confidence market members
with small positive weights. After the production wrapper patch and restart,
the controlled trace records:

- `sentiment_company_radar`: `weight=0`, not a contributor;
- `market_fund_manager_behavior`: `weight=0`, not a contributor;
- market contributors:
  `market_stock_technical`, `market_capital_flow_chip`,
  `market_ipo_investor_behavior`.

This changes wrapper projection semantics only. It does not modify market
fusion algorithms, model weights, scoring, features, training, or data sources.

## Trace Result

The final controlled trace used the C3X 19-agent allowlist because
`entity_relation_extractor`, `sentiment_company_radar`, and
`market_fund_manager_behavior` did not pass production source/owner gates.

- demo compute called/mapped/failed: `19/19/0`
- L4 compute-default called/mapped/failed: `2/2/0`
- temporal rejected agents: `[]`
- L3 member summaries: value `4`, market `5`, risk `4`, macro `5`
- PublicTurn validation: pass
- unsafe scan before scrub: empty

## Remaining Blockers

- `entity_relation_extractor`: dev/sandbox candidate exists, but no confirmed
  production root/listener/owner authority. Dev `8101` was not used as
  production evidence.
- `sentiment_company_radar`: dev candidate exists, but production endpoint is
  missing and bridge/service external-id authority is inconsistent. Dev `8104`
  was not used as production evidence.
- `market_fund_manager_behavior`: executable prod subagent exists under
  `market_composite`, but production port/identity/runbook authority remains
  unresolved.
- `macro_sentiment` and `macro_industry_hotspot`: remain semantic-deferred.
  Current `10018`/`10019` placeholder processes are not real production L2
  services.

## Owner Durability

CS1-C3R copies portable owner handoff patches into the artifact root instead
of only referencing absolute server paths.

Durability counts:

- `owner_patch_ready`: `9`
- `owner_patch_conflict`: `1` (`market_stock_technical`)
- `owner_authority_unresolved_no_patch`: `11`
- `semantic_deferred`: `2`
- `owner_source_matches_prod_exact`: `2`
- `owner_source_contains_equivalent_change`: `1`

`market_stock_technical` remains an owner patch conflict because current owner
files have both line-ending and context drift. No owner-dev repository was
modified.

## Non-Claims

- No `/v1/agent/invoke` was called.
- No provider was called.
- No runtime binding was changed.
- No live flag was changed.
- No model, scoring, feature, training, data-source, or fusion algorithm was
  changed.
- No owner-dev repository was modified.
- No `.env` value was inspected or changed.
- No raw endpoint response was retained.
