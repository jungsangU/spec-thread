# 03 초기 분석과 Discovery

`sdd-init`은 공식 설치 상태, constitution, 분석 범위와 기존 산출물을 먼저 확인한다. 초기 질문은 [대화형 진행](conversation-flow.md)에 따라 지금 필요한 한 항목씩 묻고 기존 답과 자료를 재사용한다. 질문 순서를 이유로 기존 분석·Discovery Gate를 생략하지 않는다.

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
  D -->|READY| C["Feature 경계 확정 · 기존 UUID 유지"]
  D -->|CONDITIONAL| Q["비핵심 조건 기록 · 확인 가능한 분석 계속"]
  D -->|BLOCKED| X["차단 근거 보고 · 해당 범위 중단"]
  Q --> V["보완 후 영향 범위 재검증"]
  X --> V
  V --> D
  C --> P["공식 계획·필요 설계 자료 · 신규 등록(UUID) · Baseline 검증"]
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

진입 판정은 기존 Baseline의 분석 기록·Feature·의존관계·Discovery 근거를 활용한다. 개발 범위가 확대되거나 관련 근거가 달라지면 영향 범위를 다시 평가한다. 전체 분석 완료를 선언하는 조건과 부분 분석 상태에서의 개발 진입은 각각 판단한다. Core 0.5.0의 `analysis-record`가 분석과 대상별 근거를 저장하며 `develop-check`가 현재 입력의 유효성과 대상·의존성 READY를 확인한다. start, in_progress 진입, Gate 실행과 완료에서도 이 조건을 검사한다.

## 초기화 완료와 재개

Gate를 통과한 Feature에 공식 계획과 필요한 설계 자료(`research.md`, `data-model.md`, `contracts/`, `quickstart.md` 등)를 작성하고 Baseline 일곱 파일을 검증한다. `scaffold`는 누락 파일의 틀을 만들고 기존 파일을 보존한다. 범위 내 Feature가 모두 확정되고 전체 조사와 의미 검토, 필요한 산출물 및 참조 검증을 마쳤으며 차단 소견이 없을 때 초기 분석을 완료한다. 새 `tasks.md`는 개발 때 만들고 기존 태스크는 보존한다. 초기화에는 적용 가능한 공식 명세 품질 검사, spec·plan 정합성과 Core 구조 검사를 조합한다. 태스크를 요구하는 `analyze`와 구현 이후의 `converge`는 각 전제가 갖춰진 단계에서 실행한다.

실패·중단 시 유효한 기존 산출물, 초안과 Markdown의 판단 근거를 보존한다. 재개하면 현재 파일, 분석 근거, Gate 조건, Baseline을 대조한다. 이미 검증한 범위와 UUID는 유지하고 누락·변경·조건부·차단 범위만 이어서 검증한다. 경계나 요구사항이 바뀌면 영향받은 분리·통합 검증과 Gate를 다시 평가한다. 충돌한 파일은 덮어쓰지 않고 판단을 요청한다. 초기 분석 완료와 최초 Git 반영은 별도 이정표다.

실행 검증 상태는 [백로그](OPEN-ISSUES.md), 인수 시나리오는 [PoC 기준](acceptance.md)에서 확인한다.

## 분석 기록의 CLI 계약

`analysis-record PLAN.json`은 status, unanalysed(범위 설명 배열), paths(실제 입력 파일), evidence(실제 증거 참조 배열), features(UUID별 분석 객체)를 받는다. 각 Feature 분석은 `discovery`(mode/candidate/checks)와 비어 있지 않은 `dependencies` 영향 판정 배열을 포함한다. 영향 판정은 assessment/evidence 및 필요한 critical을 기록한다. 전체 complete를 기록하려면 모든 활성 Feature의 근거가 준비돼 있어야 한다.

분석이 기록되는 features.yaml 자체를 입력으로 삼지 않고 원본 명세·계약·조사 자료를 지정한다. 입력·증거 해시, 분석 범위와 기능별 구조 해시가 현재 자료와 일치해야 유효하다. 다른 범위는 미분석으로 남겨도 되지만 대상의 핵심 의존 안전성을 근거로 검증해야 한다. 기록 후 `develop-check UUID ...`로 판정하며 실제 개발 가능 플래그는 저장하지 않는다.

## 관련 명세

공식 호출과 활성 경로는 [Spec Kit 연동](spec-kit-integration.md), 확정 이후 등록·재편은 [Feature 생명주기](feature-lifecycle.md), 개발은 [Work Item 생명주기](04-artifact-lifecycle.md)를 따른다.

## Core 0.5.0 제출 예시와 차단 순서

다음은 필드 형식을 실행 검증하기 위한 예시다. 실제 명세·계획과 판단 근거 파일이 먼저 존재해야 한다. 코드가 없는 Greenfield이므로 소스 매핑은 생략한다. 아래의 `verified`와 `SAFE`는 실제 조사 후 제출하며 이 예시 자체를 의미 검토 증거로 사용할 수 없다.

### Discovery 계획 예시

```json
{
  "mode": "greenfield",
  "candidate": "specs/example",
  "checks": {
    "scope": {"status": "verified", "evidence": "basis.md: 범위 확인"},
    "boundaries": {"status": "verified", "evidence": "basis.md: 경계 확인"},
    "requirements": {"status": "verified", "evidence": "basis.md: 요구사항 보존 확인"},
    "spec_quality": {"status": "verified", "evidence": "basis.md: 명세 품질 검토"},
    "workflow": {"status": "verified", "evidence": "basis.md: 업무 흐름 확인"}
  }
}
```

`discovery-gate`는 candidate/verdict/findings를 반환한다. findings에는 미해결 check/status/evidence/next_step을 담는다. Discovery evidence는 비어 있지 않은 설명 문자열이며 이 명령이 파일 존재나 의미를 증명하지는 않는다. 실제 입력·증거 파일의 존재와 해시는 등록·분석 기록에서 확인한다. `condition`은 명시적인 `critical: false`가 없으면 blocked로 올리고, 전체 판정은 BLOCKED가 CONDITIONAL보다 우선한다. Brownfield에서는 workflow 대신 current_behavior를 필수로 제출한다.

### Feature 등록 계획 예시

```json
{
  "feature": {"name": "example", "spec_path": "specs/example", "dependencies": []},
  "discovery": "<DISCOVERY_PLAN>",
  "paths": ["specs/example/spec.md", "specs/example/plan.md"],
  "evidence": ["basis.md"]
}
```

`<DISCOVERY_PLAN>` 문자열을 바로 위 Discovery **객체**로 교체해 feature-register에 제출한다. 반환은 등록된 UUID 문자열이다. standalone `discovery-gate --issue-id`의 UUID 반환은 Baseline 등록이 아니다. 정상 등록 흐름에서는 feature-register가 반환한 UUID를 그대로 사용하고 다시 발급하지 않는다. 등록은 spec·plan, READY, 기존 UUID·경로 중복과 현재 참조를 확인한다.

### 분석 기록 계획 예시

```json
{
  "status": "partial",
  "unanalysed": ["독립된 미분석 영역"],
  "paths": ["specs/example/spec.md", "specs/example/plan.md"],
  "evidence": ["basis.md"],
  "features": {
    "<FEATURE_UUID>": {
      "discovery": "<DISCOVERY_PLAN>",
      "dependencies": [{"assessment": "SAFE", "evidence": "미분석 영역과 핵심 의존성 위험 없음 검증"}]
    }
  }
}
```

`<FEATURE_UUID>`는 등록 반환값, `<DISCOVERY_PLAN>`은 위 객체로 교체한다. dependencies는 실제 Feature 그래프 간선 목록과 다른 **분석 소견 배열**이다. 명시적 의존이 없어도 미분석 경계 안전성에 대한 비어 있지 않은 소견이 필요하다.

개발 진입은 구조 검사 → 프로젝트 status → 프로젝트 inputs/evidence 유효성 → 대상과 의존 Feature 순회 → 각 Feature의 구조·분석·입력·증거 해시 → READY → 의존성 위험 순으로 확인한다. 현재 구현은 대상의 등록된 의존 Feature도 재귀적으로 확인하고 방문 집합으로 순환을 종료한다. complete 분석 기록은 미분석 목록이 비고 모든 활성 Feature가 유효해야 저장한다. 분석 객체가 바뀌면 이전 보고서의 analysis_hash가 맞지 않으므로 필요한 보고서를 같은 제출에서 재확정한다. Core가 그래프 밖의 미발견 의존성을 자동 탐색하는 것은 아니며 그 충분성은 Skill이 판단한다.

초기화는 기존 테스트·빌드·정적 검사·실제 검토 방법도 탐색하여 [verification.yaml](verification-profiles.md)에 재사용 정의를 등록한다. 방법이 미확인이면 unconfigured를 유지하며 검증을 추정해 통과시키지 않는다. Feature 탐색·Discovery·분리/통합 보존 정책은 변하지 않고, 이후 개발은 유효한 분석과 검증 정의를 재사용한다.

## Isolated의 초기 분석 위치

프로젝트 최초 init은 활성 Work가 없는 원본에서 수행한다. 이후 개발 중 신규 Feature는 `start --discovery`의 pending 사본에서 공식 초기 명세·Discovery를 수행한다. READY 확정 Feature UUID만 등록하고 최초 scope-expand로 해당 Work와 결합한다. 잠정 Feature에 영구 UUID를 주지 않는다. 도구·권한·Hook 검증은 [병렬 개발](parallel-development.md)을 따른다.
