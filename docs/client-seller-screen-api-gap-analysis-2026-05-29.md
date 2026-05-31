# 고객사/셀러 화면 API 부족분 분석

## 1. 문서 목적

이 문서는 SmartReturn Pro의 고객사/셀러 화면을 구현하기 전에 기존 backend API가 화면 요구사항을 어디까지 충족하는지 확인한 결과를 정리한다.

목표는 다음과 같다.

- 고객사/셀러 목록, 상세, 창고·처리장소 설정 화면에 필요한 API 응답 필드를 기존 API와 비교한다.
- 부족분을 1차 필수 보강, 후속 보강, 장기 구조 후보로 나눈다.
- 프론트 화면에서 없는 필드를 추정하거나 `client_id`, 창고, 계약 유형 등을 하드코딩하는 흐름을 막는다.
- 현재 가능한 화면 skeleton 범위와 backend 보강이 필요한 범위를 분리한다.

이번 작업은 점검과 문서화만 수행하며 backend API, frontend 화면, DB schema, migration, seed는 수정하지 않는다.

## 2. 현재 backend client API 현황

확인한 주요 파일은 다음과 같다.

- `backend/app/models/master.py`
- `backend/app/schemas/master.py`
- `backend/app/routers/master.py`
- `backend/app/services/master_service.py`
- `backend/app/repositories/master_repository.py`
- `backend/tests/test_master_api_readonly.py`
- `backend/tests/test_master_api_manage_clients.py`
- `backend/tests/test_master_api_manage_warehouses.py`
- `backend/tests/test_master_api_manage_client_warehouses.py`

현재 고객사 모델 `Client`는 다음 필드를 가진다.

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

현재 고객사 API 현황은 다음과 같다.

| 기능 | 현재 endpoint | 현재 상태 | 비고 |
| --- | --- | --- | --- |
| 고객사 목록 | `GET /api/master/clients` | 지원 | `ClientSummary` 기준. `client_id`, `client_code`, `client_name`, `active_yn` 제공 |
| 고객사 상세 | `GET /api/master/clients/{client_id}` | 지원 | `ClientDetail` 기준. 연락처, 업무 사용 여부, 비고 제공 |
| 고객사 생성 | `POST /api/master/clients` | 지원 | `ClientCreateRequest` 기준 |
| 고객사 수정 | `PATCH /api/master/clients/{client_id}` | 지원 | `client_code` 변경은 request schema에 없음 |
| 고객사 사용중지 | `POST /api/master/clients/{client_id}/disable` | 지원 | 삭제 대신 `active_yn=false` |
| 고객사 재활성화 | `POST /api/master/clients/{client_id}/enable` | 지원 | `active_yn=true` |

목록 API는 pagination, keyword search, active/inactive 포함 옵션을 제공하지 않는다. repository의 `list_clients(active_only=True)` 기본값 때문에 목록에서는 active 고객사만 반환된다.

고객사 목록 response에는 다음 화면 후보 필드가 없다.

- `contract_type`
- `owner_type`
- `default_warehouse`
- `default_processing_site`
- `created_at`
- `updated_at`
- management action 가능 여부

고객사 상세 response에는 `created_at`, `updated_at`, 계약/운영 주체, 처리장소 개념이 없다. 다만 1차 상세 기본정보 skeleton에 필요한 고객사 코드, 이름, 사업자번호 후보, 연락처, 비고, 사용 여부는 이미 제공된다.

권한/scope는 다음처럼 동작한다.

- `GET /api/master/clients`는 `MASTER_VIEW`가 필요하다.
- 내부 사용자는 active 고객사 전체를 조회한다.
- 고객사 사용자는 자기 `client_id`만 조회한다.
- 다른 고객사 상세 조회는 `CLIENT_SCOPE_DENIED`로 차단된다.
- 생성/수정/사용중지/재활성화는 `SUPER_ADMIN`, `INTERNAL_ADMIN` + `MASTER_MANAGE`, `CLIENT_MANAGE` 중심으로 제한된다.

## 3. 현재 client_warehouse_settings API 현황

현재 모델 구조는 `warehouses + client_warehouse_settings` 방식이다.

`Warehouse`는 전역 창고 후보/창고마스터 성격이며 `client_id`가 없다. 주요 필드는 다음과 같다.

- `id`
- `warehouse_code`
- `warehouse_name`
- `warehouse_type`
- `address`
- `active_yn`
- `remarks`
- `created_at`
- `updated_at`

`ClientWarehouseSetting`은 고객사별 사용 창고와 기본 창고 설정을 담당한다.

- `id`
- `client_id`
- `warehouse_id`
- `usage_type`
- `is_default`
- `active_yn`
- `created_at`
- `updated_at`

현재 API 현황은 다음과 같다.

| 기능 | 현재 endpoint | 현재 상태 | 비고 |
| --- | --- | --- | --- |
| 고객사 사용 창고 목록 | `GET /api/master/client-warehouses?client_id=` | 지원 | 고객사 사용자는 자기 고객사 기준으로 조회 가능 |
| 고객사 창고 연결 | `POST /api/master/client-warehouses` | 지원 | `client_id`, `warehouse_id`, `usage_type`, `is_default` |
| 창고 설정 수정 | `PATCH /api/master/client-warehouses/{setting_id}` | 일부 지원 | 현재는 `usage_type` 수정 중심 |
| 사용중지 | `POST /api/master/client-warehouses/{setting_id}/disable` | 지원 | 기본 창고는 disable 차단 |
| 재활성화 | `POST /api/master/client-warehouses/{setting_id}/enable` | 지원 | enable 시 `is_default=false`로 정리 |
| 기본 창고 지정 | `POST /api/master/client-warehouses/{setting_id}/set-default` | 지원 | 같은 `client_id + usage_type`의 기존 default 해제 |
| 창고 후보 조회 | 없음 | 보강 필요 | 전역 `GET /api/master/warehouses`는 내부 관리자 전용 전체 창고 목록 |
| 비활성 포함 조회 | 없음 | 보강 필요 | 현재 active setting만 반환 |
| 고객사 상세 nested path | 없음 | 보강 후보 | 현재 flat path라 상세 화면에서 사용은 가능하지만 화면 의미가 약함 |

현재 `ClientWarehouseSummary` response는 다음 필드를 제공한다.

- `client_id`
- `client_name`
- `warehouse_id`
- `warehouse_code`
- `warehouse_name`
- `usage_type`
- `is_default`
- `active_yn`

현재 `ClientWarehouseSettingResponse`에는 `setting_id`가 추가된다.

부족한 response 후보는 다음과 같다.

- `warehouse_type`
- `usage_type_label`
- `created_at`
- `updated_at`
- `allowed_actions`
- 비활성 포함 여부
- 연결 가능한 창고 후보의 `already_linked`, `linked_usage_types`

고객사 상세 화면 안에서 사용하기에는 현재 API로 active 사용 창고 목록 조회와 기본 창고 변경은 가능하다. 그러나 창고 추가 모달을 만들려면 별도의 후보 조회 API가 필요하다. 또한 고객사 상세 안에서 자연스러운 path를 쓰려면 `GET /api/master/clients/{client_id}/warehouse-settings` 같은 nested API를 추가하는 편이 낫다.

## 4. 현재 frontend API service 현황

확인한 파일은 다음과 같다.

- `frontend/src/api/client.ts`
- `frontend/src/api/master.ts`
- `frontend/src/types/master.ts`

현재 `frontend/src/api/master.ts`에는 `listClients()`만 있다.

```ts
listClients(): Promise<ClientSummary[]>
```

현재 `ClientSummary` type은 다음 정도만 정의되어 있다.

- `client_id?`
- `id?`
- `client_code`
- `client_name`
- `active_yn`

프론트 API client는 `ApiResult` unwrap, 인증 헤더 첨부, 401/403/422/5xx 기본 오류 처리 구조를 갖고 있으므로 고객사 목록 skeleton과 연결하는 기반은 있다.

부족한 frontend API service는 다음과 같다.

- `getClient(clientId)`
- `createClient`
- `updateClient`
- `disableClient`
- `enableClient`
- `listClientWarehouseSettings`
- `listWarehouseOptions`
- `createClientWarehouseSetting`
- `updateClientWarehouseSetting`
- `setDefaultClientWarehouseSetting`
- `disableClientWarehouseSetting`
- `enableClientWarehouseSetting`

## 5. 고객사/셀러 목록 화면 요구사항과 API 비교

| 화면 필요 필드 | 현재 API 제공 여부 | 1차 필수 여부 | 비고 |
| --- | --- | --- | --- |
| `client_id` | 제공 | 필수 | `GET /api/master/clients` 제공 |
| `client_code` | 제공 | 필수 | copyable 후보 |
| `client_name` | 제공 | 필수 | 목록 기본 표시 가능 |
| `contract_type` | 미제공 | 후속 | 장기 계약/운영 구조 후보 |
| `owner_type` | 미제공 | 후속 | 동현 직접/CJ 대리점/타택배사 확장 후보 |
| `default_warehouse` | 미제공 | 후속 | 현재 설정 API 조합으로 계산 가능하지만 목록 API에는 없음 |
| `default_processing_site` | 미제공 | 장기 | `processing_site` 개념 미도입 |
| `active_yn` 또는 `status` | 제공 | 필수 | 목록 상태 표시 가능 |
| `created_at` | 미제공 | 후속 | 목록 정렬/운영 이력에는 필요 |
| `updated_at` | 미제공 | 후속 | 목록 정렬/운영 이력에는 필요 |
| management action 가능 여부 | 미제공 | 후속 | 1차는 권한 context로 버튼 제어 가능 |

판단:

- 고객사/셀러 목록 skeleton은 현재 API로 구현 가능하다.
- 다만 목록을 장기 운영 화면 수준으로 만들려면 pagination/search/filter, 생성/수정 버튼 권한, 계약 유형, 운영 주체, 기본 창고 요약, 생성/수정일이 필요하다.
- 1차 목록 skeleton에서는 `client_code`, `client_name`, `active_yn` 중심으로 시작하고, 부족 필드는 “준비중”으로 두는 것이 안전하다.

## 6. 고객사 상세/창고·처리장소 설정 요구사항과 API 비교

| 화면 필요 필드/기능 | 현재 API 제공 여부 | 1차 필수 여부 | 비고 |
| --- | --- | --- | --- |
| 고객사 상세 기본정보 | 제공 | 필수 | `GET /api/master/clients/{client_id}` |
| 사업자번호 후보 | 제공 | 1차 가능 | `business_no` |
| 연락처 후보 | 제공 | 1차 가능 | `contact_name`, `contact_phone`, `contact_email` |
| 계약 유형 | 미제공 | 후속 | `contract_type` 후보 |
| 운영 주체 | 미제공 | 후속 | `owner_type` 후보 |
| 메모 | 제공 | 1차 가능 | `remarks` |
| 사용 여부 | 제공 | 필수 | `active_yn` |
| 생성/수정일 | 모델에는 있음, schema 미제공 | 후속 | 상세 운영 패널에는 필요 |
| 고객사 사용 창고 목록 | 제공 | 필수 | `GET /api/master/client-warehouses?client_id=` |
| `setting_id` | 목록 API에는 미제공 | 필수 보강 | update/default/disable action에 필요. create/update response에는 있음 |
| `warehouse_id` | 제공 | 필수 | 현재 제공 |
| `warehouse_code` | 제공 | 필수 | 현재 제공 |
| `warehouse_name` | 제공 | 필수 | 현재 제공 |
| `warehouse_type` | 미제공 | 후속 | 목록 표시에는 유용 |
| `usage_type` | 제공 | 필수 | 현재 제공 |
| `usage_type_label` | 미제공 | 후속 | 공통코드/라벨 매핑 필요 |
| `is_default` | 제공 | 필수 | 현재 제공 |
| `active_yn` | 제공 | 필수 | active 목록만 반환 |
| 비활성 포함 조회 | 미제공 | 후속 | 관리 화면에는 필요 |
| 창고 후보 조회 | 미제공 | 필수 보강 | 창고 연결 모달에 필요 |
| 처리장소 설정 | 미제공 | 장기 | `processing_site` 개념 후보 |
| allowed actions | 미제공 | 후속 | 권한별 UI 제어 보강 후보 |

판단:

- 고객사 상세 기본정보 skeleton은 현재 API로 가능하다.
- 고객사 상세 안의 창고 설정을 실사용 수준으로 만들려면 `setting_id`가 포함된 목록 response, 창고 후보 조회, 비활성 포함 옵션이 우선 필요하다.
- 처리장소는 현재 창고와 구분된 backend 개념이 없으므로 장기 후보로 분리해야 한다.

## 7. 1차 필수 API 보강 후보

고객사/셀러 목록 skeleton 전에는 큰 API 보강 없이 시작할 수 있다.

다만 고객사 상세과 창고 설정 화면을 바로 이어서 만들려면 다음은 1차 필수 보강 후보로 본다.

1. 고객사 사용 창고 목록 response에 `setting_id` 포함
   - 현재 `ClientWarehouseSettingResponse`에는 있지만 `ClientWarehouseSummary`에는 없다.
   - 상세 화면에서 기본 지정, disable, 수정 action을 연결하려면 목록 row에 `setting_id`가 필요하다.

2. 고객사별 창고 후보 조회 API
   - 예: `GET /api/master/clients/{client_id}/warehouse-options`
   - 전역 창고 전체 목록을 화면에서 필터링하면 권한/scope와 UI 의미가 흐려질 수 있다.

3. nested 고객사 창고 설정 조회 API
   - 예: `GET /api/master/clients/{client_id}/warehouse-settings`
   - 기존 flat API는 유지 가능하지만 고객사 상세 화면에는 nested path가 자연스럽다.

4. 고객사 창고 설정 service/frontend 함수 보강
   - frontend `master.ts`에는 현재 `listClients()`만 있으므로 상세/창고 설정 화면 전에 service 함수와 type 정의가 필요하다.

5. 목록 화면용 검색/filter는 skeleton 이후 빠른 보강 후보
   - 고객사 수가 늘면 `GET /api/master/clients`의 전체 active list 방식은 부족하다.

## 8. 후속 API 보강 후보

1차 skeleton 이후 보강해도 되는 항목은 다음과 같다.

- 고객사 목록 pagination
- 고객사 목록 keyword search
- active/inactive 포함 조회 옵션
- `created_at`, `updated_at` response 노출
- `contract_type`, `owner_type` 후보 필드
- 기본 창고 요약 field
- `usage_type_label` 또는 공통코드 연동
- 고객사 상세 response에 창고 설정 nested 포함 옵션
- 비활성 창고 설정 포함 조회 옵션
- allowed actions response
- 고객사 상세 변경 이력
- 처리장소 전용 API

## 9. 장기 구조 후보

장기 사업 방향을 고려하면 다음 구조 후보가 있다. 이번 단계에서 DB/schema에 바로 반영하지 않는다.

- `carrier_id`
  - CJ, 타택배사 등 운송사/택배사 단위 확장 후보.
- `agency_id`
  - CJ택배 대리점 또는 타택배사 대리점 소속 고객사 관리 후보.
- `processing_site_id`
  - 창고와 별개로 반품 검수, 사진촬영, 판정이 일어나는 처리장소 개념.
- `owner_type`
  - 동현 직접 운영, 대리점 운영, 고객사 자체 운영 등 운영 주체 구분 후보.
- `contract_type`
  - 직접 계약, 대리점 SaaS, 마이크로센터 처리, 기타 계약 유형 후보.
- `billing_target`
  - 정산 대상이 동현 직접 고객사인지, 대리점인지, 셀러인지 구분하는 후보.

이 항목들은 고객사/셀러 화면의 장기 확장을 막지 않도록 문서와 화면 배치에서 여지를 남기되, 현재 고객사 목록 skeleton을 막는 요소로 보지는 않는다.

## 10. 구현 순서 제안

결론은 C안이다.

### C안: 고객사 목록은 가능하지만 고객사 상세/창고 설정은 API 보강 필요

이유:

- 현재 `GET /api/master/clients`는 고객사/셀러 목록 skeleton에 필요한 최소 필드인 `client_id`, `client_code`, `client_name`, `active_yn`을 제공한다.
- AuthContext/ApiResult 기반의 frontend API client도 있으므로 보호 route 안의 목록 화면 skeleton은 바로 연결 가능하다.
- 하지만 고객사 상세 안의 창고·처리장소 설정은 현재 API만으로는 부족하다.
- 특히 `setting_id` 없는 목록 response, 창고 후보 조회 부재, 비활성 포함 옵션 부재, nested 고객사 path 부재는 상세 화면 실사용 흐름을 막는다.

추천 순서:

1. 고객사/셀러 목록 화면 skeleton 구현
2. 고객사 상세 진입 구조와 기본정보 skeleton 설계
3. 창고·처리장소 설정 화면 전에 `client_warehouse_settings` API 보강 구현
4. 창고 후보 조회, `setting_id` 포함 목록, 비활성 포함 옵션, nested path를 보강
5. 고객사 상세 안의 창고·처리장소 설정 skeleton 구현

## 11. closeout 결론

현재 API로 고객사/셀러 목록 skeleton은 구현 가능하다. 목록 화면에서는 `client_code`, `client_name`, `active_yn` 중심으로 시작하고, 계약 유형·운영 주체·기본 창고·생성/수정일은 후속 필드로 남기는 것이 안전하다.

다음 작업은 `고객사/셀러 목록 화면 skeleton 구현`을 추천한다. 이유는 현재 API로 목록의 핵심 흐름은 검증할 수 있고, 이후 상세/창고 설정 단계에서 실제 부족 API를 더 구체적으로 보강할 수 있기 때문이다.

다만 고객사 상세의 창고·처리장소 설정까지 바로 진행하려면 먼저 `client_warehouse_settings` API 보강이 필요하다.
