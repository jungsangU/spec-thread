---
name: sdd-mode
description: Inspect or explicitly change the project's Direct/Isolated development mode when no active work blocks it.
---

Use the initialized origin project and current agent. Run `python3 .specify/sdd-core mode` to inspect. Only an explicit user request changes the mode: `mode direct` or `mode isolated`. This never selects a mode automatically, starts an agent, creates a Git branch/worktree or grants sandbox access. Report blockers with Work Item IDs; do not mark active work failed to bypass them. Runtime path can be chosen before creating work with `mode isolated --runtime-root ABSOLUTE_EXTERNAL_DIRECTORY`; existing Runtime history cannot silently move. Enter isolated development only after the actual same-session tool/cwd/permission/Hook proof described in sdd-develop. Unsupported adapters remain blocked, without a Direct fallback.
