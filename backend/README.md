# backend

이 폴더는 SmartReturn Pro 백엔드 코드가 들어가는 위치다.

이번 단계에서는 FastAPI 최소 앱, 설정 로딩 구조, 기본 로깅 설정, `/health` API, health 테스트만 생성했다. DB 연결, Alembic, SQLAlchemy 모델, 인증 구현, 기준정보/반품 같은 업무 API는 후속 작업에서 진행한다.

## 현재 생성된 구조

- `app/main.py`: FastAPI 앱 생성과 router 연결
- `app/core/config.py`: `.env` 값을 읽기 위한 설정 구조
- `app/core/logging.py`: 기본 콘솔 로깅 설정
- `app/routers/health.py`: `/health` API
- `app/schemas/health.py`: health 응답 DTO
- `tests/test_health_api.py`: `/health` API 테스트

## 예정 구조

- `app/core`: 설정, 인증 공통 dependency, 공통 예외 처리 후보
- `app/db`: DB 연결, session, SQLAlchemy Base 후보
- `app/models`: SQLAlchemy 모델 후보
- `app/schemas`: 요청/응답 DTO
- `app/repositories`: DB 접근 계층
- `app/services`: 업무 흐름과 검증 계층
- `app/routers`: API router 계층
- `tests`: 백엔드 테스트

## 계층 책임

- router는 요청/응답과 dependency 연결만 담당한다.
- service는 업무 흐름과 검증을 담당한다.
- repository는 DB 접근을 담당한다.
- schemas는 요청/응답 DTO를 담당한다.
- models는 SQLAlchemy 모델을 담당한다.

## 실행 후보 명령

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 테스트 후보 명령

```powershell
cd backend
pytest
```

## 구현 전 확인

실제 구현 전에는 [P0 개발환경 세팅 전 계획](../docs/dev/smartreturn-pro-p0-dev-environment-plan.md)을 먼저 읽는다.
