---
name: sdd-develop
description: Develop a request with risk-proportionate Spec Kit steps and valid evidence, then complete its SDD Work Item.
---

Follow the shared conversation protocol below. Reuse existing facts and ask only the next material question. The initial request authorizes ordinary implementation, verification, repair and completion within its concrete scope; do not ask permission at every step. Git/rollback remain user actions.

## Match and preflight

Run from the initialized target project. Match existing Features from actual specs/source/relationships. Before edits run `python3 .specify/sdd-core preflight develop --agent AGENT FEATURE_UUID ...`, using the current agent (codex or claude) and full affected scope. not_started blocks development; partial requires an active READY target and verified critical dependency safety against unanalysed areas. complete never bypasses target checks. A blocker stops that operation; continue independent verified work only.

For a genuinely new Feature, first use preflight init, official specify/clarify and the installed sdd-init Discovery contract. Preserve requirements/acceptance scenarios/exceptions during splits/merges. Prepare its official spec/plan and register only after READY with feature-register PLAN.json; persist current analysis. Keep existing UUIDs and use no permanent ID for provisional candidates. Never create over an existing valid spec/plan; use the official revision flow and the correct active Feature path. New Feature tests/reviews must come from its actual plan, not invented success checks.

If versions block entry, Core replacement is a user action. For requested synchronization prepare version-sync PLAN.json with actual input files and existing quality commands, obtain explicit approval of the exact preview, then --confirm HASH. Recheck readiness afterward. Never silently update Core or auto commit.

Create pending work with `start FEATURE_UUID ...`. A failed retry is a NEW Work Item with --related FAILED_UUID. Resume only the same suspended ID after checking current scope/artifacts/profile/Gates; preserve unrelated edits. completed/failed never reopen.

## Bound the work before expanding

Use features/source-map/verification/current work records to locate the target. Analysis scope L1=target requirement/artifacts/code/tests; L2=direct dependencies/contracts; L3=propagating indirect impact; L4=whole project. Start L1 and expand on actual contract/consumer/global-constraint uncertainty, not profile name or file count. Inspect headings/search/related sections first: spec acceptance/common constraints, relevant plan/tasks/predecessors, affected contracts/data/research and project/architecture/decisions policies. Stop when target requirements, applicable constraints, direct effects and a justified unchanged boundary are known, with no important uncertainty/conflict. Do not omit common exceptions or required official scope.

Within this Work Item reuse supported facts, findings, contracts and test methods from current context/existing records. Revisit only judgments affected by changed requirements/contracts/implementation/dependencies/environment, uncertainty or resume validity checks. After context loss reconstruct from existing Work Item/Baseline/evidence; add no cache, intermediate analysis report or context DB. Fact reuse is not PASS reuse.

## Risk profile and reusable policy

Read `.specify/baseline/verification.yaml` once for applicable project/Feature rules. It stores definitions, not PASS. If unconfigured, discover real methods through the sdd-init verification contract; unknown methods do not mean no verification. Never duplicate test/CI configuration or reanalyze unchanged project scope.

Submit `profile ID PROFILE.json`: reason, basis (real local evidence refs), nonempty findings and EVERY boolean risk key:
`breaking_api`, `migration`, `auth`, `security`, `transactions`, `architecture`, `broad_dependencies`, `new_feature`, `contract_changed`, `cross_feature`, `schema_change`.
The first seven imply Strict minimum; the next four imply Standard; otherwise Lightweight is a candidate. Classify actual contracts, dependencies and uncertainty, not patch/file count. Core validates the floor and monotonic history; it does not perform semantic source analysis. Set uncertain=true for important unresolved judgment. CONFLICT and critical UNKNOWN remain blocked, not solved by a higher profile or approval. SAFE also needs concrete evidence.

conditions may contain spec_changed/clarify/discovery booleans; additional_steps adds obligations. Strict requires considerations for checklist/analyze/converge, each {required:boolean, reason:concrete explanation}. Project mandatory checks apply regardless of profile. True risks and existing required steps cannot be removed in this Work Item.

Use --apply for clear Lightweight/Standard classification within scope. Strict first classification/escalation/new high-risk facts or important uncertainty requires showing the exact risk/scope/verification preview, waiting for actual user consent, then --confirm HASH. Never fabricate consent or treat computing a hash as approval. Host execution permissions still apply.

### Office CEO delegation

For `verification-policy`, `profile`, `gates` and `gate-refresh` only, ask Core for the exact read-only preview first. If concrete approval is required, run `python3 .specify/sdd-core office-approval`. When it reports `ceo_gate_approval: true`, announce the specific approval and submit the same preview hash with `--ceo-confirm HASH` instead of asking again. Core checks the active project delegation and recomputes the hash. If the delegation expires, use the documented user approval flow; if the plan changed, re-preview it. Reader does not delegate Core approvals. Scope expansion, retirement, reconciliation and version synchronization still use their normal approval paths. Keep mandatory policy, evidence and stage checks. Never report a failed Gate as passed.

## Select and perform official steps

- All profiles need plan review/reuse, scoped tasks and implementation. Lightweight reuses an adequate plan and updates only change-related tasks; new checklist/analyze/converge are excluded by default, not prohibited. Standard performs formal tasks and changes other artifacts when needed. Strict reviews plan and explicitly evaluates the three optional reviews, adding those required by risk/policy.
- New Feature requires Discovery/specify; changed contract or spec needs the official specification revision. Clarify resolves real ambiguity. Invoke each installed official Skill in the correct Feature context and respect its own prerequisite/write/hook/approval contract. Existing checklist gates still apply to implement: never delete files or auto-check markers to avoid them.
- Analyze is a read-only cross-artifact review after complete tasks. Converge assesses implementation after tasks and implement; append its remediation tasks and implement them before completion. Their purposes/results are never interchangeable. Do not rerun equivalent official analysis without changed inputs or missing findings.
- Record performed/reused official steps with `procedure ID STEP STEP.json`: status=done|reused, conclusion and actual evidence refs. Reuse existing artifacts for concise evidence; no separate essay per step. For checklist/analyze/converge also supply concrete paths. Their recorded-result reuse requires source={work_item,step,index}, SAME step and identical current inputs/evidence. If an external report lacks this metadata, inspect its actual findings and record the necessary current assessment; assume no unsupported result-sharing API. Optional elapsed_seconds must be measured, never estimated as fact.
- Traverse related/reverse dependencies when contracts are affected; stop only at a verified unchanged boundary. Use local/related/transitive depth appropriate to risk. Investigate before UNKNOWN; resolve critical UNKNOWN/CONFLICT before advancing. Record scope and findings as facts change.
- Scope expansion uses `scope-expand ID PLAN.json` with features/reason. Preview, obtain actual approval, apply with --confirm, then reassess profile and compose Gates for the expanded scope. Ordinary repair within approved scope does not need another approval.

## Choose sufficient tests and consistency checks

Test levels are independent of analysis depth and risk: L1 in-process/unit/component/TestClient; L2 real dependency integration (DB/Redis); L3 live app server; L4 system/user E2E. Choose the minimum sufficient combination, not an obligatory ladder. Live networking, TLS/streaming, startup/shutdown, multi-worker/process/deployment behavior or mandatory project policy can require L3/L4 even for Lightweight; Strict does not imply L4. Record why live execution is needed in existing rationale/findings. Reuse repeatable project scripts, avoid needless restarts, handle port/timeout/cleanup, stop only owned processes and never use production resources without authorization. Dependency startup is not app-server startup.

Reuse existing tests; add coverage for new behavior and regression tests for fixes (reproduce first when feasible), API error/boundary/compatibility or affected data behavior. Refactors favor existing regression checks; copy/docs-only edits default to no new functional test. Keep the framework/layout/strength, follow mandatory project TDD but do not impose universal TDD. Do not substitute curl/manual probes for feasible automated checks; record a concrete reason and real alternative when tests are impractical. Do not reassess whole-project coverage for every local change.

Choose needed consistency relations: request↔spec, spec↔plan/code/test, plan↔code, tasks↔code, contract↔code, changed Baseline↔code. Cover affected unchanged requirements, consumers, compatibility and invariants as well as edited lines. Diff is a locator, not the impact boundary; distinguish user edits from this request. Expand on shared interfaces/global architecture/widespread dependencies, discovered mismatch, unreliable scope, mandatory policy or a user full-review request. Never rewrite approved intent to fit code.

Analyze/Converge are optional by default for ordinary bug fixes/contract-preserving refactors; assess local extensions, new Features and multiple requirement/design changes; actively assess cross-Feature contracts/architecture. Mandatory policy and the requested whole-review purpose override these defaults. When selected, execute the actual installed official Skill over its full required scope, reuse its valid result instead of repeating equivalent semantic review, and never mark a required official step done using only a delta review. No official fork/edit, preset override or extra extension command.

## Gate execution and selective evidence

Before develop/verify entry, compose project + target Feature + extra Work Item Gates with `gates ID PLAN.json --compose`. PLAN has reason/basis and gates (empty allowed only when existing policy covers the scope). Without --compose a full explicit set is allowed, but mandatory policy definitions still cannot be omitted/changed. Use --apply for normal composition/additions. Changed/removed existing required checks need concrete approval before --confirm; consent cannot override current mandatory policy or completion invariants.

Each resulting Gate needs id/rationale/targets/required/required_for/paths/evidence/evidence_requirement and kind=command with argv, or kind=review with method. required_for is develop/verify/complete; earlier prerequisites remain required later and completion requires every mandatory Gate. Inputs may be planned at definition time but must exist for execution; review reports must be real when PASS is submitted. Optional purpose names an explicit shared objective; official_step identifies an actual official review and adds its procedure obligation.

Use `gate-run ID GATE_ID` for real command execution. A current valid latest PASS in THIS Work Item is reused; --force explicitly reruns. Different IDs share one result only for equal purpose/official step/target/input/method/evidence. Never copy another Work Item PASS. Registry evidence $execution asks Core to capture the actual log at its managed evidence path; otherwise reuse existing project reports. Core records command/exit/output/time/fingerprints; you supply requirement coverage, impact and semantic sufficiency.

For review Gates preserve the actual official findings, then --review REVIEW.json with status PASS/FAIL/UNKNOWN/NOT_RUN, reviewer and conclusion. Never fabricate PASS; command results cannot be replaced by external reviews. Use stage-check develop/verify/complete before advancing. FAIL/NOT_RUN/UNKNOWN/STALE blocks the applicable stage. Changed/deleted inputs or evidence require re-evaluation, not a new assertion of success.

Use gate-refresh ID [--stage ...] --apply for unchanged-path selective verification: valid latest PASS stays, only failed/stale/missing checks run. Actual rename/ambiguous candidates require the concrete preview and user approval before --confirm. Review Gates still need actual review submissions. Unchanged valid definitions may carry results with provenance when adding a Gate; changed definitions require current verification. No watchers or separate verification engine.

## Management and completion

Reuse First, No Change No Write, Minimal Edit, Single Source of Truth, No Extra Report. Preserve document structure/requirement IDs and edit only affected sections/references. Spec changes only for new/changed intent; plan for changed design; tasks for current work; research/data/contracts/quickstart for their actual changes; checklists/Discovery only under existing conditions. Official required writes still apply. Use existing Work Item/findings/evidence/artifacts rather than separate completion/test/impact/coverage/change summaries or a duplicate plan, unless official/project/user requirements ask for one.

Update only changed management facts: source additions/moves/deletions in Source Map, Feature/contract relationships, actual architecture facts and verification methods. Keep state/scope/lifecycle changes current immediately; leave unrelated Baseline files untouched. Run final structural/reference validation. Never adjust approved intent automatically to match code.

Before complete, satisfy required procedures, current mandatory PASS, actual evidence, authorized scope, request coverage and nonblocking findings. `complete ID PLAN.json` takes actual_features, nonempty findings and evidence entries with ref; it does not run arbitrary plan checks or require rerunning a valid result merely because completion is next. Keep repairable failures in_progress and fix/retest; intentional pause uses suspended; failed is terminal. Preserve files on failure and report actual outcomes/remaining limits. After completion, propose another eligible request only from current project evidence, without adding Git operations.
