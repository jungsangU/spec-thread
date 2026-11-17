# 07 에이전트와 Core의 역할

| 작업 | Codex | Claude Code |
| --- | --- | --- |
| 설치 위치 | `.agents/skills/<이름>/SKILL.md` | `.claude/skills/<이름>/SKILL.md` |
| 초기화 | `$sdd-init` | `/sdd-init` |
| 개발 | `$sdd-develop` | `/sdd-develop` |
| 외부 변경 정합화 | `$sdd-sync` | `/sdd-sync` |

공식 GitHub Spec Kit는 독립 설치한다. 문서 재현 기준은 v1.4.0이다. `sdd-core install-skills codex|claude`는 공통 절차를 각 폴더에 설치하고 같은 위치에 내용이 다른 스킬과 충돌하면 오류를 보고한다. 기존 공식 설치를 교체할 필요가 없다.

에이전트가 Discovery에서 공식 `specify`와 `clarify`를 사용해 분석하고 근거를 제출한다. Core의 `discovery-gate`는 입력 형식과 필수 점검을 검사해 판정하며, 신규 Feature에는 `--issue-id`로 READY에서만 UUID를 발급한다. 에이전트는 공식 스킬과 템플릿을 사용하고, 대상 Feature의 경로를 확인하며, 문서 작성·코드 구현·의미 분석·사용자 안내를 수행한다. 공통 CLI가 구조·상태·검증 명령과 입력 동일성을 점검한다. 이 구조는 에이전트가 달라도 한 가지 완료 규칙을 사용할 수 있게 한다.

프로젝트별 에이전트 선택과 Worktree 생성·분배·중단·재개는 사용자 책임이다. 중앙 세션 관리자, 잠금, 대기열, SQLite, 실시간 감시는 설계 범위 밖이다. Codex에서 초기화와 개발을 실행 확인했다. Claude Code는 스킬 설치 형태를 확인했으며 동일한 종단간 실행 검증이 남아 있다.
