---
name: sdd-develop
description: Develop a request through the official Spec Kit workflow and complete its SDD Work Item.
---

Follow the shared conversation and presentation protocol included below throughout this skill. Collect only the next missing decision; do not turn the initial request into a bulk questionnaire.

After a read-only Feature match, run `python3 .specify/sdd-core preflight develop --agent AGENT FEATURE_UUID ...` for the confirmed scope before edits. For a genuinely new candidate without a UUID, use `python3 .specify/sdd-core preflight init --agent AGENT` before discovery, then use the develop preflight once the candidate is registered. Use the full affected scope and recheck before expanding scope. Set AGENT to the current agent kind (`codex` or `claude`).
If the gate blocks, stop the requested operation and report why. Core replacement is a user action. If asked to help synchronize versions, prepare the documented `python3 .specify/sdd-core version-sync PLAN.json` preview with known existing verification commands and concrete input paths. Present the preview and wait for explicit approval before passing its hash to `--confirm`. Check the approved scope again before continuing. Git and rollback belong to the user.

Run from the initialized target project. The develop preflight checks project analysis and the target scope in the same invocation. not_started is blocked. partial is allowed only for active READY Features with verified critical dependency safety against unanalysed scope. complete does not bypass target checks. Match existing Features first. For a genuinely new Feature, use the official specification and clarification skills to confirm its scope and boundary. Follow the Greenfield Discovery Gate procedure in the installed `sdd-init` skill for the proposed scope, including requirement preservation checks if the draft is split or merged. Register a new Feature only after READY and its official spec and plan are prepared, using `python3 .specify/sdd-core feature-register PLAN.json` and the sdd-init durable analysis contract; omit provisional Features from Work Item references. Use `python3 .specify/sdd-core start FEATURE_UUID ...` after preflight; start rechecks the Baseline and eligibility before recording a Work Item. Before development entry, establish the applicable Gate set as described below and pass any develop prerequisites. Only then run `python3 .specify/sdd-core transition ID in_progress`. For resumption use the original suspended ID only after checking current artifacts and preserving unrelated changes. Use the official installed Spec Kit skills per Feature. For existing Feature artifacts use the official revision workflow and avoid invoking creation over existing files. Run clarify, plan, checklist, tasks, analyze, implement or converge where their prerequisites and intent apply. Complete convergence remediation before final validation.

Analyze changes against concrete source, contracts and spec. Traverse reverse dependencies when contracts are affected. Update the Baseline and Source Map at stage boundaries. Map Features to relevant project-relative implementation and contract file paths. Record scope changes and evidence. When scope expands, use `scope-expand ID PLAN.json` with features (additional confirmed UUIDs) and reason, then register a newly reviewed Gate set for the expanded scope before continuing. SAFE requires evidence. Investigate gaps before UNKNOWN. Resolve CONFLICT and critical UNKNOWN before completion. Preserve current files if validation fails.

Before completion, pass all required Gates and use `python3 .specify/sdd-core complete ID PLAN.json` with actual_features, nonempty findings and real evidence entries with ref. Do not pass ad-hoc checks as a replacement for registered Gates. Complete never runs arbitrary plan checks. It validates the latest registered Gate set and current results. On repairable test/build/review failures keep in_progress, repair and rerun. On intentional pause use suspended. failed is terminal. A retry creates a new Work Item via `start FEATURE_UUID ... --related FAILED_UUID`. Report UUIDs, blockers and actual verification. Git and rollback are user actions.

## Required Gate contract

Before development or verification, select the applicable mandatory checks using the design, project rules and concrete scope. Reuse official Spec Kit review methods and the project's tests/build/static checks. You are responsible for semantic adequacy; Core checks structural correspondence and evidence.

Prepare a Gate plan with a nonempty `reason`, `basis` (local evidence file refs) and `gates`. Each Gate requires:
- `id`, `rationale`, `targets` (declared Feature UUIDs), `required` (boolean).
- `required_for`: one or more of develop, verify, complete. Earlier prerequisites remain required at later stages; completion requires every required Gate.
- `paths`: concrete inputs. Planned new files may be absent at definition time but must exist for execution.
- `evidence`: real result/report paths and `evidence_requirement`.
- `kind: command` with the existing check's argv `command`, or `kind: review` with a documented `method` and a file-backed review report.

Use `python3 .specify/sdd-core gates ID PLAN.json` to preview. Show the rationale and any changed/removed checks, then register the reviewed set with `--confirm APPROVAL_HASH`. Never shrink the set just to make completion pass. A revision preserves prior definitions and invalidates prior results.

Run `python3 .specify/sdd-core gate-run ID GATE_ID` for command Gates. For official reviews, preserve the real review findings in the evidence file, then use `--review REVIEW.json` with status (PASS/FAIL/UNKNOWN/NOT_RUN), reviewer and conclusion. A PASS claim without matching evidence is insufficient.

Use `stage-check ID develop|verify|complete` before advancing. FAIL, NOT_RUN, UNKNOWN or STALE blocks advancement. Changed code/artifacts/Gate definitions or missing/changed evidence requires re-evaluation and rerun. Completed history is immutable even when its results later become stale.

## Selective revalidation

Use `python3 .specify/sdd-core gate-refresh ID [--stage develop|verify|complete]` to preview current results, unique same-content rename candidates, reused PASS and checks requiring execution. Present the preview and get approval before `--confirm HASH`. The Core reuses only current valid latest PASS, proposes approved path/argv updates for unambiguous exact matches, reruns changed command Gates, and records provenance when carrying unchanged results to the renamed revision. Ambiguous or deleted inputs require explicit investigation and a normal Gate revision. Review Gates require real review submissions; never fabricate a PASS. Scope, basis or analysis changes still require their normal review. This is an on-demand command, not a file watcher or new verification engine.

## Development continuation

An accepted, concrete proposal from sdd-init or a prior task is a development request; the user does not need to retype this skill name. Resolve the proposed Feature and requested behavior, recheck the current entry conditions, and use the installed skill through the host's supported invocation or read and follow its installed instructions if direct dispatch is unavailable. Do not claim a delegated tool ran unless it did. Within an already authorized request, announce meaningful planning/implementation/verification transitions and continue routine steps rather than asking permission for every command. Ask again for genuinely new scope, unresolved intent or mandatory approval boundaries. After completion, suggest a specific eligible next request only when grounded in project evidence; a completed item always stays closed.
