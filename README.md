# SpecThread

<div align="center">

### AI 개발의 의도, 변경, 검증을 프로젝트에 남깁니다.

공식 **GitHub Spec Kit**와 함께 사용하는 개발 하네스.<br>
**Codex · Claude Code**의 개발 흐름에 기능 추적과 검증 기준을 연결합니다.

![Core 0.6.0](https://img.shields.io/badge/Core-0.6.0-b75d43?style=flat-square)
![Design 2.0](https://img.shields.io/badge/Design-2.0-7b7265?style=flat-square)
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
| **위험도에 비례한 개발** | Lightweight·Standard·Strict로 필요한 절차를 선택하고, 기존 검사와 유효한 결과를 재사용합니다. [정책](docs/design/verification-profiles.md) |
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

질문은 필요한 내용 하나씩 받고, 단계가 끝나면 구체적인 다음 작업을 제안합니다. 사용자는 “진행해”라고 답해 이어갈 수 있습니다. [대화형 진행](docs/design/conversation-flow.md)의 안내 방식과 기존 Gate를 함께 따릅니다.

## 세 가지 작업 흐름

| 작업 | Codex | Claude Code | 결과 |
| --- | --- | --- | --- |
| **프로젝트 시작** | `$sdd-init` | `/sdd-init` | 전체 범위 조사, 기능 후보·명세·계획, Discovery 근거와 Baseline |
| **개발 요청** | `$sdd-develop` | `/sdd-develop` | 요청별 Work Item, 공식 개발 산출물, 영향 판정과 필수 검증 결과 |
| **외부 변경 정합화** | `$sdd-sync` | `/sdd-sync` | 차이 조사, 사용자 승인 변경안, 관련 자료 정합성과 재검증 |

한 프로젝트에서 **Codex 또는 Claude Code 한 종류**를 선택합니다. Skill은 의미와 근거를 분석하고, Core는 저장된 계약과 완료 조건을 검사합니다.

## 설치와 업데이트

사용할 배포본을 직접 내려받고, **그 배포 폴더에서** 아래 명령 하나를 실행합니다. 대상 앱 폴더와 에이전트는 화면에서 선택합니다.

```sh
# 신규 설치
python3 specthread install

# 내려받은 새 배포본으로 업데이트
python3 specthread update
```

Python 3.11 이상과 사용할 AI 앱을 준비하면 됩니다. Spec Kit·SpecThread Skill 준비와 버전·구조 검사는 내부에서 처리합니다. 전역 specify/sdd-core 설치, 가상환경 활성화, JSON 계획 작성은 필요하지 않습니다. 기존 앱의 업데이트 검사는 처음 한 번 등록하고 재사용합니다.

[설치 가이드](docs/SpecThread-설치-매뉴얼.md)에서 두 명령의 화면 흐름과 중단 시 처리 방법을 확인하세요. 설치 후 앱 프로젝트의 새 AI 세션에서 Codex는 `$sdd-init`, Claude Code는 `/sdd-init`으로 분석을 시작합니다.

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

## 제품 구현 완료 기준

설계 기반 구현 요청은 [구현 → 테스트 → 설계 대조 → 누락 보완](docs/design/implementation-standard.md)을 반복하고 실제 근거로 완료를 판단합니다. 최근 결과는 [2차 효율화 구현·검증](docs/validation/scoped-development-review.md)에 있습니다.

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
| [공식 설계 목차](docs/design/README.md) | 주제별 원본·문서 책임·읽기 순서와 결정 기록으로 이동 |
| [구현·PoC 백로그](docs/design/OPEN-ISSUES.md) | 확인된 범위와 남은 실행·운영 검증 확인 |

HTML은 저장소를 내려받아 브라우저에서 열 수 있습니다. 제품 소개는 사용 예시 선택과 관계도, 인쇄·PDF를 지원합니다.

## 현재 버전과 확인 범위

**Core 0.6.0 · 설계 2.0 · Baseline schema_version 1**

Core **134개 통과**, Monitor **28개 통과·Windows 전용1개 생략**, 문서 예시 **13개 통과**입니다. 실제 네이티브 인수 제한과 전체 추적은 [병렬 개발 검증](docs/validation/parallel-development-review.md)에 기록합니다. [설계 1.1 검증](docs/validation/risk-profiles-1.1-review.md)에는 공식 Spec Kit 1.4.0의 양쪽 설치·업데이트, 실제 0.4→0.5 변환과 동일 요청 Core 비교 실측을 담았습니다. Codex·Claude Code의 실제 공식 Skill 호출을 포함한 종단간 PoC·토큰 측정과 Windows 네이티브 검증은 [백로그](docs/design/OPEN-ISSUES.md)에서 추적합니다.

AI와 설계 작업을 시작할 때는 [AGENTS.md](AGENTS.md)를 먼저 읽고 [설계 목차](docs/design/README.md)의 순서로 현재 명세와 결정을 확인합니다.

## 선택 기능

[SpecThread Monitor](monitor/README.md)는 지정한 Worktree의 작업, Gate, 산출물과 연결한 에이전트 이벤트를 로컬에서 관측합니다.

설계 1.2의 대상 중심 분석·최소 충분 테스트·변경분 정합성·문서 최소 수정과 실제 검증 한계는 [2차 효율화 검증](docs/validation/scoped-development-review.md)을 참고하세요.

### 독립 개발과 순차 반영

설계 2.0은 Direct의 관리정보 동시 저장을 보호하고, 선택한 Isolated 모드에서 Work Item별 사본·로컬 FIFO·검증·저널 반영을 지원합니다. 동일 세션의 실제 도구·권한·Hook 확인이 필요합니다. [상세 설계](docs/design/parallel-development.md)와 [실제 검증·남은 제약](docs/validation/parallel-development-review.md)을 확인하세요.
