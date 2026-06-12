# 102 보고 - 고객포털 처리현황 사전 점검(설계)

## 결론: 조회형 화면 신규 제작으로 가능. backend 수정 불필요. → 103 진행.

## 확인 결과
- **route**: `routePaths.ts`에 portal은 `portalHome(/portal)`, `portalDashboard(/portal/dashboard)`만 존재. 처리현황 route 없음.
- **화면 파일**: `pages/portal/`에 `PortalDashboardPage.tsx`만 존재. 처리현황 화면 없음 → 신규 필요.
- **재사용 API**: `listReturnHistory()` → `GET /api/returns/history`. 옵션에 clientId/dateFrom/dateTo/keyword/trackingNo/returnManagementNo/judgementStatus/status/followupStatus/page/pageSize 모두 존재 → 검색 요구 전부 충족.
- **데이터 타입**: `ReturnHistoryItem`에 운송장/주문/상품코드/상품명/바코드/판정/작업상태/반품관리번호/후속상태(label 포함)/일자(created_at, judged_at)/창고(recommended·final_warehouse_id) 모두 존재 → 그리드 요구 충족.
- **scope**: history API는 서버에서 client 범위 강제(고객 사용자=자기 client_id). 화면에서 우회 안 함.
- **권한 분기**: AuthContext에 `isClientUser`, `canSelectClient`(internal/agency) 노출 → 고객 고정 사용자는 고객사 선택 숨김, 내부/대리점 미리보기는 선택 가능.
- **미리보기 접근**: portal route는 `ProtectedRoute area="portal"`. 내부 사용자 진입 가능(RouteGuard 확인 예정, 103에서 라우트 등록 시 점검).
- **재사용 컴포넌트**: SmartPage/SmartPageHeader/SmartDataGrid(copyable+exportFileName)/SmartStatusBadge/SmartSummaryCard/SmartErrorNotice — 내부 `ReturnHistoryPage.tsx`가 사실상 동일 패턴이라 이를 미러링.
- **copyable/엑셀**: 운송장/주문/상품코드/바코드/반품관리번호 copyable, exportFileName으로 엑셀 다운로드 적용 예정.
- **저장 버튼**: 불필요. 조회 전용으로 제한.

## 중단 조건 해당 없음
- 대규모 backend 수정/권한·seed·guard 수정/새 DB 테이블 → 모두 불필요.

## 제작 계획(103)
- 신규 `pages/portal/PortalReturnStatusPage.tsx`(또는 features/portal) — `ReturnHistoryPage` 조회형 미러 + 기간 필터 추가 + 고객 고정 시 고객사 선택 숨김 + exportFileName.
- 신규 route `portalReturnStatus: "/portal/returns"`, router.tsx portal children에 등록, PortalLayout 메뉴 추가.
- 앱 코드 수정은 103에서만.
