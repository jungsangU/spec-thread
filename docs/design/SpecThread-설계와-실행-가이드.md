# SpecThread 설계와 실행 가이드

설계 2.0 · 공식 Spec Kit v1.4.0 재현 기준. 이 문서는 사용 순서와 사례를 설명한다. 정책·스키마·Gate의 원본은 [주제별 설계 문서](README.md)에 있으며 이 가이드에 재수록하지 않는다. 설계 선택의 이유는 [결정 기록](DECISIONS.md)에서 확인한다.

## 작업에 맞는 문서 찾기

| 하려는 작업 | 읽을 원본 | 입력·출력 계약 위치 |
| --- | --- | --- |
| install/update로 설치·업데이트 | [설치 매뉴얼](../SpecThread-설치-매뉴얼.md) · [에이전트 호출](07-agent-runtime.md) | 공식 설치와 네이티브 Skill |
| 프로젝트 분석·Feature 확정 | [초기 분석과 Discovery](03-analysis-standard.md) | 요구·기존 시스템 → Discovery·공식 자료·Baseline |
| 개발 요청과 완료 | [Work Item 개발](04-artifact-lifecycle.md) | 요청·Feature → 코드·테스트·작업 이력 |
| 직접 수정한 코드 정합화 | [외부 변경 Sync](reconciliation.md) | 비교 근거·변경·승인 → 정합화·검증 결과 |
| Core 교체 후 버전 정렬 | [버전 동기화](version-sync.md) | 로컬 버전·승인 계획 → 메타데이터·Gate |
| 검증 결과를 Git에 반영 | [Git·세션 운영](08-git-integration.md) | 변경·증거 → 사용자 검토와 반영 |

## 사례로 보는 문서와 코드의 의존 관계

개인 할 일 앱의 등록·조회·완료를 예로 들면, `spec.md`에는 사용자가 어떤 상태에서 무엇을 기대하는지와 수용 시나리오가 들어간다. `plan.md`는 그 의도를 실현할 화면 구조와 저장소 사용을 정한다. 데이터 모델은 할 일 ID와 상태를 정의하고, UI 계약은 사용자 입력과 완료 표시의 조건을 구체화한다. 연구 문서는 기술 선택의 근거를, quickstart는 재현 가능한 실행·검증 방법을 설명한다.

개발 요청이 들어오면 기존 Feature의 UUID와 경로를 찾고 Work Item을 만든다. `tasks.md`에서 요구사항과 작업의 연결을 확인한 뒤 저장 모듈, 화면 이벤트, 목록 렌더링, 검증 작업을 구현한다. 예를 들어 완료 처리는 명세의 기대 결과, 데이터 상태와 UI 계약, 작업 정의를 함께 읽어야 구현할 수 있다. 브라우저 테스트는 완료 버튼의 존재 외에도 선택한 항목만 완료되는지, 새로 열었을 때 상태가 복원되는지 검증한다. Source Map에는 해당 기능의 주요 구현·계약 파일 경로를 연결한다. 새 요청이 완료 의미를 바꾸면 영향받는 명세·계획·계약·태스크를 다시 검토한 후 코드를 변경한다.

이 사례의 Codex 실행에서는 Feature UUID 유지, 작업 7개 완료, Chrome 검증, Baseline 재검증과 `completed` 기록을 확인했다. 신규 사용자 5명 대상 사용성 측정은 비핵심 `UNKNOWN`으로 기록됐다. 검증이 통과한 범위와 측정하지 않은 범위를 Work Item에서 구별할 수 있다.

## 검증 운영 예시

[Gate 계획과 실행 형식](06-verification.md)을 먼저 확인한다.

먼저 적용 Gate를 등록하고 gate-run으로 검증한다. 완료 계획은 임시 JSON으로 전달한다. 아래 예에서 경로와 명령은 대상 프로젝트에 맞게 바꾼다. 배열 안의 명령은 셸 문자열이 아닌 실행 파일과 인자 목록이다. 파일에 저장된 Feature UUID를 실제 값으로 바꿔 실행한다.

```json
{
  "actual_features": ["019a1234-5678-7abc-8def-123456789abc"],
  "findings": [
    {"assessment": "SAFE", "evidence": "완료 계약과 소비자 동작을 검증했다", "critical": false}
  ],
  "evidence": [{"ref": "tests/todo-browser.mjs"}]
}
```

검사 실패 시 현재 작업을 보존하고 원인을 수정해 다시 실행한다. 검사가 입력 파일을 변경해 Fingerprint가 달라지는 경우에도 완료 판정이 보류된다. 사용자가 통합한 내용에 추가 변경이 있으면 영향과 검증 입력을 다시 확인한다. 예를 들어 공유 API가 바뀌면 소비자의 계약 호환성을 기존 검사로 검증한다.

## 구현 범위와 후속 검증

실행 확인 상태와 남은 과제는 [백로그](OPEN-ISSUES.md), 동일 샘플의 양쪽 에이전트 인수 기준은 [PoC 명세](acceptance.md)를 따른다. 사례에서 확인한 과거 실행을 최신 전체 흐름의 검증 완료로 해석하지 않는다.

주제별 문서의 구현 재현성 확인과 문서 예시 실행 결과는 [검증 보고서](../validation/design-1.0-implementation-review.md)를 참고한다.

## SpecThread 제품을 구현할 때

[제품 구현 절차](implementation-standard.md)에 따라 구현·테스트 뒤 설계 원문과 다시 대조하고 누락을 보완한다. 대상 앱 개발 명령과 제품 저장소의 구현 작업을 혼동하지 않는다. 새 Core의 Sync·선택적 재검증 실행은 [정합화](reconciliation.md)와 [검증](06-verification.md)을 따른다.

설치·업데이트는 배포 폴더의 `python3 specthread install` 또는 `python3 specthread update`로 진행한다. Core 세부 설치 명령은 내부에서 처리하며 실제 두 명령의 확인 결과는 [설치 검증](../validation/installation-two-command-review.md)에 기록한다.

## 질문과 단계 안내

init에서 필요한 질문 하나씩 답하고, 구체적인 다음 작업 제안에 “진행해”라고 답해 이어간다. 현재 단계·핵심 결과·다음 선택을 짧게 표시한다. 새로운 범위와 필수 승인은 별도로 확인하며 실제 준비 조건은 Core로 재검사한다. [대화·표시 계약](conversation-flow.md)

## 작업 중 실행 확인

초기화와 개발은 필요한 읽기 전용 시작 검사를 한 번의 호출로 실행한다. 이미 동의한 범위의 일상 작업은 이어서 진행한다. 에이전트의 권한 확인이나 SpecThread의 적용 승인 요청이 나타나면 화면에 표시된 실제 작업과 영향을 확인한다. [승인과 단계 이동](conversation-flow.md)

## Monitor 선택 설치 및 실행

초기 설치에서 Monitor를 선택하거나 기존 프로젝트에 `python3 specthread install --monitor --project PROJECT`로 추가한다. 프로젝트에서 `./monitor` 또는 Windows의 `.\monitor.cmd`를 실행한다. 새 에이전트도 함께 열려면 `--session`을 붙인다. [Monitor 사용법](../../monitor/README.md)


## 변경 위험에 비례해 개발하기

sdd-develop은 요청·계약·의존성에 따라 Lightweight/Standard/Strict를 선택한다. 경량은 유효한 기존 계획과 변경 태스크를 활용하며, 일반 기능·신규 Feature는 필요한 공식 절차를, 고위험 계약은 구체적 확인과 확대 검증을 사용한다. 단순 파일 수로 위험을 정하지 않는다.

검증 정의는 verification.yaml에서 재사용하고 같은 Work Item의 유효 PASS는 완료 직전에 무조건 다시 실행하지 않는다. 바뀐 검사·실패·누락 증거만 재검증한다. 일반 과정은 최초 요청 범위에서 이어가며 Strict·범위 확대·필수 정책 완화는 실제 사용자 판단을 받는다. 모든 프로파일의 완료 조건은 동일하다. [상세 정책·Core 예시](verification-profiles.md)


## 작은 변경을 이어서 개발할 때

대상 Feature·관련 요구와 공통 제약부터 확인하고 근거가 있는 의존 경계만 넓힌다. 유효한 기존 plan·테스트·판단을 활용하고 바뀐 정보만 수정한다. 테스트 수준 L1(in-process)·L2(실제 의존)·L3(live 서버)·L4(E2E)는 프로파일과 독립적으로 충분한 조합을 선택한다. 실제 서버가 필요하면 기존 판단 기록에 이유를 남긴다. 결함은 가능한 회귀 검사를 추가하고 불필요한 전체 문서 읽기·추가 보고서는 만들지 않는다.

필수 Analyze/Converge는 공식 원형대로 수행한다. 선택적 호출 여부와 문서 수정 조건은 [공식 연동](spec-kit-integration.md)·[산출물](01-artifact-model.md), 완료 차단과 현재 결과는 [검증](06-verification.md)을 따른다. 기존 사용자 변경과 필수 전체 검사는 보존한다.

## 독립 개발 선택

기본 Direct는 기존 사용 순서를 유지한다. Isolated를 명시적으로 선택하면 같은 세션에서 Work별 사본을 사용하고 준비된 작업을 FIFO로 최신 원본에 검증·반영한다. Git은 사용자가 처리한다. 사본은 보안 권한을 주지 않으며 미확인 Adapter는 진입을 차단한다. [명령·상태·예외 상세](parallel-development.md).
