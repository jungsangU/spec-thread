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

## Baseline 여섯 파일

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

## Feature 생명주기와 아카이브

`features.yaml`은 `active`와 `retired` Feature를 모두 영구 보존한다. Feature UUIDv7은 삭제·변경·재사용하지 않으며 `spec_path`는 이동에 따라 갱신하는 위치 정보다. Feature의 활성·폐기 상태는 Work Item의 개발 완료 상태와 독립적이다.

1. 병합·분할·제거 시 폐기 이유, 후속 Feature UUID와 결정 근거를 추적한다. 후속 기능이 없으면 참조를 임의로 만들지 않는다. 기존 UUID를 새 개념에 재사용하지 않고 활성 Feature 사이의 의존 관계를 재평가한다.
2. 폐기 Feature의 공식 산출물은 활성 `specs/`에서 `docs/sdd/archive/`로 이동해 보존한다. 공식 파일의 의미와 내부 구성은 유지한다. SpecThread가 위치·참조·활성 대상 제외를 관리하며 공식 Spec Kit의 라이프사이클은 변경하지 않는다.
3. 이동할 때 `spec_path`, 활성 Feature 컨텍스트, 문서 내부 링크, 검증 증거 참조 등 영향받는 경로를 확인하고 필요한 참조를 갱신한다. 기존 Work Item의 Feature UUID와 실행 이력은 유지한다. 완료 이력의 과거 실행 사실과 Fingerprint는 변경하지 않고 현재 참조 해석·경로 연결의 유효성을 확인한다.
4. `retired` Feature는 새 개발 대상에서 제외한다. 과거 Source Map은 이력으로 보존하고 현재 영향도·활성 품질 범위 계산에서 제외한다. 과거 매핑의 소스가 현재 트리에 없다는 이유만으로 활성 범위의 검증을 실패시키지 않는다. 아카이브 산출물과 역사적 참조의 무결성은 별도로 검증한다.
5. 변경·이동·검증 실패 시 작업을 중단하고 현재 결과와 실패 범위를 보고한다. 사용자가 Git으로 복구한다. 자동 Git 복구와 실제 자료 이동은 설계 문서 작업에 포함되지 않는다.

## Baseline 스키마 식별

`schema_version`은 Baseline 데이터 구조를 식별하며 Core 배포 버전과 독립적이다. 확장 메타데이터는 `.specify/baseline/`에 둔다. Core는 읽을 수 있는 구조와 변환 규칙을 확인한다. 미지원 스키마 또는 필요한 변환 규칙이 없으면 동기화를 차단한다. 기존 Core 누적 마이그레이션 체계를 재사용하고 별도 릴리스·변환 엔진을 만들지 않는다.

Core 0.3.0은 `features.yaml` 최상위에 `schema_version: 1`, `analysis`, `features`, `path_redirects`를 저장한다. `analysis`는 status/unanalysed/inputs/evidence, Feature는 id/name/status/spec_path/dependencies와 `discovery`를 가진다. Discovery에는 plan/verdict/dependencies/analysis_hash/feature_hash/inputs/evidence를 기록한다. Feature 경로·상태·의존성 변경과 근거 파일 변경은 이전 분석을 무효화한다.

폐기 시 `retirement`에 reason/evidence/successors를 기록한다. `path_redirects`는 과거 specs 경로를 아카이브 경로로 연결해 불변 Work Item 증거 참조를 현재 위치에서 해석한다. `work-items.yaml`은 기존 필드에 gate_revisions/gate_results를 추가하며 다른 최상위 메타데이터도 보존한다. 새 구조로 변환할 때 기존 UUID와 완료 이력은 유지하고 분석·Gate 결과를 추정해 PASS로 만들지 않는다.

## 등록과 폐기 명령

`feature-register PLAN.json`은 READY인 신규 후보를 새 UUIDv7으로 등록한다. 계획에는 `feature`(name/spec_path/dependencies), 공식 spec·plan, `discovery`(mode/candidate/checks), 실제 `paths`와 `evidence`가 필요하다. 등록 뒤 `analysis-record`로 해당 Feature의 분석·의존성 근거를 확정해야 개발할 수 있다.

`feature-retire UUID PLAN.json`은 reason, evidence(로컬 결정 근거 파일), successors(UUID 배열), dependency_updates(활성 소비자 UUID별 새 dependencies 배열)를 받는다. 미종료 Work Item이 있거나 활성 소비자 의존 재평가가 빠졌으면 차단한다. 미리보기의 approval_hash를 검토하고 사용자 승인 후 `--confirm HASH`로 적용한다. 입력이 바뀌면 다시 승인받는다. 기본 아카이브 위치는 `docs/sdd/archive/<UUID>`다. 이동한 Markdown의 상대 링크와 해당 자료를 참조하는 링크·활성 Source Map을 갱신하고, 공식 활성 선택자가 폐기 기능을 가리키면 해제한다. 역사적 Work Item과 폐기 Source Map은 그대로 보존한다.
