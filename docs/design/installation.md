# 신규 설치와 업데이트의 통합 진입점

설계 2.0 · 사용자 요청: 내려받은 배포본에서 install/update 두 명령으로 설치 절차를 끝낸다. 사용자 단계는 [설치 가이드](../SpecThread-설치-매뉴얼.md), 내부 버전 변환·품질 제한은 [버전 동기화](version-sync.md)가 원본이다.

## 경계와 명령

- 배포 폴더의 `python3 specthread install`과 `python3 specthread update`가 사용자 진입점이다. 새 앱·기존 앱·기존 Spec Kit 유무는 내부에서 분기한다.
- Core를 GitHub에서 자동 취득하지 않는다. 사용자가 선택한 로컬 배포 폴더를 설치 원본으로 사용한다. 공식 Spec Kit와 Python 의존 패키지는 명시적인 설치 실행 중에 다운로드할 수 있다. 상시 조회·알림·자동 업데이트는 없다.
- 공식 Spec Kit는 Python 전용 환경에 `specify-cli==1.4.0`으로 설치하고 공식 init/integration install/integration upgrade/status를 호출한다. 공식 관리 파일·명세·라이프사이클을 Harness가 새 형식으로 대체하지 않는다. [공식 설치](https://github.github.com/spec-kit/installation.html) · [업데이트](https://github.github.com/spec-kit/upgrade.html)
- 에이전트 앱의 설치·인증과 Git 운영은 사용자 책임이다. 설치는 `sdd-init`의 도메인 분석을 대신 실행하지 않는다.

## 선택 설치

`python3 specthread install --monitor`는 기존 설치 완료 뒤 별도 환경에 [Monitor](monitor.md)를 추가한다. 이미 등록한 대상에 이 옵션으로 install을 실행하면 Monitor만 설치한다. 프로젝트의 `./monitor` 또는 Windows의 `.\monitor.cmd`를 실행하며 대상 Core의 Python·버전 기록은 기존 설치 흐름이 소유한다.

## 입력·출력

적용 확인에서 c를 선택하면 저장한 앱 검사 명령을 변경하고 현재 입력으로 계획을 다시 계산한 뒤 적용 동의를 받는다. 별도 설치 명령을 조합하지 않는다.

입력은 action, 대상 앱 폴더, 선택 또는 기존 기록의 에이전트, 로컬 Core 소스와 필요한 기존 프로젝트 검사다. 기본 질문으로 입력하며 자동화는 --project/--agent/--check/--yes를 사용할 수 있다. 여러 에이전트를 같은 프로젝트에 자동 설치·전환하지 않는다. 새 대화형 설치는 앱 경로, 에이전트, Monitor 설치 여부를 순서대로 묻는다. `--monitor`와 `--no-monitor`로 선택을 명시할 수 있다.

대화형 update에서 --project를 생략하면 현재 폴더의 설치된 앱을 우선하고, 없으면 마지막으로 기억한 앱 경로를 표시해 `기존 앱 경로가 맞나요? [경로] [Y/n]`으로 확인한다. Enter/y는 그대로 사용하고 n은 기존 경로 입력으로 전환한다. 기억한 폴더가 없거나 삭제·설치 기록 유실·캐시 손상 상태이면 경로를 직접 입력한다. --project는 확인 없이 명시한 대상을 사용하고 비대화형은 저장 경로를 자동 선택하지 않는다. 설치·업데이트 종료 코드가 성공이고 설치 표식이 있는 대상만 UTF-8 원자적 파일 교체로 기억한다. 앱 선택용 환경설정이며 Baseline·승인·실행 상태를 대체하지 않는다. 새 배포 폴더에서도 같은 캐시를 사용하면 재사용하며 여러 앱은 명시한 경로/현재 앱 폴더가 우선한다. 구버전에서 기억한 경로가 없으면 한 번 입력해야 한다.


pip의 SSL 오류 이후 사용자가 동의하면 기본 PyPI 호스트인 pypi.org와 files.pythonhosted.org의 인증서 검사를 건너뛰고 다운로드를 한 번 다시 시도한다. `--ssl-trust`로 처음부터 지정하거나 비대화형으로 다시 실행할 수 있다. 해당 설정은 이 설치의 pip 프로세스에만 적용한다.

출력은 공식 Spec Kit 프로젝트 연동, Harness 네이티브 Skill, 기존 Project·Skill 버전 표식, Baseline 일곱 파일과 프로젝트 실행 파일·설치 설정이다. 새 설치는 아직 분석되지 않은 빈 Baseline을 만들며 UUID·READY·PASS를 추정하지 않는다. 업데이트는 기존 기록을 유지한다.

| 위치 | 소유와 목적 |
| --- | --- |
| `~/.cache/spec-thread/runtime-<배포 내용 해시>/` | 전용 Python·로컬 Core·고정 Spec Kit. 사용자 전역 Python·specify를 교체하지 않는다. SPEC_THREAD_CACHE로 위치 지정 가능 |
| `~/.cache/spec-thread/last-project.json` | 마지막 확인된 설치 대상의 경로 환경설정. SPEC_THREAD_CACHE를 변경하면 그 캐시의 기억을 사용하며, 저장 실패는 경고하고 앱 설치 성공을 취소하지 않음 |
| `.specify/sdd-core` | Core가 생성한 프로젝트 실행 파일. 선택한 Python과 패키지 경로로 실행해 PATH·가상환경 활성화에 의존하지 않음 |
| `.specify/spec-thread.json`의 runner_hash | 실행 파일의 관리 해시. 기존 버전·품질 필드와 함께 확인 |
| `.specify/spec-thread-install.json` | agent/core_version/spec_kit_version/check 기록. 프로젝트의 기존 검사 argv를 재사용하며 실행 상태 DB가 아님 |

전용 환경 캐시는 src/pyproject의 실제 내용 해시로 구분하고 준비 완료 표식을 패키지 설치 성공 후에만 쓴다. 설치 프로그램 자체의 병렬 실행 보장은 추가하지 않는다. 개발 중 관리 잠금과는 별개다. 사용자 앱을 변경하는 설치는 같은 프로젝트에서 동시에 실행하지 않는다.

## 흐름과 Gate

~~~mermaid
flowchart TD
  L["로컬 배포본의 install 또는 update"] --> P["대상 폴더·Python·에이전트 확인"]
  P --> E["전용 Core·고정 Spec Kit 환경 준비"]
  E --> R["기존 설치·사용자 수정·검사 규칙 사전 점검"]
  R --> A{"사용자 적용 동의"}
  A -->|거절| X["프로젝트 변경 없이 종료"]
  A -->|동의| O["공식 프로젝트 초기화·연동 설치 또는 갱신"]
  O --> C["Harness 설치·기존 누적 버전 동기화"]
  C --> G{"버전·구조·기존 검사·공식 설치 확인"}
  G -->|통과| D["설치 설정 기록 · 완료 안내"]
  G -->|실패| F["실패 단계·부분 변경 보고 · 사용자 조치"]
~~~

기존 Core에서는 공식 파일을 쓰기 전에 기존 누적 변환 계획을 미리 계산해 사용자 수정 Harness Skill·잘못된 구조를 조기에 차단한다. 공식 단계 이후에는 현재 입력으로 계획을 다시 계산한다. 사용자에게 JSON·승인 해시를 직접 작성·복사하도록 요구하지 않으며 같은 대화형 명령의 동의 범위에서 기존 plan_sync/apply_sync를 사용한다.

초기 설치는 공식 Spec Kit가 없으면 `init --here --force --integration AGENT --ignore-agent-tools --non-interactive --script sh`를 실행한다. force는 비어 있지 않은 앱 폴더에 공식 관리 파일을 처음 배치하기 위한 내부 옵션이다. 기존 정상 공식 설치에는 이 초기화를 반복하지 않는다. 기존 등록이 있으면 재사용하거나 공식 integration upgrade를 호출한다. 사용자 수정 공식 파일은 상태 검사로 차단하며 upgrade에 강제 덮어쓰기 옵션을 주지 않는다.

활성 Feature가 있으면 저장한 프로젝트 검사 argv를 사용하거나 실제 검사 명령을 한 번 묻는다. 전역 범위의 실제 소스·테스트 파일을 기존 품질 계획에 포함해 실행하고 입력 변경도 검사한다. Feature가 없는 초기 상태는 Core의 Baseline validate를 실행하며 이를 앱 품질 검증이라고 주장하지 않는다. 검사 실패·설치 파일 누락·수정 충돌은 완료로 보고하지 않는다. 선택한 검사 argv는 실행 전에 설치 설정에 보존하며 실패 재시도에서 앱 검사를 빈 Baseline 검사로 낮추지 않는다. 성공한 경우에만 Core·Spec Kit 설치 버전을 설정에 기록한다.

## 실패·재시도·기존 자료

프로젝트 변경 전에 취소하면 앱을 쓰지 않는다. 전용 환경 준비 실패는 완료 표식을 쓰지 않고 로그를 남긴다. 프로젝트 적용 이후 실패는 단계와 부분 변경을 보고하며 자동 Git 원복·부분 복구·실패 마이그레이션 재개를 제공하지 않는다. 사용자가 파일과 설치 상태를 확인·원복하고 같은 update 명령으로 처음부터 검증한다.

Core 실행 파일은 기록한 관리 해시와 일치하는 파일만 교체한다. 기존 Project에 실행 파일이 없으면 추가하며 사용자 수정본은 덮어쓰지 않는다. 설치된 Native Skill의 Core 명령은 `python3 .specify/sdd-core ...`를 사용해 새 AI 세션에서도 PATH와 활성 venv를 가정하지 않는다. 공식 Skill은 공식 설치본을 유지한다.

설치·업데이트의 Python 자식 프로세스와 Spec Kit 출력은 UTF-8로 통일하며 JSON 파일도 UTF-8로 읽는다. CP949 터미널의 표현 불가능한 문자는 설치를 중단시키지 않도록 대체 표기한다. 선택 설치한 Monitor의 관리 실행기와 Hook도 같은 `update`에서 갱신하며 상세 관측 계약은 [Monitor](monitor.md)를 따른다.

새 설치는 verification.yaml을 포함한 일곱 파일을 만들며 실제 검증 정의가 없으면 unconfigured다. 설치 성공은 개발 준비·검증 통과를 의미하지 않는다. 기존 0.4.0 배포의 업데이트는 [0.5.0 누적 변환](version-sync.md) 후 현재 위험/검증 정의를 확인한다.

## Core 0.6.0 모드 설치

신규 대화형 설치는 Direct/Isolated를 선택하고 `--mode direct|isolated`도 받는다. 비대화형 미지정과 기존 설정 없는 업데이트는 Direct가 기본이며 기존 mode/runtime/limits는 보존한다. 활성 Work 중 모드 변경, 활성 Workspace/저널 중 업데이트를 사전 차단한다. 다운로드한 배포본의 install/update 두 명령과 기존 품질·승인 계약은 유지한다. [모드·Runtime 상세](parallel-development.md).
