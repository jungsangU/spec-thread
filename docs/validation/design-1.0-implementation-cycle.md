# 설계 1.0 구현·재대조 반복 결과

2026-11-23 · 설계 1.0 유지(사용자 선택) · Core 0.4.0. [구현 반복 절차](../design/implementation-standard.md)를 이번 변경에 적용한 실행 기록이다. [이전 Core 0.3.0 검토](design-1.0-implementation-review.md)는 구현 전 기록으로 보존한다.

## 이번 범위와 반복

사용자가 남은 구현을 요청한 승인형 Sync 강제 검증·작업 이력, 선택적 재검증·이름 변경·결과 이관을 구현하고 제품 개발의 반복 검토 규칙을 AGENTS와 설계에 연결했다. 별도 오케스트레이터·DB·자동 Git은 추가하지 않았다.

1. 기존 Core·Skill·테스트와 ST-O4·ST-O6를 대조해 Skill에 있는 절차와 Core에 없는 강제 동작을 분리했다.
2. 기존 Work Item·Gate 기록에 정합화와 재검증을 연결했다. 정상·차단·부분 실패 테스트를 작성하고 실행했다.
3. 원문과 재대조하면서 승인 범위에 공식 자료 추가·선택자·설치 입력도 묶고, 승인된 이름 변경 시 활성 Source Map을 갱신하도록 보완했다. 기존 완료 이력·사용자 확장 메타데이터와 업그레이드 보존도 점검했다. Discovery 흐름도의 UUID 발급 위치도 실제 등록 명령의 spec·plan 준비 조건에 맞춰 명확히 했다.
4. 수정 후 전체 테스트·문서 예시 실행·실제 이전 배포본에서의 wheel 업그레이드를 다시 확인했다. 아래 구현 범위에서 남은 누락은 발견하지 않았다. 실제 에이전트 PoC까지 완료됐다는 판정은 아니다.

## 설계·구현·테스트 대응

| 설계 원본 | 구현과 실행 연결 | 검증 근거·판정 |
| --- | --- | --- |
| [제품 구현 반복](../design/implementation-standard.md) | AGENTS 필수 지침, README·가이드·기능 목록 연결, CI 문서 예시 실행 | 이번 1~4 반복과 본 대응표. 절차 반영 완료 |
| [수동 Sync](../design/reconciliation.md)의 비교 기준·승인 고정 | reconciliation.prepare, cli reconcile preview/confirm | 입력·변경안·보존 자료·Git HEAD commit 이동·공식 문서 추가 후 이전 승인 차단. 미리보기 무쓰기 통과 |
| Sync 범위와 실제 적용 | 승인된 공식 Markdown·허용 Baseline만 writes, 적용 전 snapshot 재계산 | 앱·경로 탈출·Work Item 이력 직접 쓰기·핵심 UNKNOWN·검사 없는 계획 차단 통과 |
| Sync 작업 이력·검증·실패 | reconciliation.apply → 기존 Work Item·Gate → gate-run/gate-refresh → complete | 자동 UUID/승인·base·입력 기록, 검증 전 완료 차단, 적용 실패 failed·부분 변경 보고·자동 원복 없음, 완료 후 수정 거부 통과 |
| [선택적 재검증](../design/06-verification.md) | revalidation.prepare/refresh → 기존 Gate 실행기 | 변하지 않은 최신 유효 PASS 재사용, STALE만 실행, 최신 FAIL을 과거 PASS로 대체하지 않음 통과 |
| 이름 변경 승인·이관 근거 | 동일 바이트 단일 후보, 새 revision·Source Map, reused_from | 미리보기 무쓰기, 후보 중복·삭제·승인 후 후보 추가 차단, 변경 Gate 재실행·그대로인 Gate 이력 이관과 원본 보존 통과 |
| 검토·상태 경계 | review_required, 기존 stage 조건, editable Work Item 검사 | 실제 검토가 필요한 Gate는 BLOCKED, completed 재검증 기록 변경 차단 통과 |
| [버전·설치](../design/version-sync.md) | 기존 누적 0.3.0→0.4.0, Skill 해시와 버전 일치 | Git HEAD의 실제 0.3.0 실행부·Skill을 설치 후 새 wheel로 승인 업그레이드. 앱·여섯 Baseline의 바이트 보존 및 version-check 통과 |
| [데이터 계약](../design/01-artifact-model.md) | schema_version 1 유지, kind/reconciliation·reused_from 선택 필드 | 기존 37개 회귀 테스트 및 새 계약 테스트 통과. 이전 UUID·완료 이력 변환 없음 |

## 실행 결과

- 제품 테스트 **55개 통과**: 기존 37개 + 신규 Sync·재검증 17개 + 0.3.0 업그레이드 1개.
- 문서 JSON 예시의 실행 계약 **13개 통과**. 새 Sync 예시와 gate-refresh의 기존 Work Item·Gate·완료 연결도 포함한다.
- 0.4.0 wheel 빌드 및 CLI 실행, 실제 0.3.0→0.4.0 Skill 교체·버전 표식 업그레이드와 기존 자료 보존 통과.
- Markdown 구조·내부 링크, 설계 1.0·CHANGELOG 일치, 실행 가이드 HTML 재생성·동기화 검사 수행.

재현 명령은 제품 의존성을 설치한 Python 3.11 이상과 문서 빌드 의존성을 준비한 저장소에서 실행한다.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/check-design-examples.py
node scripts/check-design-docs.mjs
node scripts/render-design-guide.mjs --check
```

## 검증의 한계와 남은 실행 확인

- 실제 Codex·Claude Code 공식 호출과 Brownfield·다중 Feature·재개·Sync의 종단간 PoC는 ST-O1·ST-O2·ST-O7·ST-O9·ST-O11에서 계속 추적한다. CLI fixture는 공식 Spec Kit의 실제 설치·위임 증거가 아니다.
- 비교·검증의 의미적 충분성과 중요한 의도 변경 승인은 Skill·사용자 책임이다. 해시 일치만으로 의미 판단이나 사용자 신원을 증명하지 않는다.
- 이름 변경 자동 제안은 바이트 동일·단일 후보이며 의미가 변한 이동은 명시적으로 재설계·재검증한다. review 결과를 자동 생성하거나 다른 Work Item에서 결과를 가져오지 않는다.
- 선언한 코드·계약·Gate 입력 밖의 영향은 Skill이 조사한다. 다중 파일 원자성·세션 동시성·자동 원복을 보장하지 않는다.
- 이번 작업은 로컬 코드·문서·테스트·격리된 패키지 업그레이드까지다. 사용자의 실제 대상 프로젝트 설치 교체, Git Commit·Push·태그·Release는 실행하지 않았다.
