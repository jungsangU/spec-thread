# SpecThread 설계와 실행 가이드

설계 1.0 · 2026-11-21 · 공식 Spec Kit v1.4.0 재현 기준

SpecThread는 개발 요청이 어떤 의도를 바꿨고 어떤 코드로 구현됐으며 무슨 검증을 통과했는지 추적한다. 공식 Spec Kit가 Feature 수준에서 명세·계획·태스크·구현을 안내하고, SpecThread는 여러 Feature를 가로지르는 변경 기록과 검증 근거를 연결한다. Git 반영은 사용자가 수행한다.

## 한눈에 보는 산출물 흐름

```text
Greenfield 요구사항 → 공식 초기 명세 → 업무 흐름·잠정 Feature 상세화
Brownfield 역공학 → 공식 초기 명세 → 현행 동작·의도 확인
                  ↓ 대상 READY · 핵심 의존성 위험 검증 · partial 개발 가능
       spec.md → plan.md + 필요한 설계 문서
                  ↓ 실제 개발 요청 · Work Item
       tasks.md → 구현 코드 + 프로젝트 테스트
                  ↓ 분석 · 구현 대조 · 실행 검증
       Source Map + Work Item 검증 기록 + Fingerprint
                  ↓ 사용자가 대상 Git 변경 범위를 검토
       기존 검사 결과 확인 → 사용자 Git 반영
```

Baseline은 흐름 전체에서 Feature 경로, 의존성, 소스, 작업과 검증 증거를 연결한다. 도중 외부 변경이 발견되면 Sync에서 코드와 승인된 의도의 차이를 검토하고 사용자가 승인한 범위를 정합화한다.

## 왜 이 구조를 선택했나

| 설계 선택 | 이유 | 실제 효과 |
| --- | --- | --- |
| 공식 기능을 먼저 사용 | 명세·계획·태스크 형식과 스킬의 변경을 공식 경로에서 받아들일 수 있다 | 프로젝트가 기존 Spec Kit 문서를 재사용한다 |
| 의도·구현·실행 증거의 권위를 구분 | 구현 편차를 곧바로 의도로 수용하면 회귀를 정상으로 기록할 수 있다 | 코드가 명세와 어긋나면 원인을 분류하고 수정 방향을 결정한다 |
| 최소 Baseline과 UUID | 전체 소스 인덱스나 중앙 발급기가 없어도 변경 이력을 연결할 수 있다 | 이름과 공식 디렉터리 번호가 바뀌어도 Feature를 추적할 수 있다 |
| 에이전트의 의미 분석과 Core의 결정론적 검사 | 정책·코드의 의미는 근거를 해석해야 하고 상태·해시·트리는 재현 가능한 검사가 필요하다 | Codex와 Claude Code에서 같은 완료 게이트를 사용한다 |
| 로컬 작업과 커밋 분리 | 병렬 작업 상태를 사용자에게 맡기고 게시 시점에 선택한 변경 전체를 검증할 수 있다 | Work Item을 완료해도 자동 커밋이 생기지 않으며 조합에 따른 회귀를 검증한다 |

## 사례로 보는 문서와 코드의 의존 관계

개인 할 일 앱의 등록·조회·완료를 예로 들면, `spec.md`에는 사용자가 어떤 상태에서 무엇을 기대하는지와 수용 시나리오가 들어간다. `plan.md`는 그 의도를 실현할 화면 구조와 저장소 사용을 정한다. 데이터 모델은 할 일 ID와 상태를 정의하고, UI 계약은 사용자 입력과 완료 표시의 조건을 구체화한다. 연구 문서는 기술 선택의 근거를, quickstart는 재현 가능한 실행·검증 방법을 설명한다.

개발 요청이 들어오면 기존 Feature의 UUID와 경로를 찾고 Work Item을 만든다. `tasks.md`에서 요구사항과 작업의 연결을 확인한 뒤 저장 모듈, 화면 이벤트, 목록 렌더링, 검증 작업을 구현한다. 예를 들어 완료 처리는 명세의 기대 결과, 데이터 상태와 UI 계약, 작업 정의를 함께 읽어야 구현할 수 있다. 브라우저 테스트는 완료 버튼의 존재 외에도 선택한 항목만 완료되는지, 새로 열었을 때 상태가 복원되는지 검증한다. Source Map에는 해당 기능의 주요 구현·계약 파일 경로를 연결한다. 새 요청이 완료 의미를 바꾸면 영향받는 명세·계획·계약·태스크를 다시 검토한 후 코드를 변경한다.

이 사례의 Codex 실행에서는 Feature UUID 유지, 작업 7개 완료, Chrome 검증, Baseline 재검증과 `completed` 기록을 확인했다. 신규 사용자 5명 대상 사용성 측정은 비핵심 `UNKNOWN`으로 기록됐다. 검증이 통과한 범위와 측정하지 않은 범위를 Work Item에서 구별할 수 있다.

## 명령별 입력과 결과

| 작업 | 핵심 입력 | 결과 |
| --- | --- | --- |
| 초기화 | 제품 요구 또는 기존 저장소, constitution, 기존 Spec Kit 자료 | Discovery Gate 판정, 확정 Feature의 spec·plan과 필요한 설계 자료, Baseline 6개 파일 |
| 개발 | 사용자 요청, Feature와 참조 문서, 현재 코드·계약 | 태스크, 코드와 테스트, 갱신된 매핑, 완료 검증 기록 |
| 외부 변경 동기화 | 비교 기준, 실제 변경, 승인된 의도, 승인 범위 | 승인된 산출물·Baseline 갱신 및 재검증 결과 |
| 버전 동기화 | 로컬 Core·Project·Skill 버전, 누적 변경 이력, 사용자 승인 | 필요한 메타데이터 변경 및 필수·품질 Gate 결과 |
| 사용자 Git 반영 전 검토 | 현재 앱·공식 문서·Baseline 변경과 검증 근거 | 영향 소견과 재검증 범위 |

## 01 산출물과 데이터 모델

SpecThread는 대상 프로젝트의 공식 Spec Kit 문서를 Feature의 원본으로 사용하고, 프로젝트 전체를 연결하는 정보는 `.specify/baseline/`에서 관리한다.

| 위치 | 책임 | 갱신 시점 |
| --- | --- | --- |
| 공식 constitution | 프로젝트 전체의 제약과 작업 원칙 | 사용자가 원칙을 정하거나 개정할 때 |
| Feature의 `spec.md` | 요구사항, 수용 시나리오와 성공 기준 | 초기화, 신규 Feature, 승인된 의도 변경 |
| `plan.md` 및 필요한 설계 산출물 | 구현 방식, 데이터, 인터페이스, 검증 방향 | 초기 설계 또는 변경 영향에 따라 |
| `tasks.md` | Feature 내부 구현 작업, 의존 순서, 체크 상태 | 실제 개발 단계 |
| `checklists/` | 작성된 요구사항의 품질 검토 | 적용 가능한 공식 스킬 단계 |
| 앱 코드, 계약, 테스트 | 실제 구현과 실행 근거 | 구현 및 검증 단계 |

### Baseline 여섯 파일

| 파일 | 최소 구조와 역할 |
| --- | --- |
| `project.md` | 목적, 범위, 제약, Discovery 범위·Gate 결과와 미확인 사항 |
| `architecture.md` | 구성 요소, 경계, 관계 및 계획·관찰의 구분 |
| `decisions.md` | 주요 판단, 근거, 승인 및 충돌 해결 기록 |
| `features.yaml` | `features[]`의 `id`, `name`, `status`, `spec_path`, `dependencies[]`와 Discovery 기록. 최상위 schema_version/analysis/path_redirects. 의존 항목은 `feature_id`, `type` |
| `source-map.yaml` | `mappings[]`의 `feature_id`, `sources[]`. 주요 구현·계약 파일의 프로젝트 상대 `path`. 폐기 매핑은 이력으로 보존하고 활성 계산에서 제외 |
| `work-items.yaml` | `work_items[]`의 `id`, `status`, `declared_features`, `actual_features`. 선택 참조는 `related_work_items`. 완료 시 `validation.status`, `fingerprint`, `evidence[].ref`; 완료 CLI가 `findings`도 기록 |

확정된 신규 Feature와 생성된 Work Item은 별도 UUID v7을 사용한다. 잠정 Feature는 이름과 초안 경로로 다루며 확정 목록에 등록하지 않는다. Feature는 지속되는 제품 기능의 정체성이고, Work Item은 기능 하나 이상에 걸친 변경 요청과 검증 이력이다. 최초 이름과 디렉터리 번호에 정체성을 묶으면 이름 변경과 병렬 작업에서 참조가 흔들리므로 ID를 불변으로 유지한다. 실제 동작의 Task ID는 공식 `tasks.md` 안에서 관리한다.

Source Map은 확정 Feature를 주요 구현·계약 파일 경로에 연결하는 파생 인덱스다. Greenfield에서 아직 확인할 소스가 없으면 빈 매핑이 가능하다. 경로가 이동하거나 매핑이 맞지 않으면 실제 코드와 공식 계약으로 다시 분석한다. 활성·폐기 Feature의 참조 보존과 아카이브는 아래 생명주기 계약을 따른다.

### Feature 생명주기와 아카이브

`features.yaml`은 `active`와 `retired` Feature를 모두 영구 보존한다. Feature UUIDv7은 삭제·변경·재사용하지 않으며 `spec_path`는 이동에 따라 갱신하는 위치 정보다. Feature의 활성·폐기 상태는 Work Item의 개발 완료 상태와 독립적이다.

1. 병합·분할·제거 시 폐기 이유, 후속 Feature UUID와 결정 근거를 추적한다. 후속 기능이 없으면 참조를 임의로 만들지 않는다. 기존 UUID를 새 개념에 재사용하지 않고 활성 Feature 사이의 의존 관계를 재평가한다.
2. 폐기 Feature의 공식 산출물은 활성 `specs/`에서 `docs/sdd/archive/`로 이동해 보존한다. 공식 파일의 의미와 내부 구성은 유지한다. SpecThread가 위치·참조·활성 대상 제외를 관리하며 공식 Spec Kit의 라이프사이클은 변경하지 않는다.
3. 이동할 때 `spec_path`, 활성 Feature 컨텍스트, 문서 내부 링크, 검증 증거 참조 등 영향받는 경로를 확인하고 필요한 참조를 갱신한다. 기존 Work Item의 Feature UUID와 실행 이력은 유지한다. 완료 이력의 과거 실행 사실과 Fingerprint는 변경하지 않고 현재 참조 해석·경로 연결의 유효성을 확인한다.
4. `retired` Feature는 새 개발 대상에서 제외한다. 과거 Source Map은 이력으로 보존하고 현재 영향도·활성 품질 범위 계산에서 제외한다. 과거 매핑의 소스가 현재 트리에 없다는 이유만으로 활성 범위의 검증을 실패시키지 않는다. 아카이브 산출물과 역사적 참조의 무결성은 별도로 검증한다.
5. 변경·이동·검증 실패 시 작업을 중단하고 현재 결과와 실패 범위를 보고한다. 사용자가 Git으로 복구한다. 자동 Git 복구와 실제 자료 이동은 설계 문서 작업에 포함되지 않는다.

### Baseline 스키마 식별

`schema_version`은 Baseline 데이터 구조를 식별하며 Core 배포 버전과 독립적이다. 확장 메타데이터는 `.specify/baseline/`에 둔다. Core는 읽을 수 있는 구조와 변환 규칙을 확인한다. 미지원 스키마 또는 필요한 변환 규칙이 없으면 동기화를 차단한다. 기존 Core 누적 마이그레이션 체계를 재사용하고 별도 릴리스·변환 엔진을 만들지 않는다.

Core 0.3.0은 `features.yaml` 최상위에 `schema_version: 1`, `analysis`, `features`, `path_redirects`를 저장한다. `analysis`는 status/unanalysed/inputs/evidence, Feature는 id/name/status/spec_path/dependencies와 `discovery`를 가진다. Discovery에는 plan/verdict/dependencies/analysis_hash/feature_hash/inputs/evidence를 기록한다. Feature 경로·상태·의존성 변경과 근거 파일 변경은 이전 분석을 무효화한다.

폐기 시 `retirement`에 reason/evidence/successors를 기록한다. `path_redirects`는 과거 specs 경로를 아카이브 경로로 연결해 불변 Work Item 증거 참조를 현재 위치에서 해석한다. `work-items.yaml`은 기존 필드에 gate_revisions/gate_results를 추가하며 다른 최상위 메타데이터도 보존한다. 새 구조로 변환할 때 기존 UUID와 완료 이력은 유지하고 분석·Gate 결과를 추정해 PASS로 만들지 않는다.

### 등록과 폐기 명령

`feature-register PLAN.json`은 READY인 신규 후보를 새 UUIDv7으로 등록한다. 계획에는 `feature`(name/spec_path/dependencies), 공식 spec·plan, `discovery`(mode/candidate/checks), 실제 `paths`와 `evidence`가 필요하다. 등록 뒤 `analysis-record`로 해당 Feature의 분석·의존성 근거를 확정해야 개발할 수 있다.

`feature-retire UUID PLAN.json`은 reason, evidence(로컬 결정 근거 파일), successors(UUID 배열), dependency_updates(활성 소비자 UUID별 새 dependencies 배열)를 받는다. 미종료 Work Item이 있거나 활성 소비자 의존 재평가가 빠졌으면 차단한다. 미리보기의 approval_hash를 검토하고 사용자 승인 후 `--confirm HASH`로 적용한다. 입력이 바뀌면 다시 승인받는다. 기본 아카이브 위치는 `docs/sdd/archive/<UUID>`다. 이동한 Markdown의 상대 링크와 해당 자료를 참조하는 링크·활성 Source Map을 갱신하고, 공식 활성 선택자가 폐기 기능을 가리키면 해제한다. 역사적 Work Item과 폐기 Source Map은 그대로 보존한다.

## 02 기준 정보와 충돌 정책

**설계 철학**은 개발 의도, 관찰된 구현, 실행 증거를 각각 추적하는 것이다. Spec Kit 원형을 유지하면 팀이 공식 도구의 요구사항·설계·구현 흐름과 업데이트를 재사용할 수 있다. SpecThread는 교차 Feature 추적, Work Item 이력, 검증 시점 고정과 로컬 버전 동기화 같은 프로젝트 전체의 빈틈을 담당한다.

| 질문 | 답을 결정하는 정보 | 차이가 있을 때 |
| --- | --- | --- |
| 어떤 동작이 필요한가 | constitution과 승인된 Feature 명세 | 영향과 개정안을 제시하고 의도 변경을 확인한다 |
| 어떤 방식으로 구현하기로 했나 | 계획, 계약, 데이터 모델과 결정 근거 | 변경된 계약과 영향받는 공식 산출물을 다시 검토한다 |
| 지금 어떻게 동작하나 | 현재 코드·계약, 사용자 Git 반영 전에는 검사한 파일 | 실제 관찰과 기대 동작의 차이를 보고한다 |
| 어떤 조건에서 확인했나 | 실행 결과, 검증 범위와 Fingerprint | 해당 입력의 변경과 필요한 재검증을 확인한다 |
| 어느 기능에 연결되나 | Baseline의 Feature·Source Map·Work Item | 원본을 대조해 필요한 매핑을 갱신한다 |

예를 들어 기존 앱이 완료된 할 일을 목록에서 숨기지만 승인된 명세가 표시를 요구한다면, 구현 차이 또는 별도 의도 변경으로 분류한다. 코드 관찰만으로 명세를 개정하면 회귀를 제품 정책으로 받아들일 수 있다. Baseline은 원본 연결과 판단 근거를 남긴다.

Brownfield Discovery는 현행 동작과 설계 의도를 별도로 확인한다. 근거가 없는 의도는 미확인으로 기록하고 새 기능은 명시적인 개발 요청에서 다룬다.

외부 변경은 사용자가 명시적으로 요청하는 `sdd-sync`의 대상이다. 비교 기준과 변경안을 제시하고 승인한 범위만 적용한다. 현재 승인과 적용 사이 입력 재확인은 스킬 지침으로 수행한다. 독립적인 승인 토큰과 트랜잭션은 구현되어 있지 않다.

## 03 초기 분석과 Discovery

`sdd-init`은 공식 설치 상태, constitution, 분석 범위와 기존 산출물을 먼저 확인한다.

| 경로 | 분석 순서 | 검증 초점 |
| --- | --- | --- |
| Greenfield | 공식 `specify`로 초기 명세 → 전체 업무 흐름 분석 → 잠정 Feature 분리 → 공식 `clarify`를 재사용하는 반복 상세화 → Discovery Gate → Feature 확정 | 업무 흐름, 요구사항·수용 시나리오와 Feature 경계의 일관성 |
| Brownfield | 소스·계약·설정·문서·테스트와 실행 근거로 기존 시스템 역공학 → 공식 Spec Kit 초기 명세 → 현행 동작과 설계 의도를 이해하는 Discovery → Gate 검증 | 관찰된 동작의 정확성, 명세와 실제 근거의 연결, 확인된 의도와 추론의 구분 |

Brownfield는 기존 시스템을 정확히 이해하는 데 우선순위를 둔다. 현행 분석에서 근거 없는 기능을 추가하거나 관찰된 동작을 승인된 의도로 승격하지 않는다. 기존 명세와 구현이 다르면 양쪽 근거와 미확인 사항을 기록한다. 새로 발견한 **현행 기능**은 분석에 추가한다. 신규 요구사항은 명시적인 후속 개발 요청에서 다룬다.

Discovery에서 공식 `specify`의 명세 생성과 `clarify`의 명확화 기능을 재사용한다. 기존 유효 명세는 재사용하고 필요한 경우 공식 개정 흐름을 따른다. 공식 명령마다 활성 경로를 확인하고 생성 호출이 다른 명세 또는 기존 파일을 덮어쓰지 않도록 한다. 기존 답변과 근거를 먼저 확인하고, 의미 있는 미확정 경계·요구사항·아키텍처 판단에만 사용자 확인을 요청한다. 공식 호출이 생성한 경로나 번호는 Harness의 영구 식별자가 아니다.

잠정 Feature는 이름과 초안 경로로 비교한다. 분리·통합 전후에 원본 명세의 요구사항, 수용 시나리오, 예외 및 계약을 결과 명세와 양방향으로 대조해 누락, 의미 변형, 충돌을 찾아 해결한다. 경계를 변경하면 의존관계도 재검토한다. 잠정 Feature는 영구 UUID나 Baseline의 확정 Feature/의존관계 레코드에 등록하지 않는다.

### Discovery Gate

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

#### 현재 Core 제출 계약

`sdd-core discovery-gate PLAN.json`은 `mode`(`greenfield` 또는 `brownfield`), `candidate`(잠정명 또는 초안 경로), `checks`를 받는다. 두 경로 모두 `scope`, `boundaries`, `requirements`, `spec_quality`를 제출하고, Greenfield는 `workflow`, Brownfield는 `current_behavior`를 추가한다. 각 점검에는 `status`(`verified`, `condition`, `blocked`)와 구체적인 `evidence`를 기록한다. 미해결 항목에는 `next_step`을 추가한다. 비핵심이라는 근거와 `critical: false`가 있는 `condition`만 조건부로 처리한다. Core의 출력은 후보, 판정, 미해결 항목이다. 이미 확정한 Feature는 기존 ID를 유지한다. 신규 후보에는 `--issue-id`로 READY가 확인될 때만 UUID가 반환된다.

### 초기 분석 상태와 개발 진입

프로젝트 분석 상태는 `not_started`, `partial`, `complete`로 구분한다. `complete`는 전체 초기 분석 완료를 의미한다. Feature별 개발 가능 여부는 프로젝트 분석 상태, 대상 Feature의 Discovery 판정과 핵심 의존성 근거로 매번 평가한다. 별도 개발 가능 플래그를 중복 저장하지 않는다.

| 조건 | 개발 진입 |
| --- | --- |
| `not_started` | 차단 |
| `partial` + 대상 `active` Feature의 Discovery `READY` + 미분석 영역과의 핵심 의존성 위험 없음이 검증됨 | 허용 |
| 대상 Discovery `CONDITIONAL` 또는 `BLOCKED`, 핵심 의존성 `UNKNOWN` 또는 `CONFLICT` | 해당 Feature 차단 |
| `complete` | 대상 Feature의 활성 상태·Discovery·의존성 및 적용 Gate를 확인한 뒤 허용. 모든 Feature의 개발을 자동 허용하지 않음 |

진입 판정은 기존 Baseline의 분석 기록·Feature·의존관계·Discovery 근거를 활용한다. 개발 범위가 확대되거나 관련 근거가 달라지면 영향 범위를 다시 평가한다. 전체 분석 완료를 선언하는 조건과 부분 분석 상태에서의 개발 진입은 각각 판단한다. Core 0.3.0의 `analysis-record`가 분석과 대상별 근거를 저장하며 `develop-check`가 현재 입력의 유효성과 대상·의존성 READY를 확인한다. start, in_progress 진입, Gate 실행과 완료에서도 이 조건을 검사한다.

### 초기화 완료와 재개

Gate를 통과한 Feature에 공식 계획과 필요한 설계 자료(`research.md`, `data-model.md`, `contracts/`, `quickstart.md` 등)를 작성하고 Baseline 여섯 파일을 검증한다. `scaffold`는 누락 파일의 틀을 만들고 기존 파일을 보존한다. 범위 내 Feature가 모두 확정되고 전체 조사와 의미 검토, 필요한 산출물 및 참조 검증을 마쳤으며 차단 소견이 없을 때 초기 분석을 완료한다. 새 `tasks.md`는 개발 때 만들고 기존 태스크는 보존한다. 초기화에는 적용 가능한 공식 명세 품질 검사, spec·plan 정합성과 Core 구조 검사를 조합한다. 태스크를 요구하는 `analyze`와 구현 이후의 `converge`는 각 전제가 갖춰진 단계에서 실행한다.

실패·중단 시 유효한 기존 산출물, 초안과 Markdown의 판단 근거를 보존한다. 재개하면 현재 파일, 분석 근거, Gate 조건, Baseline을 대조한다. 이미 검증한 범위와 UUID는 유지하고 누락·변경·조건부·차단 범위만 이어서 검증한다. 경계나 요구사항이 바뀌면 영향받은 분리·통합 검증과 Gate를 다시 평가한다. 충돌한 파일은 덮어쓰지 않고 판단을 요청한다. 초기 분석 완료와 최초 Git 반영은 별도 이정표다.

**실행 확인 범위**는 Codex Greenfield 데모와 Baseline 재검증이다. 최신 Discovery Gate, Brownfield 전수 분석, 부분 재개, 두 에이전트의 동등 결과는 추가 검증이 필요하다.

### 분석 기록의 CLI 계약

`analysis-record PLAN.json`은 status, unanalysed(범위 설명 배열), paths(실제 입력 파일), evidence(실제 증거 참조 배열), features(UUID별 분석 객체)를 받는다. 각 Feature 분석은 `discovery`(mode/candidate/checks)와 비어 있지 않은 `dependencies` 영향 판정 배열을 포함한다. 영향 판정은 assessment/evidence 및 필요한 critical을 기록한다. 전체 complete를 기록하려면 모든 활성 Feature의 근거가 준비돼 있어야 한다.

분석이 기록되는 features.yaml 자체를 입력으로 삼지 않고 원본 명세·계약·조사 자료를 지정한다. 입력·증거 해시, 분석 범위와 기능별 구조 해시가 현재 자료와 일치해야 유효하다. 다른 범위는 미분석으로 남겨도 되지만 대상의 핵심 의존 안전성을 근거로 검증해야 한다. 기록 후 `develop-check UUID ...`로 판정하며 실제 개발 가능 플래그는 저장하지 않는다.

## 04 개발 및 변경의 생명주기

초기 분석의 의미상 상태는 `not_started → partial → complete`다. [Discovery Gate](03-analysis-standard.md)는 잠정 Feature의 확정 가능성을 판정한다. 전체 초기 분석 완료에는 Feature 확정 외에도 공식 설계 산출물과 Baseline 검증이 필요하다.

### Work Item

| 전이 | 조건 |
| --- | --- |
| 생성 → `pending` | `sdd-core start UUID ...`로 대상 진입 조건 확인 후 신규 Work Item UUID 및 선언 Feature 목록 기록 |
| `pending` → `in_progress` | 개발 시작 |
| `in_progress` → `suspended` | 사용자 중단 또는 판단 대기 |
| `suspended` → `in_progress` | 현재 파일과 변경 범위를 확인하고 사용자 주도로 재개 |
| `in_progress` → `completed` | `complete` 게이트 통과와 검증 기록 저장 |
| `in_progress` → `failed` | 작업을 실패로 종료한다고 판단 |

복구 가능한 검증 실패는 `in_progress`에서 수정과 재검증으로 처리한다. 완료된 작업은 Core 전이 명령으로 재개할 수 없다. 후속 요청은 새 ID를 쓰고 필요한 경우 이전 Work Item을 참조한다. `failed`도 최종 종료 상태이며 재개하지 않는다. 실패한 작업의 재시도는 새 UUIDv7을 생성하고 `related_work_items`로 이전 실패 작업을 참조한다. Work Item 상태와 공식 태스크 체크, 프로세스 생존 여부, Git 커밋 여부는 각각 다른 사실이다.

### 개발 문서에서 코드로

1. `sdd-develop`이 [초기 분석 상태와 대상 개발 진입 조건](03-analysis-standard.md)을 확인한다. `not_started`는 차단하고 `partial`은 대상 활성 Feature의 READY와 핵심 의존성 위험 없음이 검증될 때 허용한다. `complete`에서도 대상 조건을 다시 확인한다. 선언 Feature와 실제 변경 Feature를 기록한다. 신규 Feature가 필요하면 명세와 경계를 확정한 뒤 새 UUID를 부여한다. 잠정 Feature는 선언·실제 변경 Feature 목록에 등록하지 않는다.
2. [필수 Gate 정의와 실행 계약](06-verification.md)에 따라 개발·검증 진입 전에 적용 집합과 근거를 확정한다. 변경 의도에 따라 공식 스킬로 spec과 plan을 개정·보완한다. 기존 산출물에 신규 생성 단계를 실행하면 덮어쓸 수 있으므로 개정 흐름을 사용한다.
3. 공식 `tasks`는 명세, 계획 및 적용 가능한 설계 산출물로 작업을 생성한다. 필요한 경우 `analyze`로 spec·plan·tasks 사이 누락·중복·충돌을 점검한다.
4. 에이전트는 공식 `implement` 지침과 작업 순서에 따라 실제 코드와 검증을 작성한다. 요구사항이 달라지면 해당 공식 산출물을 수정하고 이어간다. 적용 가능한 `converge`가 격차를 추가 작업으로 기록하면 구현과 검증을 다시 진행한다.
5. 모든 적용 필수 Gate가 유효한 PASS일 때만 완료한다. FAIL·NOT_RUN·UNKNOWN·STALE과 증거 부족은 해당 후속 단계와 완료를 차단한다. 관계와 Source Map을 단계 경계에서 정리한다. 최종 실행 결과, 증거와 Fingerprint를 기록한다. Git 반영은 사용자가 수행한다.

`sdd-sync`는 외부 변경을 재발견하는 복구 흐름이다. 변경 계획과 승인 범위가 개발 의도라면 공식 산출물도 적절한 절차로 개정한다. 비교 기준 저장과 승인 강제 방식은 열린 과제다.

실패한 요청의 재시도는 `start FEATURE_UUID ... --related FAILED_WORK_UUID`로 연결한다. `in_progress`로 진입하기 전에 적용 Gate 집합을 확정하고 develop 필수 Gate를 통과해야 한다. 검증 진입에는 `stage-check ID verify`, 완료 직전에는 `stage-check ID complete`를 사용한다. 각 결과는 현재 파일·정의·증거로 재평가한다. Core 0.3.0은 종료된 작업의 Gate 결과와 정의 수정도 거부한다.

작업 범위 확대는 `scope-expand ID PLAN.json`의 features(추가 확정 UUID)와 reason으로 기록한다. 기존 선언 범위를 보존하며 확대 후에는 새 범위의 Gate 집합을 다시 검토해야 한다.

## 05 영향 분석과 위험도

영향 분석은 의미 판단이다. Baseline 인덱스는 후보를 빠르게 좁히고 실제 계약·구현 및 테스트가 판단의 근거를 제공한다.

현재 영향도 계산은 활성 Feature와 현재 계약을 대상으로 한다. 폐기 Feature의 과거 Source Map은 이력으로 보존한다. 병합·분할 후 활성 의존관계를 재평가하며, 부분 분석 상태의 개발 진입은 미분석 영역과의 핵심 의존성 위험 없음까지 확인한다.

1. 요청의 선언 Feature와 실제 변경 파일, 계약의 전후 동작을 대조한다.
2. 변경 Feature에 의존하는 직접 소비자를 확인한다. 해당 계약의 영향이 계속 전파되는 경우 다음 의존 단계까지 진행한다. 영향이 없다는 근거가 생긴 경계에서 멈춘다.
3. 여러 의존과 실제 순환을 표현할 수 있다. 이미 방문한 관계는 반복 조사하지 않는다. 순환 자체는 경고이고 중대한 계약·장애 위험이 확인될 때 차단한다. 역방향 간선은 정방향 관계로부터 계산하는 설계다.
4. 구현·계약 파일을 찾지 못하면 계약·호출부·테스트와 공식 산출물을 추가 조사한다. 근거와 검증 대상 범위를 기록하고 실제 변경과 재검증이 필요한 간접 영향 범위를 구분한다.

| 판정 | 조건과 처리 |
| --- | --- |
| `SAFE` | 변경 또는 영향 없음의 근거를 기록하고 필요한 범위 확장을 진행한다 |
| 비핵심 `UNKNOWN` | 추가 조사 후 남은 제한을 근거와 함께 기록한다. 완료 및 통합 단계에서 허용 가능 |
| 핵심 `UNKNOWN` | 공개 계약, 보안, 데이터 무결성 등 중요한 판단의 근거가 부족하다. 해결 전 차단하며 사용자 승인만으로 통과시키지 않는다 |
| `CONFLICT` | 의도·구현 또는 통합 변경 사이의 실제 충돌이다. 해결하고 재검증한다 |

예를 들어 저장 API의 반환 형식을 바꾸면 호출부의 파싱과 실패 처리를 검사한다. 어댑터가 동일한 외부 반환 계약을 유지한다는 근거를 찾았다면 그 지점에서 전파를 멈출 수 있다. 테스트 부재만으로 영향이 없다고 판단할 수는 없다.

이 판정은 변경의 위험도를 평가한다. Feature 확정은 [Discovery Gate](03-analysis-standard.md)에서 다룬다.

현재 Core는 제출된 `findings`의 판정·근거를 확인하고 차단 값에 실패한다. 영향 그래프 탐색, 중요도 판정, 누락된 소견 식별은 에이전트의 책임이다.

## 06 검증과 정합성

| 검증 | 질문 | 실행 주체 |
| --- | --- | --- |
| Discovery Gate | 분리·통합 전후에 요구사항, 예외 및 계약이 보존되는가. Brownfield 명세는 현행 근거와 맞는가 | 에이전트의 의미 검토와 공식 명세 품질 검사 |
| 명세 품질 | 요구사항이 명확하고 측정 가능한가 | 공식 체크리스트 흐름. 사용자 정의 체크리스트의 검토 상태는 검토자가 관리 |
| 산출물·구현 분석 | 명세→계획→작업→구현이 일치하는가 | 에이전트가 공식 `analyze`·`converge`를 전제에 맞게 사용 |
| 동작 | 프로젝트 테스트·빌드·정적 검사가 통과하는가 | 프로젝트 검증 명령 |
| 구조 | UUID, 상태, 경로, 참조가 유효한가 | `sdd-core validate` |
| 사용자 반영 전 검토 | 반영하려는 변경이 검증 입력과 일치하는가 | 사용자 검토와 기존 검사 |

Core 0.3.0의 완료 명령은 저장된 필수 Gate 집합과 실행 결과를 대조한다. 임시 complete 계획의 임의 검사 명령으로 이를 대체할 수 없다. 모든 필수 결과가 현재 유효한 PASS이고 실제 증거·영향 근거가 있어야 completed를 저장한다.

**사용자 통합 후 검증**은 통합 결과로 검증 입력이 달라지면 기존 검사와 영향 분석을 다시 실행한다. Work Item의 과거 통과 근거는 원래 입력의 이력으로 유지한다.

### 필수 Gate 정의와 실행 계약

SpecThread Skill은 기존 설계·프로젝트 검증 규칙·Feature와 Work Item 특성을 분석하고 개발·검증 단계 진입 전에 적용할 필수 Gate 집합을 확정한다. 필수 집합의 정의와 실행 결과는 각각 기록한다.

| 기록 | 최소 내용 |
| --- | --- |
| Gate 정의 | Gate ID, 검증 대상, 실행 명령 또는 검증 방법, 필수 여부, 증거 요구사항 |
| 적용 근거·변경 이력 | 해당 작업에 필요한 이유, 적용 범위, 목록 또는 정의가 달라진 근거와 변경 내역 |
| 실행 결과 | Gate ID에 대응하는 판정, 실제 실행 결과, 실행 명령의 종료 코드, 대상, 증거 참조 및 관련 입력 Fingerprint |

Core는 확정된 정의의 구조·일관성·적용 결과의 대응·증거와 완료 조건을 결정론적으로 검증한다. 필수 목록의 임의 누락·축소로 우회하지 못하도록 적용 근거와 변경 이력을 대조한다. 의미적으로 충분한 검사인지 판단하고 근거를 수집하는 책임은 Skill에 있다.

기존 Spec Kit 명령과 프로젝트의 테스트·빌드·정적 분석을 재사용한다. 실행 명령 없이 공식 검토 방법을 쓰는 경우에도 그 방법에 맞는 실제 결과와 증거를 요구한다. 별도 중복 테스트 엔진은 추가하지 않는다.

| 필수 Gate 결과 | 후속 단계 및 완료 |
| --- | --- |
| `PASS` | 해당 정의·대상·입력에 유효한 증거가 있을 때 통과 |
| `FAIL`, `NOT_RUN`, `UNKNOWN`, `STALE` | 해당 Gate가 요구되는 후속 단계와 `completed` 전환 차단 |

모든 적용 가능한 필수 Gate가 유효한 `PASS`여야 완료한다. 증거 경로는 존재와 유효성을 확인하며 과거 Git 근거는 해당 역사적 기준에서 해석한다. 임의 성공 명령이나 성공 문자열만으로 필수 Gate를 충족했다고 판정하지 않는다.

코드·공식 산출물·필수 Gate 정의가 바뀌면 관련 PASS의 현재 유효성을 재평가한다. 무효화되면 재검증한다. 과거 `completed` 이력과 당시 결과는 보존하고 후속 작업에서 사용할 현재 근거인지 판단한다. Gate 결과는 Work Item 상태와 독립적이며 별도 Work Item 상태를 추가하지 않는다.

Core 0.3.0은 Gate 정의를 work-items.yaml의 `gate_revisions`, Gate별 실행 이력을 `gate_results`에 저장한다. 정의 변경은 기존 이력을 보존하고 새 정의 해시로 이전 결과를 무효화한다. 완료 이력의 결과는 수정하지 않으며 stage-check에서 현재 유효성만 판단한다. 의미적 검사 충분성은 Skill이 검토한다.

### Core 0.3.0 명령과 입력 예시

`gates ID PLAN.json`으로 집합을 미리 보고 검토한 해시를 `--confirm HASH`로 확정한다. 계획은 아래처럼 작성한다. paths는 실제 검사 입력을 명시하며 신규 구현 예정 파일은 정의 시점에 없어도 실행 시에는 존재해야 한다. basis는 실제 검증 규칙·적용 근거 파일이다.

```json
{
  "reason": "변경 계약에 프로젝트 테스트 규칙 적용",
  "basis": ["verification-rules.md"],
  "gates": [{
    "id": "project-tests",
    "rationale": "변경 Feature의 계약과 예외를 확인",
    "targets": ["019a1234-5678-7abc-8def-123456789abc"],
    "required": true,
    "required_for": ["complete"],
    "kind": "command",
    "command": ["python", "-m", "unittest", "discover", "-s", "tests"],
    "paths": ["app.py", "tests/test_app.py"],
    "evidence": ["test-results.txt"],
    "evidence_requirement": "기존 테스트 도구가 보존한 실제 결과 보고서"
  }]
}
```

예시 명령·경로는 프로젝트의 실제 검사와 결과 보존 방식으로 교체한다. 표준 출력·오류·종료 코드는 기존 검사 실행기가 수집한다. evidence 파일의 존재·내용 해시와 입력 해시를 확인하며 검사 중 파일 또는 Work Item/Gate 계약이 바뀌면 결과 확정을 차단한다.

- `gate-run ID GATE_ID`는 등록된 command만 실행하고 결과를 누적한다. 임시 명령이나 외부 PASS로 command Gate를 대체할 수 없다.
- 공식 Spec Kit 검토는 `kind: review`, `method`, 실제 evidence 보고서를 정의한 뒤 `gate-run ID GATE_ID --review REVIEW.json`으로 결과를 기록한다. REVIEW는 status(PASS/FAIL/UNKNOWN/NOT_RUN), reviewer, conclusion을 포함한다.
- `stage-check ID develop|verify|complete`는 해당 단계와 앞 단계의 필수 Gate를 검사한다. complete에서는 모든 required Gate가 PASS여야 한다.
- `complete ID PLAN.json`은 actual_features, 비어 있지 않은 findings, 실제 evidence[].ref를 받는다. 선언 범위를 초과한 변경은 반영 전에 작업 범위와 Gate 집합을 다시 검토해야 한다.

최신 실행이 FAIL 또는 UNKNOWN이면 과거 PASS로 대체하지 않는다. 관련 입력·증거·Gate 정의가 바뀐 PASS는 STALE이다. 실제 명령의 의미적 적절성과 검토 보고서의 충분성은 Skill이 근거로 판단한다.

## 07 에이전트와 Core의 역할

| 작업 | Codex | Claude Code |
| --- | --- | --- |
| 설치 위치 | `.agents/skills/<이름>/SKILL.md` | `.claude/skills/<이름>/SKILL.md` |
| 초기화 | `$sdd-init` | `/sdd-init` |
| 개발 | `$sdd-develop` | `/sdd-develop` |
| 외부 변경 정합화 | `$sdd-sync` | `/sdd-sync` |

공식 GitHub Spec Kit는 독립 설치한다. 문서 재현 기준은 v1.4.0이다. `sdd-core install-skills codex|claude`는 공통 절차를 각 폴더에 설치하고 같은 위치에 내용이 다른 스킬과 충돌하면 오류를 보고한다. 기존 공식 설치를 교체할 필요가 없다.

에이전트가 Discovery에서 공식 `specify`와 `clarify`를 사용해 분석하고 근거를 제출한다. Core의 `discovery-gate`는 입력 형식과 필수 점검을 검사해 판정하며, 신규 Feature에는 `--issue-id`로 READY에서만 UUID를 발급한다. Skill이 적용 필수 Gate 집합과 변경 근거를 확정하고 Core가 정의·결과·증거의 대응과 완료 조건을 검사한다. 의미적 검사 충분성은 Skill이 판단한다. 에이전트는 공식 스킬과 템플릿을 사용하고, 대상 Feature의 경로를 확인하며, 문서 작성·코드 구현·의미 분석·사용자 안내를 수행한다. 공통 CLI가 구조·상태·검증 명령과 입력 동일성을 점검한다. 이 구조는 에이전트가 달라도 한 가지 완료 규칙을 사용할 수 있게 한다.

프로젝트별 에이전트 선택과 Worktree 생성·분배·중단·재개는 사용자 책임이다. 중앙 세션 관리자, 잠금, 대기열, SQLite, 실시간 감시는 설계 범위 밖이다. Codex에서 초기화와 개발을 실행 확인했다. Claude Code는 스킬 설치 형태를 확인했으며 동일한 종단간 실행 검증이 남아 있다.

## 08 사용자 Git 운영과 Core 버전 동기화

사용자가 세션과 작업 분배, Commit·Push·Merge·Rollback을 맡는다. Worktree는 선택 사항이다. 사용자 통합으로 검증 입력이 바뀌면 기존 검사를 다시 실행한다. 제품 저장소의 PR과 설계 릴리즈는 [두 Git 저장소의 운영](08-git-integration.md)을 따른다.

사용자가 Core를 내려받아 교체하면 다음 Harness 명령에서 로컬 Core·Project·Skill 버전을 비교한다. 불일치는 영향 분석, 사용자 승인, 필요한 메타데이터 변환, 필수 Gate와 품질 Gate 순으로 처리한다. 필수 실패 시 사용자가 원복한 뒤 처음부터 다시 시도한다. Core 0.3.0의 `version-check`와 `version-sync`를 사용한다. 승인 해시와 기존 검사 계획의 형식은 [Core 버전 동기화](version-sync.md)를 참고한다.

## 검증 운영 예시

먼저 적용 Gate를 등록하고 gate-run으로 검증한다. 완료 계획은 임시 JSON으로 전달한다. 아래 예에서 경로와 명령은 대상 프로젝트에 맞게 바꾼다. 배열 안의 명령은 셸 문자열이 아닌 실행 파일과 인자 목록이다. 파일에 저장된 Feature UUID를 실제 값으로 바꿔 실행한다.

```json
{
  "actual_features": ["019a1234-5678-7abc-8def-123456789abc"],
  "findings": [
    {"assessment": "SAFE", "evidence": "완료 계약과 소비자 동작을 검증했다", "critical": false}
  ],
  "evidence": [{"ref": "tests/todo-browser.mjs"}]
}
```

검사 실패 시 현재 작업을 보존하고 원인을 수정해 다시 실행한다. 검사가 입력 파일을 변경해 Fingerprint가 달라지는 경우에도 완료 판정이 보류된다. 사용자가 통합한 내용에 추가 변경이 있으면 영향과 검증 입력을 다시 확인한다. 예를 들어 공유 API가 바뀌면 소비자의 계약 호환성을 기존 검사로 검증한다.

## 현재까지 검증한 범위

| 확인 대상 | 상태 |
| --- | --- |
| Codex Greenfield 초기화와 개발 | 샘플 프로젝트에서 실행 확인. 최신 Discovery Gate의 종단간 검증은 남아 있음 |
| 공통 CLI와 설치된 스킬 파일 | 두 에이전트의 프로젝트 경로에 설치 확인 |
| Claude Code에서 초기화와 개발을 처음부터 끝까지 실행 | 검증 예정 |
| Brownfield·다중 Feature 및 Sync 승인으로 실제 프로젝트 정합화 | 검증 예정 |
| 초기화 완료·승인 증표, 선택적 재검증 | 각각 스킬 절차 또는 설계 정책으로 남음 |

[통합 상세 설계서](SpecThread-통합-상세-설계서.md) · [결정 기록](DECISIONS.md) · [검증 및 미결정 백로그](OPEN-ISSUES.md)

공식 기능은 [Spec Kit v1.4.0](https://github.com/github/spec-kit/releases/tag/v1.4.0), [analyze 템플릿](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/analyze.md), [converge 템플릿](https://raw.githubusercontent.com/github/spec-kit/v1.4.0/templates/commands/converge.md)을 재현 기준으로 사용했다.
