# SpecThread 작업 지침

이 저장소는 SDD Harness 제품의 소스와 명세를 관리한다. 대상 애플리케이션 저장소의 Git과 분리한다. Harness가 생성하는 `.specify/baseline/` 및 공식 Spec Kit 산출물은 대상 저장소에 속한다.

1. [설계 목차](docs/design/README.md)에서 설계 버전과 문서 역할을 확인한다.
2. [아키텍처](docs/design/architecture.md), [통합 실행 명세](docs/design/SpecThread-통합-상세-설계서.md), [버전 동기화](docs/design/version-sync.md), [두 저장소의 Git 운영](docs/design/08-git-integration.md)을 읽는다.
3. [결정 이력](docs/design/DECISIONS.md), [미결정·미확인 목록](docs/design/OPEN-ISSUES.md), [설계 릴리즈 노트](CHANGELOG.md)에서 확정 범위와 근거를 확인한다. 최신 확정 설계를 기준으로 작업하며 설계와 실제 코드의 차이를 분리해 기록한다.
4. 공식 Spec Kit 형식과 라이프사이클을 유지한다. 병렬 세션은 사용자가 관리한다. 다른 저장소나 계정의 대화에 의존하는 내용을 발견하면 결정 근거와 적용 조건을 저장소 문서에 남긴다.
5. 변경한 계약은 관련 명세·결정·백로그와 실행 가이드에 반영하고, [HTML 갱신 및 검증 절차](docs/design/README.md)에 따라 HTML도 같은 변경에 포함한다. 설계 버전 변경은 사용자 선택을 받는다.
6. Git Commit, Push, Merge, Rollback과 태그는 사용자가 수행한다. 작업 결과와 검증 범위를 보고한다.

## Chat·Work의 설계 컨텍스트 복원

- Git에서 관리하는 설계 문서를 공식 원본으로 사용한다. 논의·분석·구현 전에 위 순서대로 관련 문서를 읽고, 확정 결정과 명시적 제외 사항을 유지한다.
- Chat은 [GitHub에 게시된 AGENTS.md](https://github.com/jungsangU/spec-thread/blob/main/AGENTS.md)에서 시작해 설계 문서를 조회하고 논의·결정한다. 로컬 파일이나 이 지침의 자동 로딩을 전제로 하지 않는다. ChatGPT 프로젝트 지침에는 위 GitHub URL을 진입점으로 등록한다. Work는 실제 저장소에서 파일을 대조하고 작성·수정·검증한다.
- 이전 대화나 AI 메모리보다 공식 Git 문서를 기준으로 삼는다. 최신 사용자 결정이 아직 게시되지 않았으면 게시된 설계와 구분한다. 내용이 충돌하면 변경 이유와 영향을 설명하고 사용자와 확정한 뒤 반영한다.
