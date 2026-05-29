# client_warehouse_settings API 보강 설계

## 1. 문서 목적

이 문서는 고객사 관리 화면에서 사용할 창고 설정 API 계약을 설계하기 위한 문서다.

현재 SmartReturn Pro backend는 `warehouses`와 `client_warehouse_settings`를 분리해 둔다. `warehouses`는 `client_id`가 없는 전역 창고 후보 또는 창고마스터이고, `client_warehouse_settings`가 고객사별 사용 창고, `usage_type`, 기본 창고, 사용 여부를 담당한다.

이번 문서는 이 구조를 유지하면서 고객사 중심 화면을 만들 수 있도록 다음 기준을 정리한다.

- 고객사별 사용 창고 조회
- 고객사에 창고 연결
- 고객사별 기본 창고 설정
- 사용 창고 비활성 처리
- 내부 사용자와 고객사 사용자의 권한 및 scope 기준
- `usage_type`, `is_default`, `active_yn` 정책
- 후속 API 보강 구현과 테스트 범위

이번 작업은 설계 문서 작성만 포함한다. backend 코드, DB schema, migration, seed, frontend 화면은 수정하지 않는다.

## 2. 현재 정책 요약

기준 정책은 `docs/master-data-screen-design-plan-2026-05-29.md`와 `docs/backend-warehouse-policy-audit-2026-05-29.md`를 따른다.

- `warehouses`는 전역 창고 후보 또는 창고마스터로 유지 가능하다.
- `client_warehouse_settings`는 고객사별 사용 창고와 기본 창고 설정을 담당한다.
- 고객사 관리 화면 안에서 사용 창고와 기본 창고를 설정한다.
- 창고마스터 단독 화면은 1차 기준정보 화면에서 앞세우지 않는다.
- 작업자는 세팅된 창고 안에서만 작업한다.
- 고객사 사용자는 자기 고객사의 active 사용 창고만 조회한다.
- 내부 운영자는 권한 범위 안에서 고객사를 선택하고 해당 고객사의 사용 창고를 설정한다.
- `warehouse_id`를 입력받는 모든 업무 API는 resolved `client_id` 기준으로 해당 창고를 사용할 수 있는지 서버에서 검증해야 한다.
- “전체 창고”는 실제 `warehouses` row가 아니라 조회 옵션이다.

## 3. 고객사 관리 화면이 필요로 하는 기능

고객사 상세 화면은 고객사 기본정보만 보여주는 화면이 아니라 해당 고객사가 사용할 창고와 기본 창고를 함께 관리해야 한다.

필요 기능은 다음과 같다.

- 고객사 상세 조회 시 사용 창고 목록 함께 조회
- 사용 가능한 창고 후보 목록 조회
- 고객사에 기존 창고 후보 연결
- 고객사 상세에서 새 창고 후보를 만든 뒤 즉시 고객사에 연결할 수 있는 UX/API 검토
- 고객사에서 창고 연결 해제 또는 비활성
- 고객사별 `usage_type` 지정
- `usage_type`별 기본 창고 지정
- 기본 창고 변경
- 사용중지 창고 신규 작업 선택 차단
- 이미 사용 이력이 있는 창고 설정은 삭제 대신 비활성 처리
- 비활성 설정 포함 조회 옵션
- active setting만 기본 창고 select 후보로 노출

현재 API만으로도 고객사별 사용 창고 조회, 연결, 수정, 기본 창고 지정, 비활성 처리는 가능하다. 다만 고객사 상세 화면에서 자연스럽게 쓰기에는 nested path, 창고 후보 조회, 화면용 response 필드, 비활성 포함 조회 옵션이 부족하다.

## 4. usage_type 정책

현재 backend 서비스의 허용 `usage_type`은 다음 값이다.

| 현재 값 | 화면 표시 후보 | 의미 |
| --- | --- | --- |
| `INBOUND` | 기본 입고창고 | 입고 작업 또는 입고 예정 확정 시 추천되는 창고 |
| `OUTBOUND` | 기본 출고창고 | 출고 작업 또는 출고 검수 시 기본 차감 창고 |
| `RETURN_GOOD` | 반품양품창고 | 양품 판정 반품이 입고되는 창고 |
| `RETURN_HOLD` | 보류창고 | 보류 판정 또는 확인 필요 반품 보관 창고 |
| `RETURN_REFURB` | 리퍼창고 | 리퍼 대상 반품 보관 창고 |
| `RETURN_MANUFACTURER` | 제조사반품창고 | 제조사 반품 또는 회송 대상 창고 |
| `RETURN_DISPOSAL` | 폐기창고 | 폐기 또는 폐기대기 대상 창고 |
| `SAMPLE` | 샘플창고 | 샘플 재고 또는 비판매 운영 재고 창고 |
| `STORAGE` | 보관창고 | 일반 보관 또는 기타 운영 창고 |

사용자가 제안한 `HOLD`, `REFURB`, `MANUFACTURER_RETURN`, `DISPOSAL`은 의미상 현재 값과 겹친다. 1차 구현에서는 기존 backend allowlist와 테스트를 깨지 않기 위해 현재 값을 유지하는 것을 추천한다. 화면에는 한글 표시명을 매핑하고, 추후 공통코드화가 필요하면 별도 설계에서 다룬다.

정책 기준은 다음과 같다.

- `usage_type`은 1차에서는 backend enum allowlist로 유지한다.
- 추후 운영 중 값 추가와 표시순서 관리가 필요해지면 공통코드 그룹으로 전환을 검토한다.
- 같은 `client_id + usage_type`에서 `is_default=true`는 하나만 허용한다.
- 같은 warehouse는 여러 `usage_type`에 사용될 수 있다.
- 같은 `client_id + warehouse_id + usage_type` 중복은 active/inactive 여부와 무관하게 차단한다.
- 사용중지된 setting은 기본 창고가 될 수 없다.
- 사용중지된 warehouse도 기본 창고가 될 수 없다.

## 5. 추천 API 계약

### 현재 API

현재 구현된 endpoint는 다음과 같다.

- `GET /api/master/client-warehouses`
- `POST /api/master/client-warehouses`
- `PATCH /api/master/client-warehouses/{setting_id}`
- `POST /api/master/client-warehouses/{setting_id}/disable`
- `POST /api/master/client-warehouses/{setting_id}/enable`
- `POST /api/master/client-warehouses/{setting_id}/set-default`

현재 API는 기능 자체는 대부분 갖추고 있지만 고객사 상세 화면 관점의 path와 response가 부족하다. 고객사 상세 화면에서는 `client_id`가 URL에 드러나는 nested path가 더 자연스럽다.

### 보강 API 제안

1차 보강 후보는 다음과 같다.

| endpoint | 목적 | 비고 |
| --- | --- | --- |
| `GET /api/master/clients/{client_id}/warehouse-settings` | 고객사 사용 창고 설정 목록 조회 | 현재 `GET /api/master/client-warehouses?client_id=`의 고객사 상세용 alias 또는 정식 endpoint |
| `GET /api/master/clients/{client_id}/warehouse-options` | 고객사에 연결 가능한 창고 후보 조회 | 전체 warehouse 후보 중 active 여부와 연결 여부를 함께 반환 |
| `POST /api/master/clients/{client_id}/warehouse-settings` | 고객사에 창고 연결 | 현재 body의 `client_id`를 path 기준으로 이동 |
| `PATCH /api/master/clients/{client_id}/warehouse-settings/{setting_id}` | 고객사 창고 설정 수정 | `setting_id`가 path `client_id` 소속인지 검증 |
| `POST /api/master/clients/{client_id}/warehouse-settings/{setting_id}/set-default` | 특정 setting을 usage_type 기본 창고로 지정 | 기존 set-default의 nested path |
| `POST /api/master/clients/{client_id}/warehouse-settings/{setting_id}/disable` | 고객사 창고 설정 비활성 | DELETE 대신 disable 우선 |
| `POST /api/master/clients/{client_id}/warehouse-settings/{setting_id}/enable` | 고객사 창고 설정 재활성 | 기존 enable의 nested path |

DELETE API는 1차에서 만들지 않는다. 사용 이력과 재고 수불 연결을 고려하면 고객사별 사용 창고 설정은 물리 삭제보다 비활성이 안전하다.

현재 `/api/master/client-warehouses` endpoint는 기존 테스트와 후속 호환을 위해 유지한다. 신규 nested endpoint는 고객사 상세 화면 전용 계약으로 추가하는 방향이 좋다.

## 6. request/response 설계 초안

### 고객사 사용 창고 설정 목록 response

`GET /api/master/clients/{client_id}/warehouse-settings`

Query 후보:

- `include_inactive`: 기본 `false`
- `usage_type`: optional

Response item 후보:

- `setting_id`
- `client_id`
- `client_code`
- `client_name`
- `warehouse_id`
- `warehouse_code`
- `warehouse_name`
- `warehouse_type`
- `usage_type`
- `usage_type_name`
- `is_default`
- `active_yn`
- `warehouse_active_yn`
- `memo`
- `created_at`
- `updated_at`

현재 `ClientWarehouseSettingResponse`에는 `client_code`, `warehouse_type`, `usage_type_name`, `warehouse_active_yn`, `memo`, timestamps가 없다. 화면 구현 전에 필요한 필드만 보강하는 것이 좋다.

### 창고 후보 response

`GET /api/master/clients/{client_id}/warehouse-options`

Query 후보:

- `keyword`: optional
- `include_inactive`: 기본 `false`
- `usage_type`: optional

Response item 후보:

- `warehouse_id`
- `warehouse_code`
- `warehouse_name`
- `warehouse_type`
- `is_active`
- `already_linked`
- `linked_usage_types`
- `default_usage_types`

이 API는 고객사에 연결 가능한 후보를 보여주기 위한 조회다. 고객사 사용자는 설정 변경 권한이 없으므로 1차에서는 내부 관리자 전용으로 두는 것이 안전하다.

### 고객사 창고 연결 request

`POST /api/master/clients/{client_id}/warehouse-settings`

Request 후보:

- `warehouse_id`: required
- `usage_type`: required
- `is_default`: 기본 `false`

서버는 path의 `client_id`를 기준으로 scope를 검증한다. body에 `client_id`를 받지 않는다.

### 고객사 창고 설정 수정 request

`PATCH /api/master/clients/{client_id}/warehouse-settings/{setting_id}`

Request 후보:

- `usage_type`: optional
- `active_yn`: optional 후보
- `is_default`: optional 후보

1차 구현에서는 기존 API와 맞춰 `usage_type` 수정만 열어두고, `active_yn`은 `disable/enable`, `is_default`는 `set-default`로 분리하는 방식을 추천한다. 이렇게 하면 상태 전이가 명확하고 실수로 기본 창고가 바뀌는 일을 줄일 수 있다.

### 기본창고 설정 request

`POST /api/master/clients/{client_id}/warehouse-settings/{setting_id}/set-default`

Request body는 없어도 된다. `usage_type`은 setting이 가진 값을 사용한다.

대안으로 `POST /api/master/clients/{client_id}/default-warehouses`에 `usage_type`, `warehouse_id`를 받는 형태도 가능하지만, 현재 구조와 테스트를 재사용하려면 `setting_id` 기준이 더 안전하다.

## 7. 권한/scope 기준

### 내부 관리자

- `SUPER_ADMIN`은 통과한다.
- `INTERNAL_ADMIN`은 `MASTER_MANAGE + WAREHOUSE_MANAGE` 권한이 있으면 설정 변경 가능하다.
- 내부 관리자는 `client_id` path로 고객사를 선택할 수 있다.
- 내부 관리자는 창고 후보 목록을 볼 수 있다.

### 내부 작업자

- `INTERNAL_WORKER`는 고객사별 사용 창고 조회는 필요할 수 있다.
- 설정 변경은 기본적으로 불가하다.
- 조회 허용 여부는 `MASTER_VIEW` 보유 여부와 화면 목적에 맞춰 결정한다.

### 고객사 사용자

- `CLIENT_ADMIN`, `CLIENT_USER`, `READ_ONLY`는 창고 설정 변경 불가다.
- 자기 `client_id`의 active 사용 창고 조회만 가능하다.
- 다른 고객사의 `client_id`를 path나 query로 넣으면 `CLIENT_SCOPE_DENIED` 계열 오류로 차단한다.
- 고객사 사용자에게 전체 `warehouses` 후보 목록을 노출하지 않는다.

### 서버 검증

모든 endpoint는 다음을 검증해야 한다.

- 요청 `client_id`가 `AuthContext` 기준 허용 범위인지 확인
- `setting_id`가 해당 `client_id` 소속인지 확인
- `warehouse_id`가 존재하는지 확인
- `warehouse_id`가 active warehouse인지 확인
- create/set-default/enable 시 active client인지 확인
- `active_yn=false` setting은 신규 업무 선택 후보에서 제외
- `warehouse_id` 직접 입력 공격을 업무 API에서 차단할 수 있도록 helper를 별도 제공

## 8. 기본 창고 중복 방지 정책

기본 창고 정책은 다음과 같다.

- 같은 `client_id + usage_type`에서 `is_default=true`는 하나만 허용한다.
- 새 기본 창고 지정 시 기존 active 기본값은 `false`로 변경한다.
- `active_yn=false` setting은 `is_default=true`가 될 수 없다.
- inactive warehouse에 연결된 setting은 기본 창고가 될 수 없다.
- inactive client의 setting은 기본 창고가 될 수 없다.
- 기본 창고 setting의 `usage_type` 변경은 차단한다.
- enable 시에는 `is_default=false`를 유지한다.

기본 창고 비활성화 정책은 두 가지로 나눠 검토할 수 있다.

| 정책 | 장점 | 위험 |
| --- | --- | --- |
| 대체 기본창고 없으면 비활성 차단 | 신규 업무의 기본 창고 공백을 방지 | 운영자가 먼저 기본창고를 바꿔야 해서 관리 절차가 길어짐 |
| 대체 기본창고 없이 비활성 허용 | 사용하지 않는 창고를 즉시 막을 수 있음 | 기본 창고가 없는 업무에서 오류가 늦게 발생 |

현재 구현은 default setting disable을 차단한다. 1차에서는 이 정책을 유지하는 것이 안전하다. 후속으로 “대체 기본창고를 함께 지정하면서 비활성” API가 필요하면 별도 설계한다.

## 9. 삭제/비활성 정책

삭제보다 비활성을 우선한다.

- 고객사별 사용 창고 설정은 물리 삭제하지 않는다.
- 이미 입고, 출고, 반품, 재고 이력이 있는 창고 설정은 삭제 금지다.
- 아직 사용 이력이 없는 설정의 삭제 허용 여부는 후속 검토로 둔다.
- 1차 구현에서는 `disable`을 표준 해제 방식으로 사용한다.
- 비활성 setting은 기본 조회에서 숨긴다.
- 관리자는 `include_inactive=true`로 비활성 포함 조회를 할 수 있어야 한다.
- 창고마스터 자체 삭제는 고객사 사용 창고 설정과 분리된 별도 관리자 정책으로 다룬다.
- “전체 창고”는 row가 아니므로 삭제/비활성 대상이 아니다.

현재 `GET /api/master/client-warehouses`는 active setting, active client, active warehouse만 반환한다. 관리 화면에서 비활성 설정을 확인하려면 `include_inactive` 옵션이 필요하다.

## 10. 고객사 화면 연동 기준

고객사 상세 화면은 다음 API 흐름을 기준으로 설계한다.

화면 구조:

- 고객사 기본정보
- 사용 창고 목록
- 창고 추가/연결
- 기본 창고 설정
- 사용중지 창고 보기 옵션

동작 기준:

1. 고객사 상세 진입 시 `GET /api/master/clients/{client_id}/warehouse-settings`를 호출한다.
2. 사용 창고 목록은 active setting을 기본 표시한다.
3. “사용중지 포함” 토글을 켜면 `include_inactive=true`로 다시 조회한다.
4. 창고 추가 클릭 시 `GET /api/master/clients/{client_id}/warehouse-options`를 호출한다.
5. 창고 후보를 선택하고 `usage_type`, `is_default`를 입력해 `POST /api/master/clients/{client_id}/warehouse-settings`를 호출한다.
6. 기본 창고 지정은 `set-default` endpoint로 처리한다.
7. 사용중지는 `disable` endpoint로 처리한다.
8. 기본 창고 select는 active setting 중에서만 선택한다.
9. `warehouse_name`만으로 판단하지 않고 `warehouse_id`와 `setting_id`를 기준으로 처리한다.

신규 창고 후보 생성은 두 가지 방식이 가능하다.

- 1차: 내부 관리자가 별도 창고 생성 API를 호출한 뒤 고객사에 연결한다.
- 후속: 고객사 상세 화면에서 “새 창고 만들고 연결”을 하나의 UX로 묶고, backend는 transaction 형태의 composite API를 별도 설계한다.

1차 보강에서는 composite API를 만들지 않고, 기존 `POST /api/master/warehouses`와 nested `POST /warehouse-settings` 조합을 우선 추천한다.

## 11. 재고/입고/출고/반품 연동 기준

아직 업무 API를 구현하지 않았더라도 다음 기준은 고정해야 한다.

- 재고 조회에서 `warehouse_id` 미선택은 해당 client의 active 사용 창고 전체 조회다.
- `warehouse_id` 선택 시 해당 client의 active 사용 창고인지 검증한다.
- 입고, 출고, 반품 작업에서 warehouse 선택 목록은 `client_warehouse_settings.active_yn=true` 기준이다.
- 기본 입고, 출고, 반품 창고는 `usage_type + is_default` 기준으로 추천한다.
- 작업자가 창고를 바꿀 수 있어도 해당 client의 active 사용 창고 안에서만 가능하다.
- 고객사 사용자는 자기 client의 active 사용 창고만 조회 가능하다.
- 내부 사용자는 선택 client 기준으로 active 사용 창고만 업무 후보로 본다.
- 업무별 helper 후보:
  - `list_client_allowed_warehouses(client_id, usage_type | None)`
  - `ensure_client_can_use_warehouse(client_id, warehouse_id)`
  - `ensure_client_can_use_warehouse_for_usage(client_id, warehouse_id, usage_type)`
  - `get_default_client_warehouse(client_id, usage_type)`

이 helper들은 `client_warehouse_settings`, `clients.active_yn`, `warehouses.active_yn`을 함께 확인해야 한다.

## 12. 테스트 설계

후속 API 보강 구현 시 필요한 테스트 후보는 다음과 같다.

- 내부 관리자 고객사 사용 창고 목록 조회
- 고객사 사용자 자기 고객사 사용 창고 조회
- 고객사 사용자 다른 고객사 창고 조회 차단
- 내부 작업자 조회 가능 여부 정책 검증
- 고객사 창고 연결
- 중복 연결 차단
- inactive client 연결 차단
- inactive warehouse 연결 차단
- `usage_type`별 기본창고 1개 유지
- 비활성 setting 기본창고 지정 차단
- 기본창고 비활성화 차단 또는 대체 기본창고 요구 정책 검증
- `setting_id`가 path `client_id`와 맞지 않을 때 차단
- `warehouse_id` 직접 입력 공격 차단
- `include_inactive=false` 기본 조회에서 비활성 설정 제외
- `include_inactive=true` 관리자 조회에서 비활성 설정 포함
- active setting만 신규 작업 후보로 반환
- 권한 없는 role의 생성/수정/disable/set-default 차단
- 응답에 불필요한 민감 정보가 없는지 확인

## 13. 현재 API와 보강안 비교

| 기능 | 현재 지원 여부 | 현재 endpoint | 부족한 점 | 보강 필요 여부 | 우선순위 |
| --- | --- | --- | --- | --- | --- |
| 고객사 사용 창고 목록 조회 | 지원 | `GET /api/master/client-warehouses?client_id=` | 고객사 상세용 nested path 아님, 비활성 포함 옵션 없음, `warehouse_type` 등 화면 필드 부족 | 필요 | P0 |
| 창고 후보 조회 | 부분 지원 | `GET /api/master/warehouses` | 내부 전체 창고 목록만 제공, 고객사별 연결 여부와 `linked_usage_types` 없음 | 필요 | P0 |
| 창고 연결 | 지원 | `POST /api/master/client-warehouses` | body `client_id` 방식, 고객사 상세용 path와 setting 소속 검증 표현 부족 | 필요 | P0 |
| 창고 설정 수정 | 부분 지원 | `PATCH /api/master/client-warehouses/{setting_id}` | 현재 `usage_type` 수정 중심, nested path 없음 | 필요 | P1 |
| 기본창고 지정 | 지원 | `POST /api/master/client-warehouses/{setting_id}/set-default` | nested path 없음, 고객사 화면에서 setting 소속 검증이 명확히 드러나지 않음 | 필요 | P0 |
| 사용중지 | 지원 | `POST /api/master/client-warehouses/{setting_id}/disable` | nested path 없음, 대체 기본창고 정책은 후속 | 필요 | P0 |
| 재활성 | 지원 | `POST /api/master/client-warehouses/{setting_id}/enable` | nested path 없음, enable 후 default=false 정책은 유지 필요 | 필요 | P1 |
| 비활성 포함 조회 | 미지원 | 없음 | 관리자가 사용중지 설정을 확인하기 어려움 | 필요 | P0 |
| 고객사 사용자 scope 제한 | 지원 | `GET /api/master/client-warehouses` | nested path에서도 같은 정책 필요 | 필요 | P0 |
| 내부 사용자 권한 제한 | 지원 | 관리 API는 `MASTER_MANAGE + WAREHOUSE_MANAGE` | 조회/후보 API의 내부 작업자 허용 범위는 추가 결정 필요 | 필요 | P1 |
| 사용 창고 테스트 | 지원 | `test_master_api_manage_client_warehouses.py` | nested path, 후보 조회, 비활성 포함 조회 테스트 없음 | 필요 | P0 |

## 14. 후속 구현 범위 제안

다음 작업을 목표추진 모드로 진행한다면 안전한 1차 구현 범위는 다음과 같다.

포함:

- 기존 `/api/master/client-warehouses` 동작 유지
- `GET /api/master/clients/{client_id}/warehouse-settings` 추가
- `GET /api/master/clients/{client_id}/warehouse-options` 추가
- `POST /api/master/clients/{client_id}/warehouse-settings` 추가
- `PATCH /api/master/clients/{client_id}/warehouse-settings/{setting_id}` 추가
- `POST /api/master/clients/{client_id}/warehouse-settings/{setting_id}/set-default` 추가
- `POST /api/master/clients/{client_id}/warehouse-settings/{setting_id}/disable` 추가
- 필요하면 `enable` nested endpoint도 함께 추가
- `include_inactive` 조회 옵션 추가
- response에 `warehouse_type`, `usage_type_name`, `warehouse_active_yn`, timestamps 등 화면 필드 보강
- path `client_id`와 `setting_id` 소속 검증
- 권한/scope 테스트 추가
- closeout 문서 작성

제외:

- frontend 고객사 관리 화면 구현
- 재고 API 구현
- 입고/출고/반품 API 구현
- warehouse 모델에 `client_id`를 추가하는 migration
- `client_warehouse_settings` 삭제 API
- composite “새 창고 만들고 고객사에 연결” API
- usage_type 공통코드화

## 15. closeout 결론

현재 구조는 유지 가능하다. `warehouses`는 전역 창고 후보로 두고, `client_warehouse_settings`가 고객사별 사용 창고와 기본 창고를 담당하는 방향이 P0 기준으로 가장 안전하다.

다만 고객사 관리 화면을 안정적으로 만들려면 기존 `/api/master/client-warehouses`만으로는 화면 계약이 다소 어색하다. 고객사 상세 화면 중심의 nested endpoint, 창고 후보 조회, 비활성 포함 조회, 화면용 response 필드, setting 소속 검증을 보강하는 것이 좋다.

다음 작업은 목표추진 모드로 `client_warehouse_settings` API 보강 구현을 추천한다. 이 보강이 끝나면 고객사 관리 화면 상세 디자인 문서와 화면 구현으로 넘어갈 수 있다.
