# 03 초기 분석과 Discovery

`sdd-init`은 공식 설치 상태, constitution, 분석 범위와 기존 산출물을 먼저 확인한다.

| 경로 | 분석 순서 | 검증 초점 |
| --- | --- | --- |
| Greenfield | 공식 `specify`로 초기 명세 → 전체 업무 흐름 분석 → 잠정 Feature 분리 → 공식 `clarify`를 재사용하는 반복 상세화 → Discovery Gate → Feature 확정 | 업무 흐름, 요구사항·수용 시나리오와 Feature 경계의 일관성 |
| Brownfield | 소스·계약·설정·문서·테스트와 실행 근거로 기존 시스템 역공학 → 공식 Spec Kit 초기 명세 → 현행 동작과 설계 의도를 이해하는 Discovery → Gate 검증 | 관찰된 동작의 정확성, 명세와 실제 근거의 연결, 확인된 의도와 추론의 구분 |

Brownfield는 기존 시스템을 정확히 이해하는 데 우선순위를 둔다. 현행 분석에서 근거 없는 기능을 추가하거나 관찰된 동작을 승인된 의도로 승격하지 않는다. 기존 명세와 구현이 다르면 양쪽 근거와 미확인 사항을 기록한다. 새로 발견한 **현행 기능**은 분석에 추가한다. 신규 요구사항은 명시적인 후속 개발 요청에서 다룬다.

Discovery에서 공식 `specify`의 명세 생성과 `clarify`의 명확화 기능을 재사용한다. 기존 유효 명세는 재사용하고 필요한 경우 공식 개정 흐름을 따른다. 공식 명령마다 활성 경로를 확인하고 생성 호출이 다른 명세 또는 기존 파일을 덮어쓰지 않도록 한다. 기존 답변과 근거를 먼저 확인하고, 의미 있는 미확정 경계·요구사항·아키텍처 판단에만 사용자 확인을 요청한다. 공식 호출이 생성한 경로나 번호는 Harness의 영구 식별자가 아니다.

잠정 Feature는 이름과 초안 경로로 비교한다. 분리·통합 전후에 원본 명세의 요구사항, 수용 시나리오, 예외 및 계약을 결과 명세와 양방향으로 대조해 누락, 의미 변형, 충돌을 찾아 해결한다. 경계를 변경하면 의존관계도 재검토한다. 잠정 Feature는 영구 UUID나 Baseline의 확정 Feature/의존관계 레코드에 등록하지 않는다.

## Discovery Gate

| Discovery Gate | 판정과 다음 단계 |
| --- | --- |
| `READY` | 업무 흐름 또는 현행 동작을 근거로 설명할 수 있고 Feature 경계와 요구사항 연결이 검증됐다. 검증한 범위를 확정하고 기존 UUID는 유지하며 신규 확정 Feature에만 UUID v7을 부여한다. |
| `CONDITIONAL` | 핵심 범위는 설명할 수 있지만 비핵심 조건이나 미확인 사항이 남아 있다. 조건과 영향을 기록하고 확인 가능한 분석을 이어간다. 조건이 남은 잠정 Feature는 재평가에서 `READY`를 얻은 뒤 확정한다. |
| `BLOCKED` | 핵심 동작·의도·계약의 판정 근거가 부족하거나 누락·의미 변형·충돌이 해결되지 않았다. 해당 범위의 확정과 초기 분석 완료를 보류하고 근거를 보완하거나 사용자 판단을 요청한다. |

Gate의 결과와 근거, 조건, 남은 질문과 재검증 범위는 기존 Markdown 기록(`project.md`, `decisions.md`, 해당 공식 명세)에 남긴다. 문서 분량이나 Feature 수는 판정 기준에서 제외한다. Discovery Gate는 Feature 확정에 쓰고, 영향 분석의 `SAFE` / `UNKNOWN` / `CONFLICT` 및 Work Item 상태는 각자의 판정에 사용한다.

~~~mermaid
flowchart TD
  G["Greenfield 요구사항"] --> GS["공식 Spec Kit 초기 명세"]
  GS --> W["전체 업무 흐름 분석"]
  W --> F["잠정 Feature 분리"]
  F --> R["공식 명세 명확화와 반복 상세화"]
  B["Brownfield 기존 시스템"] --> E["코드·계약·설정·테스트 역공학"]
  E --> BS["공식 Spec Kit 초기 명세"]
  BS --> BD["현행 동작과 설계 의도 확인"]
  R --> M["분리·통합 시 요구사항 보존 검증"]
  BD --> M
  M --> D{"Discovery Gate"}
  D -->|READY| C["Feature 확정 · 기존 UUID 유지 · 신규 UUID 발급"]
  D -->|CONDITIONAL| Q["비핵심 조건 기록 · 확인 가능한 분석 계속"]
  D -->|BLOCKED| X["차단 근거 보고 · 해당 범위 중단"]
  Q --> V["보완 후 영향 범위 재검증"]
  X --> V
  V --> D
  C --> P["공식 계획·필요 설계 자료 · Baseline 검증"]
  P --> ENTRY{"대상 개발 진입 조건 충족?"}
  ENTRY -->|예| DEV["partial에서도 대상 Feature 개발"]
  ENTRY -->|아니오| HOLD["대상 개발 보류"]
  P -->|실패| J["정상 결과 보존 · 실패 범위 재검증"]
  J -->|경계나 요구사항 변경 시| V
  J -->|계획 또는 구조만 보완| P
  P -->|통과| I["프로젝트 초기 분석 완료"]
~~~

### 현재 Core 제출 계약

`sdd-core discovery-gate PLAN.json`은 `mode`(`greenfield` 또는 `brownfield`), `candidate`(잠정명 또는 초안 경로), `checks`를 받는다. 두 경로 모두 `scope`, `boundaries`, `requirements`, `spec_quality`를 제출하고, Greenfield는 `workflow`, Brownfield는 `current_behavior`를 추가한다. 각 점검에는 `status`(`verified`, `condition`, `blocked`)와 구체적인 `evidence`를 기록한다. 미해결 항목에는 `next_step`을 추가한다. 비핵심이라는 근거와 `critical: false`가 있는 `condition`만 조건부로 처리한다. Core의 출력은 후보, 판정, 미해결 항목이다. 이미 확정한 Feature는 기존 ID를 유지한다. 신규 후보에는 `--issue-id`로 READY가 확인될 때만 UUID가 반환된다.

## 초기 분석 상태와 개발 진입

프로젝트 분석 상태는 `not_started`, `partial`, `complete`로 구분한다. `complete`는 전체 초기 분석 완료를 의미한다. Feature별 개발 가능 여부는 프로젝트 분석 상태, 대상 Feature의 Discovery 판정과 핵심 의존성 근거로 매번 평가한다. 별도 개발 가능 플래그를 중복 저장하지 않는다.

| 조건 | 개발 진입 |
| --- | --- |
| `not_started` | 차단 |
| `partial` + 대상 `active` Feature의 Discovery `READY` + 미분석 영역과의 핵심 의존성 위험 없음이 검증됨 | 허용 |
| 대상 Discovery `CONDITIONAL` 또는 `BLOCKED`, 핵심 의존성 `UNKNOWN` 또는 `CONFLICT` | 해당 Feature 차단 |
| `complete` | 대상 Feature의 활성 상태·Discovery·의존성 및 적용 Gate를 확인한 뒤 허용. 모든 Feature의 개발을 자동 허용하지 않음 |

진입 판정은 기존 Baseline의 분석 기록·Feature·의존관계·Discovery 근거를 활용한다. 개발 범위가 확대되거나 관련 근거가 달라지면 영향 범위를 다시 평가한다. 전체 분석 완료를 선언하는 조건과 부분 분석 상태에서의 개발 진입은 각각 판단한다. Core 0.3.0의 `analysis-record`가 분석과 대상별 근거를 저장하며 `develop-check`가 현재 입력의 유효성과 대상·의존성 READY를 확인한다. start, in_progress 진입, Gate 실행과 완료에서도 이 조건을 검사한다.

## 초기화 완료와 재개

Gate를 통과한 Feature에 공식 계획과 필요한 설계 자료(`research.md`, `data-model.md`, `contracts/`, `quickstart.md` 등)를 작성하고 Baseline 여섯 파일을 검증한다. `scaffold`는 누락 파일의 틀을 만들고 기존 파일을 보존한다. 범위 내 Feature가 모두 확정되고 전체 조사와 의미 검토, 필요한 산출물 및 참조 검증을 마쳤으며 차단 소견이 없을 때 초기 분석을 완료한다. 새 `tasks.md`는 개발 때 만들고 기존 태스크는 보존한다. 초기화에는 적용 가능한 공식 명세 품질 검사, spec·plan 정합성과 Core 구조 검사를 조합한다. 태스크를 요구하는 `analyze`와 구현 이후의 `converge`는 각 전제가 갖춰진 단계에서 실행한다.

실패·중단 시 유효한 기존 산출물, 초안과 Markdown의 판단 근거를 보존한다. 재개하면 현재 파일, 분석 근거, Gate 조건, Baseline을 대조한다. 이미 검증한 범위와 UUID는 유지하고 누락·변경·조건부·차단 범위만 이어서 검증한다. 경계나 요구사항이 바뀌면 영향받은 분리·통합 검증과 Gate를 다시 평가한다. 충돌한 파일은 덮어쓰지 않고 판단을 요청한다. 초기 분석 완료와 최초 Git 반영은 별도 이정표다.

**실행 확인 범위**는 Codex Greenfield 데모와 Baseline 재검증이다. 최신 Discovery Gate, Brownfield 전수 분석, 부분 재개, 두 에이전트의 동등 결과는 추가 검증이 필요하다.

## 분석 기록의 CLI 계약

`analysis-record PLAN.json`은 status, unanalysed(범위 설명 배열), paths(실제 입력 파일), evidence(실제 증거 참조 배열), features(UUID별 분석 객체)를 받는다. 각 Feature 분석은 `discovery`(mode/candidate/checks)와 비어 있지 않은 `dependencies` 영향 판정 배열을 포함한다. 영향 판정은 assessment/evidence 및 필요한 critical을 기록한다. 전체 complete를 기록하려면 모든 활성 Feature의 근거가 준비돼 있어야 한다.

분석이 기록되는 features.yaml 자체를 입력으로 삼지 않고 원본 명세·계약·조사 자료를 지정한다. 입력·증거 해시, 분석 범위와 기능별 구조 해시가 현재 자료와 일치해야 유효하다. 다른 범위는 미분석으로 남겨도 되지만 대상의 핵심 의존 안전성을 근거로 검증해야 한다. 기록 후 `develop-check UUID ...`로 판정하며 실제 개발 가능 플래그는 저장하지 않는다.
