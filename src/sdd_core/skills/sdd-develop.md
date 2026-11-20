---
name: sdd-develop
description: Develop a request through the official Spec Kit workflow and complete its SDD Work Item.
---

After a read-only Feature match, run `sdd-core version-check --agent AGENT [FEATURE_UUID ...]` before edits. Use the full affected scope and recheck before expanding scope. Set AGENT to the current agent kind (`codex` or `claude`).
If the gate blocks, stop the requested operation and report why. Core replacement is a user action. If asked to help synchronize versions, prepare the documented `sdd-core version-sync PLAN.json` preview with known existing verification commands and concrete input paths. Present the preview and wait for explicit approval before passing its hash to `--confirm`. Check the approved scope again before continuing. Git and rollback belong to the user.

Run from the initialized target project. Check project analysis and the target scope with `sdd-core develop-check FEATURE_UUID ...`. not_started is blocked. partial is allowed only for active READY Features with verified critical dependency safety against unanalysed scope. complete does not bypass target checks. Match existing Features first. For a genuinely new Feature, use the official specification and clarification skills to confirm its scope and boundary. Follow the Greenfield Discovery Gate procedure in the installed `sdd-init` skill for the proposed scope, including requirement preservation checks if the draft is split or merged. Register a new Feature only after READY and its official spec and plan are prepared, using `sdd-core feature-register PLAN.json` and the sdd-init durable analysis contract; omit provisional Features from Work Item references. Validate the Baseline, then use `sdd-core start FEATURE_UUID ...`. Before development entry, establish the applicable Gate set as described below and pass any develop prerequisites. Only then run `sdd-core transition ID in_progress`. For resumption use the original suspended ID only after checking current artifacts and preserving unrelated changes. Use the official installed Spec Kit skills per Feature. For existing Feature artifacts use the official revision workflow and avoid invoking creation over existing files. Run clarify, plan, checklist, tasks, analyze, implement or converge where their prerequisites and intent apply. Complete convergence remediation before final validation.

Analyze changes against concrete source, contracts and spec. Traverse reverse dependencies when contracts are affected. Update the Baseline and Source Map at stage boundaries. Map Features to relevant project-relative implementation and contract file paths. Record scope changes and evidence. When scope expands, use `scope-expand ID PLAN.json` with features (additional confirmed UUIDs) and reason, then register a newly reviewed Gate set for the expanded scope before continuing. SAFE requires evidence. Investigate gaps before UNKNOWN. Resolve CONFLICT and critical UNKNOWN before completion. Preserve current files if validation fails.

Before completion, pass all required Gates and use `sdd-core complete ID PLAN.json` with actual_features, nonempty findings and real evidence entries with ref. Do not pass ad-hoc checks as a replacement for registered Gates. Complete never runs arbitrary plan checks. It validates the latest registered Gate set and current results. On repairable test/build/review failures keep in_progress, repair and rerun. On intentional pause use suspended. failed is terminal. A retry creates a new Work Item via `start FEATURE_UUID ... --related FAILED_UUID`. Report UUIDs, blockers and actual verification. Git and rollback are user actions.

## Required Gate contract

Before development or verification, select the applicable mandatory checks using the design, project rules and concrete scope. Reuse official Spec Kit review methods and the project's tests/build/static checks. You are responsible for semantic adequacy; Core checks structural correspondence and evidence.

Prepare a Gate plan with a nonempty `reason`, `basis` (local evidence file refs) and `gates`. Each Gate requires:
- `id`, `rationale`, `targets` (declared Feature UUIDs), `required` (boolean).
- `required_for`: one or more of develop, verify, complete. Earlier prerequisites remain required at later stages; completion requires every required Gate.
- `paths`: concrete inputs. Planned new files may be absent at definition time but must exist for execution.
- `evidence`: real result/report paths and `evidence_requirement`.
- `kind: command` with the existing check's argv `command`, or `kind: review` with a documented `method` and a file-backed review report.

Use `sdd-core gates ID PLAN.json` to preview. Show the rationale and any changed/removed checks, then register the reviewed set with `--confirm APPROVAL_HASH`. Never shrink the set just to make completion pass. A revision preserves prior definitions and invalidates prior results.

Run `sdd-core gate-run ID GATE_ID` for command Gates. For official reviews, preserve the real review findings in the evidence file, then use `--review REVIEW.json` with status (PASS/FAIL/UNKNOWN/NOT_RUN), reviewer and conclusion. A PASS claim without matching evidence is insufficient.

Use `stage-check ID develop|verify|complete` before advancing. FAIL, NOT_RUN, UNKNOWN or STALE blocks advancement. Changed code/artifacts/Gate definitions or missing/changed evidence requires re-evaluation and rerun. Completed history is immutable even when its results later become stale.
