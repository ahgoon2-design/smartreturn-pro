# P0 Import Job Read-Only API 검증 마감

## 1. 검증 목적

- import job read-only API skeleton 구현 및 검증 완료 결과를 기록한다.
- 이번 범위에서는 업로드, 파일 파싱, 붙여넣기 paste import, 상태 전이, 업무 테이블 확정은 구현하지 않았다.
- 먼저 `import_jobs`, `import_job_rows`, `import_validation_errors` 조회 계약을 고정해 프론트 preview/검증 화면의 기준을 마련하는 것을 목표로 했다.

## 2. 구현 endpoint

- `GET /api/import-jobs`
- `GET /api/import-jobs/{job_id}`
- `GET /api/import-jobs/{job_id}/rows`
- `GET /api/import-jobs/{job_id}/errors`

## 3. 권한 / permission 정책

- 인증 필수
- `must_change_password=true` 사용자는 차단
- `IMPORT_VIEW` permission 기준으로 조회를 허용한다.
- `SUPER_ADMIN`은 전체 조회 가능
- `INTERNAL_ADMIN`은 전체 조회 가능
- `INTERNAL_WORKER`는 현재 seed 기준 `IMPORT_VIEW`가 없어 차단된다.
- `CLIENT_ADMIN`은 `IMPORT_VIEW`가 있으면 자기 `client_id` 범위만 조회 가능하다.
- `CLIENT_USER`, `READ_ONLY`는 현재 seed 기준 `IMPORT_VIEW`가 없어 차단된다.

## 4. client scope 정책

- 내부 운영자는 `client_id` query로 고객사 필터 조회가 가능하다.
- 고객사 사용자는 자기 `client_id` 범위만 조회한다.
- 고객사 사용자가 다른 `client_id`를 요청하면 `CLIENT_SCOPE_DENIED`로 차단한다.
- job detail, rows, errors 조회는 먼저 `requested_client_id` 기준으로 scope를 검증한다.
- `requested_client_id`가 `null`인 import job은 내부 운영자만 조회할 수 있다.

## 5. pagination / row order 정책

- job list 기본 정렬: `created_at desc`
- rows 기본 정렬: `row_no asc`
- errors 기본 정렬: `row_no asc`, 같은 row 안에서는 `id asc`
- `page` 기본값: `1`
- `page_size` 기본값: `50`
- `page_size` 최대값: `200`
- 원본 행 순서 보존은 프론트 preview/검증 화면에서 가장 중요한 비교 기준이므로 자동 재정렬을 허용하지 않는다.

## 6. validation error 조회 정책

- `severity`, `row_no` filter를 지원한다.
- 응답에는 아래 필드를 포함한다.
  - `row_id`
  - `row_no`
  - `field_name`
  - `raw_value`
  - `error_code`
  - `error_message`
  - `severity`
- 이 구조를 기준으로 프론트는 row preview와 error panel을 분리해 구성할 수 있다.

## 7. 검증 결과

- `tests/test_import_api_readonly.py`: `12 passed`
- 기준정보 핵심 회귀 테스트: `70 passed`
  - `tests/test_master_api_readonly.py`
  - `tests/test_master_api_manage_products.py`
  - `tests/test_master_api_manage_common_codes.py`
  - `tests/test_master_api_manage_clients.py`
  - `tests/test_master_api_manage_warehouses.py`
  - `tests/test_master_api_manage_client_warehouses.py`
- 전체 backend 테스트: `184 passed`
- `git diff --check` 통과

## 8. 보안 확인

- `backend/local.secret.json`은 미추적 / 미커밋 상태를 유지했다.
- secret, password, token, password_hash 노출은 없었다.

## 9. 후속 작업

- `POST /api/import-jobs` skeleton 설계 및 구현
- 파일 업로드, 엑셀 파싱, 붙여넣기 paste import는 후속 단계로 분리
- `import_type`별 생성 정책과 상태 전이 계약 확정 필요
