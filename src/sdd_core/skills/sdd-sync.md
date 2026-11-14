---
name: sdd-sync
description: Review external changes and reconcile an SDD Baseline after explicit approval.
---

Start with a read-only review. Ask for a comparison base if ambiguous, then compare the actual code, contracts and official Spec Kit artifacts. Resolve candidate Features using the Source Map and source evidence, and follow changed contracts to affected dependents. Preserve the authority of approved specs. Review the affected official artifacts using the applicable official skills, without writing in this phase. Describe the proposed Baseline and authorized artifact edits, evidence, and remaining findings. Ask the user for explicit approval of this exact proposal. If the underlying files change, present an updated proposal for approval.

Apply only approved edits. Keep existing code and unrelated user changes. Re-run applicable Spec Kit reviews, existing project checks and `sdd-core validate`. Surface unaddressed critical UNKNOWN and CONFLICT, and preserve the user's existing changes on failure. Report the exact approved scope applied and any failing checks. Never commit in this skill.
