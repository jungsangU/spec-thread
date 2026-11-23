# 04 Work Item과 개발 흐름

설계 1.0. `sdd-develop`의 실행 순서, 요청별 상태 전이와 실패·재개의 원본이다. 초기 분석 상태와 대상 진입 판정은 [Discovery](03-analysis-standard.md), Feature 자체의 등록·폐기는 [Feature 생명주기](feature-lifecycle.md)에서 정의한다.

## 입력과 결과

입력은 사용자 요청, 확정 Feature·공식 산출물, 현재 코드·계약과 Baseline이다. 결과는 태스크·코드·테스트, 갱신한 관계와 Source Map, Work Item의 최종 실행 결과·증거·Fingerprint다. 명령 진입 시 [로컬 버전 계약](version-sync.md)을 먼저 확인한다.

## Work Item 상태

~~~mermaid
stateDiagram-v2
  [*] --> pending
  pending --> in_progress: 작업 시작
  in_progress --> in_progress: 복구 가능한 검증 실패 / 수정과 재검증
  in_progress --> suspended: 사용자 중단 또는 판단 대기
  suspended --> in_progress: 현재 산출물 확인 후 사용자 주도 재개
  in_progress --> completed: 모든 적용 필수 Gate의 유효한 PASS 및 기록 성공
  in_progress --> failed: 작업 실패로 종료
  completed --> [*]
  failed --> [*]
~~~

`start FEATURE_UUID ...`는 대상 개발 진입 조건을 검사한 뒤 새 Work Item UUID와 선언 Feature를 `pending`으로 기록한다. `in_progress`는 마지막 저장 상태이며 실행 중인 프로세스를 나타내지 않는다. Work Item 상태와 공식 태스크 체크, 프로세스 생존 여부, Git 커밋 여부는 각각 다른 사실이다.

수정 가능한 테스트·빌드·검증 오류는 `in_progress`에서 수정·재검증한다. 의도적 보류는 `suspended`로 기록하고 사용자 주도로 재개한다. `failed`와 `completed`는 최종 종료 상태이며 다시 열지 않는다. 후속 요청은 새 UUID를 사용하고 필요한 경우 이전 작업을 참조한다. 실패 재시도는 `start FEATURE_UUID ... --related FAILED_WORK_UUID`로 새 작업의 `related_work_items`에 이전 실패 UUID를 연결한다. 종료된 작업의 Gate 정의와 실행 결과도 수정할 수 없다.

## 요청부터 완료까지

1. [대상 개발 진입 조건](03-analysis-standard.md)을 확인한다. 기존 Feature는 Baseline·공식 산출물·소스로 매칭하고 확실한 기존 기능을 우선 재사용한다. 모호할 때만 확인한다. 새로운 기능은 [Discovery와 등록](feature-lifecycle.md)을 거친다. 잠정 Feature는 선언·실제 변경 목록에 등록하지 않는다.
2. 요청에 Work Item UUID 하나를 부여하고 선언 Feature를 기록한다. 개발·검증 진입 전에 [필수 Gate 집합](06-verification.md)을 확정한다. `in_progress` 전환에는 develop 단계의 필수 Gate 통과가 필요하다.
3. Feature별 공식 컨텍스트를 선택하고 확정된 신규 명세 또는 기존 명세를 사용한다. 변경 의도에 맞게 spec·plan을 개정·보완한다. 기존 산출물에는 신규 생성 단계를 무조건 재실행하지 않는다. [공식 연동 계약](spec-kit-integration.md)의 쓰기 전제를 따른다.
4. 공식 `tasks`로 명세·계획·설계 자료에서 작업을 생성한다. 필요한 `analyze`로 spec·plan·tasks의 누락·중복·충돌을 점검한다. `implement` 지침과 작업 순서에 따라 코드·검증을 작성한다. 적용 가능한 `converge`가 추가 격차를 기록하면 구현·검증을 반복한다.
5. 요구사항이나 범위가 달라지면 같은 작업의 영향받은 공식 단계로 돌아간다. [영향 분석](05-impact-analysis.md)으로 계약·실제 의존성을 확인한다. 안전한 범위 확대는 `scope-expand ID PLAN.json`의 features(추가 확정 UUID)와 reason으로 기록한다. 기존 선언 범위를 보존하고 확대 후 Gate 집합을 다시 검토한다.
6. 범위 확정, 관련 공식 단계 완료, 주요 코드·계약 변경과 최종 검증의 단계 경계에서 Baseline·Source Map을 갱신한다. 구조 갱신 실패 시 현재 코드·공식 산출물을 보존하고 완료를 보류한다.
7. 검증 진입에는 `stage-check ID verify`, 완료 직전에는 `stage-check ID complete`를 사용한다. [필수 Gate·증거 계약](06-verification.md)과 Baseline 갱신을 만족하면 최종 결과를 저장하고 `completed`로 전환한다. 사용자 Git 반영은 [별도 운영 단계](08-git-integration.md)다.

## 중단 후 재개

실제 파일과 작업 범위를 대조하고 일치하면 재개한다. 독립 변경은 보존하고 같은 영역의 충돌과 출처가 불명확한 변경은 사용자 판단을 받는다. 누락된 공식 산출물은 해당 공식 절차로 복구한다. 현재 입력·정의·증거에 대한 Gate 유효성을 다시 확인한다.

이 재개는 [초기화 재개](03-analysis-standard.md) 및 [버전 동기화 실패 후 재시도](version-sync.md)와 다르다. 세션 실행·동시성과 복구의 운영 경계는 [Git·세션 운영](08-git-integration.md)을 따른다. 예외적인 외부 변경은 [수동 Sync](reconciliation.md)에서 처리한다.

## Core 0.4.0 상태 명령 계약

`transition ID in_progress|suspended|failed`를 사용한다. 허용 간선은 위 상태도에 한정된다. pending에서 바로 suspended/failed로, suspended에서 바로 failed/completed로 전환하지 않는다. 상태도의 in_progress 자기 반복은 수정·재검증 루프를 뜻하며 같은 상태로 transition을 저장하는 명령이 아니다. completed는 transition 인자로 받지 않고 `complete ID PLAN.json`으로만 기록한다.

시작 시 actual_features와 related_work_items는 배열로 기록한다. `--related`는 반복 지정할 수 있고 참조하는 Work Item은 이미 존재해야 한다. 완료 actual_features는 현재 선언 범위의 부분집합이어야 한다. 실제 변경이 선언 범위를 벗어나면 먼저 범위 확대·Gate 재확정을 수행한다. scope_changes에는 from/to/reason을 누적한다. 종료 상태를 포함한 과거 이력을 재작성하지 않는다.

수정 가능한 검증 오류를 만났다고 자동으로 failed를 저장하지 않는다. 중단·실패 전환은 현재 작업 상태와 사용자 의사를 확인하며, 일반 개발 진입의 품질 제한이 있더라도 suspended/failed 기록 자체는 가능한 로컬 버전·구조 조건에서 처리한다. 이와 달리 in_progress 재개에는 대상 진입과 develop Gate를 다시 확인한다.

Core 0.4.0의 kind=reconciliation 작업은 [정합화 승인 계약](reconciliation.md)으로 생성하며 변경으로 무효화된 Discovery를 복원하기 위해 일반 개발의 READY 진입을 전제하지 않는다. 기존 버전·활성 범위·구조·필수 Gate·증거·완료 상태 검사는 유지한다. 일반 개발 Work Item의 진입 조건을 완화하지 않는다.

## 대화에서의 다음 작업

[대화형 진행](conversation-flow.md)의 구체적 다음 제안을 사용자가 수락하면 새 명령을 다시 입력하지 않아도 개발 요청으로 처리한다. 현재 대상 진입과 범위를 다시 확인하고 기존 Work Item·Gate 규칙을 따른다. 요청 안의 통상적 단계는 진행 안내로 이어가고 새로운 범위·필수 승인만 확인한다.
