# 01 산출물과 데이터 모델

SpecThread는 대상 프로젝트의 공식 Spec Kit 문서를 Feature의 원본으로 사용하고, 프로젝트 전체를 연결하는 정보는 `.specify/baseline/`에서 관리한다.

| 위치 | 책임 | 갱신 시점 |
| --- | --- | --- |
| 공식 constitution | 프로젝트 전체의 제약과 작업 원칙 | 사용자가 원칙을 정하거나 개정할 때 |
| Feature의 `spec.md` | 요구사항, 수용 시나리오와 성공 기준 | 초기화, 신규 Feature, 승인된 의도 변경 |
| `plan.md` 및 필요한 설계 산출물 | 구현 방식, 데이터, 인터페이스, 검증 방향 | 초기 설계 또는 변경 영향에 따라 |
| `tasks.md` | Feature 내부 구현 작업, 의존 순서, 체크 상태 | 실제 개발 단계 |
| `checklists/` | 작성된 요구사항의 품질 검토 | 적용 가능한 공식 스킬 단계 |
| 앱 코드, 계약, 테스트 | 실제 구현과 실행 근거 | 구현 및 검증 단계 |

## Baseline 일곱 파일

| 파일 | 최소 구조와 역할 |
| --- | --- |
| `project.md` | 목적, 범위, 제약, Discovery 범위·Gate 결과와 미확인 사항 |
| `architecture.md` | 구성 요소, 경계, 관계 및 계획·관찰의 구분 |
| `decisions.md` | 주요 판단, 근거, 승인 및 충돌 해결 기록 |
| `features.yaml` | `features[]`의 `id`, `name`, `status`, `spec_path`, `dependencies[]`와 Discovery 기록. 최상위 schema_version/analysis/path_redirects. 의존 항목은 `feature_id`, `type` |
| `source-map.yaml` | `mappings[]`의 `feature_id`, `sources[]`. 주요 구현·계약 파일의 프로젝트 상대 `path`. 폐기 매핑은 이력으로 보존하고 활성 계산에서 제외 |
| `verification.yaml` | 재사용 검증 정의. schema_version 1, status/reason/basis, project.gates와 features.UUID.gates. [스키마 원본](verification-profiles.md) |
| `work-items.yaml` | `work_items[]`의 `id`, `status`, `declared_features`, `actual_features`. 선택 참조는 `related_work_items`. 완료 시 `validation.status`, `fingerprint`, `evidence[].ref`; 완료 CLI가 `findings`도 기록 |

Source Map은 확정 Feature를 주요 구현·계약 파일 경로에 연결하는 파생 인덱스다. Greenfield에서 아직 확인할 소스가 없으면 빈 매핑이 가능하다. Core의 Source Map 검증은 과거 파일의 추가 메타데이터를 읽을 수 있다. 구버전 경로 정규화는 [승인된 버전 동기화](version-sync.md)에서 수행한다. 경로가 이동하거나 매핑이 맞지 않으면 실제 코드와 공식 계약으로 다시 분석한다. 활성·폐기 Feature의 참조 보존, 등록·폐기 명령과 아카이브는 [Feature 생명주기](feature-lifecycle.md)를 따른다.

## Baseline 스키마 식별

`schema_version`은 Baseline 데이터 구조를 식별하며 Core 배포 버전과 독립적이다. 확장 메타데이터는 `.specify/baseline/`에 둔다. Core는 읽을 수 있는 구조와 변환 규칙을 확인한다. 미지원 스키마 또는 필요한 변환 규칙이 없으면 동기화를 차단한다. 기존 Core 누적 마이그레이션 체계를 재사용하고 별도 릴리스·변환 엔진을 만들지 않는다.

Core 0.5.0은 `features.yaml` 최상위에 `schema_version: 1`, `analysis`, `features`, `path_redirects`를 저장한다. `analysis`는 status/unanalysed/inputs/evidence, Feature는 id/name/status/spec_path/dependencies와 `discovery`를 가진다. Discovery에는 plan/verdict/dependencies/analysis_hash/feature_hash/inputs/evidence를 기록한다. Feature 경로·상태·의존성 변경과 근거 파일 변경은 이전 분석을 무효화한다.

`work-items.yaml`은 verification.revisions/steps에 프로파일 분류·상향과 공식 절차 수행을, gate_revisions/gate_results에 해당 작업의 정의·실행을 저장하며 다른 최상위 메타데이터도 보존한다. 새 구조로 변환할 때 기존 UUID와 완료 이력은 유지하고 분석·Gate 결과를 추정해 PASS로 만들지 않는다.

## 식별자와 범위 해석

확정된 신규 Feature와 생성된 Work Item은 UUIDv7을 독립 발급한다. 잠정 Feature는 이름과 초안 경로로 다루며 확정 목록에 등록하지 않는다. Feature는 지속되는 제품 기능의 정체성이고 Work Item은 기능 하나 이상에 걸친 변경 요청과 검증 이력이다. 최초 이름과 디렉터리 번호에 정체성을 묶으면 이름 변경과 병렬 작업에서 참조가 흔들리므로 ID를 불변으로 유지한다. 실제 Task ID는 공식 `tasks.md` 안에서 관리한다. ID는 공식 디렉터리 번호·슬러그·브랜치명과 별개이며 이름 변경만으로 경로를 자동 변경하지 않는다. 중복 UUID는 구조 오류로 식별하고, 서로 다른 UUID의 동일 Feature·경로 등록은 의미 검토에 보낸다. 구현이 없는 Feature에는 가상의 소스 참조를 생성하지 않는다.

Work Item 하나에 여러 Feature가 연결될 수 있다. 선언 범위는 시작 시 예상, 실제 범위는 변경이 확인된 Feature다. 관찰·재검증만 필요한 영향 Feature와 실제 수정 Feature를 구분한다. `related_work_items`는 관련 작업 UUID 참조다. 실패 재시도와 범위 확대 절차는 [Work Item 생명주기](04-artifact-lifecycle.md)에 둔다.

의존 유형의 초기 예시는 `api`, `data`, `event`, `runtime`이다. 그래프 해석과 전파·중단 판단은 [영향 분석](05-impact-analysis.md)을 따른다.

태스크 내용·상세 로그·중간 분석 그래프를 Baseline에 복사하지 않는다. 최종 영향 판정과 근거, 사용자 결정, 차단 소견을 남긴다. Core는 UUID 형식·중복, 참조 존재, 공식 산출물 경로, 상태 값, 증거와 Fingerprint의 형식·참조 일관성을 검사한다. 파일 매핑의 의미와 계약의 실제 동작은 에이전트가 근거로 판단한다.

## YAML 레코드 예시

Markdown에는 서술 규칙만 적용한다. 아래 YAML은 합의된 최소 예시를 엮은 것이다. 64자리 해시는 형식 예시다. 아래 예시는 레코드 구조를 설명하며 실제 개발에는 analysis-record와 필수 Gate 정의·결과가 추가로 필요하다.

```yaml
# features.yaml
schema_version: 1
analysis:
  status: not_started
  unanalysed: []
path_redirects: {}
features:
  - id: "019a1234-5678-7abc-8def-123456789abc"
    name: document-parsing
    status: active
    spec_path: specs/001-document-parsing
    dependencies:
      - feature_id: "019a1234-5678-7abc-8def-123456789abd"
        type: api
  - id: "019a1234-5678-7abc-8def-123456789abd"
    name: document-storage
    status: active
    spec_path: specs/002-document-storage
    dependencies: []
```

```yaml
# source-map.yaml
mappings:
  - feature_id: "019a1234-5678-7abc-8def-123456789abc"
    sources:
      - path: src/parser/service.py
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

## Core 0.5.0 직렬화·쓰기 계약

이 절은 현재 구현의 재현 계약이다. 임의로 새 저장 구조를 추정하지 않고 다음 형식을 사용한다.

| 저장 객체 | 필드와 자료형 |
| --- | --- |
| `analysis` | status 문자열, unanalysed 문자열 배열, inputs·evidence는 `{프로젝트 상대 경로 또는 증거 ref: SHA-256 64자리 소문자 hex}` |
| Feature `discovery` | plan(제출 Discovery 객체), verdict, dependencies(판정 배열), analysis_hash·feature_hash(`sha256:` 접두 해시), inputs·evidence(해시 매핑) |
| Work Item | id·status, declared_features·actual_features·related_work_items(UUID 배열), scope_changes(확대 전후 from/to와 reason), gate_revisions(배열), gate_results(Gate ID → 실행 배열) |
| Work Item `validation` | status=`passed`, fingerprint, evidence(각 항목 `{ref: 문자열}`), gate_status(완료 시 Gate별 id/status 배열). 아래 YAML의 요약 예시는 전체 Gate 기록을 대신하지 않음 |

JSON 객체 내용 해시는 `json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))`를 UTF-8로 인코딩해 SHA-256을 구한 뒤 `sha256:`를 붙인다. 입력 파일 해시는 파일 바이트 자체의 SHA-256이며 접두 없이 64자리 hex로 저장한다. Feature 구조 해시는 id/status/spec_path/dependencies만 가진 객체, 분석 해시는 저장된 analysis 객체를 대상으로 한다. Gate 해시의 대상은 [검증 계약](06-verification.md)에 정의한다.

관리 YAML은 중복 키·문자열이 아닌 키를 거부한다. UUID는 소문자 표준 UUIDv7이며 Feature와 Work Item 사이에도 중복할 수 없다. 경로는 정규화한 프로젝트 상대 POSIX 경로다. 절대 경로·`..`·프로젝트 밖으로 해석되는 경로는 거부한다. YAML 관리 파일은 심볼릭 링크로 쓰지 않는다. 현재 YAML 쓰기는 같은 폴더의 임시 파일에 직렬화한 뒤 파일 단위로 교체하며, 여러 파일의 트랜잭션·자동 원복을 의미하지 않는다.

`validate`는 스키마·참조와 필수 파일을 검사한다. 이것만 통과했다고 Discovery·Gate 의미 검토 또는 개발 진입이 완료된 것은 아니다. 활성 Feature의 spec_path에는 spec.md·plan.md가 필요하고 현재 의존성은 활성 Feature만 참조한다. Source Map은 Feature당 한 레코드이며 활성 매핑의 파일은 존재해야 한다. completed의 과거 증거는 현재 트리에 없을 수 있으므로 구조 검사와 새 실행의 증거 검사를 구분한다.

## Core 0.5.0 추가 기록

features.yaml의 schema_version 1을 유지하며 verification.yaml을 일곱 번째 Baseline 파일로 추가한다. 정합화 Work Item은 kind=reconciliation과 reconciliation(approval_hash/base/inputs/reason/findings/changes, 적용 실패 시 error)을 추가한다. Gate 결과 이관은 선택적인 reused_from(work_item/gate/run_index/definition_hash)을 추가한다. [수동 Sync](reconciliation.md)와 [검증](06-verification.md)이 생성·완료·이관 조건의 원본이다. 기존 완료 기록은 변환·재작성하지 않는다.

통합 설치는 기존 Project 표식에 runner_hash를 추가하고 .specify/sdd-core 및 .specify/spec-thread-install.json을 관리한다. 이는 Baseline 일곱 파일과 별개의 설치 자료이며 [설치 계약](installation.md)이 위치·생성·검증의 원본이다.


Core 0.5.0의 verification.revisions는 profile/reason/risks/conditions/considerations/required_steps/scope/findings/basis/previous/item_hash/approval_required/approval_reasons/approval_mode/preview_hash/hash를 누적한다. steps는 공식 절차 이름별 실제 수행 이력 배열(status/step/conclusion/recorded_at/evidence, 선택 inputs/source/elapsed_seconds)이다. 새 기록은 저장 구조·참조와 단조 상향을 검사하며 과거 완료 Work Item에 이 필드를 추정 삽입하지 않는다. Gate 스냅샷의 policy_sources는 정의의 출처이고 실행 결과의 reused_from은 결과의 원본이다. 직렬화·절차 의미는 [프로파일 계약](verification-profiles.md)을 따른다.

## 산출물 재사용과 최소 수정

No Change No Write, Reuse First, Single Source of Truth, Minimal Edit, No Extra Report를 적용한다. 공식 필수 생성·수정 계약이 우선이며 기존 구조·요구사항 식별 체계를 보존하고 관련 절·참조만 갱신한다.

| 산출물 | 생성·수정이 필요한 정보 변화 |
| --- | --- |
| spec.md / plan.md | 신규 Feature·요구사항 / 신규 Feature·기술 설계 |
| tasks.md | 현재 구현 작업·필수 선행 관계·완료 체크 |
| research.md / data-model.md / contracts | 새 조사·기술 결정 / 데이터 모델 / 인터페이스 계약 |
| quickstart.md | 실행·검증 방법 |
| checklists / Discovery | 기존 공식·검증 정책 / Discovery 적용 조건 |
| architecture.md / project.md / decisions.md | 전역 구조 / 프로젝트 정보 / 기록할 설계 결정 |
| Baseline | 실제 관리정보 변경. 상태·범위·관계 등은 필요한 시점에 즉시 반영 |

기존 Work Item·findings·Evidence·공식 산출물로 충분하면 별도 구현 완료·테스트 요약·영향·요구 충족·변경 요약 보고서나 Plan 중복 문서를 생성하지 않는다. 공식 절차·프로젝트 정책·사용자가 별도 보고서를 요구하면 예외다. 무관한 문구 정리·스타일 변경·전체 재작성·형식적 파일 수정도 하지 않는다. [분석 사실 재사용](05-impact-analysis.md)과 현재 Gate PASS 재사용은 구분한다.

## 동시 저장과 작업 사본

[병렬 개발](parallel-development.md)의 Runtime은 원본 밖에 두며 기존 Baseline schema_version 1을 유지한다. 관리 YAML은 레코드별 3방향 CAS, 관리 Markdown은 expected_hash, Source Map은 base/updated로 저장한다. 신규 Work 통합 메타데이터는 기존 레코드의 integration에 부가하고 Gate 결과의 input_modes/execution_context/retained_evidence는 선택 필드다. 과거 기록의 PASS·UUID를 임의 생성/변경하지 않는다. Snapshot은 파일의 실제 바이트·모드·디렉터리를 보존한다.
