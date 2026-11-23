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

[Codex 공식 JSONL 예제](https://developers.openai.com/blog/eval-skills)와 [Claude Code Hooks 레퍼런스](https://code.claude.com/docs/en/hooks)는 사용자가 선택해서 연결할 수 있는 후보 입력이다. 실제 실행 환경에서의 이벤트 전달과 파일 귀속은 아직 검증하지 않았다. Monitor가 클라이언트를 기동하거나 비공개 세션 파일을 탐색하거나 별도 LLM을 호출하는 방식은 범위에서 제외한다.

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
