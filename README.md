# SpecThread

<div align="center">

### AI 개발의 의도, 변경, 검증을 프로젝트에 남깁니다.

공식 **GitHub Spec Kit**와 함께 사용하는 개발 하네스.<br>
**Codex · Claude Code**의 개발 흐름에 기능 추적과 검증 기준을 연결합니다.

![Core 0.3.0](https://img.shields.io/badge/Core-0.3.0-b75d43?style=flat-square)
![Design 1.0](https://img.shields.io/badge/Design-1.0-7b7265?style=flat-square)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3f6b59?style=flat-square)
![Spec Kit 1.4.0](https://img.shields.io/badge/Spec_Kit-1.4.0-63598a?style=flat-square)

[제품 소개](docs/design/SpecThread-설계-소개.html) · [전체 기능 목록](docs/design/SpecThread-전체-기능목록.html) · [설치 매뉴얼](docs/SpecThread-설치-매뉴얼.md) · [설계 문서](docs/design/README.md)

</div>

---

## SpecThread가 하는 일

“이 요구사항은 어느 기능에 속하고, 어디까지 바꿔야 하며, 무엇을 확인해야 완료일까?”

SpecThread는 사용자 요청을 **Feature**, **Work Item**, **검증 근거**로 연결합니다. 신규 프로젝트에서는 요구사항과 업무 흐름을 분석하고, 기존 프로젝트에서는 코드·문서·테스트로 현행 동작을 이해합니다. 공식 Spec Kit의 명세·계획·태스크·구현 흐름을 활용하면서 프로젝트 전체의 관계와 완료 조건을 관리합니다.

| 기능 | 적용 방식 |
| --- | --- |
| **Discovery와 기능 확정** | 업무 흐름과 요구사항의 경계를 검토하고 READY / CONDITIONAL / BLOCKED로 판정합니다. |
| **부분 분석 상태의 개발** | 대상 기능이 READY이고 미분석 영역과 핵심 의존성 위험 없음이 검증되면 개발을 허용합니다. |
| **지속적인 기능·작업 추적** | Feature UUIDv7과 요청별 Work Item으로 구현 파일·의존관계·변경 이력을 연결합니다. |
| **필수 Gate와 실제 증거** | 적용 검증 집합을 먼저 정하고 실행 결과·증거·입력의 현재 유효성을 검사합니다. |
| **기능 재편과 이력 보존** | 폐기 산출물을 아카이브하고 과거 UUID와 작업 기록을 보존하며 활성 의존관계를 다시 평가합니다. |
| **로컬 버전 동기화** | Core·Project·Skill 버전 차이를 분석하고 사용자 승인 후 필요한 메타데이터를 변환·검증합니다. |

## Spec Kit와 어떻게 함께 쓰나요?

| 구성 | 맡는 역할 |
| --- | --- |
| **GitHub Spec Kit** | 공식 명세 작성, 명확화, 기술 계획, 태스크 생성, 구현, 산출물 분석과 구현 대조 |
| **SpecThread Skill** | 프로젝트 분석과 공식 명령 연결, 영향 판단, 적용 Gate 선정, 사용자 확인과 결과 보고 |
| **Shared SDD Core** | UUID·참조·상태·버전 검사, Gate 정의와 결과의 대응, 실행 증거·입력 유효성 검증 |
| **사용자** | 요구사항과 변경 승인, 에이전트 선택·작업 분배, Core 설치·교체, Git 반영·원복 |

```mermaid
flowchart LR
    R["요구사항 · 기존 시스템"] --> D["Discovery · Feature 확정"]
    D --> W["Work Item · 적용 Gate"]
    W --> S["공식 Spec Kit 개발 흐름"]
    S --> V["영향 분석 · 실행 검증"]
    V --> B["Baseline · 완료 이력"]
```

## 세 가지 작업 흐름

| 작업 | Codex | Claude Code | 결과 |
| --- | --- | --- | --- |
| **프로젝트 시작** | `$sdd-init` | `/sdd-init` | 전체 범위 조사, 기능 후보·명세·계획, Discovery 근거와 Baseline |
| **개발 요청** | `$sdd-develop` | `/sdd-develop` | 요청별 Work Item, 공식 개발 산출물, 영향 판정과 필수 검증 결과 |
| **외부 변경 정합화** | `$sdd-sync` | `/sdd-sync` | 차이 조사, 사용자 승인 변경안, 관련 자료 정합성과 재검증 |

한 프로젝트에서 **Codex 또는 Claude Code 한 종류**를 선택합니다. Skill은 의미와 근거를 분석하고, Core는 저장된 계약과 완료 조건을 검사합니다.

## 빠르게 시작하기

**Python 3.11 이상**과 **공식 GitHub Spec Kit v1.4.0으로 초기화한 대상 프로젝트**를 준비합니다. 공식 도구 설치와 에이전트 연동은 [설치 매뉴얼](docs/SpecThread-설치-매뉴얼.md)에 정리되어 있습니다.

SpecThread 소스 폴더를 내려받아 로컬에 설치합니다.

```sh
git clone https://github.com/jungsangU/spec-thread.git
python3 -m pip install ./spec-thread
sdd-core --version
```

관리할 **애플리케이션 프로젝트 루트**에서 사용할 에이전트에 맞는 한 줄을 실행합니다.

```sh
cd /path/to/target-project

# Codex
sdd-core install-skills codex

# Claude Code
sdd-core install-skills claude
```

선택한 에이전트 세션에서 `$sdd-init` 또는 `/sdd-init`으로 시작합니다. 기존 설치를 업데이트할 때는 [버전 동기화](docs/design/version-sync.md)의 미리보기·승인·검증 절차를 따릅니다.

<details>
<summary><strong>대상 프로젝트에는 무엇이 남나요?</strong></summary>

```text
target-project/
├── specs/                    공식 Spec Kit Feature 문서
├── docs/sdd/archive/          폐기 Feature의 보존 산출물
└── .specify/baseline/
    ├── project.md            프로젝트 분석과 범위
    ├── architecture.md       구조와 관계
    ├── decisions.md          판단·승인 근거
    ├── features.yaml         분석 상태·Feature·의존성·아카이브 연결
    ├── source-map.yaml       Feature와 구현 파일 연결
    └── work-items.yaml       요청·Gate·실행 결과 이력
```

프로젝트·설치 스킬의 버전 표식은 [Core 버전 동기화 계약](docs/design/version-sync.md)을 따릅니다.

</details>

## 검증과 운영 기준

- 적용 필수 Gate가 모두 **현재 유효한 PASS**일 때 완료합니다.
- 필수 FAIL / NOT_RUN / UNKNOWN / STALE, 증거 부족은 해당 후속 단계와 완료를 차단합니다.
- 코드·산출물·Gate 정의가 바뀌면 이전 PASS의 유효성을 다시 판단합니다.
- 수정 가능한 오류는 진행 중인 작업에서 재검증하고, 종료 실패의 재시도는 새 UUID로 이전 이력을 연결합니다.
- Commit·Push·Merge·Rollback과 세션 작업 분배는 사용자가 수행합니다. 제품 Git과 대상 프로젝트 Git은 각각 관리합니다.

## 설계와 기능 살펴보기

| 자료 | 읽는 목적 |
| --- | --- |
| [**제품 소개 · HTML**](docs/design/SpecThread-설계-소개.html) | 사용 장면·관계도·설명 이미지로 보는 제품의 역할과 사용 방법 |
| [**전체 기능 목록 · HTML**](docs/design/SpecThread-전체-기능목록.html) | 대기능·소기능·설명·적용 방식·소유·상태별 검색과 비교 |
| [설계와 실행 가이드 · HTML](docs/design/SpecThread-설계와-실행-가이드.html) | 상세 실행 흐름과 사용 예시 |
| [공식 설계 목차](docs/design/README.md) | 아키텍처·데이터 모델·명령·검증·결정 기록으로 이동 |
| [구현·PoC 백로그](docs/design/OPEN-ISSUES.md) | 확인된 범위와 남은 실행·운영 검증 확인 |

HTML은 저장소를 내려받아 브라우저에서 열 수 있습니다. 제품 소개는 사용 예시 선택과 관계도, 인쇄·PDF를 지원합니다.

## 현재 버전과 확인 범위

**Core 0.3.0 · 설계 1.0 · Baseline schema_version 1**

Core CLI 테스트 **37개**와 패키지 업그레이드, 애플리케이션 자료 보존, 문서·HTML 동기화를 검증했습니다. Codex·Claude Code 각각의 공식 스킬 호출을 포함한 실제 프로젝트 종단간 PoC와 GitHub 운영 검증은 [백로그](docs/design/OPEN-ISSUES.md)에서 추적합니다.

AI와 설계 작업을 시작할 때는 [AGENTS.md](AGENTS.md)를 먼저 읽고 [설계 목차](docs/design/README.md)의 순서로 현재 명세와 결정을 확인합니다.
