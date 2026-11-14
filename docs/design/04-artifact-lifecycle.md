# 04 Artifact Lifecycle

**확정 · D-005, D-008** Intent, Implementation, Verification은 독립 상태다. Brownfield에서 구현이 관찰되고 검증을 통과해도 비즈니스 의도는 미확정일 수 있다. 의도 변경에는 별도 승인과 이력 기록이 필요하다.

**제안 · O-003, O-005** 아래 상태 이름과 구체 전이는 설계 후 확정한다.

| 축 | 상태 후보 |
| --- | --- |
| Intent | unknown, proposed, approved, rejected, superseded |
| Implementation | unknown, not-implemented, observed, diverged |
| Verification | not-run, passed, failed, inconclusive, blocked, stale |

~~~mermaid
stateDiagram-v2
  [*] --> Unknown
  Unknown --> Proposed: 의도 후보 등록
  Proposed --> Proposed: 수정과 재검토
  Proposed --> Approved: 위험도별 승인 충족
  Proposed --> Rejected: 거절
  Approved --> Superseded: 승인된 후속 버전으로 대체
~~~

~~~mermaid
stateDiagram-v2
  [*] --> NotRun
  NotRun --> Evaluated: 실행 결과 기록
  Evaluated --> Stale: 근거의 적용 범위 변경
  Stale --> Evaluated: 재검증
~~~

Evaluated는 결과가 기록된 상태를 그림에서 묶어 표현한다. 승인된 동시 실행 한도를 코드가 위반하고 테스트도 실패했다면 Intent는 approved, Implementation은 diverged, Verification은 failed로 표현할 수 있다.
