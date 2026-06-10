# 로컬 secret config 정책

이 문서는 SmartReturn Pro 로컬 개발/검증 전용 secret config 기준이다. 실제 운영 secret 관리 기준이 아니며, 운영 환경에서는 이 파일 기반 검증이나 재설정을 사용하지 않는다.

## 목적

환경변수만으로 로컬 검증을 진행하면 Codex, PowerShell, 새 터미널, 백그라운드 서버 프로세스 사이에서 값 전달이 자주 끊긴다. 특히 `local_super_admin` 로그인, 비밀번호 변경, 기준정보 API 수동 검증은 여러 API 호출을 연속으로 수행해야 하므로 검증 전용 설정 파일이 있으면 반복 작업을 줄일 수 있다.

## 파일 기준

- 실제 로컬 secret 파일: `backend/local.secret.json`
- 커밋 가능한 예제 파일: `backend/local.secret.example.json`

`backend/local.secret.json`은 로컬 개발/검증 전용이며 절대 Git에 커밋하지 않는다. 실제 비밀번호, DB password, JWT secret, access token, 고객사 정보는 문서와 커밋에 남기지 않는다.

예제 파일은 구조만 보여준다. 실제 DB URL, 실제 관리자 비밀번호, 실제 JWT secret은 예제 파일에 넣지 않는다.

## 설정 로딩 우선순위

앱 런타임 설정은 기존 구조를 유지한다.

1. 환경변수
2. `.env`
3. 코드 기본값

로컬 검증 secret은 검증 스크립트에서만 명시적으로 읽는다.

1. 명시 경로 인자
2. `SMARTRETURN_LOCAL_SECRET_FILE`
3. `backend/local.secret.json`

FastAPI 앱 설정 로딩에 `local.secret.json`을 자동 혼합하지 않는다. 운영 런타임 설정과 로컬 검증 secret을 섞으면 운영 환경에서 개발용 비밀번호나 reset 흐름을 잘못 사용할 위험이 있다.

## local_super_admin 검증 원칙

`local_super_admin` 검증은 API 흐름을 우선한다.

1. `/api/auth/login`
2. `/api/auth/password/change`
3. 새 비밀번호로 다시 로그인
4. `/api/auth/context`
5. `/api/master/*` read-only API 검증

검증 스크립트는 비밀번호와 token 전체값을 출력하지 않는다. HTTP 오류가 발생해도 status code와 `result_code` 중심으로만 출력한다.

## DB 직접 접근 기준

DB 직접 접근은 로컬 개발 전용 reset/reissue 같은 제한된 작업에서만 허용한다. 운영/배포 환경에서는 금지한다.

금지 사항:

- `password_hash` 조회 또는 출력
- 운영 DB 접속
- DROP/DELETE 기반 초기화
- schema 변경
- 실제 고객사 개인정보 입력

향후 `reset_local_admin_password.py`를 추가한다면 `environment=local` 확인, 명시적인 로컬 DB URL 확인, password 원문 미출력, 운영 DB 차단, rollback/오류 처리 기준을 반드시 포함한다.

## Codex 작업 기준

- 실제 secret 값이 들어간 파일은 커밋하지 않는다.
- `backend/local.secret.json`은 `.gitignore` 대상이어야 한다.
- 완료 보고에는 비밀번호, token 전체값, secret, `.env` 내용을 쓰지 않는다.
- 로컬 검증 실패 시 응답 전문을 무분별하게 출력하지 않는다.

## 로컬 관리자 비밀번호 reset/reissue

`local_super_admin`의 현재 비밀번호를 알 수 없어 API 기반 검증을 시작할 수 없는 경우에만 로컬 전용 reset 스크립트를 사용한다. 이 절차는 개발 PC의 로컬 DB 복구와 검증 재개를 위한 도구이며 운영 환경에서는 사용하지 않는다.

권장 실행 순서:

1. `backend/local.secret.json`의 `environment`가 `local`인지 확인한다.
2. `auth.admin_login_id`와 `auth.new_password`를 로컬에서만 입력한다.
3. `cd backend`
4. `python scripts/reset_local_admin_password.py --confirm-local-reset`
5. `uvicorn app.main:app --host 127.0.0.1 --port 8000`
6. `python scripts/verify_master_api_local.py`

reset 스크립트는 `--confirm-local-reset` 옵션이 없으면 실행하지 않는다. DB URL은 `backend/local.secret.json`의 `database.url`이 있으면 우선 사용하고, 없으면 앱 설정의 `DATABASE_URL`을 사용한다. 어떤 경우에도 DB host가 `localhost`, `127.0.0.1`, `::1` 중 하나가 아니면 중단해야 한다.

reset 대상은 기존 `SUPER_ADMIN` role을 가진 활성 사용자로 제한한다. 사용자가 없거나, 비활성 상태이거나, `SUPER_ADMIN` role이 없으면 새 사용자를 만들거나 role을 부여하지 않고 실패해야 한다.

기본 정책은 reset 후 `must_change_password=false`로 두는 것이다. 목적이 로컬 검증 복구이므로 reset 직후 `verify_master_api_local.py`로 기준정보 read-only API 검증을 이어갈 수 있어야 하기 때문이다. 실제 비밀번호 변경 정책 흐름을 다시 검증해야 할 때만 `--require-password-change` 옵션으로 `must_change_password=true`를 선택한다.

출력 금지 항목:

- 새 비밀번호
- 기존 비밀번호
- `password_hash`
- DB URL 전체
- access token
- secret 또는 `.env` 내용

## 로컬 기준정보 fixture

product/product_barcodes 관리 API를 수동 검증하려면 active 고객사 1건이 필요하다. 운영 seed와 섞지 않기 위해 로컬 검증용 고객사는 `scripts/seed_local_master_fixture.py`에서만 준비한다. 이 스크립트는 `backend/local.secret.json`을 읽어 로컬 환경임을 확인하고, DB host가 `localhost`, `127.0.0.1`, `::1` 중 하나일 때만 실행한다.

실행 시 `--confirm-local-fixture` 옵션이 반드시 필요하다.

```powershell
cd backend
python scripts/seed_local_master_fixture.py --confirm-local-fixture
```

생성 또는 재사용하는 fixture는 아래 1건으로 제한한다.

- `client_code`: `LOCAL_TEST_CLIENT`
- `client_name`: `로컬검증고객사`
- `active_yn`: `true`

같은 `client_code`가 이미 있고 active 상태이면 새로 만들지 않고 재사용한다. 기존 고객사가 inactive 상태이면 기본 실행에서는 재활성화하지 않는다. 로컬 검증 복구가 필요할 때만 `--reactivate-existing` 옵션으로 `active_yn=true` 보정을 허용한다.

이 스크립트는 warehouse, product, product_barcodes, user, role, permission을 생성하지 않는다. 실제 고객사명, 개인정보, 운영 데이터는 사용하지 않는다. DROP, DELETE, schema 변경은 금지한다.
