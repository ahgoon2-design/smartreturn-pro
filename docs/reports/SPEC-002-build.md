# 빌드 보고서: SPEC-002 재고현황 stock_status별 구분 표시
> 게이트 ③ 산출물. 구현자(Claude Code) 작성. 스펙: docs/specs/SPEC-002-inventory-status-by-stock-status.md

## 1. 결과
통과 (backend test 92 passed / frontend build 통과 / diff --check clean). 커밋은 하지 않음(게이트④·⑤ 대기).

## 2. 구현 범위
- 한 줄 요약: 재고현황을 stock_status(재고등급)별로 보여주고, 창고 미선택 시 product_id+stock_status로 창고 전체 합산 조회를 추가했다. 재고 계산/반영(입고/출고/마감) 로직은 변경하지 않음(순수 조회).
- 게이트② 확정값 반영: (1) 내부 화면만 (2) backend 합산 조회 추가 (3) 한글/2그룹 프론트 표시 매핑 단일 출처 (4) 업무순 정렬.

## 3. 변경 파일
| 파일 | 변경 내용 |
| --- | --- |
| backend/app/schemas/inventory.py | CurrentInventoryItemResponse의 inventory_id/warehouse_id/updated_at를 Optional로, warehouse_count 추가. ListResponse에 aggregated 플래그 추가. |
| backend/app/repositories/inventory_repository.py | list_current_inventory_aggregated 신규: client_id+product_id+stock_status로 SUM(qty_on_hand)+COUNT(DISTINCT warehouse_id) 합산 조회. 기존 list_current_inventory(창고별)는 미변경. |
| backend/app/services/inventory_service.py | list_current_inventory에서 warehouse_id 미지정 시 합산 조회, 지정 시 기존 창고별 조회로 분기. aggregated 플래그 세팅. 재고 변경 로직 없음. |
| backend/tests/test_inventory_current_api.py | 신규 테스트 3종(합산 정확/창고별 회귀/등급필터). |
| frontend/src/features/inventory/stockStatus.ts | 신규. 등급 라벨·2그룹·업무순 정렬 표시 단일 출처(표시 레이어 전용, backend 계산에 하드코딩 아님). |
| frontend/src/features/inventory/CurrentInventoryPage.tsx | 재고상태 필터 7등급+전체, 한글 라벨, 구분(판매가능/처분대기) 컬럼·tone, 업무순 정렬, 합산/단일 안내 Alert, 합산 행 창고 표기(전체 N개 창고), 요약 카드(판매가능/처분대기 수량), 엑셀 다운로드 파일명. |
| frontend/src/types/inventory.ts | CurrentInventoryItem: inventory_id/warehouse_id/updated_at Optional, warehouse_count 추가. |
| frontend/src/components/common/SmartStatusBadge.tsx | 선택적 tone prop 추가(2그룹 색 구분용, 기존 동작 보존). |

## 4. 스펙 완료기준 항목별 충족/미충족
| # | 완료기준 | 충족/미충족 | 근거 |
| --- | --- | --- | --- |
| 1 | 창고 미선택 시 등급별 창고 전체 합산 한 줄 | 충족 | service 합산 분기 + repo SUM. test_aggregated_when_warehouse_not_selected(GOOD 5+3=8, warehouse_count=2) |
| 2 | 특정 창고 선택 시 그 창고만 | 충족 | 기존 창고별 경로 보존. test_per_warehouse_when_warehouse_selected_no_aggregation(WH1 GOOD=5만) |
| 3 | 같은 상품 등급 다르면 다른 줄(미합산) | 충족 | group by stock_status. 위 테스트에서 GOOD/REFURB_B/DISPOSAL 3행 분리 |
| 4 | 모든 등급 한글, 영어 코드 비노출 | 충족(육안 확인 ④/⑤) | stockStatusLabel로 라벨화, 구분/재고상태 컬럼 한글. build 통과 |
| 5 | 판매가능 vs 처분대기 한눈 구분 | 충족(육안 확인 ④/⑤) | "구분" 컬럼 group badge + tone(success/warning) + 요약 카드 2그룹 |
| 6 | 재고상태 필터 단일등급/전체 | 충족 | 필터 옵션 7등급+전체, backend stock_status 필터. test_stock_status_filter_in_aggregated_mode(GOOD=8) |
| 7 | 재고 바꾸는 버튼 없음(조회 전용) | 충족 | 화면에 조회/새로고침/초기화만. 재고 변경 로직 미추가 |
| 8 | 합산/단일 화면 안내 | 충족(육안 확인 ④/⑤) | loadedWarehouseId 기반 안내 Alert("창고 전체 합산 보기"/"특정 창고 보기") |

## 5. 실행한 검증
- git status --short: 변경 파일 확인(아래 6 외 신규/수정)
- git diff --check: clean (LF/CRLF 경고만, 본 슬라이스 파일 아님)
- backend test: `backend/.venv/Scripts/python.exe -m pytest tests/test_inventory_current_api.py tests/test_return_intake_api.py tests/test_closing_reflected_message.py tests/test_db_models_import.py -p no:cacheprovider` → 92 passed (신규 3 포함, 회귀 없음)
- frontend build: `npm.cmd run build`(tsc --noEmit + vite) → 통과, 3110 modules, exit 0

## 6. 미실행 / 확인 필요
- 브라우저 육안 확인(완료기준 4·5·8 시각 요소)은 게이트④/⑤에서. 로컬 DB 합산용 다창고 데이터가 없으면 화면 합산은 데이터 의존.
- frontend build의 chunk>500kB 경고는 기존부터 있던 전역 경고(이 슬라이스와 무관).

## 7. 남은 위험 / 다음 작업 제안
- 합산 모드 keyword 검색은 창고 조인이 없어 고객사/상품/바코드만 검색(창고명 검색 제외) — 합산 모드 특성상 의도된 동작이나 검수 시 확인 권장.
- 합산 정렬은 backend 안정 정렬 + frontend 업무순 재정렬. pageSize 300 한 페이지 기준(대량 데이터 페이지네이션은 후속).
- 포털 노출은 범위 밖(별도 슬라이스).

## 8. 커밋 후보 (선별 add 대상)
- backend/app/schemas/inventory.py, backend/app/repositories/inventory_repository.py, backend/app/services/inventory_service.py
- backend/tests/test_inventory_current_api.py
- frontend/src/features/inventory/stockStatus.ts, frontend/src/features/inventory/CurrentInventoryPage.tsx
- frontend/src/types/inventory.ts, frontend/src/components/common/SmartStatusBadge.tsx
- docs/reports/SPEC-002-build.md
(주의: git add . 금지. 커밋은 사용자 인수 후 Codex가 선별 add. 본 슬라이스 무관 변경분은 제외.)
