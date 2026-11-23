# 설계 1.0 구현 재현성 검증

검증일: 2026-11-23 · 대상: 주제별로 정리한 설계 1.0, Core 0.3.0. 이 문서는 검증 증거와 제한을 기록하며 새로운 설계 원본이나 정책을 만들지 않는다. [설계 목차](../design/README.md)

이 보고서는 Core 0.3.0 구현 당시의 비교 기록이다. 이후 사용자 추가 요청의 구현·완료 판정은 [Core 0.4.0 반복 검증](design-1.0-implementation-cycle.md)을 따른다. 아래 미구현 표시는 당시 상태이며 현재 백로그와 구분한다.

## 판정

**문서 정리 전후의 주요 계약 보존, 현행 Core와의 대조, 문서 JSON 예시의 Core 실행은 통과했다.** 구현자가 추측해야 했던 직렬화·해시·CLI 결과·단계 조건을 해당 주제 원본에 보완했다. Core·Skill 구현 코드는 수정하지 않았다.

**제품 전체를 독립적으로 재구현해 같은 결과를 낼 수 있다는 보증과 양쪽 AI의 실제 종단간 PoC는 완료로 판정하지 않는다.** Sync의 별도 Core 강제 바인딩, 검증 자동 최적화와 실제 공식 호출 확인은 [백로그](../design/OPEN-ISSUES.md)에 남아 있다. 이번 실행은 현행 Core의 계약 검증이다.

## 보존 대조

정리 전 Git HEAD의 통합 설계서·주제 문서·실행 가이드와 대조했다.

| 확인 대상 | 정리 후 원본 | 확인 결과 |
| --- | --- | --- |
| 공식 Spec Kit 기능 대조·참조 URL | [공식 연동](../design/spec-kit-integration.md) | 대조 표 보존 |
| Baseline YAML 예시·불변 UUID·범위 해석 | [데이터 모델](../design/01-artifact-model.md) | YAML 코드 블록 보존, 직렬화 상세 보완 |
| 두 초기 분석 흐름·Discovery 표·분석 재개 | [Discovery](../design/03-analysis-standard.md) | Gate 표·흐름도 보존, 제출 객체와 차단 순서 보완 |
| 개발 상태·범위 확대·실패·중단·재개 | [Work Item](../design/04-artifact-lifecycle.md) | 상태도와 필수 조건 통합, 실제 transition 명령의 제약 명시 |
| Feature 보존·아카이브·참조 갱신 | [Feature 생명주기](../design/feature-lifecycle.md) | 기존 5단계 보존, 미리보기·적용·한계 보완 |
| 영향 전파와 핵심 UNKNOWN·CONFLICT 차단 | [영향 분석](../design/05-impact-analysis.md) | 중요도·전파 중단·판정 조건 보존, critical 기본 처리 명시 |
| Gate 집합·실행·증거·완료·Fingerprint | [검증](../design/06-verification.md) | 기존 상세 본문 보존, 결과 필드·해시·단계·판정 보완 |
| 외부 변경 조사·계획·승인·적용·실패 | [수동 Sync](../design/reconciliation.md) | 확정 수동 정책과 구현·미결정 경계 보존 |
| 버전 동기화·사용자 원복 | [버전 동기화](../design/version-sync.md) | 원본 변경 없음 |
| P01~P12와 MVP 인수 기준 | [PoC](../design/acceptance.md) | 모든 시나리오 행 보존 |
| 결정·미결정 ID와 고유 실행 사례 | [결정](../design/DECISIONS.md) · [백로그](../design/OPEN-ISSUES.md) · [가이드](../design/SpecThread-설계와-실행-가이드.md) | ID·이력·사례 보존 |

## 코드·테스트 대응

| 문서 계약 | 현행 구현 | 기존 검증 근거 |
| --- | --- | --- |
| partial·READY·해시 변경·의존성 | analysis.py, discovery.py | test_lifecycle_gates.py의 partial_ready, blocked_and_critical_unknown, analysis_input_change, dependency_change |
| Gate 정의·실행·무효화·증거 | gates.py, evidence.py, checks.py | required_gate_pass, gate_revision, missing_evidence, review_gate, planned_new_input, command_cannot_rewrite_work_item_history |
| failed·새 UUID·범위 확대 | work_items.py, cli.py | failed_retry_uses_new_id_and_reference, scope_expansion |
| 폐기 승인·아카이브·이력 불변 | lifecycle.py, records.py, baseline.py | archive_preserves_uuid, retirement_requires_dependency_reassessment, inflight_work, redirects_historical_evidence |
| 버전·누적 변환·사용자 승인·제한 | version_sync.py | test_version_sync.py의 승인·변환·품질 제한·미지원 구조 테스트 |
| 설치·호출·종료 코드 | cli.py, skills/ | 설치·버전 테스트 및 아래 문서 실행 검증 |
| 외부 변경 비교·승인·재승인·적용·검증 | skills/sdd-sync.md | Skill 본문의 비교 기준 확인·입력 변경 시 재승인·적용 전 버전 검사 지침 확인. 실제 에이전트 수행은 ST-O9 |

구현 경로는 모두 `src/sdd_core/` 기준, 기존 테스트 경로는 `tests/` 기준이다. 위 이름은 테스트 함수의 구별 가능한 축약명이며 실행 시에는 전체 테스트를 사용한다.

## 실행과 결과

제품 의존성을 설치한 Python 3.11 이상에서 저장소 루트 기준으로 실행한다.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/check-design-examples.py
node scripts/check-design-docs.mjs
node scripts/render-design-guide.mjs --check
```

- 기존 제품 테스트: **37개 통과**.
- 문서 실행: **11개 계약 시나리오 통과**. Markdown의 JSON 블록을 직접 추출하고 문서에 지정한 UUID·객체 자리표시자, 프로젝트별 Python 실행 경로·테스트 결과 경로만 실제 값으로 바꿨다.
- Discovery 세 판정 → 등록 → not_started 차단 → partial 분석 → 개발 진입 → Gate 승인·실행 → 입력 변경·실패·수정 → 완료를 확인했다.
- 종료 작업 재개 차단, failed의 새 UUID 재시도, 진행 중 작업의 폐기 차단, 승인 아카이브 후 UUID·Work Item 파일 보존과 폐기 개발 차단을 확인했다.
- 문서의 수식으로 revision.hash·definition_hash·완료 fingerprint를 독립 계산해 저장 결과와 일치함을 확인했다.

[문서 실행 스크립트](../../scripts/check-design-examples.py)는 임시 프로젝트만 변경한다. `.specify`는 Core 입력을 위한 최소 fixture이며 공식 Spec Kit 실제 설치가 아니다. 프로젝트 검사는 실제 unittest로 실행한다. 결과 의미의 충분성·전체 도메인 분석·공식 Skill 위임을 자동으로 증명하지 않는다.

## 남은 검증과 구현 경계

- ST-O1·ST-O2·ST-O9·ST-O11: 실제 Codex·Claude Code 공식 호출, Brownfield·다중 Feature·초기화 재개·Sync PoC.
- ST-O4: 비교 기준 사용자 확인·정확한 변경안 승인·입력 변경 시 재승인은 이미 Skill에 구현됐다. 별도 Core 토큰/스냅샷 강제와 Sync 전용 Work Item 자동 기록은 없다. 추가 계약을 정하기 전까지 현행 수동 절차를 별도 Core 트랜잭션처럼 재해석하지 않는다.
- ST-O6·ST-O7: Gate별 입력·증거 해시, STALE·완료 차단, 집합 선언과 review 결과 제출은 이미 Core에 구현됐다. 자동 이름 추적·결과 이관/재사용 최적화는 없고, 공식 출력의 의미 해석·집합 선택은 Skill이 수행한다. 실제 공식 연동 확인이 남아 있다.
- Feature 아카이브의 인라인 링크 이외 참조, 환경 변수 컨텍스트 등은 Skill이 추가 확인해야 한다. 자동 교정 범위를 넓게 가정하지 않는다.
- ST-O14·ST-O15: GitHub 운영 확인과 아직 접근·확인되지 않은 과거 근거.

이미 확정된 정책을 새 미결정으로 되돌리지 않았다. 이 목록의 상태 원본은 백로그이며 검증 범위가 확대되면 백로그와 이 보고서의 증거를 함께 갱신한다.

## 구현 기준으로 바로잡은 분류

재대조 결과 ST-O4·ST-O6·ST-O7의 제목과 기존 광범위한 “구현 필요” 표현은 실제 구현 범위를 충분히 반영하지 못했다. 기존 실행부와 테스트에 있는 동작을 설계 공백으로 다시 열지 않고, 문서에 부족했던 계약 설명을 보완했다. 정책의 채택·폐기를 변경하지 않았으며 Core에 없는 자동화나 강화 기능을 새 필수 요건으로 추가하지 않았다. 문서 보존 검증, Core 실행 검증, Skill 지침의 존재 확인, 실제 에이전트 수행 검증은 서로 구분한다.
