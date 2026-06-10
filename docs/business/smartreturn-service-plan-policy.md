# Basic / Pro / Ultra 서비스 플랜 정책

이 문서는 SmartReturn Pro 플랜 정책 기준이다. 플랜은 데이터 계층을 바꾸지 않고 기능 사용 범위, 화면 잠금, 정산 항목, AI 보조 수준을 제어한다.

## 플랜과 데이터 계층

SmartReturn Pro의 기본 계층은 플랜과 무관하게 고정이다.

```text
platform_owner
→ agency_id
→ client_id
→ client_unit_id
→ warehouse_id
```

Basic, Pro, Ultra 플랜이 달라져도 `agency_id`, `client_id`, `client_unit_id`, `warehouse_id` 구조는 변하지 않는다. 고객사별 DB 분리 방향으로 설계하지 않는다.

## 플랜 부여 방식

권장 구조는 다음과 같다.

```text
agency 기본 플랜
+ client별 override 가능
```

예시:

```text
A CJ대리점 기본 플랜: Pro
ESP마케팅: Ultra override
소형셀러B: Basic override
```

client별 override는 대리점 기본 계약과 다르게 특정 업체만 상위 기능을 쓰거나 하위 기능만 쓰는 상황을 지원한다.

## Basic

Basic은 단순 반품 입고/처리 중심 플랜이다.

- 개봉/미개봉 중심 처리.
- 기본 사진/메모 선택.
- 기본 처리완료.
- 단순 일마감.
- 상세 리퍼등급, 부품적출, 세트구성품, 크리닝, 재포장 기능은 locked.

## Pro

Pro는 상세 검수/판정형 반품처리 플랜이다.

- 양품, 리퍼, 샘플, 폐기, 제조사반출, 보류, 사고처리 가능.
- 사진/메모/라벨/반품관리번호.
- 일마감 수량대조.
- 외부반출 검수.
- 고객사별 판정 기준표.
- Smart Import Mapper 고급 검증.
- 스캔 처리와 그리드 선택 처리 모두 지원.

## Ultra

Ultra는 동현형 프리미엄 반품운영 플랜이다.

- 크리닝.
- 재포장.
- 부품적출.
- 부품교체 출고.
- 이커머스 세트/구성품/사은품/합포장 관리.
- 세트 재구성.
- 고급 판정 추천.
- 정산 세분화.
- 작업 이력/사진/증빙 강화.

## Locked/disabled 업셀 UX

플랜 미포함 기능은 완전히 숨기지 않는다. 상위 플랜 기능은 locked/disabled 상태로 보여준다. 사용자가 상위 기능 존재를 알 수 있어야 한다.

단, 실제 실행은 frontend 메뉴 숨김이나 disabled만 믿지 않고 backend feature gate로 반드시 차단한다.

예시:

```text
리퍼 Pro
샘플 Pro
폐기 Pro
제조사반출 Pro
부품적출 Ultra
크리닝 Ultra
재포장 Ultra
세트/구성품 Ultra
AI 고급 추천 Ultra
```

화면 표현은 자물쇠 아이콘이나 “상위 플랜 기능” 배지를 사용할 수 있다. 작업자 화면에서는 업셀 문구가 작업을 방해하지 않게 작고 명확하게 표시한다.

## 기능 gate 기준

- 화면 표시 gate: 사용자가 기능 존재를 이해하도록 locked/disabled로 표시한다.
- API 실행 gate: backend가 현재 사용자, agency, client, plan을 기준으로 실행 가능 여부를 재검증한다.
- 정산 gate: 플랜에 따라 청구 항목, 단가, 무료 포함량, 초과 과금 항목을 다르게 산출할 수 있다.
- AI 보조 gate: Basic은 체크리스트 중심, Pro는 고객사 판정표 기반 추천, Ultra는 과거 이력/고급 추천을 확장할 수 있다.

## Codex 구현 전 체크

- 플랜 때문에 데이터 계층을 바꾸고 있지 않은가?
- 상위 기능을 완전히 숨겨 사용자가 존재를 모르게 만들지 않았는가?
- locked/disabled UI만으로 실행 차단을 끝내지 않았는가?
- backend feature gate가 agency/client scope와 함께 적용되는가?
- 작업자 화면에서 업셀 안내가 핵심 작업을 밀어내지 않는가?
