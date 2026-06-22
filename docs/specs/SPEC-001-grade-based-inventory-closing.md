# 슬라이스 스펙: 등급별 재고 마감반영

> ⚠️ [폐기·대체] 이 슬라이스의 전제(폐기·제조사반품 재고반영 제외)는 코드 확인 결과 불필요로 판명. 현재 코드가 stock_status별 분리 적재로 판매가능 재고 혼입을 구조적으로 방지함(decision-log D-003 참조). 재고현황 표시 요구는 신규 SPEC으로 대체. 본문은 이력 보존용.
> ✅ 대체 완료: 이 영역의 재고반영 정책은 SPEC-004에서 A안으로 확정됐다(2026-06-22). 본 내용은 SPEC-004로 대체된다.

## 1. 한 줄 목적
반품 일마감을 확정할 때, 판정 등급(양품/리퍼A/리퍼B/리퍼C/샘플)별로 현재고를 서로 합산되지 않게 분리해서 반영한다.

## 2. 사용자 / 권한 scope
- 누가 쓰나(role): 내부 운영자만. `SUPER_ADMIN`, `INTERNAL_ADMIN`, `INTERNAL_WORKER`, `AGENCY_ADMIN`. (현재 `_require_return_close`가 `RETURN_INTERNAL_OPERATION_ROLES`로 이 4개 role만 허용하고 `RETURN_CLOSE` 권한을 강제한다.)
- 권한: `RETURN_CLOSE`. 읽기전용 사용자는 마감 확정 불가.
- scope: `agency_id` + `client_id` + `warehouse_id` 필수.
  - `client_id` scope는 `resolve_effective_client_id`로 row마다 재검증한다.
  - `warehouse_id`가 확정되지 않은(고객사 기본 반품/입고 창고 설정이 없는) row는 재고반영을 하지 않고 실패로 남긴다.
- 내부 / 포털 구분: 내부 전용 화면. 고객사 포털(`CLIENT_ADMIN`/`CLIENT_USER`)에는 이 마감/재고반영 액션을 노출하지 않는다.

## 3. 화면에서 하는 일 (흐름)
1. 내부 운영자가 반품 일마감 화면(`/returns/closing`)에서 고객사/판정상태/기간으로 일마감 후보를 조회한다.
2. 그리드에서 마감할 row를 선택한다. row에는 판정 등급(양품/리퍼A/B/C/샘플)이 표시된다.
3. "마감 확정"을 실행하면 backend가 row별로 재고반영 가능 여부를 재검증한다(판정완료 상태인지, 수량이 있는지, 상품 마스터가 있는지, 창고가 확정됐는지).
4. 재고반영 대상인 보관 등급 row는 해당 등급의 재고 칸으로 +수량 반영된다. 같은 상품·같은 창고라도 양품/리퍼A/리퍼B/리퍼C/샘플은 각각 별도 재고 행으로 쌓인다.
5. 결과 요약(반영/건너뜀/실패/후속처리 건수)과 row별 결과가 화면에 표시된다.

## 4. 재사용할 기존 자산 (먼저 확인 후 채움)
- route: `frontend/src/routes/router.tsx`의 `returns/closing` → `ReturnClosingPage`, 경로 상수 `routePaths.returnClosing = "/returns/closing"`.
- 화면: `frontend/src/features/returns/ReturnClosingPage.tsx` (현재 미커밋 수정 상태). 판정상태 필터에 `REFURB`까지 옵션이 있고, 그리드는 `judgement_status` 컬럼을 표시한다. 현재 안내문(258행)에 "기본은 GOOD/양품만 반영합니다. 리퍼/샘플/제조사반품/폐기는 ... 포함하세요." 문구가 있다 — 이 슬라이스에서 폐기/제조사반품 제외 경계에 맞게 문구를 정리할 필요가 있다(7번 선행 확인 참조).
- API:
  - `GET /returns/closing/candidates` → `list_return_closing_candidates` (`backend/app/routers/returns.py` 339행, `backend/app/services/return_intake_service.py` 1552행)
  - `POST /returns/closing/confirm` → `confirm_return_closing` (`backend/app/routers/returns.py` 367행, service 1589행)
- 판정 상수 / 재고반영 대상 집합 (service 98~180행, 사실 그대로):
  - 판정값: `JUDGEMENT_GOOD="GOOD"`, `JUDGEMENT_REFURB="REFURB"`, `JUDGEMENT_REFURB_A="REFURB_A"`, `JUDGEMENT_REFURB_B="REFURB_B"`, `JUDGEMENT_REFURB_C="REFURB_C"`, `JUDGEMENT_SAMPLE="SAMPLE"`, `JUDGEMENT_MANUFACTURER_RETURN="MANUFACTURER_RETURN"`, `JUDGEMENT_DISPOSAL="DISPOSAL"`, 그 외 `HOLD`/`DEFECTIVE`.
  - `INVENTORY_REFLECTABLE_JUDGEMENT_STATUSES` (141행)는 현재 GOOD, REFURB, REFURB_A/B/C, SAMPLE **그리고 MANUFACTURER_RETURN, DISPOSAL까지 포함**한다. 즉 현재 코드는 폐기/제조사반품 판정 row도 일마감 화면에서 재고반영 대상으로 본다. → 이 슬라이스가 바로잡아야 할 핵심 지점이다(5번/7번 참조).
- 재고반영 로직 (service 1704~1769행, 사실 그대로):
  - 이미 등급 분기는 부분적으로 구현돼 있다. `stock_status = row.judgement_status` 로 두고, `event_type`만 GOOD이면 `RETURN_GOOD_IN`, 아니면 `RETURN_JUDGEMENT_IN`으로 나눈다. 단일 InventoryEvent를 생성하고 `inventory_repository.increase_current_inventory(... stock_status=stock_status ...)`로 현재고를 올린다.
  - `idempotency_key = f"return-closing:{row.id}:{stock_status.lower()}"` 형식(예: `return-closing:1234:refurb_b`). 동일 키 이벤트가 이미 있으면 중복 반영하지 않고 SKIPPED 처리한다.
- 모델 (`backend/app/models/inventory.py`):
  - `InventoryEvent.stock_status` (String(50), not null) — 등급별 재고 원장 키.
  - `CurrentInventory`는 `UniqueConstraint(client_id, warehouse_id, location_id, product_id, stock_status)`로 등급(`stock_status`)까지 포함해 현재고를 분리 저장한다. 즉 등급별 분리 저장 구조는 DB에 이미 있다.
- 공통 컴포넌트: 화면은 기존 `SmartDataGrid` / `SmartPage` 계열 + `SmartCommonCodeSelect`(판정상태 필터) 재사용. 새 그리드/새 모달을 만들지 않는다.

## 5. 있어야 할 것 / 절대 없어야 할 것
- 있어야:
  - 보관 등급(양품/리퍼A/리퍼B/리퍼C/샘플) row를 마감 확정하면 해당 등급 재고 칸에 +수량으로 반영된다.
  - 같은 상품·같은 창고라도 등급이 다르면 현재고가 합산되지 않고 각각의 재고 행으로 분리된다(이미 `CurrentInventory`가 `stock_status`까지 unique).
  - 같은 row를 두 번 확정해도 등급별 재고가 중복으로 늘지 않는다(idempotency_key로 차단, 두 번째는 건너뜀 처리).
  - `warehouse_id`가 확정되지 않은 row, 수량이 없는 row, 상품 마스터를 못 찾는 row는 재고반영하지 않고 실패/사유와 함께 결과에 남긴다.
  - 화면 결과 요약에 등급별로 어떤 재고에 반영됐는지 사람이 읽을 수 있는 문구로 보여준다(예: "리퍼B 재고에 반영했습니다").
- 없어야:
  - 폐기(`DISPOSAL`) 판정 row는 이 화면에서 재고로 쌓이면 안 된다. 폐기 처리는 외부반출/폐기 확정 단계의 몫이다. → 현재 `INVENTORY_REFLECTABLE_JUDGEMENT_STATUSES`에 `DISPOSAL`이 들어있어 반영되는 상태이므로 이 슬라이스에서 제외하도록 바로잡아야 한다.
  - 제조사반품(`MANUFACTURER_RETURN`) 판정 row도 이 화면에서 보관 재고로 쌓이면 안 된다. 제조사반품은 외부반출(EXTERNAL_OUTBOUND) 흐름의 몫이다. → 현재 reflectable 집합에 포함돼 있어 동일하게 바로잡아야 한다.
  - 보류(`HOLD`)/불량(`DEFECTIVE`) 판정 row의 재고반영(이 슬라이스 밖, HOLD 관리 화면 몫).
  - 판정 즉시 재고변경(원칙상 금지). 재고는 일마감 확정 단계에서만 반영한다.
  - 등급→재고구분 매핑이나 반영대상 등급을 화면/코드에 새로 하드코딩하는 것. 등급값/매핑은 기존 판정 상수와 고객사별 판정-창고 라우팅 기준을 따른다.
  - 폐기 재고처리, 제조사반품 외부반출, 월마감, 부품적출 재고화 — 모두 이 슬라이스 밖.

## 6. 완료기준 (사용자가 화면에서 직접 확인하는 체크리스트)
- [ ] 1) 리퍼B로 판정된 반품 1건(수량 1, 창고 확정)을 일마감 확정하면, 재고현황에서 그 상품의 "리퍼B" 재고가 +1 된다.
- [ ] 2) 같은 상품·같은 창고에 양품 1건과 리퍼B 1건을 각각 마감하면, 재고현황에 "양품 1"과 "리퍼B 1"이 별도 줄로 보이고 하나로 합산되지 않는다.
- [ ] 3) 리퍼A·리퍼C·샘플 판정 row도 각각 마감하면 그 등급 재고로만 +수량 반영되고, 다른 등급과 섞이지 않는다.
- [ ] 4) 방금 마감 확정한 같은 row를 한 번 더 확정해도 그 등급 재고가 추가로 늘지 않고, 화면 결과에 "이미 반영됨/건너뜀"으로 표시된다.
- [ ] 5) 폐기 판정 row를 골라 마감을 시도해도 어떤 등급 재고도 늘지 않는다(이 화면에서 폐기는 재고로 쌓이지 않음).
- [ ] 6) 제조사반품 판정 row를 골라 마감을 시도해도 어떤 등급 재고도 늘지 않는다(외부반출 단계로 넘어가야 함).
- [ ] 7) 창고가 확정되지 않은 row를 마감하려 하면 재고가 늘지 않고, 화면에 "창고 설정이 없어 재고반영할 수 없습니다" 같은 실패 사유가 보인다.
- [ ] 8) 고객사 포털 로그인(고객사 사용자)에는 이 일마감/재고반영 화면·버튼이 보이지 않는다.

## 7. 리스크 / 보류(HOLD) 케이스
- 선행 확인 1 (가장 중요): 현재 `INVENTORY_REFLECTABLE_JUDGEMENT_STATUSES`(service 141~150행)에 `JUDGEMENT_DISPOSAL`, `JUDGEMENT_MANUFACTURER_RETURN`이 포함돼 있어, 지금 코드는 폐기/제조사반품 판정 row도 일마감 화면에서 재고로 반영한다. 이 슬라이스의 제외 경계(완료기준 5·6)를 지키려면 이 집합에서 두 값을 제거해야 한다. 단, 이 집합은 다른 흐름(예: `_closing_candidate_response`의 `is_reflectable` 표시, candidate 조회)에서도 참조되므로(514행 등), 제거 시 일마감 후보 표시/외부반출 흐름에 부작용이 없는지 구현 전 확인 필요. → 구현 전 사용자/아키텍트에게 "폐기·제조사반품을 일마감 재고반영 대상에서 제외해도 외부반출 흐름이 정상인지" 확인 질문할 것.
- 선행 확인 2: `JUDGEMENT_REFURB`(등급 없는 "리퍼")가 reflectable에 포함돼 있다. 이 슬라이스의 보관 등급은 양품/리퍼A/B/C/샘플로 명시됐는데, 등급 미지정 `REFURB`를 그대로 별도 재고로 둘지, 리퍼A로 강제할지, 마감 불가로 막을지 정책 확인 필요. (`ReturnClosingPage`의 판정상태 필터 옵션에 `REFURB`가 존재함.) → 정책 미확정 시 `REFURB`는 이 슬라이스에서 건드리지 말고 현행 유지(HOLD)로 남긴다.
- 선행 확인 3: 화면 안내문(`ReturnClosingPage.tsx` 258행)이 "리퍼/샘플/제조사반품/폐기는 ... 포함하세요"라고 안내하는데, 제외 경계와 어긋난다. 폐기/제조사반품은 이 화면 대상이 아님을 명확히 하도록 문구 정리 필요(현장 작업자에게 enum/개발자 용어 노출 금지 원칙도 함께 확인).
- 선행 확인 4: 등급별 `warehouse_id`는 고객사별 판정-창고 라우팅 설정에서 와야 한다. 현재 `_resolve_final_return_warehouse`가 등급별로 올바른 창고를 돌려주는지(특히 리퍼/샘플이 양품과 다른 창고로 가야 하는 고객사) 구현 전 확인 필요. 창고 미확정 row는 절대 재고반영하지 않는다.
- 보류(HOLD)/불량(DEFECTIVE) 판정은 보관 등급이 아니므로 이 슬라이스에서 재고반영하지 않는다(별도 HOLD 관리 화면 몫).
- 수량 차이·상품 불일치 등 위험 row는 자동 반영하지 말고 실패/후속처리로 분리해 남긴다(자동 확정 금지 원칙).

---
이 스펙은 사용자 승인(게이트 ②) 후 구현한다. 승인 전 구현/커밋 금지.
