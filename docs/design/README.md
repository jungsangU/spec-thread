# SpecThread 설계 v0.1

이 폴더는 Harness 자체의 설계 기록이다. Harness가 관리하는 애플리케이션의 산출물은 해당 프로젝트 Git의 `.sdd/`에 저장한다.

- [확정 결정 및 변경 이력](DECISIONS.md)
- [다음 논의 및 미결정 백로그](OPEN-ISSUES.md)
- [01 Artifact Model](01-artifact-model.md) · 확정 원칙과 스키마 제안
- [02 Source of Truth](02-source-of-truth.md) · 확정 정책
- [03 Analysis Standard](03-analysis-standard.md) · 다음 논의
- [04 Artifact Lifecycle](04-artifact-lifecycle.md) · 확정 원칙과 상태 전이 제안
- [05 Impact Analysis](05-impact-analysis.md) · 제안
- [06 Verification](06-verification.md) · 확정 원칙과 실행 설계 제안
- [07 Agent Runtime](07-agent-runtime.md) · 제안
- [08 Git Integration](08-git-integration.md) · 확정 운영 정책과 통합 설계 제안

~~~mermaid
flowchart LR
  G["Greenfield 요구사항"] --> P["공통 Artifact Protocol"]
  B["Brownfield 기존 코드와 추가 요구사항"] --> P
  P --> C["Harness에서 구현 및 검증"]
  C --> K["대상 Git 커밋"]
~~~

**확정**은 합의한 정책, **제안**은 검토할 상세안, **미결정**은 선택이 남은 항목을 뜻한다. 설계가 확정되면 상세 문서, Mermaid, 결정 기록과 백로그를 함께 갱신한다.
