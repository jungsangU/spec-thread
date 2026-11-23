# 두 Git 저장소의 운영

## 대상 프로젝트 Git

Harness는 명세, Baseline, 구현과 검증 결과를 현재 작업 공간에서 준비한다. 사용자가 변경 범위와 검증 결과를 보고 Commit, Push, Merge, Rollback을 수행한다. 작업 완료와 Git 반영은 별도 사건이다. 코드와 관련 산출물이 같은 변경 범위를 나타내도록 사용자 반영 전에 확인한다.

1. 사용자가 실행할 세션과 작업 범위를 정하고 같은 Feature의 중복 작업을 피한다. 필요하면 Git Worktree 등으로 작업 공간을 분리한다.
2. Harness는 현재 변경과 영향을 검토하고 공식 검사, 기존 프로젝트 테스트, Baseline 검증을 수행한다. 핵심 불확실성과 충돌을 보고한다.
3. 사용자가 통합 범위를 선택하고 Git으로 반영한다. 통합 결과가 검증 입력과 다르면 관련 기존 검사를 다시 실행한다. 실패 또는 충돌 시 상태를 보고하고 사용자가 수정 또는 Git 원복을 결정한다.

~~~mermaid
flowchart LR
  U["사용자 작업 분배"] --> W["선택한 작업 공간"]
  W --> H["Harness 개발·영향 분석·검증"]
  H -->|통과| G["사용자 Git 검토와 반영"]
  H -->|실패| F["원인 보고와 사용자 조치"]
  G -->|통합 결과 변경| V["기존 검사로 다시 검증"]
~~~

Harness는 병렬 세션의 실행과 동시성을 보장하지 않는다. 자동 잠금, FIFO 대기열, 생존 감시·장애 복구, 중앙 세션 관리자·오케스트레이터, SQLite 상태 DB, 중앙 ID 발급기, Worktree 등록부, 체크포인트 관리자, 실시간 동기화와 별도 자동 통합 엔진을 도입하지 않는다. 초기 분석 완료 역시 사용자 Git 반영과 구분한다.

## Harness 제품 Git

개발자마다 브랜치에서 관련 코드, 설계 Markdown과 HTML을 함께 변경하고 PR로 통합한다. PR 작성자는 필수 검사를 통과한 자신의 PR을 직접 병합할 수 있다. 코드 테스트와 문서 구조·내부 링크 검증은 필수 CI이며, AI 의미 분석은 의견 또는 경고로만 사용한다. 보호 브랜치의 필수 검사 설정은 저장소 관리자가 적용한다. PR마다 설계 버전을 변경하지 않는다.

설계 릴리즈는 사용자가 선택한 Major.Minor 버전의 목차와 [CHANGELOG](../../CHANGELOG.md)를 같이 준비한 뒤 진행한다. 사용자가 제품 Git에 `design-vX.Y` 태그를 Push하면 [설계 Release 워크플로우](../../.github/workflows/design-release.yml)가 태그의 커밋에서 해당 버전 노트만 읽어 GitHub Release를 게시한다. 제품 Core의 패키지 버전·태그·노트와 독립적으로 운영한다. 게시에는 기존 태그를 확인하는 공식 GitHub CLI를 사용한다. [GitHub CLI Release 문서](https://cli.github.com/manual/gh_release_create)

Core 0.2.0에서 이전 Git 통합 명령과 배포 Skill을 제거했다. 구버전 설치는 승인 후 [버전 동기화](version-sync.md)로 정리한다. 이전 동작은 [결정 이력](DECISIONS.md)에 남아 있다.
