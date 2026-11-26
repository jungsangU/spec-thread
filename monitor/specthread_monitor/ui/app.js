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
  tool_started: "작업 시작 관측",
  turn_interrupted: "턴 중단 관측",
  file_change: "파일 변경 관측", tool_completed: "도구 완료 관측",
  file_change_failed: "파일 변경 실패 관측", command_completed: "명령 완료 관측",
  command_failed: "명령 실패 관측", command_declined: "명령 거절 관측",
  input_requested: "사용자 입력 요청 관측",
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

const personas = [
  ["👨🏻‍💻", "short"], ["👩🏽‍💻", "long"], ["🧑🏿‍💻", "curly"], ["🤖", "robot"],
  ["🐱", "cat"], ["🦊", "fox"], ["🌱", "plant"], ["👽", "alien"],
];
const sessionColors = new Map();
const sessionPalette = ["#bda1ff", "#66d5c5", "#ffbb78", "#f58db8", "#81baff", "#e8d879", "#a8db87", "#df9ef2", "#8bdeea", "#f3958e"];
function identity(session) {
  const key = `${session.agent}:${session.session}`;
  let hash = 2166136261;
  for (const char of key) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619) >>> 0;
  hash = Math.imul(hash ^ (hash >>> 16), 0x7feb352d) >>> 0;
  hash = Math.imul(hash ^ (hash >>> 15), 0x846ca68b) >>> 0;
  hash = (hash ^ (hash >>> 16)) >>> 0;
  const [icon, appearance] = personas[(hash >>> 8) % personas.length];
  if (!sessionColors.has(key)) {
    const usage = sessionPalette.map((color) => [...sessionColors.values()].filter((value) => value === color).length);
    const least = Math.min(...usage);
    const offset = hash % sessionPalette.length;
    const index = sessionPalette.findIndex((_, index) => usage[(index + offset) % usage.length] === least);
    sessionColors.set(key, sessionPalette[(index + offset) % sessionPalette.length]);
  }
  return { key, icon, appearance, color: sessionColors.get(key) };
}
function tint(element, session) {
  const who = identity(session);
  element.style.setProperty("--session-color", who.color);
  element.classList.add("session-linked");
  return element;
}
const customTopics = new Map();
let topicScope = "";
function resolvedSession(session) {
  return lastSnapshot?.activity.sessions.find((item) => item.agent === session.agent && item.session === session.session) || session;
}
function sessionTopic(original, automatic = false) {
  const session = resolvedSession(original);
  const key = `${topicScope}:${session.agent}:${session.session}`;
  if (!automatic) {
    if (!customTopics.has(key)) {
      try { customTopics.set(key, localStorage.getItem(`specthread-topic:${key}`) || ""); }
      catch { customTopics.set(key, ""); }
    }
    if (customTopics.get(key)) return customTopics.get(key);
  }
  const context = session.context || {};
  if (context.features?.length) return context.features.join(" · ");
  const activity = context.activity || session.activity;
  if (activity?.gate) return `${activity.gate} 검증`;
  if (activity?.path) {
    const actions = { editing: "수정", reading: "검토", verification: "테스트", build: "빌드" };
    return `${activity.path.split("/").at(-1)} ${actions[activity.kind] || "작업"}`;
  }
  const directory = context.directory || session.directory;
  return directory && directory !== "." ? `${directory.split("/").at(-1)} 작업` : "작업 주제 미확인";
}
function renameTopic(session) {
  const button = node("button", "주제 이름 설정", "rename-topic");
  button.type = "button";
  button.addEventListener("click", () => {
    const value = window.prompt("어떤 주제로 작업하는 세션인가요? 비우면 자동 이름으로 돌아갑니다.", sessionTopic(session));
    if (value === null) return;
    const name = value.trim().slice(0, 80);
    const key = `${topicScope}:${session.agent}:${session.session}`;
    customTopics.set(key, name);
    try {
      if (name) localStorage.setItem(`specthread-topic:${key}`, name);
      else localStorage.removeItem(`specthread-topic:${key}`);
    } catch { /* Display names still work for this page when storage is disabled. */ }
    button.blur();
    if (lastSnapshot) render(lastSnapshot);
  });
  return button;
}
function sessionTitle(session) {
  return `${identity(session).icon} ${sessionTopic(session)}`;
}
function activityTitle(session) {
  const activity = session.context?.activity || session.activity;
  const ended = session.state === "ended";
  if (["permission_requested", "input_requested"].includes(session.kind)) return `${activity?.gate || "사용자 확인"} · 확인 대기 관측`;
  if (["turn_completed", "turn_failed", "turn_interrupted"].includes(session.kind)) return "응답·결과 확인";
  const titles = { verification: "테스트·검증", build: "빌드", editing: "파일 수정", reading: "파일 읽기", command: "명령 실행", review: "SDD 작업 검토" };
  if (!activity) return ended ? "세션 종료" : "작업 내용 미확인";
  const target = activity.gate || activity.path || titles[activity.kind];
  return `${target} · ${ended ? "종료 전 관측" : session.kind === "tool_started" && session.state === "working" ? "진행 관측" : "최근 관측"}`;
}
function contextLines(session, detailed = false) {
  const context = session.context || {};
  return [
    `폴더 · ${context.directory ?? session.directory ?? "미확인"}`,
    context.features?.length ? `최근 연결 · ${context.features.join(", ")}` : "연결 Feature 미확인",
    ...(detailed ? [`세션 ID · ${session.session}`, context.work ? `Work Item · ${context.work}` : "연결 Work Item 미확인"] : []),
  ];
}
let showPermissions = false;
let lastSnapshot;
byId("show-permissions").addEventListener("change", (event) => {
  showPermissions = event.target.checked;
  // Blur the filter so focused table preservation does not defer the update.
  if (lastSnapshot) render(lastSnapshot);
});

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
  if (lastSnapshot) render(lastSnapshot);
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
  progress.append(node("strong", (metrics.tasks_unavailable ? "확인분 " : "") + ratio(metrics.tasks_done, metrics.tasks_total)),
    progressBar("공식 태스크 진척률", metrics.tasks_done, metrics.tasks_total),
    node("small", metrics.tasks_total ?
      `${metrics.tasks_done} / ${metrics.tasks_total} 완료 · 프로젝트 활성 Feature ${metrics.active_features}개${metrics.tasks_unavailable ? ` · 태스크 미확인 ${metrics.tasks_unavailable}개` : ""}${metrics.feature_sampled ? " · 부분 집계" : ""}` :
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
  const gatePass = metrics.required_pass + (metrics.historical_pass || 0);
  gateCard.append(node("strong", ratio(gatePass, metrics.required_total)),
    progressBar("필수 Gate 충족률", gatePass, metrics.required_total),
    node("small", metrics.required_total ? `${gatePass} / ${metrics.required_total} · 현재 PASS ${metrics.required_pass} · 종료 이력 PASS ${metrics.historical_pass || 0}` :
      metrics.items_without_gates ? `Gate 미정의 작업 ${metrics.items_without_gates}개` : "확인할 필수 Gate 없음"));
  const workCard = metricCard("프로젝트 작업 완료율", "work-progress");
  workCard.append(node("strong", ratio(metrics.work_completed, metrics.work_total)),
    progressBar("프로젝트 작업 완료율", metrics.work_completed, metrics.work_total),
    node("small", `${metrics.work_completed} / ${metrics.work_total} 완료 · 세션 종료와 무관한 저장 기록`));
  if (metrics.gate_unknown) gateCard.append(node("small", `현재 유효성 미확인 ${metrics.gate_unknown}개`));
  byId("metrics").replaceChildren(progress, workCard, testCard, gateCard);
}

const sessionStates = { working: "작업 관측", recent: "최근 활동", quiet: "최근 활동 없음",
  ended: "종료 관측", unknown: "현재 상태 미확인" };

const workStates = [
  ["in_progress", "진행", "#b398fa"], ["pending", "대기", "#e6b96c"],
  ["completed", "완료", "#76d8b7"], ["suspended", "보류", "#7c9ae9"], ["failed", "실패 종료", "#f38d9b"],
];

function renderWorkDistribution(items, baseline, metrics) {
  const totals = new Map(workStates.map(([state]) => [state, 0]));
  for (const [state] of workStates) totals.set(state, metrics.work_counts?.[state] || 0);
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
    line(`전체 ${baseline.item_count}개 · 프로젝트 작업 완료율 ${ratio(metrics.work_completed, metrics.work_total)}`),
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
    const events = (grouped.get(`${session.agent}:${session.session}`) || []).filter((event) => showPermissions || event.kind !== "permission_requested");
    const files = new Set(events.flatMap((event) => event.paths));
    return { session, events, files: files.size };
  });
}

let artifacts = [];
let selectedArtifact;
let artifactRequest = 0;

function renderArtifacts() {
  if (selectedArtifact && !artifacts.some((row) => row.path === selectedArtifact && row.present)) {
    artifactRequest += 1; selectedArtifact = undefined;
    byId("artifact-title").textContent = "파일 내용";
    byId("artifact-path").textContent = "선택한 파일이 현재 산출물 목록에 없습니다.";
    byId("artifact-text").hidden = true; byId("artifact-text").textContent = "";
    byId("artifact-meta").replaceChildren(chip("현재 미발견", "warn"));
    byId("artifact-refresh").disabled = true;
  }
  const filter = byId("artifact-filter").value.trim().toLowerCase();
  const kind = byId("artifact-kind").value;
  const visible = artifacts.filter((artifact) => artifact.path.toLowerCase().includes(filter) && (
    !kind || kind === "changed" && artifact.changed || kind === "baseline" && artifact.path.startsWith(".specify/baseline/") || artifact.path.split("/").at(-1) === `${kind}.md`));
  byId("artifact-summary").replaceChildren(chip(`${visible.length}개 표시`), chip(`${artifacts.filter((row) => row.changed).length}개 변경`, "warn"), chip(`${artifacts.filter((row) => !row.present).length}개 미발견`));
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
byId("artifact-kind").addEventListener("change", renderArtifacts);
byId("artifact-refresh").addEventListener("click", () => { if (selectedArtifact) loadArtifact(selectedArtifact); });

async function loadArtifact(path) {
  selectedArtifact = path;
  byId("artifact-refresh").disabled = false;
  const request = ++artifactRequest;
  for (const button of byId("artifact-data").querySelectorAll("button")) {
    button.setAttribute("aria-pressed", String(button.querySelector("code").textContent === path));
  }
  const artifact = artifacts.find((row) => row.path === path);
  byId("artifact-meta").replaceChildren(...(artifact ? [chip(artifact.changed ? "변경됨" : "저장 파일", artifact.changed ? "warn" : "neutral"), ...artifact.gate_statuses.map((status) => chip(status, statusTone(status)))] : []));
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
  lastSnapshot = data;
  topicScope = data.root;
  const { baseline, git, activity, installation } = data;
  // Allocate accents once; new sessions never recolor an existing session.
  activity.sessions.slice().sort((a, b) => `${a.agent}:${a.session}`.localeCompare(`${b.agent}:${b.session}`)).forEach(identity);
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
  renderWorkDistribution(items, baseline, data.metrics);
  const sessions = sessionStats(activity);
  const working = sessions.filter(({ session }) => session.state === "working").length;
  byId("session-scope").textContent = activity.configured ?
    `작업 관측 ${working} · 관측 세션 ${sessions.length}` : "실시간 입력 미연결";
  const sessionGates = activity.session_gates || [];
  const gateKeys = new Set(sessionGates.map((row) => `${row.agent}:${row.session}`));
  byId("session-gate-panel").hidden = !sessionGates.length;
  cards("session-gate-data", sessionGates, (row) => {
    const entry = tint(node("div", undefined, "action"), row);
    entry.append(node("p", sessionTitle(row)),
      ...row.gates.map((gate) => line(gate.id + " · " + gate.status)));
    return entry;
  }, "");
  cards("session-cards", sessions.slice(0, 6), ({ session, events, files }) => {
    const card = tint(node("div", undefined, "session-card"), session);
    const head = node("strong");
    const blocked = gateKeys.has(session.agent + ":" + session.session);
    card.classList.toggle("has-gate", blocked);
    const indicator = node("span", "●", "signal");
    indicator.setAttribute("aria-hidden", "true");
    head.append(indicator, document.createTextNode(sessionTitle(session)));
    if (blocked) card.append(node("span", "사용자 확인 필요", "gate-chip"));
    card.append(head, node("p", activityTitle(session), "session-task"),
      ...contextLines(session).map(line), line(`${session.agent === "codex" ? "Codex" : "Claude Code"} · ${sessionStates[session.state]}`),
      ...((session.context?.gates || []).slice(0, 2).map((gate) => line(`다음 검증 · ${gate.id} · ${gate.status}`))),
      line(`이벤트 ${events.length} · 변경 파일 ${files}`), renameTopic(session));
    return card;
  }, activity.project_agent
    ? `다른 터미널에서 같은 프로젝트 폴더를 열고 ${activity.project_agent}를 실행하세요. 첫 이벤트가 오면 자동으로 표시됩니다.`
    : activity.configured ? "첫 활동 이벤트를 기다리는 중" : "프로젝트에 Monitor를 추가 설치하면 세션을 연결할 수 있습니다.");
  artifacts = data.artifacts;
  renderArtifacts();
  const permissionEvents = activity.sessions.filter((event) => event.state !== "ended" &&
    ["permission_requested", "input_requested", "turn_completed", "turn_failed", "turn_interrupted"].includes(event.kind));
  const projectActions = data.next_actions.map((action) => {
    const linked = activity.sessions.filter((session) => session.context?.work === action.ref ||
      session.context?.spec_paths?.some((path) => action.ref === `${path}/tasks.md`));
    return linked.length === 1 ? { ...action, session: linked[0], text: sessionTopic(linked[0]) + " · " + action.text } : action;
  });
  const actions = projectActions.concat(permissionEvents.map((event) => ({
    text: sessionTitle(event) + " · 응답·결과 확인", ref: event.session, session: event,
  })));
  cards("action-data", actions.slice(0, 3), (action) => {
    const row = node("div", undefined, "action");
    if (action.session) tint(row, action.session);
    row.append(node("p", action.text));
    return row;
  }, "표시할 다음 행동이 없습니다.");
  renderDetailPages(data, actions);
  const latest = activity.sessions.findLast((event) => !seenEvents.has(event.id)) || lastSignal || activity.events.at(-1);
  seenEvents = new Set(activity.sessions.map((event) => event.id));
  lastSignal = activity.sessions.some((event) => event.id === latest?.id) ? latest : activity.events.at(-1);
  byId("office-signal").textContent = lastSignal ? eventLabel(lastSignal) : "세션 이벤트 대기";
  office.update(activity.sessions, sessionGates);
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
  byId("diff-title").textContent = `${title} · ${path} · 조회 ${new Date().toLocaleTimeString()}`;
  byId("patch").textContent = "읽는 중";
  try {
    const query = new URLSearchParams({ path, staged: staged ? "1" : "0" });
    const { patch } = await api(`/api/diff?${query}`);
    if (request === diffRequest && byId("patch")) renderDiffLines(patch || "표시할 텍스트 diff가 없습니다.");
  } catch (error) {
    if (request === diffRequest && byId("patch")) byId("patch").textContent = error.message;
  }
}

function createOffice() {
  const canvas = byId("office");
  const ctx = canvas.getContext("2d");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  let seats = [];
  let signals = new Map();
  let pulses = new Map();
  let gateSignals = new Map();
  let gatePulses = new Map();
  const seatKey = (session) => `${session.agent}:${session.session}`;
  let frame;

  function rect(x, y, w, h, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x, y, w, h);
  }

  function character(x, y, { appearance, color }, walking = false) {
    if (["cat", "fox"].includes(appearance)) {
      const fur = appearance === "fox" ? "#e89e63" : "#c5b8ed";
      rect(x + 2, y + 1, 4, 7, fur); rect(x + 13, y + 1, 4, 7, fur);
      rect(x + 2, y + 6, 15, 13, fur); rect(x + 5, y + 14, 9, 5, "#fff0d5");
      rect(x + 5, y + 10, 2, 3, "#252136"); rect(x + 12, y + 10, 2, 3, "#252136");
      rect(x + 8, y + 15, 3, 2, "#654154");
    } else if (appearance === "robot") {
      rect(x + 9, y, 2, 4, color); rect(x + 8, y, 4, 2, "#f7dd94");
      rect(x + 1, y + 5, 17, 14, "#b4c5d5"); rect(x + 4, y + 8, 11, 6, "#25354e");
      rect(x + 5, y + 10, 3, 2, color); rect(x + 11, y + 10, 3, 2, color);
      rect(x + 6, y + 16, 7, 1, "#57667e");
    } else if (appearance === "plant") {
      rect(x + 8, y + 3, 3, 12, "#6dbb92");
      rect(x + 2, y + 2, 7, 5, "#a1d899"); rect(x + 11, y, 7, 5, "#6fbfa3");
      rect(x + 3, y + 12, 14, 9, "#d99679");
      rect(x + 6, y + 15, 2, 2, "#403142"); rect(x + 12, y + 15, 2, 2, "#403142");
    } else if (appearance === "alien") {
      rect(x + 4, y + 2, 12, 15, "#90d3b3"); rect(x + 1, y + 6, 18, 7, "#90d3b3");
      rect(x + 4, y + 8, 4, 5, "#22263d"); rect(x + 12, y + 8, 4, 5, "#22263d");
      rect(x + 8, y + 15, 4, 1, "#416d6a");
    } else {
      const skin = appearance === "curly" ? "#91634f" : appearance === "long" ? "#c48b67" : "#efbf99";
      const hair = appearance === "long" ? "#6e3d46" : "#302c40";
      rect(x + 2, y + 2, 16, appearance === "long" ? 22 : 14, hair);
      rect(x + 4, y + 7, 12, 13, skin);
      rect(x + 4, y + 4, 12, 5, hair);
      if (appearance === "curly") { rect(x, y + 2, 20, 5, hair); rect(x + 3, y, 14, 3, hair); }
      rect(x + 6, y + 11, 2, 2, "#24203a"); rect(x + 12, y + 11, 2, 2, "#24203a");
      if (appearance === "short") { rect(x + 5, y + 10, 5, 4, "#596484"); rect(x + 11, y + 10, 5, 4, "#596484"); }
    }
    if (appearance !== "plant") {
      rect(x + 3, y + 20, 14, 6, color);
      if (walking) {
        rect(x + 1, y + 21, 18, 6, color);
        rect(x + 4, y + 25, 12, 2, "#34283e");
      }
    }
  }

  const sessionDesks = [-10, 85].flatMap((y) => [36, 114, 192, 270].map((x) => ({ x, y })));
  const managers = [
    { id: "reader-seat", label: byId("office-reader"), color: "#63bfaf", appearance: "curly", offset: 0 },
    { id: "ceo-seat", label: byId("office-ceo"), color: "#e9ae6d", appearance: "short", offset: 0.53 },
  ];
  const route = [[9, 77], [367, 77], [367, 173], [9, 173], [9, 77]];
  const routeLength = 2 * (367 - 9 + 173 - 77);
  let lastFrame = -Infinity;

  function manager(role, now, moving) {
    const occupied = byId(role.id).getAttribute("aria-pressed") === "true";
    role.label.hidden = !occupied;
    if (!occupied) return false;
    const distance = ((moving ? now / 48 : 0) + role.offset * routeLength) % routeLength;
    let remaining = distance;
    let x = route[0][0];
    let y = route[0][1];
    let facing = 1;
    for (let index = 1; index < route.length; index++) {
      const [fromX, fromY] = route[index - 1];
      const [toX, toY] = route[index];
      const length = Math.abs(toX - fromX) + Math.abs(toY - fromY);
      const progress = Math.min(1, remaining / length);
      facing = toX < fromX ? -1 : 1;
      x = Math.round(fromX + (toX - fromX) * progress);
      y = Math.round(fromY + (toY - fromY) * progress);
      if (remaining <= length) break;
      remaining -= length;
    }
    const stride = moving ? Math.sin(now / 125) : 0;
    const lift = Math.round(Math.abs(stride));
    rect(x + 2, y + 31, 16, 2, "#28263a");
    rect(x + 4, y + 26, 5, 5 - Math.max(0, Math.round(stride * 3)), "#4b3c54");
    rect(x + 11, y + 26, 5, 5 - Math.max(0, -Math.round(stride * 3)), "#4b3c54");
    ctx.save();
    ctx.translate(facing < 0 ? x + 20 : x, y - lift);
    ctx.scale(facing, 1);
    character(0, 0, role, true);
    ctx.restore();
    role.label.style.left = `${(x + 10) / canvas.width * 100}%`;
    role.label.style.top = `${(y - lift + 23) / canvas.height * 100}%`;
    return moving;
  }

  function canAnimate() {
    return !reduced.matches && !document.hidden && !byId("overview").hidden &&
      !document.body.classList.contains("focus-mode");
  }

  function draw(now = 0) {
    const moving = canAnimate();
    rect(0, 0, 420, 225, "#211e31");
    for (const y of [16, 112]) {
      rect(10, y, 332, 76, "#302940");
      rect(10, y, 332, 2, "#64536f");
      for (const x of [31, 109, 187, 265]) {
        rect(x, y + 5, 48, 20, "#514364");
        rect(x + 2, y + 7, 44, 16, "#17233c");
        for (let n = 0; n < 4; n++) {
          rect(x + 5 + n * 10, y + 15, 6, 8, "#303d61");
          rect(x + 7 + n * 10, y + 17, 2, 1, n % 2 ? "#ac9ad0" : "#dfa67d");
        }
      }
    }
    rect(12, 94, 390, 16, "#433550");
    rect(12, 190, 390, 16, "#433550");
    rect(355, 71, 46, 135, "#433550");
    rect(6, 91, 22, 115, "#433550");
    for (let x = 18; x < 400; x += 18) {
      rect(x, 105, 12, 1, "#6a5373");
      rect(x, 201, 12, 1, "#6a5373");
    }
    rect(376, 26, 18, 24, "#6b4a55");
    rect(373, 23, 24, 8, "#6fa786");
    for (const [index, { x, y }] of sessionDesks.entries()) {
      ctx.save();
      ctx.translate(0, y);
      const colors = ["#829aff", "#6bc8b3", "#b78ef4", "#e290ad", "#d2ac83"];
      rect(x + 23, 66, 20, 15, "#16192f");
      rect(x + 25, 68, 16, 9, seats[index] ? identity(seats[index]).color : colors[index % colors.length]);
      rect(x + 27, 70, 8, 1, "#f8e8ff");
      rect(x + 29, 82, 6, 5, "#17172c");
      const session = seats[index];
      if (session) {
        const key = seatKey(session);
        const active = now < (pulses.get(key) || 0);
        const alerting = now < (gatePulses.get(key) || 0);
        const bounce = alerting ? Math.floor(now / 90) % 2 * 5 : active ? Math.floor(now / 100) % 2 * 3 : 0;
        character(x, 61 - bounce, identity(session));
        if (gateSignals.has(key)) {
          const color = alerting && Math.floor(now / 135) % 2 ? "#ff9da9" : "#ffd078";
          rect(x + 10, 53 - bounce, 8, 9, "#583451");
          rect(x + 13, 54 - bounce, 2, 4, color);
          rect(x + 13, 59 - bounce, 2, 2, color);
        } else if (active) {
          rect(x + 10, 59 - bounce, 6, 2, "#ffe1ac");
          rect(x + 12, 57 - bounce, 2, 6, "#ffe1ac");
        }
      }
      rect(x - 3, 87, 42, 5, "#d38c67");
      rect(x, 92, 37, 5, "#844f51");
      rect(x + 2, 97, 4, 14, "#613748");
      rect(x + 34, 97, 4, 14, "#613748");
      ctx.restore();
    }
    const patrolling = managers.map((role) => manager(role, now, moving)).some(Boolean);
    if (moving && (patrolling || [...pulses.values(), ...gatePulses.values()].some((end) => now < end))) {
      lastFrame = now;
      frame = requestAnimationFrame(animateFrame);
    }
  }

  function animateFrame(now) {
    if (!canAnimate()) return;
    if (now - lastFrame >= 45) draw(now);
    else frame = requestAnimationFrame(animateFrame);
  }

  return {
    update(sessions, gates) {
      const nextGates = new Map(gates.map((entry) => [seatKey(entry), JSON.stringify(entry.gates)]));
      const present = sessions.filter((session) => session.state !== "ended" &&
        (session.state !== "quiet" || nextGates.has(seatKey(session))));
      const flagged = present.filter((session) => nextGates.has(seatKey(session))).slice(-sessionDesks.length);
      const others = present.filter((session) => !nextGates.has(seatKey(session)));
      const extra = sessionDesks.length - flagged.length;
      const visible = [...(extra ? others.slice(-extra) : []), ...flagged];
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
      const bubbles = seats.map((session, index) => {
        if (!session) return null;
        const bubble = tint(node("div", undefined, "speech-bubble"), session);
        bubble.style.left = `${(sessionDesks[index].x + 12) / canvas.width * 100}%`;
        bubble.style.top = `${(sessionDesks[index].y + 25) / canvas.height * 100}%`;
        const text = activityTitle(session);
        bubble.append(node("strong", sessionTopic(session)), node("span", text));
        bubble.title = [sessionTitle(session), text, ...contextLines(session)].join("\n");
        return bubble;
      }).filter(Boolean);
      byId("office-bubbles").replaceChildren(...bubbles);
      const now = performance.now();
      const animate = canAnimate();
      const nextPulses = new Map();
      for (const session of visible) {
        const key = seatKey(session);
        const end = animate && session.id !== signals.get(key) ? now + 1050 : pulses.get(key);
        if (end > now) nextPulses.set(key, end);
      }
      pulses = nextPulses;
      const nextGatePulses = new Map();
      for (const [key, signature] of nextGates) {
        const end = animate && signature !== gateSignals.get(key) ? now + 1500 : gatePulses.get(key);
        if (end > now) nextGatePulses.set(key, end);
      }
      gatePulses = nextGatePulses;
      gateSignals = nextGates;
      signals = new Map(visible.map((session) => [seatKey(session), session.id]));
      cancelAnimationFrame(frame);
      draw(now);
    },
    redraw() { cancelAnimationFrame(frame); draw(performance.now()); },
    pause() {
      pulses.clear();
      gatePulses.clear();
      cancelAnimationFrame(frame);
      draw(performance.now());
    },
  };
}

const office = createOffice();
office.pause();
for (const role of ["reader", "ceo"]) {
  const seat = byId(`${role}-seat`);
  let enabled = false;
  let queue = Promise.resolve();
  function update(requested, clicked = false) {
    queue = queue.then(async () => {
      if (!clicked && !enabled) return;
      try {
        const response = await fetch(`/api/${role}`, {
          method: "POST", headers: { "X-Monitor-Token": token }, body: JSON.stringify(requested),
          signal: AbortSignal.timeout(3000),
        });
        const state = await response.json();
        if (!response.ok) throw new Error(state.error);
        enabled = state.enabled;
        if (clicked) {
          const name = role === "ceo" ? "CEO" : "Reader";
          byId("reader-status").textContent = enabled ? `${name} 켜짐 · 에이전트 실행 승인` : `${name} 꺼짐`;
        }
      } catch (error) {
        enabled = false;
        byId("reader-status").textContent = error.message;
      }
      if (seat.getAttribute("aria-pressed") !== String(enabled)) {
        seat.setAttribute("aria-pressed", String(enabled));
        office.redraw();
      }
    });
  }
  seat.addEventListener("click", async () => {
    seat.disabled = true;
    update(!enabled, true);
    await queue;
    seat.disabled = false;
  });
  setInterval(() => { if (enabled) update(true); }, 3000);
}
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
