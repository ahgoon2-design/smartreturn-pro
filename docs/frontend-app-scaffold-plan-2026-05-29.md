# Frontend App Scaffold 기준 계획

## 1. 문서 목적

이 문서는 SmartReturn Pro의 실사용 프론트 앱 구조를 확정하기 위한 기준 문서다.

현재 `frontend`에는 import preview 흐름 확인용 정적 skeleton이 추가되어 있지만, 장기적으로 사용할 React/Vite 기반 앱 구조는 아직 확정되지 않았다. 따라서 React/Vite/TypeScript 구현을 시작하기 전에 프론트 표준 구조, 라우팅, 인증 컨텍스트, API client, 공통 Grid/화면 컴포넌트 기준을 먼저 정리한다.

이 기준은 향후 기준정보, import, 입고, 출고, 반품, 재고, 정산 화면이 같은 구조를 따르도록 표준화하는 데 목적이 있다.

## 2. 현재 frontend 상태 요약

현재 상태:

- 기존 `frontend`에는 정식 React/Vite 앱 구조가 없었다.
- 실제 라우팅, 메뉴, 인증 컨텍스트, 공통 API client, 공통 UI 컴포넌트도 없었다.
- 최근 import preview 흐름 확인을 위해 의존성 없는 정적 skeleton이 추가되었다.
- 현재 skeleton의 역할은 API 흐름 검증용이며, 장기 실사용 구조는 아니다.
- skeleton은 React 전환 시 참고용으로 유지하고, 중복 기능이 되면 전환 시 정리 후보로 둔다.

현재 skeleton 파일 목록:

- `frontend/package.json`
- `frontend/index.html`
- `frontend/scripts/build.mjs`
- `frontend/src/app.js`
- `frontend/src/lib/apiClient.js`
- `frontend/src/api/master.js`
- `frontend/src/api/importJobs.js`
- `frontend/src/screens/importPreviewScreen.js`
- `frontend/src/styles.css`
- `frontend/src/README.md`

현재 `package.json`은 실제 React/Vite 패키지 구성이 아니라 `node scripts/build.mjs` 검증용 최소 구조다. 다음 구현 단계에서 React/Vite/TypeScript 앱으로 전환할 때 package 기준을 다시 확정해야 한다.

## 3. 추천 기술 기준

| 항목 | 추천안 | 이유 |
| --- | --- | --- |
| UI framework | React | 관리자/작업자 화면의 상태 관리와 컴포넌트 재사용에 적합하다. |
| build tool | Vite | 초기 설정이 단순하고 React/TypeScript 개발 서버와 build 속도가 빠르다. |
| language | TypeScript | API schema, 권한, 화면 상태, grid row 타입을 명확히 관리해야 한다. |
| CSS 방식 | 전역 CSS + component class 우선, 필요 시 CSS Module 검토 | 초기에는 구조를 단순하게 유지하고, 공통 컴포넌트 class를 통해 밀도와 간격을 통제한다. |
| UI kit | Ant Design 우선 | form, input, select, modal, table, date picker, layout, icon 등 기능성 UI가 풍부하다. |
| Mantine | 당장 설치하지 않음 | 카드/spacing/worker panel 느낌은 공통 CSS와 컴포넌트로 흡수한다. |
| Grid | `SmartDataGrid` wrapper 우선 | 화면별 직접 table/grid 구현을 막고 row 상태, 권한, pagination, action bar 기준을 통일한다. |
| AG Grid | 필요 시 wrapper 내부에서만 사용 | 화면에서 `AgGridReact` 직접 import를 금지한다. |
| icon | Ant Design 사용 시 `@ant-design/icons` 우선, 필요 시 `lucide-react` 보조 검토 | UI kit과 아이콘 톤을 먼저 맞춘다. |

SmartReturn Pro는 관리자 화면과 작업자 화면이 섞이므로 단순 페이지 모음이 아니라 공통 layout, route guard, 권한 기준, client scope 기준이 있는 앱이어야 한다.

## 4. 추천 디렉터리 구조

권장 구조:

```text
frontend/
  src/
    app/
      App.tsx
      router.tsx
      providers.tsx
    routes/
      routePaths.ts
      routeGuards.tsx
    layouts/
      AppShell.tsx
      MainLayout.tsx
      AuthLayout.tsx
    pages/
      auth/
      dashboard/
      import/
      master/
      not-found/
    features/
      auth/
      import/
      master/
      returns/
      inventory/
      settlement/
    components/
      common/
      grid/
      form/
      layout/
      modal/
      lookup/
    api/
      apiClient.ts
      authApi.ts
      masterApi.ts
      importJobsApi.ts
    context/
      AuthContext.tsx
      ClientScopeContext.tsx
    hooks/
    styles/
      globals.css
      tokens.css
    types/
      api.ts
      auth.ts
      import.ts
      master.ts
    utils/
```

구조 판단:

- `api`는 HTTP 통신 전용으로 둔다.
- `features`는 업무 도메인별 상태, hooks, 화면 내부 컴포넌트를 둔다.
- `pages`는 라우트 entry만 둔다.
- `components`는 도메인과 무관한 공통 UI만 둔다.
- `context`는 인증과 client scope처럼 앱 전체에 걸치는 상태만 둔다.

## 5. 라우팅 기준

라우팅 원칙:

- 공개 화면과 로그인 필요 화면을 분리한다.
- 로그인 필요 화면은 `AppShell` 또는 `MainLayout` 안에 둔다.
- `route guard`는 인증 여부, `must_change_password`, role, permission을 확인한다.
- 권한 없는 화면 접근 시 빈 화면으로 보내지 말고 권한 없음 안내 화면을 표시한다.
- 없는 route는 404 페이지로 보낸다.

추천 path 규칙:

- `/login`
- `/password/change-required`
- `/dashboard`
- `/imports/preview`
- `/master/clients`
- `/master/warehouses`
- `/master/products`
- `/master/common-codes`

import preview 추천 route:

- `/imports/preview`

메뉴 구조:

- 메뉴는 route path와 permission 기준을 함께 가진다.
- `IMPORT_VIEW` 또는 `IMPORT_MANAGE` 여부에 따라 import 메뉴 노출을 제어한다.
- 고객사 사용자의 화면 노출은 `AuthContext`의 role/client scope 기준으로 판단한다.

## 6. 인증 컨텍스트 기준

관리 대상:

- 로그인 상태
- access token
- `/api/auth/context` 응답
- role
- permissions
- selected/effective client scope
- `must_change_password`

token 저장 위치 원칙:

- 초기 skeleton에서는 `localStorage`를 사용할 수 있으나, token 전체값을 화면/console/log에 출력하지 않는다.
- 실사용 전에는 보안 요구에 따라 httpOnly cookie 전환 가능성을 검토한다.
- 어떤 방식이든 API client 밖에서 token을 직접 조작하지 않도록 한다.

`/api/auth/context` 연동:

- 앱 시작 또는 새로고침 시 context를 조회한다.
- context 조회 실패가 `NOT_AUTHENTICATED` 또는 `INVALID_TOKEN`이면 로그인 화면으로 이동한다.
- `must_change_password=true`이면 비밀번호 변경 화면으로 강제 이동한다.

로그아웃:

- token 저장소를 비운다.
- 인증 context를 초기화한다.
- 로그인 화면으로 이동한다.

보안:

- token, password, secret, password_hash는 화면/console/log에 절대 노출하지 않는다.
- 인증 오류는 result_code와 사용자 문구만 표시한다.

## 7. API client 기준

공통 처리:

- 모든 API 응답은 `ApiResult` 구조를 기준으로 처리한다.
- `success=false`이면 `result_code`, `message`, `errors`, `next_action`을 표준 오류 객체로 변환한다.
- 401은 인증 만료/미인증 처리로 연결한다.
- 403은 권한 없음 안내로 연결한다.
- 422 validation error는 화면별 field error로 변환하되, 공통 result 형태와 다를 수 있음을 감안한다.
- 5xx는 stack trace 대신 일반 서버 오류 문구만 표시한다.

API service 분리:

- `authApi.ts`: login, auth context, password change
- `masterApi.ts`: clients, warehouses, products, common codes
- `importJobsApi.ts`: import job create/read, paste rows, validate, rows/errors 조회
- 업무별 API는 feature 단위로 분리한다.

하드코딩 금지:

- API base URL을 코드에 하드코딩하지 않는다.
- `client_id`를 코드에 하드코딩하지 않는다.
- token을 코드에 하드코딩하지 않는다.

환경변수 기준:

- Vite 전환 후 `import.meta.env` 기반으로 API base URL을 읽는다.
- 실제 `.env` 값은 문서와 코드 주석에 쓰지 않는다.
- `.env.example`에는 키 이름과 형식만 둔다.

현재 importJobs API service 전환 방향:

- 현재 `frontend/src/api/importJobs.js`는 skeleton용이다.
- React/TypeScript 전환 시 `frontend/src/api/importJobsApi.ts`로 옮기고 request/response type을 명시한다.

현재 master API service 전환 방향:

- 현재 `frontend/src/api/master.js`는 clients 조회만 포함한다.
- React/TypeScript 전환 시 `frontend/src/api/masterApi.ts`로 옮기고 기준정보 API를 업무별 함수로 확장한다.

## 8. 공통 UI 컴포넌트 기준

| 컴포넌트 | 목적 | 남용 방지 원칙 |
| --- | --- | --- |
| `SmartPage` | 업무 화면의 기본 outer layout | 모든 영역을 카드로 감싸지 않는다. |
| `SmartPageHeader` | 화면 제목, 상태, 주요 보조 액션 | 큰 hero처럼 만들지 않는다. |
| `SmartToolbar` | 필터, 검색, 기준 선택 | 버튼과 입력이 과도하게 늘어나면 section 분리한다. |
| `SmartActionBar` | 저장, 검증, 다음 단계 등 주요 액션 고정 | 하단 action bar가 화면 내용을 가리지 않게 한다. |
| `SmartSummaryCard` | total, valid, invalid 등 핵심 숫자 표시 | 정보 카드가 grid보다 주인공이 되면 안 된다. |
| `SmartStatusBadge` | role/status/result 표시 | 색상만으로 의미를 전달하지 않는다. |
| `SmartDataGrid` | 업무 데이터 grid wrapper | 화면에서 grid library를 직접 쓰지 않는다. |
| `SmartFilterPanel` | 고급 필터 묶음 | 간단한 필터까지 전부 패널로 숨기지 않는다. |
| `SmartEmptyState` | 빈 데이터 안내 | 긴 설명으로 grid 영역을 밀어내지 않는다. |
| `SmartErrorNotice` | API 오류/권한 오류 표시 | stack trace, token, secret을 표시하지 않는다. |
| `SmartModalShell` | 공통 모달 shell | 모달마다 크기/footer/button 위치를 다르게 만들지 않는다. |
| `SmartFormSection` | 입력 폼 섹션 구분 | 섹션을 카드처럼 중첩하지 않는다. |

## 9. Grid 기준

원칙:

- 업무 화면에서 grid 직접 구현을 남발하지 않는다.
- 원본 row 순서를 보존한다.
- `row_no` 또는 `original_row_no`를 표시한다.
- 대량 데이터에서도 하단 액션 영역이 고정되어야 한다.
- 오류/경고/상태는 뱃지와 메시지로 함께 표시한다.
- 향후 AG Grid를 쓰더라도 `SmartDataGrid` wrapper를 통해서만 사용한다.
- skeleton 단계에서 기본 table을 쓰더라도 실사용 전 `SmartDataGrid`로 전환한다.

import preview grid 기준:

- 기본 정렬은 `row_no asc`다.
- 오류/경고 필터를 적용해도 원본 순서가 유지되어야 한다.
- row 클릭 시 오류/경고 상세 패널과 연결되어야 한다.
- 동적 `raw_json` 컬럼은 import_type별 column definition으로 제한하는 방향을 우선 검토한다.

## 10. 화면 밀도와 작업자 UX 기준

공통:

- 1366x768 기준 핵심 입력, grid 첫 5행, 우측/하단 정보 영역, 하단 action bar가 보여야 한다.
- 과한 카드 남발을 금지한다.
- 조회 영역, 작업 영역, 오류 영역을 명확히 구분한다.
- 화면 목적을 1개로 유지한다.

스캔/작업자 화면:

- 큰 입력
- 큰 피드백
- 빠른 focus 이동
- 키보드 중심 조작
- 불필요한 설명 최소화

관리자 화면:

- 필터
- grid
- 상세 패널
- 상태/권한/이력 확인
- 반복 작업에 적합한 밀도

## 11. import preview skeleton 전환 기준

현재 정적 skeleton:

- API 흐름 검증용 참고 구현으로 유지한다.
- React 전환 후 중복 기능이 되면 정리 후보로 둔다.
- 삭제가 필요하면 별도 작업에서 정리하고, 이번 문서 단계에서는 삭제하지 않는다.

React 전환 방향:

- 현재 구현한 API 흐름은 `features/import` 또는 `pages/import` 하위 feature로 흡수한다.
- import preview route는 `/imports/preview`를 우선한다.
- `source_type=PASTE` 흐름을 먼저 React 화면으로 옮긴다.
- `EXCEL_FILE`은 다음 단계 skeleton에서 같은 preview 결과 grid와 errors panel을 재사용한다.
- 파일 업로드 전용 UI와 validation 결과 UI를 분리한다.

## 12. 단계별 구현 순서 제안

1. React/Vite/TypeScript 기본 앱 생성
2. `AppShell` / `MainLayout` / route guard skeleton
3. auth context와 `/api/auth/context` 연결
4. 공통 API client 정리
5. 공통 UI 컴포넌트 최소 세트 구현
6. import preview 정적 skeleton을 React 화면으로 이전
7. `SmartDataGrid` wrapper 또는 최소 Grid wrapper 도입
8. 파일 업로드 skeleton
9. 기준정보 화면 순차 연결

## 13. 구현 전 위험/주의사항

- 정적 skeleton을 그대로 확장하면 나중에 전면 재작업 가능성이 높다.
- 프론트 기준 없이 화면을 늘리면 UI, 권한, API 처리가 중복된다.
- `client_id` 하드코딩을 금지한다.
- API 응답 필드를 추정해서 화면 로직을 만들지 않는다.
- 인증/권한 우회를 금지한다.
- secret, token, password, password_hash 노출을 금지한다.
- 공통 Grid 없이 화면별 table이 늘어나는 것을 주의한다.
- 기존 SmartReturn 화면 구조를 그대로 복사하지 않는다.
- package 변경 시 `.env`, `dist`, `build`, `node_modules`가 커밋되지 않도록 확인한다.

## 14. closeout 결론

다음 작업은 React/Vite/TypeScript 앱 스캐폴드 구현을 추천한다.

단, 구현 전 package 변경과 기존 정적 skeleton 처리 방향은 이 문서 기준에 맞춰 진행해야 한다. 정적 skeleton은 참고용으로 유지하고, React 전환 후 중복 기능이 되면 별도 정리 대상으로 둔다.

스캐폴드 구현 후에는 `npm build` 또는 프로젝트 표준 frontend 검증 명령을 실행하고, 가능하면 브라우저 렌더링까지 확인해야 한다.
