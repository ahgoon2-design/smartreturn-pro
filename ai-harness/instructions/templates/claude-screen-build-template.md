# Claude 화면 제작 표준 지시문 템플릿

실행대상: Claude
보조: 똘망이(브라우저 검증)
검수 예정: Codex + 똘망이

> 시작 전 `<PROJECT_ROOT>/AGENTS.md`, `CLAUDE.md`를 읽는다. 브랜치 `smartreturn-pro`(SmartReturn Pro 라인) 기준. main 병합/동기화 제안 금지, push 금지, 커밋은 승인 전 금지.

## 1. 화면 목표
- (이 화면의 업무 목적 1개만 작성. 업로드/조회/처리/판정/설정을 한 화면에 섞지 않는다.)

## 2. 대상 route
- 예: `/returns/xxx` (routePaths.ts에 추가/사용할 키 명시)

## 3. 대상 파일 경로
- 예: `frontend/src/features/<domain>/<ScreenName>Page.tsx` (수정이면 기존 경로, 신규면 생성 경로를 지시문에 **반드시 명시** — 작업자가 다른 파일을 고르지 않게)

## 4. 기존 화면/컴포넌트 먼저 확인 (필수 선행)
- [ ] 같은 도메인 기존 화면 검색(`frontend/src/features/`) — 수정으로 충분한지 먼저 판단
- [ ] 공통 컴포넌트 확인: `SmartPage/SmartPageHeader/SmartToolbar/SmartActionBar/SmartDataSection/SmartModalShell/SmartScanPanel/SmartStatusBadge/SmartErrorNotice`, `SmartDataGrid`(+`exportFileName`/`enableCopy`)
- [ ] 그리드는 SmartDataGrid만 사용(AG Grid/antd Table 직접 사용 금지)

## 5. 새 컴포넌트 생성 전 재사용 후보 확인
- [ ] 고객사/창고/상품 선택이 필요하면 기존 화면 패턴 확인(현재 공통 `SmartClientSelect` 미구현 — 신규로 만들지 말고 기존 패턴 복제 최소화, 공통화 필요 시 보고)
- [ ] 새 공통 컴포넌트가 정말 필요하면 **만들기 전에 보고**(중복 구현 금지)

## 6. 권한/로그인/고객사/대리점 스코프 확인
- [ ] 이 화면의 사용 role 명시(SUPER_ADMIN/INTERNAL_ADMIN/INTERNAL_WORKER/AGENCY_ADMIN/CLIENT_ADMIN/CLIENT_USER/READ_ONLY 중)
- [ ] 내부/대리점=고객사 선택 가능, 고객=자기 client 고정(선택 UI 노출 금지)
- [ ] route 가드 area(internal/portal) 지정, 필요 permission을 `ProtectedRoute requiredPermissions`에 명시
- [ ] client_unit_id는 null 허용(세부 권한 미도입 — 임의 컬럼 추가 금지)

## 7. 저장 API payload 확인
- [ ] 사용할 API endpoint와 request schema(`backend/app/schemas/*.py`) 필드명을 **그대로**(snake_case) 사용
- [ ] client_id는 내부 사용자=선택값, 고객 사용자=서버가 강제(프론트에서 임의 주입 금지)
- [ ] payload에 client_id 누락 여부 확인(선택했는데 안 들어가는 케이스 금지)

## 8. backend guard ↔ frontend 버튼 노출 4종 세트 확인 (저장 기능 필수)
- [ ] ① BE `require_roles` 허용 role 확인 (`backend/app/services/*_service.py`)
- [ ] ② BE `require_permission` 코드 + seed(`app/seed/roles_permissions.py`)에 해당 role이 그 permission을 실제 보유하는지
- [ ] ③ FE 버튼 가드(`hasPermission(...)`)가 ①②와 **모순되지 않는지** (permission만 보고 role을 놓치면 "버튼 활성인데 403" 발생)
- [ ] ④ payload 필드명 = backend schema 필드명

## 9. 상태 처리 (빈/오류/차단)
- [ ] 빈 데이터: SmartDataGrid emptyText 또는 안내 카드(빈 흰 화면 금지)
- [ ] 권한 없음: 버튼 disabled+사유 또는 미노출(일관 규칙), 403/CLIENT_SCOPE_DENIED는 backend message 그대로 노출(일반 실패 문구로 덮지 않기)
- [ ] 저장 실패: `ApiClientError.message` 우선 표시
- [ ] 창고 라우팅 미설정 등 정책 차단: 차단 사유 안내(처리완료류 화면)
- [ ] loading state(spinner/disabled) 누락 금지

## 10. UI 기준
- [ ] 1366x768에서 핵심 입력 + 그리드 첫 5행 + 우측 패널 + 하단 액션바 노출
- [ ] 내부 enum/DB 필드명 화면 노출 금지(한글 라벨)
- [ ] 같은 안내문 반복 금지, 그리드가 주인공(카드가 밀어내면 실패)
- [ ] 조회형 그리드: `enableCopy` + `exportFileName`(엑셀 다운로드)

## 11. 검증 (필수)
- [ ] `npm --prefix frontend run build` (또는 typecheck)
- [ ] backend 변경 시 관련 pytest
- [ ] `git diff --check`, `git status --short`
- [ ] 미실행 검증은 "미실행"으로 보고(통과로 쓰지 않기)

## 12. 완료 보고 양식

> 최종 지시문은 하나의 text 코드블록으로 복사 가능해야 한다.
> 지시문 내부에는 코드펜스(backtick 3개 + 언어명) 같은 중첩 코드블록을 넣지 않는다.

아래 항목을 포함해 작성한다:

- [화면/route] / [변경 파일] / [재사용한 공통 컴포넌트] / [신규 생성 컴포넌트(사유)]
- [권한 4종 세트 확인 결과] / [상태 처리 확인] / [검증 결과(build/test/diff)]
- [미실행·수동 확인 필요] / [커밋 필요 여부(승인 전 금지)] / [다음: 똘망이 검증 템플릿으로 인계]

## 다음 단계
- 완료 후 `ddolmangi-screen-verify-template.md`로 브라우저 검증 → `codex-review-template.md`로 검수 → 사용자 승인 → 커밋.
