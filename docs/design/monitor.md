# SpecThread Monitor

설계 1.0 · 사용자 승인 2026-11-23. 선택 설치 모듈은 지정한 프로젝트를 읽어 화면을 제공한다. [사전 검토와 사용자 제공 시각 레퍼런스](../validation/monitor-design-review.md)

## 요구사항과 경계

- Project Overview와 SDD Pipeline은 Worktree, 분석, 공식 태스크, 설치 버전·Skill·runner 해시 대조, 저장 품질 제한의 출처를 표시한다.
- Feature·Work Item Explorer는 기존 UUID와 의존성, 선언·실제 범위 및 과거 작업 참조를 유지한다. 저장 상태의 의미는 [개발 생명주기](04-artifact-lifecycle.md)를 따른다.
- Artifact Explorer는 Spec Kit와 Baseline의 경로, 존재 여부, 수정 시각, 관측된 변경과 연결 Gate 결과를 표시한다. Gate Monitor는 실제 필수 여부, 적용 단계, 최근 실행과 증거를 표시한다. 열린 작업은 [Core 검증](06-verification.md)의 증거 유효성을 재사용하고 종료 기록은 당시 결과로 표시한다.
- Next Actions는 저장 상태에서 확인한 검토 항목과 수신한 권한 요청을 제시한다. 현재 승인 대기를 확인할 근거가 없으면 화면에 미확인으로 표시한다.
- Session Monitor는 사용자가 연결한 에이전트 스트림의 세션과 파일 이벤트를 시간순 소스 순서로 보여 준다. 작업 트리 diff의 범위는 Git이고 세션에 귀속할 수 있는 경로는 에이전트 이벤트에 명시된 경로다.
- Focus와 Living은 동일한 데이터를 제공한다. Living의 야간 픽셀 사무실은 새 관측 이벤트에서만 짧게 움직인다. 키보드 탐색, 텍스트 상태, 시스템의 축소 모션을 지원한다.

## 대시보드 지표

상단에는 활성 Feature의 공식 태스크 체크 비율, 표시한 Work Item의 완료 비율, 열린 Work Item에 기록된 전체 필수 Gate 중 현재 유효한 PASS 비율을 표시한다. Gate 집합이 없는 열린 작업 수를 함께 표시한다. 표본 한도가 적용되면 표시 범위임을 알린다.

테스트 통과율은 현재 프로젝트의 `test-results/junit.xml`에서 읽은 최근 보고서의 통과 케이스를 실행 케이스로 나눈 값이다. 실패와 오류는 실행 분모에 포함하고 건너뛴 케이스는 별도로 표시한다. 보고서 시각은 파일 수정 시각이다. 테스트 재실행은 사용자 또는 기존 검사 흐름이 수행한다.

대시보드는 공식 태스크 진행 바, 최근 테스트 도넛, 필수 Gate 진행 바, Work Item 상태 분포와 세션별 최근 이벤트·변경 파일 수를 표시한다. 종료 이벤트가 없는 세션 수는 관측 범위의 집계다. Living 사무실은 최대 다섯 캐릭터를 배치하고 한 번의 관측에서 여러 세션 활동이 바뀌면 각각 반응한다.

좌측 메뉴는 세션·Feature·Work Item과 Gate·산출물·Git·Pipeline의 상세 화면으로 이동한다. 산출물 탐색에서 경로를 검색하고 선택하면 발견된 프로젝트 내부 일반 텍스트 파일의 처음 96 KiB를 미리 본다. 원문은 텍스트로 표시한다.

## 실행 구조

브라우저 → 로컬 Monitor → Core 읽기 로직·공식 산출물·읽기 전용 Git·사용자가 지정한 이벤트 파일. Core와 Skill은 Monitor를 호출하지 않는다. 통합 설치 도구는 사용자가 선택한 경우 Monitor 패키지를 추가한다. 실행과 중지는 사용자가 제어한다. 새 에이전트 세션과 함께 연 Monitor는 해당 세션이 끝나면 함께 닫힌다. 브라우저가 보이는 동안 3초 간격으로 읽기 스냅샷을 요청한다. 파일 감시 서비스, 세션 조정, 자동 Git 조작, 승인·검사 명령 실행, 별도 LLM 호출은 구성에 없다. [Git·세션 운영](08-git-integration.md), [소스 권위](02-source-of-truth.md)

Monitor 배포는 Core와 별도다. 0.1.0은 Core 0.4.0을 사용한다. Baseline 스키마 1을 읽고 미지원·누락·불완전 데이터는 Git과 공식 파일 관측으로 내려간다. 사용자가 설치나 마이그레이션을 선택하는 경우 [기존 버전 동기화](version-sync.md)를 사용한다.

설치 기록 대조는 대상 runner를 실행하지 않는다. 개발 진입 판단과 실제 버전 동기화의 필수·품질 Gate는 Core가 담당한다.

## 입력과 관측 한도

- 제품 루트에서 `python3 specthread install --monitor`를 실행해 설치 대상을 선택한다. 프로젝트의 `./monitor`는 사용자 요청으로 새 터미널 에이전트 세션과 대시보드를 함께 연다. 별도 관측은 `./monitor --dashboard-only`로 실행한다. 에이전트 CLI가 없으면 대시보드만 열린다. 기존 Core는 별도 환경을 사용한다.
- 동시 실행은 프로젝트가 선택한 CLI와 공식 Hooks를 사용한다. Codex는 설치 시 프로젝트 Hook에 관측 핸들러를 추가하며 사용자의 공식 신뢰 절차가 적용된다. Claude Code는 실행 시 설정을 전달한다. Hooks는 현재 연결에서만 메타데이터를 권한 제한 임시 파일로 전달한다. 이 파일은 크기 한도를 넘으면 추가 기록을 멈추며 세션 종료 때 제거한다. 기존 세션의 종료·복구·재시작이나 승인 조작은 수행하지 않는다.
- Codex의 [공식 exec JSONL](https://learn.chatgpt.com/docs/non-interactive-mode)은 실행당 한 파일에 사용자가 기록하여 `--codex-events FILE`로 선택한다. [Codex 공식 Hooks](https://learn.chatgpt.com/docs/hooks)의 사용자 설정 전달자도 지원한다. Codex Hooks의 패치 본문 대신 exec의 명시적 file_change 경로로 파일을 연결한다.
- Claude Code의 [공식 Hooks](https://code.claude.com/docs/en/hooks)에서 사용자가 별도로 설정한 전달자가 stdin 객체를 한 줄씩 기록하면 `--claude-events FILE`로 선택한다. `claude -p --verbose --output-format stream-json`의 세션 시작·결과 줄도 읽는다. Hooks의 파일 경로는 지정한 루트의 이벤트만 사용한다. 실시간 전달은 사용자가 선택한 인터페이스의 지원과 설정에 의존한다.
- 이벤트 수집은 최신 256 KiB를 소스별 최대 10개에서 읽고, 최근 100개를 응답에 포함한다. 프롬프트·명령 본문·도구 출력·대화의 내용은 Monitor 응답과 저장 범위에서 제외한다. 입력 파일은 사용자가 관리하고 공식 원본 스트림 외에 Monitor가 만드는 연결 로그는 동시 실행에만 사용하는 임시 메타데이터 파일이다.
- Git 호출은 3초와 기본 256 KiB 출력 한도를 사용한다. 스냅샷은 2초 동안 메모리에 재사용하며 하나의 요청 처리 흐름에서 연산한다. Git 변경 250개, 산출물 400개, Feature·Work Item 각 100개까지 표시한다. Baseline 개별 읽기는 2 MiB, 열린 작업 Gate 증거는 작업당 8 MiB, 스냅샷당 최대 16개 작업을 확인한다. 한도 밖의 현재 Gate 유효성은 UNKNOWN이다.
- 서버는 IPv4 루프백으로만 연결하고 Host 검사, 실행마다 새로 발급하는 API 토큰, 캐시 금지와 외부 스크립트·프레임 차단을 적용한다. Git diff에는 소스 내용이 포함된다. 실행 링크는 해당 사용자에게만 제공한다.

## 인수 확인

[검증 대응표](../validation/monitor-design-review.md)에서 실제 검증 결과와 후속 PoC를 확인한다.
