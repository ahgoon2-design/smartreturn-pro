# 102 - 고객포털 처리현황 화면 사전 점검(설계만)

## 목표
화면 제작 전 기존 route/파일/API/컴포넌트를 확인해 조회형 화면만으로 가능한지 판단.

## 담당 작업
- 설계/점검만. 앱 코드 수정 금지.

## 사전 조건
- 브랜치 smartreturn-pro, 코드 검색 가능.

## 실행 범위 / 확인할 것
- [ ] 고객포털 처리현황 route 존재 여부(`routePaths.ts`, `router.tsx`, PortalLayout 메뉴)
- [ ] 기존 화면 파일 존재 여부(`features/portal/` 등)
- [ ] 내부 반품 이력/처리현황 API 재사용 가능 여부(`/api/returns/history` client_id 필터)
- [ ] 고객 사용자=자기 client_id만 조회되는지(서버 scope 강제)
- [ ] 내부 사용자 포털 미리보기 접근 가능(RouteGuard area=portal)
- [ ] AppShell(PortalLayout)/RouteGuard/AuthContext 충돌 없음
- [ ] 재사용 후보: SmartPage/PageHeader/Toolbar/DataGrid(+copyable/exportFileName)
- [ ] 운송장/상품코드/바코드/반품관리번호 copyable, 엑셀 다운로드 필요 여부
- [ ] 저장/수정 버튼 불필요(조회 전용으로 제한)

## 중단 조건
- route/API 불명확 + 대규모 backend 수정 필요 → 중단
- 권한/seed/backend guard 수정 필요 → 이번 큐 중단·보고
- 새 DB 테이블 필요 → 중단

## 보고 위치
- `ai-harness/reports/102-customer-portal-status-plan-report.md`

## 다음 지시문
- 조회형 제작만으로 가능 → `103-customer-portal-status-build.md`
- backend 권한 수정 필요 → 중단
