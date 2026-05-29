# Import Preview 화면 계약 초안

## 1. 문서 목적

- import preview 화면을 만들기 전에 프론트/API 표시 계약을 정리한다.
- `POST /api/import-jobs`, `POST /api/import-jobs/{job_id}/rows/paste`, `POST /api/import-jobs/{job_id}/validate`, rows 조회, errors 조회 흐름을 기준으로 화면이 어떤 데이터를 받아 어떻게 표시해야 하는지 고정한다.
- paste rows와 향후 Excel file upload가 같은 preview/validate 구조를 공유하도록 기준을 정한다.
- 화면 구현 전에 데이터 흐름, 표시 상태, 버튼 상태, 오류 표시 방식을 먼저 고정한다.

## 2. 적용 범위

- 1차 적용 import_type:
  - `PRODUCT_MASTER`
  - `PRODUCT_BARCODE`
- 향후 확장 가능한 import_type:
  - `RETURN_EXPECTED`
  - `RETURN_RECEPTION`
  - `INBOUND_EXPECTED`
  - `OUTBOUND_ORDER`
- 1차 source_type:
  - `PASTE`
- 향후 source_type:
  - `EXCEL_FILE`
- `EXCEL_FILE`은 향후 파일 업로드 skeleton에서 같은 `import_job` / rows / validation / errors 계약을 재사용한다.
- 이 문서는 화면 계약 초안이며, API 구현, DB schema, migration, seed, 프론트 코드는 변경하지 않는다.

## 3. 기본 화면 흐름

1. 고객사를 선택한다.
2. `import_type`을 선택한다.
3. `source_type`을 선택하거나 화면 진입 방식에 따라 `PASTE`로 고정한다.
4. paste 입력 영역에 원본 데이터를 붙여넣거나 그리드 입력을 준비한다.
5. 사용자가 미리보기/행 저장을 실행한다.
6. 프론트는 `POST /api/import-jobs`로 `DRAFT` job을 생성한다.
7. 프론트는 `POST /api/import-jobs/{job_id}/rows/paste`로 rows를 저장한다.
8. 저장 후 `GET /api/import-jobs/{job_id}/rows`로 원본 행 순서 preview를 표시한다.
9. 사용자가 검증 실행을 누른다.
10. 프론트는 `POST /api/import-jobs/{job_id}/validate`를 호출한다.
11. 검증 완료 후 rows와 errors를 다시 조회한다.
12. 화면은 검증 결과 요약, row별 상태, error/warning 상세를 표시한다.
13. 화면은 다음 단계 진행 가능 여부를 판단한다.

## 4. 화면 상태 정의

| 화면 상태 | 설명 | 대표 UI 동작 |
| --- | --- | --- |
| 초기 상태 | 화면 진입 직후이며 job이 없다. | 고객사/import_type/source_type 선택 영역을 표시한다. |
| 고객사 미선택 | import 대상 고객사가 없다. | 미리보기/행 저장, 검증 실행, 다음 단계 진행을 비활성화한다. |
| import_type 미선택 | import 유형이 없다. | paste 입력은 가능하더라도 저장 액션은 비활성화한다. |
| paste 입력 전 | source 데이터가 비어 있다. | 붙여넣기 안내와 비어 있는 grid preview를 표시한다. |
| paste 입력 후 rows 저장 전 | 프론트 메모리에 원본 행이 있지만 서버 저장 전이다. | 미리보기/행 저장 버튼을 활성화한다. |
| rows 저장 완료 | job status가 `READY_TO_VALIDATE`이며 row validation_status는 `NOT_VALIDATED`다. | 검증 실행 버튼을 활성화한다. |
| validate 진행 중 | 검증 API 호출 중이다. | 주요 입력과 저장/검증 버튼을 잠그고 진행 상태를 표시한다. |
| validate 완료: VALIDATED | 모든 row가 `VALID` 또는 `WARNING`이다. | 다음 단계 진행 가능 상태로 표시하되 warning이 있으면 확인 필요를 강조한다. |
| validate 완료: HAS_ERRORS | `INVALID` row가 1건 이상 있다. | 다음 단계 진행을 비활성화하고 오류 행 확인을 강조한다. |
| validate 차단 | job status, source_type, force 등 정책 위반으로 검증이 실패했다. | API result_code를 사용자 문구로 변환해 표시한다. |
| 인증 만료 또는 권한 없음 | `NOT_AUTHENTICATED`, `INVALID_TOKEN`, 권한 오류가 발생했다. | 로그인 갱신 또는 권한 문의 안내를 표시한다. |
| 서버 오류 | 예상하지 못한 5xx 또는 네트워크 오류다. | 재시도 안내와 최소 오류 문구만 표시한다. |

## 5. 버튼/액션 계약

| 액션 | 활성 조건 | 비활성/차단 조건 |
| --- | --- | --- |
| 붙여넣기 초기화 | paste 입력값 또는 저장 전 preview 데이터가 있을 때 | 검증 진행 중 |
| 미리보기/행 저장 | 고객사, `import_type`, `source_type`, paste row가 모두 있을 때 | 고객사 미선택, import_type 미선택, paste row 없음, 이미 rows 저장 완료 |
| 검증 실행 | job status가 `READY_TO_VALIDATE`이고 row가 1건 이상 저장되어 있을 때 | `DRAFT`, `VALIDATED`, `HAS_ERRORS`, `EXCEL_FILE`, row 없음, 검증 진행 중 |
| 오류 행만 보기 | errors 조회 결과에 `severity=ERROR`가 있을 때 | ERROR row가 없을 때 |
| 경고 행만 보기 | errors 조회 결과에 `severity=WARNING`이 있을 때 | WARNING row가 없을 때 |
| 전체 보기 | 필터가 적용되어 있을 때 | 전체 보기 상태 |
| 원본 순서 보기 | 사용자가 임의 정렬/필터를 적용했을 때 | 이미 `row_no asc` 기본 정렬 상태 |
| 다음 단계 진행 | status가 `VALIDATED`이고 ERROR row가 없을 때 | `HAS_ERRORS`, 검증 전, 검증 진행 중, 인증/권한 오류 |
| 취소/닫기 | 항상 가능하되 저장/검증 중에는 확인 모달 표시 | 서버 요청 진행 중 강제 이동은 확인 필요 |

## 6. 그리드 표시 계약

SmartReturn Pro 화면에서는 `SmartDataGrid` 또는 향후 공통 Grid를 기준으로 preview grid를 구성한다. 이 문서는 구현을 요구하지 않고 표시 계약만 정의한다.

필수 원칙:

- 원본 붙여넣기/엑셀 행 순서를 기본 정렬로 유지한다.
- `row_no` 또는 `original_row_no` 기준 표시가 필요하다.
- 사용자가 임의 정렬을 하더라도 원본 순서로 되돌릴 수 있어야 한다.
- 오류/경고 상태가 한눈에 보여야 한다.
- 대량 행에서도 하단 버튼과 요약 영역이 사라지면 안 된다.
- row 클릭 시 해당 row의 error/warning 상세가 패널에 연결되어야 한다.

표시 후보 컬럼:

| 컬럼 | 데이터 기준 | 표시 방향 |
| --- | --- | --- |
| 행번호 | `row_no` | 원본 순서 기준으로 고정 표시한다. |
| 상태 | `validation_status` | `VALID`, `WARNING`, `INVALID`, `NOT_VALIDATED` 뱃지로 표시한다. |
| 오류/경고 수 | errors 집계 | row별 ERROR/WARNING 건수를 표시한다. |
| product_code | `normalized_json.product_code` 또는 `raw_json.product_code` | import_type에 따라 표시한다. |
| product_name | `normalized_json.product_name` 또는 `raw_json.product_name` | 상품마스터에서 우선 표시한다. |
| barcode | `normalized_json.barcode` 또는 `raw_json.barcode` | 상품/바코드 검증에 사용한다. |
| barcode_type | `normalized_json.barcode_type` 또는 `raw_json.barcode_type` | 값이 없으면 공란으로 둔다. |
| unit_qty | `normalized_json.unit_qty` 또는 `raw_json.unit_qty` | `PRODUCT_BARCODE`에서 검증 결과와 함께 표시한다. |
| 원본값 요약 | `raw_json` | 모든 원본값을 펼치기보다 주요 필드 요약을 우선한다. |
| 처리 메시지 | `validation_message` | 대표 오류/경고 메시지 1개 또는 요약 문구를 표시한다. |

추가 검토 필요:

- API 응답에서 warning row 수가 job summary에 항상 포함되는지 확인이 필요하다.
- `raw_json`의 동적 컬럼을 grid column으로 자동 확장할지, import_type별 고정 컬럼으로 제한할지 별도 화면 정책이 필요하다.

## 7. validation_status 표시 규칙

| validation_status | 화면 문구 | 표시 방향 |
| --- | --- | --- |
| `VALID` | 정상 | 초록 계열 뱃지 또는 성공 상태로 표시한다. |
| `WARNING` | 경고 | 노랑/주황 계열 뱃지로 표시하고 다음 단계 가능 여부는 정책에 따라 허용한다. |
| `INVALID` | 오류 | 빨강 계열 뱃지로 표시하고 다음 단계 진행을 막는다. |
| `NOT_VALIDATED` | 검증 전 | 회색 계열 뱃지로 표시하고 검증 실행 필요 상태로 안내한다. |

상태 문구는 작업자가 바로 이해할 수 있는 한글을 우선한다. enum 값은 hover tooltip 또는 개발자용 상세 영역에서만 보조로 표시할 수 있다.

## 8. 오류/경고 표시 계약

`ImportValidationError`는 row별 inline 표시와 상세 패널 표시를 함께 지원해야 한다.

표시 방식:

- grid row 안에서는 ERROR/WARNING 개수와 대표 메시지를 표시한다.
- 우측 또는 하단 상세 패널에서는 선택 row의 오류/경고 목록을 표시한다.
- errors 조회 결과는 `row_id` 또는 `row_no`로 rows와 연결한다.
- `severity=ERROR`는 다음 단계 진행을 막는 오류로 표시한다.
- `severity=WARNING`은 확인 필요 항목으로 표시한다.

주요 error_code 표시 방향:

| error_code | 사용자 문구 후보 | 표시 방향 |
| --- | --- | --- |
| `REQUIRED_FIELD_MISSING` | 필수값이 없습니다. | 필드명과 함께 ERROR로 표시한다. |
| `PRODUCT_BARCODE_MISSING` | 대표 바코드가 없습니다. | `PRODUCT_MASTER`에서 WARNING으로 표시한다. |
| `INVALID_MIN_VALUE` | 허용 최소값보다 작습니다. | 수량 필드에 ERROR로 표시한다. |
| `INVALID_NUMBER` | 숫자 형식이 아닙니다. | 수량 필드에 ERROR로 표시한다. |
| 기타 확장 코드 | 확인이 필요한 항목입니다. | 알 수 없는 코드도 원문 enum과 기본 문구를 함께 표시한다. |

민감한 원문값, token, secret, password, password_hash는 grid, 상세 패널, console log에 표시하지 않는다.

## 9. 요약 카드 계약

validate 결과 후 상단 또는 고정 요약 영역에 아래 값을 표시한다.

| 항목 | 데이터 기준 | 비고 |
| --- | --- | --- |
| 전체 행 | `total_rows` | 저장된 총 row 수 |
| 정상 행 | `valid_rows` | 현재 정책상 `VALID + WARNING` 포함 |
| 경고 행 | errors 기준 WARNING row 집계 | API 필드 부족 시 프론트 집계 후보 |
| 오류 행 | `invalid_rows` | `INVALID` row 수 |
| 오류 발생 행 | `error_rows` | ERROR가 있는 row 수 |
| 진행률 | `progress_percent` | validate 완료 시 100 |
| job status | `status` | `DRAFT`, `READY_TO_VALIDATE`, `VALIDATED`, `HAS_ERRORS` 등 |
| import_type | `import_type` | 화면 템플릿/컬럼 결정에 사용 |
| source_type | `source_type` | `PASTE`, 향후 `EXCEL_FILE` |
| client | `requested_client_id`와 client 표시명 | 표시명 API/lookup은 추가 검토 필요 |

추가 검토 필요:

- backend response에 `warning_rows`가 별도 필드로 필요한지 확인한다.
- 고객사명 표시를 위해 현재 화면에서 client lookup 결과를 보관할지, job detail에 표시명을 추가할지 검토가 필요하다.

## 10. job status와 화면 전환 계약

| job status | 화면 동작 |
| --- | --- |
| `DRAFT` | job만 생성된 상태다. paste row 저장 전이면 검증 실행을 막는다. |
| `READY_TO_VALIDATE` | rows 저장 완료 상태다. 검증 실행 버튼을 활성화한다. |
| `VALIDATING` | 향후 비동기 검증에서 사용할 수 있다. 현재 skeleton에서는 즉시 처리지만 화면 상태 후보로 둔다. |
| `VALIDATED` | 검증 완료 상태다. ERROR가 없으므로 다음 단계 진행 후보가 된다. WARNING은 상세 확인을 유도한다. |
| `HAS_ERRORS` | 오류가 있는 상태다. 다음 단계 진행을 막고 오류 행 필터를 우선 제공한다. |
| `FAILED` | 서버 오류 또는 비정상 검증 실패 후보 상태다. 현재 API에서 명시 저장하지 않더라도 화면 표시 방향은 준비한다. |

차단 표시:

- 이미 검증 완료된 job 재검증 차단: “이미 검증이 완료된 자료입니다.”
- `force=true` 미지원: “강제 재검증은 아직 지원하지 않습니다.”
- `EXCEL_FILE` validate 차단: “파일 업로드 자료 검증은 파일 업로드 단계 연결 후 사용할 수 있습니다.”

## 11. 권한/인증 오류 표시 계약

| result_code 또는 상황 | 화면 문구 후보 |
| --- | --- |
| `NOT_AUTHENTICATED` | 로그인이 필요합니다. 다시 로그인해 주세요. |
| `INVALID_TOKEN` | 로그인 정보가 만료되었거나 올바르지 않습니다. 다시 로그인해 주세요. |
| 권한 없음 | 이 작업을 수행할 권한이 없습니다. 관리자에게 문의해 주세요. |
| 세션 만료 | 세션이 만료되었습니다. 저장되지 않은 입력을 확인한 뒤 다시 로그인해 주세요. |

원칙:

- secret, token 전체값, password, password_hash는 화면과 로그에 절대 노출하지 않는다.
- 인증/권한 오류는 상세 stack trace 대신 사용자 문구와 result_code만 표시한다.
- 재로그인 후 같은 화면으로 복귀할 수 있는지는 후속 UX 정책에서 정한다.

## 12. PASTE와 EXCEL_FILE 공통화 방향

- `PASTE`는 현재 구현된 rows 저장/validate 흐름을 사용한다.
- `EXCEL_FILE`은 다음 skeleton에서 파일 업로드 후 같은 `import_job` / rows / validate 구조로 연결한다.
- 프론트 preview 화면은 source_type이 달라도 동일한 결과 grid와 오류 패널을 재사용해야 한다.
- 파일 업로드 전용 UI와 검증 결과 UI를 분리한다.
- 파일 선택, 업로드 진행률, worksheet 선택은 `EXCEL_FILE` 전용 영역에서 처리한다.
- rows 저장 이후 preview grid, validation summary, errors panel은 `PASTE`와 `EXCEL_FILE`이 공유한다.

## 13. 추천 화면 구조

텍스트 와이어프레임:

```text
[상단 고정 영역]
  고객사 선택 | import_type | source_type | job status | 전체/정상/경고/오류 요약

[입력 영역]
  PASTE: 붙여넣기 입력 또는 편집 가능한 원본 입력 그리드
  EXCEL_FILE: 파일 업로드 영역(후속)

[preview grid]
  row_no | 상태 | 오류/경고 수 | product_code | product_name | barcode | unit_qty | 메시지

[오류/경고 상세 패널]
  선택 row의 ERROR/WARNING 목록
  전체 오류 목록 필터: 전체 / 오류 / 경고

[하단 고정 action bar]
  붙여넣기 초기화 | 미리보기/행 저장 | 검증 실행 | 오류 행만 보기 | 전체 보기 | 다음 단계 진행 | 취소
```

1366x768 기준으로 핵심 입력, grid 첫 5행, 오류/경고 상세 또는 요약, 하단 action bar가 보여야 한다. 대량 행에서도 주요 버튼이 사라지지 않도록 sticky/fixed action bar가 필요하다.

## 14. 구현 전 확인해야 할 API 계약

현재 API 응답에서 프론트가 반드시 필요로 하는 필드:

- job 생성/상세:
  - `id`
  - `import_type`
  - `source_type`
  - `requested_client_id`
  - `status`
  - `total_rows`
  - `parsed_rows`
  - `valid_rows`
  - `invalid_rows`
  - `error_rows`
  - `progress_percent`
- rows 조회:
  - `id`
  - `job_id`
  - `row_no`
  - `raw_json`
  - `normalized_json`
  - `validation_status`
  - `validation_message`
- errors 조회:
  - `id`
  - `job_id`
  - `row_id`
  - `row_no`
  - `field_name`
  - `raw_value`
  - `error_code`
  - `error_message`
  - `severity`
- pagination:
  - `page`
  - `page_size`
  - `total_count`
  - 전체 page 계산에 필요한 metadata

추가 검토 필요:

- `warning_rows`를 API response에서 직접 제공할지, 프론트가 errors 조회 결과로 집계할지 결정이 필요하다.
- row별 ERROR/WARNING count를 rows response에 포함할지 검토가 필요하다.
- client 표시명을 job detail에 포함할지, 별도 lookup으로 해결할지 결정이 필요하다.
- import_type별 화면 컬럼 정의를 API metadata로 내려줄지, 프론트 상수로 둘지 결정이 필요하다.

## 15. closeout 결론

이 문서는 화면 구현 전 계약 초안이다. paste rows 저장과 validation 결과를 화면에서 일관되게 표시하기 위한 데이터 흐름, 상태, 버튼, grid, 오류/경고 표시 기준을 먼저 정리했다.

다음 단계는 이 문서를 기준으로 프론트 import preview 화면 skeleton 구현 또는 API 응답 필드 보강 여부를 판단하는 것이다.

추천 다음 작업은 “프론트 import preview 화면 skeleton 구현”이다. 단, `warning_rows`, row별 오류/경고 count, client 표시명처럼 API 필드 부족이 실제 화면 구현을 막는다고 판단되면 skeleton 전에 API 응답 보강 작업을 먼저 해야 한다.
