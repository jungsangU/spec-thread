# 06 검증과 정합성

| 검증 | 질문 | 실행 주체 |
| --- | --- | --- |
| Discovery Gate | 분리·통합 전후에 요구사항, 예외 및 계약이 보존되는가. Brownfield 명세는 현행 근거와 맞는가 | 에이전트의 의미 검토와 공식 명세 품질 검사 |
| 명세 품질 | 요구사항이 명확하고 측정 가능한가 | 공식 체크리스트 흐름. 사용자 정의 체크리스트의 검토 상태는 검토자가 관리 |
| 산출물·구현 분석 | 명세→계획→작업→구현이 일치하는가 | 에이전트가 공식 `analyze`·`converge`를 전제에 맞게 사용 |
| 동작 | 프로젝트 테스트·빌드·정적 검사가 통과하는가 | 프로젝트 검증 명령 |
| 구조 | UUID, 상태, 경로, 참조가 유효한가 | `sdd-core validate` |
| 사용자 반영 전 검토 | 반영하려는 변경이 검증 입력과 일치하는가 | 사용자 검토와 기존 검사 |

Core 0.3.0의 완료 명령은 저장된 필수 Gate 집합과 실행 결과를 대조한다. 임시 complete 계획의 임의 검사 명령으로 이를 대체할 수 없다. 모든 필수 결과가 현재 유효한 PASS이고 실제 증거·영향 근거가 있어야 completed를 저장한다.

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

Core 0.3.0은 Gate 정의를 work-items.yaml의 `gate_revisions`, Gate별 실행 이력을 `gate_results`에 저장한다. 정의 변경은 기존 이력을 보존하고 새 정의 해시로 이전 결과를 무효화한다. 완료 이력의 결과는 수정하지 않으며 stage-check에서 현재 유효성만 판단한다. 의미적 검사 충분성은 Skill이 검토한다.

## Core 0.3.0 명령과 입력 예시

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
