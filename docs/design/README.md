# SpecThread 설계

2026-11-16 기준. 통합 설계서의 합의와 현행 Core 및 스킬 구현을 함께 읽을 수 있도록 정리했다.

- [설계 철학과 실행 가이드 Markdown](SpecThread-설계와-실행-가이드.md) · [HTML](SpecThread-설계와-실행-가이드.html)
- [통합 상세 설계서](SpecThread-통합-상세-설계서.md)
- [결정 기록](DECISIONS.md) · [검증 및 미결정 백로그](OPEN-ISSUES.md)
- [01 산출물과 데이터 모델](01-artifact-model.md)
- [02 기준 정보와 충돌 정책](02-source-of-truth.md)
- [03 초기 분석과 Discovery](03-analysis-standard.md)
- [04 개발 및 변경의 생명주기](04-artifact-lifecycle.md)
- [05 영향 분석과 위험도](05-impact-analysis.md)
- [06 검증과 정합성](06-verification.md)
- [07 에이전트와 Core의 역할](07-agent-runtime.md)
- [08 명시적 Git 통합](08-git-integration.md)

**설계 정책**은 운영 목표와 합의한 규칙이다. **현행 구현**은 코드가 처리하는 범위다. **실행 검증**은 테스트에서 확인한 동작이며 미결정 및 미확인 사항은 백로그에서 추적한다.


## HTML 동시 갱신

설계 변경 시 상세 문서와 실행 가이드를 함께 갱신한다. HTML은 실행 가이드 Markdown에서 생성한다. 저장소 루트에서 아래 명령으로 생성하고 일치 여부를 확인한다. HTML은 다이어그램을 포함하며 브라우저에서 인터넷 없이 열 수 있다.

```sh
npm install --no-save --package-lock=false marked@17.0.5 @viz-js/viz@3.25.0
node scripts/render-design-guide.mjs
node scripts/render-design-guide.mjs --check
```
