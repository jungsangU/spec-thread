# 06 검증과 정합성

| 검증 | 질문 | 실행 주체 |
| --- | --- | --- |
| Discovery Gate | 분리·통합 전후에 요구사항, 예외 및 계약이 보존되는가. Brownfield 명세는 현행 근거와 맞는가 | 에이전트의 의미 검토와 공식 명세 품질 검사 |
| 명세 품질 | 요구사항이 명확하고 측정 가능한가 | 공식 체크리스트 흐름. 사용자 정의 체크리스트의 검토 상태는 검토자가 관리 |
| 산출물·구현 분석 | 명세→계획→작업→구현이 일치하는가 | 에이전트가 공식 `analyze`·`converge`를 전제에 맞게 사용 |
| 동작 | 프로젝트 테스트·빌드·정적 검사가 통과하는가 | 프로젝트 검증 명령 |
| 구조 | UUID, 상태, 경로, 참조가 유효한가 | `sdd-core validate` |
| 사용자 반영 전 검토 | 반영하려는 변경이 검증 입력과 일치하는가 | 사용자 검토와 기존 검사 |

Core 0.4.0의 완료 명령은 저장된 필수 Gate 집합과 실행 결과를 대조한다. 임시 complete 계획의 임의 검사 명령으로 이를 대체할 수 없다. 모든 필수 결과가 현재 유효한 PASS이고 실제 증거·영향 근거가 있어야 completed를 저장한다.

**사용자 통합 후 검증**은 통합 결과로 검증 입력이 달라지면 기존 검사와 영향 분석을 다시 실행한다. Work Item의 과거 통과 근거는 원래 입력의 이력으로 유지한다.

## 필수 Gate 정의와 실행 계약

SpecThread Skill은 기존 설계·프로젝트 검증 규칙·Feature와 Work Item 특성을 분석하고 개발·검증 단계 진입 전에 적용할 필수 Gate 집합을 확정한다. 필수 집합의 정의와 실행 결과는 각각 기록한다.

| 기록 | 최소 내용 |
| --- | --- |
| Gate 정의 | Gate ID, 검증 대상, 실행 명령 또는 검증 방법, 필수 여부, 증거 요구사항 |
| 적용 근거·변경 이력 | 해당 작업에 필요한 이유, 적용 범위, 목록 또는 정의가 달라진 근거와 변경 내역 |
| 실행 결과 | Gate ID에 대응하는 판정, 실제 실행 결과, 실행 명령의 종료 코드, 대상, 증거 참조 및 관련 입력 Fingerprint |

Core는 확정된 정의의 구조·일관성·적용 결과의 대응·증거와 완료 조건을 결정론적으로 검증한다. 필수 목록의 임의 누락·축소로 우회하지 못하도록 적용 근거와 변경 이력을 대조한다. 의미적으로 충분한 검사인지 판단하고 근거를 수집하는 책임은 Skill에 있다.

기존 Spec Kit 명령과 프로젝트의 테스트·빌드·정적 분석을 재사용한다. 실행 명령 없이 공식 검토 방법을 쓰는 경우에도 그 방법에 맞는 실제 결과와 증거를 요구한다. 별도 중복 테스트 엔진은 추가하지 않는다.

| 필수 Gate 결과 | 후속 단계 및 완료 |
| --- | --- |
| `PASS` | 해당 정의·대상·입력에 유효한 증거가 있을 때 통과 |
| `FAIL`, `NOT_RUN`, `UNKNOWN`, `STALE` | 해당 Gate가 요구되는 후속 단계와 `completed` 전환 차단 |

모든 적용 가능한 필수 Gate가 유효한 `PASS`여야 완료한다. 증거 경로는 존재와 유효성을 확인하며 과거 Git 근거는 해당 역사적 기준에서 해석한다. 임의 성공 명령이나 성공 문자열만으로 필수 Gate를 충족했다고 판정하지 않는다.

코드·공식 산출물·필수 Gate 정의가 바뀌면 관련 PASS의 현재 유효성을 재평가한다. 무효화되면 재검증한다. 과거 `completed` 이력과 당시 결과는 보존하고 후속 작업에서 사용할 현재 근거인지 판단한다. Gate 결과는 Work Item 상태와 독립적이며 별도 Work Item 상태를 추가하지 않는다.

Core 0.4.0은 Gate 정의를 work-items.yaml의 `gate_revisions`, Gate별 실행 이력을 `gate_results`에 저장한다. 정의 변경은 기존 이력을 보존하고 새 정의 해시로 이전 결과를 무효화한다. 완료 이력의 결과는 수정하지 않으며 stage-check에서 현재 유효성만 판단한다. 의미적 검사 충분성은 Skill이 검토한다.

## Core 0.4.0 명령과 입력 예시

`gates ID PLAN.json`으로 집합을 미리 보고 검토한 해시를 `--confirm HASH`로 확정한다. 계획은 아래처럼 작성한다. paths는 실제 검사 입력을 명시하며 신규 구현 예정 파일은 정의 시점에 없어도 실행 시에는 존재해야 한다. basis는 실제 검증 규칙·적용 근거 파일이다.

```json
{
  "reason": "변경 계약에 프로젝트 테스트 규칙 적용",
  "basis": ["verification-rules.md"],
  "gates": [{
    "id": "project-tests",
    "rationale": "변경 Feature의 계약과 예외를 확인",
    "targets": ["019a1234-5678-7abc-8def-123456789abc"],
    "required": true,
    "required_for": ["complete"],
    "kind": "command",
    "command": ["python", "-m", "unittest", "discover", "-s", "tests"],
    "paths": ["app.py", "tests/test_app.py"],
    "evidence": ["test-results.txt"],
    "evidence_requirement": "기존 테스트 도구가 보존한 실제 결과 보고서"
  }]
}
```

예시 명령·경로는 프로젝트의 실제 검사와 결과 보존 방식으로 교체한다. 표준 출력·오류·종료 코드는 기존 검사 실행기가 수집한다. evidence 파일의 존재·내용 해시와 입력 해시를 확인하며 검사 중 파일 또는 Work Item/Gate 계약이 바뀌면 결과 확정을 차단한다.

- `gate-run ID GATE_ID`는 등록된 command만 실행하고 결과를 누적한다. 임시 명령이나 외부 PASS로 command Gate를 대체할 수 없다.
- 공식 Spec Kit 검토는 `kind: review`, `method`, 실제 evidence 보고서를 정의한 뒤 `gate-run ID GATE_ID --review REVIEW.json`으로 결과를 기록한다. REVIEW는 status(PASS/FAIL/UNKNOWN/NOT_RUN), reviewer, conclusion을 포함한다.
- `stage-check ID develop|verify|complete`는 해당 단계와 앞 단계의 필수 Gate를 검사한다. complete에서는 모든 required Gate가 PASS여야 한다.
- `complete ID PLAN.json`은 actual_features, 비어 있지 않은 findings, 실제 evidence[].ref를 받는다. 선언 범위를 초과한 변경은 반영 전에 작업 범위와 Gate 집합을 다시 검토해야 한다.

최신 실행이 FAIL 또는 UNKNOWN이면 과거 PASS로 대체하지 않는다. 관련 입력·증거·Gate 정의가 바뀐 PASS는 STALE이다. 실제 명령의 의미적 적절성과 검토 보고서의 충분성은 Skill이 근거로 판단한다.

## Fingerprint와 재검증 범위

개발 중에는 영향 분석에 따라 변경 파일, 영향받은 계약과 Feature 관련 소스 및 공식 산출물을 검증 입력으로 선정한다. 검증 통과 시 내용에 기반한 Fingerprint를 기록한다. 영향받은 검증은 재실행하고 동일 입력으로 확인 가능한 통과 결과만 재사용한다. 입력 재구성이 모호하면 해당 결과를 재사용할 수 있는 근거를 추가 확보한다. 완료 시 Work Item의 필수 검증을 모두 만족해야 한다. 사용자 Git 통합으로 검증 입력이 달라지면 기존 필수 검사와 영향 검증을 다시 실행한다.

검증 환경은 변하지 않는다는 운영 전제를 사용자가 보장한다. 런타임 버전 및 설치 환경 수집·감지·환경 Fingerprint는 제외한다. Fingerprint는 검증한 파일의 유효성 확인용이며 브랜치 감시나 Git 기준 확인에 쓰지 않는다. 완료 Work Item의 과거 Fingerprint와 증거를 이후 검증으로 덮어쓰지 않는다. 테스트 결과를 증거로 참조할 때 공식 태스크 체크와 실행 근거를 구분한다. 현재 Gate별 paths·결과·해시로 입력과 증거의 유효성을 추적한다. 삭제와 이름 변경으로 기존 경로가 없어지면 해당 PASS는 STALE이다. Skill이 새 경로와 정의를 검토하고 필요한 Gate를 다시 실행한다. Core 0.4.0의 승인형 gate-refresh는 아래 규칙으로 이름 변경 후보와 재실행 대상을 제시한다.

Discovery 판정은 [초기 분석](03-analysis-standard.md), 동기화 필수·품질 Gate는 [버전 동기화](version-sync.md), 제품 PR의 CI는 [Git 운영](08-git-integration.md)에 정의한다. 이 문서는 Work Item 검증 집합·실행 결과의 계약을 소유한다.

## Core 0.4.0 필드·단계·결과 재현 계약

### Gate 계획의 필수 제약

- reason은 비어 있지 않은 문자열, basis는 프로젝트 내부의 비어 있지 않은 실제 근거 파일 ref 배열이다.
- gates에는 최소 한 개의 required=true Gate가 있어야 하며 필수 Gate들의 targets 합집합이 현재 Work Item 범위를 모두 포함해야 한다. id는 집합 내에서 중복할 수 없다.
- 각 Gate는 id/rationale/targets/required/required_for/paths/evidence/evidence_requirement/kind를 가진다. targets는 비어 있지 않은 선언 범위 UUID 배열, required는 boolean, required_for는 develop/verify/complete 중 하나 이상의 배열이다. paths는 비어 있지 않은 파일 경로 배열이다.
- command는 kind=command일 때 비어 있지 않은 argv 문자열 배열이며 셸 문자열로 실행하지 않는다. 증거 출력 파일은 정의 때 없을 수 있으나 실행 결과 판정 때 필요하다.
- kind=review에는 method 문자열이 필요하고 evidence 파일은 정의 검토 시점부터 존재해야 한다. reviewer·conclusion·status의 제출이 실제 보고서 내용 검토를 대신하지 않는다.

### 단계 적용 순서

required=false Gate는 필수 차단 집합에 넣지 않는다. develop에서는 required_for에 develop이 있는 필수 Gate를, verify에서는 develop 또는 verify가 있는 필수 Gate를, complete에서는 모든 필수 Gate를 확인한다. verify 전용 Gate 실행 전에 develop 조건을, complete 전용 Gate 실행 전에 develop·verify 조건을 검사한다. 완료 단계 Gate만 있는 집합도 개발 진입 전에 집합 자체는 확정돼 있어야 한다.

최신 집합의 무결성·basis 파일 해시·Work Item 범위 일치를 먼저 검사한다. Gate 목록을 바꾸면 revision 전체 해시가 달라져 이전 집합에서 실행한 결과를 현재 PASS로 사용하지 않는다. 실행은 pending/in_progress/suspended 작업에서 기록할 수 있으며 종료 작업에서는 거부한다. 의미상 올바른 단계 진행은 Skill이 안내한다.

### 저장 필드와 해시

| 레코드 | 필드 |
| --- | --- |
| gate_revisions 원소 | work_item, previous(이전 revision 배열 해시), scope, gates, reason, basis(증거 해시 매핑), inputs(경로→해시 또는 신규 예정 파일의 null), hash |
| gate_results[Gate ID]의 실행 원소 | status, definition_hash, inputs; 성공 판정 시 evidence; command는 execution(command/exit_code/stdout/stderr), review는 review(status/reviewer/conclusion); 오류 시 error |

revision.hash는 hash 자체를 제외한 revision 객체의 내용 해시다. definition_hash는 Gate 정의에 `revision: 최신 revision.hash`를 추가한 객체의 내용 해시다. 완료 fingerprint는 그 완료에 적용된 최신 Gate 실행들의 inputs를 합친 경로→파일 해시 객체의 내용 해시다. 같은 경로는 최신 입력 값 하나로 합친다. 직렬화는 [데이터 모델](01-artifact-model.md)의 객체 내용 해시를 따른다.

별도 `fingerprint PATH ...` CLI는 경로 중복을 제거·정렬한 `[path, 파일 SHA-256 hex]` 배열을 `json.dumps(..., ensure_ascii=True, separators=(",", ":"))`의 ASCII 바이트로 해시한다. 이는 완료 fingerprint의 객체 형식과 다르므로 서로 대체하지 않는다.

### 증거와 결과 판정

새 Gate의 증거는 프로젝트에 보존한 비어 있지 않은 파일 ref이며 외부 URL을 받지 않는다. `파일#L정수`는 해당 줄의 존재도 확인하고 파일 전체 바이트를 해시한다. 일반 제목 anchor의 의미까지 자동 검증하지는 않는다. 과거 경로가 없어지면 path_redirects로 아카이브 위치를 해석할 수 있다.

최신 실행이 없으면 NOT_RUN이다. 최신 실행이 PASS가 아니면 그 결과를 사용하고 이전 PASS로 되돌리지 않는다. PASS 기록의 입력·증거 키 집합이나 실행 명령·정상 종료·검토 제출이 정의와 맞지 않으면 UNKNOWN, 정의·파일·증거 해시가 달라졌거나 파일이 없어졌으면 STALE이다. command의 비정상 종료·증거 누락은 FAIL이며 실제 실행 중 입력 변경은 STALE로 기록한다. 실행 중 Work Item/Gate YAML이 바뀌면 결과 저장을 거부한다.

complete는 검증 명령을 재실행하지 않는다. 현재 진입 조건, 비어 있지 않은 findings, 선언 범위, 최신 필수 Gate와 실제 evidence를 검사하고 inputs가 비어 있지 않을 때만 completed를 저장한다. 테스트를 실행한 사실·파일 존재 검사는 의미상 충분성의 증명이 아니며 Skill이 실제 계약·보고서를 검토한다.

## Core 0.4.0 선택적 재검증

`gate-refresh ID [--stage develop|verify|complete]`는 읽기 전용으로 현재 action(reuse/run), renames, ambiguous, 새 Gate 정의와 입력 해시·approval_hash를 제시한다. 같은 명령에 승인된 `--confirm HASH`를 주면 현재 미리보기를 재계산하고 일치할 때만 처리한다. 이름 변경 없는 필요한 검사 실행도 승인을 받는다.

- 현재 최신 PASS가 정의·입력·증거에 유효하면 실행을 생략한다. 최신 FAIL/UNKNOWN을 건너 과거 PASS를 가져오지 않는다. 무효·미실행 command Gate만 기존 실행기로 다시 실행하고 실패하면 뒤 검사를 멈춘다.
- 사라진 입력·증거의 마지막 파일 해시와 같은 바이트의 프로젝트 내부 파일을 찾는다. 표준 의존성·Git·에이전트·캐시 폴더는 제외한다. 후보가 정확히 하나인 경우만 이름 변경으로 제안한다. 없음·복수 후보 또는 경로가 명령 문자열 내부에 포함돼 안전하게 바꿀 수 없는 경우 차단한다. 동일 내용 탐지는 의미적 동일성 보장이 아니며 사용자가 제안을 승인한다.
- 승인된 변경은 Gate paths/evidence와 정확히 일치하는 argv 경로, 활성 Source Map 경로를 갱신하고 새 Gate revision을 기록한다. 변경된 Gate는 다시 실행한다. analysis 근거가 무효라면 기존 분석 재확정도 필요하다. 분석 해시를 자동으로 바꿔 READY를 만들지 않는다.
- 새 revision으로 옮길 때 Gate 정의 자체가 동일하고 최신 결과가 현재 유효한 PASS인 항목만 결과 사본을 추가한다. reused_from에 work_item/gate/run_index/definition_hash를 기록하고 새 definition_hash를 계산한다. 원래 revision과 실행 이력은 바꾸지 않는다. 다른 Work Item의 결과를 자동으로 가져오지 않는다.
- review Gate는 실제 제출이 필요하면 review_required/BLOCKED로 멈춘다. 자동 PASS를 작성하지 않는다. 개발→검증→완료의 기존 선행 Gate를 유지한다. 종료 Work Item은 갱신하지 않는다.

반환은 work_item/results/status(PASS 또는 BLOCKED)이며 각 results에 gate/status/action을 기록한다. 미리보기는 0, 적용 검사 차단은 2, 승인·구조·분석·모호성 오류는 1이다. 이름 변경 승인 후 경로·정의 갱신과 검사 실패가 생겨도 자동 롤백하지 않으며 기존 진행 작업에서 원인을 해결한다. 별도 검증 엔진·자동 감시·세션 관리 계층을 추가하지 않는다.
