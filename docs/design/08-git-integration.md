# 08 Git Integration과 Reconciliation

**확정 · D-004, D-006, D-007, D-008**

- 대상 프로젝트 Git revision을 구현 및 정합성 비교 기준으로 사용한다. Harness 자체의 Git은 Harness 설계와 구현 이력을 관리한다.
- 정상 개발은 Spec → Claim → Code → Verification을 거쳐 코드와 관련 Artifact 변경을 같은 커밋에 담는다. Artifact 갱신 여부는 Claim 영향에 따른다.
- 예외적 외부 변경에는 상시 감시와 자동 보정을 적용하지 않는다. 사용자가 요청하면 inspect → plan → approve → apply → verify를 수행한다.
- 계획에는 현재 revision, 영향받는 Claim, 코드와 Artifact 변경 범위, 복구 근거와 검증 방법을 제시한다. 적용 전 기준이 바뀌면 다시 비교한다. 승인 거절 시 변경 없이 종료하고 검증 실패 시 결과를 보고해 재검토한다.

~~~mermaid
flowchart TD
  S["Spec"] --> C["Claim과 필요한 승인"]
  C --> I["Code"]
  I --> V["Verification"]
  V -->|기준 충족| K["코드와 관련 Artifact 동시 커밋"]
  V -->|실패| F["수정 또는 재검토"]
  U["사용자의 명시적 복구 요청"] --> X["Inspect"]
  X -->|불일치 없음| E["종료"]
  X -->|불일치 있음| P["Plan"]
  P --> A{"Approve: 사용자 승인"}
  A -->|거절| E
  A -->|승인| B{"계획 기준 유지?"}
  B -->|변경됨| X
  B -->|유지| Y["Apply"]
  Y --> Z["Verify"]
  Z -->|실패| F
  Z -->|통과| R["별도 복구 커밋"]
~~~

승인된 동시 실행 한도가 1건인데 외부 커밋으로 3건이 되면 코드를 1건으로 복원하고 동시성 테스트를 다시 실행하는 계획을 제시한다. 함수 이름만 바뀌면 Source Symbol과 구현 설명 갱신을 제시할 수 있다. 승인된 의도 자체를 바꾸려면 별도 Spec 승인 절차를 사용한다.

**제안 · O-007, O-008** 최초 Baseline은 스키마, 근거, 코드 연결 및 적용 가능한 검증을 충족한 커밋으로 식별한다. 커밋 전에 얻은 Evidence를 대상 코드 스냅샷에 연결하는 방식, PR·CI 및 이력 재작성 정책, 계획 만료, 적용 중 부분 실패 처리와 명령 이름은 미결정이다.
