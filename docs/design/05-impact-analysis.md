# 05 Impact Analysis

**제안 · D-002, D-006, D-007 · O-004**

대상 Git revision과 변경 범위를 비교해 변경 Symbol에서 Claim, Artifact, 검증 대상으로 영향을 전파한다. 정상 개발은 Harness의 변경 범위에서, 외부 변경은 사용자가 요청한 Reconciliation에서 평가하는 안이다.

~~~mermaid
flowchart LR
  D["기준과 비교 대상의 diff"] --> S["변경 Symbol과 관계"]
  S --> C["영향받는 Claim 후보"]
  C --> A["갱신할 Artifact 후보"]
  C --> V["재실행할 검증 후보"]
  S --> U["모호한 매핑은 검토"]
~~~

로그만 바뀌어 Claim에 영향이 없는 경우, 리팩터링으로 구현 설명만 바뀌는 경우, 승인된 계약을 위반한 경우를 구분한다. 이름 변경, 간접 의존성, 분석 지원 범위 밖의 코드에 대한 재분석 범위는 미결정이다.
