# SpecThread

공식 GitHub Spec Kit v1.4.0을 독립 설치한 프로젝트에서 사용하는 로컬 구현입니다. [설치 매뉴얼](docs/SpecThread-설치-매뉴얼.md) · [설계서](docs/design/SpecThread-통합-상세-설계서.md)

## 로컬 설치

Python 3.11 이상에서 Harness 소스 폴더를 설치한 뒤, Spec Kit로 초기화한 대상 프로젝트 루트에서 에이전트 하나를 선택합니다.

```sh
python3 -m pip install /path/to/spec-thread
cd /path/to/target-project
sdd-core install-skills codex
# 또는 sdd-core install-skills claude
```

| 업무 | Codex 스킬 | Claude Code 스킬 |
| --- | --- | --- |
| 프로젝트 분석 | `$sdd-init` | `/sdd-init` |
| 개발 | `$sdd-develop` | `/sdd-develop` |
| 외부 변경 정합화 | `$sdd-sync` | `/sdd-sync` |
| 명시적 통합 커밋 | `$sdd-commit` | `/sdd-commit` |

스킬은 공식 작업과 의미 분석을 에이전트에게 맡깁니다. Core는 Baseline과 상태 전이, 파일 Fingerprint, 검증 명령 실행 및 Git 트리 반영을 담당합니다. Core의 통합 검증은 선택한 계획의 명령과 스킬이 수집한 영향 분석 근거를 사용합니다.

## 통합 커밋 운영 범위

현재 구현은 기존 커밋이 있는 같은 Git 저장소의 Worktree를 지원합니다. 대상 로컬 브랜치는 어떤 Worktree에도 체크아웃되어 있지 않아야 합니다. 선택한 상대 경로는 각 Worktree의 현재 파일 내용을 사용합니다. 인덱스에만 존재하는 중간 버전이나 최초 Baseline 커밋은 이 경로의 지원 범위 밖입니다.

`sdd-core preview PLAN.json`의 기준과 트리 ID를 검토한 뒤 계획에 `reviewed_base`와 `reviewed_tree`를 기록합니다. `sdd-core commit PLAN.json`은 동일 트리에서 전체 검증 명령을 실행하고 Git 기준이 일치할 때 단일 커밋을 반영합니다. 계획의 검증 명령은 사용자와 프로젝트가 신뢰하는 명령을 사용합니다.

공식 스킬의 실제 호출과 전체 흐름은 Codex 및 Claude Code에서 각각 실행 검증이 필요합니다. Sync 승인과 초기화 완료 확인은 현재 스킬 절차에 있으며 Core가 독립적으로 강제하는 단계는 아닙니다.
