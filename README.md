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

스킬은 공식 작업과 의미 분석을 에이전트에게 맡깁니다. Core는 Baseline과 상태 전이, 파일 Fingerprint, 검증 명령 실행 및 Git 트리 반영을 담당합니다. Core의 통합 검증은 선택한 계획의 명령과 스킬이 수집한 영향 분석 근거를 사용합니다.

## Git과 버전 운영

두 Git 저장소의 Commit·Push·Merge·Rollback은 사용자가 수행합니다. Core 0.2.0은 `version-check`로 로컬 설치의 일치를 확인합니다. 기존 설치를 교체한 경우 [버전 동기화](docs/design/version-sync.md) 절차를 사용합니다.

## Discovery와 설계 가이드

AI와 설계 작업을 시작할 때는 [AGENTS.md](AGENTS.md)를 먼저 읽고, [설계 목차](docs/design/README.md)에서 관련 명세와 결정 기록을 확인합니다.

`sdd-init`은 공식 Spec Kit의 명세 작성·명확화를 재사용하고 `sdd-core discovery-gate`로 Feature 확정 조건을 검사합니다. 최신 절차는 [설계 문서와 HTML 가이드](docs/design/README.md)에서 확인할 수 있습니다. 기존 설치 버전과 스킬이 다르면 동기화 미리보기로 적용 대상과 품질 검사를 검토합니다.
