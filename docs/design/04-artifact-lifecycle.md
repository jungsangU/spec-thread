# 04 개발 및 변경의 생명주기

초기 분석의 의미상 상태는 `not_started → partial → complete`다. [Discovery Gate](03-analysis-standard.md)는 잠정 Feature의 확정 가능성을 판정한다. 전체 초기 분석 완료에는 Feature 확정 외에도 공식 설계 산출물과 Baseline 검증이 필요하다.

## Work Item

| 전이 | 조건 |
| --- | --- |
| 생성 → `pending` | `sdd-core start UUID ...`로 대상 진입 조건 확인 후 신규 Work Item UUID 및 선언 Feature 목록 기록 |
| `pending` → `in_progress` | 개발 시작 |
| `in_progress` → `suspended` | 사용자 중단 또는 판단 대기 |
| `suspended` → `in_progress` | 현재 파일과 변경 범위를 확인하고 사용자 주도로 재개 |
| `in_progress` → `completed` | `complete` 게이트 통과와 검증 기록 저장 |
| `in_progress` → `failed` | 작업을 실패로 종료한다고 판단 |

복구 가능한 검증 실패는 `in_progress`에서 수정과 재검증으로 처리한다. 완료된 작업은 Core 전이 명령으로 재개할 수 없다. 후속 요청은 새 ID를 쓰고 필요한 경우 이전 Work Item을 참조한다. `failed`도 최종 종료 상태이며 재개하지 않는다. 실패한 작업의 재시도는 새 UUIDv7을 생성하고 `related_work_items`로 이전 실패 작업을 참조한다. Work Item 상태와 공식 태스크 체크, 프로세스 생존 여부, Git 커밋 여부는 각각 다른 사실이다.

## 개발 문서에서 코드로

1. `sdd-develop`이 [초기 분석 상태와 대상 개발 진입 조건](03-analysis-standard.md)을 확인한다. `not_started`는 차단하고 `partial`은 대상 활성 Feature의 READY와 핵심 의존성 위험 없음이 검증될 때 허용한다. `complete`에서도 대상 조건을 다시 확인한다. 선언 Feature와 실제 변경 Feature를 기록한다. 신규 Feature가 필요하면 명세와 경계를 확정한 뒤 새 UUID를 부여한다. 잠정 Feature는 선언·실제 변경 Feature 목록에 등록하지 않는다.
2. [필수 Gate 정의와 실행 계약](06-verification.md)에 따라 개발·검증 진입 전에 적용 집합과 근거를 확정한다. 변경 의도에 따라 공식 스킬로 spec과 plan을 개정·보완한다. 기존 산출물에 신규 생성 단계를 실행하면 덮어쓸 수 있으므로 개정 흐름을 사용한다.
3. 공식 `tasks`는 명세, 계획 및 적용 가능한 설계 산출물로 작업을 생성한다. 필요한 경우 `analyze`로 spec·plan·tasks 사이 누락·중복·충돌을 점검한다.
4. 에이전트는 공식 `implement` 지침과 작업 순서에 따라 실제 코드와 검증을 작성한다. 요구사항이 달라지면 해당 공식 산출물을 수정하고 이어간다. 적용 가능한 `converge`가 격차를 추가 작업으로 기록하면 구현과 검증을 다시 진행한다.
5. 모든 적용 필수 Gate가 유효한 PASS일 때만 완료한다. FAIL·NOT_RUN·UNKNOWN·STALE과 증거 부족은 해당 후속 단계와 완료를 차단한다. 관계와 Source Map을 단계 경계에서 정리한다. 최종 실행 결과, 증거와 Fingerprint를 기록한다. Git 반영은 사용자가 수행한다.

`sdd-sync`는 외부 변경을 재발견하는 복구 흐름이다. 변경 계획과 승인 범위가 개발 의도라면 공식 산출물도 적절한 절차로 개정한다. 비교 기준 저장과 승인 강제 방식은 열린 과제다.

실패한 요청의 재시도는 `start FEATURE_UUID ... --related FAILED_WORK_UUID`로 연결한다. `in_progress`로 진입하기 전에 적용 Gate 집합을 확정하고 develop 필수 Gate를 통과해야 한다. 검증 진입에는 `stage-check ID verify`, 완료 직전에는 `stage-check ID complete`를 사용한다. 각 결과는 현재 파일·정의·증거로 재평가한다. Core 0.3.0은 종료된 작업의 Gate 결과와 정의 수정도 거부한다.

작업 범위 확대는 `scope-expand ID PLAN.json`의 features(추가 확정 UUID)와 reason으로 기록한다. 기존 선언 범위를 보존하며 확대 후에는 새 범위의 Gate 집합을 다시 검토해야 한다.
