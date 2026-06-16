# SPEC-002 독립 검증 보고서

## 1. 검증 개요

- 브랜치: `smartreturn-pro`
- 검증 일시: 2026-06-16 09:24:03 +09:00
- 검증 대상:
  - `backend/app/repositories/inventory_repository.py`
  - `backend/app/schemas/inventory.py`
  - `backend/app/services/inventory_service.py`
  - `backend/tests/test_inventory_current_api.py`
  - `frontend/src/components/common/SmartStatusBadge.tsx`
  - `frontend/src/features/inventory/CurrentInventoryPage.tsx`
  - `frontend/src/features/inventory/stockStatus.ts`
  - `frontend/src/types/inventory.ts`
  - `docs/reports/SPEC-002-build.md`
- 검증 모드: 게이트④ 독립 검증. 코드 수정, stage, commit, push, stash 조작 없이 읽기/실행/보고만 수행.

## 2. 완료기준 항목별 대조

| 번호 | SPEC-002 완료기준 | 판정 | 근거 |
| --- | --- | --- | --- |
| 1 | 창고를 선택하지 않고 조회하면, 같은 상품의 양품·리퍼B 등 각 등급이 여러 창고 수량을 합한 값으로 한 줄씩 보인다. | 충족 | `inventory_repository.list_current_inventory_aggregated()`가 `client_id + product_id + stock_status`로 group by하고 `SUM(qty_on_hand)`를 반환한다. `test_aggregated_when_warehouse_not_selected` 통과. |
| 2 | 특정 창고를 선택해 조회하면, 그 창고에 있는 수량만 보이고 다른 창고 수량은 섞이지 않는다. | 충족 | `inventory_service.list_current_inventory()`가 `warehouse_id is None`일 때만 합산 경로를 타고, 창고 선택 시 기존 창고별 조회를 유지한다. `test_per_warehouse_when_warehouse_selected_no_aggregation` 통과. |
| 3 | 같은 상품이라도 등급이 다르면 서로 다른 줄로 보이고 하나로 합쳐지지 않는다. | 충족 | 합산 group by에 `CurrentInventory.stock_status`가 포함된다. 테스트 데이터의 `GOOD`, `REFURB_B`, `DISPOSAL`이 별도 행으로 확인된다. |
| 4 | 모든 등급이 한글로 보이고, `GOOD`, `REFURB_A` 같은 영어 코드가 화면에 그대로 보이지 않는다. | 충족 | `stockStatus.ts`의 `stockStatusLabel()`과 `CurrentInventoryPage`의 `재고상태` 컬럼이 한글 라벨을 사용한다. 실제 브라우저 육안 확인은 게이트⑤에서 필요하다. |
| 5 | 판매가능과 처분대기가 한눈에 구분된다. | 충족 | `stockStatusGroupLabel()`/`stockStatusGroupTone()`으로 `판매가능`/`처분대기` 그룹 배지와 요약 카드를 표시한다. 실제 색상 체감은 게이트⑤에서 확인 필요. |
| 6 | 재고상태 필터에서 "리퍼B"만 골라 조회하면 리퍼B 등급 줄만 보인다. "전체"로 두면 모든 등급이 보인다. | 충족 | `STOCK_STATUS_FILTER_OPTIONS`가 전체 + 7등급을 제공하고, `stock_status` query를 backend로 전달한다. `test_stock_status_filter_in_aggregated_mode` 통과. |
| 7 | 화면 어디에도 재고를 바꾸는 버튼이 없다. 조회·새로고침·초기화만 있다. | 충족 | `CurrentInventoryPage`에 조회/새로고침/초기화만 확인된다. `increase_current_inventory()`나 `InventoryEvent` 생성 호출은 SPEC-002 조회 경로에 추가되지 않았다. |
| 8 | 지금 보는 게 "창고 전체 합산"인지 "특정 창고 재고"인지 화면 안내로 알 수 있다. | 충족 | `loadedWarehouseId` 기준 Alert가 "창고 전체 합산 보기" 또는 "특정 창고 보기"를 표시한다. |

## 3. Backend 검증

- repository:
  - `list_current_inventory_aggregated()`가 창고 미선택 합산 전용 조회를 담당한다.
  - `CurrentInventory.qty_on_hand`를 합산하고 `warehouse_count`를 계산한다.
  - `agency_id`, `client_id`, `product_code`, `barcode`, `keyword`, `stock_status` 필터가 적용된다.
- schema:
  - 합산 행을 표현하기 위해 `inventory_id`, `warehouse_id`, `updated_at`이 optional로 바뀌었다.
  - `warehouse_count`와 list 응답의 `aggregated` 플래그가 추가되었다.
- service:
  - `require_permission(auth, "INVENTORY_VIEW")` 후 `resolve_effective_client_id`, `resolve_effective_agency_id`로 범위를 확정한다.
  - `warehouse_id is None`이면 합산 조회, 창고 선택 시 기존 창고별 조회를 사용한다.
- API 응답:
  - 창고 미선택: `aggregated=True`, `warehouse_id=None`, `warehouse_count` 포함.
  - 창고 선택: `aggregated=False`, `warehouse_count=1`.
- 테넌트/권한/데이터 범위 위험:
  - `INVENTORY_VIEW`, `agency_id`, `client_id` scope는 확인됨.
  - 별도 warehouse allow-list 검증은 이 구현에 새로 추가되지 않았다. 현재 SPEC-002 범위에서는 기존 재고 조회 권한 모델을 따른 것으로 판단한다.

## 4. Frontend 검증

- CurrentInventoryPage:
  - 전체 + 7등급 필터, 판매가능/처분대기 컬럼, 한글 상태 라벨, 합산/단일 안내 Alert가 반영됐다.
  - 합산 행은 `전체 합산`, `전체 N개 창고`로 표시된다.
  - 합산 row key는 `agg-${client_id}-${product_id}-${stock_status}` 형태로 보완됐다.
- stockStatus.ts:
  - `GOOD`, `REFURB_A`, `REFURB_B`, `REFURB_C`, `SAMPLE`, `MANUFACTURER_RETURN`, `DISPOSAL` 라벨/그룹/정렬이 표시 레이어 단일 출처로 정리됐다.
  - legacy `REFURB`는 표시 호환용으로만 두고 신규 필터 옵션에서는 제외한다.
- SmartStatusBadge:
  - 기존 `status` 기반 tone 추론은 유지하고 optional `tone` override를 추가했다.
  - 기존 호출부의 기본 동작을 깨뜨릴 변경은 확인되지 않았다.
- 타입 정합성:
  - frontend `CurrentInventoryItem` 타입이 backend optional/null 응답과 `warehouse_count`를 반영한다.
  - TypeScript build 통과.
- 1366x768 사용성 위험:
  - 브라우저 검증은 이번 단계에서 수행하지 않았다.
  - 컬럼 수가 늘어났으므로 게이트⑤에서 실제 1366x768 화면 밀도와 배지/안내문 노출을 확인해야 한다.

## 5. 테스트/build 결과

- 사전 명령:
  - `git branch --show-current` → `smartreturn-pro`
  - `git status --short` → SPEC-002 구현 파일, 반품 화면 6개, 보류 문서가 dirty/untracked 상태
  - `git diff --check` → 실제 오류 없음. 반품 화면 6개 LF/CRLF 경고만 출력.
  - `git diff --cached --name-only` → 빈 결과(staged 파일 없음)
  - `docs/reports/SPEC-002-build.md` → 존재 확인
- backend test:
  - 명령: `.\.venv\Scripts\python.exe -m pytest tests/test_inventory_current_api.py -p no:cacheprovider` (`backend` 디렉터리)
  - 결과: 3 passed, 0 failed
- frontend build:
  - 1차 명령: `npm.cmd run build` (`frontend` 디렉터리)
  - 1차 결과: 실패. `vite.config.js` load 중 `Error: spawn EPERM`
  - base-comparison: SPEC-002 소스 오류가 아니라 sandbox/esbuild 실행 noise로 분류. 반품 화면 6개 오류도 아님.
  - 재시도 명령: `npm.cmd run build` 승인 실행
  - 재시도 결과: 통과. `tsc --noEmit -p tsconfig.json && vite build`, 3110 modules transformed, built in 10.76s
  - 경고: chunk size 500 kB 초과 Vite 경고. SPEC-002 신규 회귀로 보지 않음.

## 6. 재고 정책 충돌 여부

- 처리완료 시점 `inventory_events` 생성 금지와 충돌 여부:
  - 충돌 없음. SPEC-002 구현은 조회/표시 경로이며 `InventoryEvent` 생성이나 `current_inventory` 증감 호출을 추가하지 않는다.
- 일마감/월마감/외부반출 확정 이후 재고반영 원칙과 충돌 여부:
  - 충돌 없음. 이미 반영된 `current_inventory`를 `stock_status`별로 조회/합산/표시한다.
  - 일마감/월마감/외부반출/폐기 확정 액션은 이 화면에 추가되지 않았다.

## 7. 결론

- 판정: PASS
- 이유:
  - SPEC-002 완료기준 8개가 코드/스키마/테스트/build 기준으로 충족된다.
  - backend inventory 테스트 3개가 통과했다.
  - frontend build가 승인 실행에서 통과했다.
  - 1차 build 실패는 `spawn EPERM` 실행환경 noise로 분류되며 SPEC-002 신규 회귀가 아니다.
- 게이트⑤ 화면 인수로 넘어가도 되는지:
  - 가능. 단, 실제 화면에서 1366x768 사용성, 한글 라벨, 판매가능/처분대기 색상 구분, 창고 합산 안내를 수동 확인해야 한다.
- 구현 커밋 가능 여부:
  - 게이트⑤ 화면 인수 후 선별 커밋 가능.
  - 커밋 시 SPEC-002 구현 파일과 `docs/reports/SPEC-002-build.md`, `docs/reports/SPEC-002-verify.md`만 포함하고 반품 화면 6개/보류 문서는 제외해야 한다.
- 추가 수정 필요 항목:
  - 필수 수정 없음.
  - 후속 검토: warehouse allow-list 정책이 확정되면 inventory 조회에도 warehouse scope 검증 보강.
  - 후속 검토: 재고등급 라벨/그룹을 장기적으로 공통코드/서버 기준으로 내려받을지 결정.
