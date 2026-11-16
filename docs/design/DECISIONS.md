# 설계 결정 기록

2026-11-16 기준. 구현 상태와 검증 근거는 [통합 설계서](SpecThread-통합-상세-설계서.md)와 [미결정 백로그](OPEN-ISSUES.md)에 연결한다.

| ID | 결정 | 결정 이유 |
| --- | --- | --- |
| ST-01 | 공식 Spec Kit 독립 설치, 공식 기능 우선 및 원형 유지 | 명세·계획·태스크와 공식 도구 업데이트를 재사용한다 |
| ST-02 | Greenfield·Brownfield 공통 Feature 모델과 Baseline 6개 파일 | 입력 근거가 달라도 같은 개발 과정에서 산출물을 읽을 수 있다 |
| ST-03 | 의도·구현·실행 증거의 권위 분리 | 구현 편차가 사용자 승인 없이 제품 정책으로 굳는 일을 막는다 |
| ST-04 | 확정 Feature와 Work Item의 UUID v7, Feature와 파일 경로를 연결하는 Source Map | 참조를 이름·번호와 분리하고 병렬 변경 및 유지 비용을 줄인다 |
| ST-05 | Codex·Claude Code를 같은 정책으로 지원하고 스킬과 공통 CLI로 제공 | 의미 분석은 에이전트가 맡고 상태·구조·Git 검사 결과는 공유한다 |
| ST-06 | 핵심 UNKNOWN과 CONFLICT 차단, 비핵심 UNKNOWN은 근거 기록 | 확인 비용을 영향에 비례시키면서 중요 계약을 보호한다 |
| ST-07 | Fingerprint와 증거를 완료 이력에 보존 | 무엇을 검사했는지 구분하고 기존 이력을 유지한다 |
| ST-08 | 외부 변경은 승인형 수동 Sync | 사용자의 작업과 승인된 의도를 보호한다 |
| ST-09 | 사용자 Worktree 운영, 개발과 명시적 Git 커밋 분리 | 세션 관리 복잡도를 줄이고 선택 변경을 하나의 검증된 트리로 반영한다 |
| ST-10 | 최초 Baseline과 Git 통합의 구체적 계약은 별도 확정 | 전체 분석 완료, 최초 Git 기준 성립, 일반 Work Item 완료를 구분해야 한다 |
| ST-11 | 공식 명세 생성·명확화를 재사용하는 Greenfield/Brownfield Discovery와 READY / CONDITIONAL / BLOCKED Gate | 업무 흐름과 현행 근거를 검토하고 경계와 요구사항을 검증한 기능만 확정한다 |
