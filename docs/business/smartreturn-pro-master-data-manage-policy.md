# SmartReturn Pro 기준정보 관리 정책

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

## 1. 문서 목적과 적용 범위

이 문서는 P0 기준정보 create/update/disable API skeleton 구현 전에 따라야 할 관리 기준을 정리한다. P0 기준정보 read-only API는 수동 검증을 완료했으며, 이 문서는 생성, 수정, 사용중지, 재활성화 API를 만들기 전의 정책 기준이다.

적용 범위는 아래 P0 기준정보 테이블이다.

- `clients`
- `warehouses`
- `client_warehouse_settings`
- `products`
- `product_barcodes`
- `common_code_groups`
- `common_codes`

이 문서는 API 구현 문서가 아니다. 이번 기준에 따라 후속 작업에서 schema, service, repository, router skeleton을 작성한다.

## 2. 공통 관리 원칙

- 기준정보는 물리 삭제보다 `active_yn=false` 사용중지를 기본으로 한다.
- 업무 데이터, 입고, 출고, 반품, 재고, import, scan 이력과 연결된 기준정보는 물리 삭제하지 않는다.
- 생성, 수정, 사용중지, 재활성화는 별도 행위로 분리한다.
- P0에서는 DELETE API를 제공하지 않는다.
- 프론트가 보낸 `client_id`를 신뢰하지 않고 서버의 `AuthContext`와 effective client scope 기준으로 검증한다.
- 과거 이력 조회에서는 사용중지된 기준정보도 표시되어야 한다.
- 신규 업무 선택에서는 사용중지 기준정보를 기본 제외한다.
- 사용중지된 기준정보를 다시 사용할 필요가 있으면 별도 enable API로 재활성화한다.

## 3. 삭제 금지와 사용중지 기준

DELETE API는 P0에서 미지원한다. 기준정보 삭제가 쉬워지면 과거 반품, 입고, 출고, 재고, import, scan 이력의 참조 무결성이 깨질 수 있다.

사용중지는 아래 의미를 가진다.

- 신규 업무 선택 제한
- 과거 이력 조회 유지
- 기존 업무 데이터 참조 무결성 유지
- 운영자가 잘못 등록한 기준정보를 신규 사용 대상에서 제외

재활성화는 가능 후보로 둔다. 다만 재활성화 전에 코드 중복, scope, 연결 대상 상태, 현재 업무 정책과 충돌하지 않는지 다시 검증해야 한다.

물리 삭제는 테스트 데이터 초기화나 로컬 개발 도구에서만 검토할 수 있다. 운영 API로 제공하지 않는다.

## 4. 권한, role, permission 기준

기준정보 조회는 `MASTER_VIEW`를 사용한다. 기준정보 관리는 관리 대상별 permission을 함께 확인한다.

| 작업 범위 | 필요 permission |
| --- | --- |
| 기준정보 조회 | `MASTER_VIEW` |
| 기준정보 포괄 관리 | `MASTER_MANAGE` |
| 고객사 관리 | `CLIENT_MANAGE` |
| 창고/고객사 사용창고 관리 | `WAREHOUSE_MANAGE` |
| 상품/상품바코드 관리 | `PRODUCT_MANAGE` |
| 공통코드 관리 | `COMMON_CODE_MANAGE` |

role 기준은 아래와 같다.

| role | 관리 API 기준 |
| --- | --- |
| `SUPER_ADMIN` | 전체 기준정보 관리 가능. 단, 위험 작업은 대상별 permission과 감사 기준을 함께 적용한다. |
| `INTERNAL_ADMIN` | 필요한 관리 permission이 있으면 P0 기준정보 관리 가능. |
| `INTERNAL_WORKER` | P0에서는 조회 중심이다. 기준정보 생성/수정/사용중지 권한을 기본 부여하지 않는다. |
| `CLIENT_ADMIN` | P0에서는 기준정보 관리 불가. 자기 고객사 정보도 직접 수정하지 않는다. |
| `CLIENT_USER` | 기준정보 관리 불가. 자기 `client_id` 범위 조회 중심이다. |
| `READ_ONLY` | 조회만 가능하고 모든 쓰기 작업은 금지한다. |

후속 고객사 포털에서 고객사 상품 등록을 허용해야 한다면 `CLIENT_PRODUCT_MANAGE` 같은 별도 permission 후보를 검토할 수 있다. P0 seed에는 추가하지 않는다.

## 5. 고객사 `clients` 관리 정책

- 생성/수정/사용중지 권한은 `SUPER_ADMIN` 또는 `INTERNAL_ADMIN` 중 `CLIENT_MANAGE` 권한을 가진 사용자에게 부여한다.
- `CLIENT_ADMIN`, `CLIENT_USER`는 P0에서 자기 고객사 정보도 수정할 수 없다.
- `client_code`는 생성 후 변경 금지를 기본으로 한다. 변경이 꼭 필요하면 운영 승인과 이력 기록이 필요하다.
- `client_code`는 전역 중복 금지로 둔다.
- `client_name`은 운영상 중복 가능성이 있으나 혼동을 줄이기 위해 중복 경고를 둔다.
- 사용중지 고객사는 신규 업무, 로그인, 업로드를 제한한다.
- 사용중지 고객사의 과거 데이터 조회는 내부 운영자 기준으로 허용한다.
- 고객사는 물리 삭제하지 않는다.

## 6. 창고 `warehouses` 관리 정책

- 생성/수정/사용중지 권한은 내부 운영자 중 `WAREHOUSE_MANAGE` 권한을 가진 사용자에게 부여한다.
- 고객사 사용자는 창고 마스터를 변경할 수 없다.
- 재고 또는 업무 이력이 있는 창고는 삭제하지 않는다.
- 사용중지 창고는 신규 업무 선택 대상에서 제외한다.
- 과거 이력에는 사용중지 창고도 계속 표시한다.
- 현재고가 있는 창고의 사용중지는 별도 재고 정책과 함께 제한하거나 강한 경고가 필요하다.
- 창고 코드 변경은 업무 이력과 연동 시스템에 영향을 줄 수 있으므로 생성 후 변경 제한을 기본으로 한다.

## 7. 고객사 사용창고 `client_warehouse_settings` 관리 정책

- 고객사별 사용창고 연결, 해제, 기본창고 변경은 내부 운영자 중 `WAREHOUSE_MANAGE` 권한을 가진 사용자만 수행한다.
- 고객사 사용자는 사용창고 설정을 변경할 수 없다.
- 재고 또는 업무 이력이 있는 연결은 물리 삭제하지 않고 `active_yn=false`로 비활성화한다.
- 기본 창고는 같은 고객사 내 active 연결 중 하나만 허용한다.
- 사용중지된 창고는 신규 기본 창고로 지정할 수 없다.
- 연결을 비활성화하기 전에 해당 고객사의 진행 중 업무와 현재고 영향 여부를 확인해야 한다.

## 8. 상품 `products` 관리 정책

- 생성/수정/사용중지 권한은 내부 운영자 중 `PRODUCT_MANAGE` 권한을 가진 사용자에게 부여한다.
- `CLIENT_ADMIN`의 상품 등록/수정은 P0에서 금지하고, 후속 고객사 포털 후보로 둔다.
- 상품은 `client_id` scope가 필수다.
- `client_id + product_code`는 중복 금지로 둔다.
- 대표 `barcode`는 `client_id` 범위 중복 금지 후보로 둔다.
- 입고, 출고, 반품, 재고, import, scan 이력이 있는 상품은 삭제하지 않는다.
- 사용중지 상품은 신규 입고, 출고, 반품, 재고 조정 선택 대상에서 제외한다.
- 과거 이력에는 사용중지 상품도 계속 표시한다.
- 상품명, 규격, 비고 같은 표시 정보는 수정 가능하되, 업무 이력 식별에 쓰이는 코드는 제한한다.

## 9. 상품바코드 `product_barcodes` 관리 정책

- 생성/수정/사용중지 권한은 내부 운영자 중 `PRODUCT_MANAGE` 권한을 가진 사용자에게 부여한다.
- `products.barcode`는 대표 낱개 바코드다.
- `product_barcodes`는 추가, 박스, 카톤, 외부 바코드를 관리한다.
- `client_id + barcode`는 중복 금지로 둔다.
- `unit_qty`는 1 이상이어야 한다.
- 이미 스캔, 입출고, 재고, 반품에서 사용된 바코드는 `barcode` 값과 `unit_qty` 수정을 제한한다.
- 삭제 대신 `active_yn=false` 사용중지를 기본으로 한다.
- 과거 스캔 이력에서는 당시 바코드 정보를 보존해야 한다.
- 바코드가 잘못 등록된 경우 신규 매칭에서 제외하고, 필요한 경우 새 바코드를 추가 등록한다.

## 10. 공통코드 `common_code_groups` / `common_codes` 관리 정책

- 관리 권한은 `SUPER_ADMIN` 또는 `INTERNAL_ADMIN` 중 `COMMON_CODE_MANAGE` 권한을 가진 사용자에게 부여한다.
- 시스템 필수 공통코드와 운영 설정 공통코드를 구분한다.
- `group_code`, `code_value`는 업무 데이터 저장 키이므로 생성 후 변경 금지를 기본으로 한다.
- `group_name`, `code_name`, `sort_order` 또는 `display_order`는 수정 가능하다.
- 사용중지 코드는 신규 선택 대상에서 제외한다.
- 과거 데이터 표시는 유지한다.
- 공통코드는 물리 삭제하지 않는다.
- 시스템 필수 코드는 사용중지도 제한할 수 있다.

## 11. API endpoint 설계 방향

아래 endpoint는 후속 skeleton 구현 후보이며, 이번 문서 작업에서는 구현하지 않는다.

- `POST /api/master/clients`
- `PATCH /api/master/clients/{client_id}`
- `POST /api/master/clients/{client_id}/disable`
- `POST /api/master/clients/{client_id}/enable`
- `POST /api/master/warehouses`
- `PATCH /api/master/warehouses/{warehouse_id}`
- `POST /api/master/warehouses/{warehouse_id}/disable`
- `POST /api/master/warehouses/{warehouse_id}/enable`
- `POST /api/master/products`
- `PATCH /api/master/products/{product_id}`
- `POST /api/master/products/{product_id}/disable`
- `POST /api/master/products/{product_id}/enable`
- `POST /api/master/product-barcodes`
- `PATCH /api/master/product-barcodes/{barcode_id}`
- `POST /api/master/product-barcodes/{barcode_id}/disable`
- `POST /api/master/product-barcodes/{barcode_id}/enable`
- `POST /api/master/common-code-groups`
- `PATCH /api/master/common-code-groups/{group_id}`
- `POST /api/master/common-codes`
- `PATCH /api/master/common-codes/{code_id}`
- `POST /api/master/common-codes/{code_id}/disable`
- `POST /api/master/common-codes/{code_id}/enable`

DELETE API는 P0에서 미지원한다.

## 12. DB/model 보강 후보

현재 P0 모델의 기준정보 테이블은 대체로 아래 필드를 가진다.

- `active_yn`
- `created_at`
- `updated_at`

후속 보강 후보는 아래와 같다.

- `created_by`
- `updated_by`
- `disabled_at`
- `disabled_by`
- 기준정보 변경 감사 로그 테이블

이번 문서에서는 후보로만 정리한다. 이번 작업에서 migration은 만들지 않는다. `is_deleted`를 추가하기보다 `active_yn` 중심 정책을 유지하는 것을 우선한다.

## 13. 구현 전 체크리스트

create/update/disable API 구현 전 아래 항목을 확인한다.

- 호출자의 role과 permission을 확인했는가?
- `MASTER_MANAGE` 또는 대상별 관리 permission을 확인했는가?
- `client_id` scope를 서버 `AuthContext` 기준으로 검증했는가?
- 필요한 경우 `warehouse_id` scope를 검증했는가?
- 프론트가 보낸 `client_id`를 그대로 신뢰하지 않았는가?
- 코드, 바코드, 이름 등 중복 검증 기준을 적용했는가?
- `active_yn` 필터 기준을 조회와 신규 선택에서 분리했는가?
- 사용 이력이 있으면 물리 삭제를 금지했는가?
- 사용중지 후 신규 업무 선택에서 제외되는가?
- 과거 이력 조회에서는 사용중지 기준정보가 표시되는가?
- 성공/실패 응답에 secret, password, token, `password_hash`가 노출되지 않는가?
- `backend/local.secret.json`이 커밋 대상에 포함되지 않았는가?
- 테스트에서 내부 운영자, 고객사 사용자, READ_ONLY 권한 차이를 검증했는가?
- DELETE API를 만들지 않았는가?
