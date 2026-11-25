# 07 에이전트 설치와 명령 호출

| 작업 | Codex | Claude Code |
| --- | --- | --- |
| 설치 위치 | `.agents/skills/<이름>/SKILL.md` | `.claude/skills/<이름>/SKILL.md` |
| 초기화 | `$sdd-init` | `/sdd-init` |
| 개발 | `$sdd-develop` | `/sdd-develop` |
| 외부 변경 정합화 | `$sdd-sync` | `/sdd-sync` |

공식 GitHub Spec Kit의 원형·설치 경로를 유지하며 [통합 설치](installation.md)가 공식 설치·연동 명령을 내부 호출한다. 문서 재현 기준은 v1.4.0이다. `sdd-core install-skills codex|claude`는 공통 절차를 각 폴더에 설치하고 같은 위치에 내용이 다른 스킬과 충돌하면 오류를 보고한다. 기존 공식 설치를 교체할 필요가 없다.

## 호출과 처리 경계

논의상 `/sdd.init`, `/sdd.develop`, `/sdd.sync`는 각각 초기화, 개발, 외부 변경 정합화다. 배포 이름과 실제 호출 표기는 위 표를 따른다. 명령의 성공 종료 자체는 의미 분석의 통과 근거가 아니다.

- [아키텍처](architecture.md): 에이전트·Skill·Core·사용자의 책임.
- [공식 Spec Kit 연동](spec-kit-integration.md): 공식 기능, 활성 Feature 경로와 호출 전제.
- [초기 분석](03-analysis-standard.md): `discovery-gate`와 근거 제출 계약.
- [Work Item 개발](04-artifact-lifecycle.md): 네이티브 Skill이 안내하는 실행 순서.
- [외부 변경 Sync](reconciliation.md): 승인형 수동 작업.
- [검증 명세](06-verification.md): Gate 정의·결과·증거 검사.
- [Git·세션 운영](08-git-integration.md): 에이전트 선택·작업 분배·병렬 운영과 제외 범위.

실제 에이전트별 실행 검증 상태는 [백로그](OPEN-ISSUES.md)에서 관리한다.

## 작업 시작 검사와 실행 권한

초기화는 `python3 .specify/sdd-core preflight init --agent AGENT`로 설치 버전·Baseline을 확인한다. 개발은 `python3 .specify/sdd-core preflight develop --agent AGENT FEATURE_UUID ...` 한 번으로 해당 검증과 대상 개발 진입을 확인한다. 이 명령은 파일을 쓰거나 프로젝트 테스트를 실행하지 않는다. 기존 조회 명령도 계속 지원한다.

이미 동의한 범위의 통상 명령에는 별도의 SpecThread 확인 질문을 추가하지 않는다. 에이전트의 실제 실행 권한과 필수 SDD 승인 경계는 각각 해당 정책을 적용한다.

## 공통 CLI 호출·종료 코드

Core 명령은 `sdd-core [--root PROJECT] COMMAND ...`로 호출한다. --root 기본값은 현재 폴더이며 서브명령 앞에 둔다. JSON 계획 파일은 UTF-8 JSON 객체다. 네이티브 `sdd-sync`는 Skill이며 Core `reconcile`에 승인 계획을 연결한다. 같은 이름의 Core sync 서브명령은 없다. `version-sync`는 별도의 Core 서브명령이다.

| 종료 | 현재 CLI 의미 |
| --- | --- |
| 0 | 명령 정상 처리. discovery-gate의 CONDITIONAL/BLOCKED도 --issue-id를 사용하지 않았다면 구조상 정상 처리이므로 JSON verdict를 반드시 읽음 |
| 1 | 읽기·입력·구조·승인·전이·필수 Gate 차단 등 처리 오류. stderr에 이유를 출력 |
| 2 | gate-run이 PASS 이외의 결과를 기록함, discovery-gate --issue-id에서 UUID 미발급, version-sync 적용 후 전역 품질 차단. 명령 인자 파서 오류도 2이므로 출력 형식과 오류를 함께 판독 |

uuid/start/feature-register는 UUID 문자열, preflight는 phase/core_version/agent/features/status JSON, discovery-gate/gates 미리보기/gate-run/stage-check/feature-retire 미리보기/version-sync는 JSON을 반환한다. analysis-record·transition·complete·Gate 확정·아카이브 적용은 성공 시 별도 JSON을 출력하지 않는다. 성공 여부와 영속 파일을 확인한다. 명령 오류가 항상 전체 파일 원복을 의미하지는 않는다. 부분 적용 가능성이 있는 작업은 각 원본의 실패 처리 계약을 따른다.

Core 0.5.0의 reconcile/gate-refresh 미리보기·적용은 JSON 결과를 출력한다. gate-refresh가 실제 검사·검토 대기로 BLOCKED면 2를 반환한다. 상세 입력·출력·실패 처리는 [Sync](reconciliation.md)와 [선택적 재검증](06-verification.md)에 둔다.

일반 사용자 설치·업데이트는 [install/update](installation.md)를 사용한다. install-skills·version-sync는 그 내부 API와 고급 진단용이며 설치 가이드에서 사용자 필수 단계로 나열하지 않는다. 네이티브 Skill의 Core 호출은 프로젝트 runner를 통해 전용 환경으로 연결한다.

세 Skill의 공통 대화·표시 지침은 설치 시 `_conversation.md`에서 합성한다. 공개 명령은 세 개를 유지하며 UI가 지원하는 경우에만 질문 선택 기능을 사용한다. 공통 실행·표시 계약은 [대화형 진행](conversation-flow.md)에 둔다.

두 sdd-develop 설치본은 동일한 [위험도 프로파일·일반/예외 승인·절차 기록](verification-profiles.md)을 따른다. Core의 --apply 자동 경로와 --confirm 예외 경로는 에이전트의 명령 실행 권한을 대체하지 않는다. 공식 Skill은 고정 버전 원형을 유지하며 네이티브 Skill에서 필요한 호출만 선택한다.
