# Backend 창고 모델/API 정책 적합성 점검

## 1. 문서 목적

이 문서는 현재 backend 창고 모델/API 구조가 SmartReturn Pro 기준정보 화면 설계와 맞는지 점검하기 위한 문서다.

점검 목적은 아래와 같다.

- 고객사 관리 화면 구현 전에 창고 정책의 backend 적합성을 확인한다.
- 고객사용 플랫폼, 내부 운영자 플랫폼, 재고 조회, 입고, 출고, 반품 흐름을 고려해 필요한 보강 항목을 정리한다.
- 현재 구조를 무조건 버리거나 무조건 유지하지 않고, 유지 가능한 부분과 위험한 부분을 분리한다.

이번 작업은 점검/문서화만 포함한다. backend 모델, API, DB schema, migration, seed, 테스트 코드는 수정하지 않는다.

## 2. 기준 정책 요약

`docs/master-data-screen-design-plan-2026-05-29.md` 기준 정책은 아래와 같다.

- 기준정보 1차 화면은 고객사 관리, 상품 관리, 공통코드 관리로 시작한다.
- 창고 단독 화면을 1차에서 앞세우지 않는다.
- 고객사 관리 안에서 고객사가 사용할 창고를 선택, 추가, 기본값 설정하는 흐름을 우선한다.
- 이카운트 ERP처럼 여러 창고를 등록하고, 사용할 창고를 선택/제한하는 방식을 참고한다.
- SmartReturn Pro는 3PL 구조이므로 재고/권한/scope는 `client_id + warehouse_id` 기준으로 분리한다.
- 창고 미선택 조회는 해당 고객사의 전체 허용 창고 조회다.
- 창고 선택 조회는 선택한 창고만 조회한다.
- “전체 창고”는 실제 `warehouse` row가 아니라 조회 옵션이다.

이 정책의 핵심은 화면에서 “창고”를 고객사 업무 기준으로 다루되, backend에서는 어떤 모델 구조로 고객사-창고 scope를 보장할지 명확히 하는 것이다.

## 3. 현재 backend 모델 구조 확인

확인 파일:

- `backend/app/models/master.py`
- `backend/app/schemas/master.py`

### `clients`

`Client` 모델은 `clients` 테이블을 사용한다.

주요 필드:

- `id`
- `client_code`
- `client_name`
- `business_no`
- `contact_name`
- `contact_phone`
- `contact_email`
- `use_oms`
- `use_wms`
- `use_returns`
- `use_settlement`
- `active_yn`
- `remarks`
- `created_at`
- `updated_at`

index:

- `ix_clients_active_yn`
- `ix_clients_client_name`

`client_code`는 unique다.

### `warehouses`

`Warehouse` 모델은 `warehouses` 테이블을 사용한다.

주요 필드:

- `id`
- `warehouse_code`
- `warehouse_name`
- `warehouse_type`
- `address`
- `active_yn`
- `remarks`
- `created_at`
- `updated_at`

index:

- `ix_warehouses_active_yn`
- `ix_warehouses_warehouse_type`

`warehouse_code`는 unique다.

중요 확인:

- 현재 `warehouses`에는 `client_id`가 없다.
- 현재 구조만 보면 `warehouses`는 고객사 종속 창고라기보다 전역 창고 후보 또는 전역 창고 기준정보에 가깝다.
- soft delete는 물리 삭제가 아니라 `active_yn`으로 표현한다.

### `client_warehouse_settings`

`ClientWarehouseSetting` 모델은 `client_warehouse_settings` 테이블을 사용한다.

주요 필드:

- `id`
- `client_id`
- `warehouse_id`
- `usage_type`
- `is_default`
- `active_yn`
- `created_at`
- `updated_at`

제약/인덱스:

- `unique(client_id, warehouse_id, usage_type)`
- `ix_client_warehouse_settings_client_id`
- `ix_client_warehouse_settings_warehouse_id`
- `ix_client_warehouse_settings_client_usage`

관계:

- `client_id`는 `clients.id`를 참조한다.
- `warehouse_id`는 `warehouses.id`를 참조한다.

현재 허용 `usage_type` 후보는 service 기준 아래 값이다.

- `INBOUND`
- `OUTBOUND`
- `RETURN_GOOD`
- `RETURN_HOLD`
- `RETURN_DISPOSAL`
- `RETURN_REFURB`
- `RETURN_MANUFACTURER`
- `SAMPLE`
- `STORAGE`

### 모델 구조 판단

현재 구조는 “고객사 종속 `warehouses`”가 아니라 “전역 `warehouses` + 고객사별 `client_warehouse_settings` 사용 창고 설정” 구조다.

따라서 기준정보 화면 정책에서 말한 “창고는 고객사 종속 기준정보로 본다”는 화면/업무 정책을 현재 DB 구조로 직접 표현하려면 다음 둘 중 하나가 필요하다.

1. 현재 구조를 유지하되, 화면/API에서는 `client_warehouse_settings`를 고객사 소속 창고의 실질 기준으로 삼는다.
2. `warehouses` 자체를 고객사 종속 모델로 바꾸는 migration/리팩토링을 별도 설계한다.

이번 점검 기준에서는 1번이 단기적으로 현실적이다. 다만 scope 검증과 명칭 정리가 필요하다.

## 4. 현재 backend API 구조 확인

확인 파일:

- `backend/app/routers/master.py`
- `backend/app/services/master_service.py`
- `backend/app/repositories/master_repository.py`
- `backend/app/core/auth_context.py`
- `backend/app/core/permissions.py`

### 고객사 API

현재 고객사 API:

- `GET /api/master/clients`
- `POST /api/master/clients`
- `GET /api/master/clients/{client_id}`
- `PATCH /api/master/clients/{client_id}`
- `POST /api/master/clients/{client_id}/disable`
- `POST /api/master/clients/{client_id}/enable`

동작 요약:

- read-only 조회는 `MASTER_VIEW`가 필요하다.
- 내부 사용자는 전체 active 고객사 목록을 볼 수 있다.
- 고객사 사용자는 자기 `client_id` 고객사만 볼 수 있다.
- 고객사 상세는 `resolve_effective_client_id`로 client scope를 검증한다.
- 관리 API는 `SUPER_ADMIN` 또는 `INTERNAL_ADMIN` + `MASTER_MANAGE` + `CLIENT_MANAGE`가 필요하다.
- 삭제 대신 `active_yn=false` 사용중지 방식을 쓴다.

### 창고 API

현재 창고 API:

- `GET /api/master/warehouses`
- `POST /api/master/warehouses`
- `PATCH /api/master/warehouses/{warehouse_id}`
- `POST /api/master/warehouses/{warehouse_id}/disable`
- `POST /api/master/warehouses/{warehouse_id}/enable`

동작 요약:

- `GET /api/master/warehouses`는 `MASTER_VIEW`가 필요하고, router/service에서 내부 운영자만 허용한다.
- 고객사 사용자는 전체 창고 목록을 볼 수 없다.
- 관리 API는 `SUPER_ADMIN` 또는 `INTERNAL_ADMIN` + `MASTER_MANAGE` + `WAREHOUSE_MANAGE`가 필요하다.
- `warehouse_code` 중복은 차단한다.
- `warehouse_code`는 수정 API에서 변경 대상이 아니다.
- 삭제 대신 `active_yn=false` 사용중지 방식을 쓴다.

주의:

- 창고 생성 API에는 `client_id`가 없다.
- 창고 목록 API는 전체 active warehouse를 내부 사용자에게 반환한다.
- 고객사 관리 화면에서 “고객사 소속 창고 추가” UX를 만들려면 `warehouses` 생성과 `client_warehouse_settings` 생성이 이어져야 한다.

### 고객사별 사용 창고 API

현재 고객사별 사용 창고 API:

- `GET /api/master/client-warehouses`
- `POST /api/master/client-warehouses`
- `PATCH /api/master/client-warehouses/{setting_id}`
- `POST /api/master/client-warehouses/{setting_id}/disable`
- `POST /api/master/client-warehouses/{setting_id}/enable`
- `POST /api/master/client-warehouses/{setting_id}/set-default`

동작 요약:

- read-only 조회는 `MASTER_VIEW`가 필요하다.
- `GET /api/master/client-warehouses`는 `resolve_effective_client_id`를 사용한다.
- 내부 사용자는 query `client_id`로 고객사를 선택할 수 있다.
- 고객사 사용자는 자기 `client_id`로 강제된다.
- repository 조회는 active setting, active client, active warehouse만 반환한다.
- 관리 API는 `SUPER_ADMIN` 또는 `INTERNAL_ADMIN` + `MASTER_MANAGE` + `WAREHOUSE_MANAGE`가 필요하다.
- 생성 시 active client, active warehouse를 확인한다.
- `client_id + warehouse_id + usage_type` 중복을 차단한다.
- `is_default=true` 생성 시 같은 `client_id + usage_type`의 기존 active default를 해제한다.
- 기본 설정의 `usage_type` 변경은 차단한다.
- default setting disable은 차단한다.
- enable 시 active client, active warehouse를 다시 확인한다.
- enable 시 `is_default=false`로 유지된다.
- set-default는 active setting, active client, active warehouse를 확인하고 같은 `client_id + usage_type`의 기존 active default를 해제한다.

### warehouse_id scope 검증 여부

현재 기준정보 API 범위에서는 고객사별 사용 창고 조회/관리 API가 `client_warehouse_settings`를 기준으로 scope를 형성한다.

하지만 앞으로 재고/입고/출고/반품 API에서 `warehouse_id`만 입력받는 경우에는 아래 검증이 추가로 필요하다.

- 요청의 resolved `client_id`가 해당 `warehouse_id`를 사용할 수 있는지 확인
- `client_warehouse_settings.active_yn=true`인지 확인
- 연결된 `Warehouse.active_yn=true`인지 확인
- 업무별 `usage_type`이 맞는지 확인

현재 `Warehouse` 모델에는 `client_id`가 없으므로 `warehouse.client_id` 직접 비교는 불가능하다. 현 구조를 유지한다면 `client_warehouse_settings`를 scope 검증 기준으로 삼아야 한다.

## 5. 현재 테스트 구조 확인

확인 파일:

- `backend/tests/test_master_api_readonly.py`
- `backend/tests/test_master_api_manage_clients.py`
- `backend/tests/test_master_api_manage_warehouses.py`
- `backend/tests/test_master_api_manage_client_warehouses.py`

### read-only 테스트

확인된 테스트:

- 인증 없음 차단
- must_change_password 사용자 차단
- `MASTER_VIEW` 권한 필요
- `SUPER_ADMIN` 전체 고객사 조회
- `CLIENT_ADMIN` 자기 고객사만 조회
- 고객사 사용자의 다른 고객사 상세 조회 차단
- `GET /api/master/client-warehouses`가 고객사 scope를 적용
- 내부 사용자는 query `client_id`로 고객사 창고 조회 가능
- `GET /api/master/warehouses`는 내부 사용자 전용
- 상품 조회/상세의 client scope 검증
- 공통코드 조회

### 고객사 관리 테스트

확인된 테스트:

- 인증 없음 401
- `READ_ONLY`, `CLIENT_ADMIN`, `INTERNAL_WORKER` 관리 API 차단
- `INTERNAL_ADMIN` 생성 성공
- `client_code` 중복 차단
- `client_code` 변경 시도 시 기존 값 유지
- disable/enable

### 창고 관리 테스트

확인된 테스트:

- 인증 없음 401
- `READ_ONLY`, `CLIENT_ADMIN`, `INTERNAL_WORKER` 관리 API 차단
- `INTERNAL_ADMIN` 생성 성공
- `warehouse_code` 중복 차단
- `warehouse_code` 변경 시도 시 기존 값 유지
- disable/enable

### 고객사별 사용 창고 테스트

확인된 테스트:

- 인증 없음 401
- `READ_ONLY`, `CLIENT_ADMIN`, `INTERNAL_WORKER` 관리 API 차단
- `INTERNAL_ADMIN` 생성 성공
- inactive client 연결 생성 차단
- inactive warehouse 연결 생성 차단
- `client_id + warehouse_id + usage_type` 중복 차단
- setting 수정 성공
- default setting의 `usage_type` 변경 차단
- create `is_default=true` 시 기존 default 해제
- set-default 시 기존 default 해제
- default setting disable 차단
- non-default disable/enable
- read-only `GET /api/master/client-warehouses`가 active setting만 반환

### 테스트에서 아직 약한 부분

현재 범위에서는 아래 테스트가 후속 보강 후보로 보인다.

- 재고/입고/출고/반품 API에서 `warehouse_id` 직접 입력 공격을 차단하는 테스트
- 특정 client에 연결되지 않은 warehouse를 업무 API에서 사용할 수 없는지 검증하는 테스트
- 고객사 사용자가 query/body에 다른 고객사의 `warehouse_id`를 넣었을 때 차단되는 테스트
- usage_type별 업무 선택 검증 테스트
- 전체 창고 조회 옵션이 실제 warehouse row 없이 동작하는 테스트
- 고객사 관리 화면에서 창고 생성 + 사용 설정을 한 흐름으로 검증하는 API/서비스 테스트

이 항목들은 해당 업무 API 또는 고객사 상세 API가 설계될 때 추가하는 것이 맞다.

## 6. 현재 구조의 장점

현재 `warehouses + client_warehouse_settings` 구조의 장점은 아래와 같다.

- 이카운트 ERP처럼 여러 창고 후보를 먼저 만들고 고객사별 사용 창고를 제한할 수 있다.
- 같은 물리/논리 창고를 여러 고객사가 공유할 수 있는 3PL 운영 모델에 대응할 수 있다.
- 고객사별 기본 창고를 `usage_type + is_default`로 관리할 수 있다.
- 창고 미선택/선택 조회 구조를 만들 때 `client_warehouse_settings` 기준으로 허용 창고 목록을 만들 수 있다.
- 내부 운영자와 고객사 사용자 권한 분리에 활용할 수 있다.
- warehouse 자체 사용중지와 고객사별 사용 설정 사용중지를 분리할 수 있다.
- `usage_type`을 통해 입고, 출고, 반품양품, 보류, 리퍼, 제조사반품 등의 기본 창고를 한 구조로 표현할 수 있다.

특히 3PL에서는 하나의 물리 창고를 여러 고객사가 쓰는 경우가 있을 수 있으므로, 전역 warehouse 후보와 고객사별 사용 설정을 분리하는 구조가 완전히 부적합하다고 단정할 수는 없다.

## 7. 현재 구조의 위험

현재 구조의 위험은 아래와 같다.

### 전역 창고 노출 위험

`warehouses`에 `client_id`가 없고 `GET /api/master/warehouses`가 내부 운영자에게 전체 창고를 반환한다. 고객사 사용자에게는 차단되어 있지만, 화면 구현에서 이 API를 고객사 창고 선택에 그대로 사용하면 전역 창고마스터처럼 보일 위험이 있다.

### warehouse_id 단독 사용 위험

업무 API가 `warehouse_id`만 받고 `client_warehouse_settings`를 검증하지 않으면 다른 고객사와 연결된 창고 또는 연결되지 않은 창고를 사용할 수 있다. 현재 기준정보 API는 이 위험을 직접 일으키지 않지만, 향후 재고/입고/출고/반품 API에서는 반드시 검증해야 한다.

### 사용 설정과 실제 소속 개념 혼동

현재 구조는 “고객사 소속 창고”라기보다 “고객사가 사용할 수 있는 창고 설정”에 가깝다. 화면에서 고객사 소속 창고처럼 표현하려면 naming과 UX를 조심해야 한다.

### 기본창고 중복/상태 위험

현재 service에서 `client_id + usage_type` active default 1개를 보장하고, default disable을 차단한다. DB partial unique index는 없고 service 레벨 보장이다. 동시성까지 고려하면 후속 보강 후보가 될 수 있다.

### 사용중지 창고가 기본창고로 남는 위험

default setting disable은 차단하지만, 전역 warehouse 자체를 disable할 때 해당 warehouse가 어떤 고객사의 default setting인지 사전 차단하지 않는다. 현재 `client-warehouses` read-only 조회는 inactive warehouse를 제외하지만, default 설정 데이터 자체는 남을 수 있다. 이 부분은 화면/업무 API에서 혼란이 생길 수 있어 후속 점검이 필요하다.

### 고객사 관리 화면 UX/API 결합 위험

고객사 상세 안에서 창고를 추가하려면 현재 구조상 다음 두 작업이 필요하다.

1. `POST /api/master/warehouses`
2. `POST /api/master/client-warehouses`

이 흐름을 화면에서 자연스럽게 묶으려면 “기존 창고 선택”과 “새 창고 생성 후 고객사 연결”을 구분하는 API/UX 계약이 필요하다.

### 전체 창고 row 생성 위험

“전체 창고”를 실제 `warehouses` row로 만들면 scope와 수불 기준이 흐려진다. 현재 모델/API에는 전체 창고 row를 강제하는 구조는 없지만, 화면 설계에서 select option으로만 처리해야 한다.

## 8. 정책 적합성 판단

추천 판단은 C안이다.

### C안: 현재 구조 유지하되 명칭/역할 재정의 필요

현재 구조를 당장 버릴 필요는 없다. `warehouses`를 창고 후보 또는 물리/논리 창고 기준정보로 두고, `client_warehouse_settings`를 고객사별 사용 창고와 기본 창고의 실질 기준으로 삼으면 기준정보 1차 화면 요구사항을 일부 충족할 수 있다.

다만 다음 조건이 붙어야 한다.

- 화면/문서/API naming에서 “전역 창고마스터”가 앞에 드러나지 않게 한다.
- 고객사 관리 화면 중심으로 창고를 노출한다.
- 고객사별 창고 조회는 `GET /api/master/client-warehouses`를 기본으로 사용한다.
- 고객사 상세에서 창고를 추가할 때 전역 warehouse 생성과 고객사 연결을 같은 UX 흐름으로 묶는 설계가 필요하다.
- 모든 업무 API는 `client_warehouse_settings` 기준으로 `client_id + warehouse_id + usage_type + active_yn`을 검증해야 한다.

### A안 유지 가능성

A안, 즉 “전역 창고마스터 + 고객사별 사용 창고 설정” 구조 자체는 유지 가능하다. 3PL에서 여러 고객사가 같은 물리 창고를 공유하거나, 내부 운영자가 공통 창고 후보를 관리하는 경우 장점이 있다.

하지만 기준정보 화면 정책은 “고객사 관리 안에서 고객사 소속 창고처럼 다룬다”는 UX를 요구하므로, 전역 창고마스터가 화면 전면에 드러나면 정책과 어긋난다. 따라서 A안은 API scope와 UX를 강화한다는 조건부 유지안이다.

### B안 필요 가능성

B안, 즉 `warehouses.client_id` 추가 또는 client-owned warehouse 구조로 재설계하는 방향은 가장 명확한 고객사 종속 모델이다. 하지만 migration, 기존 API 리팩토링, 테스트 재작성, 공유 창고 운영 정책 재검토가 필요하다.

현재 P0 단계에서는 바로 B안으로 확정하기보다, C안으로 화면/API 계약을 정리한 뒤 재고/입출고/반품 업무 API 설계에서 위험이 커지는지 다시 판단하는 것이 안전하다.

## 9. 고객사 관리 화면 구현 전 필수 확인 항목

고객사 관리 화면을 만들기 전에 아래 조건을 확인해야 한다.

- 고객사 상세에서 사용 창고 목록 조회가 가능한가?
  - 현재 `GET /api/master/client-warehouses?client_id={client_id}`로 가능하다.
- 고객사 상세에서 사용 창고 추가가 가능한가?
  - 현재 `POST /api/master/client-warehouses`로 가능하다.
  - 단, 새 warehouse를 동시에 만드는 UX/API 계약은 별도 설계가 필요하다.
- 고객사별 사용 창고 해제가 가능한가?
  - 현재 `POST /api/master/client-warehouses/{setting_id}/disable`로 가능하다.
- 고객사별 `usage_type`별 기본 창고 설정이 가능한가?
  - 현재 `POST /api/master/client-warehouses/{setting_id}/set-default`로 가능하다.
- `usage_type`별 `is_default` 중복 방지가 가능한가?
  - 현재 service에서 기존 default를 자동 해제한다.
  - DB 제약은 아니므로 동시성은 후속 검토 대상이다.
- 고객사 사용자에게 자기 고객사 창고만 반환 가능한가?
  - 현재 `GET /api/master/client-warehouses`는 `resolve_effective_client_id`로 자기 고객사 scope를 적용한다.
- 내부 사용자에게 선택 client 기준 창고만 반환 가능한가?
  - 현재 query `client_id`로 가능하다.
- 사용중지 창고가 신규 작업에 선택되지 않도록 할 수 있는가?
  - read-only client warehouse 조회는 active setting, active client, active warehouse만 반환한다.
- 기존 창고/설정 API가 고객사 화면 요구사항을 만족하는가?
  - 조회/연결/기본값/사용중지는 가능하다.
  - “고객사 상세에서 새 창고 생성 후 즉시 연결”과 “usage_type별 기본창고 UI 계약”은 추가 설계가 필요하다.

고객사 관리 화면 구현 자체는 완전히 차단할 정도는 아니다. 다만 화면 구현 전에 backend 정책 문서 또는 API 보강 설계에서 “전역 warehouse 후보 + 고객사별 사용 설정”이라는 역할을 명확히 해야 한다.

## 10. 재고/입고/출고/반품 API 후속 검증 기준

아직 해당 업무 API가 없더라도 앞으로 아래 기준을 지켜야 한다.

- 모든 재고 조회는 resolved `client_id` 기준으로 수행한다.
- `warehouse_id`가 없으면 해당 고객사의 허용 창고 전체 조회로 처리한다.
- `warehouse_id`가 있으면 해당 client가 사용할 수 있는 창고인지 검증한다.
- 입고/출고/반품 수불은 `client_id + warehouse_id + product_id` 기준으로 기록한다.
- 고객사 사용자는 자기 `client_id`만 가능하다.
- 내부 사용자는 권한 범위 client만 가능하다.
- `warehouse_id` 직접 입력 공격을 방지한다.
- “전체 창고”는 DB row가 아니라 조회 옵션이다.
- 업무별 창고 선택은 `usage_type`을 기준으로 가능한 창고만 반환해야 한다.
- inactive client, inactive warehouse, inactive client warehouse setting은 신규 업무 선택에서 제외해야 한다.

현 구조 유지 시 업무 API에서 필요한 검증 helper 후보:

- `ensure_client_can_use_warehouse(client_id, warehouse_id)`
- `ensure_client_can_use_warehouse_for_usage(client_id, warehouse_id, usage_type)`
- `list_client_allowed_warehouses(client_id, usage_type | None)`
- `get_default_client_warehouse(client_id, usage_type)`

이 helper들은 `client_warehouse_settings`와 `warehouses.active_yn`을 함께 확인해야 한다.

## 11. 후속 작업 후보

점검 결과에 따른 후속 후보는 아래와 같다.

### 후보 1: 고객사 관리 화면 상세 디자인 문서 작성

현재 구조를 C안으로 유지한다면 다음 단계로 고객사 관리 화면 상세 디자인 문서를 작성할 수 있다.

전제:

- 화면에서 `client_warehouse_settings`를 고객사 소속 창고의 실질 기준으로 사용한다.
- 전역 `warehouses` 단독 화면은 만들지 않는다.
- 새 창고 생성 + 고객사 연결 UX를 명확히 설계한다.

### 후보 2: backend client_warehouse_settings API 보강 설계

아래가 부족하다고 판단되면 먼저 API 보강 설계를 진행한다.

- 고객사 상세용 창고 목록 response 보강
- usage_type별 기본창고 summary response
- 새 warehouse 생성과 client_warehouse_settings 생성을 묶는 endpoint 필요 여부
- inactive warehouse가 default로 남는 경우 처리
- 고객사별 창고 선택용 lookup API

### 후보 3: migration/모델 리팩토링 설계

정책을 “창고는 반드시 고객사 소유 row”로 확정한다면 migration/모델 리팩토링 설계가 필요하다.

검토 후보:

- `warehouses.client_id` 추가
- `warehouse_code` unique 범위를 전역에서 `client_id + warehouse_code`로 변경
- `client_warehouse_settings` 역할 축소 또는 기본창고 설정 테이블로 재정의
- 기존 데이터 마이그레이션 전략

### 후보 4: client warehouse scope 테스트 보강

향후 업무 API 전, 또는 helper 도입 시 아래 테스트 보강이 필요하다.

- 고객사 사용자 다른 고객사 warehouse 접근 차단
- 내부 사용자 selected client 외 warehouse 사용 차단
- inactive setting 선택 차단
- inactive warehouse 선택 차단
- usage_type 불일치 창고 선택 차단
- 전체 창고 조회가 실제 warehouse row 없이 동작하는지 확인

## 12. closeout 결론

현재 backend 창고 모델/API는 기준정보 화면 설계의 “고객사 안에서 창고를 관리한다”는 UX 정책과 완전히 같은 형태는 아니다. `warehouses`에는 `client_id`가 없고, 구조적으로는 전역 창고 후보 + 고객사별 사용 창고 설정에 가깝다.

다만 현재 `client_warehouse_settings`가 `client_id`, `warehouse_id`, `usage_type`, `is_default`, `active_yn`을 갖고 있고, read-only 조회와 관리 API가 이미 고객사별 사용 창고/기본 창고 흐름을 제공한다. 따라서 단기 P0에서는 C안, 즉 “현재 구조 유지 + 명칭/역할 재정의 + scope 검증 강화”가 가장 안전하다.

화면 구현 전 반드시 보강해야 할 정도의 즉시 차단 항목은 “고객사 관리 화면 상세 디자인 문서 작성” 자체에는 없다. 하지만 고객사 관리 화면 구현에 들어가기 전에는 다음을 먼저 결정해야 한다.

- 고객사 상세에서 새 창고를 만들 때 `warehouses` 생성과 `client_warehouse_settings` 생성을 어떻게 연결할지
- 화면에서 전역 `GET /api/master/warehouses`를 직접 노출하지 않을지
- 고객사별 창고 선택 UI가 `GET /api/master/client-warehouses`를 기본으로 사용할지
- 재고/입고/출고/반품 API에서 `warehouse_id` scope 검증 helper를 어떤 기준으로 둘지

다음 작업으로는 “고객사 관리 화면 상세 디자인 문서 작성”보다 “backend client_warehouse_settings API 보강 설계”를 먼저 추천한다. 이유는 고객사 상세 화면의 창고 추가/기본창고 설정 UX가 현재 API만으로 가능한 범위와 보강이 필요한 범위를 더 명확히 나눠야 하기 때문이다.

그 다음 고객사 관리 화면 상세 디자인 문서로 넘어가면, 화면 구현 중 정책 충돌이 줄어든다.
