---
name: sdd-init
description: Discover and verify the full project scope and initialize the SpecThread Baseline.
---

Follow the shared conversation and presentation protocol included below throughout this skill. Collect only the next missing decision; do not turn the initial request into a bulk questionnaire.

Before creating any artifacts, run `python3 .specify/sdd-core preflight init --agent AGENT`. Set AGENT to the current agent kind (`codex` or `claude`).
If the gate blocks, stop the requested operation and report why. Core replacement is a user action. If asked to help synchronize versions, prepare the documented `python3 .specify/sdd-core version-sync PLAN.json` preview with known existing verification commands and concrete input paths. Present the preview and wait for explicit approval before passing its hash to `--confirm`. Check the approved scope again before continuing. Git and rollback belong to the user.

Run only on explicit user request from the target project root. Verify the official Spec Kit integration, read the constitution and inspect existing official artifacts. Confirm scope or mode only if ambiguous. Use the existing Baseline from installation. Run `python3 .specify/sdd-core scaffold` only if the Baseline does not exist and the installed project passes preflight. Use the [Discovery gate procedure](#discovery-gate) below.

## Guided intake

Inspect existing project files and prior answers before asking. For Greenfield, start with the intended users and problem only when they are unknown. Then discover the main end-to-end usage flow, must-have behavior, important constraints, and Feature boundaries as needed, one question per turn. The order is adaptive: skip known answers and follow the next question whose answer affects the work. Offer two or three short examples or choices when useful and always accept free text or "not sure". Never require a complete product description, feature list and technical constraints in one answer. If the user already provided a full brief, use it rather than forcing a step-by-step interview.

Once the minimal purpose and context are sufficient, create the official initial specification BEFORE full business-workflow analysis and provisional Feature splitting. Continue the later questions through analysis and official clarify; do not wait for a complete questionnaire or invent unknown functionality to fill the initial draft.

For Brownfield, inspect current code/specifications/tests first. Explain the observed system briefly and ask only the next material ambiguity about current behavior or intent; do not ask the user to reconstruct all existing features. Preserve uncertainty and all existing Gate rules. Use the official specify/clarify flow once sufficient context exists, gathering remaining answers progressively rather than changing the official document format.

At an analysis milestone, summarize the understood scope and unresolved point concisely. Do not treat a conversational confirmation as Discovery READY. Persist actual evidence with the existing analysis contract. At the end, check the proposed active Feature with `python3 .specify/sdd-core preflight develop --agent AGENT FEATURE_UUID ...`; only if it passes propose one concrete sdd-develop handoff. Partial analysis must satisfy the same target/dependency rules.

## Discovery

- **Greenfield:** Invoke the installed official Spec Kit `specify` skill to create the initial scope specification from the user's requirements and domain context. Analyze the whole business workflow, including handoffs and exceptions, before splitting into provisional Features. Iterate on boundaries and requirements with official `clarify` on each affected draft.
- **Brownfield:** Reverse-engineer the existing system first. Use its code, contracts, configuration, tests, documentation, and available execution evidence. Reuse valid official specs, or invoke official `specify` to create initial specs from observed facts. Then use official `clarify` to resolve ambiguities about existing behavior and design intent. Keep observed behavior, approved intent, inferred intent, and gaps distinct. Add newly discovered existing Features to the analysis. Never invent new functionality or change the implementation during initial analysis.
- Before each official invocation, confirm the active Feature directory and its write scope. Use a separate draft path for creation when the target already contains a valid spec. Reuse existing answers. Use the official revision workflow for existing specs and preserve unrelated Feature context. Do not run hooks that switch branches or commit.
- Refer to provisional Features by draft name and path. On every split or merge, compare the original and resulting specs in both directions for dropped or distorted requirements, changed acceptance scenarios and exceptions, conflicting or unsupported behavior, and dependency changes. Resolve discrepancies before marking the relevant check verified. Keep original drafts available until the comparison is complete.

## Discovery Gate

For each Feature, submit a temporary JSON plan to `python3 .specify/sdd-core discovery-gate PLAN.json`. Set `mode` to `greenfield` or `brownfield`, `candidate` to the draft name or path, and `checks` to an object keyed by:

- `scope`: completeness of the analyzed scope and known exclusions.
- `boundaries`: Feature ownership and dependency consistency.
- `requirements`: preservation of requirements, scenarios, exceptions and contracts across draft changes.
- `spec_quality`: applicable official requirements quality checks.
- `workflow` (Greenfield): coverage of the complete business flow.
- `current_behavior` (Brownfield): evidence for existing behavior and the separation of observed behavior from design intent.

Each check needs `status` (`verified`, `condition`, or `blocked`) and concrete `evidence`. Unresolved checks also need a `next_step`. Set `critical: false` only for documented nonessential conditions. Treat unresolved conflicts and missing evidence for critical behavior, intent or contracts as blocked. The Core combines these inputs. You are responsible for collecting and assessing the underlying evidence.

- **READY:** Confirm the Feature boundary. Preserve an existing confirmed ID and official path. For a new Feature, prepare its official spec and plan, then use `python3 .specify/sdd-core feature-register PLAN.json` to register it only on READY. The plan contains `feature` with name/spec_path/dependencies, the same `discovery` checks, and concrete `paths` and `evidence` file arrays. Reuse the returned UUID; never issue another ID for the registered Feature. Never use the generic UUID command for provisional Features.
- **CONDITIONAL:** Record the noncritical uncertainty and next step. Continue independent analysis; re-evaluate the affected Feature before confirming it.
- **BLOCKED:** Record the blocking evidence. Stop confirmation of that scope until evidence or a user decision resolves it. Continue unrelated work when it can be verified independently.

## Existing verification methods

Inspect the project's actual test/build/static-check commands, CI/configuration, constitution and Feature acceptance requirements once. Record reusable references in `.specify/baseline/verification.yaml`; do not copy the test or CI configuration itself. Use `python3 .specify/sdd-core verification-policy POLICY.json` to preview, then --apply for initial/additive definitions that Core marks automatic. Changed/removed existing definitions or an explicitly reviewed empty shared policy need actual user approval of the preview and --confirm HASH. Do not interpret no discovered command as a passing verification setup: preserve unconfigured and explain the missing actual test or review method.

POLICY.json uses schema_version:1, status:configured, reason, basis (existing nonempty local evidence refs), project:{gates:[]} and features:{FEATURE_UUID:{gates:[]}}. Gate templates use the normal Gate fields from sdd-develop plus profiles (lightweight/standard/strict) and mandatory boolean. mandatory:true applies in ALL profiles and requires required:true. Project targets may be "$scope"; a Feature template targets "$scope" or its own UUID. Reference concrete inputs and existing commands/methods, not fabricated success checks. Optional purpose identifies an identical verification objective; official_step on review Gates names a specific official procedure and never merges analyze with converge. Use evidence:["$execution"] on command templates when Core should write the actual execution log; otherwise reference the project's existing report paths.

A confirmed new Feature may add its own definitions; leave unrelated project/Feature definitions unchanged. Retired Feature definitions remain in the registry but are excluded from current selection. Reassess project-wide path references during retirement rather than weakening a mandatory check. Historical Work Item snapshots/results are never rewritten by registry edits. Run validate after actual management changes.

## Completion and resumption

Record scope, evidence, decisions, verdicts and next steps in the existing Markdown records (`project.md`, `decisions.md` and official specs as appropriate). For confirmed Features, use official `plan` to produce missing plans and necessary design documents. Keep existing tasks and leave new tasks to development. Write confirmed Features and dependencies to the Baseline and map each implemented Feature to its relevant project-relative source and contract file paths. Use an empty mapping where there is no implementation yet. Run `python3 .specify/sdd-core validate` and verify project coverage, official artifacts and references. Persist verified analysis and per-Feature reports through `python3 .specify/sdd-core analysis-record PLAN.json` using the contract below. Only report full completion when all in-scope Features are confirmed, required documents are present, and blocking findings are resolved.

On failure or interruption, preserve valid outputs and drafts. On resume, inspect actual files, the recorded checks and existing confirmed registrations. Keep verified work and IDs. Revisit missing or changed scope and unresolved conditions; rerun split/merge checks and the Gate if their inputs changed. Ask for a decision before overwriting conflicting edits. Never commit in this skill.


## Durable analysis contract

Keep project analysis state separate from derived Feature development eligibility. A partial project may develop an active READY Feature once critical dependencies on unanalysed scope are verified safe. Never mark an unanalysed scope complete to bypass this rule. Record:
- `status`: `not_started`, `partial`, or `complete`.
- `unanalysed`: descriptions of outstanding scope, empty only when none remains.
- `paths` and `evidence`: real, stable analysis/specification input files and evidence files.
- `features`: an object keyed by confirmed UUID. Each value contains `discovery` (the submitted mode/candidate/checks plan) and a nonempty `dependencies` findings array with assessment/evidence/critical where applicable.

`analysis-record` binds each report to the project assessment and input/evidence hashes. `complete` requires all active Features to pass. A changed scope or changed assessment input requires affected reports to be reviewed again. A partial assessment must document core dependency safety, including known boundaries with unanalysed scope. `python3 .specify/sdd-core develop-check FEATURE_UUID ...` evaluates the current scope; do not store an additional development-enabled flag.

Feature and Work Item identifiers are permanent. Retire confirmed Features only with an approved `feature-retire` preview, preserving history and re-evaluating active dependencies. The Core owns Baseline metadata; official Spec Kit owns its original document content and workflow.
