# 슬라이스 스펙: 반품 재고반영 실행 구조

## 0. 근거와 범위

- SPEC 번호: `SPEC-005`
- 근거 문서:
  - `docs/specs/SPEC-004-return-inventory-ledger-contract.md` (A안 정책 확정)
  - `docs/reports/return-writeflow-tenancy-audit.md`
- 번호 확인: 기존 `docs/specs` 최대 번호는 `SPEC-004`이며, 이 문서는 다음 신규 번호 `SPEC-005`로 작성한다.
- 작성 상태: 초안. 사용자 승인(게이트②) 전 구현 금지.
- 이 SPEC은 SPEC-004 A안 정책을 **어떻게 구현하는지** 실행 구조를 잠근다. SPEC-004의 정책 결정을 변경하지 않는다.
- 코드/API/DB/schema/migration 구현은 사용자 승인 후 별도 게이트③에서 진행한다.

### 테넌시/권한 범위에 대해

- 이 스펙은 **tenant isolation 전체 정책 스펙이 아니다.**
- 이 스펙은 재고반영 실행 경로(일마감 confirm, 외부반출 confirm, 폐기 confirm)에서 **반드시 강제해야 할 데이터 범위 계약만 정의한다.**
- 재고반영 API, `inventory_events` 생성, `current_inventory` 변경은 backend에서 `client_id` / `client_unit_id` / `warehouse_id` 범위를 강제해야 한다. 프론트 선택값이나 화면 필터만으로 데이터 범위를 신뢰하지 않는다.
- **tenant isolation 전체 정책은 이 SPEC에서 새로 정의하지 않는다.** 아래 기준 문서로 위임 참조한다.
  - `AGENTS.md` — 권한 원칙 · DB/업무 원장 원칙
  - `ai-harness/memory/000-read-this-first.md` — 절대 규칙 §권한/테넌시
  - `ai-harness/handoff/latest-handoff.md` — 현재 프로젝트 상태
  - `docs/reports/return-writeflow-tenancy-audit.md` — 반품 쓰기흐름·테넌시 탐색 보고서
- 별도 tenant isolation slice spec이 필요하면 후속 큐로 분리한다. 이 SPEC에서 확정하지 않는다.
- **SPEC-002는 `stock_status` 표시 스펙이다.** tenant isolation 근거로 참조하지 않는다.

## 1. 한 줄 목적

SPEC-004 A안(일마감 양수 반영 → 확정 시 음수 차감)을 실제 backend 서비스 함수 수준의 실행 계약으로 정의해, 구현자가 계약을 벗어난 재고 변경을 만들 수 없도록 잠근다.

## 2. 사용자 / 권한 scope

### 2.1 role 기준

| 액션 | 필요 role | 필요 권한 |
|---|---|---|
| 일마감 confirm | `SUPER_ADMIN`, `INTERNAL_ADMIN`, `INTERNAL_WORKER`, `AGENCY_ADMIN` | `RETURN_CLOSE` |
| 외부반출 confirm | `SUPER_ADMIN`, `INTERNAL_ADMIN`, `INTERNAL_WORKER`, `AGENCY_ADMIN` | `RETURN_OUTBOUND` |
| 폐기 confirm | `SUPER_ADMIN`, `INTERNAL_ADMIN`, `INTERNAL_WORKER`, `AGENCY_ADMIN` | `RETURN_OUTBOUND` |
| 독립 재고반영 API | — | 후속 SPEC으로 분리 (이번 범위 밖) |

- 고객사 포털 사용자(`CLIENT_ADMIN`, `CLIENT_USER`)는 위 액션을 모두 실행할 수 없다.

### 2.2 데이터 범위 강제 순서

> **이 순서는 재고반영 실행 경로(일마감/외부반출/폐기 confirm)에서만 적용하는 backend enforcement 계약이다.** tenant isolation 전체 정책을 새로 정의하지 않는다. 전체 정책은 §0의 위임 참조 문서를 따른다.

backend가 재고반영 실행 전 아래 순서로 강제한다. 하나라도 실패하면 해당 row는 `BLOCKED` 또는 확인필요로 분리한다.

1. **인증 컨텍스트 확인**: 요청자의 `role`과 권한을 session/JWT에서 추출한다.
2. **`agency_id` 강제**: row의 `agency_id`가 요청자의 권한 범위 내인지 확인한다.
3. **`client_id` 강제**: row의 `client_id`가 요청자의 접근 허용 `client_id`와 일치하는지 확인한다.
4. **`client_unit_id` 확인**: row의 `client_unit_id`가 있으면 같은 `client_id`에 속하는지 확인한다.
5. **`warehouse_id` 확인**: row의 확정 창고가 존재하고 같은 `agency_id` / `client_id` 범위 내인지 확인한다.
6. **재고반영 가능 상태 확인**: row 상태, 수량, 상품 마스터 연결 여부를 확인한다.
7. 프론트가 보낸 `client_id` / `warehouse_id` / `agency_id` 값은 신뢰하지 않는다. 항상 서버 컨텍스트 기준으로 재검증한다.

## 3. 재고반영 실행 경로 계약

### 3.1 공통 원칙

- `inventory_events`와 `current_inventory`는 **항상 같은 database transaction 안에서** 함께 처리한다.
- 원장 이벤트(`inventory_events`)를 먼저 생성하고 현재고(`current_inventory`)를 갱신한다. 역순 금지.
- `current_inventory`만 단독으로 변경하는 경로는 존재하면 안 된다.
- 모든 확정 액션은 row-level lock 또는 동등한 동시성 제어를 사용해 같은 row의 동시 확정을 막는다.

### 3.2 일마감 confirm 실행 흐름

**진입 API**: `POST /api/returns/closing/confirm`
**서비스 진입점**: `return_intake_service.py` → `confirm_return_closing()`

**실행 순서:**

1. **사전 scope 검증** (§2.2 순서 적용): 요청자 권한, `agency_id`, `client_id`, `client_unit_id`, `warehouse_id` 강제.
2. **재고반영 대상 필터**: 아래 조건을 모두 충족하는 row만 처리한다.
   - `status = COMPLETED` (처리완료 상태)
   - `judgement_status`가 `INVENTORY_REFLECTABLE` 집합에 속함 (§3.2.1 참조)
   - `inventory_reflected_yn = false`
   - `warehouse_id`가 확정됨 (null 불가)
   - 상품 마스터 연결됨 (`product_id` 또는 `product_code` 기준)
   - OVER/초과 확인필요 상태가 아님 (§3.5 참조)
3. **row-level lock 획득**: 처리할 row에 lock을 건 뒤 `inventory_reflected_yn`을 재확인한다(double-check).
4. **idempotency 확인**: `InventoryEvent.idempotency_key = f"return-closing:{row.id}:{stock_status.lower()}"` 패턴으로 기존 이벤트를 조회한다. 이미 존재하면 `SKIPPED`로 집계하고 해당 row를 건너뛴다.
5. **`inventory_events` 생성**: 하나의 transaction 안에서
   - `qty_delta`: 양수(+)
   - `stock_status`: `row.judgement_status` (등급 그대로 유지)
   - `event_type`: `GOOD` 판정이면 `RETURN_GOOD_IN`, 나머지는 `RETURN_JUDGEMENT_IN`
   - `agency_id`, `client_id`, `warehouse_id`: row의 실제 값 사용 (프론트 값 불신)
   - `source_type = "RETURN_CLOSING"`, `source_id = row.id`
6. **`current_inventory` 증가**: 같은 transaction 안에서 `client_id`, `warehouse_id`, `product_id`, `stock_status` 단위로 증가.
7. **`inventory_reflected_yn = true`**, `inventory_reflected_at` 저장.
8. **결과 집계**: `applied_count`, `skipped_count`, `failed_count`, `blocked_count`를 명확히 반환.

#### 3.2.1 INVENTORY_REFLECTABLE 집합 (A안 기준)

| 판정 | 재고반영 여부 | stock_status | 비고 |
|---|---|---|---|
| `GOOD` | ✅ 양수 반영 | `GOOD` | 정상재고 |
| `REFURB_A` | ✅ 양수 반영 | `REFURB_A` | 리퍼 등급별 분리 |
| `REFURB_B` | ✅ 양수 반영 | `REFURB_B` | |
| `REFURB_C` | ✅ 양수 반영 | `REFURB_C` | |
| `SAMPLE` | ✅ 양수 반영 | `SAMPLE` | |
| `MANUFACTURER_RETURN` | ✅ 양수 반영 | `MANUFACTURER_RETURN` | **처분대기 재고** (A안 확정) |
| `DISPOSAL` | ✅ 양수 반영 | `DISPOSAL` | **처분대기 재고** (A안 확정) |
| `HOLD` | ❌ 차단 | — | 재판정 대기 |
| `DEFECTIVE` | ❌ 차단 | — | 별도 불량 재고화 후속 SPEC |

- `MANUFACTURER_RETURN`·`DISPOSAL`의 양수 반영은 처분대기 재고 `stock_status`를 그대로 유지한다. `GOOD`으로 바꾸지 않는다.
- 결정 필요: `REFURB`(등급 미지정) generic 값이 있을 경우 `REFURB_A`로 매핑할지, 차단할지 구현 전 결정 필요.

### 3.3 외부반출 confirm 실행 흐름

**진입 API**: `POST /api/returns/external-outbound/confirm`
**서비스 진입점**: `return_intake_service.py` → 외부반출 confirm 함수

**실행 순서:**

1. **사전 scope 검증** (§2.2 순서 적용)
2. **일마감 반영 여부 확인**: 외부반출 대상 row가 `inventory_reflected_yn = true`인지 확인한다.
   - `false`이면: **일마감 재고반영이 완료되지 않은 row는 외부반출 확정 처리에 진입할 수 없다.** 해당 row는 `BLOCKED_INVENTORY_NOT_REFLECTED` 또는 확인필요로 분리하며, 재고 차감 없이 업무 확정만 완료하는 흐름은 금지한다.
   - `true`이면: 3번으로 진행.
3. **idempotency 확인**: `InventoryEvent.idempotency_key = f"return-external-outbound:{row.id}:{stock_status.lower()}"` 기존 이벤트 조회. 있으면 `SKIPPED`.
4. **기존 양수 이벤트 조회**: row의 일마감 반영 이벤트를 찾아 `stock_status`와 `warehouse_id`를 추출한다.
5. **창고 일치 확인**: 음수 차감 `warehouse_id` = 기존 양수 이벤트의 `warehouse_id`. 불일치하면 차단.
6. **`inventory_events` 생성**: 하나의 transaction 안에서
   - `qty_delta`: 음수(−)
   - `stock_status`: 기존 양수 이벤트의 `stock_status` **그대로** (임의 변경 금지)
   - `event_type`: `RETURN_EXTERNAL_OUTBOUND_OUT`
   - `source_type = "RETURN_EXTERNAL_OUTBOUND"`, `source_id = row.id`
7. **`current_inventory` 감소**: 같은 transaction.
8. **외부반출 상태 확정** + 업무 이력(확정자, 확정시각, 사유) 저장.

### 3.4 폐기 confirm 실행 흐름

**진입 API**: `POST /api/returns/disposal/tasks/{task_id}/confirm`
**서비스 진입점**: `return_intake_service.py` → 폐기 confirm 함수

**실행 순서:**

1. **사전 scope 검증** (§2.2 순서 적용)
2. **일마감 반영 여부 확인**: `inventory_reflected_yn = true`인지 확인한다.
   - `false`이면: **일마감 재고반영이 완료되지 않은 row는 폐기 확정 처리에 진입할 수 없다.** 해당 row는 `BLOCKED_INVENTORY_NOT_REFLECTED` 또는 확인필요로 분리하며, 재고 차감 없이 업무 확정만 완료하는 흐름은 금지한다.
   - `true`이면: 3번 진행.
3. **idempotency 확인**: `InventoryEvent.idempotency_key = f"return-disposal:{row.id}:{stock_status.lower()}"` 기존 이벤트 조회. 있으면 `SKIPPED`.
4. **기존 양수 이벤트 조회**: `stock_status`와 `warehouse_id` 추출.
5. **창고 일치 확인**: 음수 차감 `warehouse_id` = 기존 양수 이벤트의 `warehouse_id`. 불일치하면 차단.
6. **`inventory_events` 생성**: 하나의 transaction 안에서
   - `qty_delta`: 음수(−)
   - `stock_status`: 기존 양수 이벤트의 `stock_status` **그대로**
   - `event_type`: `RETURN_DISPOSAL_OUT`
   - `source_type = "RETURN_DISPOSAL"`, `source_id = task_id`
7. **`current_inventory` 감소**: 같은 transaction.
8. **폐기 확정 상태** + 업무 증빙(사유, 메모, 확정자, 확정시각) 저장.

## 4. idempotency key 표준

| 확정 타입 | key 패턴 |
|---|---|
| 일마감 양수 반영 | `return-closing:{row_id}:{stock_status}` |
| 외부반출 음수 차감 | `return-external-outbound:{row_id}:{stock_status}` |
| 폐기 음수 차감 | `return-disposal:{row_id}:{stock_status}` |

- `stock_status`는 소문자로 정규화한다 (예: `disposal`, `manufacturer_return`).
- `InventoryEvent.idempotency_key`는 unique 제약이 있어야 한다. DB 레벨 unique index를 강제한다.
- 같은 key가 이미 존재하면 새 이벤트를 생성하지 않고 `SKIPPED` 결과를 반환한다.
- HOLD: 현재 `InventoryEvent`에 `idempotency_key` unique index가 존재하는지 구현 전 확인 필요. 없으면 migration 추가 필요(별도 DB SPEC).

## 5. OVER/초과/확인필요 진입 차단 기준

- OVER/초과 row는 재고반영 실행 단계에 진입하지 않는다.
- 진입 차단 조건 (하나라도 해당하면 재고반영 대상에서 제외):

| 조건 | 처리 |
|---|---|
| `inventory_reflected_yn = true`인데 재반영 시도 | `SKIPPED` (idempotency) |
| `warehouse_id` null 또는 미확정 | `BLOCKED_NO_WAREHOUSE` |
| `product_id` 없거나 상품 마스터 미연결 | `BLOCKED_NO_PRODUCT` |
| 수량 0 또는 음수 | `BLOCKED_INVALID_QTY` |
| OVER/초과 확인필요 상태 플래그 | `BLOCKED_OVER_REVIEW` |
| `client_id` scope 불일치 | `BLOCKED_SCOPE_MISMATCH` |
| `agency_id` scope 불일치 | `BLOCKED_SCOPE_MISMATCH` |
| 일마감 미반영 row의 외부반출/폐기 확정 시도 | `BLOCKED_INVENTORY_NOT_REFLECTED` |

- BLOCKED 결과는 운영자가 확인할 수 있도록 row 단위로 사유를 저장한다.
- BLOCKED 결과는 자동으로 삭제하거나 무시하지 않는다.
- 결정 필요: OVER/초과 확인필요 상태 플래그의 컬럼명과 상태값을 정해야 한다(SPEC-004 §8 결정 필요 1).

## 6. 중복 차단 구현 계약

| 대상 | 구현 수단 |
|---|---|
| 중복 일마감 양수 반영 | `inventory_reflected_yn` + idempotency key 이중 확인 → `SKIPPED` |
| 중복 외부반출 음수 차감 | 외부반출 상태 + idempotency key 이중 확인 → `SKIPPED` |
| 중복 폐기 음수 차감 | 폐기 상태 + idempotency key 이중 확인 → `SKIPPED` |
| 동시 요청 race condition | row-level lock (`SELECT ... FOR UPDATE` 또는 동등) |
| `current_inventory` 중복 증감 | transaction 안에서 이벤트 생성 → 현재고 갱신 순서 강제 |

- lock 획득 후 상태 재확인(double-check)을 반드시 수행한다. lock 전 상태로 판단하지 않는다.
- 동시 요청 중 하나가 lock을 획득해 처리하면 나머지는 `SKIPPED`를 받는다.
- HOLD: `SELECT ... FOR UPDATE`가 현재 ORM/SQLAlchemy 사용 패턴에서 올바르게 동작하는지 구현 전 확인.

## 7. 처분대기 재고 추적 계약

- `MANUFACTURER_RETURN`·`DISPOSAL` 판정 row의 일마감 반영 결과는 `stock_status = "MANUFACTURER_RETURN"` 또는 `stock_status = "DISPOSAL"`로 `inventory_events`와 `current_inventory`에 남는다.
- 정상재고(`GOOD`, `REFURB_A/B/C`, `SAMPLE`)와 **같은 재고 행에 합산되지 않는다.**
- 처분대기 재고 조회는 `stock_status IN ("MANUFACTURER_RETURN", "DISPOSAL")` 필터로 분리 집계한다.
- 정산 분리 집계: `event_type IN ("RETURN_JUDGEMENT_IN", "RETURN_EXTERNAL_OUTBOUND_OUT", "RETURN_DISPOSAL_OUT")`으로 처분대기 입고/반출/폐기 이력을 분리할 수 있어야 한다.
- 결정 필요: `DISPOSAL` 처분대기 양수 반영 후 폐기 확정 음수 차감까지의 보관 기간 추적이 필요한지, `inventory_events`의 `raw_json`에 폐기 사유를 포함할지 정해야 한다.

## 8. 있어야 할 것 / 절대 없어야 할 것

### 있어야 할 것

- 모든 재고반영 경로는 `agency_id`, `client_id`, `warehouse_id`를 backend에서 재검증한다.
- 일마감 confirm 응답에는 `applied`, `skipped`, `failed`, `blocked` row 수와 row별 결과가 포함된다.
- 외부반출/폐기 confirm 응답에도 재고 차감 성공/건너뜀/차단 여부가 포함된다.
- BLOCKED 결과는 원인 코드와 함께 저장돼 운영자가 확인할 수 있다.
- 처분대기 재고(`MANUFACTURER_RETURN`, `DISPOSAL`)는 정산에서 분리 집계할 수 있다.
- idempotency key unique 제약이 DB 레벨에서 강제된다.

### 절대 없어야 할 것

- 판정/처리완료 즉시 `inventory_events` 생성 또는 `current_inventory` 변경.
- 원장 이벤트 없이 `current_inventory`만 변경하는 경로.
- 일마감 양수 반영 없이 외부반출/폐기 음수 차감을 허용하는 경로.
- 음수 이벤트의 `stock_status`를 `GOOD`이나 다른 등급으로 임의 변경하는 구현.
- OVER/초과 확인필요 row가 자동으로 재고반영되는 경로.
- 여러 `client_id`의 row를 하나의 외부반출 batch로 묶는 구현.
- 프론트가 보낸 `client_id` / `warehouse_id`를 backend가 그대로 신뢰하는 구현.
- lock 없이 동시 요청이 같은 row를 두 번 재고반영하는 구현.
- SPEC-002(`stock_status` 표시 스펙)를 tenant isolation 근거로 참조하는 구현.
- 반품 외 모듈의 deny-by-default/RLS/중앙화 격리 구현(별도 구조 SPEC).

## 9. 완료기준

- [ ] 1) 일마감 confirm 후 `GOOD` 판정 row의 `inventory_events`에 양수 이벤트가 생성되고 `current_inventory`가 증가한다.
- [ ] 2) 일마감 confirm 후 `DISPOSAL`·`MANUFACTURER_RETURN` 판정 row의 `inventory_events`에 처분대기 `stock_status`로 양수 이벤트가 생성된다. `GOOD` 재고에 합산되지 않는다.
- [ ] 3) 같은 row를 두 번 일마감 confirm해도 `inventory_events`가 중복 생성되지 않고 `SKIPPED` 결과가 반환된다.
- [ ] 4) 일마감 반영된 `MANUFACTURER_RETURN` row를 외부반출 confirm하면 동일 `stock_status`로 음수 이벤트가 생성되고 `current_inventory`가 감소한다.
- [ ] 5) 일마감 반영된 `DISPOSAL` row를 폐기 confirm하면 동일 `stock_status`로 음수 이벤트가 생성되고 `current_inventory`가 감소한다.
- [ ] 6) 일마감 미반영 row를 외부반출/폐기 confirm하면 확정 처리에 진입하지 못하고 `BLOCKED_INVENTORY_NOT_REFLECTED` 결과가 반환된다. 재고 차감 없이 업무 확정만 완료되는 결과는 없어야 한다.
- [ ] 7) `warehouse_id`가 없는 row를 일마감 confirm하면 `BLOCKED_NO_WAREHOUSE` 결과가 반환된다.
- [ ] 8) OVER/초과 확인필요 row를 일마감 confirm해도 재고반영되지 않는다.
- [ ] 9) 고객사 포털 사용자(`CLIENT_ADMIN`, `CLIENT_USER`)로 일마감/외부반출/폐기 confirm API를 호출하면 403이 반환된다.
- [ ] 10) 서로 다른 `client_id`의 row가 섞인 외부반출 batch confirm을 시도하면 backend가 거부한다.
- [ ] 11) `inventory_events` 없이 `current_inventory`만 변경되는 경로가 없다(재고 이벤트 테이블 기준 검증).

## 10. 결정 필요 / 보류(HOLD)

**결정 필요:**
- 결정 필요 1 (SPEC-004 이월): OVER/초과 확인필요 상태 컬럼명·상태값을 정해야 한다.
  예: `return_intake_rows`에 `is_over_review_required boolean` 컬럼 추가 여부.
- 결정 필요 2: `REFURB` generic(등급 미지정) 값이 있을 경우 일마감 확정 시 처리 방식.
  - 선택지 A: `REFURB_A`로 자동 매핑 후 반영.
  - 선택지 B: 차단하고 `BLOCKED_AMBIGUOUS_GRADE`로 분리.
- 결정 필요 3 (SPEC-004 이월): `client_unit_id`가 없는 row의 재고반영을 허용할지, 운영단위 보정 후에만 허용할지.
- 결정 필요 4: `InventoryEvent.idempotency_key` unique index가 현재 DB에 존재하는지 확인 필요. 없으면 별도 DB SPEC으로 migration 추가.

**HOLD:**
- HOLD: `SELECT ... FOR UPDATE` lock 패턴 현재 ORM 호환 여부 — 구현 전 확인.
- HOLD: 외부반출/폐기 이벤트 idempotency key용 추가 컬럼/index — 별도 DB SPEC.
- HOLD: 독립 재고반영 API(재처리/복구 전용) — 일마감 confirm 안정화 후 후속 SPEC.
- HOLD: 반품 외 모듈 RLS/deny-by-default/중앙화 격리 구조 — 별도 구조 SPEC.
- HOLD: 처분대기 재고 보관 기간 추적, 폐기 사유 `raw_json` 포함 여부 — 정산 SPEC에서 결정.

---

이 스펙은 사용자 승인(게이트②) 후 구현한다. 승인 전 구현/커밋/push 금지.
