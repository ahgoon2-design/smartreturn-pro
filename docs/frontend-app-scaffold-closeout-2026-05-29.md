# Frontend App Scaffold 구현 마감

## 1. 구현 목적

SmartReturn Pro 프론트의 실사용 앱 골격을 React, Vite, TypeScript 기준으로 전환했다. 이번 작업은 화면을 완성하는 단계가 아니라, 이후 기준정보, import, 입고, 출고, 반품, 재고, 정산 화면이 같은 구조를 따를 수 있도록 AppShell, 라우팅, 인증 context, API client, 공통 UI skeleton을 준비하는 작업이다.

## 2. 변경 전 frontend 상태

기존 `frontend`는 React/Vite 앱이 아니라 단일 정적 import preview skeleton이었다.

- `frontend/index.html`
- `frontend/scripts/build.mjs`
- `frontend/src/app.js`
- `frontend/src/lib/apiClient.js`
- `frontend/src/api/master.js`
- `frontend/src/api/importJobs.js`
- `frontend/src/screens/importPreviewScreen.js`
- `frontend/src/styles.css`

정적 skeleton은 API 흐름 확인용으로 유효했지만, 장기 실사용 구조로 확장하기 어렵기 때문에 React feature로 흡수했다.

## 3. React/Vite/TypeScript 전환 내용

`frontend/package.json`을 React/Vite/TypeScript 기준으로 전환했다.

추가 기준:

- React + React DOM
- Vite
- TypeScript
- React Router
- Ant Design
- Ant Design Icons

script 기준:

- `npm.cmd run dev`
- `npm.cmd run build`
- `npm.cmd run preview`
- `npm.cmd run typecheck`

기존 `frontend/scripts/build.mjs`는 정적 파일 존재 확인용이었기 때문에 제거했다. 실제 검증은 TypeScript typecheck와 Vite build로 대체한다.

## 4. 새 디렉터리 구조

이번 작업에서 실제 사용하는 최소 구조를 만들었다.

```text
frontend/src/
  app/
  routes/
  layouts/
  pages/
  features/import/
  context/
  api/
  components/common/
  components/grid/
  styles/
  types/
```

빈 폴더만 만들지 않고, 현재 skeleton에서 사용하는 파일만 추가했다.

## 5. AppShell / Layout / Routes 구성

`MainLayout`은 아래 요소를 가진다.

- 상단 헤더: `SmartReturn Pro`
- 인증 연동 상태 표시
- 좌측 메뉴 skeleton
- 메인 컨텐츠 영역

route skeleton:

- `/`
- `/imports/preview`
- `/login`
- `*` not found

아직 구현되지 않은 기준정보, 입고, 출고, 반품, 재고, 정산 메뉴는 준비중 상태로만 표시한다.

## 6. AuthContext 구성

`AuthProvider`와 `useAuth` hook을 추가했다.

현재 범위:

- loading 상태
- auth context 상태
- `/api/auth/context` 호출 자리
- logout placeholder
- 기존 localStorage token key 호환

이번 작업에서는 실제 로그인 화면 완성, token 발급, 권한별 route guard 완성은 포함하지 않았다. token, password, secret, password_hash는 화면과 console에 출력하지 않는 원칙을 유지한다.

## 7. API client 구성

`frontend/src/api/client.ts`를 기준으로 공통 API client를 구성했다.

포함 내용:

- `ApiResult` 응답 처리
- `ApiClientError` 변환
- 401/403/422/5xx 공통 처리 여지
- `VITE_API_BASE_URL` 기반 base URL 구조
- 로컬 개발 fallback: `http://127.0.0.1:8000`
- token 저장값 출력 금지

API service:

- `api/auth.ts`
- `api/master.ts`
- `api/importJobs.ts`

## 8. 공통 UI skeleton

아래 최소 공통 컴포넌트를 추가했다.

- `SmartPage`
- `SmartPageHeader`
- `SmartActionBar`
- `SmartStatusBadge`
- `SmartErrorNotice`
- `SmartSummaryCard`
- `SmartDataGrid`

`SmartDataGrid`는 아직 본격 AG Grid wrapper가 아니다. 실사용 전에는 공통 Grid 정책에 맞춰 확장해야 한다.

## 9. Import Preview React 이전

기존 정적 import preview skeleton의 핵심 흐름을 React 화면으로 이전했다.

route:

- `/imports/preview`

연결 API:

- `GET /api/master/clients`
- `POST /api/import-jobs`
- `POST /api/import-jobs/{job_id}/rows/paste`
- `POST /api/import-jobs/{job_id}/validate`
- `GET /api/import-jobs/{job_id}/rows`
- `GET /api/import-jobs/{job_id}/errors`

화면 기능:

- 고객사 선택
- `import_type` 선택
- `source_type` 선택
- paste textarea
- rows 저장
- validate 실행
- summary 표시
- rows grid 표시
- errors 상세 표시
- 전체/오류/경고 필터
- `row_no` 기준 원본 순서 유지
- 다음 단계 진행 버튼 비활성 표시

상태 표시:

- `VALID`: 정상
- `WARNING`: 경고
- `INVALID`: 오류
- `NOT_VALIDATED`: 검증 전
- `DRAFT`: 작성 중
- `READY_TO_VALIDATE`: 검증 대기
- `VALIDATED`: 검증 완료
- `HAS_ERRORS`: 오류 있음

## 10. 기존 정적 skeleton 처리

정적 skeleton 파일은 React 앱과 중복되어 혼선을 만들 수 있으므로 제거했다.

제거 파일:

- `frontend/scripts/build.mjs`
- `frontend/src/app.js`
- `frontend/src/lib/apiClient.js`
- `frontend/src/api/master.js`
- `frontend/src/api/importJobs.js`
- `frontend/src/screens/importPreviewScreen.js`
- `frontend/src/styles.css`

기능은 React/Vite/TypeScript 구조로 흡수했다.

## 11. 미구현 항목

- 실제 로그인 화면
- token 발급/갱신 흐름
- 권한별 route guard 완성
- SmartDataGrid 본격 구현
- 파일 업로드 `EXCEL_FILE`
- import confirm/save
- 기준정보 화면
- 입고/출고/반품/재고/정산 화면

## 12. API 응답 필드 보강 후보

현재 skeleton 구현을 막는 필드 부족은 없었다.

다만 실사용 전 아래는 보강 후보로 남긴다.

- job summary/detail의 `warning_rows`
- row별 오류/경고 count
- job detail의 client 표시명
- import_type별 grid column metadata

## 13. 다음 추천 작업

다음 작업은 `AuthContext`와 route guard를 실제 로그인 흐름에 연결하는 것을 추천한다. 그 다음 `SmartDataGrid` wrapper를 강화하고, import preview 화면을 기준으로 파일 업로드 skeleton을 연결하는 순서가 안전하다.
