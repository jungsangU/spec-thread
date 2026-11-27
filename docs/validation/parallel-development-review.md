# 병렬 개발·Core 동시성 구현 검증

2026-11-27 · 설계 2.0 · Core 0.6.0 · [명세](../design/parallel-development.md) · [실측 원자료](parallel-development-measurements.json)

## 판정

Core·네이티브 공통 Skill·설치·Monitor 연결을 구현했다. **전체 인수 완료는 아니다.** 실제 Codex 자연 Hook 연결, Claude 실행 환경, Windows, 외부 자원/병렬 서버 및 표에 표시한 종료 지점은 미확인이다. 이 제한을 없애기 위해 근거 없이 Adapter checks를 true로 만들지 않았다. 모형 테스트와 실제 네이티브 검증을 구분한다.

제품 구현 반복에서 발견한 whole-file Gate invalidation, 공유 기록 유실, 후보 수정 재생성 유실, 조기 completed, 원본 반영 중단, 환경별 자식 프로세스 조회 실패를 보완했다. 실제 알려진 구현 미완료는 아래 표와 백로그에 남긴다. 승인된 설계를 축소해 통과로 처리하지 않는다.

## 구현 대응

| 범위 | 코드·검증 |
| --- | --- |
| 잠금/CAS | src/sdd_core/concurrency.py, records.py, gates.py, cli.complete_work; tests/test_concurrency.py |
| 사본·FIFO·병합·반영·복구 | src/sdd_core/workspaces.py; tests/test_workspaces.py |
| 실행 환경·소유 프로세스 | checks.py, processes.py; 실제 spawn/종료·outsider 보존 |
| 네이티브 | skills/sdd-develop.md와 init/sync/mode, _conversation.md; 실제 공통 bundle 양쪽 설치 |
| 설치·버전 | setup.py, version_sync.py, specthread; 실제0.5.1→0.6.0 Claude·양쪽6.0 install/update |
| Monitor | observe/server/session/events/UI; 등록 사본·기존 Git·Claude receiver·기존 Office/Reader/CEO 회귀 |
| 문서 | 원본 parallel-development, 관련 주제의 변경 절·결정ST44~64·2.0 노트·HTML3종 |

## 실제 측정

macOS/Python3.11 로컬의 작은 검증 fixture, 각3회다. 앞 버전은 작업 시작 전 실제 src 복제다. 같은 실제 assertion을 실행하고 무관한 Work 레코드를 실행 중 추가했다. 모델·토큰·전체 SDD 시간 측정이 아니다.

| 지표 | 기존0.5.1 | 신규0.6.0 |
| --- | --- | --- |
| 독립 두 프로세스 ×3회 무관 변경 오차 차단 | 6회 | 0회 |
| 단일 Gate 중앙값 | 0.053557s | 0.048772s |
| 병렬 fixture 중앙값 | 0.233970s | 0.266248s |

Isolated 작은 fixture의 Snapshot 중앙값 0.029232s, 영향 검토 미리보기+검증+반영 중앙값 0.192340s. 복제 방법·파일 수·논리/할당량은 원자료에 남긴다. COW 고유 물리 크기나 일반 앱 속도 향상으로 해석하지 않는다. 원본 비교 CAS·해시·안전 복구 비용이 있으며 대형 프로젝트·실제 모델 생산성은 미측정이다.

## 실행 검증

최종 테스트 수와 문서·HTML 검사는 아래 최종 실행 절에 기록한다. 스크립트는 `scripts/benchmark-core-concurrency.py`; 기본 python3는3.7인 환경이므로 Python3.11 및 프로젝트 의존성이 필요했다. macOS 제한 실행에서는 psutil sysctl 조회가 거부되어 정상 통과로 처리하지 않았고, 허용된 호스트 검증에서는 실제 종료/정리 테스트가 통과했다. 영구 권한 설정을 변경하지 않았다.

공식 Spec Kit gitless 실행은 원형1.4.0 스크립트3개 실제 exit0을 확인했다. 같은 native Codex 세션에서는 절대경로 생성/편집·실제 cwd·원본 무변경·Core 원본 차단을 확인했지만 새 fixture의 자연 Hook는 받지 못했다. Core enter는 의도대로 차단됐다. Claude 설치/update와 receiver/경계 검사는 통과했으나 실행 파일이 없어 Claude 자체를 실행하지 않았다.

## 필수63개 인수 추적

통과는 명시한 수준에만 적용한다. 구현/부분/미확인은 미완료이며 독립 에이전트 실행 보장으로 확대하지 않는다.

| 번호 | 요구 | 현재 근거와 판정 |
| --- | --- | --- |
| 1 | 서로 다른 Work Item의 Gate를 동시에 실행해도 정상 결과가 무효화되지 않는다. | **통과 · 실제 프로세스** — tests/test_concurrency.py: 두 프로세스 Gate/독립 레코드 CAS/같은 Work 충돌 |
| 2 | 다른 Work Item의 상태 변경이 정상 Gate 결과 저장을 방해하지 않는다. | **통과 · 실제 프로세스** — tests/test_concurrency.py: 두 프로세스 Gate/독립 레코드 CAS/같은 Work 충돌 |
| 3 | 동시에 서로 다른 Work Item을 수정해도 변경 사항이 유실되지 않는다. | **통과 · 실제 프로세스** — tests/test_concurrency.py: 두 프로세스 Gate/독립 레코드 CAS/같은 Work 충돌 |
| 4 | 동일 Work Item에 대한 충돌은 안전하게 감지된다. | **통과 · 실제 프로세스** — tests/test_concurrency.py: 두 프로세스 Gate/독립 레코드 CAS/같은 Work 충돌 |
| 5 | 실제 Gate 입력 변경 시 기존 PASS가 적절하게 무효화된다. | **통과 · Core** — 기존 lifecycle/gates/evidence 및 verification_profiles 회귀 |
| 6 | 완료 조건 확인과 상태 저장 사이의 경쟁 조건이 방지된다. | **통과 · 실제 프로세스 경쟁** — 완료 Gate 검사 중 별도 쓰기가 잠금에서 대기하고 완료 저장 후 같은 레코드의 stale 쓰기를 거부. completed와 원래 이력 보존 |
| 7 | Direct Mode의 기존 개발 흐름이 유지된다. | **통과 · Core** — 기존 Direct 회귀·실제 구/신 Core 비교 |
| 8 | 두 Work Item이 서로 다른 Workspace에서 독립적으로 개발된다. | **통과 · Core fixture** — test_workspaces: 별도 실제 사본·두 Work 순차 통합·기록 보존. 네이티브 모델 병렬 실행과 별개 |
| 9 | 동일 파일을 수정해도 상대 Workspace와 원본에 즉시 영향을 주지 않는다. | **통과 · Core fixture** — test_workspaces: 별도 실제 사본·두 Work 순차 통합·기록 보존. 네이티브 모델 병렬 실행과 별개 |
| 10 | Workspace에서 생성한 SDD 산출물이 원본에 조기 반영되지 않는다. | **통과 · Core fixture** — test_workspaces: 별도 실제 사본·두 Work 순차 통합·기록 보존. 네이티브 모델 병렬 실행과 별개 |
| 11 | Reflink 미지원 환경에서 일반 복제가 정상 동작한다. | **통과 · Core** — 일반 복제 fallback 실제 바이트/독립 inode, symlink·경로 차단 |
| 12 | Symlink 및 경로 탈출로 원본을 수정하지 않는다. | **통과 · Core** — 일반 복제 fallback 실제 바이트/독립 inode, symlink·경로 차단 |
| 13 | 원본 반영 중 신규 Snapshot 생성이 차단된다. | **통과 · 실제 프로세스 경합** — 실제 별도 프로세스의 publish 소유 중 Snapshot 대기, integration 소유 중 새 Workspace 생성 성공 |
| 14 | 장시간 통합 검증 중에도 신규 Workspace 생성이 가능하다. | **통과 · 실제 프로세스 경합** — 실제 별도 프로세스의 publish 소유 중 Snapshot 대기, integration 소유 중 새 Workspace 생성 성공 |
| 15 | 여러 Work Item이 FIFO 순서로 통합된다. | **통과 · Core** — 준비 등록 FIFO 및 두 Work 순차 반영. 실제 동시 Agent 전체 흐름 미확인 |
| 16 | 서로 다른 파일 변경이 정상 통합된다. | **통과 · Core fixture** — test_workspaces: 별도 실제 사본·두 Work 순차 통합·기록 보존. 네이티브 모델 병렬 실행과 별개 |
| 17 | 동일 파일의 비충돌 변경이 정상 병합된다. | **통과 · Core** — 실제 3방향 비중첩 텍스트/겹침/Binary 차단·해결 입력 해시 재확인 |
| 18 | 동일 영역의 의미적 충돌이 감지된다. | **계약 구현 · 의미 검증 미확인** — Skill에 두 의도/직접·간접 소비자 검토, Core nonempty findings. 모델 판단 정확성은 미검증 |
| 19 | Baseline 레코드의 독립 변경이 모두 보존된다. | **통과 · Core fixture** — test_workspaces: 별도 실제 사본·두 Work 순차 통합·기록 보존. 네이티브 모델 병렬 실행과 별개 |
| 20 | 파일 생성·수정·삭제가 정상 통합된다. | **통과 · Core** — 파일 생성/수정·모드·디렉터리 및 반영/복구, 기존 archive 삭제 회귀. 복합 디렉터리 삭제 추가 인수 권장 |
| 21 | Binary 및 모호한 충돌이 임의로 덮어써지지 않는다. | **통과 · Core** — 실제 3방향 비중첩 텍스트/겹침/Binary 차단·해결 입력 해시 재확인 |
| 22 | 텍스트 충돌이 없는 기능적 의존성 변경이 감지된다. | **계약 구현 · 의미 검증 미확인** — Skill에 두 의도/직접·간접 소비자 검토, Core nonempty findings. 모델 판단 정확성은 미검증 |
| 23 | 유효한 Gate 결과는 재사용된다. | **통과 · Core** — 기존 selective revalidation/profiles + 같은 Work 후보 이력 보존. 실제 대형 프로젝트 영향 판단 미확인 |
| 24 | 영향을 받은 Gate만 재실행된다. | **통과 · Core** — 기존 selective revalidation/profiles + 같은 Work 후보 이력 보존. 실제 대형 프로젝트 영향 판단 미확인 |
| 25 | 동일 실패 원인 반복 시 자동 해결이 종료된다. | **Core 한도 회귀 통과 · 네이티브 미확인** — 충돌 한도 도달·자동 재시도 차단·현재 사용자 resume 해시 후 통합. 실제 모델 해결 반복은 미실행 |
| 26 | 사용자 승인 대기 중 다른 Work Item이 통합될 수 있다. | **통과 · Core fixture** — blocked dequeue/Lock 해제, preview 현재 원본 재검토, 후보 추가 수정 history 보존 |
| 27 | 재개 시 최신 원본을 기준으로 재검토한다. | **통과 · Core fixture** — blocked dequeue/Lock 해제, preview 현재 원본 재검토, 후보 추가 수정 history 보존 |
| 28 | 통합 대기 중 Agent 종료 | **실제 worker 종료 통과 · Agent 전체 미확인** — kernel worker 소유 중 대기열 유지, 실제 소유 프로세스 종료 후 안전 제거. 네이티브 Agent 종료는 별개 |
| 29 | Integration Lock 획득 직후 종료 | **구현 · 종료 지점 추가 인수 필요** — 커널 worker/integration 소유권·종료 worker 정리. 해당 각 지점 강제 종료는 미실행 |
| 30 | 충돌 해결 중 종료 | **구현 · 종료 지점 추가 인수 필요** — 커널 worker/integration 소유권·종료 worker 정리. 해당 각 지점 강제 종료는 미실행 |
| 31 | Gate 검증 중 종료 | **통과 · 실제 종료** — Gate 소유 프로세스 종료 후 알려진 자기 자식만 정리, outsider 유지 |
| 32 | 원본 반영 직전 종료 | **구현 · 종료 지점 추가 인수 필요** — 커널 worker/integration 소유권·종료 worker 정리. 해당 각 지점 강제 종료는 미실행 |
| 33 | 원본 일부 반영 후 강제 종료 | **통과 · 실제 종료/쓰기** — 반영 첫/중간/마지막 경계 os._exit(73) 후 recovery; 외부 변경 감지·중단 |
| 34 | Work Item 완료 상태 기록 전후 종료 | **통과 · 실제 종료/쓰기** — 반영 첫/중간/마지막 경계 os._exit(73) 후 recovery; 외부 변경 감지·중단 |
| 35 | 복구 중 외부 파일 변경 발생 | **통과 · 실제 종료/쓰기** — 반영 첫/중간/마지막 경계 os._exit(73) 후 recovery; 외부 변경 감지·중단 |
| 36 | 살아 있는 프로세스의 Lock을 잘못 해제하지 않음 | **통과 · 실제 프로세스** — 살아 있는 kernel lock 획득 거부, 종료 후 획득 |
| 37 | 실패 Workspace 및 Evidence 보존 | **통과 · Core** — 실패 사본 유지, retained actual evidence, 성공 runtime 정리·명시적 폐기 이력 |
| 38 | 성공 Workspace 안전 정리 | **통과 · Core** — 실패 사본 유지, retained actual evidence, 성공 runtime 정리·명시적 폐기 이력 |
| 39 | 병렬 테스트 서버 포트 충돌 방지 | **구현 · 실제 병렬 서버 미확인** — dynamic/serial 실행 계획 요구. 실제 두 서버/포트 인수 미실행 |
| 40 | Work Item별 임시 파일 및 테스트 결과 분리 | **통과 · 실제 실행** — Work TMP/결과/lease 분리, 자기 child 종료·외부 프로세스 보존 |
| 41 | 다른 Work Item의 실행 프로세스를 종료하지 않음 | **통과 · 실제 실행** — Work TMP/결과/lease 분리, 자기 child 종료·외부 프로세스 보존 |
| 42 | 외부 DB 및 Redis 격리 설정 활용 | **차단 통과 · 외부 연동 미확인** — 미확인 외부 리소스 실행 차단·serial lock 구현. 실제 DB/Redis 격리 미실행 |
| 43 | 외부 리소스 격리 미확인 상황의 안전한 처리 | **차단 통과 · 외부 연동 미확인** — 미확인 외부 리소스 실행 차단·serial lock 구현. 실제 DB/Redis 격리 미실행 |
| 44 | Codex 기존 Session에서 Workspace 개발 | **부분 실제 PoC** — 동일 Codex 세션5 checks 확인. 새 fixture 자연 Hook 미확인으로 실제 entry 차단 |
| 45 | Claude Code 기존 Session에서 Workspace 개발 | **미확인 · Claude 실행 환경 없음** — 공통 Core·Claude 설치/Hook receiver·같은 세션 경계 fixture 통과. 실제 Claude CLI 실행 아님 |
| 46 | Git 없는 Workspace에서 공식 Spec Kit 실행 | **통과 · 실제 공식 스크립트** — Spec Kit1.4 create-new-feature/setup-plan/check-prerequisites, .git 없음. 전체 Agent 호출 아님 |
| 47 | Agent의 원본 직접 수정 방지 | **협력 guard 통과 · 네이티브 범위 부분** — Core 원본 변경 차단, 실제 Codex 절대 사본 수정. 임의 native tool의 OS 강제 격리 보장 아님 |
| 48 | 원본 앱 폴더에서 기존 Monitor 실행 | **통과 · Monitor fixture/회귀** — 등록 Scope snapshot/artifact/원본 Git 분리, 임의 외부 root 거부, HTTP 권한 기존 유지 |
| 49 | 복수 Workspace의 기존 Session 연결 | **receiver 통과 · 자연 복수 세션 미확인** — Claude 형식 Hook의 실제 receiver 호출은 원본/sameSession/workspace 한번 연결. 합성 입력임 |
| 50 | Workspace 산출물 및 Gate 상태 조회 | **통과 · Monitor fixture/회귀** — 등록 Scope snapshot/artifact/원본 Git 분리, 임의 외부 root 거부, HTTP 권한 기존 유지 |
| 51 | 기존 Git Diff 기능 유지 | **통과 · Monitor fixture/회귀** — 등록 Scope snapshot/artifact/원본 Git 분리, 임의 외부 root 거부, HTTP 권한 기존 유지 |
| 52 | 기존 Living Office 기능 유지 | **기존 회귀 통과** — Living UI·Reader·CEO 기존 테스트 유지. 실제 native delegation 전체 PoC는 별도 |
| 53 | Reader 및 CEO 기존 승인 기능 유지 | **기존 회귀 통과** — Living UI·Reader·CEO 기존 테스트 유지. 실제 native delegation 전체 PoC는 별도 |
| 54 | Monitor 미실행 상태에서도 정상 개발 및 통합 | **통과 · Core** — Monitor 없이 두 Work 개발 준비/통합·복구 테스트 |
| 55 | 등록되지 않은 외부 Workspace 접근 차단 | **통과 · Monitor fixture/회귀** — 등록 Scope snapshot/artifact/원본 Git 분리, 임의 외부 root 거부, HTTP 권한 기존 유지 |
| 56 | 기존 프로젝트 업데이트 시 Direct Mode 적용 | **통과 · 실제 배포 업그레이드** — 보존 실제0.5.1 Claude 설치→0.6.0, 앱·Baseline 바이트 보존·Direct 기본 |
| 57 | 신규 프로젝트 설치 시 모드 선택 | **통과 · 설치/회귀** — 양쪽 공식 설치/update, mode 선택/default/preserve 회귀. 사용자 실제 대화 선택은 별도 |
| 58 | 비대화형 설치 기본값 적용 | **통과 · 설치/회귀** — 양쪽 공식 설치/update, mode 선택/default/preserve 회귀. 사용자 실제 대화 선택은 별도 |
| 59 | 기존 모드 설정 보존 | **통과 · 설치/회귀** — 양쪽 공식 설치/update, mode 선택/default/preserve 회귀. 사용자 실제 대화 선택은 별도 |
| 60 | 활성 작업 중 모드 전환 차단 | **통과 · Core** — 활성 Work mode 차단·Workspace/저널 update blocker·내부 update 금지 |
| 61 | 활성 Workspace 및 미완료 트랜잭션 중 업데이트 차단 | **통과 · Core** — 활성 Work mode 차단·Workspace/저널 update blocker·내부 update 금지 |
| 62 | 기존 Baseline 및 산출물 보존 | **통과 · 실제 배포 업그레이드** — 보존 실제0.5.1 Claude 설치→0.6.0, 앱·Baseline 바이트 보존·Direct 기본 |
| 63 | 기존 Monitor 설정 보존 | **기존 회귀 · 실제 사용자 설치 추가 인수** — Monitor 설정은 버전 변환에서 변경하지 않음, 기존 Hook/update 테스트 유지 |

## 남은 검증과 제한

- 동일 세션 전체 개발/통합은 Codex 자연 Hook 확인과 Claude 실제 실행이 필요하다. 해당 미확인 환경은 fail closed를 유지한다.
- 커널 잠금/psutil/Hook Windows 경로, DB/Redis/포트, 대형 저장소 성능은 이번 Mac 검증으로 완료하지 않는다.
- 의미 충돌·간접 영향·동의의 실제 판단은 Skill 책임이다. Core가 nonempty findings·해시를 검사해도 판단의 진실성을 증명하지 못한다.
- 파일 사본은 OS Sandbox가 아니다. 추적 밖 daemon/double-fork는 기존 프로젝트 정리·소유권 확인이 필요하다. 확인하지 못한 프로세스를 임의 종료하지 않는다.
- 명시적 외부 Sync는 활성 작업 종료 후 기존 source reconciliation Work로 수행한다. 자동 Git/새 Agent/중앙 제어를 추가하지 않았다.
- Commit·Push·태그·Release 게시는 이번 작업에서 실행하지 않았다.

## 최종 실행 결과

- Core: `python3.11 -m unittest discover -s tests` **134개 통과**. 최종 설치 모드 사전 검증·취소와 완료 검사/저장 경쟁 재현을 포함한다.
- Monitor: **29개 중28 통과, Windows 전용1 생략**. 선택 Scope 세션/이벤트 분리와 원본 복귀 이력 회귀 포함.
- Markdown: **30개 구조·링크·설계2.0/CHANGELOG 일치** 검사 통과. 기존 문서 실행 예시 **13개 계약 통과**.
- HTML: 가이드 생성물 일치, 세 HTML 실제 Chrome 로드·오류0·1440px 가로 넘침0. 기능 목록119행, 독립 검색17행 확인. 소개 추가 영역 화면 직접 확인.
- 공식 Spec Kit1.4.0: Codex/Claude install/update 실제 성공. 보존 실제0.5.1 Claude→0.6.0에서 앱·7 Baseline 바이트·Direct 기본 보존.
- 네 Skill의 frontmatter/구조 검증 통과. JavaScript 두 UI 파일 문법 및 Git diff 공백 검사 통과. Git Commit/Push/태그는 미실행.

전체 인수 완료 판정은 보류한다. 63개 표의 미확인·추가 인수와 실제 네이티브 진입 제한이 남아 있다. 사용자 시스템의 기존 설치·권한·대화를 변경해 검증을 가장하지 않았다.
