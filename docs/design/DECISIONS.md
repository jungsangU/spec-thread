# 결정 기록

| ID | 상태 | 결정 | 논의 근거 | 상세 |
| --- | --- | --- | --- | --- |
| D-001 | 확정 | Greenfield와 Brownfield에 동일 Artifact Protocol 적용 | 입력이 달라도 후속 개발 규칙과 산출물 해석을 공유 | [모델](01-artifact-model.md) |
| D-002 | 확정 | C 방식. Artifact 파일, Claim, Evidence, Source Symbol 연결 | 대형 문서의 재검토 범위와 사실별 파일의 파편화를 줄임 | [모델](01-artifact-model.md) |
| D-003 | 확정 | 대상 Git의 `.sdd/`에 Markdown + YAML Frontmatter 중심으로 저장 | 사람이 읽고 Git에서 검토하며 도구가 메타데이터를 파싱할 수 있음 | [모델](01-artifact-model.md) |
| D-004 | 확정 | Spec은 의도, Git Source는 구현 사실, Verification은 실행 근거 | 기존 구현이나 추론이 승인된 의도로 취급되는 오류를 방지 | [권위](02-source-of-truth.md) |
| D-005 | 확정 | Claim별 R0~R3 승인과 Intent·Implementation·Verification 분리 | 전수 승인 비용과 전면 자동 승인에 따른 정책 오인을 줄임 | [상태](04-artifact-lifecycle.md) |
| D-006 | 확정 | Harness Only. Spec → Claim → Code → Verification 후 코드와 관련 Artifact 동시 커밋 | 의도·구현·검증의 일치 시점을 한 revision으로 추적 | [Git](08-git-integration.md) |
| D-007 | 확정 | 예외적인 외부 변경은 사용자 요청과 승인에 따른 수동 Reconciliation | 예외 복구 기능을 제공하면서 정상 흐름에 상시 감시를 추가하는 부담을 줄임 | [Git](08-git-integration.md) |
| D-008 | 확정 | 코드에 맞춰 승인된 Spec을 자동 변경하지 않음 | 코드 변경만으로 업무 정책이 바뀌는 것을 방지 | [권위](02-source-of-truth.md) |
| D-009 | 확정 | Harness 설계는 `docs/design/`에 문서, 결정, 근거, Mermaid와 백로그를 누적 | 단계별로 설계 변경과 판단 근거를 추적 | [목차](README.md) |

~~~mermaid
flowchart LR
  A["초기안: 외부 커밋 자동 보정"] --> B["외부 변경을 예외로 한정"]
  B --> C["D-006 정상 개발에서 동시 커밋"]
  B --> D["D-007 수동 Reconciliation"]
  D --> E["D-008 승인된 Spec 보호"]
~~~

## 변경 이력

| 버전 | 날짜 | 변경 |
| --- | --- | --- |
| v0.1 | 2026-11-11 | D-001~D-009 최초 기록. 외부 변경 자동 보정 초기안을 수동 복구 정책으로 대체. 대상 Git revision을 비교 기준으로 유지. |

출처는 SDD 산출물 관리 표준 및 최초 로컬 산출물 요청이다. 결정 ID는 이번 작업에서 부여했다. 이후 결정이 바뀌면 새 ID와 대체 관계를 기록한다.
