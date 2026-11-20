---
name: sdd-init
description: Discover and verify the full project scope and initialize the SpecThread Baseline.
---

Before creating any artifacts, run `sdd-core version-check --agent AGENT`. Set AGENT to the current agent kind (`codex` or `claude`).
If the gate blocks, stop the requested operation and report why. Core replacement is a user action. If asked to help synchronize versions, prepare the documented `sdd-core version-sync PLAN.json` preview with known existing verification commands and concrete input paths. Present the preview and wait for explicit approval before passing its hash to `--confirm`. Check the approved scope again before continuing. Git and rollback belong to the user.

Run only on explicit user request from the target project root. Verify the official Spec Kit integration, read the constitution and inspect existing official artifacts. Confirm scope or mode only if ambiguous. Run `sdd-core scaffold` to create missing Baseline files without replacing existing files. Use the [Discovery gate procedure](#discovery-gate) below.

## Discovery

- **Greenfield:** Invoke the installed official Spec Kit `specify` skill to create the initial scope specification from the user's requirements and domain context. Analyze the whole business workflow, including handoffs and exceptions, before splitting into provisional Features. Iterate on boundaries and requirements with official `clarify` on each affected draft.
- **Brownfield:** Reverse-engineer the existing system first. Use its code, contracts, configuration, tests, documentation, and available execution evidence. Reuse valid official specs, or invoke official `specify` to create initial specs from observed facts. Then use official `clarify` to resolve ambiguities about existing behavior and design intent. Keep observed behavior, approved intent, inferred intent, and gaps distinct. Add newly discovered existing Features to the analysis. Never invent new functionality or change the implementation during initial analysis.
- Before each official invocation, confirm the active Feature directory and its write scope. Use a separate draft path for creation when the target already contains a valid spec. Reuse existing answers. Use the official revision workflow for existing specs and preserve unrelated Feature context. Do not run hooks that switch branches or commit.
- Refer to provisional Features by draft name and path. On every split or merge, compare the original and resulting specs in both directions for dropped or distorted requirements, changed acceptance scenarios and exceptions, conflicting or unsupported behavior, and dependency changes. Resolve discrepancies before marking the relevant check verified. Keep original drafts available until the comparison is complete.

## Discovery Gate

For each Feature, submit a temporary JSON plan to `sdd-core discovery-gate PLAN.json`. Set `mode` to `greenfield` or `brownfield`, `candidate` to the draft name or path, and `checks` to an object keyed by:

- `scope`: completeness of the analyzed scope and known exclusions.
- `boundaries`: Feature ownership and dependency consistency.
- `requirements`: preservation of requirements, scenarios, exceptions and contracts across draft changes.
- `spec_quality`: applicable official requirements quality checks.
- `workflow` (Greenfield): coverage of the complete business flow.
- `current_behavior` (Brownfield): evidence for existing behavior and the separation of observed behavior from design intent.

Each check needs `status` (`verified`, `condition`, or `blocked`) and concrete `evidence`. Unresolved checks also need a `next_step`. Set `critical: false` only for documented nonessential conditions. Treat unresolved conflicts and missing evidence for critical behavior, intent or contracts as blocked. The Core combines these inputs. You are responsible for collecting and assessing the underlying evidence.

- **READY:** Confirm the Feature boundary. Preserve an existing confirmed ID and official path. For a new Feature, prepare its official spec and plan, then use `sdd-core feature-register PLAN.json` to register it only on READY. The plan contains `feature` with name/spec_path/dependencies, the same `discovery` checks, and concrete `paths` and `evidence` file arrays. Reuse the returned UUID; never issue another ID for the registered Feature. Never use the generic UUID command for provisional Features.
- **CONDITIONAL:** Record the noncritical uncertainty and next step. Continue independent analysis; re-evaluate the affected Feature before confirming it.
- **BLOCKED:** Record the blocking evidence. Stop confirmation of that scope until evidence or a user decision resolves it. Continue unrelated work when it can be verified independently.

## Completion and resumption

Record scope, evidence, decisions, verdicts and next steps in the existing Markdown records (`project.md`, `decisions.md` and official specs as appropriate). For confirmed Features, use official `plan` to produce missing plans and necessary design documents. Keep existing tasks and leave new tasks to development. Write confirmed Features and dependencies to the Baseline and map each implemented Feature to its relevant project-relative source and contract file paths. Use an empty mapping where there is no implementation yet. Run `sdd-core validate` and verify project coverage, official artifacts and references. Persist verified analysis and per-Feature reports through `sdd-core analysis-record PLAN.json` using the contract below. Only report full completion when all in-scope Features are confirmed, required documents are present, and blocking findings are resolved.

On failure or interruption, preserve valid outputs and drafts. On resume, inspect actual files, the recorded checks and existing confirmed registrations. Keep verified work and IDs. Revisit missing or changed scope and unresolved conditions; rerun split/merge checks and the Gate if their inputs changed. Ask for a decision before overwriting conflicting edits. Never commit in this skill.


## Durable analysis contract

Keep project analysis state separate from derived Feature development eligibility. A partial project may develop an active READY Feature once critical dependencies on unanalysed scope are verified safe. Never mark an unanalysed scope complete to bypass this rule. Record:
- `status`: `not_started`, `partial`, or `complete`.
- `unanalysed`: descriptions of outstanding scope, empty only when none remains.
- `paths` and `evidence`: real, stable analysis/specification input files and evidence files.
- `features`: an object keyed by confirmed UUID. Each value contains `discovery` (the submitted mode/candidate/checks plan) and a nonempty `dependencies` findings array with assessment/evidence/critical where applicable.

`analysis-record` binds each report to the project assessment and input/evidence hashes. `complete` requires all active Features to pass. A changed scope or changed assessment input requires affected reports to be reviewed again. A partial assessment must document core dependency safety, including known boundaries with unanalysed scope. `sdd-core develop-check FEATURE_UUID ...` evaluates the current scope; do not store an additional development-enabled flag.

Feature and Work Item identifiers are permanent. Retire confirmed Features only with an approved `feature-retire` preview, preserving history and re-evaluating active dependencies. The Core owns Baseline metadata; official Spec Kit owns its original document content and workflow.
