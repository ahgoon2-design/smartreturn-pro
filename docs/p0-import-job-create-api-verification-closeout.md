# P0 Import Job Create API 검증 마감

## 1. 검증 목적

- `POST /api/import-jobs` 생성 skeleton 구현 및 검증 완료 결과를 기록한다.
- 이번 범위에서는 업로드, 파싱, row 저장, validation, confirm을 구현하지 않았고, import job 부모 껍데기 생성 계약만 먼저 고정했다.

## 2. 구현 endpoint

- `POST /api/import-jobs`

## 3. 생성 API 역할

- import job 부모 껍데기를 생성한다.
- 이후 파일 첨부, row 저장, validation, confirm 단계의 기준 job으로 사용한다.
- 업무 테이블 저장은 수행하지 않는다.
- 생성 직후 status는 `DRAFT`로 시작한다.

## 4. import_type allowlist

- `PRODUCT_MASTER`
- `PRODUCT_BARCODE`
- `RETURN_EXPECTED`
- `RETURN_RECEPTION`
- `INBOUND_EXPECTED`
- `OUTBOUND_ORDER`

허용되지 않은 값은 표준 `400` 오류로 차단한다.

## 5. source_type allowlist

- `EXCEL_FILE`
- `PASTE`
- `MANUAL`

이번 단계에서 아래 값은 허용하지 않는다.

- `GOOGLE_SHEET`
- `API`

허용되지 않은 값은 표준 `400` 오류로 차단한다.

## 6. requested_client_id 정책

- 내부 운영자도 1차에서는 `requested_client_id`가 필수다.
- 지정된 `requested_client_id`는 존재해야 하며 `active_yn=true` 검증을 통과해야 한다.
- 고객사 사용자 생성은 이번 단계에서 차단한다.
- 내부 공통 `null` client job은 후속 단계로 보류한다.

## 7. requested_warehouse_id 정책

- `requested_warehouse_id`는 optional이다.
- 값이 있으면 warehouse 존재 여부와 `active_yn=true`를 검증한다.
- `client_warehouse_settings` active 연결 검증은 이번 단계에서 강제하지 않는다.
- client/warehouse 연결 검증은 후속 import_type별 상세 정책 단계에서 추가한다.

## 8. 권한 / permission 정책

- 인증 필수
- `must_change_password` 차단
- `IMPORT_MANAGE` 필요
- `SUPER_ADMIN` 허용
- `INTERNAL_ADMIN + IMPORT_MANAGE` 허용
- `INTERNAL_WORKER`, `CLIENT_ADMIN`, `CLIENT_USER`, `READ_ONLY` 차단
- `IMPORT_VIEW`만으로는 생성할 수 없다.

## 9. 초기값 정책

- `status=DRAFT`
- `total_rows=0`
- `parsed_rows=0`
- `valid_rows=0`
- `invalid_rows=0`
- `inserted_rows=0`
- `updated_rows=0`
- `skipped_rows=0`
- `error_rows=0`
- `progress_percent=0`
- `started_at=null`
- `finished_at=null`

## 10. 검증 결과

- `tests/test_import_api_create.py`: `12 passed`
- `tests/test_import_api_readonly.py`: `12 passed`
- 기준정보 핵심 회귀 테스트: `70 passed`
  - `tests/test_master_api_readonly.py`
  - `tests/test_master_api_manage_products.py`
  - `tests/test_master_api_manage_common_codes.py`
  - `tests/test_master_api_manage_clients.py`
  - `tests/test_master_api_manage_warehouses.py`
  - `tests/test_master_api_manage_client_warehouses.py`
- 전체 backend 테스트: `196 passed`
- `git diff --check` 통과

## 11. 보안 확인

- `backend/local.secret.json`은 미추적 / 미커밋 상태를 유지했다.
- secret, password, token, password_hash 노출은 없었다.

## 12. 후속 작업

- `POST /api/import-jobs/{job_id}/files` skeleton 설계
- paste row 저장 skeleton 설계
- `import_type`별 row 저장 / validation / status 전이 계약 확정
- 파일 업로드, 엑셀 파싱, 붙여넣기 단계는 후속으로 분리
