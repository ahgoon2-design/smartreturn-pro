# backend

이 폴더는 SmartReturn Pro 백엔드 코드가 들어갈 예정 위치다.

향후 FastAPI 앱은 `backend/app` 아래에 구성한다. 이번 단계에서는 실제 FastAPI 앱, 패키지 파일, DB 연결, migration, 실행 코드를 만들지 않았다.

## 예정 구조

- `app/core`: 설정, 인증 공통 dependency, 공통 예외 처리 후보
- `app/db`: DB 연결, session, SQLAlchemy Base 후보
- `app/models`: SQLAlchemy 모델 후보
- `app/schemas`: 요청/응답 DTO 후보
- `app/repositories`: DB 접근 계층
- `app/services`: 업무 흐름과 검증 계층
- `app/routers`: API router 계층
- `tests`: 백엔드 테스트 후보

## 계층 책임

- router는 요청/응답과 dependency 연결만 담당한다.
- service는 업무 흐름과 검증을 담당한다.
- repository는 DB 접근을 담당한다.
- schemas는 요청/응답 DTO를 담당한다.
- models는 SQLAlchemy 모델을 담당한다.

## 구현 전 확인

실제 구현 전에는 [P0 개발환경 세팅 전 계획](../docs/dev/smartreturn-pro-p0-dev-environment-plan.md)을 먼저 읽는다.
