# P0 고객사/창고 관리 API 수동 검증 완료 기록

## 1. 검증 목적

이 문서는 SmartReturn Pro P0 기준정보 관리 API 중 `clients` / `warehouses` 관리 API의 수동 검증 완료 결과를 기록한다.

검증 대상은 고객사와 창고 기준정보의 생성, 중복 차단, 수정, 사용중지, 재활성화 흐름이다. `client_warehouse_settings`는 기본창고 1개 정책과 warehouse scope가 엮여 있어 후속 설계 및 구현 범위로 분리한다.

## 2. 검증 환경

- 검증일: 2026-05-28
- 검증 DB: 로컬 개발 DB
- 검증 계정: `local_super_admin`
- 로컬 secret: `backend/local.secret.json`은 git 제외 상태 유지
- 전체 backend 테스트: `157 passed`
- health check: `/health` HTTP 200
- health 응답 요약:
  - `status=ok`
  - `app_name=SmartReturn Pro`

## 3. AuthContext 확인 결과

`/api/auth/context` 호출 결과는 기준정보 관리 API 수동 검증에 필요한 내부 운영자 권한을 만족했다.

- role: `SUPER_ADMIN`
- `permissions_count=31`
- `MASTER_VIEW=True`
- `CLIENT_MANAGE=True`
- `WAREHOUSE_MANAGE=True`
- `is_internal_user=True`
- `must_change_password=False`

## 4. clients API 검증 결과

고객사 관리 API는 아래 항목을 수동 검증했다.

- `POST /api/master/clients`
  - HTTP 200
  - `result_code=MASTER_CLIENT_CREATED`
- 같은 `client_code` 중복 생성
  - HTTP 400 차단 확인
- `PATCH /api/master/clients/{client_id}`
  - HTTP 200
  - `result_code=MASTER_CLIENT_UPDATED`
- `client_code` 변경 시도
  - 기존 `client_code` 값 유지 확인
- `POST /api/master/clients/{client_id}/disable`
  - HTTP 200
  - `result_code=MASTER_CLIENT_DISABLED`
  - `active_yn=false`
- `POST /api/master/clients/{client_id}/enable`
  - HTTP 200
  - `result_code=MASTER_CLIENT_ENABLED`
  - `active_yn=true`

## 5. warehouses API 검증 결과

창고 관리 API는 아래 항목을 수동 검증했다.

- `POST /api/master/warehouses`
  - HTTP 200
  - `result_code=MASTER_WAREHOUSE_CREATED`
- 같은 `warehouse_code` 중복 생성
  - HTTP 400 차단 확인
- `PATCH /api/master/warehouses/{warehouse_id}`
  - HTTP 200
  - `result_code=MASTER_WAREHOUSE_UPDATED`
- `warehouse_code` 변경 시도
  - 기존 `warehouse_code` 값 유지 확인
- `POST /api/master/warehouses/{warehouse_id}/disable`
  - HTTP 200
  - `result_code=MASTER_WAREHOUSE_DISABLED`
  - `active_yn=false`
- `POST /api/master/warehouses/{warehouse_id}/enable`
  - HTTP 200
  - `result_code=MASTER_WAREHOUSE_ENABLED`
  - `active_yn=true`

## 6. 보안 확인

수동 검증 중 응답 요약과 콘솔 출력에서 아래 항목이 노출되지 않음을 확인했다.

- stack trace
- secret
- token 전체값
- password
- password_hash

`backend/local.secret.json`은 git 추적 및 커밋 대상에 포함되지 않는 상태를 유지했다.

## 7. 참고 사항

- 중복 차단은 HTTP 400으로 확인했으나 추가 파싱 확인 명령 출력은 잡히지 않아 status 중심으로 기록한다.
- `client_warehouse_settings`는 기본창고 1개 정책, active 연결, warehouse scope와 연결되므로 후속 설계 및 구현 범위로 분리한다.
- P0 정책에 따라 고객사/창고 관리 API는 DELETE 없이 `active_yn` 기반 disable/enable만 사용한다.
