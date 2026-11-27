# 병렬 개발과 Core 동시성

설계 2.0 · ST-44~ST-64 · Core 0.6.0. 본 문서는 Decision 18~38의 원본이다. [Work Item](04-artifact-lifecycle.md)·[Gate](06-verification.md)·[Git](08-git-integration.md)의 기존 정책을 유지하며, 이전의 Core 잠금·FIFO·작업 사본·반영 복구 제외 정책을 이 범위에서 대체한다. 구현 및 실제 에이전트 검증 상태는 [검증 보고서](../validation/parallel-development-review.md)를 따른다. 확정 설계와 미검증 지원 환경을 혼동하지 않는다.

## 모드와 책임

| 구분 | Direct | Isolated |
| --- | --- | --- |
| 개발 위치 | 원본 프로젝트 | Work Item별 전체 논리 복제 |
| 기본값 | 기존·비대화형 설치의 기본 | 신규 설치에서 사용자 선택 |
| Core 관리정보 | 짧은 잠금·레코드별 CAS | 동일 보호 + 사본 내부 개발 |
| 앱 코드의 병렬 편집 | 사용자가 충돌 방지 | 독립 사본에서 개발 후 순차 통합 |
| 완료 | 기존 완료 Gate 후 completed | 최신 원본 통합·검증·반영 성공 후 completed |

사용자는 세션을 열고 작업을 분배한다. Core는 에이전트를 실행·재시작·복원하지 않는다. 중앙 서버·Redis·SQLite·상주 오케스트레이터·Git branch/worktree/merge/stash를 도입하지 않는다. Core는 결정론적 파일 처리·로컬 순번·소유권·기록·기존 검사 호출을 맡고, 네이티브 Skill은 동일 세션의 도구 대상 지정, 의미 분석·간접 영향·복잡한 충돌 해결·기존 승인 연결을 맡는다. 파일 격리는 보안 Sandbox가 아니다. 임의의 네이티브 쓰기 도구를 Core가 가로채지 못하므로 실제 도구 범위·권한 검증과 Skill 준수가 필수다.

모드 설정은 기존 `.specify/spec-thread.json`의 `development`에 둔다. `mode`로 조회하고 `mode direct|isolated`로 명시적으로 변경한다. 활성 Work Item/Workspace 또는 미완료 반영 중에는 모드·Runtime·복제 제외 변경을 차단한다. 기존 설정을 업데이트가 초기화하지 않는다. `resolution_attempts` 기본 3, `resolution_seconds` 기본 300이며 명시적으로 조정할 수 있다. 자동 모드 전환은 없다.

## Runtime과 복제

원본 Baseline은 기존 위치·스키마를 유지한다. 기본 Runtime은 원본의 형제 `.spec-thread-runtime/<정규화된 원본 경로 SHA256>/`이며, `mode isolated --runtime-root ABS`로 외부 절대 경로를 지정할 수 있다. 원본 내부·원본의 조상·다른 프로젝트 등록은 거부한다. 기존 Runtime 이력을 묵시적으로 이동하지 않는다. 안정적인 원본 관리 잠금은 형제 `.spec-thread-locks/<project hash>/`에 두어 Runtime 설정 변경과도 경쟁하지 않게 한다.

| 위치 | 내용·보존 |
| --- | --- |
| workspaces.json | schema_version 1, 원본·Work UUID·토큰·경로·별도 통합 상태·실행 설정·FIFO 등록 |
| work/UUID/snapshot | 최초 실제 파일 내용·모드·빈 디렉터리. 매니페스트만 저장하지 않음 |
| work/UUID/workspace | 최초 네이티브 개발 대상. 공식 산출물·Baseline·앱 코드 모두 독립 |
| work/UUID/candidate | 최초 Snapshot + 작업 변경 + 최신 원본의 통합 후보. 생성 후 활성 개발 대상 |
| work/UUID/candidate-history | 원본 재변경 시 아직 반영되지 않은 후보 수정 보존. 미해결 경로를 명시해 재검토 |
| work/UUID/publication | 검증된 후보의 완료 상태를 준비하는 내부 이미지. 에이전트 편집 금지 |
| work/UUID/temp | 해당 Work의 임시 파일·명령 프로세스 소유권 |
| locks, transaction.json, backup | 커널 소유권, 반영 저널, 실제 파일 백업·단계 기록 |

COW/reflink를 우선 시도하고 미지원이면 일반 복제로 대체한다. 하드링크는 금지한다. `.git`, 의존성·가상환경·캐시와 Runtime은 제외하고 프로젝트 실행에 필요한 소스·설정·테스트·공식 산출물은 복제한다. 추가 제외는 명시적 설정이며 Core/Skill/관리 파일을 제외해 검사를 우회하지 않는다. symlink·특수 파일·경로 탈출은 추측 복사하지 않고 차단한다. 필요한 의존성·DB·Redis 등은 기존 프로젝트 방법으로 준비한다. 복제 전후 파일/디렉터리 지문이 다르면 일관된 Snapshot으로 인정하지 않는다.

성공은 증거 보존 뒤 사본을 정리한다. 실패·보류는 임의 만료 삭제하지 않는다. `workspace usage`는 논리 크기·보고된 할당량을 구분하며 COW의 고유 물리 사용량으로 주장하지 않는다. `workspace cleanup`은 실제 삭제 대상 미리보기·확인 해시로 종료·미등록 잔여물만 정리한다. 명시적 discard는 실제 Work 기록·Feature 문맥·증거를 보존하고 원본 Work를 failed로 종료하며 provisional Feature를 활성 등록하지 않는다.

## 동일 세션 진입과 공식 Spec Kit

1. 원본에서 기존 Feature 개발 preflight 후 `start FEATURE_UUID ...`. Isolated는 pending Work UUID와 사본 경로를 반환한다. 새 Feature는 `start --discovery`로 영구 Feature UUID 없이 사본을 만들고, 공식 Discovery READY 후 Feature 등록 및 최초 `scope-expand --apply`로 범위를 결합한다. 이후 확대는 기존 승인을 유지한다.
2. 프로젝트 최초 `/sdd.init`은 활성 Work가 없는 원본에서 전역 초기화한다. 개발 중 신규 Feature Discovery는 해당 사본에서만 한다.
3. 같은 Codex/Claude 세션의 실제 편집 대상·명령 cwd·Sandbox 쓰기 권한·원본 Core 직접 변경 차단·자연 Hook 원본 연결을 확인한다. `workspace enter ID --plan ENTRY.json`은 agent/session/scope, 여섯 checks, 선택 대상에 존재하는 실제 evidence, execution 설정을 받는다. 미확인·권한 거부·다른 세션은 차단하며 Direct로 자동 Fallback하지 않는다. 임의 true 선언은 실제 PoC를 대체하지 않는다.
4. 각 네이티브 도구에 절대 작업 경로를 지정한다. shell cd는 다른 도구의 루트를 바꾸지 않는다. Claude Read/Edit/Write와 Bash, Codex apply_patch와 실행 cwd를 각각 확인한다. Windows 네이티브 경로와 Git Bash 파싱을 구분하고 기존 Hook runner의 argv/인코딩 정책을 재사용한다.
5. 공식 Spec Kit의 형식·라이프사이클·스크립트는 수정하지 않는다. Git 없는 사본에서 공식 지원 경로를 사용한다. `SPECIFY_INIT_DIR`, `SPECIFY_FEATURE_DIRECTORY`, `SPECIFY_FEATURE_NO_PERSIST=1`을 명시하고 `GIT_CEILING_DIRECTORIES`를 사본 부모로 두어 상위 Git을 발견하지 않게 한다. 실제 공식 create/setup/prerequisite 실행과 에이전트 전체 흐름 검증은 별개다.

ENTRY의 checks는 same_session, absolute_edit_target, command_cwd, sandbox_access, origin_write_guard, hook_origin_link다. execution은 external_resources=none|isolated|serial, ports=dynamic|serial, 선택 env, relocatable을 포함한다. 세션·경로·설정이 바뀌면 재확인한다. 이미 등록된 후보로 대상이 변경돼도 도구·권한을 다시 확인한 뒤 scope=candidate로 진입한다.

## 잠금과 CAS

| 보호 | 범위 | 오래 수행하는 검사 |
| --- | --- | --- |
| Metadata | 최신 파일 재읽기·변경 적용·저장, 같은 Work 완료 검사와 저장 | 금지 |
| Integration | FIFO 선두의 후보 생성·영향 판단·기존 Gate·반영 | 허용, 다른 Work 개발·Snapshot 허용 |
| Snapshot/Publish | 실제 원본 Snapshot 복제와 원본 반영/복구 | 통합 테스트 제외 |
| Worker | 해당 통합 요청의 실제 커널 소유권 | 프로세스 종료 시 OS 해제 |

잠금 순서는 worker → integration → publish → metadata이며 필요 없는 상위 잠금은 잡지 않는다. PID·시간만으로 살아 있는 소유자의 잠금을 제거하지 않는다. 종료가 커널 소유권으로 증명된 대기 worker만 제거하고 다음 요청으로 진행한다. 세션 생존을 감시하는 상주 프로세스는 없다.

Core 관리 YAML은 읽은 원본/내 변경/저장 시 최신 문서를 비교한다. 독립 Work/Feature/Source Map·Gate 레코드 변경을 보존하고 동일 Work의 상충 변경은 거부한다. 목록은 의미 있는 ID·경로로 비교한다. 다른 Work가 work-items.yaml을 썼다는 이유만으로 실행 중 Gate 결과를 무효화하지 않는다. 해당 Work·정의·정책·실제 입력·증거·실행 환경이 바뀌면 저장/재사용을 차단한다. 승인 미리보기의 입력 해시 계약은 유지한다.

관리 Markdown은 `baseline-write FILE PLAN`의 expected_hash/text CAS, Source Map은 `source-map PLAN`의 base/updated로 갱신한다. 구조 검증 후 저장하며 의미적으로 변경이 없으면 쓰지 않는다. 네이티브 전체 파일 덮어쓰기로 공유 기록 보호를 우회하지 않는다.

## 준비·FIFO·통합

~~~mermaid
flowchart TD
  P["원본 pending + 독립 Snapshot/Workspace"] --> A{"동일 세션 도구·권한·Hook 확인"}
  A -->|확인| D["기존 공식 절차·구현·Gate"]
  A -->|미확인| B["진입 차단·원본 Fallback 금지"]
  D --> R["준비 검증 후 FIFO 등록"]
  R --> I["Integration Lock·최신 원본 후보"]
  I --> C{"구조·텍스트·의미·간접 영향"}
  C -->|충돌·사용자 결정| W["blocked·잠금 해제·사본 보존"]
  W -->|최신 원본 재검토| R
  C -->|해결| V["동일 Work 유효 결과 재사용·영향 Gate만 재검증"]
  V -->|실패| W
  V -->|통과| T["짧은 Publish Lock·저널 반영"]
  T --> F["원본 completed + integrated·증거 보존·사본 정리"]
~~~

준비된 in_progress Work의 기존 필수 절차·Gates가 충족돼야 FIFO에 등록한다. 순서는 시작/완료 시간이 아니라 **준비 등록 시점**이다. `workspace integrate ID --wait`는 현재 요청의 동기 대기이며 별도 Agent/스케줄러를 띄우지 않는다. 사용자 입력·승인·불명확 충돌 대기는 대기열에서 빠지고 잠금을 놓는다. 재개는 최신 원본으로 새 후보·영향 검토를 하며 옛 승인 해시를 재사용하지 않는다.

최초 Snapshot/Work/현재 원본 3방향 비교로 생성·수정·삭제·모드·디렉터리를 다룬다. UTF-8의 비중첩 줄 수정만 결정론적으로 병합한다. Baseline은 기존 스키마의 레코드 정체성으로 병합한다. Binary·겹침·모호한 변경은 충돌이다. 텍스트가 합쳐져도 계약·소비자·Feature 의존성의 충돌일 수 있으므로 Agent가 현재 원본 변화와 직접/간접 영향을 근거로 검토한다. Core의 findings 형식 검사는 의미 정확성 보장이 아니다.

`workspace preview ID`는 source/workspace/candidate 지문, 원본 매니페스트, changed/conflicts를 반환한다. 충돌 해결 계획은 해당 preview 해시와 경로별 write+실제 바이트 SHA256 또는 delete를 제출한다. 추가 직접 영향 수정에는 findings/reason이 필요하다. Work Item YAML은 Core 명령으로 수정한다. 원본이 바뀌면 해결의 입력 삼중항을 다시 확인하고, 후보에서 추가한 수정은 history로 보존해 명시적으로 재검토한다.

통합 계획은 preview 해시, nonempty findings, 기존 completion(actual_features/findings/evidence)을 갖는다. 소스 반영 직전까지 Work 상태는 in_progress다. 후보 안에서 completed로 조기 전환하지 않는다. 검증된 후보를 내부 publication 이미지에 복제해 최종 완료 검사 후 원본 반영한다.

## 검증·실행 환경·반복 한도

기존 위험도·Gate·절차·승인 체계를 그대로 호출한다. 동일 Work의 같은 정의·정책·입력·증거·실행 환경에서 유효한 PASS만 재사용한다. 다른 Work의 PASS를 복사하지 않는다. 파일 모드 변화, 삭제, 테스트 환경·Core·실행 설정·경로 변화는 유효성 판단에 포함한다. relocatable은 실제 경로 독립성이 확인될 때만 선택한다. 실패 원인을 고칠 때도 이미 유효한 다른 Gate를 반복 실행하지 않는다.

충돌 자동 해결은 기본 3회/5분이며 정상 장시간 테스트 시간은 해결 제한에 포함하지 않는다. 같은 원인·입력의 반복 실패나 진전 없음은 조기 중단한다. 검증 실패를 무제한 다시 돌리지 않는다. 한도 후 사용자 결정이 있으면 현재 해시의 resume_confirm으로 새 제한 시도를 허용한다. 해시는 동의 자체가 아니며 Skill이 실제 동의를 확인한다.

TMP/TEMP·테스트 결과·프로세스는 Work별이다. 포트는 동적 할당 또는 기존 순차 검증 잠금, 외부 DB/Redis는 기존 프로젝트의 독립 namespace/transaction/인스턴스 설정을 활용한다. 미확인 리소스는 병렬 실행하지 않는다. 실행 환경은 선택 변수만 추가하며 사용자 HOME/PATH 등을 바꾸지 않는다. 명령별 임시 감독 프로세스는 정확한 생성 시각을 포함한 소유권으로 자기 자식만 정리한다. 전체 시스템 프로세스를 임의 종료하지 않는다. 프로젝트가 daemon/double-fork 등 추적 밖 실행을 만들면 기존 정리 절차·실제 소유권 확인이 필요하고 지원을 추정하지 않는다. OS가 소유권 조회를 막으면 안전하게 차단한다.

## 반영·복구·상태

Work의 pending/in_progress/suspended/completed/failed와 별도 통합 상태 not_ready/waiting/integrating/resolving/blocked/integrated/discarded를 혼합하지 않는다. failed는 종료 상태이고 재시도는 새 UUID다. 수리 가능한 테스트 실패는 in_progress, 의도적 보류는 suspended다. 명시적 사본 폐기는 pending도 실패 이력으로 종료할 수 있지만 완료를 우회하지 못한다.

~~~mermaid
stateDiagram-v2
  [*] --> not_ready
  not_ready --> waiting: 준비 등록
  waiting --> integrating: FIFO 선두·Lock
  integrating --> resolving: 충돌 분석
  resolving --> blocked: 한도·사용자 입력
  integrating --> blocked: 검증 실패·외부 변경
  blocked --> waiting: 현재 입력 재검토
  integrating --> integrated: 원본 반영 + completed
  not_ready --> discarded: 명시적 폐기
  blocked --> discarded: 명시적 폐기
~~~

실제 바이트 백업·staging·before/after 저널을 반영 전에 준비한다. 생성·수정·삭제·디렉터리·모드 작업마다 현재가 예상 before인지 확인하고, 반영 후 전체 지문을 확인한다. 원본 Work completed와 registry integrated는 같은 저널 경계에 속한다. 물리적으로 여러 파일이 한 순간에 바뀐다고 주장하지 않는다. Core 협력 접근과 Snapshot/Publish 잠금으로 중간 상태 사용을 막는다. 비협력 외부 읽기/쓰기까지 원자적으로 통제하지 못한다.

비정상 종료 후 다음 Core 진입이 저널을 확인한다. 기록된 after와 정확히 같은 항목만 before로 되돌려 일관 상태를 복원하고, 외부 변경이 보이면 멈춰 보존한다. 임의 소스 덮어쓰기·Agent 재시작은 하지 않는다. 이는 Core 반영 트랜잭션 복구이며 사용자 Git rollback·실패 버전 업데이트 재개 기능과 다르다. 업데이트는 활성 사본/저널이 있으면 차단한다. 버전 실패는 기존대로 사용자 Git 원복 후 처음부터 재시도한다.

## Monitor 및 기존 기능 경계

Monitor는 원본에서 실행하고 등록된 같은 프로젝트의 Workspace/후보만 읽는다. 원본 Git diff와 사본 상태를 섞지 않고 선택 Scope·미반영 표시를 한다. 기존 세션 ID와 자연 Hook의 cwd를 등록 경로로 해석하여 원본 이벤트 저장소로 연결한다. 출처 경로를 믿고 미등록 외부 루트를 읽지 않는다. 기존 Living Office·Reader·CEO의 권한은 확대하지 않는다. Monitor 없이도 Core 통합이 동작한다.

수동 Sync의 의도·승인·외부 변경 계약은 유지한다. Isolated 정상 개발 통합과 외부 변경 Sync를 혼동하지 않는다. 원본 Sync는 활성 작업 종료 후 기존의 명시적 승인·kind=reconciliation Work·실제 Gate·complete 경로로 수행한다. 적용 시 Snapshot/Publish와 짧은 Metadata 잠금으로 입력을 재확인한다. 임의 모드 Fallback·자동 Sync·사본 통합 승인 전용은 금지한다.
