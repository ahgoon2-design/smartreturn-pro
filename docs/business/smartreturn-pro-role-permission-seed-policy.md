# SmartReturn Pro P0 role/permission seed 정책

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

이 문서는 실제 seed 코드가 아니다. 실제 seed 구현 전에 어떤 role과 permission을 기본값으로 넣을지 확정하는 기준 문서다.

## 1. 문서 목적

- SmartReturn Pro P0 단계에서 필요한 기본 role과 permission seed 기준을 확정한다.
- `SUPER_ADMIN`, `INTERNAL_ADMIN`, `INTERNAL_WORKER`, `CLIENT_ADMIN`, `CLIENT_USER`, `READ_ONLY`의 역할 의미를 고정한다.
- `permission_code` 후보와 role별 기본 권한 매핑을 문서화한다.
- seed 데이터 작성 전 금지사항과 안전 기준을 정리한다.
- 실제 seed 파일, DB insert, migration 수정, API 구현은 이 문서 범위에 포함하지 않는다.

## 2. 기본 원칙

- 사용자 권한은 `client_id` 유무가 아니라 role 기준으로 판단한다.
- 내부 운영자 role과 고객사 사용자 role은 명확히 분리한다.
- 내부 운영자에게 `client_id`가 있어도 고객사 사용자로 판단하지 않는다.
- 고객사 사용자는 자기 `client_id`로 고정된다.
- 프론트 메뉴 제한은 UX이고, 실제 보안은 백엔드 permission/client scope 검증이 담당한다.
- P0 seed는 운영 시작을 위한 최소값만 만든다.
- 과도한 세부 권한은 후속 단계에서 추가한다.
- 실제 사용자 계정 seed는 최소화하고, 평문 비밀번호를 문서나 커밋에 남기지 않는다.

## 3. 표준 role 정의

### SUPER_ADMIN

의미:
- 시스템 전체 최고 관리자다.
- 모든 고객사, 창고, 기준정보, 사용자, 시스템 설정에 접근할 수 있다.

권한 기준:
- 전체 관리가 가능하다.
- 운영사 최고 관리자 전용이다.
- 실제 운영에서는 최소 인원에게만 부여한다.

### INTERNAL_ADMIN

의미:
- 동현물류 내부 운영 관리자다.
- 고객사를 선택할 수 있다.
- 기준정보, 반품, 입고, 출고, 재고, 운영관리 작업을 수행할 수 있다.

권한 기준:
- 사용자 관리와 위험 설정 일부는 `SUPER_ADMIN`보다 제한될 수 있다.
- P0에서는 운영 관리자 역할로 사용한다.

### INTERNAL_WORKER

의미:
- 동현물류 내부 작업자다.
- 고객사를 선택할 수 있다.
- 반품처리, 입고검수, 출고검수, 마감 대조 같은 현장 작업 중심 역할이다.

권한 기준:
- 시스템 설정, 사용자 관리, 정산 설정은 제한한다.
- `client_id`가 있어도 고객사 사용자로 판단하지 않는다.

### CLIENT_ADMIN

의미:
- 고객사 관리자다.
- 자기 `client_id`에 고정된다.
- 자기 고객사의 조회, 자료 업로드 후보, 포털 관리 후보를 가진다.

권한 기준:
- 내부 판정, 마감, 반출, 재고조정은 기본 제한한다.
- 고객사 포털 구현 시 확장한다.

### CLIENT_USER

의미:
- 고객사 일반 사용자다.
- 자기 `client_id`에 고정된다.
- 조회 중심 역할이다.

권한 기준:
- 내부 작업 처리 권한은 없다.
- 자료 업로드는 후속 정책에 따라 제한적으로 허용할 수 있다.

### READ_ONLY

의미:
- 읽기 전용 사용자다.
- 자기 `client_id` 또는 허용 범위에서 조회만 가능하다.

권한 기준:
- 생성, 수정, 삭제, 확정, 취소, 정정이 불가하다.

## 4. permission_code 후보

P0 seed에 넣을 `permission_code`는 너무 세분화하지 않고 P0 구현에 필요한 수준으로 시작한다.

### 시스템/사용자

- `SYSTEM_ADMIN`
- `USER_MANAGE`
- `ROLE_MANAGE`

### 기준정보

- `MASTER_VIEW`
- `MASTER_MANAGE`
- `CLIENT_MANAGE`
- `WAREHOUSE_MANAGE`
- `PRODUCT_MANAGE`
- `COMMON_CODE_MANAGE`

### import job / 업로드

- `IMPORT_VIEW`
- `IMPORT_MANAGE`

### 반품

- `RETURN_VIEW`
- `RETURN_PREPARE`
- `RETURN_PROCESS`
- `RETURN_JUDGE`
- `RETURN_CLOSE`
- `RETURN_OUTBOUND`
- `RETURN_TRACE`

### 입고

- `INBOUND_VIEW`
- `INBOUND_PROCESS`
- `INBOUND_CONFIRM`

### 출고

- `OUTBOUND_VIEW`
- `OUTBOUND_PROCESS`
- `OUTBOUND_CONFIRM`

### 재고

- `INVENTORY_VIEW`
- `INVENTORY_EVENT_VIEW`
- `INVENTORY_ADJUST`

### 정산

- `SETTLEMENT_VIEW`
- `SETTLEMENT_MANAGE`

### Local Agent / 장치

- `LOCAL_AGENT_VIEW`
- `LOCAL_AGENT_MANAGE`

정책:
- `permission_code`는 저장 키이므로 변경을 신중히 한다.
- 화면 표시명은 별도 `permission_name` 또는 문서의 한글명으로 관리한다.
- 권한이 늘어나도 role/client scope 검증을 대체하지 않는다.

## 5. permission 한글명 후보

| permission_code | 한글명 | 설명 | P0 포함 여부 | 후속 후보 여부 |
| --- | --- | --- | --- | --- |
| `SYSTEM_ADMIN` | 시스템 관리 | 시스템 위험 설정과 전역 운영 설정 권한이다. | 포함 후보 | 예 |
| `USER_MANAGE` | 사용자 관리 | 사용자 생성, 사용중지, 비밀번호 초기화 후보 권한이다. | 포함 | 예 |
| `ROLE_MANAGE` | 역할 관리 | role과 permission 매핑을 관리하는 권한이다. | 포함 후보 | 예 |
| `MASTER_VIEW` | 기준정보 조회 | 고객사, 창고, 상품, 공통코드 기준정보 조회 권한이다. | 포함 | 예 |
| `MASTER_MANAGE` | 기준정보 관리 | 기준정보 생성, 수정, 사용중지 권한이다. | 포함 | 예 |
| `CLIENT_MANAGE` | 고객사 관리 | 고객사 기준정보 관리 권한이다. | 포함 | 예 |
| `WAREHOUSE_MANAGE` | 창고 관리 | 창고와 고객사 사용창고 설정 관리 권한이다. | 포함 | 예 |
| `PRODUCT_MANAGE` | 상품 관리 | 상품과 추가 바코드 관리 권한이다. | 포함 | 예 |
| `COMMON_CODE_MANAGE` | 공통코드 관리 | 공통코드 그룹과 코드값 관리 권한이다. | 포함 | 예 |
| `IMPORT_VIEW` | 업로드 조회 | import job, 업로드 이력, 검증 결과 조회 권한이다. | 포함 | 예 |
| `IMPORT_MANAGE` | 업로드 관리 | 업로드 preview, 검증, 저장 확정 후보 권한이다. | 포함 | 예 |
| `RETURN_VIEW` | 반품 조회 | 반품 자료와 처리 결과 조회 권한이다. | 포함 | 예 |
| `RETURN_PREPARE` | 반품자료 준비 | CJ/택배 반품예정 자료 등록과 저장 확정 후보 권한이다. | 포함 | 예 |
| `RETURN_PROCESS` | 반품처리 | 실제 도착 반품 스캔과 작업 시작 후보 권한이다. | 포함 | 예 |
| `RETURN_JUDGE` | 반품 판정 | 반품 상품/수량/판정 저장 후보 권한이다. | 포함 | 예 |
| `RETURN_CLOSE` | 반품 마감 | 판정 완료 결과 대조와 마감확정 후보 권한이다. | 포함 | 예 |
| `RETURN_OUTBOUND` | 반품 반출 | 외부반출 묶음 생성, 스캔 대조, 반출확정 후보 권한이다. | 포함 | 예 |
| `RETURN_TRACE` | 반품 통합추적 | 반품 전체 흐름 읽기 전용 추적 권한이다. | 포함 | 예 |
| `INBOUND_VIEW` | 입고 조회 | 입고 자료와 입고 결과 조회 권한이다. | 포함 후보 | 예 |
| `INBOUND_PROCESS` | 입고 처리 | 입고검수 작업 후보 권한이다. | 포함 후보 | 예 |
| `INBOUND_CONFIRM` | 입고 확정 | 입고 확정 후보 권한이다. | 포함 후보 | 예 |
| `OUTBOUND_VIEW` | 출고 조회 | 출고 자료와 출고 결과 조회 권한이다. | 포함 후보 | 예 |
| `OUTBOUND_PROCESS` | 출고 처리 | 출고검수 작업 후보 권한이다. | 포함 후보 | 예 |
| `OUTBOUND_CONFIRM` | 출고 확정 | 출고 확정 후보 권한이다. | 포함 후보 | 예 |
| `INVENTORY_VIEW` | 재고 조회 | 현재고와 기본 재고 현황 조회 권한이다. | 포함 | 예 |
| `INVENTORY_EVENT_VIEW` | 재고 이벤트 조회 | `inventory_events` 이력 조회 권한이다. | 포함 | 예 |
| `INVENTORY_ADJUST` | 재고 조정 | 수동 재고 조정 후보 권한이다. | 포함 후보 | 예 |
| `SETTLEMENT_VIEW` | 정산 조회 | 정산 결과 조회 후보 권한이다. | 포함 후보 | 예 |
| `SETTLEMENT_MANAGE` | 정산 관리 | 정산 생성, 마감, 조정 후보 권한이다. | 후속 후보 | 예 |
| `LOCAL_AGENT_VIEW` | Local Agent 조회 | 장치 연결상태와 로그 조회 후보 권한이다. | 포함 후보 | 예 |
| `LOCAL_AGENT_MANAGE` | Local Agent 관리 | 장치 설정과 등록 관리 후보 권한이다. | 후속 후보 | 예 |

## 6. role별 기본 permission 매핑

| role_code | 기본 permission | 제한 사항 | 비고 |
| --- | --- | --- | --- |
| `SUPER_ADMIN` | 모든 permission | 없음. 단, 실제 운영에서는 최소 인원 원칙을 적용한다. | 운영사 최고 관리자 전용 |
| `INTERNAL_ADMIN` | `USER_MANAGE`, `MASTER_VIEW`, `MASTER_MANAGE`, `CLIENT_MANAGE`, `WAREHOUSE_MANAGE`, `PRODUCT_MANAGE`, `COMMON_CODE_MANAGE`, `IMPORT_VIEW`, `IMPORT_MANAGE`, `RETURN_VIEW`, `RETURN_PREPARE`, `RETURN_PROCESS`, `RETURN_JUDGE`, `RETURN_CLOSE`, `RETURN_OUTBOUND`, `RETURN_TRACE`, `INBOUND_VIEW`, `INBOUND_PROCESS`, `INBOUND_CONFIRM`, `OUTBOUND_VIEW`, `OUTBOUND_PROCESS`, `OUTBOUND_CONFIRM`, `INVENTORY_VIEW`, `INVENTORY_EVENT_VIEW`, `LOCAL_AGENT_VIEW` | `SYSTEM_ADMIN`, `ROLE_MANAGE`, `INVENTORY_ADJUST`, `SETTLEMENT_MANAGE`는 후속 정책에서 제한 여부를 확정한다. | P0 운영 관리자 기본 role |
| `INTERNAL_WORKER` | `MASTER_VIEW`, `RETURN_VIEW`, `RETURN_PROCESS`, `RETURN_JUDGE`, `RETURN_CLOSE` 후보, `RETURN_OUTBOUND` 후보, `INBOUND_VIEW`, `INBOUND_PROCESS`, `OUTBOUND_VIEW`, `OUTBOUND_PROCESS`, `INVENTORY_VIEW`, `LOCAL_AGENT_VIEW` | `USER_MANAGE`, `SYSTEM_ADMIN`, `ROLE_MANAGE`, `INVENTORY_ADJUST`, `SETTLEMENT_MANAGE`, `COMMON_CODE_MANAGE` 금지 | 현장 작업 중심 |
| `CLIENT_ADMIN` | `MASTER_VIEW` 제한적, `IMPORT_VIEW` 후보, `RETURN_VIEW`, `RETURN_TRACE`, `INBOUND_VIEW` 후보, `OUTBOUND_VIEW`, `INVENTORY_VIEW`, `SETTLEMENT_VIEW` 후보 | 자기 `client_id` 범위만 가능하다. `RETURN_PROCESS`, `RETURN_JUDGE`, `RETURN_CLOSE`, `RETURN_OUTBOUND`, `INVENTORY_ADJUST`는 기본 금지다. | 고객사 포털 구현 시 확장 |
| `CLIENT_USER` | `RETURN_VIEW`, `RETURN_TRACE`, `OUTBOUND_VIEW`, `INVENTORY_VIEW` 후보, `SETTLEMENT_VIEW` 후보 | 자기 `client_id` 범위만 가능하다. 생성, 수정, 확정, 취소, 정정은 금지다. | 조회 중심 |
| `READ_ONLY` | `RETURN_VIEW`, `RETURN_TRACE`, `OUTBOUND_VIEW`, `INVENTORY_VIEW`, `SETTLEMENT_VIEW` 후보 | 모든 쓰기 작업 금지. 화면에서도 쓰기 버튼을 숨기고 백엔드에서도 쓰기 API를 차단한다. | 읽기 전용 |

## 7. seed 구현 방식 후보

권장 방식:
- idempotent seed 함수 또는 스크립트로 작성한다.
- 이미 존재하는 `role_code`, `permission_code`는 중복 생성하지 않는다.
- 이름과 설명은 업데이트 가능하지만 저장 키인 code 값은 변경하지 않는다.
- seed 실행은 개발 초기 또는 migration 이후 별도 명령으로 수행한다.
- seed가 실패하면 부분 중복이 생기지 않도록 트랜잭션과 재실행 정책을 고려한다.

후보 위치:
- `backend/app/seed/`
- `backend/app/seed/roles.py`
- `backend/scripts/seed_p0.py`

이번 작업에서는 위 파일을 만들지 않는다.

주의:
- Alembic migration에 seed 데이터를 직접 넣을지, 별도 seed 스크립트로 뺄지는 후속 구현 전 결정한다.
- 권한 seed는 업무 데이터가 아니지만, migration에 넣으면 rollback과 환경 차이에 주의해야 한다.
- P0에서는 별도 seed 스크립트 후보를 우선 검토한다.

## 8. 초기 관리자 계정 정책

- 초기 `SUPER_ADMIN` 계정은 필요하지만, 평문 비밀번호를 문서, 코드, 커밋에 남기지 않는다.
- 초기 계정 생성은 후속 seed 또는 별도 admin bootstrap 명령으로 분리한다.
- `must_change_password=true`를 기본으로 둔다.
- 운영사 관리자는 비밀번호를 조회하지 못하고 초기화/재발급만 가능하다.
- 초기 비밀번호는 실행 시 입력받거나 로컬 환경변수로 주입하는 방식을 검토한다.
- 실제 고객사 사용자 계정 seed는 P0에서 만들지 않는다.

## 9. role/client scope와 permission의 관계

- permission은 “무엇을 할 수 있는지”를 정한다.
- client scope는 “어느 고객사 데이터에 접근할 수 있는지”를 정한다.
- warehouse scope는 “어느 창고 데이터에 접근할 수 있는지”를 정한다.
- permission이 있어도 client scope 밖 데이터는 접근할 수 없다.
- permission이 있어도 warehouse scope 밖 창고 작업은 할 수 없다.
- `READ_ONLY`는 조회 permission만 있어도 쓰기 API를 호출할 수 없다.

## 10. 금지사항

- `client_id` 유무로 내부/고객사 사용자 판단 금지.
- role 없이 기본 `CLIENT_USER`로 추론 금지.
- `SUPER_ADMIN`을 일반 작업자에게 부여 금지.
- 모든 내부 작업자에게 `SYSTEM_ADMIN` 부여 금지.
- 고객사 사용자에게 `RETURN_JUDGE`, `RETURN_CLOSE`, `RETURN_OUTBOUND` 기본 부여 금지.
- permission만 보고 client scope 검증을 생략 금지.
- seed에 실제 고객사 개인정보 입력 금지.
- seed에 평문 운영 비밀번호 저장 금지.
- 권한 부족을 프론트에서만 막고 백엔드에서 허용하는 구조 금지.

## 11. 후속 구현 순서

1. role/permission seed 구현 방식 확정
2. seed 스크립트 skeleton 작성
3. role/permission idempotent upsert 구현
4. 초기 관리자 계정 bootstrap 정책 확정
5. `AuthContext` schema 구현
6. `require_roles` / `require_permission` / `require_client_access` dependency 구현
7. 기준정보 API에 권한 적용
8. 반품 API에 권한 적용

## 12. Codex 구현 전 체크

- 이 작업이 role seed인지 permission seed인지 구분했는가?
- `role_code` / `permission_code`가 안정적인 저장 키인가?
- 이미 존재하는 code를 중복 생성하지 않는가?
- permission과 client scope를 혼동하지 않는가?
- 고객사 사용자가 다른 고객사 데이터에 접근할 수 없게 설계했는가?
- 초기 비밀번호를 문서/코드/커밋에 남기지 않았는가?
- 실제 고객사 개인정보를 seed에 넣지 않았는가?
- 백엔드 권한 검증 없이 프론트 메뉴 숨김만으로 처리하고 있지 않은가?
