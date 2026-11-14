# SpecThread 설치 매뉴얼

2026-11-14 · macOS 터미널 기준 · Spec Kit v1.4.0 고정

공식 에이전트와 Spec Kit를 먼저 설치한 뒤, 저장소에 있는 SpecThread 로컬 구현을 설치할 수 있습니다. 외부에 배포된 패키지는 없으며 실제 두 에이전트에서의 전체 실행 검증은 진행 중입니다. [통합 상세 설계서](design/SpecThread-통합-상세-설계서.md)

## 1. 실행 환경 선택 및 준비

프로젝트에서 사용할 에이전트를 하나 선택합니다. 두 환경을 비교하려면 별도의 테스트 프로젝트에서 각각 설치합니다. 아래 명령은 **Harness 설계 문서 폴더가 아닌 관리하려는 애플리케이션 프로젝트**에 적용합니다.

Homebrew가 있는 macOS에서는 `brew install uv`로 uv를 설치할 수 있습니다. 이미 설치한 도구는 버전만 확인합니다. Spec Kit는 Python 3.11 이상을 사용합니다. uv로 설치하면 도구의 Python 환경을 관리할 수 있습니다. Git은 아래 GitHub 소스 설치 경로와 향후 Harness 커밋 흐름에 사용합니다. [uv 설치 가이드](https://docs.astral.sh/uv/getting-started/installation/) · [Spec Kit 설치 요구사항](https://github.github.com/spec-kit/installation.html)

```sh
uv --version
git --version
```

### Codex 사용 시

Node.js와 npm이 설치된 터미널에서 실행합니다.

```sh
npm install -g @openai/codex@latest
codex --version
```

대상 프로젝트에서 `codex`를 실행한 뒤 최초 실행 안내에 따라 로그인합니다. [OpenAI 공식 설치 예시](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) · [Codex CLI 문서](https://learn.chatgpt.com/docs/codex/cli)

### Claude Code 사용 시

```sh
brew install --cask claude-code
claude --version
```

대상 프로젝트에서 `claude`를 실행한 뒤 최초 실행 안내에 따라 인증합니다. Homebrew가 없는 환경의 설치 방법도 공식 문서에서 확인할 수 있습니다. [Claude Code 설치·인증 안내](https://code.claude.com/docs/en/setup)

## 2. 공식 Spec Kit 설치

설계서와 같은 버전인 v1.4.0을 사용합니다. `specify version`에 해당 버전이 표시되는지 확인합니다. [Spec Kit v1.4.0 릴리스](https://github.com/github/spec-kit/releases/tag/v1.4.0)

```sh
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.4.0
specify version
```

설치 후 `specify`를 찾지 못하면 `uv tool update-shell`을 실행하고 새 터미널에서 다시 확인합니다. 다른 버전이 나오면 `command -v specify`와 `uv tool list`로 실제 사용 중인 설치본을 확인합니다. 기존 설치가 있으면 처음 설치에 사용한 도구에서 버전을 바꾼 뒤 다시 확인합니다. [uv 도구 사용법](https://docs.astral.sh/uv/guides/tools/) · [Spec Kit 설치 확인](https://github.github.com/spec-kit/installation.html)

## 3. 대상 프로젝트에 공식 연동 설치

### 새 프로젝트

새 프로젝트를 만들 상위 폴더에서 실행합니다. 사용하려는 에이전트에 해당하는 한 줄을 선택합니다.

```sh
# Codex
specify init sdd-codex-demo --integration codex

# Claude Code
specify init sdd-claude-demo --integration claude
```

생성된 폴더로 이동합니다. 향후 Harness 커밋을 검증할 샘플이라면 사용자가 해당 폴더를 Git 저장소로 준비합니다. Spec Kit의 Git 초기화·브랜치 기능은 선택적 `git` 확장에 있습니다. Harness 호환성 테스트용 기본 예제에서는 이 확장을 설치하지 않습니다. [공식 Core 명령](https://github.github.com/spec-kit/overview/core.html)

### 기존 프로젝트에 Spec Kit 처음 설치

대상 Git 저장소 루트에서 `git status --short`로 기존 변경을 확인합니다. 진행 중인 작업을 보존하고 초기화 전후를 비교할 수 있는 상태로 준비합니다. 공식 `--force` 옵션은 비어 있지 않은 폴더에 설치할 때 쓰며, 충돌하는 Spec Kit 관리 경로의 파일을 교체할 수 있습니다. 아래에서 한 줄을 실행한 뒤 새 파일을 포함해 차이를 검토합니다. [기존 프로젝트 도입 가이드](https://github.github.com/spec-kit/how-to/existing-projects.html)

```sh
# Codex
specify init --here --force --integration codex

# Claude Code
specify init --here --force --integration claude
```

### 이미 Spec Kit가 설치된 프로젝트

대상 프로젝트 루트에서 `specify integration list`로 등록 상태를 확인합니다. 필요한 에이전트 연동이 빠져 있을 때 해당 한 줄을 실행합니다. 연동 전환이나 버전 변경이 필요하면 공식 관리 경로를 사용합니다. [Spec Kit 연동 관리](https://github.github.com/spec-kit/integrations/cli.html) · [업그레이드 가이드](https://github.github.com/spec-kit/upgrade.html)

```sh
specify integration install codex
specify integration install claude
```

## 4. 설치 확인

1. 대상 프로젝트에 `.specify/`가 생성됐는지 확인합니다. Codex는 `.agents/skills/speckit-constitution/SKILL.md`, Claude Code는 `.claude/skills/speckit-constitution/SKILL.md`를 확인합니다.
2. 같은 프로젝트 루트에서 선택한 에이전트의 새 세션을 시작합니다. 설치 직후라면 세션을 다시 열어 Skill 목록이 새로 로드되도록 합니다.
3. 쓰기를 확인할 테스트 프로젝트에서 에이전트 입력창에 아래 예를 입력합니다. 기존 프로젝트에 헌법이 있다면 먼저 내용을 검토합니다.

| 환경 | 에이전트 입력창에 넣을 예시 |
| --- | --- |
| Codex | `$speckit-constitution 공개 API 호환성을 유지하고 기존 검증 절차를 따른다.` |
| Claude Code | `/speckit-constitution 공개 API 호환성을 유지하고 기존 검증 절차를 따른다.` |

명령이 인식되고 테스트 프로젝트의 `.specify/memory/constitution.md`에 의도한 내용이 반영되면 공식 연동 확인을 마칩니다. 스킬이 보이지 않으면 프로젝트 루트, 연동 키, 설치된 Skill 경로로 돌아가 확인합니다. Claude Code 자체 상태는 `claude doctor` 또는 세션의 `/doctor`에서 확인할 수 있습니다. [Codex 연동](https://github.github.com/spec-kit/integrations/codex.html) · [Claude Code 연동](https://github.github.com/spec-kit/integrations/claude.html) · [Claude Code 문제 해결](https://code.claude.com/docs/en/troubleshooting)

## 5. Harness 로컬 설치 및 실행

[Harness README](../README.md)의 로컬 설치 절차에 따라 Core CLI와 프로젝트용 스킬을 설치합니다. 대상 프로젝트 루트에서 `sdd-core install-skills codex` 또는 `sdd-core install-skills claude`를 실행한 뒤 새 세션을 시작합니다.

Codex에서는 `$sdd-init`, Claude Code에서는 `/sdd-init`으로 초기 분석을 실행합니다. 공식 `specify init`만 마친 시점에는 Harness Baseline이 생성되기 전입니다. 초기 분석을 마치면 Feature별 공식 spec·plan과 `.specify/baseline/`의 6개 파일, 초기 검증 결과를 확인합니다. 개발·외부 변경 정합화·명시적 커밋의 호출 방식과 현재 Git 지원 범위는 README에 정리했습니다.
