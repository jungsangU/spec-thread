# 두 명령 설치·업데이트 검증

2026-11-23 · 로컬 배포 후보 Core 0.4.0 · 설계 1.0 유지. [설치 계약](../design/installation.md)과 [사용자 가이드](../SpecThread-설치-매뉴얼.md)에 대한 구현·실행 대조다.

## 확인한 문제와 수정

이전 문서는 공식 CLI 설치, 프로젝트 초기화, 연동 설치와 업데이트, Core pip 설치, Skill 설치, JSON 버전 계획을 사용자가 조합해야 했다. 설치된 전역 CLI·PATH·Python 환경이 다르면 같은 문장을 따라도 다른 실행부를 사용했다.

로컬 배포 폴더의 `python3 specthread install`과 `python3 specthread update`로 진입점을 통합했다. 기존 상태를 읽고 공식 명령·기존 Core 동기화를 내부에서 호출한다. 별도 DB·오케스트레이터·자동 Git을 추가하지 않았다.

## 설계·구현·증거 대응

| 계약 | 구현 | 확인 |
| --- | --- | --- |
| 로컬 배포본과 두 진입점 | 루트 specthread, sdd_core/setup.py | 가이드의 두 명령을 실제 실행. 구버전 기본 python3에서 지원 Python 탐색도 확인 |
| 공식 기능 재사용 | 전용 specify-cli 1.4.0, init/integration upgrade/status | 실제 공식 PyPI 패키지로 Codex와 Claude Code의 공식 Skill 설치. 전역 specify에 의존하지 않음 |
| Core·Skill 실행 경로 일치 | version_sync의 runner_bytes/runner_output, Project runner_hash | PATH·venv 활성화 없이 python3 .specify/sdd-core version-check 성공 |
| 앱·명세·Baseline 보존 | 기존 install_skills/scaffold/plan_sync/apply_sync 재사용 | 앱·사용자 constitution·spec/plan·활성 UUID·여섯 Baseline·Work Item 파일의 바이트 보존 |
| 검사 규칙의 쉬운 입력·재사용 | 설치 설정 check와 대화형 c 선택 | 활성 Feature 업데이트에서 실제 앱 검사를 한 번 입력하고 다음 update에서 재입력 없이 사용. 같은 update에서 검사 변경 테스트 통과 |
| 실패와 사용자 수정 보호 | 사전 공식 상태·번들·runner 검사와 기존 품질 Gate | 사용자 수정 공식/네이티브 Skill·미등록 공식 파일·사용자 runner·다른 에이전트 차단. 검사 실패는 성공으로 표시하지 않음 |
| 입력 전달 | bootstrap의 비대화형 stdin 전달 | 파이프 입력이 자식 설치 프로세스에서 EOF가 되던 문제를 수정하고 회귀 테스트 추가 |

## 실제 실행 결과

- 제품 테스트 **71개 통과**. 기존 55개와 설치 UX·실행 경로·취소·실패·보존·검사 변경의 신규 테스트 16개.
- 문서 JSON 계약 실행 **13개 통과**. 통합 설치 변경 이후 기존 Core 흐름의 회귀도 확인.
- 실제 공식 Spec Kit 1.4.0을 임시 전용 환경에 설치한 뒤, 배포 폴더에서 install/update 두 명령을 실행했다.
- Codex: 기존 앱 파일이 있는 프로젝트 신규 설치 → 활성 Feature 추가 후 업데이트 → 저장 검사로 반복 업데이트를 확인했다.
- Claude Code: 빈 프로젝트 신규 설치에서 공식 Skill과 Harness Skill 파일을 모두 확인했다.
- Git 저장소를 자동 초기화하지 않았고 앱·헌법·명세·UUID·Baseline·작업 기록을 보존했다.

테스트는 격리된 임시 앱과 캐시에서 수행했다. 사용자의 실제 앱이나 전역 Core·specify를 설치·교체하지 않았다. 네트워크는 공식 Spec Kit·의존성 준비에 사용했고 새 Core는 GitHub에서 받지 않았다.

## 재현과 한계

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/check-design-examples.py
node scripts/check-design-docs.mjs
node scripts/render-design-guide.mjs --check
```

사용자 경로 검증은 배포 폴더에서 가이드의 두 명령을 실행하고 대상 앱 폴더·에이전트·동의를 대화형으로 전달했다. 실제 앱 검사는 import와 assert가 있는 프로젝트 파일을 실행했으며 임의 성공 명령으로 대체하지 않았다.

이 확인은 설치·업데이트와 Skill 파일·Core 실행 경로에 대한 증거다. AI 앱 로그인, 새 세션의 Skill UI 표시와 도메인 개발 종단간 PoC는 별도다. 현재 가이드 범위는 macOS/Linux이며 Windows 전체 경로는 검증하지 않았다. 사용자 수정 파일·지원하지 않는 기존 형식은 강제 덮어쓰기 대신 오류를 보고한다. 설치 적용 실패 시 자동 원복이나 부분 복구를 보장하지 않는다.
