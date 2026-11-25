# 검증 및 미결정 백로그

| ID | 구분 | 남은 항목 | 완료 기준 |
| --- | --- | --- | --- |
| ST-O1 | 실행 검증 | Claude Code 초기화·개발 및 실제 공식 스킬 호출 | 두 환경의 동일 샘플에서 공통 계약과 검증 결과 확인 |
| ST-O2 | 실행 검증 | Brownfield, 부분 초기화 재개, 다중 Feature 변경 | 기존 명세·작업 보존, 대상 경로와 영향 범위 재검증 |
| ST-O3 | 결정 완료 · CLI 구현 · PoC | 초기 분석 상태와 대상별 개발 진입 | ST-16. partial + 대상 active/READY + 핵심 의존성 위험 없음 검증, not_started·BLOCKED·핵심 UNKNOWN/CONFLICT 차단을 Baseline과 Skill·Core에 연결하고 검증 |
| ST-O4 | Core·Skill 구현 · 실제 에이전트 PoC | 승인형 외부 변경 정합화·작업 기록 | Core 0.5.0 reconcile이 비교 commit/보존 파일·입력·변경안·검증 계획을 승인 해시에 묶고 적용 전에 재검사한다. 기존 Work Item을 자동 생성하고 적용 실패·검증·완료 이력을 남긴다. CLI와 차단 테스트를 통과했으며 실제 에이전트 실행은 ST-O9에서 추적 |
| ST-O5 | 결정 완료 · CLI 구현 · PoC | Feature 생명주기·아카이브·Baseline 스키마 | ST-17·ST-18. 영구 UUID, active/retired, 폐기 근거·후속 UUID, 경로·증거 참조 갱신과 활성 계산 제외를 구현한다. 직렬화와 schema_version 1 변환은 Core 0.5.0에 구현됐고 실제 프로젝트 PoC로 확인 |
| ST-O6 | Core·Skill 구현 · 실제 프로젝트 PoC | 선택적 재검증·이름 변경·결과 이관 | gate-refresh가 승인된 미리보기로 현재 유효 PASS를 유지하고 필요한 command Gate만 실행한다. 동일 바이트의 단일 이름 변경 후보를 승인 후 반영하고 변경 Gate는 재실행한다. 동일 정의의 유효 결과만 reused_from 근거와 함께 이관한다. 모호성·삭제·새 review·종료 이력 우회는 차단한다 |
| ST-O7 | 선언·기록 구현 · 공식 연동 실행 검증 | 공식 분석·수렴 출력과 Core Gate의 결합 | Gate 계획의 basis·gates, kind=review·method·evidence와 결과 제출은 이미 구현됐다. 프로젝트별 검사 선택과 공식 보고서 해석은 Skill 책임이다. 태스크 생성 전 품질·계획 검토, 출력과 Gate의 실제 연결, 활성 경로·기존 명세 개정·Git 훅의 쓰기 영향을 실제 환경에서 확인한다 |
| ST-O9 | 실행 검증 | 실제 데모의 외부 변경 Sync | 승인 흐름과 핵심 UNKNOWN 차단을 실제 변경으로 확인 |
| ST-O10 | 보류 | 동일 프로젝트에서 두 에이전트 혼용, 별도 검증 프레임워크 | MVP 범위 이후 재검토. 기존 통합 설계서의 설치 래퍼·세부 패키징, 선택 언어·도입 프로젝트·Core 배포 방식에 대한 추가 선택도 이 항목에서 추적하며 현재 Python 패키지·설치 계약을 미결정으로 되돌리지 않음 |
| ST-O11 | 실행 검증 | Discovery Gate 및 분리·통합·재개 | 두 경로의 순서, 요구사항 보존, 현행 근거, 세 판정과 확정 전 UUID 미발급을 확인 |

이미 확인한 범위는 Codex Greenfield 예제의 초기화·개발·브라우저 검증·완료, 공통 CLI, 양쪽 스킬 배치 및 데모의 공식 준비 스크립트다. 초기화 완료 확인과 Sync 승인은 현재 스킬 수준이다. 최신 종단간 검증은 ST-O1·ST-O2·ST-O11로 추적한다.

## 1.0의 추가 확인 사항

| ID | 구분 | 내용 |
| --- | --- | --- |
| ST-O14 | 운영 확인 | 제품 Git 필수 검사 지정과 사용자 태그 Push 후 설계 Release 게시를 실제 저장소에서 확인한다. |
| ST-O15 | 과거 근거 미확인 | 접근이 확인되지 않은 이전 대화·첨부의 추가 결정과 원격의 기존 설계 태그 유무는 확인하지 못했다. 후속 자료가 제공되면 현재 정책과 대조한다. |
| ST-O16 | 결정 완료 · CLI 구현 · PoC | ST-19·ST-20. failed 종료와 새 UUID·이전 실패 참조, 수정 가능한 오류의 in_progress 유지, 필수 Gate 정의·적용 이력·증거·유효성·후속 단계 차단을 검증한다. |

ST-O3·ST-O5·ST-O16 및 필수 Gate의 정책 결정은 완료됐다. 직렬화와 CLI 계약은 각 주제 문서의 Core 0.5.0 절에 기록했다. 실제 에이전트 실행과 프로젝트별 검사는 PoC 과제다. ST-O4·ST-O6의 Core 구현과 실제 에이전트 PoC를 구분하고 ST-O14 운영 검증·ST-O15 과거 근거 확인은 별도로 유지한다.

Core 0.5.0의 구현 근거는 analysis/discovery, work_items/gates/evidence, lifecycle, version_sync 모듈과 기존 제품 테스트다. 외부 변경 Sync의 실행부는 sdd-sync Skill이다. Core 자동화가 없다는 이유로 Skill에 구현된 절차를 미구현으로 분류하지 않는다. ST-O4의 강제 바인딩·작업 기록과 ST-O6의 선택적 실행·이관은 사용자 추가 요청으로 Core 0.4.0에 구현했다. 기존 Core·Skill·Work Item·Gate만 확장하며 별도 오케스트레이터·상태 DB는 추가하지 않았다.

## Monitor 실행 확인

| ID | 구분 | 내용 |
| --- | --- | --- |
| ST-O17 | 실행 검증 | [Monitor](monitor.md)의 실제 대화형 Codex·Claude Code 개별 이벤트와 파일 귀속, 사용자 운영 환경의 종단간 검증. Codex 로컬 저장 기록 18개·종료 세션 2개의 실제 API/브라우저 조회는 [검증 보고서](../validation/monitor-design-review.md)에 확인했다. 신규 이벤트 자연 수신, Windows 네이티브 설치·Hook 실행 결과와 기존 세션의 설정 반영 시점은 확인 필요 |

인수 시나리오·수집할 증거와 MVP 통과 기준은 [PoC 명세](acceptance.md)에 둔다. 확정 정책·직렬화·CLI 계약은 [주제별 원본](README.md)을 따른다.


## 1.1 실행 검증 보완

D01~D10은 ST-33~ST-38로 확정했고 Core 0.5.0·공통 Skill에 구현했다. 검증 정의·프로파일·필수 절차·동일 Work Item 결과 활용·선택 갱신·예외 확인 및 구버전 변환의 테스트 결과는 [1.1 검증 보고서](../validation/risk-profiles-1.1-review.md)에 기록한다. 정책을 미결정으로 되돌리지 않는다.

ST-O1·ST-O7의 실제 에이전트 검증에는 새 프로파일의 의미 분류, 공식 절차 조건 선택, 실제 승인 대화와 공식 결과 활용도 포함한다. 양쪽 설치·Core 계약 비교는 통과했지만 네이티브 모델의 전체 개발 시간·실제 토큰·사용자 대화 횟수는 측정하지 않았다. 기존 ST-O17의 Windows 네이티브 확인도 유지한다.
