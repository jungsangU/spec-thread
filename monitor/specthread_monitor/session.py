"""Opt-in interactive launch and an observation-only hook receiver."""
import argparse
import base64
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event, Thread
import webbrowser

from sdd_core.version_sync import PROJECT
from .events import IDENTIFIER, hook_event, observed_gate_work, observed_activity, observed_directory
from .project_events import configured_agent, record
from .reader import reader_response

EVENTS = ("SessionStart", "UserPromptSubmit", "PostToolUse", "PermissionRequest", "PreToolUse", "Notification", "Stop", "SessionEnd", "Interrupt")
EVENT_FILE = "SPECTHREAD_MONITOR_EVENTS"
FILE_LIMIT = 1024 * 1024


def hook_groups(command):
    return {event: [{"hooks": [{"type": "command", "command": command, "timeout": 1}]}]
            for event in EVENTS if event != "Interrupt"}


def launch_arguments(executable, agent):
    if agent == "codex":
        return [executable]
    argv = [sys.executable, "-X", "utf8", "-m", "specthread_monitor.session"]
    command = shlex.join(argv)
    if os.name == "nt":
        parts = " ".join("'" + value.replace("'", "''") + "'" for value in argv)
        script = ("$OutputEncoding = [Console]::InputEncoding = [Text.UTF8Encoding]::new($false); "
                  f"[Console]::In.ReadToEnd() | & {parts}; exit $LASTEXITCODE")
        command = "powershell.exe -NoProfile -NonInteractive -EncodedCommand " + base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return [executable, "--settings", json.dumps({"hooks": hook_groups(command)})]


def record_event(root=None, agent=None):
    destination = os.environ.get(EVENT_FILE) if root is None else None
    agent = agent or os.environ.get("SPECTHREAD_MONITOR_AGENT")
    if (root is None and not destination) or agent not in ("codex", "claude"):
        return
    try:
        raw = json.loads(sys.stdin.buffer.read(1024 * 1024))
        if not isinstance(raw, dict) or raw.get("hook_event_name") not in EVENTS:
            return
        project = Path.cwd().resolve() if root is None else root.resolve()
        workroot=project
        workspace_ref=None
        cwd=Path(raw.get('cwd',''))
        if cwd.is_absolute():
            for directory in (cwd,*cwd.parents):
                if (directory/'.specify/workspace.json').is_file():
                    from sdd_core.workspaces import reference
                    workspace_ref=reference(directory)
                    origin=Path(workspace_ref['origin'])
                    if project not in (origin,directory):return
                    project=origin;workroot=directory;break
        session, kind, paths = hook_event(workroot, raw, agent)
        if not kind or not isinstance(session, str) or not IDENTIFIER.fullmatch(session):
            return
        event = {"session_id": session, "cwd": str(project), "hook_event_name": raw["hook_event_name"]}
        if workspace_ref:
            event['workspace']=workspace_ref['work_item']
        if raw["hook_event_name"] == "Notification":
            event["notification_type"] = raw.get("notification_type")
        if raw["hook_event_name"] == "PreToolUse":
            event["tool_name"] = raw.get("tool_name")
        activity = observed_activity(workroot, raw)
        directory = observed_directory(workroot, raw)
        if activity:
            event["activity"] = activity
        if directory is not None:
            event["directory"] = directory
        work = observed_gate_work(raw)
        if work is None and workspace_ref:work={'work':workspace_ref['work_item'],'phase':None}
        if work:
            event["gate_work"] = work
        if paths:
            event.update(tool_name="Edit", tool_input={"file_path": paths[0]})
        if root is not None:
            record(project, agent, event)
            decision = reader_response(workroot, raw)
            if decision:
                print(json.dumps(decision), flush=True)
            return
        path = Path(destination)
        if path.stat().st_size < FILE_LIMIT:
            with path.open("ab") as stream:
                stream.write(json.dumps(event, ensure_ascii=True).encode() + b"\n")
    except (OSError, ValueError, TypeError, RecursionError):
        pass


def wait_for_dashboard():
    """The user, rather than an agent session, owns the dashboard lifetime."""
    try:
        Event().wait()
    except KeyboardInterrupt:
        pass


def run_session(root, port, sources, *, browser=True, idle_seconds=900):
    from .server import MonitorServer, serve_dashboard

    try:
        agent = json.loads((root / PROJECT).read_text(encoding="utf-8"))["agent"]
    except (OSError, ValueError, TypeError, KeyError):
        print("프로젝트의 SpecThread 설치 기록을 읽을 수 없습니다.", file=sys.stderr)
        return 1
    executable = shutil.which(agent) if agent in ("codex", "claude") else None
    if executable is None:
        print("에이전트 CLI를 찾을 수 없어 대시보드만 엽니다.", file=sys.stderr)
        return serve_dashboard(root, sources, port, browser=browser, idle_seconds=idle_seconds)
    project_hooks = configured_agent(root) == agent
    arguments = [executable] if project_hooks else launch_arguments(executable, agent)
    with TemporaryDirectory(prefix="specthread-session-") as directory:
        event_file = Path(directory) / "events.jsonl"
        event_file.touch(mode=0o600)
        env = dict(os.environ)
        if not project_hooks:
            env.update({EVENT_FILE: str(event_file), "SPECTHREAD_MONITOR_AGENT": agent})
        try:
            server = MonitorServer(root, sources if project_hooks else [*sources, (agent, event_file)], port, idle_seconds)
        except OSError:
            print("Monitor 주소를 열지 못했습니다. 에이전트 세션은 계속 시작합니다.", file=sys.stderr)
            return subprocess.call(arguments, cwd=root, env=env)
        with server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://{server.authority}/#token={server.token}"
                print(f"SpecThread Monitor  {url}", flush=True)
                if agent == "codex":
                    print("처음에는 Codex의 /hooks에서 Monitor Hook을 검토하고 신뢰해야 세션 이벤트가 표시됩니다.", flush=True)
                if browser:
                    try:
                        webbrowser.open(url)
                    except (OSError, webbrowser.Error):
                        pass
                result = subprocess.call(arguments, cwd=root, env=env)
                print("에이전트 세션이 종료됐습니다. 프로젝트 Monitor는 계속 열려 있습니다. 종료하려면 Ctrl+C를 누르세요.", flush=True)
                wait_for_dashboard()
                return result
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path)
    parser.add_argument("--agent", choices=("codex", "claude"))
    options = parser.parse_args()
    record_event(options.root, options.agent)
