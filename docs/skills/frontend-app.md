---
name: frontend-app
description: >-
  React/Vite/TypeScript frontend 작업 시 적용하는 프론트엔드 앱 스킬. 앱 구조, 라우팅, 인증
  context, API client, frontend scaffold 기준을 정리하므로 frontend 화면·상태·통신 코드를
  만들거나 수정하는 작업 시 반드시 이 스킬을 적용한다.
---

# Frontend App Skill

## 목적

SmartReturn Pro frontend 작업 시 React/Vite/TypeScript 앱 구조와 인증, 라우팅, API client 기준을 정리한다.

frontend 작업 전에는 반드시 `docs/frontend-app-scaffold-plan-2026-05-29.md`를 함께 참고한다.

## 기술 기준

- React
- Vite
- TypeScript
- Ant Design 우선
- `@ant-design/icons` 우선
- Mantine은 당장 설치하지 않는다.
- 부드러운 카드, 간격, 작업 패널 느낌은 공통 CSS와 SmartReturn 공통 컴포넌트로 흡수한다.

## 앱 구조 기준

권장 구조:

```text
frontend/src/
  app/
  routes/
  layouts/
  pages/
  features/
  components/
  api/
  context/
  styles/
  types/
  utils/
```

빈 폴더만 만들지 않고 실제 쓰는 파일 중심으로 만든다.

## 라우팅 기준

- 공개 화면과 로그인 필요 화면을 분리한다.
- `AppShell` 또는 `MainLayout` 기준으로 업무 화면을 감싼다.
- route guard는 인증, `must_change_password`, role, permission을 점검할 수 있어야 한다.
- 권한 없는 화면은 빈 화면으로 보내지 않고 안내를 표시한다.
- 404 화면을 둔다.

## 인증 context 기준

- `/api/auth/context`를 기준으로 사용자 role, permissions, client scope를 확인한다.
- `must_change_password=true`는 별도 처리 흐름을 둔다.
- `NOT_AUTHENTICATED`, `INVALID_TOKEN`은 공통 처리한다.
- token, password, secret은 화면과 console에 출력하지 않는다.
- 임시 관리자 token을 하드코딩하지 않는다.

## API client 기준

- `ApiResult` 공통 응답을 처리한다.
- 401, 403, 422, 5xx 오류 처리 여지를 공통 client에 둔다.
- API service는 도메인별로 분리한다.
- API base URL은 하드코딩하지 않고 Vite 환경변수 기준으로 설정할 수 있게 한다.
- 실제 `.env` 값은 문서나 코드 주석에 쓰지 않는다.
- `client_id`를 화면 코드에 하드코딩하지 않는다.

## 정적 skeleton 기준

정적 skeleton은 실사용 구조가 아니다. React/Vite 앱으로 전환할 때 기존 흐름은 feature로 흡수하고, 중복되는 정적 파일은 혼선이 없도록 정리한다.

## 작업 시 확인

- 기존 API client, AuthContext, route 구조를 먼저 확인한다.
- 기존 공통 컴포넌트로 조합 가능한지 먼저 본다.
- 화면별 임시 fetch, 임시 token, 하드코딩 client_id를 만들지 않는다.
- build 또는 typecheck를 실행한다.
- backend 코드가 바뀌지 않았다면 backend pytest는 생략할 수 있으나 이유를 보고한다.
