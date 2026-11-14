# 07 Agent Runtime

**설계 방향 · D-001, D-006** Claude Code와 Codex가 동일 Artifact Protocol과 Harness 개발 흐름을 사용한다.

**제안 · O-006** 공통 입출력 계약을 에이전트 어댑터가 구현한다. 에이전트는 Spec, 기준 revision, 작업 범위를 받아 후보 변경과 근거를 반환한다. Harness가 계약, 승인, 작업 범위와 검증 결과를 확인한다.

~~~mermaid
sequenceDiagram
  participant H as Harness
  participant A as Agent Adapter
  participant G as 대상 Git
  H->>G: 기준 revision과 입력 확인
  H->>A: 공통 계약과 작업 범위 전달
  A-->>H: 후보 변경과 근거 반환
  H->>H: 범위와 승인 및 검증 결과 확인
  opt 커밋 조건 충족
    H->>G: 코드와 관련 Artifact 커밋
  end
~~~

승인 및 검증 결과의 쓰기 권한, 실행 격리, 재시도, 동시 작업 충돌은 미결정이다.
