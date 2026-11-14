# SpecThread 통합 상세 설계서

2026-11-14 · MVP 설계 기준 · 공식 기능 대조 기준 GitHub Spec Kit **v1.4.0** (`0019fa1`)

이 문서는 SDD 산출물 관리 표준 대화의 합의를 구현 가능한 단위로 정리한다. **확정**은 합의한 정책, **보류**는 MVP 이후 확장 후보, **미결정**은 구현 계약의 선택이 남은 항목, **PoC 확인**은 실제 설치·실행으로 확인해야 할 항목이다. 상충하는 기록은 §11에 근거와 함께 남겼다. 공식 최신 릴리스는 GitHub의 Latest 대상으로 확인했다. [v1.4.0 릴리스](https://github.com/github/spec-kit/releases/tag/v1.4.0)

## 1. 목적과 권위

Greenfield(그린필드)와 Brownfield(브라운필드)에 동일한 산출물 규격과 개발 절차를 적용한다. 신규 프로젝트에서는 요구사항·도메인 자료에서 시작하고, 기존 프로젝트에서는 소스·설정·계약·문서·실행 근거에서 시작한다. Greenfield의 아키텍처는 계획으로, Brownfield의 관찰 결과는 현재 구현 사실로 표시한다. 구현이 없는 Feature(피처)에는 가상의 소스 참조를 생성하지 않는다.

- **의도**는 승인된 공식 `spec.md`와 프로젝트 헌법이 정한다. `plan.md`와 `tasks.md`는 이를 구현할 기술 계획과 작업을 담는다.
- **현재 구현**의 근거는 실제 코드·계약이다. 로컬 개발 중에는 현재 작업 공간, 커밋 시에는 통합으로 고정한 Git 트리를 사용한다.
- **검증**은 해당 입력으로 얻은 점검 결과와 증거를 제공한다. 승인된 의도와 관찰된 구현이 어긋나면 차이를 보고하고 승인된 해결 방향을 적용한다.
- **Baseline(베이스라인)**은 프로젝트 전체 구조·관계·추적·작업 이력이다. Source Map(소스 맵)은 파생 인덱스이며 실제 소스와 공식 산출물에서 복구한다. 과거 검증 이력과 현재 Feature 구조를 함께 추적하되 각자의 원본을 유지한다.

정상 개발은 Harness(하네스)를 사용하고 외부 변경은 예외로 다룬다. 분석은 근거를 우선하며 중요한 요구사항 추정, Feature 경계 또는 아키텍처 판단에만 조건부로 사용자 확인을 요청한다.

## 2. 구성 및 실행 책임

~~~mermaid
flowchart LR
  U["사용자"] --> X["Codex"]
  U --> Y["Claude Code"]
  X --> A["Codex용 Harness Skill"]
  Y --> B["Claude Code용 Harness Skill"]
  A --> K["공식 Spec Kit 스킬·스크립트"]
  B --> K
  A --> C["Shared SDD Core CLI"]
  B --> C
  K --> S["공식 Feature 산출물"]
  C --> L["대상 프로젝트 .specify/baseline/"]
  A --> P["로컬 코드·계약·기존 검증 도구"]
  B --> P
  U --> G["명시적 Harness Git Commit"]
  G --> C
  G --> T["임시 통합 공간 → 대상 Git의 단일 커밋"]
~~~

| 구성 | 책임 |
| --- | --- |
| Codex / Claude Code | 둘 다 MVP 정식 지원. 저장소 해석, 의미 분석, 명세·설계의 작성 및 수정, 구현, 검사 실행과 증거 수집 |
| Harness Skill(스킬) | 세 명령의 실행 절차, 공식 스킬 호출, 사용자 확인 및 보고. 두 환경의 연결 방식만 개별 구현 |
| Shared SDD Core CLI | UUID v7 발급·검사, YAML 구조와 참조 무결성, 상태와 필수 검증 게이트, 파일 Fingerprint(핑거프린트), Git 통합 과정의 결정론적 검증 |
| 공식 Spec Kit | 독립 설치·업데이트. 공식 명령과 템플릿을 재사용하고 공식 관리 파일 및 생성 규칙의 원형 유지 |
| 사용자 | 프로젝트별 실행 환경 선택, 세션·Worktree(워크트리) 생성·실행·중단·재개·분배·정리, Git 기준 관리, 승인 및 커밋 대상 선택 |

CLI는 에이전트의 의미 판단, 근거 참조 및 검사 결과를 입력받아 누락·불일치·차단 조건을 점검한다. 명령 종료 성공만으로 의미 검증 통과를 인정할 수 없으므로 결과 계약은 PoC에서 점검한다. 두 환경에는 같은 스키마·상태·완료 조건을 적용한다. 한 프로젝트 안에서 두 환경을 동시에 혼용하거나 작업을 인계하는 기능은 MVP 범위 밖이다.

`/sdd.init`, `/sdd.develop`, `/sdd.sync`는 사용자 관점의 논리적 명령명이다. Codex와 Claude Code에서 동일한 점 표기 명령으로 직접 호출 가능한지는 확인되지 않았다. Harness의 실제 스킬 이름·호출 형태와 Core CLI 공개 문법은 PoC 항목이다.

## 3. 공식 Spec Kit 기능 대조

| 영역 | 공식 기능 및 전제 | Harness 설계에 적용 |
| --- | --- | --- |
| 설치·연동 | `specify init`은 프로젝트 및 에이전트 연동을 설치한다. 기존 Spec Kit 프로젝트에는 `specify integration install codex` 또는 `claude`를 사용할 수 있다. Codex는 `.agents/skills/`의 `$speckit-…`, Claude Code는 `.claude/skills/`의 `/speckit-…`를 사용한다. | 설치와 업그레이드는 공식 도구에 맡기고 Harness 스킬은 별도 배포한다. `specify init`과 `/sdd.init`은 각각 설치와 프로젝트 분석에 사용한다. [설치](https://github.github.com/spec-kit/installation.html) · [Codex](https://github.github.com/spec-kit/integrations/codex.html) · [Claude Code](https://github.github.com/spec-kit/integrations/claude.html) |
| Feature 선택 | 활성 경로는 `.specify/feature.json` 또는 우선순위가 높은 `SPECIFY_FEATURE_DIRECTORY`로 선택한다. 브랜치 전환만으로 Feature가 바뀌지 않는다. v1.4.0 `specify` 템플릿은 호출당 한 Feature를 생성하며 지정 경로에 초기 템플릿을 쓴다. | 하나의 Work Item에서도 Feature별 공식 컨텍스트를 선택한다. 신규 Feature에는 공식 생성 흐름을 사용한다. 기존 Feature에는 공식 가이드의 개정 흐름을 사용하고 `specify`·`plan` 재실행 전에는 기존 파일에 대한 쓰기 동작을 검증한다. 활성 경로의 저장·복원·통합 처리와 충돌을 PoC에서 확인한다. [활성 경로](https://github.github.com/spec-kit/overview/core.html) · [태그 소스](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/specify.md) |
| Brownfield·기존 명세 | 공식 가이드는 기존 프로젝트에서 constitution을 세우고 소스와 제약을 반영해 기능을 개발하는 방법을 안내한다. 기존 `spec.md`를 개정할 수 있으나 `spec/plan/tasks` 차이를 자동 조정하는 전용 코어 명령은 제공하지 않는다. | 전체 Feature 탐색·식별과 현행 Baseline 구축은 Harness 책임이다. 기존 Feature 개정은 의도된 변경과 기존 산출물을 확인하고 해당 단계만 갱신한다. [기존 프로젝트](https://github.github.com/spec-kit/how-to/existing-projects.html) · [기존 명세 발전](https://github.github.com/spec-kit/how-to/evolving-specs.html) |
| 작성·구현 | `constitution`, `specify`, `clarify`, `plan`, `checklist`, `tasks`, `analyze`, `implement`, `converge`를 단계와 전제에 맞춰 쓴다. `tasks.md`는 Feature 내부 작업·순서·완료 체크를 관리한다. | 승인된 Feature의 기존 산출물을 재사용한다. Harness UUID 기반 Work Item은 사용자 요청의 변경·검증 이력을 여러 Feature에 걸쳐 연결한다. [공식 흐름](https://github.github.com/spec-kit/quickstart) |
| 산출물 품질 | `specify`는 요구사항 품질 체크를 포함한다. `checklist`는 요구사항 품질을 점검한다. `analyze`는 완성된 `tasks.md`와 `spec.md`, `plan.md`가 필요한 읽기 전용 산출물 분석이다. | 태스크 없는 초기화에는 적용 가능한 명세 품질 체크와 Harness 검증을 조합한다. 분석 결과와 프로젝트 테스트 결과는 각각 확인한다. [명세 템플릿](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/specify.md) · [analyze 템플릿](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/analyze.md) |
| 구현 수렴 | `converge`는 `tasks`와 현재 태스크에 대한 `implement` 이후 코드와 산출물을 대조한다. 조치할 격차가 있으면 `tasks.md`에 추가하고, 수렴하면 파일을 유지한다. | 검증 공간에서 새로운 작업이 필요한 결과는 실패로 보고한다. 수렴 명령의 쓰기 동작을 고려하여 검증 전후 파일 상태를 확인한다. [converge 템플릿](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/converge.md) |
| Git | Git 작업은 기본 미설치인 번들 `git` 확장에서 제공한다. Feature 브랜치 및 단계별 선택적 커밋 훅이 있다. | 자동 커밋 금지 및 사용자 브랜치 책임과 충돌하는 훅을 활성화하지 않는 구성을 확인한다. Harness의 선택적 Worktree 통합과 검증된 트리 반영은 별도 책임이다. [Core CLI](https://github.github.com/spec-kit/overview/core.html) · [v1.4.0 Git 확장 매니페스트](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/extensions/git/extension.yml) |
| 자동 실행 | 공식 YAML Workflow와 검토 게이트가 있다. 공식 어댑터의 비대화형 실행은 `codex exec` 및 `claude -p`를 사용한다. 번들 `speckit` 흐름에는 태스크와 구현 단계도 있다. | 공식 호출 경로의 재사용 후보. 초기화에는 필요한 단계만 실행하며 자체 세션 오케스트레이터는 MVP에서 제외한다. 양쪽 스킬에서의 위임과 실제 환경 변수 전파·결과 판독은 PoC로 확인한다. [Workflows](https://github.github.com/spec-kit/workflows/overview.html) · [단계 정의](https://github.github.com/spec-kit/workflows/steps.html) |
| 저장·추적 | 공식 흐름은 Feature 산출물, 태스크 체크, 체크리스트 및 명령 결과를 제공한다. 공식 문서와 확인한 태그 소스에서는 프로젝트 전체 Feature UUID 그래프, Work Item별 검증 Fingerprint 및 선택된 Worktree의 통합 검증을 제공하는 코어 계약을 확인하지 못했다. | Baseline과 통합 검증은 Harness에서 확장한다. 새 요구가 생기면 공식 기능을 먼저 확인한다. [공식 흐름](https://github.github.com/spec-kit/quickstart) · [공식 확장 CLI](https://github.github.com/spec-kit/extensions/cli.html) |

공식 기능 확인 → 기존 명령·산출물·워크플로우 재사용 검토 → 부족한 부분 식별 → 최소 확장 → 원형과의 중복·충돌 검토 순으로 적용한다. 공식 `checklist`가 생성하는 사용자 정의 체크리스트는 검토자가 체크 상태를 관리한다. `specify`와 `clarify`가 관리하는 기본 요구사항 체크리스트와 실행 테스트 결과를 구분한다. [v1.4.0 checklist 템플릿](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/checklist.md)

## 4. Baseline 최소 데이터 계약

대상 프로젝트 Git에서 앱 코드, 공식 산출물과 함께 관리하는 경로다. 이 설계서 자체는 Harness 개발 저장소의 `docs/design/`에 있다.

| 파일 · 위치 `.specify/baseline/` | 최소 내용 |
| --- | --- |
| `project.md` | 목적, 범위, 제약, 분석 대상과 제외 범위, 프로젝트 분석 결과와 미확인 사항 |
| `architecture.md` | 전체 구조, 주요 구성 요소·경계·관계, 확인된 계약, 계획과 관찰의 구분 |
| `decisions.md` | 주요 판단, 근거, 필요한 사용자 승인 및 충돌 해결 결정 |
| `features.yaml` | `features[]`에 `id`, `name`, `spec_path`, `dependencies[]`. 각 의존 항목에 `feature_id`, `type` |
| `source-map.yaml` | `mappings[]`에 `feature_id`, `sources[]`. 각 항목에 `path`, `symbol`로 주요 구현·계약을 참조 |
| `work-items.yaml` | `work_items[]`에 `id`, `status`, `declared_features`, `actual_features`, 최종 `validation` 요약. 예시의 검증 필드는 `status`, `fingerprint`, `evidence[].ref` |

Markdown에는 서술 규칙만 적용한다. 아래 YAML은 합의된 최소 예시를 엮은 것이다. 64자리 해시는 형식 예시다.

```yaml
# features.yaml
features:
  - id: "019a1234-5678-7abc-8def-123456789abc"
    name: document-parsing
    spec_path: specs/001-document-parsing
    dependencies:
      - feature_id: "019a1234-5678-7abc-8def-123456789abd"
        type: api
  - id: "019a1234-5678-7abc-8def-123456789abd"
    name: document-storage
    spec_path: specs/002-document-storage
    dependencies: []
```

```yaml
# source-map.yaml
mappings:
  - feature_id: "019a1234-5678-7abc-8def-123456789abc"
    sources:
      - path: src/parser/service.py
        symbol: ParserService.parse
```

```yaml
# work-items.yaml
work_items:
  - id: "019a1234-5678-7abc-8def-123456789abe"
    status: completed
    declared_features:
      - "019a1234-5678-7abc-8def-123456789abc"
    actual_features:
      - "019a1234-5678-7abc-8def-123456789abc"
    validation:
      status: passed
      fingerprint: "sha256:0000000000000000000000000000000000000000000000000000000000000000"
      evidence:
        - ref: specs/001-document-parsing/tasks.md
```

- Feature와 Work Item(워크 아이템)은 생성 시 UUID v7을 독립 발급한다. ID는 불변·재사용 금지다. 공식 디렉터리 번호, 슬러그, 브랜치명과 별개다. 이름 변경만으로 경로를 자동 변경하지 않는다. 중복 UUID와 서로 다른 UUID의 동일 Feature/경로 등록은 각각 식별해 후자는 의미 검토에 보낸다.
- Work Item 하나에 여러 Feature가 연결될 수 있다. 선언 범위는 시작 시 예상, 실제 범위는 변경이 확인된 Feature다. 영향받은 Feature와 검증 대상 Feature에는 관찰이나 재검증만 필요한 항목도 포함할 수 있다. 범위 변경 이유를 남긴다. `related_work_items`는 필요할 때만 명시하는 선택적 UUID 참조다.
- 의존 유형 초기 예시는 `api`, `data`, `event`, `runtime`이다. 여러 의존과 실제 순환을 허용한다. 역방향 관계는 계산한다. 순환은 기본 경고이며 중대한 설계 충돌·장애 위험이 확인되면 차단한다. Feature 분할·병합 시 기존 ID를 새 개념에 재사용하거나 의존관계를 일괄 승계하지 않는다. 이전 참조의 보존 표현은 미결정이다.
- Core는 UUID 형식·중복, 참조 존재, 공식 산출물 경로, 상태 값, 증거와 Fingerprint의 형식·참조 일관성을 검사한다. 코드 심볼의 역할과 계약의 실제 의미는 에이전트가 근거로 판단한다. Source Map은 모든 함수나 변수를 색인하지 않는다.
- 검증 요약과 증거 참조를 Work Item별로 누적 보존한다. 태스크 내용·상세 로그·중간 분석 그래프를 Baseline에 복사하지 않는다. 최종 영향 판정과 근거, 사용자 결정, 차단 소견을 남기는 정책은 확정이다. 필드명 및 필수 여부가 마지막 최소 예시에 반영되지 않은 항목은 §11에 정리했다.

## 5. 명령별 실행

### `/sdd.init` — 최초 분석 및 미완료 초기화 재개

1. 공식 설치 상태와 프로젝트 범위를 확인한다. Greenfield는 요구사항·도메인 자료, Brownfield는 실제 소스·계약·설정·문서 및 기존 Spec Kit 산출물을 읽는다.
2. 프로젝트 목적·경계·구성 요소를 분석하고 전체 Feature 후보를 찾는다. 새로 발견한 Feature를 분석 목록에 추가한다. 확실한 항목부터 진행하고 모호한 경계·의존성은 근거 재확인 후 차단 항목만 사용자에게 올린다.
3. 기존 공식 산출물을 재사용하거나 Feature별 공식 `spec.md`, `plan.md`와 필요한 설계 문서(`research.md`, `data-model.md`, `contracts/`, `quickstart.md` 등)를 작성한다. 새 `tasks.md`는 실제 개발 시 생성한다. 이미 있던 정상 태스크는 보존한다.
4. 6개 파일을 초기화한다. UUID·경로·관계·Source Map을 점검하고 Brownfield는 주요 구현·계약과 분석 결과를 대조한다. 공식 명세 품질 검사를 적용하고 태스크 없는 단계의 `analyze` 및 `converge` 전제 충돌은 §11의 PoC로 다룬다.
5. 식별한 전체 Feature의 분석 완료, 누락 점검, 핵심 산출물 존재, 근거 및 미확인 사항 기록, 차단 소견 0건을 확인한다. 실패하면 생성된 정상 산출물을 보존하고 나머지 검증을 재실행한다. 재개는 현재 파일과 Baseline 검증으로 판단하고, 이미 유효하게 완료한 Feature는 유지하며 미완료 범위를 이어서 처리한다. 초기 분석 완료와 초기 Git 반영은 §11의 별도 이정표다.

### `/sdd.develop` — 사용자 요청부터 Work Item 완료까지

1. 프로젝트 전체 초기화가 끝났는지 확인한다. 기존 Feature는 Baseline, 공식 산출물, 소스로 매칭한다. 확실한 기존 Feature를 우선 재사용하고, 모호할 때만 확인한다. 새로운 Feature에는 UUID를 발급한다.
2. 사용자 요청에 Work Item UUID 하나를 부여하고 선언 Feature를 기록한다. Feature별로 공식 컨텍스트를 선택하여 신규 명세 작성 또는 기존 명세 개정 후 필요한 계획·태스크·분석·구현·수렴을 수행한다.
3. 개발 중 요구사항이나 범위가 변하면 동일한 작업의 영향받은 공식 단계로 돌아간다. 계약 변화와 실제 의존성을 분석하고 안전한 범위 확장은 사유를 기록한 뒤 진행한다.
4. 범위 확정, 관련 공식 단계 완료, 주요 코드·계약 변경 및 최종 검증 같은 단계 경계에서 Baseline과 Source Map을 갱신한다. 구조 갱신이 실패하면 현재 코드와 공식 산출물을 보존하고 완료를 보류한다.
5. 모든 관련 Feature의 필수 로컬 검증과 Baseline 갱신에 성공하면 최종 결과·증거·Fingerprint를 기록하고 `completed`로 전환한다. Git 커밋은 별도 명시 요청에서 수행한다.

### `/sdd.sync` — 예외적인 외부 변경 정합화

1. 사용자가 지정한 외부 변경과 비교 근거를 확인한다. 실제 코드, 계약 및 공식 산출물에서 차이를 확인하고 영향 Feature·의존관계를 추적한다.
2. 승인된 의도와 구현의 차이, 필요한 공식 산출물의 검증·개정, Baseline 변경안을 제시한다. 코드 또는 계약의 관찰 결과를 사용자 의도로 승격하지 않는다.
3. 승인한 범위만 반영한다. 변경 영향, 증거 및 Baseline 무결성을 재검증한다. 거절·차단·실패 시 차이와 남은 조치를 보고하고 사용자의 기존 파일을 보존한다. 외부 변경 자체를 자동으로 되돌리거나 덮어쓰지 않는다.
4. 기준 revision 선택, 계획 승인과 적용 사이 입력 변경 처리, Sync에 의한 Work Item 이력의 구체적 기록 방식은 미결정이다.

~~~mermaid
flowchart TD
  I["/sdd.init · 전체 탐색"] --> S["Feature별 spec·plan / Baseline 초안"]
  S --> IV{"전체 초기 검증"}
  IV -->|차단 소견| IR["기존 결과 보존 · 추가 근거 또는 수정"]
  IR --> IV
  IV -->|통과| R["초기 분석 완료"]
  R --> D["/sdd.develop · Work Item"]
  D --> F["공식 Feature 단계 · 구현 · 영향 분석"]
  F --> L{"로컬 필수 검증 / Baseline 기록"}
  L -->|실패| F
  L -->|통과| C["completed"]
  C --> G["사용자의 별도 Harness Git Commit"]
  E["외부 변경"] --> Y["/sdd.sync · 분석 및 제안"]
  Y -->|사용자 승인| Z["Baseline 반영 및 재검증"]
~~~

## 6. 상태 전이 및 병렬 실행

~~~mermaid
stateDiagram-v2
  [*] --> pending
  pending --> in_progress: 작업 시작
  in_progress --> in_progress: 복구 가능한 검증 실패 / 수정과 재검증
  in_progress --> suspended: 사용자 중단 또는 판단 대기
  suspended --> in_progress: 현재 산출물 확인 후 사용자 주도 재개
  in_progress --> completed: 필수 로컬 검증 통과 및 기록 성공
  in_progress --> failed: 작업 실패로 종료
  completed --> [*]
  failed --> [*]
~~~

`in_progress`는 마지막 저장 상태다. 실제 실행 중인 프로세스를 나타내지 않는다. `failed`의 상세 판정 및 재처리 규칙은 미결정이며 도식의 종료는 해당 실행의 종료를 뜻한다. 완료 작업은 다시 열지 않는다. 후속 변경은 새 UUID의 Work Item으로 기록하고 필요하면 이전 작업을 참조한다. 초기 분석의 의미상 상태는 `not_started → partial → complete`로 추적하며 저장 필드 충돌은 §11에 명시했다.

재개 시 실제 파일과 작업 범위를 대조한다. 일치한 경우 재개하고 독립 변경은 보존한다. 같은 영역의 충돌과 출처가 불명확한 변경은 사용자 판단을 받는다. 누락된 공식 산출물은 해당 공식 절차를 통해 복구한다. SQLite, 락, FIFO 대기열, 중앙 ID 발급기, Worktree 등록부, 세션 감시, 체크포인트 관리자, 자동 복구·실시간 동기화는 MVP에서 제외한다.

## 7. 영향 분석과 위험도 게이트

1. 변경 코드와 계약을 확인해 직접 변경 Feature를 정한다. 파일 위치나 변경량만으로 중요도를 정하지 않고 공개 계약·데이터·보안·의존 관계에 미치는 영향을 확인한다. Source Map과 Feature 그래프로 후보를 좁히고 실제 코드·계약·공식 산출물로 확인한다.
2. 직접 의존 Feature에 계약 영향이 확인되면 다음 의존 단계까지 전파한다. 영향이 없다는 근거를 확인한 경로에서는 전파를 멈춘다. 순환에서는 이미 확인한 관계를 반복 처리하지 않는다. 영향이 확인된 Feature만 수정 대상으로 확장한다.
3. 근거가 부족하면 관련 심볼, 호출부, 데이터 계약, 테스트를 추가 조사한다. 여전히 판단이 불가능할 때 `UNKNOWN`으로 남긴다. `SAFE`에도 판단 근거를 남긴다.
4. Source Map의 심볼 이동·삭제·불일치는 실제 코드와 공식 산출물에서 재분석하여 교정한다. 해결되지 않은 핵심 참조는 게이트에 반영한다.

| 판정 | 개발·초기화 완료 | 통합 커밋 |
| --- | --- | --- |
| `SAFE` | 근거 기록 후 진행. 개발 범위 자동 확장 가능 | 필수 통합 검증을 통과하면 허용 |
| 비핵심 `UNKNOWN` | 추가 분석 후 경고·근거 기록으로 허용 가능 | 통합 재검증 후 허용 가능 |
| 핵심 계약·보안·데이터 무결성 `UNKNOWN` | 완료 차단. 근거 확보 또는 위험 해소 필요 | 동일하게 차단. 사용자 승인만으로 해제 불가 |
| `CONFLICT` | 상충하는 계약·산출물·구현 근거를 제시하고 사용자와 해결 후 재검증 | 해결 전 차단 |

## 8. 검증과 Fingerprint

| 검증 층 | 범위 |
| --- | --- |
| 공식 Spec Kit | 단계에 맞는 명세 품질, 산출물 간 정합성, 구현과 의도 간 격차 |
| 대상 프로젝트 | 이미 존재하는 테스트·빌드·정적 분석 등 필수 명령과 결과 |
| Harness | Baseline 구조·참조, Feature 관계·Source Map·영향 판정, 결과의 파일 동일성 및 통합 검증 |

개발 중에는 영향 분석에 따라 변경 파일, 영향받은 계약과 Feature 관련 소스 및 공식 산출물을 검증 입력으로 선정한다. 검증 통과 시 내용에 기반한 Fingerprint를 기록한다. 영향받은 검증은 재실행하고 동일 입력으로 확인 가능한 통과 결과만 재사용한다. 입력 재구성이 모호하면 해당 결과를 재사용할 수 있는 근거를 추가 확보한다. 완료 시 Work Item의 필수 검증을 모두 만족해야 한다. 커밋에서는 선택된 변경을 통합한 결과에 대해 **최종 통합 검증 세트 전체를 재실행**한다.

검증 환경은 변하지 않는다는 운영 전제를 사용자가 보장한다. 런타임 버전 및 설치 환경 수집·감지·환경 Fingerprint는 제외한다. Fingerprint는 검증한 파일의 유효성 확인용이며 브랜치 감시나 Git 기준 확인에 쓰지 않는다. 완료 Work Item의 과거 Fingerprint와 증거를 이후 검증으로 덮어쓰지 않는다. 테스트 결과를 증거로 참조할 때 공식 태스크 체크와 실행 근거를 구분한다. 해시 직렬화, 파일 집합의 재구성, 삭제·이름 변경, 검증 항목별 재사용에 필요한 데이터 및 증거 보존 계약은 미결정이다.

## 9. 명시적 Harness Git Commit

### 실행 계약

- 사용자가 전체 작업을 완료 또는 안전하게 중단하고 기준 브랜치와 동시 작업을 확인한 뒤 명시적으로 요청한다. 입력은 선택된 Worktree와 대응 Work Item, 대상 Git 기준 및 포함할 변경 범위다. 정확한 입력 형식은 미결정이다.
- Harness는 선택된 Work Item의 저장 상태가 `completed`인지 검증한다. 선택하지 않은 Worktree의 변경은 포함 대상에서 제외한다. 선택 작업이 미선택 변경에 의존하면 통합 검증을 차단한다.
- 대상은 관리 중인 애플리케이션 Git이다. 작업 공간과 Git 커밋 생명주기는 분리한다. 명시적 요청 없이 프로젝트 커밋을 만들지 않는다.

### 트랜잭션 흐름

~~~mermaid
sequenceDiagram
  actor U as 사용자
  participant H as Harness
  participant T as 임시 통합 공간
  participant G as 대상 Git
  U->>H: 안전 상태 확인 후 선택 작업 커밋 요청
  H->>H: 선택 Work Item completed 검사
  H->>T: 대상 기준과 선택 변경을 고정해 통합
  T->>T: 3-way 통합 / Baseline 의미 검증
  T->>T: 최종 검증 세트 전체 실행
  alt 충돌 또는 검증 실패
    T-->>U: 원인·작업·Feature 보고
  else 통과
    T->>G: 검증한 트리의 단일 커밋을 기대 기준으로 반영
    G-->>U: 커밋 결과 또는 Git 기준 불일치
  end
~~~

1. 대상 기준의 코드와 Baseline을 출발점으로 선택 변경만 별도 임시 공간에 조립한다. 공통 조상과 각 변경을 대조하는 3-way 통합을 사용한다. 선택 변경의 추출 방식과 적용 순서, staged·unstaged·untracked 범위는 PoC에서 확정한다.
2. 코드·공식 산출물과 Baseline을 같은 후보 트리로 묶는다. 구조화 파일은 Feature 및 Work Item UUID, 의존 간선, 소스 참조 단위로 대조한다. 독립 변경은 함께 유지하고 동일 의미에 대한 상충·삭제 대 수정·경로 충돌은 명시적으로 보고한다. 수정 시각으로 우선순위를 정하지 않는다. Markdown은 텍스트 병합 후 구조·의미를 확인한다.
3. 후보 트리를 고정해 공식 검사, 프로젝트 테스트·빌드·정적 분석, 교차 Feature·Baseline 검증을 전체 실행한다. 검증이 소비한 입력과 최종 커밋의 트리가 일치해야 한다. 검사에서 파일을 쓰거나 추가 구현 소견이 생겼으면 그 결과를 그대로 게시하지 않는다.
4. 통과하면 코드, 공식 산출물, Baseline을 포함한 **단일 커밋**을 생성하고 검증된 트리를 기대 기준에서 그대로 반영한다. Git 기준 불일치, 충돌 또는 커밋 실패 시 보고하고 중단한다. 기준 브랜치 상시 감시와 자동 재통합·재검증·강제 반영은 제외한다. Git이 기대한 기준에서만 반영되도록 하는 보호와 현재 체크아웃·인덱스 일관성의 구현은 PoC 대상이다.
5. 실패 시 관련 Work Item·Feature·근거를 보고한다. 사용자가 원본 Worktree를 선택하여 수정하고 로컬 검증을 진행한다. 완료된 Work Item 자체는 불변이며 후속 수정은 새 Work Item 정책을 따른다. 다음 명시 요청에서 임시 공간을 다시 구성하고 최종 검증 세트 전체를 재실행한다. 성공·실패 모두 원본 Worktree를 자동 삭제하거나 수정하지 않는다.

## 10. PoC, 검증 시나리오, MVP 인수 기준

PoC에서는 공식 태그, 설치된 프로젝트 파일, 에이전트 종류·버전, 실제 호출 및 쓰기 경로, 종료 결과와 파일 차이를 함께 기록한다. 이 문서의 문헌 확인과 실제 양쪽 환경 실행 검증은 별개의 증거다.

| ID | 실행 시나리오 | 통과 기대 결과 |
| --- | --- | --- |
| P01 | 독립된 테스트 프로젝트 두 개에 공식 v1.4.0을 Codex와 Claude Code로 각각 설치. Harness 연결 후 호출·쓰기·출력 비교 | 각 환경에서 세 명령 진입, 동일 Core 스키마와 차단 판정. 공식 관리 파일 임의 패치 없이 연결 |
| P02 | Greenfield 요구사항으로 두 Feature 분석. 하나는 소스 미구현. 태스크 없는 초기 검증 | 동일 6개 파일 및 Feature별 spec·plan. 허위 심볼과 신규 tasks 없음. 적용 가능한 공식 검사와 별도 검사 범위 확인 |
| P03 | Brownfield에 숨은 의존성·기존 산출물·모호한 Feature 혼재. 중단 후 재실행 | 신규 발견 동적 추가, 정상 파일 보존, 근거 있는 항목부터 분석. 중대 미확인 항목 해결 전 전체 완료 차단 |
| P04 | 한 Work Item에서 기존 Feature 수정과 새 Feature 추가. 다른 Feature의 명세와 컨텍스트도 존재 | 기존 UUID·경로·보존 대상 내용 유지, 신규만 UUID 생성. 공식 단계 반복에서 대상별 출력 확인. `specify` 초기 쓰기 및 feature.json 부수 효과 확인 |
| P05 | API 변경이 A→B→C로 전달되는 경우와 중간 계약이 유지되는 경우. 비핵심·핵심 UNKNOWN과 충돌 입력 | 근거 따라 전파·정지. 비핵심은 기록·재검증 후 허용 가능. 핵심 UNKNOWN과 CONFLICT는 완료 및 커밋 차단 |
| P06 | 검증한 코드·계약 변경, 파일 삭제·이름 변경, 무관한 수정, 검증 실패 후 재실행 | 영향받은 개발 검사만 무효화, 필수 로컬 검사 누락 차단. 완료 이력은 유지. 통합에서는 최종 검증 세트 전체 실행 |
| P07 | 중단 후 독립 변경·충돌·누락 파일과 재개. 외부 코드 변경에 대한 Sync 승인·거절 | 독립 변경 보존, 충돌 보고, 공식 절차로 누락 복구. Sync는 승인 범위만 반영하고 승인된 의도를 임의 개정하지 않음 |
| P08 | W1과 W3 선택, W2 제외. 분리된 YAML 변경과 동일 API 충돌, W2에 대한 숨은 의존성 각각 시험 | 무충돌 시 의미 단위 통합과 단일 커밋. 충돌 또는 미선택 의존성은 차단. 세 원본의 상태 유지 |
| P09 | 후보 트리 검증 중 도구가 산출물 변경, 검증 뒤 대상 ref 변경, 대상 브랜치가 체크아웃된 상태를 각각 재현 | 검증되지 않은 트리와 달라진 기대 기준을 반영하지 않음. 실패 시 대상과 원본의 일관성 확인. 검증 트리 ID와 최종 커밋 트리 ID 비교 |
| P10 | `git` 확장 훅 유무, 기존 Worktree의 로컬 변경·인덱스·기존 커밋 혼합, 실패 후 후속 Work Item으로 수정 | 암묵적 브랜치 이동·커밋 없이 선택된 변경만 사용. 명시적으로 재요청한 통합에서 전체 검증 정책 유지 |
| P11 | UUID 중복, 존재하지 않는 Feature, 잘못된 경로·상태·증거, 다른 UUID로 등록된 동일 Feature | 구조 오류와 의미 충돌 각각 식별. 차단 사유에 근거와 관련 ID 표시. 잘못된 기록으로 completed 전환 금지 |
| P12 | 초기 분석 통과 후 별도 Git 반영을 시도하는 신규 저장소와 기존 저장소 | 자동 커밋 없이 초기화 결과를 보존. 최초 커밋에서 사용할 선택 단위 및 개발 진입 계약을 검증 |

진행 순서는 공식 호환성 PoC → 공통 스키마·게이트와 두 스킬 연결 → 초기화·개발·Sync 검증 → 임시 통합과 단일 커밋 검증이다. MVP 인수에는 두 환경에서 동일 샘플을 각각 끝까지 실행한 증거가 필요하다. 비교 기준은 의미상 대응하는 Feature·참조, 동일 상태 전이 및 게이트 결과이며 독립 발급 UUID와 서술 문장의 바이트 동일성을 요구하지 않는다.

## 11. 결정 기록과 구현 전 확인 사항

| 구분 | 기록 |
| --- | --- |
| **확정** | Spec Kit 독립 설치·원형 유지·공식 기능 우선. Codex / Claude Code 동등 지원. 공통 Core CLI 및 Baseline 6개 파일. MVP에 세 명령, 검증 게이트와 명시적 Harness Git Commit 포함 |
| **확정** | 초기화는 프로젝트 전체 분석. 개발은 Work Item 완료까지. Sync는 사용자 승인형 외부 변경 정합화. 완료 Work Item은 보존하고 새 변경을 새 UUID로 추적 |
| **확정** | 로컬 개발과 커밋 분리. 사용자 소유의 병렬 작업 및 기준 관리. 선택 완료 작업만 임시 통합, 통합 검증 전체 실행, 검증된 트리 반영 |
| **대체된 설계** | 로컬 v0.1의 `.sdd/` 및 별도 Artifact/Claim/Evidence 스키마 중심 구조는 최신 Spec Kit + Baseline 설계의 MVP 스키마에 포함되지 않는다. 의도·구현·검증 권위 구분과 사용자 승인 수동 정합화 원칙은 유지한다. R0~R3와 새 게이트 간의 대응 규칙은 확정된 바 없다. 과거 순번 ID, 중앙 발급·잠금·대기열·SQLite 및 Codex 우선 정책은 후속 결정으로 대체됐다. [초기 결정 이력](DECISIONS.md) |
| **보류** | 선택적 전용 검증 프레임워크. 기존 실행 도구와 판정 정책은 논리적으로 분리해 둔다. 한 프로젝트에서의 두 에이전트 혼용, 설치 래퍼 및 세부 패키징은 별도 검토 대상 |
| **미결정 · 초기화 이정표** | 과거 합의에 초기화 완료 커밋 1회와 개발 전 해당 커밋 존재가 포함된다. 이후 합의는 자동 커밋 금지와 `completed` Work Item 선택을 요구한다. 이 문서는 초기화 검증과 Git 반영을 별도 이정표로 표시했다. 최초 Baseline 커밋에 일반 Work Item을 요구하는지와 그 생성 방식, 초기화 커밋을 개발 진입 시 어떻게 확인할지는 확정하지 않는다. |
| **미결정 · 스키마 간극** | 앞선 합의에 `initial_analysis.status`, `analysis_status`, `scope_changes`, `changed_features` / `affected_features`, `assessment`, 판단 `evidence` / `decisions`, `assessed_features`, `blocking_findings`가 나온다. 마지막 최소 예시는 이 키들을 모두 포함하지 않는다. 의미상 기록 요구는 보존하고, `changed_features`와 `actual_features`의 중복을 포함해 저장 위치·명칭·필수 여부는 스키마 확정 시 결정한다. 별도 `committed` Worktree 상태 기록의 이전 언급도 후기의 최소 상태 모델 및 등록부 제외 정책과 대조해 보류한다. |
| **PoC 확인 · 공식 검증** | 태스크 생성 전의 공식 명세 품질 체크와 계획 검토에 대한 실제 검증 범위. 분석 결과 파싱과 게이트 매핑. 기존 명세 개정 및 활성 Feature 경로 전달. 공식 Git 훅 및 작업 공간 파일 변경 여부. |
| **미결정 · Fingerprint와 결과 계약** | 경로·내용 직렬화, 파일 목록 및 검사별 범위를 복원할 방법, 형식·결과 코드·근거 참조의 보존 및 변경 후 유효성, 프로젝트별 필수 검사 선언 위치. |
| **미결정 · Git과 실패 처리** | 변경 스냅샷 범위·조상·병합 순서, 경로 충돌과 완료 이력 충돌 처리, 최종 대상 ref를 엄격한 기준으로 반영하는 구현 및 체크아웃된 브랜치 처리, 검증 직후 수정 검출, 임시 리소스 정리, Sync 승인 입력 바인딩. 일반 Git 작업 및 Worktree 정리의 구체적 명령은 사용자 책임 계약에 맞춰 결정한다. |
| **미결정 · 유지보수** | 선택 언어·도입 프로젝트, 스키마 버전·마이그레이션, 폐기 Feature의 참조 보존, Core 배포와 실행 환경별 실제 명령 이름. |

PoC에서 설계와 공식 동작이 다르면 재현 조건과 영향받는 결정을 명시하고 기존 합의를 변경할지 따로 검토한다. 원본 설계 대화 · [로컬 초기 설계 백로그](OPEN-ISSUES.md)
