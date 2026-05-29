# Import Preview SmartDataGrid 전환 마감

## 1. 작업 목적

기존 Import Preview 화면을 새 `SmartDataGrid` 계약에 맞게 정리했다.

이번 작업은 파일 업로드, 기준정보 화면, 입고/출고/반품 화면을 구현하는 작업이 아니다. 기존 `POST /api/import-jobs`, `POST /api/import-jobs/{job_id}/rows/paste`, `POST /api/import-jobs/{job_id}/validate`, rows/errors 조회 흐름은 유지하면서 grid 표시 계약만 정리했다.

## 2. 변경 전 Import Preview grid 상태

변경 전 `frontend/src/features/import/ImportPreviewPage.tsx`에는 아래 grid 전용 로직이 화면 파일 안에 함께 있었다.

- `SmartDataGridColumn` column 정의
- `row_no` 정렬과 전체/오류/경고 필터 로직
- row별 errors 연결 로직
- row별 warning/error count 계산
- 주요 필드 읽기 로직
- validation message 표시 로직

`SmartDataGrid` wrapper는 이미 사용 중이었으나, Import Preview의 grid 정책이 화면 파일 안에 섞여 있어 후속 화면 재사용성이 낮았다.

## 3. SmartDataGrid 전환 내용

Import Preview 전용 grid helper를 추가했다.

- `frontend/src/features/import/importPreviewGrid.tsx`

이 파일로 아래 책임을 옮겼다.

- `SmartDataGridColumn` 생성
- row 필터링
- row별 errors 연결
- row별 severity 판정
- row className 결정
- warning row count 계산
- 주요 row value 표시

`ImportPreviewPage.tsx`는 API 호출, 화면 상태, 액션 흐름을 계속 담당하고, grid 표시 정책은 helper로 분리했다.

## 4. column 정의 정리 내용

Import Preview grid column은 `SmartDataGridColumn<ImportJobRow>` 기준으로 정리했다.

필수 column:

- `row_no`
- `validation_status`
- `product_code`
- `product_name`
- `barcode`
- `barcode_type`
- `unit_qty`
- `validation_message`
- 오류/경고 count

`validation_status`는 `renderType="status"`를 사용해 `SmartGridStatusCell` / `SmartStatusBadge` 경로로 표시한다.

`product_code`, `product_name`, `barcode`, `barcode_type`, `unit_qty`는 `copyable=true`를 적용했다.

## 5. 원본 row_no 순서 보존 적용 내용

Import Preview grid는 아래 `SmartDataGrid` 옵션을 사용한다.

- `preserveOriginalOrder`
- `originalOrderKey="row_no"`
- `enableOriginalOrderReset`

필터링은 `filterImportPreviewRows` helper에서 수행하며, 필터 적용 후에도 `row_no asc` 기준을 유지한다.

`rows` 원본 배열을 직접 mutate하지 않고 복사본을 정렬한다.

## 6. validation_status 표시 통일 내용

상태 표시는 `SmartDataGridColumn`의 `renderType="status"`를 통해 공통 badge 흐름으로 통일했다.

표시 기준:

- `VALID`: 정상
- `WARNING`: 경고
- `INVALID`: 오류
- `NOT_VALIDATED`: 검증 전

상태 문구와 색상은 `SmartStatusBadge` 기준을 따른다.

## 7. 오류/경고 표시 정리 내용

errors 조회 결과는 기존과 동일하게 `row_id`, `id`, `row_no` 기준으로 rows와 연결한다.

정리한 기준:

- `severity=ERROR` 또는 `validation_status=INVALID`이면 error row
- `severity=WARNING` 또는 `validation_status=WARNING`이면 warning row
- 오류/경고 count column 유지
- 처리 메시지 column은 `validation_message`가 있으면 우선 표시하고, 없으면 error_code 목록을 표시
- 오류 row와 경고 row는 `SmartDataGrid` row className으로 강조
- 오류/경고 count와 처리 메시지 cell에도 highlight 기준을 적용

기존 주요 error_code 표시 구조는 유지한다.

- `REQUIRED_FIELD_MISSING`
- `PRODUCT_BARCODE_MISSING`
- `INVALID_MIN_VALUE`
- `INVALID_NUMBER`

row별 ERROR/WARNING count가 API에 직접 포함되어 있지는 않으므로, 현재는 errors 조회 결과를 기반으로 안전하게 계산한다. 이 항목은 후속 API 보강 후보로 유지한다.

## 8. 전체/오류/경고 필터 유지 확인

기존 필터는 유지했다.

- 전체 보기
- 오류 행만 보기
- 경고 행만 보기

필터 상태는 화면 외부 state로 유지하고, 실제 row 필터링은 `filterImportPreviewRows` helper로 분리했다. 필터 전환 후에도 `row_no` 원본 순서가 유지된다.

## 9. copyable cell 적용 내용

아래 column에 `copyable=true`를 적용했다.

- `product_code`
- `product_name`
- `barcode`
- `barcode_type`
- `unit_qty`

token, password, secret, password_hash와 관련된 값은 grid column에 포함하지 않았고, 복사 대상으로 만들지 않았다.

## 10. API 흐름 유지 여부

아래 API 흐름은 변경하지 않았다.

- `GET /api/master/clients`
- `POST /api/import-jobs`
- `POST /api/import-jobs/{job_id}/rows/paste`
- `POST /api/import-jobs/{job_id}/validate`
- `GET /api/import-jobs/{job_id}/rows`
- `GET /api/import-jobs/{job_id}/errors`

API path, request body, response 처리 흐름은 그대로 유지했다.

## 11. 미구현/후속 항목

- row별 ERROR/WARNING count를 API response에 포함할지 검토
- job summary의 `warning_rows` 표준화
- selected row와 오류/경고 상세 패널 직접 연동
- `SmartGridExportButton` 또는 엑셀 다운로드 버튼
- 파일 업로드 `EXCEL_FILE` preview 연결
- Import Preview의 source_type별 column metadata 분리

## 12. 검증 결과

- `npm.cmd run typecheck`: 통과
- `npm.cmd run build`: 통과
- `git diff --check`: 통과

backend 코드는 변경하지 않아 backend pytest는 생략했다.

## 13. 다음 추천 작업

1. 기준정보 화면 디자인 토론
2. 파일 업로드 `EXCEL_FILE` skeleton 설계
3. 기준정보 화면 중 고객사/창고/상품 중 첫 화면 구현 후보 선정
