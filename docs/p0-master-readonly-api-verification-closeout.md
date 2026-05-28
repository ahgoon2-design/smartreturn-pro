# P0 기준정보 read-only API 수동 검증 완료 기록

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

## 검증 목적

P0 기준정보 read-only API skeleton이 로그인/JWT/AuthContext, `MASTER_VIEW` permission, client scope 기준에 맞게 실제 로컬 서버에서 동작하는지 확인했다.

## 검증 결과

- 검증 일자: 2026-05-28
- 검증 방식: `verify_master_api_local.py` 로컬 수동 검증
- 검증 결과: 성공
- 종료 코드: `0`
- 전체 테스트: `106 passed`
- `/health`: HTTP 200, `status=ok`, `app_name=SmartReturn Pro`
- `backend/local.secret.json`: git 제외 상태 유지
- 응답/로그 노출 확인: stack trace, secret, token 전체값, password, `password_hash` 노출 없음

## AuthContext 확인

- role: `SUPER_ADMIN`
- permissions count: 31
- `MASTER_VIEW`: true
- `is_internal_user`: true
- `is_client_user`: false
- `client_id`: null
- `must_change_password`: false

## 기준정보 API 확인

아래 API는 Bearer token 기반으로 HTTP 200 응답을 확인했다.

- `GET /api/master/clients`
- `GET /api/master/warehouses`
- `GET /api/master/products`
- `GET /api/master/common-code-groups`
- `GET /api/master/common-codes`

현재 로컬 seed 데이터가 없으면 목록 응답은 0건일 수 있다. 0건 목록이어도 HTTP 200과 정상 `ApiResult` 또는 page 구조이면 성공으로 본다.

## 선택 검증 항목

- `GET /api/master/client-warehouses`: 검증 가능한 `client_id` 후보가 없으면 `skipped=no_client_id_candidate`로 처리한다.
- `GET /api/master/products/{product_id}` missing 검증: 안전한 missing id 후보가 없으면 `skipped=no_safe_missing_id_candidate`로 처리한다.
- 상세 API 검증은 로컬에 client/product/common-code seed 후보가 생긴 뒤 다시 수행할 수 있다.

## 오류 응답 확인

- 인증 없음: HTTP 401, `NOT_AUTHENTICATED`
- 잘못된 토큰: HTTP 401, `INVALID_TOKEN`
- 오류 응답에 stack trace, secret, token 전체값, password, `password_hash`가 노출되지 않음을 확인했다.

## 후속 메모

- 기준정보 read-only API skeleton의 P0 수동 검증은 완료 상태로 본다.
- 다음 단계에서 테스트용 기준정보 seed 또는 fixture가 준비되면 client/product 상세 조회와 `group_code` 필터 검증을 추가로 수행한다.
- 생성/수정/삭제/사용중지 API는 아직 구현 범위가 아니다.
