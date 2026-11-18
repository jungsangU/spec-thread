# SpecThread 설계 1.0

2026-11-17 확정 설계. 초기 설계 0.1에서 발전한 첫 정식 기준이며 Core 배포 패키지 버전과 독립적이다. [설계 릴리즈 노트](../../CHANGELOG.md)

- [설계 철학과 실행 가이드 Markdown](SpecThread-설계와-실행-가이드.md) · [HTML](SpecThread-설계와-실행-가이드.html)
- [전체 기능 목록표 HTML](SpecThread-전체-기능목록.html) · 대기능·소기능·상세 설명·소유·상태별 탐색
- [전체 아키텍처](architecture.md) · [설치와 사용자 책임](../SpecThread-설치-매뉴얼.md) · [Core 버전 동기화](version-sync.md)
- [통합 상세 설계서](SpecThread-통합-상세-설계서.md)
- [결정 기록](DECISIONS.md) · [검증 및 미결정 백로그](OPEN-ISSUES.md)
- [01 산출물과 데이터 모델](01-artifact-model.md)
- [02 기준 정보와 충돌 정책](02-source-of-truth.md)
- [03 초기 분석과 Discovery](03-analysis-standard.md)
- [04 개발 및 변경의 생명주기](04-artifact-lifecycle.md)
- [05 영향 분석과 위험도](05-impact-analysis.md)
- [06 검증과 정합성](06-verification.md)
- [07 에이전트와 Core의 역할](07-agent-runtime.md)
- [08 두 Git 저장소의 운영](08-git-integration.md)

**설계 정책**은 운영 목표와 합의한 규칙이다. **현행 구현**은 코드가 처리하는 범위다. **실행 검증**은 테스트에서 확인한 동작이며 미결정 및 미확인 사항은 백로그에서 추적한다.


## 새 세션 읽기 순서

[공통 지침](../../AGENTS.md) → 아키텍처 → 통합 상세 설계서 → 버전 동기화와 Git 운영 → 결정 이력과 미결정 항목 순서로 읽는다. 각 주제 문서가 스키마와 세부 운영 기준을 보충한다. 실행 가이드와 HTML은 탐색용으로 사용한다.

후속 설계 논의는 [미결정 백로그](OPEN-ISSUES.md)의 `결정 필요` 항목에서 시작한다. 이미 확정된 정책의 구현·실행 검증과 명시적 제외 사항은 [결정 기록](DECISIONS.md)과 함께 확인한다.

## HTML 동시 갱신

설계 변경 시 상세 문서와 실행 가이드를 함께 갱신한다. HTML은 실행 가이드 Markdown에서 생성한다. 저장소 루트에서 아래 명령으로 생성하고 일치 여부를 확인한다. HTML은 다이어그램을 포함하며 브라우저에서 인터넷 없이 열 수 있다.

```sh
npm install --no-save --package-lock=false marked@17.0.5 @viz-js/viz@3.25.0
node scripts/render-design-guide.mjs
node scripts/render-design-guide.mjs --check
```
