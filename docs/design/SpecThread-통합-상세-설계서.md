# SpecThread 통합 상세 설계서

설계 1.1. 이 파일은 주제별 상세 명세를 연결하는 통합 진입점이다. 상세 규칙을 복사하지 않고 아래 원본 문서를 참조한다. 문서별 책임과 전체 읽기 순서는 [설계 목차](README.md), 실제 사용 예시는 [실행 가이드](SpecThread-설계와-실행-가이드.md)에 있다.

## 1. 목적과 권위

[기준 정보와 충돌 정책](02-source-of-truth.md).

## 2. 구성 및 실행 책임

[전체 아키텍처](architecture.md). 설치·호출 표기는 [에이전트 런타임](07-agent-runtime.md)을 따른다.

## 3. 공식 Spec Kit 기능 대조

[공식 Spec Kit 연동 계약](spec-kit-integration.md).

## 4. Baseline 최소 데이터 계약

[Baseline 데이터 모델](01-artifact-model.md). 등록·병합·분할·아카이브는 [Feature 생명주기](feature-lifecycle.md)에 둔다.

## 5. 명령별 실행

[개발 실행 흐름](04-artifact-lifecycle.md). `sdd-init`은 [초기 분석](03-analysis-standard.md), `sdd-sync`는 [외부 변경 정합화](reconciliation.md)를 따른다. 명령 진입의 버전 검사는 [버전 동기화](version-sync.md)에 있다.

## 6. 상태 전이 및 병렬 실행

[Work Item 상태와 재개](04-artifact-lifecycle.md). 초기 분석 상태는 [Discovery](03-analysis-standard.md), 병렬 운영은 [Git·세션 운영](08-git-integration.md)에서 정의한다.

## 7. 영향 분석과 위험도 게이트

[영향 분석과 위험도](05-impact-analysis.md).

## 8. 검증과 Fingerprint

[필수 Gate와 Fingerprint](06-verification.md).

## 9. 세션과 Git 운영

[Git·세션 운영](08-git-integration.md).

## 10. PoC, 검증 시나리오, MVP 인수 기준

[PoC·MVP 인수 기준](acceptance.md).

## 11. 확정 정책과 구현 전 확인 사항

[검증·미결정 백로그](OPEN-ISSUES.md). 결정 이유·대체 이력은 [DECISIONS](DECISIONS.md)에, 유효한 명세는 각 주제 본문에 둔다. 확정·보류·미결정·PoC 확인을 구분한다.

## 12. 현행 구현과 확인 범위

[현재 확인 범위](OPEN-ISSUES.md).
