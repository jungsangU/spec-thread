"use strict";

// View state only. Project facts continue to come from the read-only snapshot.
const detailViews = new Map();
const pendingSelection = new Map();
let pipelineExpanded = false;
let selectedDiffKey;

function chip(text, tone = "neutral") {
  return node("span", text, `status-chip ${tone}`);
}
function statusTone(status) {
  return ["PASS", "READY", "completed", "active", "MATCH"].includes(status) ? "good" :
    ["FAIL", "BLOCKED", "failed", "CONFLICT", "MISMATCH"].includes(status) ? "bad" :
    ["NOT_RUN", "STALE", "UNKNOWN", "CONDITIONAL", "suspended", "pending"].includes(status) ? "warn" : "neutral";
}
function sectionBlock(title, children, caption) {
  const block = node("section", undefined, "detail-block");
  block.append(node("h3", title));
  if (caption) block.append(line(caption));
  block.append(...children);
  return block;
}
function fieldGrid(fields) {
  const grid = node("dl", undefined, "field-grid");
  for (const [title, value] of fields) {
    const field = node("div");
    field.append(node("dt", title), node("dd", value ?? "미확인"));
    grid.append(field);
  }
  return grid;
}
function detailHeader(title, subtitle, badges = []) {
  const header = node("header", undefined, "detail-header");
  header.append(node("p", subtitle, "eyebrow"), node("h2", title));
  const tags = node("div", undefined, "tag-row"); tags.append(...badges); header.append(tags);
  return header;
}
function routeButton(title, page, id) {
  const button = node("button", title, "entity-link"); button.type = "button";
  button.addEventListener("click", () => {
    pendingSelection.set(page, id);
    const view = detailViews.get(page);
    if (view) { view.input.value = ""; view.filter.value = ""; }
    button.blur(); location.hash = page;
    if (lastSnapshot) render(lastSnapshot);
  });
  return button;
}
function artifactLink(path) {
  const available = lastSnapshot.artifacts.some((row) => row.path === path && row.present);
  if (!available) return line(`${path} · 현재 미발견`);
  const button = node("button", path.split("/").at(-1), "entity-link"); button.type = "button";
  button.title = path;
  button.addEventListener("click", () => {
    location.hash = "artifacts";
    byId("artifact-filter").value = ""; byId("artifact-kind").value = "";
    renderArtifacts(); loadArtifact(path);
  });
  return button;
}

function picker(page, container, rows, options, describe, inspect, empty) {
  let view = detailViews.get(page);
  if (!view) {
    const root = byId(container);
    const toolbar = node("div", undefined, "browse-toolbar");
    const input = node("input"); input.type = "search"; input.placeholder = "주제·이름·경로 검색";
    input.setAttribute("aria-label", `${pages[page]} 검색`);
    const filter = node("select"); filter.setAttribute("aria-label", `${pages[page]} 상태 필터`);
    const count = node("span", "", "muted");
    toolbar.append(input, filter, count);
    const split = node("div", undefined, "detail-explorer");
    const list = node("div", undefined, "entity-list"); list.setAttribute("aria-label", `${pages[page]} 항목 선택`);
    const pane = node("article", undefined, "entity-detail"); pane.id = `${page}-inspector`;
    split.append(list, pane); root.replaceChildren(toolbar, split);
    view = { input, filter, count, list, pane, selected: undefined, options: "" };
    detailViews.set(page, view);
    for (const control of [input, filter]) control.addEventListener(control === input ? "input" : "change", () => { view.unresolved = undefined; render(lastSnapshot); });
  }
  view.filter.hidden = options.length === 0;
  const optionKey = JSON.stringify(options);
  if (view.options !== optionKey) {
    const previous = view.filter.value;
    const all = node("option", "전체 상태"); all.value = "";
    view.filter.replaceChildren(all, ...options.map(([value, text]) => {
      const option = node("option", text); option.value = value; return option;
    }));
    view.filter.value = options.some(([value]) => value === previous) ? previous : "";
    view.options = optionKey;
  }
  const query = view.input.value.trim().toLowerCase();
  const visible = rows.filter((row) => {
    const item = describe(row);
    return (!view.filter.value || item.status === view.filter.value || item.categories?.includes(view.filter.value)) &&
      (!query || [item.title, item.subtitle, item.search].join(" ").toLowerCase().includes(query));
  });
  if (pendingSelection.has(page)) {
    view.selected = pendingSelection.get(page); pendingSelection.delete(page);
    view.unresolved = view.selected && !rows.some((row) => describe(row).id === view.selected) ? view.selected : undefined;
  }
  if (view.unresolved && visible.some((row) => describe(row).id === view.unresolved)) { view.selected = view.unresolved; view.unresolved = undefined; }
  if (!view.unresolved && !visible.some((row) => describe(row).id === view.selected)) view.selected = visible.length ? describe(visible[0]).id : undefined;
  view.count.textContent = `${visible.length} / ${rows.length}개 · 선택해 상세 보기`;
  const focused = view.list.contains(document.activeElement) ? document.activeElement.dataset.entity : null;
  const scroll = view.list.scrollTop;
  view.list.replaceChildren(...visible.map((row) => {
    const item = describe(row);
    const button = node("button", undefined, "entity-card"); button.type = "button";
    button.dataset.entity = item.id; button.setAttribute("aria-pressed", String(item.id === view.selected));
    if (item.session) tint(button, item.session);
    const head = node("div", undefined, "entity-card-heading"); head.append(node("strong", item.title), chip(item.badge || label(item.status), statusTone(item.status)));
    button.append(head, line(item.subtitle));
    if (item.progress) { button.append(progressBar(item.title, item.progress.done, item.progress.total), line(`${item.progress.done} / ${item.progress.total} 태스크 완료`)); }
    if (item.note) button.append(line(item.note));
    button.addEventListener("click", () => { view.selected = item.id; view.unresolved = undefined; button.blur(); selectedDiffKey = undefined; render(lastSnapshot); });
    return button;
  }));
  if (!visible.length) view.list.append(line(empty || "조건에 맞는 항목이 없습니다."));
  view.list.scrollTop = scroll;
  if (focused) [...view.list.children].find((row) => row.dataset.entity === focused)?.focus({ preventScroll: true });
  const selected = view.unresolved ? undefined : visible.find((row) => describe(row).id === view.selected);
  const dependencies = page === "features" ? [lastSnapshot.baseline.features, lastSnapshot.baseline.items?.map((work) => [work.id, work.status, work.declared_features, work.actual_features])] :
    page === "work-items" ? [lastSnapshot.baseline.features, lastSnapshot.activity.sessions.filter((session) => session.context?.work === view.selected).map((session) => [session.id, sessionTopic(session)])] :
    page === "pipeline" ? [lastSnapshot.metrics, lastSnapshot.installation, lastSnapshot.baseline.analysis] : [];
  const signature = JSON.stringify([view.unresolved, selected, selected ? describe(selected) : null, dependencies]);
  view.refreshed = false;
  if (view.signature !== signature) {
    const previousFocus = view.pane.contains(document.activeElement) ? document.activeElement : null;
    const focusIndex = previousFocus ? [...view.pane.querySelectorAll("button,summary,a,[tabindex]")].indexOf(previousFocus) : -1;
    if (page === "changes" && view.selected !== view.inspected) diffRequest += 1;
    const paneScroll = view.selected === view.inspected ? view.pane.scrollTop : 0;
    const open = new Set([...view.pane.querySelectorAll("details[open]")].map((item) => item.dataset.key));
    view.pane.replaceChildren(...(selected ? inspect(selected) : [node("h2", view.unresolved ? "이 참조는 현재 표시 범위에 없습니다." : "표시할 항목이 없습니다."), line(view.unresolved ? "목록 읽기 한도 밖의 이력이거나 현재 기록에서 찾을 수 없는 참조입니다. 다른 항목으로 대체하지 않습니다." : empty || "검색어나 상태 필터를 바꿔 보세요."), ...(view.unresolved ? [node("code", view.unresolved)] : [])]));
    for (const details of view.pane.querySelectorAll("details")) if (open.has(details.dataset.key)) details.open = true;
    const nextFocus = [...view.pane.querySelectorAll("button,summary,a,[tabindex]")][focusIndex];
    if (nextFocus && nextFocus.tagName === previousFocus.tagName && nextFocus.textContent === previousFocus.textContent) nextFocus.focus({ preventScroll: true });
    view.pane.scrollTop = paneScroll; view.inspected = view.selected; view.signature = signature; view.refreshed = true;
  }
  return selected;
}

function renderSessionDetails(data) {
  const rows = sessionStats(data.activity);
  picker("sessions", "session-data", rows,
    [["working", "작업 관측"], ["recent", "최근 활동"], ["quiet", "최근 활동 없음"], ["ended", "종료"], ["unknown", "현재 상태 미확인"]],
    ({ session, events, files }) => ({ id: identity(session).key, title: sessionTitle(session), status: session.state,
      badge: sessionStates[session.state], subtitle: activityTitle(session), session,
      search: [...contextLines(session, true), ...events.flatMap((event) => event.paths)].join(" "), note: `${session.context?.directory || session.directory || "폴더 미확인"} · 변경 파일 ${files}개` }),
    ({ session, events, files }) => {
      const linked = session.context || {};
      const timeline = node("ol", undefined, "activity-timeline");
      for (const event of events.slice().reverse()) {
        const entry = node("li");
        entry.append(node("strong", names[event.kind] || event.kind), line(event.observed_at ? new Date(event.observed_at * 1000).toLocaleTimeString() : "관측 시각 미확인"));
        if (event.activity?.gate) entry.append(line(`검증 · ${event.activity.gate}`));
        for (const path of event.paths) entry.append(node("code", path));
        timeline.append(entry);
      }
      if (!events.length) timeline.append(node("li", "표시할 작업 이벤트가 없습니다. 권한 이벤트는 기본으로 숨깁니다."));
      const gates = (linked.gates || []).map((gate) => {
        const card = tint(node("div", undefined, "gate-tile"), session);
        card.append(node("strong", gate.id), chip(gate.status, statusTone(gate.status))); return card;
      });
      return [detailHeader(sessionTitle(session), "선택한 세션의 작업과 최근 관측", [chip(sessionStates[session.state]), chip(session.agent === "codex" ? "Codex" : "Claude Code")]),
        renameTopic(session), fieldGrid([["현재 관측", activityTitle(session)], ["작업 폴더", linked.directory || session.directory], ["연결 Feature", linked.features?.join(" · ") || "미확인"], ["변경 파일", `${files}개`]]),
        sectionBlock("연결 작업과 검증", [...(linked.work ? [routeButton("연결된 Work Item 보기 →", "work-items", linked.work)] : [line("명시적으로 연결된 Work Item이 없습니다.")]), ...gates]),
        sectionBlock("최근 활동", [timeline], `${events.length}개 관측 · 최신순`),
        details("원본 식별 정보", `identity:${identity(session).key}`, contextLines(session, true).map(line))];
    }, data.activity.configured ? "연결된 세션이 없거나 검색 결과가 없습니다." : "프로젝트에 Monitor Hook을 연결하면 작업 세션이 표시됩니다.");
}

function renderFeatureDetails(data) {
  const features = data.baseline.features || [], works = data.baseline.items || [];
  const names = new Map(features.map((row) => [row.id, row.name]));
  picker("features", "feature-data", features, [["active", "활성"], ["retired", "폐기·아카이브"]],
    (feature) => ({ id: feature.id, title: feature.name, status: feature.status, badge: feature.status === "active" ? "활성" : "아카이브",
      subtitle: `Discovery ${feature.discovery || "미확인"}`, search: `${feature.spec_path} ${feature.id}`, progress: feature.tasks }),
    (feature) => {
      const connected = works.filter((work) => [...work.declared_features, ...work.actual_features].includes(feature.id));
      const dependencies = feature.dependencies.map((edge) => routeButton(`${names.get(edge.feature_id) || "연결 Feature"} · ${edge.type}`, "features", edge.feature_id));
      const dependents = features.filter((row) => row.dependencies.some((edge) => edge.feature_id === feature.id));
      const taskBlock = node("div", undefined, "feature-progress");
      taskBlock.append(node("strong", feature.tasks ? ratio(feature.tasks.done, feature.tasks.total) : "미확인"), progressBar(feature.name, feature.tasks?.done || 0, feature.tasks?.total || 0), line(feature.tasks ? `${feature.tasks.done}개 완료 / ${feature.tasks.total}개 태스크` : "공식 tasks.md를 아직 확인할 수 없습니다."));
      return [detailHeader(feature.name, "Feature 범위·공식 태스크·연결 작업", [chip(feature.status === "active" ? "활성" : "아카이브", statusTone(feature.status)), chip(`Discovery ${feature.discovery || "미확인"}`, statusTone(feature.discovery))]),
        taskBlock,
        sectionBlock("이 기능이 의존하는 기능", dependencies.length ? dependencies : [line("기록된 의존 관계가 없습니다.")]),
        sectionBlock("이 기능을 사용하는 기능", dependents.length ? dependents.map((row) => routeButton(row.name, "features", row.id)) : [line("기록된 역방향 의존 관계가 없습니다.")]),
        sectionBlock("관련 작업", connected.length ? connected.map((work) => routeButton(`${label(work.status)} · ${workTitle(work, data)}`, "work-items", work.id)) : [line("표시 범위에 연결된 Work Item이 없습니다.")]),
        sectionBlock("명세·계획·태스크 열기", ["spec.md", "plan.md", "tasks.md"].map((name) => artifactLink(`${feature.spec_path}/${name}`))),
        details("경로와 원본 ID", feature.id, [line(feature.spec_path), node("code", feature.id)])];
    }, "등록된 Feature가 없거나 필터에 맞는 항목이 없습니다.");
}
function workTitle(work, data) {
  const linked = data.activity.sessions.find((session) => session.context?.work === work.id);
  if (linked) return sessionTopic(linked);
  const ids = work.actual_features.length ? work.actual_features : work.declared_features;
  return ids.map((id) => data.baseline.features.find((feature) => feature.id === id)?.name).filter(Boolean).join(" · ") || "범위 이름 미확인 작업";
}
function renderWorkDetails(data) {
  const works = data.baseline.items || [];
  picker("work-items", "work-data", works, workStates.map(([value, text]) => [value, text]),
    (work) => ({ id: work.id, title: workTitle(work, data), status: work.status,
      subtitle: `${work.gates.filter((gate) => gate.required).length}개 필수 Gate · ${work.gates.filter((gate) => gate.current === "PASS").length}개 현재 PASS`, search: `${work.id} ${work.gates.map((gate) => gate.id).join(" ")}` }),
    (work) => {
      const linked = data.activity.sessions.filter((session) => session.context?.work === work.id);
      const names = (ids) => ids.map((id) => data.baseline.features.find((feature) => feature.id === id)?.name || id).join(" · ") || "없음";
      const gateCards = work.gates.map((gate) => {
        const block = node("section", undefined, "gate-tile");
        if (linked.length === 1) tint(block, linked[0]);
        const result = gate.historical ? gate.recorded : gate.current;
        const heading = node("div", undefined, "entity-card-heading"); heading.append(node("h3", gate.id), chip(result || "미확인", statusTone(result)));
        block.append(heading, ...(gate.rationale ? [line(gate.rationale)] : []), line(`${gate.required ? "필수" : "선택"} · ${gate.historical ? "종료 당시 기록" : "현재 증거 유효성"}`),
          ...(gate.definition_sources?.length ? [line(`정의 출처 · ${gate.definition_sources.join(" · ")}`)] : []),
          ...(gate.reused_from ? [line("동일 Work Item의 유효 결과 재사용 기록")] : []),
          ...(Number.isFinite(gate.duration_seconds) ? [line(`실제 실행 ${gate.duration_seconds.toFixed(3)}초`)] : []),
          fieldGrid([["검증 방식", gate.kind === "command" ? "기존 검사 명령" : gate.kind === "review" ? gate.method || "검토 기록" : "미확인"], ["적용 단계", gate.stages.join(" → ") || "—"], ["실행 횟수", `${gate.runs}회`], ["저장 결과", gate.recorded]]),
          details(`검증 증거 ${gate.evidence.length}개`, `${work.id}:${gate.id}`, gate.evidence.length ? gate.evidence.map((ref) => {
            const path = ref.split("#")[0]; return data.artifacts.some((artifact) => artifact.path === path && artifact.present) ? artifactLink(path) : node("code", ref);
          }) : [line("기록된 증거 참조 없음")])); return block;
      });
      return [detailHeader(workTitle(work, data), "Work Item · 검증을 확인한 뒤 다음 단계를 판단하세요", [chip(label(work.status), statusTone(work.status))]),
        ...linked.map((session) => tint(routeButton(sessionTitle(session), "sessions", identity(session).key), session)),
        ...(work.verification ? [sectionBlock("검증 프로파일", [chip(work.verification.profile), line(work.verification.reason),
          fieldGrid([["분류·확장 이력", `${work.verification.revisions}회`], ["진행 권한", work.verification.approval_mode === "explicit_user" ? "구체적 승인 기록" : "최초 요청 범위"]]),
          ...(work.verification.required_steps || []).map((step) => line(`${step} · ${work.verification.steps?.[step] || "미완료"}`))])] : []),
        fieldGrid([["요청 범위", names(work.declared_features)], ["실제 영향 범위", names(work.actual_features)]]),
        ...(work.gate_issue ? [node("p", work.gate_issue, "notice")] : []),
        sectionBlock("검증 Gate", gateCards.length ? gateCards : [line("등록된 Gate 집합이 없습니다. 검사 실행과 등록은 기존 Core 흐름에서 수행합니다.")]),
        sectionBlock("이전·관련 작업", work.related_work_items?.length ? work.related_work_items.map((id) => routeButton("이전 작업 상세 →", "work-items", id)) : [line("참조한 이전 작업이 없습니다.")]),
        details("원본 Work Item ID", work.id, [node("code", work.id)])];
    }, "표시할 Work Item이 없습니다.");
}

function gitCategory(change) { return ["DD", "AU", "UD", "UA", "DU", "AA", "UU"].includes(change.status) ? "conflict" : change.status === "??" ? "untracked" : change.status[1] !== " " ? "working" : "staged"; }
function renderGitDetails(data) {
  const rows = data.git?.files || [];
  const selected = picker("changes", "change-data", rows, [["working", "작업 트리 변경"], ["staged", "스테이징 변경"], ["untracked", "새 파일"], ["conflict", "충돌"]],
    (change) => ({ id: change.path, title: change.path.split("/").at(-1), status: gitCategory(change), badge: { working: "수정", staged: "스테이징", untracked: "새 파일", conflict: "충돌" }[gitCategory(change)], subtitle: change.path, search: change.status, categories: [gitCategory(change), ...(!["untracked", "conflict"].includes(gitCategory(change)) && change.status[0] !== " " ? ["staged"] : [])] }),
    (change) => {
      const preview = node("div"); preview.id = "diff-display";
      preview.append(node("h3", "변경 내용"));
      const title = node("p", "", "muted"); title.id = "diff-title";
      const patch = node("pre"); patch.id = "patch"; patch.tabIndex = 0; patch.setAttribute("aria-label", "선택한 파일의 Git diff"); preview.append(title, patch);
      const tabs = node("div", undefined, "tag-row");
      for (const staged of [false, true]) if (change.status !== "??" && gitCategory(change) !== "conflict" && change.status[staged ? 0 : 1] !== " ") {
        const button = node("button", staged ? "스테이징 diff" : "작업 트리 diff", "diff-tab"); button.type = "button";
        button.setAttribute("aria-pressed", String(staged === (selectedDiffKey?.startsWith(change.path + ":") ? selectedDiffKey.endsWith(":true") : change.status[1] === " ")));
        button.addEventListener("click", () => { selectedDiffKey = `${change.path}:${staged}`;
          for (const tab of tabs.querySelectorAll(".diff-tab")) tab.setAttribute("aria-pressed", String(tab === button));
          loadDiff(change.path, staged, button.textContent); }); tabs.append(button);
      }
      if (gitCategory(change) === "untracked") patch.textContent = "아직 Git이 추적하지 않는 새 파일입니다. 이 화면에서 파일을 추가하거나 수정하지 않습니다.";
      if (gitCategory(change) === "conflict") patch.textContent = "Git 충돌이 기록되어 있습니다. 사용자 Git 도구에서 충돌 내용을 확인하세요.";
      const refresh = node("button", "diff 새로고침", "entity-link"); refresh.type = "button";
      refresh.disabled = ["untracked", "conflict"].includes(gitCategory(change));
      refresh.addEventListener("click", () => loadDiff(change.path, selectedDiffKey?.startsWith(change.path + ":") ? selectedDiffKey.endsWith(":true") : change.status[1] === " ", "선택한 파일 diff"));
      tabs.append(refresh);
      return [detailHeader(change.path.split("/").at(-1), change.path, [chip(change.status)]),
        line(`관측 브랜치 · ${data.git.branch || "미확인"}`), line("diff는 파일 선택·탭 전환·새로고침 시 읽습니다."), tabs, preview];
    }, data.git ? "현재 변경된 파일이 없습니다." : "Git 상태를 읽을 수 없습니다.");
  if (selected && detailViews.get("changes").refreshed && !["untracked", "conflict"].includes(gitCategory(selected))) {
    let staged = selectedDiffKey?.startsWith(selected.path + ":") ? selectedDiffKey.endsWith(":true") : selected.status[1] === " ";
    if (staged && selected.status[0] === " ") staged = false;
    if (!staged && selected.status[1] === " ") staged = true;
    selectedDiffKey = `${selected.path}:${staged}`;
    for (const tab of byId("changes-inspector").querySelectorAll(".diff-tab")) tab.setAttribute("aria-pressed", String(tab.textContent === (staged ? "스테이징 diff" : "작업 트리 diff")));
    loadDiff(selected.path, staged, staged ? "스테이징 diff" : "작업 트리 diff");
  }
}
function renderDiffLines(patch) {
  const lines = patch.split("\n");
  const highlighted = lines.slice(0, 2000).map((text) => node("span", text || " ", text.startsWith("+") ? "diff-add" : text.startsWith("-") ? "diff-remove" : text.startsWith("@@") ? "diff-hunk" : "diff-line"));
  // Keep all response text while bounding syntax-highlighting DOM size.
  if (lines.length > 2000) highlighted.push(node("span", lines.slice(2000).join("\n"), "diff-line"));
  byId("patch").replaceChildren(...highlighted);
}

function renderPipelineDetails(data, actions) {
  const baseline = data.baseline, metrics = data.metrics, installation = data.installation;
  const stages = [
    { id: "analysis", title: "프로젝트 분석", note: label(baseline.analysis), content: () => [fieldGrid([["분석 상태", label(baseline.analysis)], ["활성 Feature", `${metrics.active_features}개`]]), line("Discovery와 초기 분석 판정은 기존 Core 기록을 따릅니다."), routeButton("Feature 경계와 Discovery 보기 →", "features")] },
    { id: "specs", title: "명세와 태스크", note: `${metrics.tasks_done}/${metrics.tasks_total} 태스크`, content: () => [fieldGrid([["태스크 완료", `${metrics.tasks_done} / ${metrics.tasks_total}`], ["태스크 미확인 Feature", `${metrics.tasks_unavailable || 0}개`]]), routeButton("공식 산출물 보기 →", "artifacts"), routeButton("Feature별 진척 보기 →", "features")] },
    { id: "work", title: "개발 작업", note: `${metrics.work_completed}/${metrics.work_total} 완료`, content: () => [fieldGrid(workStates.map(([state, title]) => [title, `${metrics.work_counts?.[state] || 0}개`])), routeButton("Work Item과 영향 범위 보기 →", "work-items")] },
    { id: "verification", title: "검증과 증거", note: `현재 PASS ${metrics.required_pass}`, content: () => [fieldGrid([["필수 Gate 전체", `${metrics.required_total}개`], ["현재 유효 PASS", `${metrics.required_pass}개`], ["종료 당시 PASS", `${metrics.historical_pass || 0}개`], ["현재 유효성 미확인", `${metrics.gate_unknown || 0}개`]]), routeButton("검증 Gate와 증거 보기 →", "work-items"), line("이력 PASS는 현재 파일을 재검증한 결과와 구분합니다.")] },
    { id: "installation", title: "설치와 품질", note: installation?.record_integrity || "미확인", content: () => [fieldGrid([["Core 버전", installation?.core_version], ["Skill·runner 해시", installation?.record_integrity], ["품질 제한", installation?.quality_available ? installation.global_blocked ? "전역 차단" : installation.restricted_features.join(" · ") || "없음" : "미확인"]]), line("설치 변경과 검증 실행은 Monitor에서 수행하지 않습니다.")] },
  ];
  picker("pipeline", "pipeline-data", stages, [], (stage) => ({ id: stage.id, title: stage.title, subtitle: stage.note, status: "stage", badge: "근거 보기" }),
    (stage) => [detailHeader(stage.title, "프로젝트 기록에 근거한 단계별 현황"), ...stage.content()], "확인할 단계가 없습니다.");
  const target = byId("pipeline-actions");
  if (target.contains(document.activeElement)) return;
  const visible = pipelineExpanded ? actions : actions.slice(0, 4);
  target.replaceChildren(...visible.map((action) => {
    const card = node("div", undefined, "action-card"); if (action.session) tint(card, action.session);
    card.append(node("strong", action.text));
    const work = data.baseline.items?.find((row) => row.id === action.ref);
    if (work) card.append(routeButton("해당 작업 확인 →", "work-items", work.id));
    else if (action.session) card.append(routeButton("세션 상세 →", "sessions", identity(action.session).key));
    else card.append(line(action.ref));
    return card;
  }));
  if (!actions.length) target.append(line("기록에서 확인된 다음 검토 항목이 없습니다."));
  if (actions.length > 4) {
    const button = node("button", pipelineExpanded ? "접기" : `검토 항목 ${actions.length}개 모두 보기`, "entity-link");
    button.addEventListener("click", () => { pipelineExpanded = !pipelineExpanded; button.blur(); render(lastSnapshot); }); target.append(button);
  }
}
function renderDetailPages(data, actions) {
  const page = location.hash.slice(1);
  if (page === "sessions") renderSessionDetails(data);
  if (page === "features") renderFeatureDetails(data);
  if (page === "work-items") renderWorkDetails(data);
  if (page === "changes") renderGitDetails(data);
  if (page === "pipeline") renderPipelineDetails(data, actions);
}
