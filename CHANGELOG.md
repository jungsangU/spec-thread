# 설계 릴리즈 노트

버전은 Harness 설계의 Major.Minor를 뜻한다. Core 배포 버전과 공식 Spec Kit 버전은 별도로 관리한다.

## 1.0

- 질문을 하나씩 받고 구체적인 다음 제안에 자연어로 동의해 이어가는 공통 대화·표시 규칙을 세 Skill에 합성한다. 기존 Gate·승인·이력 정책을 유지한다.

- 로컬 배포본의 install/update 두 명령으로 공식 Spec Kit·Harness 설치·검사를 연결한다. Core 원격 다운로드는 사용자 책임을 유지하며 전용 환경·프로젝트 runner·기존 검사 재사용을 제공한다.

- 2026-11-23 사용자 선택으로 설계 1.0 유지. 제품 구현·설계 재대조 반복 절차와 승인형 Core 정합화·Work Item 기록, 선택적 재검증 계약을 구체화했다. Core 배포 0.4.0과 분리한다.

- Harness 제품 Git과 대상 프로젝트 Git의 책임을 분리하고 Commit, Push, Merge, Rollback과 작업 분배를 사용자 책임으로 확정했다. Worktree는 선택 사항이며 별도 통합 엔진을 필수로 두지 않는다.
- 공식 Spec Kit를 재사용하는 Greenfield·Brownfield Discovery, Feature 확정과 UUIDv7, Project Baseline, Work Item 상태, 영향 평가 및 외부 변경 정합화를 유지했다.
- 사용자 취득·교체, Core·Project·Skill 정확한 일치, 누적 영향 분석과 승인, 선택적 메타데이터 변환, 필수·품질 Gate, 실패 시 사용자 원복 후 처음부터 재시도를 버전 동기화 계약으로 확정했다.
- 제품 Git의 PR 자율 병합, 필수 코드·문서 CI 및 AI 의견의 경고 정책을 기록했다. AI 진입점, 재사용 가능한 설계 문서, HTML 동기화와 설계 전용 Release 워크플로우를 정리했다.

## 0.1

- 최초 로컬 설계 초안. 공통 산출물, 의도·구현·검증 근거의 권위, 위험도 기반 승인과 사용자 요청에 의한 정합화 원칙을 기록했다.
- 이후 공식 Spec Kit와 Project Baseline 계약 및 Discovery Gate로 발전했다. 대체된 세부 모델과 Git 통합의 결정 근거는 [결정 기록](docs/design/DECISIONS.md)에 남긴다. 이 초기 표기는 공식 게시 태그를 뜻하지 않는다.
