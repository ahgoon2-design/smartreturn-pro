# SmartReturn Pro 스캔/Local Agent/재고 정책

이 문서는 SmartReturn Pro 신규 제작 기준이다. 기존 SmartReturn의 구현기록, 스캔 처리, Local Agent 동작, 재고 반영 방식을 그대로 따르지 않는다.

## ProductScanMatchService 매칭 순서

1. `products.product_code`
2. `products.barcode`
3. `product_barcodes.barcode`
4. `NOT_FOUND`

## 매칭 원칙

- 모든 매칭은 `client_id` 범위 안에서만 한다.
- `warehouse_id`가 필요한 업무에서는 창고 scope도 함께 적용한다.
- 매칭 실패는 업무 저장 실패가 아니라 `NOT_FOUND` 결과로 기록한다.
- 동일 바코드가 여러 후보를 만들 수 있으면 후보 목록과 판정 기준을 분리한다.

## 스캔 이벤트와 재고 이벤트

- `scan_events`는 스캔 이벤트 로그다.
- `inventory_events`는 재고 이벤트 원장이다.
- 스캔 성공이 곧 재고 반영을 의미하지 않는다.
- 재고 반영은 서버 업무 확정 흐름에서만 발생한다.
- 로컬 클라이언트는 재고를 직접 변경하지 않는다.

## Local Agent 역할

- Local Agent는 사운드, 라벨, 프린터, 장치 제어를 담당한다.
- Local Agent 실패가 업무 저장 실패가 되면 안 된다.
- Local Agent 연결상태, 처리모드, 프린터, 사운드 상태는 화면에 표시한다.
- Local Agent 자동 업데이트와 원격 설정 강제 변경은 초기 제외 범위다.

## 재고 반영 원칙

- 재고 반영은 서버 업무 확정 흐름에서만 발생한다.
- `inventory_events` 없이 `current_inventory`를 직접 수정하지 않는다.
- 재고 반영 실패는 업무 확정 결과와 명확히 연결해 추적한다.
- 취소나 반전은 원본 이벤트 삭제가 아니라 반전 이벤트로 처리한다.

## 수량검수 `purpose_code`

- `PRE_STOCK_APPLY`만 재고 반영 가능하다.
- `POST_STOCK_AUDIT`는 재고 반영 금지다.
- `RETURN_CONFIRMATION_CHECK`는 재고 반영 금지다.
- `MANUAL_STOCK_COUNT`는 재고 반영 금지다.

## Codex 구현 전 체크

- `ProductScanMatchService` 매칭 순서를 지켰는가?
- 모든 매칭이 `client_id` 범위 안에서 수행되는가?
- `scan_events`를 재고 원장처럼 사용하지 않았는가?
- Local Agent 실패가 업무 저장 실패가 되지 않는가?
- 화면에 Local Agent 연결상태/처리모드/프린터/사운드 상태가 표시되는가?
- 로컬 클라이언트가 재고를 직접 변경하지 않는가?
- `purpose_code`별 재고 반영 가능 여부를 지켰는가?
