# P0 Import Paste Rows API 검증 마감

## 1. 검증 목적

- `POST /api/import-jobs/{job_id}/rows/paste` 구현 및 검증 완료 결과를 기록한다.
- 이번 범위에서는 파일 업로드, 엑셀 파싱, validation, confirm을 구현하지 않았다.
- paste/grid 입력 row 저장 계약만 먼저 고정했다.

## 2. 구현 endpoint

- `POST /api/import-jobs/{job_id}/rows/paste`

## 3. API 역할

- 이미 생성된 import job에 붙여넣기 또는 그리드 입력 row 데이터를 저장한다.
- 파일 업로드와 엑셀 파싱은 수행하지 않는다.
- 업무 테이블 저장은 수행하지 않는다.
- validation 실행은 수행하지 않는다.
- 저장된 row는 `GET /api/import-jobs/{job_id}/rows`에서 `row_no asc` 순서로 조회할 수 있다.

## 4. validation_status 초기값

- `validation_status=NOT_VALIDATED`를 사용한다.
- row 저장 직후에는 아직 validation 전 단계다.
- `VALID`, `WARNING`, `INVALID`는 검증 이후 상태로 사용한다.
- `PENDING`보다 `NOT_VALIDATED`가 "검증하지 않음"을 더 명확하게 표현한다.

## 5. source_type 제한

허용:

- `PASTE`
- `MANUAL`

차단:

- `EXCEL_FILE`
- `GOOGLE_SHEET`
- `API`

`EXCEL_FILE`은 후속 files API로 분리한다.

## 6. row_no 정책

- `row_no` 미전달 시 서버가 입력 순서대로 `1..N`을 자동 부여한다.
- `row_no` 전달 시 원본값을 보존한다.
- 요청 내부 중복 `row_no`는 차단한다.
- `row_no < 1`은 차단한다.
- 저장 시 요청 순서를 임의 정렬하지 않는다.
- 조회 API는 기존 정책대로 `row_no asc` 정렬을 사용한다.

## 7. 기존 row 처리 정책

- 기존 rows가 있는 job에는 paste row 저장을 차단한다.
- `replace_existing=true`는 차단한다.
- append는 지원하지 않는다.
- 기존 rows/errors 삭제는 수행하지 않는다.
- replace/delete/append는 후속 명시 정책에서 다룬다.

## 8. 저장 후 job 상태/count 정책

- `status=READY_TO_VALIDATE`
- `total_rows=저장 row 수`
- `parsed_rows=저장 row 수`
- `valid_rows=0`
- `invalid_rows=0`
- `error_rows=0`
- `progress_percent=0`
- `inserted_rows`, `updated_rows`, `skipped_rows`는 0을 유지한다.

## 9. validation error 정책

- paste row 저장 단계에서는 `ImportValidationError`를 생성하지 않는다.
- errors는 후속 validation API 단계에서 생성한다.

## 10. 검증 결과

- `tests/test_import_api_paste_rows.py`: `13 passed`
- `tests/test_import_api_create.py` + `tests/test_import_api_readonly.py`: `24 passed`
- 기준정보 핵심 테스트: `70 passed`
  - `tests/test_master_api_readonly.py`
  - `tests/test_master_api_manage_products.py`
  - `tests/test_master_api_manage_common_codes.py`
  - `tests/test_master_api_manage_clients.py`
  - `tests/test_master_api_manage_warehouses.py`
  - `tests/test_master_api_manage_client_warehouses.py`
- 전체 backend 테스트: `209 passed`
- `git diff --check` 통과

## 11. 보안 확인

- `backend/local.secret.json`은 미추적/미커밋 상태를 유지했다.
- secret, password, token, password_hash 노출은 없었다.

## 12. 후속 작업

- paste rows API 수동 검증
- validation API skeleton 설계
- `POST /api/import-jobs/{job_id}/files` skeleton 설계
- `import_type`별 row validation/status 전이 계약 확정
