---
name: sdd-develop
description: Develop a request through the official Spec Kit workflow and complete its SDD Work Item.
---

Run from the initialized target project. Verify the full initial analysis and artifact coverage. Match existing Features before adding any new UUIDs. Validate the Baseline, then use `sdd-core start [FEATURE_UUID ...]` and `sdd-core transition ID in_progress`. For resumption use the original suspended ID only after checking current artifacts and preserving unrelated changes. Use the official installed Spec Kit skills per Feature. For existing Feature artifacts use the official revision workflow and avoid invoking creation over existing files. Run clarify, plan, checklist, tasks, analyze, implement or converge where their prerequisites and intent apply. Complete convergence remediation before final validation.

Analyze changes against concrete source, contracts and spec. Traverse reverse dependencies when contracts are affected. Update the Baseline and Source Map at stage boundaries. Record scope changes and evidence. SAFE requires evidence. Investigate gaps before UNKNOWN. Resolve CONFLICT and critical UNKNOWN before completion. Preserve current files if validation fails.

Use `sdd-core complete ID PLAN.json` with an actual_features UUID array, files in paths, a findings array of objects with assessment, evidence and critical (boolean), an evidence array of objects with ref, and checks as the project's required argv arrays. Complete applicable official analysis and summarize its evidence separately before executing the Core gate. Delete temporary plan files after use. Report the Work Item and validation result. Never commit in this skill.
