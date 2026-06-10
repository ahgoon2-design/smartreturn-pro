# Import Validation API 로컬 수동 검증 마감

## 1. 문서 목적

- `POST /api/import-jobs/{job_id}/validate` 로컬 E2E 수동 검증 완료 결과를 기록한다.
- 프론트 preview 화면 계약 또는 파일 업로드 skeleton으로 넘어가기 전에 import validation API의 실제 동작 안정성을 확인했다.

## 2. 검증 환경

- 저장소: `C:\smartreturn-pro`
- remote: `origin https://github.com/ahgoon2-design/smartreturn-pro.git`
- branch: `main`
- 서버 실행 방식: Python `subprocess.Popen`
- PowerShell `Start-Process`는 사용하지 않았다.
- uvicorn 실행 기준:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- `backend/local.secret.json`은 존재하지만 `.gitignore` 제외 대상이며, tracked/staged 상태가 아니었다.

## 3. 자동 테스트 결과

```powershell
.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider
```

- 결과: `226 passed`

## 4. 기본 API 확인

- `/health`: HTTP `200`, `status=ok`, `app_name=SmartReturn Pro`
- `/api/auth/context`
  - `SUPER_ADMIN`
  - `permissions_count=31`
  - `IMPORT_MANAGE=True`
  - `is_internal_user=True`
  - `must_change_password=False`
- active client
  - `LOCAL_TEST_CLIENT` 확인 및 사용

## 5. VALID 케이스 결과

- `import_type=PRODUCT_MASTER`
- `source_type=PASTE`
- `product_code`, `product_name`, `barcode` 있음
- 기대 및 실제 결과
  - `result_code=IMPORT_JOB_VALIDATED`
  - `status=VALIDATED`
  - row `validation_status=VALID`
  - `valid_rows=1`
  - `invalid_rows=0`
  - `error_rows=0`
  - `progress_percent=100`
  - errors `total_count=0`

## 6. WARNING 케이스 결과

- `import_type=PRODUCT_MASTER`
- `barcode` 없음
- 기대 및 실제 결과
  - `status=VALIDATED`
  - row `validation_status=WARNING`
  - `valid_rows=1`
  - `warning_rows=1`
  - `invalid_rows=0`
  - errors `severity=WARNING`
  - error code: `PRODUCT_BARCODE_MISSING`

## 7. INVALID 케이스 결과

- `import_type=PRODUCT_MASTER`
- `product_name` 누락
- 기대 및 실제 결과
  - `status=HAS_ERRORS`
  - row `validation_status=INVALID`
  - `invalid_rows=1`
  - `error_rows=1`
  - `progress_percent=100`
  - errors `severity=ERROR`
  - error code: `REQUIRED_FIELD_MISSING`

## 8. PRODUCT_BARCODE unit_qty 검증 결과

- `import_type=PRODUCT_BARCODE`
- `unit_qty=0`
- 기대 및 실제 결과
  - `status=HAS_ERRORS`
  - row `validation_status=INVALID`
  - error code: `INVALID_MIN_VALUE`

## 9. 차단 검증 결과

- DRAFT job validate
  - HTTP `400`
  - `IMPORT_JOB_VALIDATE_STATUS_INVALID`
- `EXCEL_FILE` source_type job validate
  - HTTP `400`
  - `IMPORT_JOB_VALIDATE_SOURCE_TYPE_INVALID`
- rows 없는 `READY_TO_VALIDATE` job validate
  - HTTP `400`
  - `IMPORT_JOB_VALIDATE_NO_ROWS`
  - 이 케이스는 public API로 만들 수 없는 상태라 API로 생성한 검증용 job의 status만 로컬 DB에서 보정해 확인했다.
  - row insert/delete는 하지 않았다.
- 이미 검증 완료된 job validate 재실행
  - HTTP `400`
  - `IMPORT_JOB_VALIDATE_ALREADY_DONE`
- `force=true`
  - HTTP `400`
  - `IMPORT_JOB_VALIDATE_FORCE_UNSUPPORTED`
- 없는 `job_id`
  - HTTP `404`
  - `IMPORT_JOB_NOT_FOUND`
- 인증 없음
  - HTTP `401`
  - `NOT_AUTHENTICATED`
- 잘못된 토큰
  - HTTP `401`
  - `INVALID_TOKEN`

## 10. 보안 및 정리 확인

- stack trace 노출 없음
- 실제 secret, token 전체값, password 값, password_hash 노출 없음
- uvicorn subprocess 종료 완료
- 포트 `8000` LISTEN 없음
- 최종 `git status --short` clean 확인

## 11. closeout 결론

- import validation API는 `PRODUCT_MASTER` 기본 검증, 경고, 오류, `PRODUCT_BARCODE` `unit_qty` 오류, 인증/권한/상태 차단까지 로컬 E2E 기준으로 통과했다.
- 다음 단계로 프론트 preview 화면 계약 초안 또는 파일 업로드 skeleton 설계로 넘어갈 수 있다.
- 우선 추천은 프론트 preview 화면 계약 초안이다. paste rows와 validate 결과를 화면에서 어떻게 표시할지 계약을 먼저 고정해야 파일 업로드 skeleton도 같은 preview/validation 구조로 연결하기 쉽다.
