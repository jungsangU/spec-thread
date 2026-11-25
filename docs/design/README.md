# SpecThread 설계 1.1

설계 1.1 · Core 0.5.0. 주제별 원본과 구현 대조 절차를 사용한다. 설계 버전과 Core 배포 버전은 독립적이다. [설계 릴리즈 노트](../../CHANGELOG.md)

## 주제별 원본 명세

각 상세 규칙은 아래 문서 한 곳에서 관리한다. 다른 주제의 조건이 필요하면 원본을 참조하고 표·절·다이어그램 전체를 복사하지 않는다.

| 분류 | 원본 문서 | 담당 범위와 경계 |
| --- | --- | --- |
| 구성 | [전체 아키텍처](architecture.md) | 제품 Git·대상 Git의 구성과 Core·Skill·에이전트·사용자의 책임. 상세 실행 규칙은 아래 문서 참조 |
| 공식 도구 연동 | [Spec Kit 연동](spec-kit-integration.md) | 고정한 공식 버전의 기능 대조, 활성 Feature 선택, 재사용·쓰기 전제 |
| 설치·업데이트 | [통합 설치](installation.md) | 로컬 배포본 install/update, 공식 연동·전용 환경·프로젝트 실행 파일·설치 Gate |
| 런타임 연결 | [07 에이전트 설치·호출](07-agent-runtime.md) | Codex·Claude Code의 설치 경로, Skill 이름과 호출 표기 |
| 데이터 | [01 산출물·Baseline](01-artifact-model.md) | 파일별 역할, UUID·범위·Source Map, 스키마와 YAML 예시. 등록·폐기 절차는 별도 문서 |
| 정보 권위 | [02 기준 정보·충돌](02-source-of-truth.md) | 승인된 의도·현재 구현·검증 증거의 권위와 차이 해석 |
| 초기 분석 | [03 초기 분석·Discovery](03-analysis-standard.md) | Greenfield·Brownfield, 잠정 Feature와 확정, Discovery Gate, partial 개발 진입, 초기화 재개·분석 CLI |
| Feature 생명주기 | [등록·재편·폐기](feature-lifecycle.md) | Feature 등록, 병합·분할, 활성·폐기, 아카이브·경로 참조와 승인 CLI |
| 대화·진행 UX | [질문과 단계 연결](conversation-flow.md) | 질문 하나씩, 다음 제안·짧은 동의, 단계별 표시와 에이전트별 한계 |
| 개발 실행 | [04 Work Item·개발](04-artifact-lifecycle.md) | sdd-develop, 요청별 상태·범위 확대·실패·중단·재개. Feature 자체 상태와 구분 |
| 영향 판단 | [05 영향 분석·위험도](05-impact-analysis.md) | 의존성 전파·중단, SAFE·UNKNOWN·CONFLICT, 근거와 핵심 위험 차단 |
| 검증 프로파일 | [위험도 기반 절차·정의 재사용](verification-profiles.md) | 분류·최소 절차·자동/예외 승인·verification.yaml·결과 공유 |
| 실행 검증 | [06 Gate·증거·Fingerprint](06-verification.md) | 필수 집합 정의·실행·이력·단계 차단·완료·무효화와 재검증 |
| 외부 변경 | [수동 Sync](reconciliation.md) | inspect→plan→approve→apply→verify, 실패 시 보존, 현행 승인 경계. Core 버전 동기화와 구분 |
| 로컬 업데이트 | [Core 버전 동기화](version-sync.md) | 취득·버전 일치·누적 메타데이터 변환·승인·필수/품질 Gate·사용자 원복 |
| Git·협업 | [08 Git·세션 운영](08-git-integration.md) | 대상 Git 반영, 병렬 세션 책임·제외 범위, 제품 브랜치·PR·CI·설계 릴리즈 |
| 제품 구현 절차 | [구현·설계 대조 반복](implementation-standard.md) | 구현·테스트·원문 재대조·누락 보완의 반복과 완료 증거 |
| 개발 관측 | [SpecThread Monitor](monitor.md) | 사용자 실행형 읽기 전용 관측, 이벤트·화면 및 입력 한도 |
| 인수 검증 | [PoC·MVP 인수 기준](acceptance.md) | P01~P18 시나리오, 수집 증거와 통과 기준. 실제 진행 상태는 백로그 |

## 결정과 진행 상태

- [DECISIONS](DECISIONS.md): 결정 ID, 선택 이유와 대체·폐기 이력. 본문의 현재 명세와 구분한다.
- [OPEN-ISSUES](OPEN-ISSUES.md): 미결정·보류, 구현 경계와 실제 검증 상태. 확정 정책을 미결정으로 되돌리지 않는다.
- [CHANGELOG](../../CHANGELOG.md): 사용자 선택으로 배포한 설계 버전의 릴리즈 노트.

**설계 정책**, **현행 구현**, **실행 검증**은 각각 합의한 규칙, 코드가 처리하는 범위, 실제로 확인한 결과다. 주제 본문의 Core 0.5.0 절은 구체적 계약을, 백로그는 남은 확인 상태를 담당한다.

## 소개와 사용 안내

다음은 규칙의 별도 원본이 아닌 탐색·설명 자료다.

- [제품 소개 HTML](SpecThread-설계-소개.html): 사용 장면과 그림, Spec Kit·SpecThread·사용자의 관계.
- [전체 기능 목록 HTML](SpecThread-전체-기능목록.html): 기능·적용 방식·소유·상태별 검색. 각 행에서 주제별 근거로 이동.
- [실행 가이드](SpecThread-설계와-실행-가이드.md) · [HTML](SpecThread-설계와-실행-가이드.html): 사용 순서, 할 일 앱 사례와 완료 계획 예시.
- [통합 상세 설계서 진입점](SpecThread-통합-상세-설계서.md): 기존 경로와 절 제목을 유지하는 주제별 상세 문서 안내.
- [설치 매뉴얼](../SpecThread-설치-매뉴얼.md): 실제 설치와 시작 절차.

## 새 세션 읽기 순서

1. [AGENTS](../../AGENTS.md) → 이 목차 → [아키텍처](architecture.md) → [기준 정보](02-source-of-truth.md)에서 저장소·책임·권위를 이해한다.
2. [결정 기록](DECISIONS.md)과 [백로그](OPEN-ISSUES.md)를 읽어 유효한 정책·제외 기능·미확인 상태를 구분한다.
3. 작업에 맞는 위 원본을 읽고 연결된 데이터·영향·검증 계약까지 확인한다. 전체 재구성이 필요하면 표의 원본 문서를 순서대로 모두 읽는다.
4. 실행 예시는 가이드, 인수 조건은 PoC 문서를 확인한다. 개요·사례만 읽고 상세 계약을 추정하지 않는다.

## 구현 재현성 검증

현재 설계 1.1의 D01~D10 구현·검증·비교와 미측정 범위는 [위험도 기반 검증 보고서](../validation/risk-profiles-1.1-review.md)를 따른다. 아래 설계 1.0 보고서는 당시의 보존·기존 구현 근거다.

[Core 0.5.0 구현·설계 재대조 결과](../validation/design-1.0-implementation-cycle.md)와 [문서 정리 당시 검토](../validation/design-1.0-implementation-review.md)에 정리 전후 보존 대조, 코드·테스트 대응, 문서 예시 실행과 미완료 범위를 기록한다. 정책 원본을 대체하지 않는 검증 보고서다. 구현 작업은 주제별 입력·출력·저장 필드·명령·Gate·실패 조건까지 읽어야 한다.

실제 공식 Spec Kit 1.4.0을 사용한 두 명령 설치·업데이트 검증은 [설치 검증 보고서](../validation/installation-two-command-review.md)를 따른다.

공통 대화 지침의 설치·무결성 확인과 실제 대화 검증의 한계는 [대화 UX 검증](../validation/conversation-flow-review.md)에 기록한다.

## 문서와 HTML 갱신

정책·계약 변경은 해당 주제 원본에 반영하고 관련 문서의 참조와 설명 자료만 맞춘다. 결정 변경은 DECISIONS, 남은 확인 상태는 OPEN-ISSUES에 반영한다. 같은 상세 명세를 가이드나 통합 진입점에 다시 싣지 않는다. 문서 정리만으로 설계 버전을 올리지 않는다.

실행 가이드 HTML만 같은 이름의 Markdown에서 생성한다. 제품 소개·기능 목록 HTML은 별도 설명 자료이므로 관련 내용과 근거 링크를 직접 갱신한다. HTML은 브라우저에서 인터넷 없이 열 수 있다.

```sh
npm install --no-save --package-lock=false marked@17.0.5 @viz-js/viz@3.25.0
node scripts/render-design-guide.mjs
node scripts/render-design-guide.mjs --check
node scripts/check-design-docs.mjs
# 제품 의존성을 설치한 Python 3.11 이상
python3 scripts/check-design-examples.py
```
