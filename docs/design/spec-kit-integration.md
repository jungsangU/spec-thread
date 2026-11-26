# 공식 Spec Kit 연동 계약

설계 1.2 · 재현 기준 GitHub Spec Kit **v1.4.0** (`0019fa1`). 이 문서는 공식 기능·전제와 SpecThread 연결 방식의 원본이다. 현재 최신 버전 일반론이 아니라 고정한 태그의 문헌 대조다. [릴리스](https://github.com/github/spec-kit/releases/tag/v1.4.0)

| 영역 | 공식 기능 및 전제 | Harness 설계에 적용 |
| --- | --- | --- |
| 설치·연동 | `specify init`은 프로젝트 및 에이전트 연동을 설치한다. 기존 Spec Kit 프로젝트에는 `specify integration install codex` 또는 `claude`를 사용할 수 있다. Codex는 `.agents/skills/`의 `$speckit-…`, Claude Code는 `.claude/skills/`의 `/speckit-…`를 사용한다. | 설치와 업그레이드는 공식 도구에 맡기고 Harness 스킬은 별도 배포한다. `specify init`과 `sdd-init`은 각각 설치와 프로젝트 분석에 사용한다. [설치](https://github.github.com/spec-kit/installation.html) · [Codex](https://github.github.com/spec-kit/integrations/codex.html) · [Claude Code](https://github.github.com/spec-kit/integrations/claude.html) |
| Feature 선택 | 활성 경로는 `.specify/feature.json` 또는 우선순위가 높은 `SPECIFY_FEATURE_DIRECTORY`로 선택한다. 브랜치 전환만으로 Feature가 바뀌지 않는다. v1.4.0 `specify` 템플릿은 호출당 한 Feature를 생성하며 지정 경로에 초기 템플릿을 쓴다. | 하나의 Work Item에서도 Feature별 공식 컨텍스트를 선택한다. 신규 Feature에는 공식 생성 흐름을 사용한다. 기존 Feature에는 공식 가이드의 개정 흐름을 사용하고 `specify`·`plan` 재실행 전에는 기존 파일에 대한 쓰기 동작을 검증한다. 활성 경로의 저장·복원·통합 처리와 충돌을 PoC에서 확인한다. [활성 경로](https://github.github.com/spec-kit/overview/core.html) · [태그 소스](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/specify.md) |
| Brownfield·기존 명세 | 공식 가이드는 기존 프로젝트에서 constitution을 세우고 소스와 제약을 반영해 기능을 개발하는 방법을 안내한다. 기존 `spec.md`를 개정할 수 있으나 `spec/plan/tasks` 차이를 자동 조정하는 전용 코어 명령은 제공하지 않는다. | 전체 Feature 탐색·식별과 현행 Baseline 구축은 Harness 책임이다. 기존 Feature 개정은 의도된 변경과 기존 산출물을 확인하고 해당 단계만 갱신한다. [기존 프로젝트](https://github.github.com/spec-kit/how-to/existing-projects.html) · [기존 명세 발전](https://github.github.com/spec-kit/how-to/evolving-specs.html) |
| Discovery | 공식 `specify`는 초기 명세를 만들고, `clarify`는 활성 명세의 모호성을 확인하고 답을 기록한다. | Harness가 업무 흐름·현행 근거 분석, 분리·통합 검증과 Discovery Gate를 담당한다. 공식 호출은 잠정 Feature의 확정이나 Harness UUID 발급을 뜻하지 않는다. [v1.4.0 specify](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/specify.md) · [v1.4.0 clarify](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/clarify.md) |
| 작성·구현 | `constitution`, `specify`, `clarify`, `plan`, `checklist`, `tasks`, `analyze`, `implement`, `converge`를 단계와 전제에 맞춰 쓴다. `tasks.md`는 Feature 내부 작업·순서·완료 체크를 관리한다. | 승인된 Feature의 기존 산출물을 재사용한다. Harness UUID 기반 Work Item은 사용자 요청의 변경·검증 이력을 여러 Feature에 걸쳐 연결한다. [공식 흐름](https://github.github.com/spec-kit/quickstart) |
| 산출물 품질 | `specify`는 요구사항 품질 체크를 포함한다. `checklist`는 요구사항 품질을 점검한다. `analyze`는 완성된 `tasks.md`와 `spec.md`, `plan.md`가 필요한 읽기 전용 산출물 분석이다. | 태스크 없는 초기화에는 적용 가능한 명세 품질 체크와 Harness 검증을 조합한다. 분석 결과와 프로젝트 테스트 결과는 각각 확인한다. [명세 템플릿](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/specify.md) · [analyze 템플릿](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/analyze.md) |
| 구현 수렴 | `converge`는 `tasks`와 현재 태스크에 대한 `implement` 이후 코드와 산출물을 대조한다. 조치할 격차가 있으면 `tasks.md`에 추가하고, 수렴하면 파일을 유지한다. | 검증 공간에서 새로운 작업이 필요한 결과는 실패로 보고한다. 수렴 명령의 쓰기 동작을 고려하여 검증 전후 파일 상태를 확인한다. [converge 템플릿](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/converge.md) |
| Git | Git 작업은 기본 미설치인 번들 `git` 확장에서 제공한다. Feature 브랜치 및 단계별 선택적 커밋 훅이 있다. | 자동 커밋 금지 및 사용자 브랜치 책임과 충돌하는 훅을 활성화하지 않는 구성을 확인한다. 프로젝트 Git 반영은 사용자가 담당한다. [Core CLI](https://github.github.com/spec-kit/overview/core.html) · [v1.4.0 Git 확장 매니페스트](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/extensions/git/extension.yml) |
| 자동 실행 | 공식 YAML Workflow와 검토 게이트가 있다. 공식 어댑터의 비대화형 실행은 `codex exec` 및 `claude -p`를 사용한다. 번들 `speckit` 흐름에는 태스크와 구현 단계도 있다. | 공식 호출 경로의 재사용 후보. 초기화에는 필요한 단계만 실행하며 자체 세션 오케스트레이터는 MVP에서 제외한다. 양쪽 스킬에서의 위임과 실제 환경 변수 전파·결과 판독은 PoC로 확인한다. [Workflows](https://github.github.com/spec-kit/workflows/overview.html) · [단계 정의](https://github.github.com/spec-kit/workflows/steps.html) |
| 저장·추적 | 공식 흐름은 Feature 산출물, 태스크 체크, 체크리스트 및 명령 결과를 제공한다. 공식 문서와 확인한 태그 소스에서는 프로젝트 전체 Feature UUID 그래프와 Work Item별 검증 Fingerprint을 제공하는 코어 계약을 확인하지 못했다. | Baseline과 프로젝트 검증 연결은 Harness에서 확장한다. 새 요구가 생기면 공식 기능을 먼저 확인한다. [공식 흐름](https://github.github.com/spec-kit/quickstart) · [공식 확장 CLI](https://github.github.com/spec-kit/extensions/cli.html) |

공식 기능 확인 → 기존 명령·산출물·워크플로우 재사용 검토 → 부족한 부분 식별 → 최소 확장 → 원형과의 중복·충돌 검토 순으로 적용한다. 공식 `checklist`가 생성하는 사용자 정의 체크리스트는 검토자가 체크 상태를 관리한다. `specify`와 `clarify`가 관리하는 기본 요구사항 체크리스트와 실행 테스트 결과를 구분한다. [v1.4.0 checklist 템플릿](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/checklist.md)

## 관련 명세

[에이전트 설치·호출](07-agent-runtime.md) · [Discovery](03-analysis-standard.md) · [개발 흐름](04-artifact-lifecycle.md) · [검증](06-verification.md) · [공식 호출 PoC](acceptance.md)


## 프로파일별 호출 선택

[설계 1.2 프로파일](verification-profiles.md)은 공식 명령을 바꾸지 않고 적용할 단계를 선택한다. Lightweight의 기본 제외는 새 Checklist/Analyze/Converge 호출을 항상 생성하지 않는다는 뜻이며 이미 존재하는 공식 체크리스트·필수 확장 훅·프로젝트 정책을 무시하지 않는다. 선택한 Implement는 실제 tasks와 기존 공식 검사를 수행한다. Analyze와 Converge는 각각 산출물 일관성과 구현 격차라는 별개 목적을 유지한다. 공식 Analyze가 요구하는 후속 조치 승인 등 원형의 명시적 판단은 일반 자동 진행으로 대체하지 않는다. 공식 결과 공유 API를 가정하지 않고 실제 보고서와 동일 입력이 확인된 범위만 재사용한다.

## Analyze·Converge 호출 효율

| 변경 유형 | 선택 기준 |
| --- | --- |
| 단순 결함·계약 유지 리팩터링 | 선택적 Analyze·Converge 기본 제외 |
| 국소 확장 | 변경분 정합성으로 충분한지 조건 검토 |
| 복수 요구·설계 변경 또는 신규 Feature | 각 공식 검증의 적용 조건 검토 |
| 복수 Feature 계약·큰 아키텍처 변경 | 두 목적을 각각 적극 검토 |
| 공식/프로젝트 필수 또는 사용자 전체 검토 | 해당 목적의 공식 절차를 필수 범위로 수행 |

이 기준은 프로파일 최소·동적 절차와 필수 정책을 대체하지 않는다. 선택적 절차가 불필요하면 추가하지 않되, 필요해 호출한 공식 Skill을 변경분만 읽는 축약 검증으로 바꾸지 않는다. 실제 설치본의 입력·출력·선행 조건을 확인하고 원형의 필수 범위를 지킨다. 공식 검토와 같은 의미의 별도 분석은 중복하지 않고 결과를 기존 Work Item 판단에 활용한다. 유효성은 [프로파일·절차 기록 계약](verification-profiles.md)을 따른다. Analyze·Converge의 목적을 합치거나 변경분 검토로 필수 공식 절차를 완료 처리하지 않는다.

공식 Skill 수정·Fork·Preset을 통한 검증 변경·Extension의 별도 검증 명령·모방 엔진은 이번 범위에 도입하지 않는다. 기존 sdd-develop의 호출 선택과 기존 Core의 기록·Gate만 사용한다.
