# 슬라이스 스펙: 재고현황 stock_status별 구분 표시

> 배경: SPEC-001(등급별 재고 마감반영)은 코드 확인 결과 [폐기·대체]됨. 현재 코드가 이미 `stock_status`별로 분리 적재한다(`CurrentInventory`의 `UniqueConstraint`에 `stock_status` 포함, 일마감 시 `stock_status = 판정값`으로 별도 행 적재). 따라서 재고 계산/반영 로직은 손댈 필요가 없고, 남은 진짜 요구는 "이미 분리되어 쌓인 재고를 등급별로 보기 좋게 보여주는 조회 화면"이다. 이 SPEC이 그 표시 슬라이스만 담는다. (decision-log D-003: 폐기/제조사반품 재고반영 유지 확정 참조.)

## 1. 한 줄 목적
이미 `stock_status`(재고등급)별로 분리 적재된 현재고를, 등급(양품/리퍼/샘플/제조사반품/폐기)별 행으로 구분해 보여주는 순수 조회/표시 화면이다. (재고 수치/계산은 바꾸지 않는다.)

## 2. 사용자 / 권한 scope
- 누가 쓰나(role): 내부 운영자 `SUPER_ADMIN`, `INTERNAL_ADMIN`, `INTERNAL_WORKER`, `AGENCY_ADMIN` + `INVENTORY_VIEW` 권한 보유자. (현재 backend `inventory_service.list_current_inventory`가 `require_permission(auth, "INVENTORY_VIEW")`를 강제하고, 화면 route도 `ProtectedRoute requiredPermissions={["INVENTORY_VIEW"]}`로 보호된다.)
- 권한: `INVENTORY_VIEW`(조회 전용). 이 화면은 재고를 바꾸는 어떤 액션도 갖지 않으므로 `INVENTORY_ADJUST`는 필요 없다.
- scope: `agency_id` + `client_id`는 backend에서 항상 재검증한다(`resolve_effective_agency_id`/`resolve_effective_client_id`). `warehouse_id`는 선택값이며 미선택 시 권한 범위 내 전체 창고가 대상이다.
- 내부 / 포털 구분: 1차 대상은 내부 운영 화면이다. 고객사 포털(`CLIENT_ADMIN`/`CLIENT_USER`/`READ_ONLY`)에 이 화면을 노출할지는 권한 시드 정책상 `INVENTORY_VIEW`가 이들 role에 "후보"로만 잡혀 있어 확정 전이다(7번 선행 확인 1). 이 슬라이스는 내부 화면 보강만 다루고, 포털 노출은 범위 밖이다.

## 3. 화면에서 하는 일 (흐름)
1. 내부 운영자가 재고현황 화면(`/inventory/current`)에 들어와 고객사(필수/선택), 창고(선택), 상품코드/상품명/바코드 키워드로 조회한다.
2. 창고를 선택하지 않으면 권한 범위 내 모든 창고의 재고를 대상으로, 같은 상품·같은 등급은 창고를 가로질러 한 줄로 합산해 보여준다. 창고를 선택하면 그 창고의 재고만 보여준다.
3. 표시 단위는 `stock_status` 행 단위다: 양품(GOOD), 리퍼A/B/C(REFURB_A/B/C), 샘플(SAMPLE), 제조사반품(MANUFACTURER_RETURN), 폐기(DISPOSAL). 같은 상품이라도 등급이 다르면 다른 줄로 보인다.
4. 등급은 현장/운영자가 읽을 수 있는 한글 라벨로 보여준다(enum 원문 비노출). 라벨은 기존 `CLOSING_REFLECTED_STOCK_LABELS` 정의를 표시 기준으로 따른다(정상재고/리퍼A 재고/리퍼B 재고/리퍼C 재고/샘플 재고/제조사반품 재고/폐기 재고).
5. 등급은 시각적으로 2그룹으로 구분된다: "판매가능"(양품·리퍼·샘플) vs "처분대기"(제조사반품·폐기). 그룹은 색/배지/구분선 등 부드러운 상태 표현으로 나누되 진한 원색은 피한다(디자인 시스템 기준).
6. 새로고침/초기화로 조회조건을 다시 적용할 수 있다. 화면은 조회만 하며 재고를 바꾸는 버튼은 없다.

## 4. 재사용할 기존 자산 (코드로 확인함)
- route: `frontend/src/routes/router.tsx` 182~186행 `path: "inventory/current"` → `CurrentInventoryPage`, 경로 상수 `ROUTE_PATHS.inventoryCurrent = "/inventory/current"` (`frontend/src/routes/routePaths.ts:25`). 좌측 메뉴는 `frontend/src/layouts/MainLayout.tsx:130` "재고현황"(`INVENTORY_VIEW` 없으면 disabled). → 신규 화면/route 신설이 아니라 **기존 `CurrentInventoryPage` 보강**이다.
- 화면: `frontend/src/features/inventory/CurrentInventoryPage.tsx` (이미 존재, `SmartPage`/`SmartPageHeader`/`SmartDataGrid`/`SmartSummaryCard`/`SmartStatusBadge` 사용). 현재는 재고상태 필터가 `ALL`/`GOOD` 2개뿐이고(19~22행), 라벨 매핑(`toStockStatusLabel`)이 `GOOD`만 "정상재고"로 바꾸며 나머지는 enum 원문을 그대로 노출한다(286~291행). 안내문/요약도 "GOOD/양품" 중심으로만 작성돼 있다. → 이 슬라이스가 등급 라벨/그룹 구분/필터 옵션을 보강할 지점.
- API: `GET /api/inventory/current` (`backend/app/routers/inventory.py:18`) → `inventory_service.list_current_inventory` → `inventory_repository.list_current_inventory`. 프론트 호출은 `frontend/src/api/inventory.ts`의 `listCurrentInventory`. **client_id/agency_id/warehouse_id/product_code/barcode/keyword/stock_status 필터와 `stock_status` 정렬을 이미 지원**한다(`inventory_repository.py:82~150`, 정렬은 145행 `order_by(... CurrentInventory.stock_status)`). 신규 쿼리/엔드포인트를 만들지 않는다.
- 공통 컴포넌트: `SmartDataGrid`, `SmartPage`, `SmartPageHeader`, `SmartSummaryCard`, `SmartStatusBadge` 재사용. 신규 그리드/모달 금지. 고객사/창고 선택은 기존 화면의 `Select` 패턴을 유지하되 공통 선택 컴포넌트 기준(`SmartLookupModal`/`SmartCommonCodeSelect`)과 충돌하면 디자인 시스템 기준을 따른다(7번 선행 확인 3).
- 등급 라벨 정의: `backend/app/services/return_intake_service.py:153~162` `CLOSING_REFLECTED_STOCK_LABELS`를 표시 라벨의 기준으로 삼는다(프론트에 같은 의미의 한글 라벨 매핑을 둔다). enum 원문은 화면에 노출하지 않는다.

## 5. 있어야 할 것 / 절대 없어야 할 것
- 있어야:
  - 재고상태 필터가 양품/리퍼A/리퍼B/리퍼C/샘플/제조사반품/폐기를 모두 한글 라벨로 선택할 수 있고, "전체"도 있다.
  - 모든 등급 행이 한글 라벨로 보인다(enum 원문 GOOD/REFURB_A 등 화면 비노출).
  - 같은 상품이라도 등급이 다르면 다른 줄로 분리되어 보인다(이미 `CurrentInventory`가 `stock_status`까지 unique이므로 데이터는 분리돼 있음).
  - 창고 미선택 시 같은 상품·같은 등급은 창고 전체 합산 수량으로 한 줄로 보인다. 창고 선택 시 그 창고 수치만 보인다. (현재 backend는 창고 미선택 시 창고별로 행을 나눠 주므로 합산 표시가 필요 — 7번 선행 확인 2.)
  - 판매가능(양품·리퍼·샘플)과 처분대기(제조사반품·폐기)가 시각적으로 구분된다(그룹 배지/색/구분).
  - 합산/단일 어느 모드인지 화면에서 알 수 있는 안내(예: "창고 전체 합산" vs "○○창고 재고").
- 없어야:
  - 재고 수치를 바꾸는 어떤 로직/액션(반영, 조정, 가감, 마감, 반출, 폐기 확정). 이 화면은 조회 전용이다. **재고 계산/반영 로직 변경 금지.**
  - 일마감/외부반출/폐기 확정 등 확정 단계 액션(다른 슬라이스 몫).
  - 적출/교환 부품의 재고 표시. 부품적출/부품교체는 1차 `MEMO_ONLY` 처리 이력(메모/스토리)이며 재고 행으로 보여주지 않는다. 이 화면 범위 밖.
  - 등급→재고구분 매핑이나 그룹 분류를 backend 재고 계산에 새로 하드코딩하는 것(표시용 라벨/그룹 매핑은 프론트 표시 레이어에만 둔다).
  - 고객사 포털 노출(이 슬라이스는 내부 화면 보강만; 포털은 선행 확인 후 별도 슬라이스).
  - 재고 이벤트 상세 이력(`/inventory/events` 화면 몫).

## 6. 완료기준 (사용자가 화면에서 직접 확인하는 체크리스트)
- [ ] 1) 창고를 선택하지 않고 조회하면, 같은 상품의 양품·리퍼B 등 각 등급이 여러 창고 수량을 합한 값으로 한 줄씩 보인다.
- [ ] 2) 특정 창고를 선택해 조회하면, 그 창고에 있는 수량만 보이고 다른 창고 수량은 섞이지 않는다.
- [ ] 3) 같은 상품이라도 등급이 다르면(예: 양품과 리퍼B) 서로 다른 줄로 보이고 하나로 합쳐지지 않는다.
- [ ] 4) 모든 등급이 한글(정상재고/리퍼A 재고/리퍼B 재고/리퍼C 재고/샘플 재고/제조사반품 재고/폐기 재고)로 보이고, GOOD·REFURB_A 같은 영어 코드가 화면에 그대로 보이지 않는다.
- [ ] 5) 판매가능(양품·리퍼·샘플)과 처분대기(제조사반품·폐기)가 한눈에 구분된다(색/배지/구분선 등).
- [ ] 6) 재고상태 필터에서 "리퍼B"만 골라 조회하면 리퍼B 등급 줄만 보인다. "전체"로 두면 모든 등급이 보인다.
- [ ] 7) 화면 어디에도 재고를 바꾸는 버튼(반영/조정/마감/반출/폐기)이 없다. 조회·새로고침·초기화만 있다.
- [ ] 8) 지금 보는 게 "창고 전체 합산"인지 "특정 창고 재고"인지 화면 안내로 알 수 있다.

## 7. 리스크 / 보류(HOLD) 케이스
- 선행 확인 1 (포털 노출): 권한 시드 정책(`docs/business/smartreturn-pro-role-permission-seed-policy.md`)상 `INVENTORY_VIEW`는 `CLIENT_ADMIN`/`CLIENT_USER`/`READ_ONLY`에 "후보"로만 표기돼 있고 확정 노출이 아니다. 또 현재 `/inventory/current` route는 내부 레이아웃(`MainLayout`)에 있고 별도 포털 화면이 없다. → 고객사가 자기 폐기/제조사반품 처분대기 재고까지 봐도 되는지는 정책 미확정. 이 슬라이스는 내부 화면 보강만 진행하고, 포털 노출 여부는 구현 전 사용자/아키텍트 확인 후 별도 슬라이스로 분리한다.
- 선행 확인 2 (창고 전체 합산 — 가장 중요): 현재 backend `list_current_inventory`는 `warehouse_id` 미지정 시 권한 범위 내 모든 창고 행을 그대로 반환하며, 같은 상품·같은 등급이라도 **창고별로 행을 나눠 준다(합산하지 않음)**. `CurrentInventory`의 unique 키에 `warehouse_id`가 포함되기 때문이다. 따라서 완료기준 1·8의 "창고 전체 합산"을 만족하려면 합산 처리가 필요하다. 두 가지 접근이 있다:
  - (a) backend에 합산 모드 추가(`warehouse_id` 미지정 시 `client_id`+`product_id`+`stock_status`로 `SUM(qty_on_hand)` group by). 단 이러면 응답에서 `warehouse_code`/`warehouse_name`/`inventory_id`/`updated_at`이 단일값으로 떨어지지 않으니 응답 스키마/표시 처리 보완 필요.
  - (b) 프론트에서 현재 page 결과를 클라이언트 측 합산. 단 현재 화면은 `pageSize: 300`으로 한 페이지만 받으므로 창고/상품이 많으면 합산이 잘릴 위험이 있다(정확도 문제).
  → 어느 방식으로 "전체 합산"을 구현할지(특히 backend 합산 추가 여부와 합산 시 창고 칸 표기 방식)는 구현 전 사용자/아키텍트 확정 필요. 정확도상 (a) backend 합산이 권장되나 응답 스키마 변경을 동반하므로 단순 표시 슬라이스 범위를 넘는지 함께 판단한다. 합산 미확정이면 합산 대신 "창고별 행 + 창고 선택 안내"로 1차 출시하고 합산은 후속(HOLD)으로 둘 수 있다.
- 선행 확인 3 (등급 라벨/그룹 출처): 표시 라벨은 `CLOSING_REFLECTED_STOCK_LABELS`(서버 상수)를 기준으로 하되, 화면 표시용으로 프론트에 같은 의미의 한글 매핑을 두는 게 맞는지(프론트 하드코딩 vs 공통코드 조회) 확인 필요. "판매가능/처분대기" 2그룹 분류 기준(어떤 stock_status가 어느 그룹인지)도 공통코드/마스터에서 받아야 하는지, 표시 레이어 매핑으로 충분한지 확정 필요. 재고 계산에는 절대 하드코딩하지 않는다.
- 선행 확인 4 (조회 정렬/페이지): 등급 정렬은 현재 `stock_status` 알파벳순(`order_by`)이라 GOOD→REFURB_A→...→SAMPLE 순서가 "판매가능 먼저, 처분대기 나중" 같은 업무 순서와 다를 수 있다. 표시 정렬을 업무 순서로 보정할지(프론트 표시 정렬) 확인 필요. 재고 수치에는 영향 없음.
- HOLD: 적출/교환 부품 재고화는 명시적으로 이 화면 범위 밖이다. 부품이 재고관리 대상으로 확장될 때 별도 슬라이스로 다룬다.

---
이 스펙은 사용자 승인(게이트 ②) 후 구현한다. 승인 전 구현/커밋 금지.
