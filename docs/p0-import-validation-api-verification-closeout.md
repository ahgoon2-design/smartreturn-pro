# P0 Import Validation API 검증 마감

## 1. 검증 목적

- `POST /api/import-jobs/{job_id}/validate` 구현 및 검증 완료 결과를 기록한다.
- paste/manual로 저장된 import rows를 검증해 row `validation_status`, `ImportValidationError`, `ImportJob` count/status를 갱신하는 계약을 고정했다.
- 파일 업로드, 엑셀 파싱, confirm, master data 매칭은 이번 범위에서 제외했다.

## 2. 구현 endpoint

- `POST /api/import-jobs/{job_id}/validate`

## 3. validation 실행 범위

- `PASTE`, `MANUAL` source_type만 허용한다.
- `READY_TO_VALIDATE` 상태만 허용한다.
- `NOT_VALIDATED` row만 검증 대상으로 삼는다.
- 공통 구조와 `import_type`별 최소 필드 검증만 수행한다.
- master data 매칭, 업무 테이블 저장, confirm은 후속 범위로 분리한다.

## 4. validation_status 전이

- `NOT_VALIDATED` -> `VALID`
- `NOT_VALIDATED` -> `WARNING`
- `NOT_VALIDATED` -> `INVALID`
- `ERROR`가 하나라도 있으면 `INVALID`를 우선한다.
- `WARNING`만 있으면 `WARNING`으로 둔다.
- 오류/경고가 없으면 `VALID`로 둔다.

## 5. ImportValidationError 생성 정책

- severity는 `ERROR`, `WARNING`을 사용한다.
- `ERROR`가 존재하는 row는 `INVALID`로 전환한다.
- `WARNING`만 존재하는 row는 `WARNING`으로 전환한다.
- 오류가 없는 row는 `VALID`로 전환한다.
- validation 재실행은 1차에서 차단한다.
- `force=true` 요청도 1차에서 차단한다.

## 6. job status/count 업데이트 정책

- 모든 row가 `VALID` 또는 `WARNING`이면 `status=VALIDATED`로 갱신한다.
- `INVALID` row가 하나라도 있으면 `status=HAS_ERRORS`로 갱신한다.
- `valid_rows`는 `VALID + WARNING` row 수로 집계한다.
- `invalid_rows`는 `INVALID` row 수로 집계한다.
- `error_rows`는 `ERROR`가 있는 row 수로 집계한다.
- `progress_percent=100`으로 갱신한다.
- `inserted_rows`, `updated_rows`, `skipped_rows`는 업무 저장 전이므로 `0`을 유지한다.

## 7. import_type별 최소 검증

### PRODUCT_MASTER

- `product_code` 필수
- `product_name` 필수
- `barcode` 없음은 `WARNING`

### PRODUCT_BARCODE

- `product_code` 필수
- `barcode` 필수
- `unit_qty`가 있으면 숫자이며 `1` 이상

### RETURN_RECEPTION

- `tracking_no` 또는 `invoice_no` 중 하나 필수
- `product_code` 또는 `barcode` 중 하나 필수

### RETURN_EXPECTED

- `tracking_no` 또는 `invoice_no` 중 하나 필수

### INBOUND_EXPECTED

- `product_code` 필수
- `expected_qty` 필수, 숫자이며 `1` 이상

### OUTBOUND_ORDER

- `order_no` 또는 `tracking_no` 중 하나 필수
- `product_code` 필수

## 8. 검증 결과

- `tests/test_import_api_validate.py`: `17 passed`
- import read-only/create/paste 테스트: `37 passed`
- 기준정보 핵심 회귀 테스트: `70 passed`
- 전체 backend 테스트: `226 passed`
- `git diff --check` 통과

## 9. 보안 확인

- `backend/local.secret.json` 미추적/미커밋 상태를 유지했다.
- secret, password, token, password_hash 노출은 없었다.

## 10. 후속 작업

- validation API 수동 검증
- validation 결과 closeout 문서화
- 파일 업로드 API skeleton 설계
- 또는 프론트 preview 화면 계약 초안 정리
- confirm/save API는 validation 수동 검증 이후 별도 설계
