# SpecThread Monitor

## 설치

기존 SpecThread 설치 명령에 `--monitor`를 붙입니다. 제품 폴더에서 실행한 뒤 설치할 프로젝트를 지정하세요. 이미 등록한 프로젝트에서도 이 옵션으로 Monitor를 추가할 수 있습니다.

```sh
python3 specthread install --monitor
```

## 실행

설치한 프로젝트 폴더에서 아래 한 줄을 실행하면 설정된 에이전트의 새 터미널 세션과 Monitor가 함께 열립니다.

```sh
./monitor
```

Codex에서는 처음에 `/hooks`로 Monitor Hook을 검토하고 신뢰해야 합니다. 에이전트 CLI 설치와 로그인은 기존 설정을 사용합니다. CLI를 찾지 못하면 대시보드만 열립니다. 대시보드만 열려면 `./monitor --dashboard-only`를 실행하고 표시된 주소를 여세요. Git 프로젝트에서는 변경 목록과 diff도 표시됩니다.

왼쪽 메뉴에서 세션·작업·산출물 상세 화면을 엽니다. 산출물 화면에서 경로를 검색하고 파일 내용을 확인할 수 있습니다. 테스트 통과율을 표시하려면 기존 테스트 도구에서 JUnit 보고서를 `test-results/junit.xml`로 저장하세요.

<details>
<summary>선택 설정 · 실시간 세션 연결</summary>

## 세션 데이터 연결

파일·Git·Baseline 관측은 에이전트 설정 없이 동작합니다. 사용자가 지원되는 CLI 실행의 JSONL을 따로 보관하는 경우 대시보드 실행 때 해당 파일을 지정할 수 있습니다. 각 파일은 해당 Worktree 전용으로 사용합니다.

```sh
# Codex CLI의 실행별 JSONL을 표시
specthread-monitor --root /path/to/worktree --codex-events /path/to/codex-exec.jsonl
# 사용자가 구성한 Claude Code Hooks JSONL 또는 stream-json 출력
specthread-monitor --root /path/to/worktree --claude-events /path/to/claude-events.jsonl
```

Codex CLI에서는 사용자 작업에 `codex exec --json`을 사용해 표준 출력을 실행 전용 파일로 보낼 수 있습니다. Claude Code Hooks는 사용자 설정에서 `SessionStart`, `PostToolUse`, `PermissionRequest`, `Stop`, `SessionEnd` 입력을 JSONL로 전달할 수 있습니다. 해당 이벤트를 사용할 수 있는지는 에이전트 환경과 설정에 따라 달라집니다. CLI의 `claude -p --verbose --output-format stream-json`은 세션 시작과 결과를 관측합니다. 원본 이벤트 파일에는 프롬프트와 출력이 포함될 수 있습니다. 원본 파일의 권한·보존은 사용자가 관리합니다.

### 대화형 Hooks 연결

[Codex Hooks](https://learn.chatgpt.com/docs/hooks)와 [Claude Code Hooks](https://code.claude.com/docs/en/hooks)의 명령형 Hook은 stdin으로 JSON 객체 한 개를 전달합니다. 이벤트 종류별로 같은 로컬 스크립트를 지정할 수 있습니다. 예시는 사용자 전용 디렉터리에 이벤트 필드만 남기며 `jq`가 필요합니다. 설치된 에이전트에서 Hook을 지원하고 신뢰 설정을 마친 경우에 사용합니다.

```sh
#!/bin/sh
umask 077
jq -c '{
  session_id, cwd, hook_event_name, tool_name,
  tool_input: {file_path: .tool_input.file_path?}
}' 2>/dev/null >> /absolute/private/path/agent-hooks.jsonl || :
```

각 에이전트·Worktree에 별도 출력 파일을 지정합니다. Codex 파일은 `--codex-events`, Claude Code 파일은 `--claude-events`로 연결합니다. 이 스크립트에는 Hook 응답이나 승인 결정이 없습니다. Codex Hook의 패치 본문을 저장하지 않으므로 Codex에서 파일 귀속이 필요하면 exec의 `file_change` 이벤트를 사용합니다.

</details>

<details>
<summary>개발 및 검증</summary>

## 검증

제품 루트에서 아래 명령을 실행합니다. UI의 HTML, CSS 및 JavaScript는 별도 번들러 없이 Monitor 패키지에 함께 배포합니다.

```sh
python -m unittest discover -s monitor/tests
node --check monitor/specthread_monitor/ui/app.js
python -m pip wheel --no-deps ./monitor
```

[설계와 제약](../docs/design/monitor.md)

</details>
