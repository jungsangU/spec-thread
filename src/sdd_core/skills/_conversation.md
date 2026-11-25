## Shared SpecThread conversation and presentation protocol

This section is included in each installed sdd-init, sdd-develop and sdd-sync Skill for both supported agents. It controls the current agent's conversation, not a new scheduler, automatic session transition, or background process. Do not alter official Spec Kit formats, mandatory Gates, approval rules, UUID/history semantics, or user-owned Git operations.

### Ask progressively

- Read existing artifacts and earlier answers first. Ask ONE material question per message and wait for its answer. Do not bundle project purpose, actors, workflow, features, constraints and technology into a multi-part form.
- Prefer a short question with two or three helpful choices when appropriate; accept normal text and "not sure". Use a native single-question selection UI if available, otherwise use a compact plain-text choice. Never pretend plain text is a clickable button.
- A question is needed only when its answer affects scope, behavior, a critical uncertainty or a required decision. Skip already answered or documented points. Let users provide a full brief voluntarily and extract all usable answers from it.
- Treat "not sure" as uncertainty, never as evidence or approval. Investigate independently where possible; defer nonessential questions with explicit impact and keep critical UNKNOWN/CONFLICT blocked.
- Keep meaningful facts, unresolved questions and decisions in existing project.md/decisions.md or the affected official artifact. Preserve the provenance of observed behavior versus approved intent. Do not add a questionnaire DB or save another authoritative workflow status.

### Make transitions easy

- At meaningful boundaries show the current step, one concrete result, and the proposed next action in the user's language. Identify the actual skill/step, affected Feature/request and scope; keep shell commands, JSON and hashes out of ordinary prompts.
- A suggested handoff must be grounded in current project records and Gate checks. Never offer blocked development as ready; explain the specific blocker and ask the single next question needed to resolve it.
- Offer one unambiguous next step, e.g. "다음은 ‘할 일 등록’ 기능 개발(sdd-develop)입니다. 이 범위로 진행할까요?" Wait for a reply before beginning a new request.
- A short "진행해", "계속" or equivalent approves only the ONE concrete pending proposal. Multiple pending choices, stale context, expanded scope or changed inputs require clarification or a fresh proposal. Silence is not approval.
- After agreement, invoke the native target skill if supported; otherwise read and follow its installed SKILL.md within the same agent and scope. Do not require the user to type the command again when the host can continue. If the host cannot execute the next step, say so and give one prefilled next command/request with context, not a long checklist. Never report an unexecuted invocation as success.
- Within a request already authorized through implementation and verification, continue normal internal steps and repair/retest loops with concise progress, without repeatedly asking "continue?" for every command. Within sdd-develop, ordinary Lightweight/Standard classification, policy-based Gate composition, unchanged check reruns, selective Baseline updates and valid completion use the original request authorization. Strict/important uncertainty, scope expansion and mandatory-policy weakening require the concrete user decision; reconcile/retirement/version approvals remain explicit. A preview hash binds input, never creates consent.
- "나중에", "보류" or "그만" stops the offered handoff; preserve the current files and notes. Use suspended only when the existing Work Item transition actually permits it. Never manufacture a new state or reopen failed/completed history.
- On resume, read the existing artifacts, identify the last actual result and unresolved decision, and recheck the affected Gates before proposing a continuation. The old chat proposal is not a reusable approval token. Git actions remain user-owned and never an automatic next stage.

### Routine commands and host permissions

- Use the agent's project file tools for inspection when available. Run the Core preflight once for its scope; a successful result already includes the phase's checks. Recheck after material input or scope changes and at the documented Gate boundaries.
- Within the user's accepted scope, run routine file reads, local edits and authorized verification directly through standard project tools. Do not add a separate conversation confirmation, custom shell wrapper or an elevated execution request for ordinary steps. Avoid combining unrelated commands in a shell call.
- If the host requires permission, use its normal approval prompt for the actual operation. Explain the concrete blocker if denied and preserve it. Read-only inspection cannot replace evidence that requires execution. Keep explicit approval for Gate definitions and refresh plans, scope expansion, retirement, Sync and version synchronization. Do not broaden permissions or reinterpret a host authorization as approval of an SDD decision.

### Present a calm, consistent interface

Use the user's language. Keep the same information order in Codex and Claude Code, while respecting each host's display and question capabilities. Do not change the user's global theme, output style, terminal settings, agent configuration or unrelated conversations.

Use a short stage label, a brief substantive result/explanation, and ONE question or next choice. Prefer whitespace and modest emphasis. Avoid giant tables, ASCII boxes, repeated banners, decorative emoji, made-up percentages, fake buttons, and full command/log dumps. Use semantic status words only for actual observed results. Do not show a fixed "3/5" progress count when the discovery path is not known yet. Provide detailed findings, errors and artifact links when useful; brevity must not hide risks or required approval content.

Example, first unknown input:

**프로젝트 분석 · 목적 확인**
누구의 어떤 불편을 해결하려는 프로젝트인가요?
예: 개인 일정 정리 / 팀의 요청 관리 / 직접 설명

Example, an eligible handoff:

**기능 정리 완료**
‘할 일 등록’의 범위와 개발 준비를 확인했습니다.
다음은 **기능 개발 · sdd-develop**입니다. 이 기능부터 진행할까요?

These are presentation examples, not evidence of a real project's readiness. Use the correct host-native spelling when showing an invocation: Codex `$sdd-develop`, Claude Code `/sdd-develop`. Rendered appearance depends on the host; these instructions do not create a custom GUI or guarantee identical model responses.
