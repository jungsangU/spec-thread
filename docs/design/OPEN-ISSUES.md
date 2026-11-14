# 설계 백로그

| ID | 상태 | 논의 주제 | 결정할 내용 |
| --- | --- | --- | --- |
| O-001 | 다음 · 미결정 | [Analysis Standard](03-analysis-standard.md) | 입력 범위, 근거 기준, 정규화, Claude Code와 Codex 결과의 일치 판정 |
| O-002 | 미결정 | [Artifact Schema](01-artifact-model.md) | 타입·필수 필드·관계·ID·Symbol 식별, 버전 및 마이그레이션 |
| O-003 | 미결정 | [Artifact Lifecycle](04-artifact-lifecycle.md) | 상태 전이 조건, 승인 권한과 위임, 위험도 상향, 폐기 및 대체 |
| O-004 | 미결정 | [Impact Analysis](05-impact-analysis.md) | 언어별 탐지, 관계 전파, 재분석 범위와 모호한 변경 처리 |
| O-005 | 미결정 | [Verification](06-verification.md) | 위험도별 증거, 실행기, 결과 스키마, stale 판단 및 커밋 차단 조건 |
| O-006 | 미결정 | [Agent Runtime](07-agent-runtime.md) | 어댑터 계약, 쓰기 권한, 실행 격리, 재시도 및 동시 작업 |
| O-007 | 미결정 | [Git Integration](08-git-integration.md) | Baseline 요건, revision 바인딩, PR·CI 및 merge/rebase/revert |
| O-008 | 미결정 | [Reconciliation](08-git-integration.md) | 명령 인터페이스, 계획 승인 범위와 만료, 중단·부분 실패 처리 |
| O-009 | 미결정 | 도입 범위 | 첫 지원 언어와 대상 프로젝트, MVP 시나리오, 외부 SDD 도구 연동 |

~~~mermaid
flowchart TD
  A["O-001 분석 기준"] --> S["O-002 스키마와 O-003 생명주기"]
  S --> I["O-004 영향 분석"]
  S --> V["O-005 검증"]
  S --> R["O-006 런타임"]
  I --> G["O-007 Git과 O-008 복구"]
  V --> G
  G --> M["O-009 MVP 시나리오"]
  R --> M
~~~

다이어그램은 논의 순서 제안이다. 항목이 확정되면 결정 ID와 상세 문서를 연결한다.
