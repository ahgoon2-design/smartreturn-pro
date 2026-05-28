# P0 상품 기준정보 관리 API 수동 검증 완료 기록

이 문서는 SmartReturn Pro 신규 기준 문서이며, 기존 SmartReturn 구현 기록을 그대로 복사하지 않는다.

## 검증 목적

P0 기준정보 관리 API 1차 범위인 `products`와 `product_barcodes` 관리 API가 로컬 환경에서 실제로 동작하는지 수동 검증한 결과를 기록한다.

## 검증 환경

- 검증일: 2026-05-28
- 검증 DB: 로컬 개발 DB
- 검증 계정: `local_super_admin`
- 검증 client fixture: `LOCAL_TEST_CLIENT`
- `backend/local.secret.json`: git 제외 상태 유지
- 검증 전 전체 테스트: `125 passed`
- `/health`: HTTP 200, `status=ok`, `app_name=SmartReturn Pro`

## AuthContext 확인

- role: `SUPER_ADMIN`
- permissions count: 31
- `MASTER_VIEW`: true
- `PRODUCT_MANAGE`: true
- `is_internal_user`: true
- `must_change_password`: false

## 상품 API 검증 결과

아래 API를 Bearer token 기반으로 호출해 정상 동작을 확인했다.

- `POST /api/master/products`: HTTP 200, `MASTER_PRODUCT_CREATED`
- `POST /api/master/products`: 같은 `client_id + product_code` 중복 생성 차단, `MASTER_PRODUCT_CODE_DUPLICATED`
- `POST /api/master/products`: 같은 대표 `barcode` 중복 생성 차단, `MASTER_PRODUCT_BARCODE_DUPLICATED`
- `PATCH /api/master/products/{product_id}`: HTTP 200, `MASTER_PRODUCT_UPDATED`
- `POST /api/master/products/{product_id}/disable`: HTTP 200, `MASTER_PRODUCT_DISABLED`, `active_yn=false`
- `POST /api/master/products/{product_id}/enable`: HTTP 200, `MASTER_PRODUCT_ENABLED`, `active_yn=true`

## 상품바코드 API 검증 결과

아래 API를 Bearer token 기반으로 호출해 정상 동작을 확인했다.

- `POST /api/master/product-barcodes`: HTTP 200, `MASTER_PRODUCT_BARCODE_CREATED`
- `POST /api/master/product-barcodes`: 같은 `client_id + barcode_norm` 중복 생성 차단, `MASTER_PRODUCT_BARCODE_DUPLICATED`
- `POST /api/master/product-barcodes`: `unit_qty < 1` 요청 차단, HTTP 422
- `PATCH /api/master/product-barcodes/{barcode_id}`: HTTP 200, `MASTER_PRODUCT_BARCODE_UPDATED`
- `POST /api/master/product-barcodes/{barcode_id}/disable`: HTTP 200, `MASTER_PRODUCT_BARCODE_DISABLED`, `active_yn=false`
- `POST /api/master/product-barcodes/{barcode_id}/enable`: HTTP 200, `MASTER_PRODUCT_BARCODE_ENABLED`, `active_yn=true`

## 보안 확인

- 응답 요약에 stack trace, secret, token 전체값, password, `password_hash`가 노출되지 않음을 확인했다.
- `backend/local.secret.json`은 git 추적 및 커밋 대상에 포함되지 않았다.
- 실제 고객사 정보나 개인정보를 사용하지 않았고, 로컬 fixture 고객사만 사용했다.

## 참고 사항

- 오래된 `uvicorn` 서버가 포트 8000에 떠 있으면 최신 라우트가 없는 상태로 검증될 수 있다. 수동 검증 전 최신 코드로 서버를 재기동했는지 확인해야 한다.
- `unit_qty` validation 오류가 현재 HTTP 422로 반환된다. 이 오류를 `ApiResult` 형태로 통일할지는 후속 정책에서 검토한다.
