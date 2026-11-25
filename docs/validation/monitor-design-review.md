# SpecThread Monitor 설계 대조 및 구현 검증

2026-11-23 · 제품 체크아웃 `main` `364752e` · 설계 1.0 · Core 0.4.0. 사용자 실행형 범위는 2026-11-23 승인됐다. 확정 설계와 구현 근거는 [설계 목차](../design/README.md)와 [제품 구현 절차](../design/implementation-standard.md)를 따른다.

이전 대화 조회본은 3절 Collector 구조 중간에서 잘렸고 첨부 목록은 비어 있었다. 아래 체크리스트는 조회 가능한 내용과 현재 요청에 열거된 전체 기능명을 반영한다. 사용자가 별도로 제공한 시각 레퍼런스를 확인했다. 3절 이후 원문의 추가 세부 조건은 미확인이다.

## 충돌 및 해석

| 요청 또는 가정 | 최신 설계와 구현 | 구현 제안 |
| --- | --- | --- |
| 실시간 수집, 세션 상태 표시 | [Git·세션 운영](../design/08-git-integration.md), [ST-13](../design/DECISIONS.md), [Gate](../design/06-verification.md)는 상시 외부 변경 감시, 생존 감시, 실시간 동기화와 자동 복구를 제외한다. | 사용자가 실행한 Monitor에서만 로컬 스냅샷을 새로 읽고 명시적으로 전달된 에이전트 이벤트만 표시한다. 백그라운드 감시, 세션 상태 판정·조정, 자동 정합화는 제외한다. 이 적용 범위는 사용자 승인을 받아 ST-26으로 기록했다. |
| 세션별 Git 변경 귀속과 양쪽 에이전트 통합 | [런타임](../design/07-agent-runtime.md)은 프로젝트별 에이전트 선택을 전제한다. 동일 프로젝트에서 혼용은 [ST-O10](../design/OPEN-ISSUES.md) 보류다. Git diff 자체에는 세션 식별자가 없다. | 두 환경에 동일한 관측 계약을 제공한다. 출처가 명시된 파일 이벤트만 세션에 귀속하고 현재 diff는 사용자가 지정한 Worktree 범위로 표시한다. |
| Feature·Work Item·Pipeline 진행 통합 | [산출물 모델](../design/01-artifact-model.md)과 [Work Item 생명주기](../design/04-artifact-lifecycle.md)는 UUID v7, Feature active/retired, 별개의 Work Item 저장 상태를 규정한다. failed는 종료되어 재시도 시 새 UUID를 사용한다. suspended는 의도적 보류다. 수정 가능한 실패는 in_progress를 유지한다. | Baseline의 UUID와 상태를 그대로 표시한다. 분석 상태, 공식 태스크 체크, 에이전트 이벤트, Git 반영을 각각 원본에 연결한다. |
| Gate와 승인 대기, 다음 행동 자동 판정 | [검증](../design/06-verification.md)과 [버전 동기화](../design/version-sync.md)는 유효한 필수 Gate PASS, 버전·데이터 필수 검사와 품질 검사 차단 범위, 승인 단계를 별도로 정의한다. Core에는 모든 사용자 승인 대기를 열거하는 API가 없다. | Core의 읽기 가능한 검증 로직을 재사용하고 저장된 이력과 현재 증거 유효성을 표시한다. 승인 대기는 명시적 출처가 있을 때 표시한다. 다음 행동은 근거 링크가 있는 안내로 제공한다. |
| 선택 설치와 예전 프로젝트 지원 | [설치](../design/installation.md)는 install/update와 Core·Project·선택 Skill 버전 일치를 규정한다. Baseline 스키마는 Core 버전과 독립적이다. | Monitor를 독립 실행 모듈로 제공한다. Core와 Skill이 Monitor를 호출하는 역방향 의존성을 만들지 않는다. 미지원·미초기화 데이터는 파일·Git 관측으로 내려가며 마이그레이션은 기존 사용자 승인 흐름이 담당한다. |
| 제품 저장소에서 SDD 산출물 작성 | [AGENTS](../../AGENTS.md)는 공식 Spec Kit 산출물과 Baseline의 소유를 대상 프로젝트 Git에 둔다. 제품 구현은 주제별 설계 원본과 검증 대응표를 사용한다. | 승인 뒤 Monitor 요구사항·상세 설계를 제품의 주제별 원본에 기록하고 DECISIONS·OPEN-ISSUES·목차·관련 HTML에 연결한다. 데모 대상의 Baseline은 관측 검증에 읽기만 한다. |

## 요구사항 체크리스트

| 범위 | 인수 기준 |
| --- | --- |
| Project Overview | 대상 Git·Worktree, Baseline 지원 여부와 입력 출처·시점 표시 |
| Session Monitor | 명시적으로 전달한 이벤트의 출처·세션 ID·최근 활동, 근거 있는 파일 이벤트와 Worktree diff 조회 |
| Feature / Work Item Explorer | UUID, lifecycle, 선언·실제 범위, 의존성, 과거 작업 참조 |
| Artifact Explorer | Spec Kit 및 Baseline 원본 연결, 파일 존재와 관측된 변경, 검증 증거 연결 |
| SDD Pipeline / Gate Monitor | 분석·태스크·저장 상태, 적용 단계별 필수 Gate, 결과·증거 유효성, 기록된 버전 및 품질 차단 범위 |
| Next Actions | 미완료 태스크·차단 근거·확인 가능한 승인 대기의 읽기 전용 안내 |
| Focus / Living Mode | 동일한 실제 관측 데이터, 텍스트 상태, 관측 이벤트에만 반응하는 픽셀 애니메이션, 축소 모션 설정 |
| 수집 및 성능 | 사용자 실행 중에만 갱신, 읽기 크기·이력 개수·명령 시간 한도, 이벤트 부재 및 일시적 입력 오류 시 파일·Git 기반 대체 |
| 보안·보존·접근성 | 로컬 접근, 프로젝트 상대 경로 검증, 변경 요청을 처리하지 않는 API, 민감한 이벤트 필드 제거, 제한된 메모리 보존, 키보드·상태 텍스트 |
| 검증 및 문서 | 기존 회귀와 신규 정상·차단·실패 테스트, UI 빌드·브라우저 확인, 문서 검사, 실제 데모 읽기 전후 대조, 양쪽 에이전트 연동 결과 및 DECISIONS·OPEN-ISSUES 반영 |

[Codex 공식 JSONL 예제](https://developers.openai.com/blog/eval-skills)와 [Claude Code Hooks 레퍼런스](https://code.claude.com/docs/en/hooks)는 사용자가 선택해서 연결할 수 있는 후보 입력이다. 실제 실행 환경에서의 이벤트 전달과 파일 귀속은 아직 검증하지 않았다. 최초 승인 범위는 별도 실행형 관측이었다. 후속 ST-27부터 사용자가 명시적으로 선택하면 새 터미널 세션을 함께 열 수 있다. 비공개 세션 파일 탐색과 별도 LLM 호출은 제외한다.

## 시각 레퍼런스

[사용자 제공 픽셀아트 샘플](https://chatgpt.com/s/m_6b0434b865488191bb50381f76c83820)을 확인했다. Living Mode에는 야간 픽셀 사무실과 실제 활동에 반응하는 캐릭터를 배치하고, 샘플의 좌측 탐색·상단 요약·우측 Pipeline 및 Next Actions 구조를 활용한다. Focus Mode는 사무실을 숨기고 작업·Gate·다음 행동을 앞에 배치한다. 샘플의 카드 수치와 세션 이름은 예시이며 화면은 관측값과 출처를 표시한다.

## 구현 및 실행 결과

| 요구사항 | 구현 지점 | 실행 증거와 상태 |
| --- | --- | --- |
| 개요·Pipeline·Feature·Work Item | [스냅샷](../../monitor/specthread_monitor/observe.py), [화면](../../monitor/specthread_monitor/ui/app.js) | 최신 스키마 fixture에서 UUID, 태스크 1/2, 설치 파일 대조 확인. 기존 공식 설치 검증 자료의 양쪽 에이전트 스키마도 읽었다. 구형 실제 데모는 분석·작업의 미확인을 표시했다. |
| Artifact·Gate·Next Actions | 스냅샷, 화면, [Monitor 테스트](../../monitor/tests/test_monitor.py) | Core가 작성한 실제 명령 Gate의 PASS와 입력 변경 후 STALE, 대응 Next Action을 확인했다. 실제 데모에서 산출물 17개와 구형 스키마 안내를 확인했다. 승인 요청 이벤트는 수신 사실과 미확인 상태를 표시한다. |
| 세션·파일 관측 | [이벤트 입력](../../monitor/specthread_monitor/events.py) | 양쪽 공식 입력 형식 fixture를 처리했다. 브라우저에서 두 표본 세션, 테스트에서 출처·범위·민감 본문 제외·큰 스트림 한도를 확인했다. 실제 대화형 Hook 종단간 확인은 ST-O17로 남긴다. |
| Git Diff·읽기 전용·격리 | [Git 관측](../../monitor/specthread_monitor/observe.py), [로컬 서버](../../monitor/specthread_monitor/server.py) | Git 경로 리터럴 처리, staged/unstaged diff, 외부 필터 미실행, 경로·인증·Host 검사를 확인했다. 실제 데모에서 변경 59개를 읽었으며 Git 메타데이터와 가상환경을 제외한 일반 파일 64개 해시가 일치했다. 별도 fixture에서는 Git 메타데이터를 포함해 모든 일반 파일 해시를 대조했다. |
| Living·Focus·UI 패키지 | [UI](../../monitor/specthread_monitor/ui/index.html), [패키지](../../monitor/pyproject.toml) | wheel 빌드 및 별도 환경 설치 후 CLI 도움말과 UI 자산 서빙을 확인했다. 실제 브라우저에서 키보드로 Focus·Living을 전환하고 사무실 표시, 두 표본 세션과 구형 프로젝트 대체 화면을 확인했다. |
| 회귀·문서 | [제품 CI](../../.github/workflows/product-ci.yml), [설계 원본](../design/monitor.md) | 기존 Python 테스트 73개, 설치본 Monitor 테스트 7개, JS 구문 검사, Core 문서 실행 예시, 설계 문서 28개와 생성 HTML 동기화 및 릴리즈 노트 추출을 통과했다. |

Monitor 화면에 표시하는 Git diff는 현재 Worktree의 스테이징·작업 트리 변경이다. 세션별 과거 diff 복원, 자동 세션 유추, 승인 대기 상태의 포괄적 판정은 제공 범위에 없다. 지원 인터페이스의 실제 전송 밀도, 사용자 Hook 구성 및 대화형 파일 귀속은 후속 PoC에서 확인한다.


## 2026-11-24 추가 개선 대조

| 개선 항목 | 구현과 확인 범위 |
| --- | --- |
| 초기 설치와 SSL 재시도 | [통합 설치](../design/installation.md)의 앱 경로·에이전트·Monitor 선택 및 `--ssl-trust`를 구현했다. pip 인증서 오류 뒤 기본 PyPI 호스트에 한정해 재시도하는 경로는 설치 테스트에서 확인했다. |
| Monitor만 추가 및 실행 | macOS의 임시 Claude Code용 프로젝트에 Core만 설치한 뒤 Monitor를 추가했다. Core 실행 파일·버전 기록의 해시가 유지됐다. 설치한 데모 실행 명령도 확인했다. Windows용 실행 파일과 설치 검사는 CI에 추가했으며 네이티브 Windows 실행 결과는 아직 미확인이다. |
| 이미 열린 Monitor의 새 세션 관측 | [실행 가이드](../../monitor/README.md)의 대시보드 우선 실행을 적용했다. 이미 응답 중인 대시보드에 별도 프로세스로 Claude Hook 두 건을 전달했고 동일 API에 두 세션이 표시됐다. 로그인된 실제 에이전트의 Hook 전달·신뢰·설정 반영은 ST-O17에서 추적한다. |
| 세션별 Gate 모션 | [Monitor 명세](../design/monitor.md)의 Work Item UUID 연결을 적용했다. 표본 세션 두 개 중 관련 세션에만 Gate 목록과 캐릭터 느낌표를 표시하는 것을 브라우저에서 확인했다. 현재 대상 단계 밖 미실행 Gate와 연결 근거 없는 세션은 자동 표시 대상에서 제외한다. |
| SDD 실행 확인 | [에이전트 런타임](../design/07-agent-runtime.md)의 읽기 전용 preflight 및 공통 Skill 지침을 적용했다. 프로젝트 파일 불변, 일치하지 않는 에이전트와 개발이 차단된 Feature 거부를 테스트했다. 실제 에이전트의 권한 팝업 감소 횟수는 미확인이다. |


## 2026-11-25 설치 인코딩·Windows Hook·사용자 확인 표시

| 보고 항목 | 원인과 수정 | 검증·한계 |
| --- | --- | --- |
| 간헐적 CP949 오류 | 설치기가 JSON을 기본 인코딩으로 읽고 Spec Kit 출력을 `text=True`의 로캘 인코딩으로 해석했다. pip·Core·Spec Kit 자식 환경과 파이프는 UTF-8로 통일하고 격리 Python에는 `-X utf8`을 명시한다. 터미널에 표현 불가능한 문자는 대체 표기한다. | CP949 강제 자식에서 한글·이모지 출력 실패를 재현하고 수정 경로에서 같은 출력과 JSON 파싱 성공을 확인했다. 사용자 원본 traceback이 없어 보고된 모든 실패가 같은 지점에서 발생했는지는 단정하지 않는다. |
| Windows Stop Hook 경로·인자 오류 | Claude용 exec-form `args`는 최신 공식 문서에서는 지원되지만 구버전 호환을 보장하지 못한다. 구버전에서 command만 셸로 실행되면 경로·인자가 잘못 해석될 수 있다. Claude에는 command 단일 문자열, Codex에는 commandWindows를 사용하고, 실제 경로·인자는 PowerShell EncodedCommand 내부에서 인용한다. stdin 전달도 UTF-8로 맞춘다. Windows 실행기는 UTF-8로 읽고 실행 후 원래 코드 페이지와 반환 코드를 보존한다. | 한글·공백·백슬래시·작은따옴표 경로, 설정 반복 적용, 사용자 Hook 보존을 검사했다. Windows의 Git Bash·cmd에서 생성 Hook을 실제 실행하는 테스트를 추가했다. 이 테스트는 macOS에서 건너뛰며 Windows CI 결과는 아직 미확인이다. 실제 에이전트 버전·로그도 미제공이므로 비차단 오류의 나머지 원인은 미확인이다. |
| Gate에서 느낌표 누락 | 기존 조건은 특정 Core 명령에서 관측한 Work Item UUID와 필수 Gate 결과에 한정됐다. 권한·질문·계획 승인·지원 알림과 턴 종료·실패·중단도 사용자 확인 신호로 표시한다. 다음 활동에서 해제하며 확인 신호는 단순 활동 시간 만료로 지우지 않는다. | 다른 세션 오표시 방지, 후속 입력 해제, 오래된 확인 신호 유지, 민감 질문·알림 본문 미저장을 검사했다. Chrome에서 사용자 확인 카드·패널·캐릭터 느낌표와 해제를 확인했다. 턴 종료는 실제 승인 대기 확정이 아니라 결과 확인 안내다. 미전달 이벤트와 비공개 대화 내용은 추정하지 않는다. |
| 수정본 적용 | 기존 관리 Monitor가 있으면 내려받은 배포본의 update에서 패키지·실행기·관리 Hook을 함께 갱신한다. 사용자 Hook과 파일은 보존한다. | 설치 회귀 테스트에서 기존 Monitor 갱신 호출을 확인했다. 설정 변경 후 에이전트 재시작과 Codex Hook 재신뢰는 사용자가 수행한다. |

관련 공식 계약: [Claude command/args 및 셸](https://code.claude.com/docs/en/hooks), [Codex commandWindows와 Hook 이벤트](https://learn.chatgpt.com/docs/hooks). 이 수정은 설계 1.0과 기존 Core·Monitor 배포 버전을 유지한다. Windows 네이티브 및 실제 에이전트 종단간 확인은 기존 ST-O17 범위로 남긴다.

검증 결과: Core·설치 전체 79개 통과, 이후 설치 관련 최종 회귀 21개 통과. Monitor 20개 중 19개 통과·Windows 전용 1개 제외. 설계 문서 28개 구조·링크 검사, 실행 예시 13개 계약 검증, 생성 HTML 동기화, JavaScript 구문, Git diff 공백 검사를 통과했다. Chrome에서 확인 대기 유지·다른 세션 비표시·다음 프롬프트 후 해제와 JavaScript 오류 없음을 확인했다.


## 2026-11-25 프로젝트 진척률·세션 작업 연결 개선

| 사용자 요구 | 구현·검증 근거 | 판정 |
| --- | --- | --- |
| 어디서 어떤 작업을 하는 세션인지 식별 | events/session은 지원 도구 시작·종류·작업 폴더·프로젝트 내부 테스트 파일·Core 명령의 UUID/Gate 식별자만 보존하고 server는 기존 Work Item과 Feature를 연결한다. 권한·턴 종료 이후에도 최근 연결을 유지하는 테스트, 실제 작업 디렉터리 기준 테스트 파일명·비밀 인자 제외·프로젝트 밖 경로 제외를 확인했다. | 구현·자동 테스트 통과. 신호 없는 업무 내용은 미확인으로 유지 |
| 캐릭터·작업·검증·다음 행동 같은 색과 활동 말풍선 | UI는 번호 대신 작업 주제명·색상과 최대 다섯 말풍선을 연결한다. Feature 이름 또는 확인한 작업 내용이 기본 제목이며 사용자가 표시 이름을 직접 지정할 수 있다. 원래 세션 ID는 상세에만 둔다. 사람·로봇·동물·식물·외계인 여덟 외형을 그린다. Chrome에서 다섯 말풍선과 세션 카드 색 일치·서로 다른 팔레트, Feature/폴더/검증명 표시를 확인했다. | 데스크톱·모바일 브라우저 확인 |
| 권한 이벤트 노이즈 축소 | 세션 목록은 permission_requested를 기본으로 숨기고 체크박스로 다시 표시한다. 느낌표와 수신 상태는 필터와 독립적이다. | Chrome에서 기본 숨김·체크 후 표시 확인 |
| 세션 종료 이후 전체 프로젝트 진척률 | 전체 Baseline에서 작업 상태·Gate 합계를 계산하고 활성 Feature 태스크를 읽는다. 종료 Gate PASS는 현재 PASS와 구분해 보존한다. 105개 Feature/작업 fixture에서 상세 100개와 전체 105개 집계의 분리 및 완료 Gate 분모 유지를 확인했다. | 자동 테스트 통과. 미확인 태스크·증거는 표시하며 통과로 추정하지 않음 |
| 에이전트 종료 후 Monitor 유지 | --session은 에이전트 종료 뒤에도 사용자 Ctrl+C까지 HTTP 서버를 유지한다. 테스트는 자식 종료 뒤 API가 응답하며 사용자 종료 경계 후 서버·임시 파일이 정리되는지 검사한다. | 자동 테스트 통과. 별도 상주 서비스·세션 제어 없음 |

Core·설치 회귀 79개 통과, Monitor 24개 중 23개 통과·Windows 전용 1개 제외. Chrome에서 프로젝트 진척률이 세션 종료 전후 동일함, 다중 세션 표시·색상·권한 필터·모바일 가로 넘침 없음·JavaScript 오류 없음을 확인했다. 설계 문서 28개 구조·링크, 생성 HTML 동기화, JavaScript 구문과 diff 공백 검사도 통과했다. 현재 설계 1.0·Core 0.4.0을 유지하며 실제 Windows 및 로그인한 에이전트의 이벤트 전달 검증은 기존 ST-O17에 남는다. 화면 검증은 명시한 표본 이벤트를 사용했으며 실제 대화 내용을 읽어 업무를 추론한 결과가 아니다.

후속 주제명 검증: Chrome에서 “로그인 API 검증”으로 주제명을 지정한 뒤 캐릭터 말풍선·세션 카드에 같은 이름이 표시되고 브라우저 새로고침 후에도 유지됨을 확인했다. 연결된 검증·다음 행동도 같은 주제명으로 표시한다.


## 2026-11-25 상세 메뉴 탐색 UI

| 범위 | 구현과 검증 |
| --- | --- |
| 세션·Feature·Work Item | [상세 화면 모듈](../../monitor/specthread_monitor/ui/details.js)에서 검색·상태 필터·선택/상세 패널을 제공한다. 세션 주제와 타임라인, Feature 태스크·의존 관계, Work Item Gate 목적·방식·결과·증거로 정보를 나눈다. 원본 ID는 접힌 상세에 둔다. Chrome에서 주제 검색·선택 및 자동 스냅샷 이후 검색 유지, 권한 이벤트 기본 숨김·다시 표시를 확인했다. |
| 근거 연결 | Feature의 tasks.md에서 산출물 원문으로 이동하고 연결 Work Item·세션·이전 작업을 탐색한다. 목록 범위 밖의 이전 Work Item을 눌렀을 때 다른 작업으로 대체하지 않고 미확인 안내를 표시함을 확인했다. |
| 산출물 | 문서 종류·변경 필터, 발견/변경 요약, 원문·경로·Gate 상태 및 다시 읽기를 제공한다. 현재 목록에서 사라진 파일은 이전 미리보기를 비우고 늦은 응답을 무효화한다. 파일 미리보기 경로·읽기 크기 제한은 기존 API를 유지한다. |
| Git | 선택 파일의 diff만 읽고 작업 트리/스테이징 탭·추가/삭제/구간 색상·조회 시각을 제공한다. 두 위치 모두 변경된 파일은 스테이징 필터에도 포함한다. Chrome에서 스테이징 전환, 자동 갱신 중 불필요한 diff 재조회 없음, 이전 diff 응답을 지연시킨 뒤 새 파일 선택 결과에 섞이지 않음을 확인했다. 새 파일·충돌은 별도 안내한다. |
| Pipeline | 분석·명세/태스크·작업·검증·설치 단계 선택과 해당 기록·화면 이동을 제공한다. 현재 PASS/종료 이력 PASS/미확인을 분리하고 다음 검토 항목은 펼칠 수 있게 구성했다. 실행 상태나 승인을 새로 판정하지 않는다. |
| 표시·패키지·회귀 | 여섯 메뉴의 1440px/390px Chrome 탐색·필터·교차 이동·빈 상태·가로 넘침 없음·JavaScript 오류 없음을 확인했다. 상세 모듈은 기존 서버의 정적 자산 허용 목록에 등록했고 HTTP 제공 테스트를 통과했다. Monitor 테스트 24개 중 23개 통과·Windows 전용 1개 제외, 두 UI 모듈 구문·문서 28개 구조/링크·생성 HTML 동기화·diff 공백 검사를 통과했다. CI에도 새 모듈 구문 검사를 추가했다. |

화면 검증은 기존 API 형태의 명시적 표본 데이터와 파일/diff 응답을 사용했다. 실제 Windows와 로그인된 에이전트의 Hook 전달은 이 UI 검증의 완료 범위에 포함하지 않는다. Core·Skill 실행 및 대상 프로젝트 파일·Git을 수정하는 기능은 추가하지 않았다.


## 2026-11-25 실제 로컬 Codex 기록 조회 확인

표본 API 응답을 사용하지 않고 현재 작업 환경에 설치된 `demo/app`을 최신 제품 소스의 Monitor HTTP 서버로 읽었다. Chrome에서 Codex 이벤트 18개와 종료된 실제 세션 ID 2개가 표시되며, 종료 필터·상세 화면 이동·Baseline project.md 원문 조회를 확인했다. 산출물은 7개 발견됐고 JavaScript 오류는 없었다. 이 이벤트는 2026-11-24에 보존된 기록으로, 오늘 새 이벤트가 생성되어 전달됐다는 검증과 구분한다.

해당 실제 프로젝트의 Feature와 Work Item은 각각 0개다. 현재 상위 작업 폴더도 analysis=not_started·빈 Baseline이며 저장된 Hook 이벤트는 0개다. 따라서 이 경로들에서 Feature/Gate/완료 진척의 실데이터 검증을 수행했다고 주장하지 않는다. 제품 Git 저장소에서는 실제 HTTP snapshot 조회와 변경 파일 Git diff 조회를 확인했다. 제품 Git과 대상 프로젝트 Baseline의 소유는 구분했다.

Codex 0.172.0 설치와 기존 Monitor Hook 명령의 실행 경로를 확인했으며, 설치본은 이전 Monitor 패키지를 가리킨다. 현재 프로젝트 Hook 신뢰 여부와 새 세션의 자연 발생 이벤트 수신은 이번 읽기 검증으로 확정할 수 없다. 공식 Hook 재검토·신뢰 및 최신 배포본 갱신 후 신규 이벤트 확인은 남는다. 과거의 ‘실제 Codex 연동 미확인’ 표기는 저장 기록 조회와 신규 이벤트 수신을 분리해 해석한다.
