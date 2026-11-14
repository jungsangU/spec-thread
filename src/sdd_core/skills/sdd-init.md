---
name: sdd-init
description: Analyze an entire target project and initialize its SpecThread Baseline.
---

Run only on explicit user request. Work from the target project root. Verify the official Spec Kit integration is installed. Read the project constitution and existing Feature artifacts. Discover the whole product scope from requirements (Greenfield) or code, contracts, configuration and docs (Brownfield). Record approved intent separately from observed implementation. Add discovered Features as the analysis progresses. Ask about important unresolved boundaries or intent and continue with unrelated confirmed Features.

Run `sdd-core scaffold`. Use `sdd-core uuid` for stable new Feature IDs. Use the installed official Spec Kit skills to author each new Feature specification and plan. For an existing Feature preserve its path and ID, and follow the official artifact revision flow. Confirm the active Feature directory before each invocation. Use applicable official requirements-quality checks. Leave new tasks to development, and keep existing tasks. Analyze remaining cross-Feature references, project coverage, architecture and the Source Map. Populate all six Baseline files, with one record per Feature and Source Map entry per mapped Feature. Run `sdd-core validate`. Report completion only after whole-project review and resolution of blocking UNKNOWN and CONFLICT. Preserve usable outputs on failure. Never commit in this skill.
