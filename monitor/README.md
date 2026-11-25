# SpecThread Monitor

## 설치

제품 폴더에서 `python3 specthread install`을 실행하면 앱 폴더, 에이전트, Monitor 설치 여부를 묻습니다. 이미 SpecThread를 설치한 프로젝트에는 Monitor만 추가할 수 있습니다.

```sh
python3 specthread install --monitor --project /path/to/project
```

pip SSL 오류 후 재시도 질문에 `y`를 고르거나 처음부터 `--ssl-trust`를 지정하세요. 해당 설치에서만 기본 PyPI 호스트의 인증서 검사를 건너뜁니다.

기존 Monitor도 내려받은 최신 배포본에서 `python3 specthread update --project /path/to/project`를 실행하면 함께 갱신됩니다. Hook 변경 후 에이전트 세션을 다시 열고 Codex에서는 변경된 Hook을 다시 검토·신뢰하세요.

## 실행

설치한 프로젝트에서 Monitor를 먼저 엽니다. Windows PowerShell에서는 `.\monitor.cmd`를 실행하세요.

```sh
./monitor
```

브라우저가 열리면 첫 터미널을 켜 둔 채, **다른 터미널에서 같은 프로젝트 폴더를 열고** 평소처럼 실행합니다.

```sh
claude
```

Claude Code용으로 설치한 프로젝트는 첫 Hook 이벤트가 들어오면 열려 있는 화면에 세션을 추가합니다. Codex 프로젝트는 `codex`를 실행하며 처음에 `/hooks`로 Monitor Hook을 검토하고 신뢰해야 합니다. 각 에이전트의 프로젝트 신뢰 및 관리 정책이 적용됩니다. 기존 세션이 새 Hook을 로드하지 못하면 새 세션에서 확인하세요.

작업 관측 표시가 유지되는 기본 시간은 15분입니다. `./monitor --session-idle-seconds 300`처럼 바꿀 수 있습니다. Hook 자체의 실행 한도는 기본 5초이며 설치 시 `--hook-timeout 10`처럼 지정합니다. Git 프로젝트에서는 변경 목록과 diff도 표시됩니다.

느낌표는 연결된 필수 Gate뿐 아니라 권한 요청·질문·계획 승인·턴 종료 후 결과 확인에도 표시됩니다. 종료 신호만 관측한 경우 실제 승인 대기로 단정하지 않습니다. 새 프롬프트나 도구 완료가 오면 사용자 확인 표시는 해제됩니다.

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

## 프로젝트 진행과 세션 구분

프로젝트 진척률은 세션이 아니라 Baseline과 공식 tasks.md에 저장된 기록에서 집계합니다. 완료 Work Item과 당시 Gate PASS도 유지하며 현재 검증 결과와 구분합니다. 세션 종료·이벤트 정리·브라우저 새로고침으로 진행 기록을 초기화하지 않습니다. `--session`으로 함께 연 에이전트가 종료돼도 Monitor는 계속 열리며 Monitor 터미널에서 Ctrl+C로 종료합니다.

캐릭터와 같은 작업 주제명·색상을 세션·연결 작업·검증·다음 행동에서 찾을 수 있습니다. Feature 이름이나 확인된 작업 내용을 앞에 표시하고 번호는 상세에만 둡니다. “주제 이름 설정”으로 직접 이름을 붙일 수도 있습니다. 말풍선은 관측한 작업을, 카드는 폴더와 최근 연결 Feature·Work Item을 표시합니다. 연결 근거가 없으면 미확인으로 표시합니다. 단순 권한 확인 이벤트는 세션 목록에서 기본으로 숨기며 체크박스로 다시 볼 수 있습니다. 실제 대기 느낌표는 유지됩니다.

## 상세 메뉴 탐색

왼쪽 메뉴는 요약을 검색·필터한 뒤 하나를 골라 상세를 보는 방식입니다. 세션은 작업 주제와 활동 타임라인, Feature는 진척과 의존 관계, Work Item은 Gate 결과와 증거를 중심으로 표시합니다. 연결된 작업·기능·문서를 눌러 근거 화면으로 이동할 수 있습니다.

산출물은 종류별 파일 탐색과 원문 미리보기, Git은 선택한 파일의 작업 트리·스테이징 diff를 제공합니다. Git diff는 선택·탭 전환·새로고침 시 읽으며 자동 갱신 때마다 읽던 내용을 초기화하지 않습니다. Pipeline에서 단계별 기록과 다음 검토 항목을 확인하세요.
