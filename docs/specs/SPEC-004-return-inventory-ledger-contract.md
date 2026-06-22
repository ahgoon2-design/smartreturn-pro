# 슬라이스 스펙: 반품 확정 후 재고 원장/재고반영 계약

## 0. 근거와 범위

- SPEC 번호: `SPEC-004`
- 근거 문서: `docs/reports/return-writeflow-tenancy-audit.md`
- 번호 확인: 기존 `docs/specs` 최대 번호는 `SPEC-003`이며, 이 문서는 다음 신규 번호 `SPEC-004`로 작성한다.
- 이 SPEC은 반품처리 모듈의 확정 이후 재고 원장(`inventory_events`)과 현재고(`current_inventory`) 반영 계약만 정의한다.
- **작성 상태: 폐기·제조사반품 재고반영 정책은 A안으로 확정됐다(2026-06-22 사용자 결정).** 이 문서는 A안 확정을 반영한 계약 문서다. 구현은 별도 게이트에서 진행한다.
- UX/Help, 화면 문구 보강, 반품 외 모듈 deny-by-default/RLS/중앙화 격리 구조는 제외한다. 반품 외 모듈 격리 구조는 별도 구조 SPEC으로 보류한다.
- 코드/API/DB/schema/migration 구현은 이 문서 작성 범위가 아니다. 구현은 사용자 승인 후 별도 게이트에서 진행한다.

## 1. 한 줄 목적

반품 판정 이후 일마감, 외부반출, 폐기 확정 단계에서 재고 원장과 현재고가 중복 없이, 고객사/대리점/운영단위/창고 스코프를 지키며 반영되도록 **계약을 확정한다**. (A안: 일마감 양수 반영 → 확정 시 음수 차감)

## 2. 사용자 / 권한 scope

- 누가 쓰나(role):
  - 일마감/재고반영: 내부 운영자 `SUPER_ADMIN`, `INTERNAL_ADMIN`, `INTERNAL_WORKER`, `AGENCY_ADMIN` 중 `RETURN_CLOSE` 권한 보유자.
  - 외부반출/폐기 확정: 내부 운영자 `SUPER_ADMIN`, `INTERNAL_ADMIN`, `INTERNAL_WORKER`, `AGENCY_ADMIN` 중 `RETURN_OUTBOUND` 권한 보유자.
  - 독립 재고반영 API는 후속 SPEC에서 결정한다. 이번 구현 범위 밖이다.
- scope:
  - `agency_id`: 모든 재고 원장/현재고/반품 row에서 필수 스코프다.
  - `client_id`: 모든 반품 쓰기 API와 재고 이벤트에서 필수 스코프다.
  - `client_unit_id`: 반품 row의 운영단위 추적값이다. 재고 원장/현재고 모델에 직접 컬럼이 없더라도, 이벤트 생성 전 row의 운영단위가 같은 고객사에 속하는지 backend에서 재검증해야 한다.
  - `warehouse_id`: 재고를 바꾸는 이벤트에는 필수다. 창고가 확정되지 않은 row는 재고 원장 생성과 현재고 반영을 차단한다.
- 내부 / 포털 구분:
  - 내부 운영 화면 전용이다.
  - 고객사 포털 사용자는 일마감, 외부반출 확정, 폐기 확정, 독립 재고반영 액션을 실행할 수 없다.
- 프론트가 보낸 `client_id`, `client_unit_id`, `warehouse_id`는 신뢰하지 않는다. backend는 인증 컨텍스트와 row/batch의 실제 소유 범위를 기준으로 다시 검증한다.

## 3. 확정 단계별 재고 원장 계약

### 3.1 판정/처리완료

- 판정 저장과 처리완료 시점에는 `inventory_events`를 생성하지 않는다.
- 판정 저장과 처리완료 시점에는 `current_inventory`를 변경하지 않는다.
- 근거: 기존 검수 보고서에서 판정/처리완료 시점의 `current_inventory` 변경 또는 `inventory_events` 생성은 발견하지 못했다.
- 처리완료는 재고반영이 아니라 후속 확정 단계로 넘길 준비 상태다.

### 3.2 일마감 confirm

- `POST /api/returns/closing/confirm`은 1차 재고반영 트리거다.
- 일마감 confirm은 재고반영 대상 row에 대해 양수 `inventory_events`를 생성하고 같은 transaction 안에서 `current_inventory`를 증가시킨다.
- `inventory_events`는 재고 원장이고, `current_inventory`는 원장 반영 결과 요약이다. `current_inventory`만 단독으로 바꾸면 안 된다.
- 이미 반영된 row는 `inventory_reflected_yn`, 기존 이벤트 조회, `InventoryEvent.idempotency_key`로 중복 반영을 차단한다.
- 창고, 상품, 수량, 고객사 스코프가 확정되지 않은 row는 재고반영하지 않고 실패/확인필요로 남긴다.

**A안 확정 (2026-06-22):**

- 폐기(`DISPOSAL`)·제조사반품(`MANUFACTURER_RETURN`) 판정 row는 일마감에서 **처분대기 재고**로 양수(+) 반영한다.
- 처분대기 재고는 `stock_status`로 구분하며, 판매가능 정상재고(`GOOD`)와 별도 재고 행으로 분리된다.
- **★같은 row는 일마감 양수 반영 1회 + 확정 차감 1회만 허용한다.** 중복 방지는 `idempotency_key` 강제로 보장한다.
- 처분대기 입고·보관·폐기·제조사반품·외부반출 이력은 정산에서 분리 집계 가능해야 한다.
- 처분대기 재고는 별도 상태/창고/grade 기준으로 추적한다.

### 3.3 외부반출 확정 후 재고 정책

- 외부반출 확정은 제조사반품, 외부 회수, 공급처 반송처럼 창고 재고에서 빠져나가는 확정 단계다.

**A안 확정 (2026-06-22):**

- 일마감에서 이미 양수 반영된 row만 외부반출 확정 시 음수 `inventory_events`를 생성하고 같은 transaction 안에서 `current_inventory`를 감소시킨다.
- 음수 이벤트의 `stock_status`는 기존 양수 반영 이벤트의 `stock_status`를 따른다. 임의로 `GOOD` 또는 다른 등급으로 바꾸지 않는다.
- 재고 미반영 row(일마감 양수 반영이 없는 row)의 외부반출 확정은 차단하거나 확인필요로 분리한다.
- 외부반출 음수 이벤트의 idempotency key는 row 단위로 결정 가능해야 한다. 예: `return-external-outbound:{row_id}:{stock_status}`.

### 3.4 폐기 확정 후 재고 정책

- 폐기 확정은 재고로 보관 중이던 처분대기품을 폐기 처리해 창고 재고에서 제거하는 확정 단계다.

**A안 확정 (2026-06-22):**

- 일마감에서 이미 양수 반영된 row만 폐기 확정 시 음수 `inventory_events`를 생성하고 같은 transaction 안에서 `current_inventory`를 감소시킨다.
- 음수 이벤트의 `stock_status`는 기존 양수 반영 이벤트의 `stock_status`를 따른다.
- 재고 미반영 row의 폐기 확정은 차단하거나 확인필요로 분리한다.
- 폐기 확정은 사유, 메모, 확정자, 확정시각 같은 업무 증빙을 남긴다.
- 폐기 음수 이벤트의 idempotency key는 row 단위로 결정 가능해야 한다. 예: `return-disposal:{row_id}:{stock_status}`.

### 3.5 일마감 confirm과 독립 재고반영 API

- 일마감 confirm이 1차 재고반영 API다.
- 별도 독립 재고반영 API는 일반 사용자가 임의 row를 골라 재고를 바꾸는 액션으로 만들면 안 된다.
- 독립 재고반영 API가 필요하다면 목적은 재처리, 장애 복구, 원장/현재고 정합성 보정으로 한정한다.
- 독립 재고반영 API를 만들 경우에도 같은 idempotency key, 같은 scope 검증, 같은 transaction 계약을 사용해야 한다.

**확정 (2026-06-22): 독립 재고반영 API는 이번 구현 범위에 포함하지 않는다.** 일마감 confirm 안정화 후 재처리/복구 전용 후속 SPEC으로 분리한다.

## 4. 재사용할 기존 자산

- 검수 보고서: `docs/reports/return-writeflow-tenancy-audit.md`
- route/API:
  - `POST /api/returns/closing/confirm`
  - `POST /api/returns/external-outbound/confirm`
  - `POST /api/returns/disposal/tasks/{task_id}/confirm`
- 기존 service 근거:
  - 일마감 confirm은 `backend/app/services/return_intake_service.py:1589`, `:1729`, `:1759`, `:1760`에서 재고 이벤트와 현재고 증가를 수행하는 것으로 검수됐다.
  - 외부반출 confirm은 `backend/app/services/return_intake_service.py:1850`, `:1954`, `:1975`, `:1991`에서 상태와 batch를 저장하지만 재고 이벤트는 발견되지 않았다.
  - 폐기 confirm은 `backend/app/services/return_intake_service.py:2285`, `:2305`, `:2316`에서 폐기 상태를 저장하지만 재고 이벤트는 발견되지 않았다.
- 기존 모델 근거:
  - `InventoryEvent`: `agency_id`, `client_id`, `warehouse_id`, `stock_status`, `idempotency_key`를 가진 재고 원장.
  - `CurrentInventory`: `client_id`, `warehouse_id`, `location_id`, `product_id`, `stock_status` 단위 현재고 요약.
  - `ReturnIntakeRow`: 반품 처리 row, `agency_id`, `client_id`, `client_unit_id`, 판정/창고/후속 상태 보유.
  - `ReturnExternalOutboundBatch`: 현재 `client_id` nullable 구조라 batch 테넌시 계약 보강이 필요하다 — 신규 batch는 단일 `client_id` 필수(non-nullable 권장, migration은 별도 DB SPEC).

## 5. 있어야 할 것 / 절대 없어야 할 것

### 있어야 할 것

- `inventory_events`와 `current_inventory`는 항상 같은 transaction 안에서 함께 처리한다.
- 재고가 증가하거나 감소하는 모든 확정 액션은 원장 이벤트를 먼저 만들고 현재고를 갱신한다.
- 같은 row, 같은 확정 타입, 같은 `stock_status`는 한 번만 재고에 반영된다.
- 중복 요청은 성공/skip 결과를 명확히 돌려주되, 재고 수량을 두 번 바꾸지 않는다.
- **A안 정책: 외부반출/폐기 확정은 일마감 양수 반영 이력이 있는 row만 재고 차감 대상으로 삼는다.**
- **재고 미반영 row(일마감 양수 반영 없는 row)의 외부반출/폐기 확정은 차단하거나 확인필요로 분리한다.**
- 재고반영 이벤트 생성 전 backend는 `agency_id`, `client_id`, `client_unit_id`, `warehouse_id`를 재검증한다.
- `warehouse_id`가 확정되지 않았거나 기존 재고 반영 이벤트의 창고와 불일치하면 재고 차감을 차단한다.
- OVER/초과 이력은 삭제하거나 조용히 무시하지 않고 확인필요 상태로 분리한다.
- `ReturnExternalOutboundBatch`는 신규 확정 batch에서 단일 `client_id`를 가져야 한다(non-nullable 권장; DB schema 확정·migration은 별도 DB SPEC).

### 절대 없어야 할 것

- 판정/처리완료 즉시 `inventory_events` 생성.
- 판정/처리완료 즉시 `current_inventory` 변경.
- 원장 이벤트 없이 `current_inventory`만 변경.
- 프론트가 보낸 `client_id`/`warehouse_id`를 backend가 그대로 믿는 구현.
- 여러 고객사의 row를 하나의 외부반출 batch로 묶는 구현.
- 재고 미반영 row를 외부반출/폐기로 확정한 뒤 일마감에서 재고로 다시 쌓는 구현.
- 중복 요청으로 같은 row의 재고가 두 번 증가하거나 두 번 감소하는 구현.
- 일마감 양수 반영 없이 외부반출/폐기 음수 차감을 허용하는 구현.
- 반품 외 모듈까지 건드리는 deny-by-default/RLS/중앙화 격리 구현.

## 6. 정책 계약 상세

### 6.1 OVER/초과 이력 처리

- OVER/초과는 "수량/상품/예정자료 대비 초과 또는 불일치가 있어 자동 확정하면 안 되는 반품 처리 이력"으로 본다.
- OVER/초과 row는 다음 두 그룹으로 분리한다.
  - 정상 확정 가능: 운영자가 근거를 확인해 정상 수량/상품/창고로 확정한 건.
  - 확인 필요: 초과 사유, 상품 불일치, 수량 불일치, 창고 미확정 등으로 재고 원장 생성이 보류된 건.
- **확인 필요 row는 일마감, 외부반출, 폐기 확정에서 자동 재고반영 대상이 아니다. (확정)**
- OVER/초과 이력은 삭제 금지다. 운영자 확인 결과, 확인자, 확인시각, 사유를 추적할 수 있어야 한다.
- HOLD: OVER/초과 상태명, 전환 경로, 승인 권한, 허용 오차는 구현 전 별도 결정 필요.
  - OVER/초과 판단 기준: 예정 수량 초과, 스캔 수량 초과, 상품 불일치, 미예정 입고 중 어떤 조건을 포함할지.
  - 허용 오차 또는 예외 승인 권한.
  - 상태명과 전환 경로 예: `OVER_REVIEW_REQUIRED`, `OVER_APPROVED`, `OVER_REJECTED` 같은 신규 상태가 필요한지.

### 6.2 중복 차단 기준

| 대상 | 차단 기준 |
|---|---|
| 중복 마감 | row의 `inventory_reflected_yn`, 기존 `InventoryEvent.idempotency_key`, row 상태를 함께 확인한다. |
| 중복 외부반출 | row의 외부반출 상태, outbound batch 연결, 외부반출 음수 이벤트 idempotency key를 함께 확인한다. |
| 중복 폐기 | row의 폐기 상태, 폐기 확정 이력, 폐기 음수 이벤트 idempotency key를 함께 확인한다. |
| 중복 inventory_events | `InventoryEvent.idempotency_key` unique 계약을 유지한다. 같은 key 이벤트가 있으면 새 이벤트를 만들지 않는다. |
| 중복 재고반영 | 이벤트 생성과 현재고 갱신을 같은 transaction에서 처리하고, 이미 존재하는 이벤트면 현재고를 다시 갱신하지 않는다. |

- 구현 시 row-level lock 또는 동등한 동시성 제어가 필요하다.
- 동시 요청이 들어와도 한 요청만 원장 이벤트와 현재고 변경을 수행해야 한다.
- HOLD: 현재 DB 구조에서 row-level lock만으로 충분한지, 외부반출/폐기 이벤트 idempotency key를 위한 추가 컬럼 또는 index가 필요한지 구현 전 판단해야 한다.

### 6.3 ReturnExternalOutboundBatch.client_id nullable 계약

- **확정 (2026-06-22): 신규 외부반출 확정 batch는 단일 `client_id`를 반드시 가져야 한다(non-nullable 권장).** 여러 `client_id`의 row를 하나의 외부반출 batch에 섞는 것을 허용하지 않는다.
- DB 레벨 `client_id NOT NULL` 강제(migration)는 별도 DB SPEC으로 분리한다. 이번 계약 문서에서는 정책만 확정한다.
- 요청 row들이 서로 다른 고객사에 속할 때 backend가 확정을 거부한다.
- `agency_id`는 row/client의 실제 소속을 기준으로 결정한다.
- `client_unit_id`는 batch 공통 필수값으로 두지 않는다. 하나의 고객사 안에서 운영단위가 여러 개 섞일 수 있는지는 별도 결정 필요.
- HOLD: 기존 nullable 데이터 backfill 기준, `client_id NOT NULL` migration — 별도 DB SPEC.

### 6.4 스코프 강제 기준

- `agency_id`:
  - 내부 운영자라도 요청 row가 권한 범위 밖 agency에 속하면 확정할 수 없다.
  - 재고 이벤트와 현재고는 row/client의 실제 agency를 사용한다.
- `client_id`:
  - 고객사 사용자는 자기 `client_id` 밖의 row를 확정할 수 없다.
  - 내부 운영자는 선택 고객사를 기준으로 확정하되, row별 client scope를 다시 검증한다.
- `client_unit_id`:
  - row의 `client_unit_id`가 있는 경우 해당 운영단위가 같은 `client_id`에 속하는지 확인한다.
  - `client_unit_id`가 없는 row를 확정할 수 있는지는 업무 정책 결정 필요. (§8 결정 필요 3 참조)
- `warehouse_id`:
  - 양수 반영은 최종 확정 창고가 필요하다.
  - 외부반출/폐기 음수 반영은 기존 양수 반영 이벤트의 창고와 같은 창고에서 차감한다.
  - 기존 반영 이벤트가 없거나 창고가 불일치하면 차감하지 않는다.

## 7. 완료기준 (A안 확정 기준)

### 7.1 공통 완료기준

- [ ] 1) 판정 저장/처리완료만 수행한 row는 `inventory_events`와 `current_inventory`가 변하지 않는다.
- [ ] 2) 같은 row, 같은 확정 타입, 같은 `stock_status`는 재고가 중복 증가하거나 중복 감소하지 않는다.
- [ ] 3) OVER/초과 row는 자동 재고반영되지 않고 확인필요로 분리된다.
- [ ] 4) 고객사/대리점/운영단위/창고 스코프 밖 row를 확정하려 하면 backend가 거부하거나 확인필요로 분리한다.
- [ ] 5) 재고 이벤트 없이 `current_inventory`만 바뀌는 경로가 없다.

### 7.2 A안 완료기준

- [ ] 1) 일마감 confirm은 반영 가능한 row에 대해 양수 원장 이벤트와 현재고 증가를 한 번만 수행한다. 폐기·제조사반품 row도 처분대기 `stock_status`로 양수 반영된다.
- [ ] 2) 같은 row를 다시 일마감 confirm해도 현재고가 중복 증가하지 않고 skip 결과가 남는다.
- [ ] 3) 일마감으로 재고 반영된 제조사반품 row를 외부반출 확정하면 음수 원장 이벤트와 현재고 감소가 한 번만 수행된다.
- [ ] 4) 일마감으로 재고 반영된 폐기 row를 폐기 확정하면 음수 원장 이벤트와 현재고 감소가 한 번만 수행된다.
- [ ] 5) 재고 미반영 row(일마감 양수 반영 없는 row)의 외부반출/폐기 확정을 차단하거나 확인필요로 분리한다.
- [ ] 6) 정산에서 처분대기 입고·보관·폐기·제조사반품·외부반출 이력을 분리 집계할 수 있다.

### 7.3 batch 테넌시 완료기준

- [ ] 1) 서로 다른 `client_id`의 row를 하나의 외부반출 batch로 묶으려 할 때 backend가 거부한다.
- [ ] 2) row 단위 scope 검증과 audit가 고객사 혼재 위험을 추적한다.

## 8. 결정 필요 / 보류(HOLD) 케이스

**확정 완료 항목 (2026-06-22):**
- ✅ 폐기·제조사반품 재고반영 정책: **A안 확정** — 일마감 처분대기 양수 반영, 확정 시 음수 차감.
- ✅ 외부반출/폐기 확정 순서: **A안 확정** — 일마감 재고반영 후 확정 순서 강제. 재고 미반영 row 확정은 차단/확인필요.
- ✅ 독립 재고반영 API: **후속 SPEC으로 분리** — 이번 구현 범위 제외. 재처리/복구 전용.
- ✅ batch client_id: **non-nullable 권장 확정** — 여러 고객사 row 혼재 금지. DB migration은 별도 DB SPEC.
- ✅ OVER/초과: **확인필요/HOLD 확정** — 자동 재고반영 금지, 보존 필수.

**결정 필요:**
- 결정 필요 1: OVER/초과 상태명(`OVER_REVIEW_REQUIRED` 등), 전환 경로, 승인 권한, 허용 오차를 정해야 한다.
- 결정 필요 2: 외부반출 batch가 같은 고객사 안에서 여러 `client_unit_id`를 포함할 수 있는지 정해야 한다.
- 결정 필요 3: `client_unit_id`가 없는 row의 재고반영을 허용할지, 운영단위 보정 후에만 허용할지 정해야 한다.

**HOLD:**
- HOLD: 반품 외 모듈의 공통 RLS, deny-by-default, 중앙화 scope 강제 구조는 별도 구조 SPEC으로 보류한다.
- HOLD: UX/Help 문구, 작업자 안내, 화면 레이아웃 보강은 후속 작업이다.
- HOLD: `ReturnExternalOutboundBatch.client_id NOT NULL` migration — 별도 DB SPEC.
- HOLD: 외부반출/폐기 이벤트 idempotency key용 추가 컬럼/index 필요 여부 — 구현 전 판단.

---

이 스펙은 A안 확정 상태다. 구현은 별도 게이트에서 진행한다. 커밋/push 금지(수문장 단계 대기).
