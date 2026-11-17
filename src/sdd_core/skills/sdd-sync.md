---
name: sdd-sync
description: Review external changes and reconcile an SDD Baseline after explicit approval.
---

After read-only impact assessment, run `sdd-core version-check --agent AGENT [FEATURE_UUID ...]` before proposing edits. Include every affected Feature. Run it again before applying the approved scope. Set AGENT to the current agent kind (`codex` or `claude`).
If the gate blocks, stop the requested operation and report why. Core replacement is a user action. If asked to help synchronize versions, prepare the documented `sdd-core version-sync PLAN.json` preview with known existing verification commands and concrete input paths. Present the preview and wait for explicit approval before passing its hash to `--confirm`. Check the approved scope again before continuing. Git and rollback belong to the user.

Start with a read-only review. Ask for a comparison base if ambiguous, then compare the actual code, contracts and official Spec Kit artifacts. Resolve candidate Features using the Source Map file paths and concrete implementation evidence, and follow changed contracts to affected dependents. Preserve the authority of approved specs. Review the affected official artifacts using the applicable official skills, without writing in this phase. Describe the proposed Baseline and authorized artifact edits, evidence, and remaining findings. Ask the user for explicit approval of this exact proposal. If the underlying files change, present an updated proposal for approval.

Apply only approved edits. Keep existing code and unrelated user changes. Re-run applicable Spec Kit reviews, existing project checks and `sdd-core validate`. Surface unaddressed critical UNKNOWN and CONFLICT, and preserve the user's existing changes on failure. Report the exact approved scope applied and any failing checks. Never commit in this skill.
