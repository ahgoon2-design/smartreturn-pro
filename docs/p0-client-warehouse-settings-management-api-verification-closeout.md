# P0 고객사 사용창고 관리 API 수동 검증 완료 기록

이 문서는 SmartReturn Pro P0 기준정보 관리 API 중 `client_warehouse_settings` 관리 API의 수동 검증 완료 결과를 기록한다.

## 1. 검증 목적

검증 대상은 고객사별 사용창고 연결의 생성, 중복 차단, `usage_type` 수정, 기본창고 전환, default 정책, 사용중지, 재활성화 흐름이다.

`DELETE` API는 제공하지 않고 `active_yn` 기반 disable/enable만 사용한다는 P0 정책도 함께 확인했다.

## 2. 검증 환경

- 검증일: 2026-05-28
- 검증 DB: 로컬 개발 DB
- 검증 계정: `local_super_admin`
- 로컬 기준 고객사: `LOCAL_TEST_CLIENT`
- 로컬 secret: `backend/local.secret.json`은 git 제외 상태 유지
- 전체 backend 테스트: `172 passed`
- `/health`: HTTP 200
- `/health` 응답 요약
  - `status=ok`
  - `app_name=SmartReturn Pro`

## 3. AuthContext 확인 결과

`/api/auth/context` 호출 결과는 고객사 사용창고 관리 API 수동 검증에 필요한 내부 운영자 권한을 만족했다.

- role: `SUPER_ADMIN`
- `permissions_count=31`
- `MASTER_VIEW=True`
- `CLIENT_MANAGE=True`
- `WAREHOUSE_MANAGE=True`
- `is_internal_user=True`
- `must_change_password=False`

로그인 흐름은 reset 이후 상태를 반영해 `current_password` 로그인 실패 후 `new_password` fallback 로그인 성공으로 처리되었고, `password_change`는 `already_reset_state`로 skip되었다.

## 4. 사전 준비 결과

- `seed_local_master_fixture.py --confirm-local-fixture` 실행 결과:
  - `LOCAL_TEST_CLIENT` 재사용
  - `active_yn=true`
- active warehouse가 3건 미만이어서 테스트용 warehouse 2건을 관리 API로 생성했다.

## 5. client_warehouse_settings API 검증 결과

다음 endpoint를 Bearer token 기반으로 수동 검증했다.

- `POST /api/master/client-warehouses`
- `PATCH /api/master/client-warehouses/{setting_id}`
- `POST /api/master/client-warehouses/{setting_id}/disable`
- `POST /api/master/client-warehouses/{setting_id}/enable`
- `POST /api/master/client-warehouses/{setting_id}/set-default`

세부 결과:

- 잘못된 `usage_type` 생성 시도
  - HTTP 400
  - `result_code=MASTER_CLIENT_WAREHOUSE_USAGE_TYPE_INVALID`
- default 설정 생성
  - HTTP 200
  - `result_code=MASTER_CLIENT_WAREHOUSE_CREATED`
- non-default 설정 생성
  - HTTP 200
  - `result_code=MASTER_CLIENT_WAREHOUSE_CREATED`
- `usage_type` 수정
  - HTTP 200
  - `result_code=MASTER_CLIENT_WAREHOUSE_UPDATED`
- 같은 `client_id + warehouse_id + usage_type` 조합 중복 생성
  - HTTP 400
  - `result_code=MASTER_CLIENT_WAREHOUSE_DUPLICATED`
- 같은 `client_id + usage_type` 범위에서 새 default 지정
  - HTTP 200
  - `result_code=MASTER_CLIENT_WAREHOUSE_DEFAULT_SET`
- set-default 후 기존 default 자동 해제
  - read-only 조회에서 기존 row `is_default=false` 확인
  - 대상 row `is_default=true` 확인
- default setting disable 시도
  - HTTP 400
  - `result_code=MASTER_CLIENT_WAREHOUSE_DEFAULT_DISABLE_DENIED`
- non-default setting disable
  - HTTP 200
  - `result_code=MASTER_CLIENT_WAREHOUSE_DISABLED`
  - `active_yn=false`
- disabled setting enable
  - HTTP 200
  - `result_code=MASTER_CLIENT_WAREHOUSE_ENABLED`
  - `active_yn=true`
  - `is_default=false` 유지

## 6. read-only 유지 확인

기존 `GET /api/master/client-warehouses?client_id=...` 동작이 유지됨을 함께 확인했다.

- active setting만 반환
- `warehouse_id`, `usage_type`, `is_default`, `active_yn` 응답 구조 유지
- set-default 이후 default 해제/전환 상태가 조회 결과에 반영됨

## 7. 오류 응답 확인

- 인증 없이 `GET /api/master/client-warehouses`
  - HTTP 401
  - `result_code=NOT_AUTHENTICATED`
- 잘못된 Bearer token으로 `GET /api/master/client-warehouses?client_id=1`
  - HTTP 401
  - `result_code=INVALID_TOKEN`

## 8. 보안 확인

수동 검증 출력과 응답 요약에서 아래 항목이 노출되지 않음을 확인했다.

- secret
- token 전체값
- password
- `password_hash`
- stack trace

`backend/local.secret.json`은 git 추적 및 커밋 대상에 포함되지 않는 상태를 유지했다.

## 9. 참고 사항

- `usage_type`는 P0에서 문자열 후보 집합으로 검증했고, 공통코드 연동은 후속 범위로 남겨둔다.
- default 1개 보장은 현재 DB partial unique index 없이 service transaction 기준으로 처리한다.
- inactive setting도 과거 이력 표시 후보가 될 수 있으나, 현재 read-only endpoint는 active setting만 반환한다. 이 부분은 후속 조회 옵션 범위로 분리한다.
