# 105 보고 - 고객 포털 권한 표시 / 403 처리 UX 정리 + Fable 변경분 검수

## 한줄 결론
직전 백엔드 커밋 `d2f5cacb`(고객 반품 권한 분리)를 기준으로 고객 포털 조회 화면의 권한 인지·403 UX를 정리했다. backend 무수정. build 통과. 브라우저 사용자 테스트 가능 상태.

## 백엔드 기준 확인 (읽기 전용, 수정 안 함)
- `/api/returns/history`는 인증만 요구하고 권한은 service `_require_return_view`(`RETURN_VIEW`)로 강제.
- seed(`roles_permissions.py`): `CLIENT_ADMIN`/`CLIENT_USER` = `RETURN_VIEW` + `RETURN_CLIENT_SUBMIT` 보유 → 고객 포털 조회/접수 가능.
- 고객 role에는 RETURN_PREPARE/처리/마감/외부반출 권한 없음 → 해당 API는 backend 403.
- `resolve_effective_client_id`: 고객 사용자는 자기 client_id 고정, 타 고객사 요청 시 `ClientScopeDeniedError`(403).
- 결론: 프론트는 UX 정리만 하면 되고, 보안은 backend가 강제(프론트 숨김 단독 의존 아님).

## 변경 파일 (frontend만)
- 수정: `frontend/src/pages/portal/PortalReturnStatusPage.tsx`
  - `hasPermission("RETURN_VIEW")` 기반 `canViewReturns` 도입.
  - 권한 없으면 요청을 보내지 않고 화면 내 경고(Alert)로 안내(모달 아님, 화면 안 깨짐).
  - 403 메시지 정리: 백엔드 사유가 있으면 그대로 노출, scope 차단(result_code SCOPE/CLIENT)은 "다른 고객사 데이터 접근 불가"로 구분, 그 외 일반 권한 안내.
- (이전 단계에서 생성/연결, 이번에 함께 검수) `frontend/src/pages/portal/PortalReturnStatusPage.tsx`(신규 화면), `routePaths.ts`(`portalReturnStatus`), `router.tsx`(`/portal/returns` 등록), `PortalLayout.tsx`(메뉴 "반품 처리현황" 활성화).

## 목표 대비 결과
1. 고객 로그인 → OK(기존 흐름).
2. 고객 포털 진입 → OK(`PortalLayout`, `area="portal"`).
3. 고객 포털 반품 조회 접근 → OK(`RETURN_VIEW` 보유, `/portal/returns`). (접수 업로드 화면은 "준비중" disabled — 이번 범위 밖, "또는 조회"로 충족.)
4. 내부 처리/판정/마감/반출 액션 비노출/비실행 → OK. PortalLayout에 해당 액션 없음 + 내부 화면은 `area="internal"` 가드로 고객 사용자 차단(포털로 리다이렉트) + backend 권한 403.
5. 권한/scope 차단 시 화면 안 깨지고 명확 안내 → OK. RETURN_VIEW 없음=화면 내 Alert, 403/scope=사유 노출 SmartErrorNotice. 모달 미사용.
6. 내부/포털 메뉴·레이아웃 분리 → OK. MainLayout(internal) vs PortalLayout(portal), RouteGuard area 분리.

## Fable 변경분 검수
- 기존 라우팅/권한 구조와 충돌 없음. 신규 라우트는 portal children에 정상 편입, area 가드 일관.
- 신규 디자인 시스템/대형 리팩터링 없음. 기존 공통 컴포넌트(SmartPage/SmartDataGrid/SmartErrorNotice/SmartStatusBadge/SmartSummaryCard) 재사용.
- 조회 전용 유지(쓰기 버튼 없음). 하드코딩 client_id/판정/상태 없음.

## 검증
- `npm run build`(tsc --noEmit + vite build): 통과 (3104 modules, 15.28s).
- `git diff --check`: clean.
- 민감파일 점검: 금지 정보 원문 없음.
- backend 파일 변경: 없음.

## 브라우저 검증 결과 (실측, 똘망이/Playwright)
- 환경: backend 8000 `/health` ok, frontend 5173 200.
- 계정: CLIENT_ADMIN 테스트 계정 / [REDACTED_PASSWORD]
- 로그인 → `/portal/dashboard` 자동 진입 (목표 1·2 통과).
- `/portal/returns` 진입 → 화면 렌더, 자기 고객사 데이터 2건 표시 (목표 3 통과).
- 고객사 Select 미노출(고객 고정), 필터(판정/처리상태/운송장/반품관리/키워드/기간) 정상.
- 내부 처리/판정/마감/반출 버튼 없음. 액션은 새로고침/조회/초기화/엑셀 다운로드/셀 복사뿐 (목표 4 통과).
- 운송장/반품관리번호/상품코드/바코드 "셀 값 복사" 버튼 표시 (복사 정책 준수).
- 포털 전용 메뉴만 노출, 내부 운영자 메뉴 없음, 준비중 항목은 disabled (목표 6 통과).
- 콘솔 error 0건(포털 페이지 기준).
- **scope 강제 실측**: 같은 인증 세션으로 API 직접 호출 시
  - `GET /api/returns/history` → 200, items 2 (자기 고객사)
  - `GET /api/returns/history?client_id=999999` → **403 `CLIENT_SCOPE_DENIED`**
  - 즉, 프론트 숨김이 아니라 backend가 실제 차단. 프론트 403 UX는 이 result_code에 매핑됨 (목표 5 통과).
- 확인불가: RETURN_VIEW 미보유 계정의 화면 내 권한 안내(전용 계정 없음) → 코드/build로만 검증.

## 브라우저 사용자 테스트 절차 (backend 8000 기동 후)
1. 고객 계정(예: ESPMARKETING)으로 로그인 → 자동으로 포털 진입.
2. 좌측 "반품 > 반품 처리현황" → `/portal/returns`. 고객사 Select 숨김, 그리드/필터 표시, 0건 안내 확인.
3. 내부 계정(ahgoon)으로 포털 미리보기 진입 시 고객사 Select 노출 확인.
4. (권한 차단 UX) RETURN_VIEW 없는 계정이 있으면 화면 내 경고 표시 확인.
5. 운송장/상품코드/바코드/반품관리번호 복사, 콘솔 에러 없음, 1366x768 비파손.

## 남은 위험 / Codex 검수 필요
- 고객 사용자 client_id scope 교차조회 차단을 backend 통합테스트로 1건 확인 권장.
- (선택) 판정/상태 한글 라벨이 화면별 중복 정의(공통 formatter 부재, R5 유형) → 추후 공통화.
- 고객 포털 "반품 접수 등록" 화면은 미구현(준비중). RETURN_CLIENT_SUBMIT 경로 UI는 별도 작업 필요.

## 커밋 필요 여부
- 사용자 승인 후 frontend만 커밋. backend 무관.
- 추천 메시지: `feat(portal): add customer return status screen with permission-aware 403 ux`
