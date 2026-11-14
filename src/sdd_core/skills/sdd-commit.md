---
name: sdd-commit
description: Integrate selected completed SDD Work Items and commit only after full validation.
disable-model-invocation: true
---

Require an explicit user request to commit. Confirm the target local branch, the selected Worktree paths and completed Work Item UUIDs, and the user's confirmation that all Worktrees are safely stopped or completed. Use the existing project checks and assess cross-Feature impact of the selected combination, including dependencies on unselected work. Critical UNKNOWN or CONFLICT blocks the operation.

Use a temporary JSON plan with target (full refs/heads/ name), message, safe_worktrees (true only after user confirmation), findings (assessment/evidence/critical), checks (full project verification set as argv arrays), and sources. Each source has worktree (absolute root), work_items (selected IDs), paths (exact relative changed paths including .specify/baseline/work-items.yaml). Review the combined candidate using `sdd-core preview PLAN.json` and ensure the findings and checks cover the actual combination. Put the returned base and tree in reviewed_base and reviewed_tree. Run `sdd-core commit PLAN.json` against the target repository. Report the returned commit ID or conflict. On failure preserve originals and let the user choose the Worktree for corrective work. Do not auto retry or remove original Worktrees.
