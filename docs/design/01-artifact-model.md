# 01 Artifact Model

**확정 · D-001, D-002, D-003**

| 요소 | 역할 |
| --- | --- |
| Artifact | 요구사항, 업무 규칙, 컴포넌트 등 논리 단위의 Git 파일 |
| Claim | 독립적으로 검증하고 영향과 승인을 추적하는 최소 의미 단위 |
| Evidence | 요구사항 원문, revision이 지정된 분석, 테스트 실행 등 Claim의 근거 |
| Source Symbol | 함수·클래스 등 코드 추적 단위 |

Greenfield는 요구사항을 Spec/Claim으로 정리하고 구현한다. Brownfield는 기존 코드로부터 관찰 사실과 Spec 후보를 추출하고, 추가 요구사항을 공통 모델에 반영한 뒤 코드를 수정한다. 두 경로 모두 동일한 타입과 관계를 사용하며 초기 상태와 출처가 다를 수 있다.

~~~mermaid
flowchart LR
  G["요구사항"] --> S["Spec과 Claim"]
  B["기존 Git 코드"] --> X["관찰 사실과 Spec 후보 추출"]
  X --> S
  X --> N["추가 요구사항"]
  N --> S
  A["Artifact 파일"] -->|포함| S
  S -->|근거 참조| E["Evidence"]
  S -->|구현 참조| Y["Source Symbol"]
  S --> C["코드 생성 또는 수정"]
~~~

대상 저장소의 `.sdd/`에서 문서 본문은 Markdown으로 작성하고 기계가 읽는 메타데이터는 YAML Frontmatter에 둔다.

**제안 · O-002** 도메인·요구사항·규칙·컴포넌트·인터페이스 문서와 검증 결과의 배치를 설계한다. 검색용 JSON 또는 DB 인덱스는 재생성 가능한 캐시를 후보로 둔다. 아래 필드명은 스키마 예시다.

~~~yaml
id: BR-001
type: business-rule
claims:
  - id: CLM-005
    risk: R2
    evidence_refs: [EV-001]
    source_symbol_refs: [SYM-001]
~~~

Claim 본문 예시로는 “에이전트별 동시 실행은 최대 1건이다”가 있다.
