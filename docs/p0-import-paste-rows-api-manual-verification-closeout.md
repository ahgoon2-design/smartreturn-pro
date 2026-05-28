# P0 Import Paste Rows API 수동 검증 마감

## 1. 검증 목적

- `POST /api/import-jobs/{job_id}/rows/paste` 로컬 수동 검증 완료 결과를 기록한다.
- paste/grid 입력 row 저장 계약이 실제 uvicorn 서버에서 정상 동작하는지 확인했다.

## 2. 검증 환경

- 로컬 DB
- `local_super_admin`
- `backend/local.secret.json` git 제외 유지
- uvicorn 로컬 서버
- 검증 후 포트 `8000` 종료 확인

## 3. 사전 확인

- 전체 backend 테스트: `209 passed`
- `/health`: HTTP `200`
- `/api/auth/context` 확인
  - `SUPER_ADMIN`
  - `permissions_count=31`
  - `IMPORT_MANAGE=True`
  - `is_internal_user=True`
  - `must_change_password=False`
- active client 후보 확인 후 1건을 사용했다.

## 4. import job 생성 검증

- `POST /api/import-jobs` 성공
- `result_code=IMPORT_JOB_CREATED`
- `status=DRAFT`
- count/progress 초기값 `0` 확인

## 5. paste rows 저장 검증

- `POST /api/import-jobs/{job_id}/rows/paste` 성공
- `result_code=IMPORT_JOB_ROWS_SAVED`
- `saved_row_count=3`
- `status=READY_TO_VALIDATE`
- `total_rows=3`
- `parsed_rows=3`
- `valid_rows=0`
- `invalid_rows=0`
- `error_rows=0`
- `progress_percent=0`

## 6. row_no 정책 검증

- `row_no` 미전달 시 `1,2,3` 자동 부여 확인
- `row_no` 전달 시 `10,20,30` 원본값 보존 확인
- `GET /api/import-jobs/{job_id}/rows` 조회 시 `row_no asc` 정렬 확인

## 7. row 저장 상태 검증

- `validation_status=NOT_VALIDATED` 확인
- `raw_json` 보존 확인
- `normalized_json`은 요청값 또는 `null` 기준으로 보존됨을 확인
- paste 저장 단계에서 validation error가 생성되지 않음
- `GET /api/import-jobs/{job_id}/errors` 결과 `total_count=0` 확인

## 8. 차단 검증

- 기존 rows 있는 job에 재저장: HTTP `400`, `IMPORT_JOB_ROWS_ALREADY_EXISTS`
- `replace_existing=true`: HTTP `400`, `IMPORT_JOB_REPLACE_UNSUPPORTED`
- 중복 `row_no`: HTTP `400`, `IMPORT_JOB_ROW_NO_DUPLICATED`
- `row_no < 1`: HTTP `400`, `IMPORT_JOB_ROW_NO_INVALID`
- `EXCEL_FILE` source_type: HTTP `400`, `IMPORT_JOB_PASTE_SOURCE_TYPE_INVALID`
- 없는 `job_id`: HTTP `404`, `IMPORT_JOB_NOT_FOUND`
- 인증 없음: HTTP `401`, `NOT_AUTHENTICATED`
- 잘못된 토큰: HTTP `401`, `INVALID_TOKEN`

## 9. 보안 확인

- stack trace, secret, token 전체값, password, password_hash 노출 없음
- `backend/local.secret.json` 미추적/미커밋 유지

## 10. 후속 작업

- validation API skeleton 설계
- `NOT_VALIDATED`에서 `VALID`/`WARNING`/`INVALID`로 전이되는 계약 수립
- validation error 생성 정책 확정
- 파일 업로드 API skeleton은 validation 계약 이후 또는 별도 단계로 분리
