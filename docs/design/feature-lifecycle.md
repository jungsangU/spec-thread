# Feature 등록·재편·폐기

설계 1.0. Feature의 불변 식별, 병합·분할, 폐기 및 아카이브 처리의 원본이다. 레코드 구조는 [산출물과 데이터 모델](01-artifact-model.md), 확정 전 분석은 [Discovery](03-analysis-standard.md)를 따른다.

## 활성·폐기와 아카이브

`features.yaml`은 `active`와 `retired` Feature를 모두 영구 보존한다. Feature UUIDv7은 삭제·변경·재사용하지 않으며 `spec_path`는 이동에 따라 갱신하는 위치 정보다. Feature의 활성·폐기 상태는 Work Item의 개발 완료 상태와 독립적이다.

1. 병합·분할·제거 시 폐기 이유, 후속 Feature UUID와 결정 근거를 추적한다. 후속 기능이 없으면 참조를 임의로 만들지 않는다. 기존 UUID를 새 개념에 재사용하지 않고 활성 Feature 사이의 의존 관계를 재평가한다.
2. 폐기 Feature의 공식 산출물은 활성 `specs/`에서 `docs/sdd/archive/`로 이동해 보존한다. 공식 파일의 의미와 내부 구성은 유지한다. SpecThread가 위치·참조·활성 대상 제외를 관리하며 공식 Spec Kit의 라이프사이클은 변경하지 않는다.
3. 이동할 때 `spec_path`, 활성 Feature 컨텍스트, 문서 내부 링크, 검증 증거 참조 등 영향받는 경로를 확인하고 필요한 참조를 갱신한다. 기존 Work Item의 Feature UUID와 실행 이력은 유지한다. 완료 이력의 과거 실행 사실과 Fingerprint는 변경하지 않고 현재 참조 해석·경로 연결의 유효성을 확인한다.
4. `retired` Feature는 새 개발 대상에서 제외한다. 과거 Source Map은 이력으로 보존하고 현재 영향도·활성 품질 범위 계산에서 제외한다. 과거 매핑의 소스가 현재 트리에 없다는 이유만으로 활성 범위의 검증을 실패시키지 않는다. 아카이브 산출물과 역사적 참조의 무결성은 별도로 검증한다.
5. 변경·이동·검증 실패 시 작업을 중단하고 현재 결과와 실패 범위를 보고한다. 사용자가 Git으로 복구한다. 자동 Git 복구와 실제 자료 이동은 설계 문서 작업에 포함되지 않는다.

폐기 시 `retirement`에 reason/evidence/successors를 기록한다. `path_redirects`는 과거 specs 경로를 아카이브 경로로 연결해 불변 Work Item 증거 참조를 현재 위치에서 해석한다.

## 등록과 폐기 명령

`feature-register PLAN.json`은 READY인 신규 후보를 새 UUIDv7으로 등록한다. 계획에는 `feature`(name/spec_path/dependencies), 공식 spec·plan, `discovery`(mode/candidate/checks), 실제 `paths`와 `evidence`가 필요하다. 등록 뒤 `analysis-record`로 해당 Feature의 분석·의존성 근거를 확정해야 개발할 수 있다.

`feature-retire UUID PLAN.json`은 reason, evidence(로컬 결정 근거 파일), successors(UUID 배열), dependency_updates(활성 소비자 UUID별 새 dependencies 배열)를 받는다. 미종료 Work Item이 있거나 활성 소비자 의존 재평가가 빠졌으면 차단한다. 미리보기의 approval_hash를 검토하고 사용자 승인 후 `--confirm HASH`로 적용한다. 입력이 바뀌면 다시 승인받는다. 기본 아카이브 위치는 `docs/sdd/archive/<UUID>`다. 이동한 Markdown의 상대 링크와 해당 자료를 참조하는 링크·활성 Source Map을 갱신하고, 공식 활성 선택자가 폐기 기능을 가리키면 해제한다. 역사적 Work Item과 폐기 Source Map은 그대로 보존한다.

## Core 0.4.0 미리보기·적용 결과 계약

미리보기는 feature/from/to/reason/successors/dependency_updates/decision_evidence/moves/writes/inputs/features_hash와 approval_hash를 반환한다. moves는 이전→새 파일 경로, writes는 갱신할 파일별 내용 해시, inputs는 승인에 묶인 실제 파일 해시다. 승인 해시는 [객체 내용 해시](01-artifact-model.md)로 미리보기의 approval_hash 제외 내용을 계산한다. `--confirm` 적용 직전에 같은 계획과 현재 입력으로 미리보기를 다시 계산해 비교한다. 미리보기에는 파일 이동·쓰기 부수 효과가 없다.

successors는 중복 없는 다른 활성 Feature UUID 배열이며 후속이 없으면 빈 배열이다. dependency_updates는 영향받는 모든 활성 소비자를 포함해야 하고 새 의존성은 폐기 대상 대신 유효한 활성 Feature를 참조해야 한다. 미종료는 pending/in_progress/suspended를 뜻한다. 목적 아카이브가 이미 있거나 이동 대상 자료 안에 심볼릭 링크가 있으면 차단한다.

적용은 디렉터리 이동 → 필요한 문서·활성 Source Map·공식 선택자 갱신 → Feature 기록 저장 → Baseline 및 아카이브 내부 링크 검증 순서다. 현재 구현이 갱신하는 Markdown 링크는 인라인 링크·이미지 링크다. 참조형 링크·임의 설정 파일의 경로·환경 변수의 활성 경로가 모두 자동 교정된다고 가정하지 않는다. Skill은 계획·적용 검토에서 추가 참조와 공식 컨텍스트를 확인한다. 실패 시 부분 반영 가능성을 보고하고 사용자가 원복한 뒤 새 승인으로 처음부터 검토한다. 자동 원복·부분 복구 보장은 없다.

### 폐기 계획 예시

다음 예시는 현재 활성 소비자가 없고 후속 기능 없이 폐기하는 경우다. 실제 소비자가 있으면 dependency_updates에 빠짐없이 새 의존 배열을 제출한다.

```json
{
  "reason": "검증된 대체 작업 이후 예제 기능을 폐기",
  "evidence": "basis.md",
  "successors": [],
  "dependency_updates": {}
}
```
