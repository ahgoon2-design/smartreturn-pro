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
