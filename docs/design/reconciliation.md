# 외부 변경의 수동 정합화

설계 1.1. 사용자가 명시적으로 요청하는 `sdd-sync`의 입력·승인·적용·검증과 실패 처리의 원본이다. 비교 기준, 실제 외부 변경, 승인된 의도와 적용 범위를 입력으로 받아 승인된 산출물·Baseline 갱신 및 재검증 결과를 반환한다. 일반 개발은 [Work Item 흐름](04-artifact-lifecycle.md)을 따른다.

## 실행 순서

명령 진입 시 [로컬 버전 계약](version-sync.md)을 확인한다.

1. **Inspect.** 사용자가 지정한 외부 변경과 비교 근거를 읽기 전용으로 확인한다. 실제 코드, 계약 및 공식 산출물에서 차이를 확인하고 영향 Feature·의존관계를 추적한다.
2. **Plan → Approve.** 승인된 의도와 구현의 차이, 필요한 공식 산출물의 검증·개정, Baseline 변경안을 제시한다. 사용자가 적용 범위를 승인하기 전까지 변경하지 않는다. 코드 또는 계약의 관찰 결과를 사용자 의도로 승격하지 않는다.
3. **Apply → Verify.** 승인한 범위만 반영한다. 변경 영향, 증거 및 Baseline 무결성을 재검증한다. 거절·차단·실패 시 차이와 남은 조치를 보고하고 사용자의 기존 파일을 보존한다. 외부 변경 자체를 자동으로 되돌리거나 덮어쓰지 않는다.

~~~mermaid
flowchart TD
  I["사용자가 지정한 외부 변경과 비교 근거"] --> R["Inspect · 읽기 전용 조사"]
  R --> P["Plan · 영향과 변경안"]
  P --> A{"사용자 승인"}
  A -->|거절| X["기존 파일 보존 · 결과 보고"]
  A -->|승인| C["Apply · 승인 범위만 반영"]
  C --> V{"Verify · 영향과 무결성 검증"}
  V -->|실패| X
  V -->|통과| O["정합화 결과 보고"]
~~~

## Core 0.5.0 승인·기록 계약

Skill이 조사·의미 판단과 사용자 승인을 맡고 Core `reconcile`이 승인된 입력·변경안 검증, 문서 반영과 기존 Work Item 기록을 처리한다. 비교가 모호하면 먼저 사용자에게 확인한다.

```json
{
  "base": {"kind": "git", "revision": "HEAD"},
  "features": ["<FEATURE_UUID>"],
  "reason": "외부 변경 조사 후 승인된 명세 정합화",
  "basis": ["sync-review.md"],
  "paths": ["app.py", "tests/test_app.py"],
  "findings": [{"assessment": "SAFE", "evidence": "현행 코드와 승인 의도의 차이를 검토"}],
  "changes": [{"path": "specs/example/spec.md", "content": "# 승인된 전체 명세 내용\n"}],
  "verification": {"reason": "정합화 후 검사", "basis": ["verification-rules.md"], "gates": []}
}
```

예시의 UUID·경로·전체 명세와 verification.gates를 실제 값으로 채운다. gates는 [기존 Gate 계획](06-verification.md)의 필수 정의로 모든 대상 Feature를 커버해야 하며 빈 배열은 거부한다. 의도 개정은 사용자에게 정확한 변경을 승인받아야 한다. Git 비교는 revision을 commit으로 해석해 승인에 묶는다. Git 기준 대신 사용자에게 받은 보존 자료를 쓰면 base는 `{"kind":"files","refs":["comparison-before.md"]}`다. 이는 과거 Git revision을 추정하는 기능이 아니다.

1. `sdd-core reconcile PLAN.json`은 읽기 전용으로 base/features/reason/findings/basis/writes/verification/inputs/approval_hash를 반환한다. 입력은 사용자가 지정한 코드·계약·검사 파일, 대상 공식 문서 트리, constitution·활성 선택자, 기존 Baseline과 설치 표식·Skill이다. 계획의 paths에 빠진 앱 파일의 의미 영향은 Skill이 추가 조사해야 한다.
2. 사용자 승인 뒤 같은 계획에 `--confirm APPROVAL_HASH`를 전달한다. Core가 비교 기준과 입력·전체 변경 내용을 재계산해 다르면 쓰기 전에 차단한다. 미리보기만으로 Work Item을 만들지 않는다.
3. 일치하면 새 UUIDv7 Work Item을 kind=reconciliation/status=in_progress로 생성하고 reconciliation에 승인 해시·base·inputs·reason·findings·변경 내용 해시를 보존한다. 기존 위반·미종료 이력은 덮어쓰지 않는다.
4. changes의 전체 내용을 승인 경로에 반영하고 Baseline을 검증한 뒤 승인 계획의 Gate 집합을 등록한다. 허용 쓰기는 `specs/` 아래 Markdown과 Baseline의 project.md/architecture.md/decisions.md/source-map.yaml이다. 앱·테스트·Work Item 이력·Feature 목록은 직접 쓰지 않는다. 등록·폐기는 기존 명령을 사용한다.
5. 반환된 work_item에 실제 gate-run 또는 승인형 gate-refresh를 수행하고 기존 complete 계획으로 완료한다. Sync는 변경으로 무효화된 Discovery를 고치기 위한 작업이므로 일반 개발 진입의 READY를 전제로 하지 않는다. 버전·활성 대상·구조·필수 Gate·증거·영향 차단은 유지한다. 일반 개발은 별도 analysis-record/develop-check로 유효한 Discovery를 다시 확정해야 한다.
6. 적용 중 구조·쓰기 실패는 해당 Sync Work Item을 failed로 끝내고 부분 적용·원복 범위를 보고한다. 자동 복구하지 않는다. 사용자 원복 후 새 승인·새 UUID로 재시도한다. 적용 이후 수정 가능한 검사 실패는 in_progress에서 수정·재검증한다. suspended/failed/completed와 이력 보존은 기존 상태 계약을 따른다.

다중 파일의 원자적 트랜잭션·세션 잠금·외부 변경 상시 감시·자동 Git은 제공하지 않는다. 승인 해시는 저장된 스냅샷과 재계산 결과의 일치를 검사하는 값이며 사용자 신원을 암호학적으로 인증하는 토큰이 아니다. 명시적 승인 확인은 Skill 책임이다. 실제 에이전트 실행 검증은 [ST-O9](OPEN-ISSUES.md)에서 추적한다.
