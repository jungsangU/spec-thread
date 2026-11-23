# 전체 아키텍처와 책임 경계

**확정 설계 1.0.** SpecThread는 대상 프로젝트에서 공식 Spec Kit을 사용하는 개발 절차에 프로젝트 전체 추적, 결정론적 검증, 로컬 버전 동기화를 추가한다. 제품 저장소에는 Core, 두 에이전트용 스킬, 설계 원본, 제품 CI 및 릴리즈 정의가 있다. 대상 저장소에는 애플리케이션 코드·테스트, 공식 Spec Kit 산출물, 설치된 에이전트 통합 및 프로젝트 Baseline이 있다. 양쪽의 브랜치·커밋·릴리즈와 검증 책임을 각각 관리한다.

~~~mermaid
flowchart LR
  subgraph P["Harness 제품 Git"]
    S["Core와 네이티브 스킬"]
    D["설계와 제품 CI"]
    C["Core 배포"]
    R["설계 릴리즈"]
    S --> C
    D --> R
  end
  U["사용자"] -->|다운로드·설치·교체| C
  C --> L["로컬 Core와 선택한 스킬"]
  subgraph T["대상 프로젝트 Git 및 작업 환경"]
    A["Codex 또는 Claude Code"]
    K["공식 Spec Kit"]
    F["공식 Feature 산출물"]
    B["Project Baseline"]
    I["앱 코드와 테스트"]
    A --> L
    L --> K
    K --> F
    L --> B
    A --> I
  end
  U -->|Git 및 세션 운영| T
~~~

| 구성 | 입력 | 책임과 출력 |
| --- | --- | --- |
| Codex 또는 Claude Code | 사용자 요청, 대상 코드·문서, 스킬 지침 | 의미 분석, 명세 및 구현 작업, 실행 증거 수집. 프로젝트는 둘 중 한 종류를 사용한다. |
| 네이티브 Skill | 요청 유형, 활성 Feature, Core 판정 | 각 환경의 스킬 진입점에서 초기화·개발·외부 변경 정합화를 안내한다. 공식 스킬 호출, 사용자 승인, 영향 및 증거 보고를 맡는다. |
| Shared SDD Core | 제출된 분석, 파일과 메타데이터, 프로젝트 검사 명령, 로컬 버전 | UUID와 참조, Gate 입력 및 판정, 상태 전이, 검증 명령과 Fingerprint를 처리한다. 버전 불일치 시 로컬 계약을 비교하고 검증한다. 의미 판단은 스킬과 사용자 근거가 필요하다. |
| 공식 GitHub Spec Kit | constitution과 활성 Feature 범위 | 명세·명확화·계획·태스크·검증·구현의 공식 원형과 전제를 담당한다. Harness는 공식 파일 형식, 라이프사이클, 설치 및 업데이트 경로를 유지한다. |
| 사용자 | 실행 환경, 작업 범위, 변경 및 검사 결과 | Core 취득과 교체, 프로젝트별 에이전트 선택, 세션 실행·중단·분배·중복 방지, 승인, Git 작업 및 원복을 담당한다. |

Baseline은 전체 Feature, 의존관계, 경로와 Work Item 증거를 연결한다. 승인된 의도는 constitution과 공식 명세에, 실행 사실은 소스·계약·검증 증거에 남긴다. 자세한 스키마는 [산출물 모델](01-artifact-model.md), 권위 및 충돌 정책은 [기준 정보](02-source-of-truth.md), 명령·공식 기능·상태와 검증 계약은 [통합 실행 명세](SpecThread-통합-상세-설계서.md)를 참조한다.

선택 설치 [Monitor](monitor.md)는 사용자 지정 Worktree와 이벤트 입력을 로컬에서 읽는다. Core와 Skill의 실행 경로에서 독립된 관측 모듈이다.

상세 명세의 경계는 [설계 목차](README.md)를 따른다. 공식 기능·호출 전제는 [Spec Kit 연동](spec-kit-integration.md), 네이티브 설치·호출은 [에이전트 런타임](07-agent-runtime.md), 병렬 운영과 명시적 제외 기능은 [Git·세션 운영](08-git-integration.md), 로컬 버전 확인·변환은 [버전 동기화](version-sync.md)에 둔다.
