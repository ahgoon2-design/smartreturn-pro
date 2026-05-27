# backend

이 폴더는 SmartReturn Pro 백엔드 코드가 들어갈 위치다.

현재 단계에서는 FastAPI 최소 앱, 설정 로딩 구조, 기본 로깅 설정, `/health` API, health 테스트, SQLAlchemy DB 기본 구조, Alembic 초기 구조만 생성했다. 기준정보/반품 같은 업무 API, 인증 구현, P0 업무 모델은 후속 작업에서 진행한다.

## 현재 생성된 구조

- `app/main.py`: FastAPI 앱 생성과 router 연결
- `app/core/config.py`: `.env` 값을 읽기 위한 설정 구조
- `app/core/logging.py`: 기본 콘솔 로깅 설정
- `app/db/base.py`: SQLAlchemy Declarative Base
- `app/db/session.py`: SQLAlchemy engine, session factory, `get_db` dependency 후보
- `app/routers/health.py`: `/health` API
- `app/schemas/health.py`: health 응답 DTO
- `alembic`: Alembic migration 기준 구조
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

## DB/Alembic 기준

- DB 구조는 SQLAlchemy + Alembic 기준으로 관리한다.
- `startup`에서 `Base.metadata.create_all`을 호출하지 않는다.
- 자동 `ALTER TABLE` 또는 schema sync 구조를 만들지 않는다.
- DB 스키마 변경은 Alembic migration으로만 관리한다.
- `DATABASE_URL`은 `.env` 또는 환경변수로 주입한다.
- `.env.example`은 예시 파일이며 실제 `.env`는 커밋 금지다.
- 이번 단계에서는 P0 업무 모델이 없으므로 migration 생성은 후속 작업에서 진행한다.

DB 관련 의존성은 sync SQLAlchemy + `psycopg` 기준으로 시작한다. `asyncpg`는 이번 단계에 추가하지 않았다.

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

## Alembic 후보 명령

```powershell
cd backend
alembic current
alembic revision --autogenerate -m "message"
alembic upgrade head
```

P0 모델이 아직 없으므로 `alembic revision --autogenerate`는 후속 모델 작업 이후에 실행한다.

## P0 seed 후보 명령

```powershell
cd backend
python scripts/seed_p0.py
```

현재 seed 스크립트는 `roles`, `permissions`, `role_permissions` 기본값만 다룬다. 초기 `SUPER_ADMIN` 사용자 계정, 비밀번호, 고객사, 상품, 창고, 업무 데이터는 생성하지 않는다.

## 구현 전 확인

실제 구현 전에는 [P0 개발환경 세팅 전 계획](../docs/dev/smartreturn-pro-p0-dev-environment-plan.md)을 먼저 읽는다.

## 초기 관리자 bootstrap

```powershell
cd backend
python scripts/seed_p0.py
python scripts/bootstrap_super_admin.py
```

초기 `SUPER_ADMIN` 계정은 role/permission seed 실행 후 별도 bootstrap 스크립트로 생성한다. 비밀번호는 콘솔 입력 또는 환경변수로 1회 주입하며 코드, 문서, 커밋에 남기지 않는다. 생성된 초기 관리자는 `must_change_password=true`로 시작한다. 로그인 API와 일반 인증 흐름은 아직 구현 전이다.

## AuthContext/권한 검증 skeleton

`AuthContext`와 role, permission, client scope, warehouse scope 검증 유틸을 추가했다. 내부 운영자와 고객사 사용자는 `client_id` 유무가 아니라 role 기준으로 구분한다. 실제 로그인, JWT, API dependency 연결은 후속 작업에서 구현한다.

## 인증 API skeleton

`POST /api/auth/login`은 login_id/password를 확인하고 access token을 발급한다. `GET /api/auth/context`는 Bearer token 기준 현재 사용자 AuthContext를 반환한다. refresh token, 사용자 관리 API, 프론트 로그인 화면은 아직 구현 전이다.

`POST /api/auth/password/change`는 Bearer token 기반으로 현재 사용자의 비밀번호를 변경한다. `must_change_password=true`여도 로그인과 비밀번호 변경은 가능하며, 일반 업무 API 차단은 후속 dependency 적용 단계에서 처리한다. 비밀번호 평문과 token/secret은 로그, 응답, 커밋에 남기지 않는다.

## auth 오류 응답

인증/권한 오류는 공통 `ApiResult` 형태로 응답한다. 내부 stack trace, token, password, `password_hash`, secret은 오류 응답에 포함하지 않는다. 이 기준은 아직 auth/login/password/context 라우터에만 적용되어 있으며 기준정보/반품 API에는 후속 작업에서 연결한다.

## P0 기준정보 read-only API skeleton

`GET /api/master/*` 기준정보 조회 skeleton이 추가되었다. 생성/수정/삭제는 아직 구현하지 않았으며, 고객사/창고/상품/공통코드 조회는 `AuthContext`, `MASTER_VIEW` permission, client scope 기준으로 동작한다.
## 로컬 secret 기반 수동 검증

`backend/local.secret.example.json`을 `backend/local.secret.json`으로 복사하면 로컬 검증 스크립트에서 사용할 수 있다. 실제 `local.secret.json`은 Git에 커밋하지 않는다.

```powershell
cd backend
python scripts/verify_master_api_local.py
```

이 스크립트는 실행 중인 uvicorn 서버를 대상으로 로그인, 비밀번호 변경, AuthContext, 기준정보 read-only API를 검증한다. 실행 전에 `uvicorn app.main:app --host 127.0.0.1 --port 8000`으로 서버를 먼저 실행해야 한다. 비밀번호와 access token 전체값은 출력하지 않으며, 운영 환경에서는 사용하지 않는다.
