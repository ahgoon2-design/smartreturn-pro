# Frontend Auth / Route Guard 구현 마감

## 1. 작업 목적

React/Vite/TypeScript 프론트 스캐폴드 위에 실제 인증 흐름과 route guard 기반을 연결했다. 이번 작업은 화면 디자인 확장이 아니라 로그인, token 관리, `/api/auth/context`, `must_change_password`, 보호 route, 권한 없음 화면의 공통 기반을 고정하는 작업이다.

## 2. 변경 전 상태

이전 프론트 앱에는 `AuthContext` skeleton과 로그인 placeholder가 있었지만 실제 로그인 API, access token 저장, route redirect, 권한 부족 처리, 비밀번호 변경 필요 화면이 연결되어 있지 않았다. Import Preview 화면은 API 호출 구조를 갖고 있었으나 보호 route 안에서 인증 상태를 기준으로 제어되지는 않았다.

## 3. 확인한 backend 인증 API

- `POST /api/auth/login`
  - request: `login_id`, `password`
  - response: `access_token`, `token_type`, `expires_in`, `must_change_password`, `user`, `result_code`, `message`
- `GET /api/auth/context`
  - response: `user_id`, `login_id`, `user_name`, `roles`, `permissions`, `client_id`, `client_name`, `default_warehouse_id`, `must_change_password`, `is_internal_user`, `is_client_user`, `effective_client_id`
- `POST /api/auth/password/change`
  - request: `current_password`, `new_password`, `new_password_confirm`
  - response: `success`, `result_code`, `message`, `must_change_password`

## 4. 구현한 인증 구조

- `frontend/src/api/auth.ts`
  - `login`
  - `fetchAuthContext`
  - `changePassword`
- `frontend/src/api/client.ts`
  - `Authorization: Bearer` 자동 첨부
  - `ApiResult` 응답과 직접 응답을 모두 처리
  - 401, `NOT_AUTHENTICATED`, `INVALID_TOKEN` 발생 시 token 정리 hook 제공
- `frontend/src/context/AuthContext.tsx`
  - `login`
  - `logout`
  - `refreshAuthContext`
  - `changePassword`
  - `hasPermission`
  - `canAccess`
  - `clearAuth`

## 5. token 저장 기준

초기 skeleton 기준으로 access token은 `localStorage`의 프로젝트 전용 key인 `smartreturn.pro.accessToken`에 저장한다. 기존 skeleton에서 쓰던 legacy key는 읽기/정리 호환만 유지한다.

token 값은 화면, console, 문서, 완료 보고에 출력하지 않는다. 향후 보안 정책이 확정되면 httpOnly cookie 전환 가능성을 별도 보안 검토 후보로 남긴다.

## 6. Route Guard 구성

- `PublicRoute`
  - 로그인된 사용자가 `/login`에 접근하면 기본 import preview 화면으로 보낸다.
  - `must_change_password=true`이면 비밀번호 변경 화면으로 보낸다.
- `ProtectedRoute`
  - 비로그인 사용자는 `/login`으로 보낸다.
  - `must_change_password=true`이면 `/auth/password-change`로 보낸다.
  - 권한이 부족하면 `/forbidden`으로 보낸다.
- 주요 route
  - `/login`
  - `/`
  - `/imports/preview`
  - `/auth/password-change`
  - `/forbidden`
  - `/not-found`

Import Preview는 현재 생성/저장/검증 API를 호출하는 화면이므로 `IMPORT_MANAGE` 권한을 요구한다. `SUPER_ADMIN`은 `hasPermission`에서 통과하도록 처리했다.

## 7. Login Page 구성

`frontend/src/pages/auth/LoginPage.tsx`를 추가했다.

- 사용자 ID 입력
- 비밀번호 입력
- 로그인 버튼
- 로딩 상태
- 안전한 오류 메시지 표시

실제 비밀번호, token, secret 값은 화면이나 console에 출력하지 않는다.

## 8. Password Change Required 화면 구성

`frontend/src/pages/auth/PasswordChangeRequiredPage.tsx`를 추가했다.

- 현재 비밀번호
- 새 비밀번호
- 새 비밀번호 확인
- 변경 버튼
- 로그아웃 버튼

backend의 `POST /api/auth/password/change` API에 연결했다. 변경 성공 후 auth context를 다시 조회하고 기본 화면으로 이동한다.

## 9. AppShell 연동 내용

`MainLayout`에 로그인 사용자명, 대표 role, `must_change_password` 상태, 로그아웃 버튼을 표시했다. 아직 구현되지 않은 업무 메뉴는 준비중/disabled 상태를 유지한다.

## 10. Import Preview 보호 route 연결 확인

`/imports/preview`는 보호 route 안으로 이동했다.

- 비로그인 접근은 `/login`으로 이동
- 로그인 후 접근 가능
- `IMPORT_MANAGE` 권한 필요
- 고객사 목록, import job 생성, paste rows 저장, validate, rows/errors 조회는 공통 API client의 Bearer token 첨부를 사용
- 기존 `VALID`, `WARNING`, `INVALID`, `NOT_VALIDATED` 표시와 전체/오류/경고 필터는 유지

## 11. 오류 처리 기준

- `NOT_AUTHENTICATED`, `INVALID_TOKEN`: token 정리 후 재로그인이 가능한 상태로 전환
- 403: 권한 없음 화면 또는 안전한 오류 메시지 표시
- 422: 입력값 확인 메시지 표시
- 5xx: 일반 서버 오류 메시지 표시

stack trace, token, password, secret, password_hash는 표시하지 않는다.

## 12. 미구현/후속 보강 항목

- refresh token 또는 httpOnly cookie 기반 인증 정책
- permission별 메뉴 노출 세분화
- `/api/auth/logout` 서버 API가 생길 경우 logout API 연결
- 로그인/비밀번호 변경 화면의 최종 디자인 고도화
- Import Preview를 `SmartDataGrid` 정식 wrapper로 전환

## 13. 검증 결과

- `npm.cmd run typecheck`: 통과
- `npm.cmd run build`: 통과
- `git diff --check`: 통과
- backend 코드는 변경하지 않아 backend pytest는 생략했다.

## 14. 보안 확인

- 실제 secret/token/password/password_hash 값을 문서나 코드에 기록하지 않았다.
- `backend/local.secret.json`은 수정/커밋하지 않았다.
- `.env`, `config.json`, 실제 secret/local 파일, `node_modules`, `dist`, `build`는 커밋 대상에 포함하지 않는다.

## 15. 다음 추천 작업

1. SmartDataGrid wrapper 강화
2. Import Preview를 SmartDataGrid로 전환
3. 파일 업로드 `EXCEL_FILE` skeleton 설계
4. 기준정보 화면 디자인 토론
