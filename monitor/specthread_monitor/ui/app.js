"use strict";

const byId = (id) => document.getElementById(id);
const fragment = new URLSearchParams(location.hash.slice(1));
const storageKey = "specthread-monitor-token";
const token = fragment.get("token") || sessionStorage.getItem(storageKey);
if (fragment.has("token")) {
  sessionStorage.setItem(storageKey, token);
  history.replaceState(null, "", location.pathname);
}
const names = {
  session_started: "세션 시작 관측", session_ended: "세션 종료 관측",
  turn_started: "턴 시작 관측", turn_completed: "턴 완료 관측", turn_failed: "턴 실패 관측",
  turn_interrupted: "턴 중단 관측",
  file_change: "파일 변경 관측", tool_completed: "도구 완료 관측",
  file_change_failed: "파일 변경 실패 관측", command_completed: "명령 완료 관측",
  command_failed: "명령 실패 관측", command_declined: "명령 거절 관측",
  permission_requested: "권한 요청 관측",
};
const states = {
  available: "읽기 가능", missing: "Baseline 없음", unavailable: "읽기 오류",
  unsupported: "미지원 스키마", pending: "대기", in_progress: "진행 기록",
  suspended: "보류", completed: "완료", failed: "실패 종료",
  not_started: "미시작", partial: "부분 분석", complete: "분석 완료",
};
const label = (value) => Object.hasOwn(states, value) ? states[value] : (value || "미확인");
const eventLabel = (event) => `${event.agent === "codex" ? "Codex" : "Claude Code"} · ${names[event.kind]}`;

function node(tag, text, className) {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (className) result.className = className;
  return result;
}

function line(text) {
  return node("p", text, "muted");
}

function cards(id, rows, create, empty) {
  const target = byId(id);
  const focused = target.contains(document.activeElement);
  if (focused) return;
  const open = new Set([...target.querySelectorAll("details[open]")].map((element) => element.dataset.key));
  const rendered = rows.map(create);
  for (const card of rendered) if (open.has(card.dataset.key)) card.open = true;
  target.replaceChildren(...(rendered.length ? rendered : [line(empty)]));
}

function recordsTable(id, headers, rows, empty) {
  const target = byId(id);
  if (target.contains(document.activeElement)) return;
  if (!rows.length) {
    target.replaceChildren(line(empty));
    return;
  }
  const open = new Set([...target.querySelectorAll("details[open]")].map((element) => element.dataset.key));
  const table = node("table", undefined, "records");
  const heading = table.createTHead().insertRow();
  for (const header of headers) {
    const column = node("th", header);
    column.scope = "col";
    heading.append(column);
  }
  const body = table.createTBody();
  for (const columns of rows) {
    const row = body.insertRow();
    for (const value of columns) {
      const cell = row.insertCell();
      if (typeof value === "string") cell.textContent = value;
      else {
        if (open.has(value.dataset.key)) value.open = true;
        cell.append(value);
      }
    }
  }
  target.replaceChildren(table);
}

function details(title, key, children) {
  const panel = node("details", undefined, "row");
  panel.dataset.key = key;
  panel.append(node("summary", title), ...children);
  return panel;
}

let seenEvents = new Set();
let lastSignal;

const pages = {
  overview: "프로젝트 대시보드", sessions: "세션 활동", features: "Feature",
  "work-items": "Work Item · Gate", artifacts: "산출물 탐색", changes: "Git 변경",
  pipeline: "SDD Pipeline",
};
function showPage() {
  const route = location.hash.slice(1);
  const current = Object.hasOwn(pages, route) ? route : "overview";
  for (const page of document.querySelectorAll("[data-page]")) page.hidden = page.id !== current;
  for (const link of document.querySelectorAll("nav a")) {
    if (link.hash === `#${current}`) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  byId("page-title").textContent = pages[current];
}
window.addEventListener("hashchange", showPage);
showPage();

function metricCard(title, tone) {
  const card = node("section", undefined, `metric ${tone}`);
  card.append(node("h2", title));
  return card;
}

function ratio(number, total) {
  return total ? `${Math.round(number * 100 / total)}%` : "—";
}

function progressBar(title, value, total) {
  if (!total) return node("div", undefined, "meter-empty");
  const bar = node("progress");
  bar.max = total;
  bar.value = value;
  bar.setAttribute("aria-label", title);
  return bar;
}

function renderMetrics(metrics) {
  const progress = metricCard("공식 태스크 진척률", "primary");
  progress.append(node("strong", ratio(metrics.tasks_done, metrics.tasks_total)),
    progressBar("공식 태스크 진척률", metrics.tasks_done, metrics.tasks_total),
    node("small", metrics.tasks_total ?
      `${metrics.tasks_done} / ${metrics.tasks_total} 완료 · 활성 Feature ${metrics.features_with_tasks}개${metrics.feature_sampled ? " · 표시 범위" : ""}` :
      "표시할 공식 태스크 없음"));

  const { tests } = metrics;
  const testCard = node("section", undefined, "metric test");
  const available = tests.state === "available";
  const executed = available ? tests.passed + tests.failed + tests.errors : 0;
  const ring = node("div", undefined, "ring");
  ring.style.setProperty("--pass", executed ? ratio(tests.passed, executed) : "0%");
  ring.style.setProperty("--end", executed ? "100%" : "0%");
  ring.append(node("strong", ratio(tests.passed, executed)));
  const testText = node("div");
  testText.append(node("h2", "테스트 통과율"), node("small", available ?
    `${tests.passed} / ${executed} 통과 · 실패 ${tests.failed + tests.errors} · 건너뜀 ${tests.skipped}` :
    tests.state === "unavailable" ? "보고서 읽기 오류" : "JUnit 보고서 없음"));
  if (available) testText.append(node("small", new Date(tests.reported_at).toLocaleString()));
  testCard.append(ring, testText);

  const gateCard = metricCard("필수 Gate 충족률", "gates");
  gateCard.append(node("strong", ratio(metrics.required_pass, metrics.required_total)),
    progressBar("필수 Gate 충족률", metrics.required_pass, metrics.required_total),
    node("small", metrics.required_total ? `${metrics.required_pass} / ${metrics.required_total} 유효 PASS` :
      metrics.items_without_gates ? `Gate 미정의 작업 ${metrics.items_without_gates}개` : "확인할 필수 Gate 없음"));
  byId("metrics").replaceChildren(progress, testCard, gateCard);
}

const workStates = [
  ["in_progress", "진행", "#b398fa"], ["pending", "대기", "#e6b96c"],
  ["completed", "완료", "#76d8b7"], ["suspended", "보류", "#7c9ae9"], ["failed", "실패 종료", "#f38d9b"],
];

function renderWorkDistribution(items, baseline) {
  const totals = new Map(workStates.map(([state]) => [state, 0]));
  for (const item of items) if (totals.has(item.status)) totals.set(item.status, totals.get(item.status) + 1);
  const target = byId("work-distribution");
  if (baseline.state !== "available") {
    target.replaceChildren(line("Work Item 기록을 읽을 수 없습니다."));
    return;
  }
  const band = node("div", undefined, "work-band");
  band.setAttribute("aria-hidden", "true");
  const grid = node("div", undefined, "state-grid");
  for (const [state, title, color] of workStates) {
    const count = totals.get(state);
    if (count) {
      const segment = node("span");
      segment.style.setProperty("--count", count);
      segment.style.setProperty("--swatch", color);
      band.append(segment);
    }
    const tile = node("div", undefined, "state-tile");
    const name = node("span");
    const dot = node("span", "●");
    dot.setAttribute("aria-hidden", "true");
    tile.style.setProperty("--swatch", color);
    name.append(dot, document.createTextNode(title));
    tile.append(name, node("strong", count));
    grid.append(tile);
  }
  target.replaceChildren(
    line(`전체 ${baseline.item_count}개 · 표시 작업 완료율 ${ratio(totals.get("completed"), items.length)}`),
    band, grid,
  );
}

function sessionStats(activity) {
  const grouped = new Map();
  for (const event of activity.events) {
    const key = `${event.agent}:${event.session}`;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(event);
  }
  return activity.sessions.slice().reverse().map((session) => {
    const events = grouped.get(`${session.agent}:${session.session}`) || [];
    const files = new Set(events.flatMap((event) => event.paths));
    return { session, events, files: files.size };
  });
}

let artifacts = [];
let selectedArtifact;
let artifactRequest = 0;

function renderArtifacts() {
  const filter = byId("artifact-filter").value.trim().toLowerCase();
  const visible = artifacts.filter((artifact) => artifact.path.toLowerCase().includes(filter));
  cards("artifact-data", visible, (artifact) => {
    const row = node("button", undefined, "artifact-button");
    row.type = "button";
    row.setAttribute("aria-pressed", String(artifact.path === selectedArtifact));
    row.append(node("code", artifact.path), node("span", [
      artifact.present ? "존재" : "없음", artifact.changed ? "변경됨" : null,
      artifact.modified ? new Date(artifact.modified).toLocaleString() : null,
      ...artifact.gate_statuses,
    ].filter(Boolean).join(" · ")));
    row.disabled = !artifact.present;
    row.addEventListener("click", () => loadArtifact(artifact.path));
    return row;
  }, "일치하는 산출물이 없습니다.");
}
byId("artifact-filter").addEventListener("input", renderArtifacts);

async function loadArtifact(path) {
  selectedArtifact = path;
  const request = ++artifactRequest;
  for (const button of byId("artifact-data").querySelectorAll("button")) {
    button.setAttribute("aria-pressed", String(button.querySelector("code").textContent === path));
  }
  byId("artifact-title").textContent = path.split("/").at(-1);
  byId("artifact-path").textContent = path;
  const output = byId("artifact-text");
  output.hidden = false;
  output.textContent = "읽는 중";
  try {
    const { text, truncated } = await api(`/api/artifact?${new URLSearchParams({ path })}`);
    if (request !== artifactRequest) return;
    output.textContent = text || "빈 파일";
    if (truncated) byId("artifact-path").textContent = `${path} · 앞 96 KiB 표시`;
  } catch (error) {
    if (request === artifactRequest) output.textContent = error.message;
  }
}

function render(data) {
  const { baseline, git, activity, installation } = data;
  const features = baseline.features || [];
  const items = baseline.items || [];
  byId("project-name").textContent = data.root;
  byId("connection").textContent = `● ${label(baseline.state)}`;
  byId("observed").textContent = [
    git?.branch, `관측 ${new Date(data.observed_at).toLocaleTimeString()}`,
    ...Object.values(data.alerts),
    ...(activity.errors.length ? ["일부 이벤트 입력 읽기 오류"] : []),
  ].filter(Boolean).join(" · ");
  renderMetrics(data.metrics);
  renderWorkDistribution(items, baseline);
  const sessions = sessionStats(activity);
  const openSessions = sessions.filter(({ session }) => session.kind !== "session_ended");
  byId("session-scope").textContent = activity.configured ?
    `종료 미관측 ${openSessions.length} · 전체 ${sessions.length}` : "실시간 입력 미연결";
  cards("session-cards", sessions.slice(0, 6), ({ session, events, files }) => {
    const card = node("div", undefined, "session-card");
    const head = node("strong");
    const indicator = node("span", "●", "signal");
    indicator.setAttribute("aria-hidden", "true");
    head.append(indicator, document.createTextNode(session.agent === "codex" ? "Codex" : "Claude Code"));
    card.append(head, line(names[session.kind]), line(`이벤트 ${events.length} · 변경 파일 ${files}`));
    return card;
  }, activity.configured ? "첫 세션 이벤트를 기다리는 중" : "세션을 함께 실행하면 이곳에 활동이 표시됩니다.");
  recordsTable("session-data", ["에이전트", "최근 활동", "변경 파일", "이벤트"], sessions.map(({ session, events, files }) => [
    session.agent === "codex" ? "Codex" : "Claude Code", names[session.kind], String(files),
    details(`${events.length}건 펼치기`, `${session.agent}:${session.session}`, [
      line(session.session), ...events.slice().reverse().map((event) => line([names[event.kind], ...event.paths].join(" · "))),
    ]),
  ]), activity.configured ? "표시할 이벤트가 없습니다." : "에이전트 이벤트 미연결");
  recordsTable("feature-data", ["Feature", "상태", "공식 태스크", "상세"], features.map((feature) => [
    feature.name, feature.status, feature.tasks ? `${feature.tasks.done}/${feature.tasks.total}` : "미확인",
    details("상세 펼치기", feature.id, [
      line(feature.id), line(feature.spec_path), line(`저장된 Discovery ${label(feature.discovery)}`),
      ...feature.dependencies.map((dependency) => line(`의존성 ${dependency.type} · ${dependency.feature_id}`)),
    ]),
  ]), "등록된 Feature를 읽을 수 없습니다.");
  recordsTable("work-data", ["상태", "Work Item", "Gate와 작업 범위"], items.map((work) => {
    const children = [
      line(`선언 Feature ${work.declared_features.join(", ") || "—"}`),
      line(`실제 Feature ${work.actual_features.join(", ") || "—"}`),
      ...((work.related_work_items || []).map((id) => line(`이전 작업 ${id}`))),
    ];
    if (work.gate_issue) children.push(line(work.gate_issue));
    for (const gate of work.gates) {
      const row = node("div", undefined, "row");
      row.append(node("p", `${gate.id} · ${gate.required ? "필수" : "선택"} · ${gate.historical ? "종료 이력" : `현재 ${gate.current}`}`, "badge"),
        line(`기록 ${gate.recorded} · 실행 ${gate.runs}회${gate.stages.length ? ` · ${gate.stages.join(" / ")}` : ""}`),
        ...gate.evidence.map((ref) => line(`증거 ${ref}`)));
      children.push(row);
    }
    return [label(work.status), node("code", work.id), details("상세 펼치기", work.id, children)];
  }), "저장된 Work Item을 읽을 수 없습니다.");
  artifacts = data.artifacts;
  renderArtifacts();
  cards("pipeline-data", [
    `Baseline 분석 · ${label(baseline.analysis)}`,
    `공식 Spec Kit · ${data.artifacts.filter((artifact) => artifact.present && artifact.path.startsWith("specs/")).length}개 발견`,
    `진행 기록 · ${baseline.state === "available" ? `${items.filter((item) => item.status === "in_progress").length}개 (표시 범위)` : "미확인"}`,
    `설치 Core · ${installation?.core_version || "미확인"}`,
    `설치 버전·Skill·runner 해시 · ${installation?.record_integrity || "미확인"}`,
    installation?.global_blocked ? "저장된 품질 검사 · 전역 차단" :
      `저장된 품질 제한 · ${installation?.quality_available ? installation.restricted_features.join(", ") || "없음" : "미확인"}`,
  ], line, "");
  const permissionEvents = activity.sessions.filter((event) => event.kind === "permission_requested");
  const actions = data.next_actions.concat(permissionEvents.map((event) => ({
    text: "에이전트의 권한 요청 확인 · 현재 대기 여부 미확인", ref: event.session,
  })));
  cards("action-data", actions.slice(0, 3), (action) => {
    const row = node("div", undefined, "action");
    row.append(node("p", action.text));
    return row;
  }, "표시할 다음 행동이 없습니다.");
  cards("pipeline-actions", actions, (action) => {
    const row = node("div", undefined, "row");
    row.append(node("p", action.text), line(action.ref));
    return row;
  }, "표시할 다음 행동이 없습니다.");
  cards("change-data", git?.files || [], (change) => {
    const row = node("div", undefined, "row");
    row.append(node("p", `${change.status.trim()} · ${change.path}`));
    if (change.status === "??" || change.status.includes("U")) return row;
    for (const staged of [true, false]) {
      if (change.status[staged ? 0 : 1] === " ") continue;
      const title = staged ? "스테이징 diff" : "작업 파일 diff";
      const button = node("button", title);
      button.type = "button";
      button.addEventListener("click", () => loadDiff(change.path, staged, title));
      row.append(button);
    }
    return row;
  }, git ? "현재 Worktree 변경이 없습니다." : "Git 변경을 읽을 수 없습니다.");
  const latest = activity.sessions.findLast((event) => !seenEvents.has(event.id)) || lastSignal || activity.events.at(-1);
  seenEvents = new Set(activity.sessions.map((event) => event.id));
  lastSignal = activity.sessions.some((event) => event.id === latest?.id) ? latest : activity.events.at(-1);
  byId("office-signal").textContent = lastSignal ? eventLabel(lastSignal) : "세션 이벤트 대기";
  office.update(activity.sessions);
}

async function api(path) {
  const response = await fetch(path, { headers: { "X-Monitor-Token": token || "" }, signal: AbortSignal.timeout(15000) });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error);
  return body;
}

let diffRequest = 0;
async function loadDiff(path, staged, title) {
  const request = ++diffRequest;
  byId("diff-display").hidden = false;
  byId("diff-title").textContent = `${title} · ${path}`;
  byId("patch").textContent = "읽는 중";
  byId("patch").focus();
  try {
    const query = new URLSearchParams({ path, staged: staged ? "1" : "0" });
    const { patch } = await api(`/api/diff?${query}`);
    if (request === diffRequest) byId("patch").textContent = patch || "표시할 텍스트 diff가 없습니다.";
  } catch (error) {
    if (request === diffRequest) byId("patch").textContent = error.message;
  }
}

function createOffice() {
  const canvas = byId("office");
  const ctx = canvas.getContext("2d");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  let seats = [];
  let signals = new Map();
  let pulses = new Map();
  const seatKey = (session) => `${session.agent}:${session.session}`;
  let frame;

  function rect(x, y, w, h, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x, y, w, h);
  }

  function draw(now = 0) {
    rect(0, 0, 360, 124, "#272138");
    rect(0, 82, 360, 42, "#503648");
    rect(0, 78, 360, 4, "#86637c");
    for (let x = 0; x < 360; x += 21) {
      rect(x, 101, 19, 1, "#755061");
      rect(x + 7, 117, 19, 1, "#755061");
    }
    for (const x of [14, 133, 252]) {
      rect(x, 8, 94, 50, "#765775");
      rect(x + 3, 11, 88, 44, "#131c39");
      rect(x + 70, 17, 7, 7, "#f2d59d");
      for (let i = 0; i < 7; i++) {
        const h = 10 + (i * 11) % 19;
        rect(x + 5 + i * 12, 54 - h, 9, h, "#2b3764");
        rect(x + 7 + i * 12, 57 - h, 3, 2, i % 2 ? "#a68ee2" : "#d3a779");
      }
      rect(x + 47, 10, 2, 47, "#765775");
      rect(x - 2, 56, 98, 4, "#9c7288");
    }
    for (const x of [5, 339]) {
      rect(x + 4, 76, 12, 13, "#c18b70");
      rect(x, 68, 7, 6, "#7bb592");
      rect(x + 11, 64, 7, 10, "#519a85");
      rect(x + 8, 68, 3, 9, "#4a8d76");
    }
    for (const [index, x] of [23, 87, 151, 215, 279].entries()) {
      const colors = ["#829aff", "#6bc8b3", "#b78ef4", "#e290ad", "#d2ac83"];
      rect(x + 23, 66, 20, 15, "#16192f");
      rect(x + 25, 68, 16, 9, colors[index]);
      rect(x + 27, 70, 8, 1, "#f8e8ff");
      rect(x + 29, 82, 6, 5, "#17172c");
      const session = seats[index];
      if (session) {
        const active = now < (pulses.get(seatKey(session)) || 0);
        const bounce = active ? Math.floor(now / 100) % 2 * 3 : 0;
        rect(x + 2, 66 - bounce, 15, 16, session.agent === "codex" ? "#8965d9" : "#b6694b");
        rect(x + 4, 72 - bounce, 11, 9, "#efb989");
        rect(x + 6, 74 - bounce, 2, 2, "#24203a");
        rect(x + 12, 74 - bounce, 2, 2, "#24203a");
        rect(x + 3, 81 - bounce, 13, 6, colors[index]);
        if (active) {
          rect(x + 10, 59 - bounce, 6, 2, "#ffe1ac");
          rect(x + 12, 57 - bounce, 2, 6, "#ffe1ac");
        }
      }
      rect(x - 3, 87, 54, 5, "#d38c67");
      rect(x, 92, 49, 5, "#844f51");
      rect(x + 2, 97, 4, 14, "#613748");
      rect(x + 42, 97, 4, 14, "#613748");
    }
    if ([...pulses.values()].some((end) => now < end) && !reduced.matches && !document.hidden) {
      frame = requestAnimationFrame(draw);
    }
  }

  return {
    update(sessions) {
      const visible = sessions.filter((session) => session.kind !== "session_ended").slice(-5);
      const byKey = new Map(visible.map((session) => [seatKey(session), session]));
      seats = seats.map((session) => session && byKey.get(seatKey(session)));
      const seated = new Set(seats.filter(Boolean).map(seatKey));
      for (const session of visible) {
        const key = seatKey(session);
        if (seated.has(key)) continue;
        const empty = seats.indexOf(undefined);
        if (empty === -1) seats.push(session);
        else seats[empty] = session;
      }
      const now = performance.now();
      const animate = !reduced.matches && !document.hidden && !byId("overview").hidden &&
        !document.body.classList.contains("focus-mode");
      const nextPulses = new Map();
      for (const session of visible) {
        const key = seatKey(session);
        const end = animate && session.id !== signals.get(key) ? now + 1050 : pulses.get(key);
        if (end > now) nextPulses.set(key, end);
      }
      pulses = nextPulses;
      signals = new Map(visible.map((session) => [seatKey(session), session.id]));
      cancelAnimationFrame(frame);
      draw(now);
    },
    pause() {
      pulses.clear();
      cancelAnimationFrame(frame);
      draw();
    },
  };
}

const office = createOffice();
office.pause();
for (const [id, focus] of [["focus-mode", true], ["living-mode", false]]) {
  byId(id).addEventListener("click", () => {
    document.body.classList.toggle("focus-mode", focus);
    byId("focus-mode").setAttribute("aria-pressed", String(focus));
    byId("living-mode").setAttribute("aria-pressed", String(!focus));
    office.pause();
  });
}

async function refresh() {
  try {
    if (!document.hidden) render(await api("/api/snapshot"));
  } catch (error) {
    byId("connection").textContent = `연결 오류 · ${error.message}`;
  } finally {
    if (token) setTimeout(refresh, 3000);
  }
}

if (token) refresh();
else byId("connection").textContent = "실행 시 표시된 링크를 열어 주세요";
