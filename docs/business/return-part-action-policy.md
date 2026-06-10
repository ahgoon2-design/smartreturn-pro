# 부품적출/부품교체/폐기 처리 정책

부품적출은 폐기 메모가 아니라 폐기 전 재사용 가능한 부품을 분리하는 작업이다. 다만 모든 부품을 무조건 재고화하지 않는다. 현장 부담을 줄이기 위해 처리 등급을 나눈다.

## 기본 원칙

- 부품적출/부품교체는 처음부터 완전한 재고관리로 과대 설계하지 않는다.
- 1차는 `MEMO_ONLY` 이력 중심으로 설계한다.
- 고객사 요청, 고가, 청구, 분쟁 가능 부품만 재고관리로 확장한다.
- 폐기 확정 전 적출 가능한 부품이 있으면 작업자가 확인할 수 있어야 한다.

## 3단계 정책

### 1. 기록 생략 가능

- 소모품.
- 포장재.
- 작은 현장 보정.
- 고객사/청구/분쟁 영향이 없는 단순 처리.

### 2. MEMO_ONLY

- 뚜껑 교체.
- 패킹 교체.
- 소량 구성품 보충.
- 재고는 움직이지 않고 작업 이력만 남김.

### 3. 재고 반영

- 고가 부품.
- 청구 대상.
- 분쟁 가능 부품.
- 고객사 요청 부품.
- 별도 부품재고로 관리해야 하는 품목.

## 부품 처리 action 후보

```text
PART_HARVEST
PART_REPLACE_OUTBOUND
PART_USED_FROM_DISPOSAL
PART_USED_FROM_NEW_PRODUCT
PART_USED_FROM_REFURB
PART_USED_FROM_SAMPLE
COMPONENT_SUPPLEMENT
GIFT_ADDED
SET_REBUILD
```

작업자 화면에는 위 값을 그대로 표시하지 않는다. 예를 들어 `PART_HARVEST`는 “부품적출”, `COMPONENT_SUPPLEMENT`는 “구성품 보충”으로 표시한다.

## inventory_effect 후보

```text
NONE
MEMO_ONLY
STOCK_INCREASE
STOCK_DECREASE
STOCK_MOVE
```

- `NONE`: 시스템 재고/이력에 남기지 않는 현장 보정.
- `MEMO_ONLY`: 작업 이력만 남기고 재고 원장은 변경하지 않음.
- `STOCK_INCREASE`: 적출 부품 재고 증가.
- `STOCK_DECREASE`: 부품 사용 또는 교체 출고로 재고 감소.
- `STOCK_MOVE`: 창고/상태 이동.

## 부품적출 흐름

```text
폐기/부품적출 대상
→ 적출 가능한 부품 확인
→ 처리 등급 결정
→ MEMO_ONLY 또는 재고 반영 선택
→ 적출 부품 창고 확정
→ 적출 부품 재고반영 또는 이력 저장
→ 잔여품 폐기 확정
```

## 기록 기준

재고 반영 또는 MEMO_ONLY 이력이 필요한 경우 최소 아래 기준을 남긴다.

```text
agency_id
client_id
client_unit_id
source_product_id
extracted_product_id
warehouse_id
quantity
condition_status
inventory_effect
worker
timestamp
memo/photo
```

## Codex 구현 전 체크

- 부품적출을 폐기 메모 하나로만 처리하고 있지 않은가?
- 모든 작은 부품을 강제로 재고화해 현장 부담을 키우지 않는가?
- MEMO_ONLY와 재고 반영 대상을 구분하는가?
- 재고 반영이 필요한 경우 `warehouse_id`와 `inventory_events` 흐름을 유지하는가?
- 작업자 화면에 내부 action enum을 그대로 노출하지 않는가?
