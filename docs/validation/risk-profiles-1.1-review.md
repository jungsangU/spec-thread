# 설계 1.1 위험도 기반 개발·검증 구현 대조

검증일: 2026-11-25. 설계 1.1은 사용자가 선택한 Minor이며 제품 구현은 Core 0.5.0이다. 설계 원본은 [검증 프로파일](../design/verification-profiles.md), 결정 근거는 [ST-33~ST-38](../design/DECISIONS.md)다. 기존 Monitor 작업은 보존했다. Commit·Push·태그·사용자 프로젝트 업데이트는 실행하지 않았다.

## 기존 비용과 변경 범위

기존 구현은 매 요청의 Gate 전체 정의와 반복 확인, 동일 Gate 재호출 시 실제 재실행, 매번 관리 파일 직렬화가 발생했다. Skill은 모든 요청에 같은 공식 단계 흐름을 적용해 경량 변경도 단계·보고 비용이 컸다. 실제 전체 개발 비용은 모델별 측정이 필요하며 이 관찰만으로 전체 시간·토큰 개선율을 주장하지 않는다.

새 정책은 필수 검증을 줄이는 대신 위험에 맞는 최소 절차, 정의 재사용과 유효 결과 활용, 일반 진행·예외 승인을 분리한다. YAML 반복 파싱 비용에는 기존 PyYAML의 CSafeLoader를 재사용하고 부재 시 SafeLoader로 돌아간다. 중복 키·문자열 키 검사와 참조 검증은 유지한다.

## 요구·구현 대응

| 확정 요구 | 설계·실제 구현 | 검증 |
| --- | --- | --- |
| D01~D03 프로파일·최소 절차 | verification.py profile_preview/apply_profile/record_step/steps_required, sdd-develop | 경량 최소·일반 신규 Feature·Strict 자동 경로 거부·상향·하향 차단·UNKNOWN/CONFLICT·필수 절차 누락 |
| D04~D05 정의 재사용 | verification.yaml, registry_preview/apply_registry/templates/compose/enforce, init Skill | 프로젝트/Feature/추가 Gate 합성·필수 정책 생략/변경 차단·미확인 정책 차단 |
| D06 결과 공유 | 기존 gates.py 실행·재검증의 현재 입력/증거 검사, procedure 원본 참조 | 동일 Work Item 최신 유효 결과·같은 목적 공유·다른 Work Item PASS 승계 금지·Analyze/Converge 구분 |
| D07 선택 갱신 | records.py 원자 쓰기 전 바이트 비교, Skill 관리정보 분기 | 변경 없는 파일 바이트·mtime 유지, 관련 파일만 갱신 |
| D08 실제 증거 | checks.py 실제 시작/시간, 기존 실행 결과와 관리 로그 경로 | 실제 명령·종료·출력·시간·증거 해시, FAIL 수리·입력/증거 무효화 |
| D09 일반/예외 | cli.py --apply/--confirm, scope-expand Preview, 공통 대화 Skill | Strict/불확실성·범위 확대·필수 정의 변경은 자동 적용 차단, stale Preview 거부 |
| D10 공통 완료 | 기존 complete/stage-check + 필수 절차 검사 | 필수 PASS·범위·소견·실제 증거 유지, 필수 공식 검토 입력 변경 시 완료 차단 |
| 기존 프로젝트 전환 | version_sync.py 기존 누적 변환 0.4→0.5 | 실제 0.4 생성 이력·앱·Feature·Source Map 보존, 미확인 정의 틀만 추가 |
| 양쪽 에이전트·Monitor | 공통 bundle·네이티브 설치 경로, 읽기 전용 profile 메타데이터 | 양쪽 공식 설치/업데이트, 공통 정책·Core 계약. 실제 모델 실행은 아래 한계 참조 |

Core가 위험의 의미를 자동 분석하지는 않는다. Skill이 사실을 제출하고 Core가 구조·최소 프로파일·단조 확장·승인 경로·현재 정책·증거를 강제한다. 사용자 소유 로컬 CLI의 Hash는 입력 바인딩이며 실제 사람 동의의 암호학적 증명이 아니다. Skill은 실제 답을 기다리고 동의를 제조하지 않는다. 호스트 실행 권한도 유지한다.

## 프로파일별 실행 경로

- Lightweight: 매칭·Preflight → Work Item → 국소 계약/불확실성 분류 → 기존 plan 검토·변경 tasks → 정책 Gate 합성 → 구현 → 유효 결과 활용/변경 검사 → 필요한 Baseline만 갱신 → 공통 완료. 기존 필수 체크리스트·Gate는 남는다.
- Standard: 관련 의존·계약과 기존 계획을 검토하고 정식 tasks를 수행한다. 신규 Feature는 Discovery/specify와 READY·등록을 거친다. 명세·계약 변경에 필요한 공식 개정을 추가한다.
- Strict: 위험·범위·검증의 구체적 동의를 받은 뒤 확대 영향 분석, 계획 검토와 checklist/analyze/converge 적용 검토를 기록한다. 필요한 절차를 수행하고 공통 완료 조건을 통과한다.
- 추가 위험/범위: 같은 Work Item 이력에 상향·절차를 추가한다. 범위 확대는 승인 Preview에 바인딩하며 필수 검증을 하향하지 않는다.
- 실패/중단: 수정 가능한 검사 오류는 in_progress에서 수리·선택 재검증한다. suspended는 현재 입력·프로파일·정책을 재확인하고 재개한다. failed/completed는 종료이며 재시도는 새 UUID다.

공식 Spec Kit 명세·산출물·전제·라이프사이클은 변경하지 않았다. Analyze는 tasks 이후 읽기 전용 검토, Converge는 구현 뒤 충족 여부와 추가 tasks이며 서로 대체하지 않는다. 기존 review 결과를 참조할 수 있지만 지원되지 않는 공식 결과 공유 API를 가정하지 않는다.

## 실행 검증

Core unittest 98개 통과. 프로파일 전용 테스트는 경량 변경, 일반/신규 Feature, 고위험·도중 상향, 필수 Gate 우회, 선택 재실행, 증거 무효화, 중단·재개와 현재 필수 공식 검토의 유효성을 포함한다. Monitor는 24개 중 23개 통과·Windows 전용 1개 생략이다. 로컬 HTTP 테스트는 포트 바인딩 허용 환경에서 실행했다.

문서 구조·링크 29개와 설계 버전/CHANGELOG 일치, 가이드 HTML 재생성 일치를 검사했다. HTML 소개·기능목록·실행 가이드를 Chrome의 데스크톱/모바일 크기로 열어 JS 오류 없음을 확인했고 소개·목록 화면을 시각 확인했다. 세 번들 Skill은 quick_validate를 통과했다.

scripts/check-design-examples.py는 문서의 실제 JSON을 임시 Core 프로젝트에서 실행한다. READY/CONDITIONAL/BLOCKED, partial, Gate 실행·실패 수리·완료, Fingerprint 독립 계산, 승인 Sync, failed 재시도·아카이브를 검증한다. 공식 Spec Kit 실행을 가장하지 않는 격리 계약 fixture다.

캐시의 실제 specify-cli 1.4.0 환경에서 새로운 Core 소스로 Codex와 Claude Code 각각 install→update를 실행했다. 공식 상태 ok, Core 0.5.0·일곱 Baseline 파일·verification unconfigured와 양쪽 동일한 개발 Skill 번들 16,718바이트를 확인했다. 이는 실제 공식 설치 연동 확인이며 모델이 공식 Skill을 호출해 개발한 종단간 시험과는 구분한다.

실제 Core 0.4.0 소스로 만든 완료 Work Item을 0.5.0으로 승인 변환했다. 필수/품질 Gate 통과, work-items/features/source-map/app.py/실제 검사 파일의 SHA256 보존, 완료 이력 1건 유지와 미확인 정책 추가를 확인했다. 이력에 프로파일을 추측해 소급 부여하지 않았다. 실패 시 자동 원복·부분 복구·재개 엔진은 추가하지 않았다.

## 비교 측정

[재현 스크립트](../../scripts/benchmark-verification-profiles.py)와 [실측 원자료](risk-profiles-1.1-measurements.json)를 함께 제공한다. 이전 소스는 commit 035ba12에서 읽기 전용 추출했다. 같은 Python·요청·초기 소스·실제 assertion 테스트로 agent 설치 종류별 3회, 각 버전 총 6회 실행했다. 새 정책 등록은 측정 전에 수행했다. 두 번의 같은 Gate 요청을 보내 중복 실행 여부를 비교했다.

| 항목 | Core 0.4.0 | Core 0.5.0 |
| --- | --- | --- |
| Core 요청 처리 중앙값(구현·검사 포함) | 0.409561초 | 0.288911초 |
| 두 Gate 요청 처리 중앙값 | 0.174460초 | 0.100312초 |
| 실제 파일 수정 중앙값 | 0.000243초 | 0.000255초 |
| 실제 테스트 호출/요청 | 2회 | 1회 |
| Gate 계획에 필요한 명시 확인 경로/요청 | 1회 | 0회 |
| 완료 | 6/6 | 6/6 |

이는 단순 UI 상수 변경의 Core 마이크로벤치마크다. 시간 차이는 파서 최적화와 재실행 제거를 함께 포함하며 모델 사고·설치·정책 최초 탐색·사용자 대화를 포함하지 않는다. 전체 개발 시간·토큰·사람의 실제 승인 횟수를 이 수치로 대체하지 않는다. 일반 기능·신규 Feature·Strict 등은 동작 테스트로 검증했지만 동일 모델의 전후 성능 실험은 수행하지 않았다. Skill 본문 크기도 실제 LLM 토큰 측정이 아니다.

## 파일과 기존 기능 재사용

- Core: baseline.py, records.py, gates.py, checks.py, cli.py, version_sync.py와 verification.py. 기존 Work Item·Gate·Fingerprint·실행기·누적 마이그레이션을 사용한다.
- Skill: sdd-init.md, sdd-develop.md, _conversation.md. 별도 공개 명령·오케스트레이터·상태 DB를 추가하지 않았다.
- 문서: verification-profiles 원본, 관련 아키텍처·데이터·상태·영향·검증·공식 연동·설치·대화·버전·인수 문서, DECISIONS·OPEN-ISSUES·목차·CHANGELOG·사용 가이드·관련 HTML. 세부 정책을 한 원본으로 연결했다.
- 테스트/재현: test_verification_profiles.py, 기존 lifecycle/version-sync·Monitor 검증, 문서 예제·Core 비교 스크립트. Core/Monitor 의존 버전 일치도 반영했다.
- Monitor: 현재 프로파일/분류 이유/승인 경로/절차, Gate 정책·재사용 출처·실측 시간만 표시한다. 저장되지 않은 승인 Preview용 별도 대기 시스템을 만들지 않았다.

## 남은 확인과 판단

상세 설계와 해당 Core·Skill 구현은 반영했다. 테스트된 Core 계약·공식 설치·실제 구버전 변환은 통과했다. Codex·Claude Code 네이티브 모델이 같은 실제 프로젝트에서 모든 프로파일을 수행하고 공식 Skill을 위임하는 실행은 미검증이다. 실제 전체 개발 시간·토큰·사용자 대화 감소, Windows 네이티브 Hook/설치는 완료로 표시하지 않는다. 이 범위는 기존 ST-O1·ST-O7·ST-O17에 연결한다.

새로운 정책 선택은 필요하지 않다. 1.1 선택을 반영했고 기존 제외·Git 책임을 유지한다. 적용 전 대상 프로젝트는 새 로컬 배포본의 update와 기존 품질 Gate를 사용해야 하며 이번 작업에서 사용자 프로젝트를 자동 업데이트하지 않았다.
