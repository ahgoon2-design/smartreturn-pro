# Backend API Skill

## 목적

SmartReturn Pro FastAPI backend 작업 시 지켜야 할 API, 권한, 테스트 기준을 정리한다.

## 기본 기준

- FastAPI router, schema, service, repository 계층을 기존 패턴에 맞춘다.
- `ApiResult` 공통 응답 구조를 유지한다.
- 인증/권한은 기존 `AuthContext`와 permission 유틸을 우선 사용한다.
- client scope와 warehouse scope를 우회하지 않는다.
- 프론트에서 보낸 `client_id`를 무조건 신뢰하지 않는다.
- 내부 운영자와 고객사 사용자는 role 기준으로 구분한다.

## 오류 응답

- 표준 result_code를 사용한다.
- 권한 실패, scope 실패, not found, 중복 차단은 기존 API result_code 패턴에 맞춘다.
- validation 422 응답 통일 정책을 유지한다.
- stack trace를 응답에 노출하지 않는다.

## 보안 기준

- `backend/local.secret.json` 내용은 출력하지 않는다.
- `.env` 내용은 출력하지 않는다.
- 실제 secret, token, password, password_hash 값을 출력하지 않는다.
- 테스트 fixture도 운영 데이터나 실제 고객사명을 사용하지 않는다.

## DB 변경 기준

아래 변경이 필요하면 먼저 보고하고 사용자의 지시 범위를 확인한다.

- DB schema 변경
- migration 생성
- seed 변경
- role/permission 정책 변경
- 삭제 API 추가
- audit log, created_by, disabled_at 같은 신규 필드 추가

## 테스트 기준

backend 변경 시 기본 검증은 `pytest`를 사용한다.

작업 범위에 따라 아래를 선택한다.

- 변경 파일 관련 단위 테스트
- 기준정보 핵심 회귀 테스트
- import API 회귀 테스트
- 전체 backend 테스트

예:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider
```

## closeout 기준

아래 경우 closeout 문서가 필요할 수 있다.

- API skeleton 구현 완료
- 로컬 수동 검증 완료
- 권한/scope 정책 검증 완료
- frontend 계약에 영향을 주는 API 응답 계약 확정

문서 변경만 있는 경우 backend test는 생략할 수 있으나, 생략 사유를 완료 보고에 적는다.
