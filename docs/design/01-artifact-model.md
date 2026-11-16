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
| `features.yaml` | `features[]`의 `id`, `name`, `spec_path`, `dependencies[]`. 의존 항목은 `feature_id`, `type` |
| `source-map.yaml` | `mappings[]`의 `feature_id`, `sources[]`. 주요 구현·계약 파일의 프로젝트 상대 `path` |
| `work-items.yaml` | `work_items[]`의 `id`, `status`, `declared_features`, `actual_features`. 선택 참조는 `related_work_items`. 완료 시 `validation.status`, `fingerprint`, `evidence[].ref`; 완료 CLI가 `findings`도 기록 |

확정된 신규 Feature와 생성된 Work Item은 별도 UUID v7을 사용한다. 잠정 Feature는 이름과 초안 경로로 다루며 확정 목록에 등록하지 않는다. Feature는 지속되는 제품 기능의 정체성이고, Work Item은 기능 하나 이상에 걸친 변경 요청과 검증 이력이다. 최초 이름과 디렉터리 번호에 정체성을 묶으면 이름 변경과 병렬 작업에서 참조가 흔들리므로 ID를 불변으로 유지한다. 실제 동작의 Task ID는 공식 `tasks.md` 안에서 관리한다.

Source Map은 확정 Feature를 주요 구현·계약 파일 경로에 연결하는 파생 인덱스다. Greenfield에서 아직 확인할 소스가 없으면 빈 매핑이 가능하다. 경로가 이동하거나 매핑이 맞지 않으면 실제 코드와 공식 계약으로 다시 분석한다. 승인 상태 표현과 폐기 Feature의 참조 보존 방식은 미결정이다.
