# 반품 판정 후 재고반영/일마감 흐름 계획

> ✅ 대체 완료: 이 영역의 재고반영 정책은 SPEC-004에서 A안으로 확정됐다(2026-06-22). 본 내용은 SPEC-004로 대체된다.

## 1. 문서 목적

이 문서는 반품처리 작업에서 판정이 완료된 뒤 재고를 언제, 어떤 기준으로 반영할지 정리한다. 목표는 판정 저장 즉시 재고를 움직여 생기는 오류를 막고, 일마감/수량확인/재고 이벤트 생성의 1차 기준을 고정하는 것이다.

이번 문서는 설계 기준만 정리하며 backend, frontend, DB, migration은 변경하지 않는다.

## 2. 현재 완료된 반품처리 흐름

현재 반품처리 1차 흐름은 다음 단계까지 완료되어 있다.

1. 반품 접수 batch 생성
2. 반품 접수 row 저장
3. 접수 row 검증
4. 검증된 row를 `READY_FOR_PROCESSING` 처리 대상으로 전환
5. 운송장 스캔으로 처리 대상 조회
6. 상품 바코드 확인
7. 판정 저장
8. 판정 결과를 그리드와 상세 패널에 즉시 반영
9. 추적 대상 판정의 `return_management_no`, `return_label_no` 생성
10. 사진/증빙 선택 첨부
11. Local Agent 미연결/라벨 출력 placeholder 표시

현재 `return_intake_rows`에는 판정/라벨/첨부 흐름을 위한 필드는 있으나, 재고반영 완료 여부와 재고 이벤트 연결 필드는 아직 없다.

## 3. 1차 재고반영 원칙

- 판정 저장 즉시 재고반영하지 않는다.
- 판정 완료 row는 일마감 후보가 된다.
- 관리자 또는 마감 작업자가 수량과 대상을 확인한 뒤 마감 확정한다.
- 마감 확정 시 재고 이벤트를 생성한다.
- 재고 이벤트 생성 후 `current_inventory`를 반영한다.
- 이미 재고반영된 row는 재반영을 차단한다.
- 실패/중복/스킵 결과는 summary로 명확히 반환한다.

## 4. 판정별 1차 처리 정책

`GOOD`

- 정상재고 입고 후보다.
- 고객사 기본 반품/입고 창고 또는 `client_warehouse_settings` 기준 창고로 입고 후보가 된다.
- 일마감 확정 후 정상재고 수량을 증가시킨다.

`REFURB`

- 정상재고가 아니다.
- 리퍼/보류성 재고 또는 외부반출 대상 후보다.
- 1차에서는 재고 증가보다 추적 대상/후속 처리로 둔다.

`SAMPLE`

- 정상재고가 아니다.
- 샘플 추적 대상이다.
- 후속 외부반출/보관 흐름 후보로 둔다.

`MANUFACTURER_RETURN`

- 정상재고가 아니다.
- 제조사반품 외부반출 대상이다.
- `return_management_no` 또는 `return_label_no` 기준 추적이 필요하다.

`DISPOSAL`

- 정상재고가 아니다.
- 폐기 대상이다.
- 1차에서는 재고 증가 없음으로 처리한다.
- 폐기 확정과 이력 관리는 후속 후보로 둔다.

`HOLD`

- 정상재고가 아니다.
- 보류 대상이다.
- 고객사 확인 후 재판정 또는 후속 처리 후보로 둔다.

## 5. 일마감 후보 조회 기준

후속 구현 API 후보는 다음과 같다.

- `GET /api/returns/closing/candidates`
- `POST /api/returns/closing/confirm`

후보 조회 조건은 다음을 기준으로 한다.

- `return_intake_rows.status = COMPLETED`
- `judgement_status`가 존재해야 한다.
- `inventory_reflected_yn = false` 또는 동등한 미반영 필드가 필요하다.
- `client_id` 필터를 지원한다.
- 날짜 필터를 지원한다.
- `judgement_status` 필터를 지원한다.

이번 문서에서는 API를 구현하지 않는다.

## 6. 필요한 최소 DB 후보

후속 구현에서 현재 모델에 추가가 필요한 후보는 다음과 같다.

`return_intake_rows` 후보:

- `inventory_reflected_yn`
- `inventory_reflected_at`
- `inventory_event_id`
- `closing_batch_id` 또는 `return_closing_id`

현재 재고 모델은 이미 다음 테이블이 존재한다.

- `inventory_events`
- `current_inventory`

따라서 다음 구현에서는 새 재고 원장을 먼저 만들기보다 기존 `inventory_events`, `current_inventory`를 활용할 수 있는지 확인한다.

## 7. 재고 이벤트 방향

재고 이벤트는 반드시 추적 가능해야 한다.

후보 필드:

- `event_id`
- `client_id`
- `product_id` 또는 `product_code`
- `warehouse_id`
- `qty`
- `event_type`
- `source_type`
- `source_id`
- `judgement_status`
- `created_at`
- `created_by`

현재 `inventory_events`에는 `event_no`, `client_id`, `warehouse_id`, `product_id`, `product_code`, `stock_status`, `event_type`, `qty_delta`, `source_type`, `source_id`, `source_line_id`, `idempotency_key`, `created_by`, `raw_json` 등이 있다.

event_type 후보:

- `RETURN_GOOD_IN`
- `RETURN_DISPOSAL`
- `RETURN_HOLD`
- `RETURN_MANUFACTURER_OUTBOUND_PENDING`
- `RETURN_REFURB_PENDING`
- `RETURN_SAMPLE_PENDING`

1차 구현은 `GOOD` 판정의 정상재고 입고 이벤트부터 시작하는 것을 추천한다. 다른 판정은 조회와 추적 대상으로 표시하되 재고 증가를 만들지 않는다.

## 8. 창고 결정 기준

`GOOD` 재고반영 시 창고 결정 우선순위는 다음을 추천한다.

1. 고객사별 반품/양품/입고 용도 기본 창고 설정
2. 없으면 고객사 기본 입고 창고
3. 없으면 재고반영 차단 및 창고 설정 필요 오류 반환

현재 `warehouses`는 전역 창고 마스터이고, 고객사별 사용 창고/기본 창고는 `client_warehouse_settings`가 담당한다. 실제 `usage_type` 값은 후속 구현에서 현재 코드의 allowlist와 맞춰 결정한다.

## 9. 중복 반영 방지

- row 단위로 재고반영 여부를 관리한다.
- 같은 row에서 재고 이벤트를 중복 생성하지 않는다.
- 마감 API 재호출 시 이미 반영된 row는 `skipped`로 집계한다.
- `inventory_events.idempotency_key`를 활용해 이벤트 중복 생성을 추가로 막는다.
- 장애 또는 일부 실패가 발생하면 `applied_rows`, `skipped_rows`, `failed_rows` 같은 partial result를 명확히 반환한다.

## 10. 1차 skeleton 구현 범위 제안

다음 목표추진 작업 범위는 다음을 추천한다.

1. `return_intake_rows`에 재고반영 관련 최소 필드를 추가한다.
2. 기존 `inventory_events`, `current_inventory` 활용 가능성을 우선 확인한다.
3. `GET /api/returns/closing/candidates`를 추가한다.
4. `POST /api/returns/closing/confirm`을 추가한다.
5. `GOOD` 판정 row만 정상재고 증가 처리한다.
6. `REFURB`, `SAMPLE`, `MANUFACTURER_RETURN`, `DISPOSAL`, `HOLD`는 후보로 조회하되 재고증가 없음 또는 후속 처리로 표시한다.
7. `/returns/closing` 화면 skeleton을 추가한다.
8. `SmartDataGrid`로 마감 후보를 표시한다.
9. 마감 확정 버튼과 결과 summary를 제공한다.

## 11. 이번에 구현하지 않을 것

- 외부반출
- 리퍼 세분화
- 제조사반품 출고검수
- 폐기 확정
- 정산
- Ecount ERP API 연동
- 복잡한 location/bin 재고
- 실사/재고조정
- 판정별 장기 재고 정책 고도화

## 12. Closeout 결론

다음 작업은 목표추진 모드로 반품 일마감/재고반영 skeleton 구현을 진행하는 것을 추천한다.

1차 구현은 `GOOD` 판정 정상재고 반영부터 시작한다. 다른 판정은 정상재고로 바로 넣지 않고 추적/후속 처리 대상으로 남긴다. 재고반영은 판정 저장 시점이 아니라 일마감 확정 시점에 수행하며, row 단위 중복 반영 방지와 재고 이벤트 추적성을 반드시 포함해야 한다.
