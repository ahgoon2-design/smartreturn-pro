# SmartReturn Pro DB 및 import 정책

이 문서는 SmartReturn Pro 신규 제작 기준이다. 기존 SmartReturn의 구현기록, 테이블 구조, import 처리 방식을 그대로 따르지 않는다.

## DB 설계 방향

- PostgreSQL 우선 설계로 작성한다.
- 다만 특정 DB 기능에 과도하게 종속되지 않도록 DB 중립성을 고려한다.
- 업무 원장, 업무 테이블, 로그 테이블, import job 테이블을 분리한다.
- 데이터 정합성은 화면 편의보다 우선한다.

## scope 원칙

- SmartReturn Pro의 데이터 계층은 `platform_owner → agency_id → client_id → client_unit_id → warehouse_id` 기준이다.
- Basic, Pro, Ultra 플랜은 이 계층을 바꾸지 않는다.
- 핵심 운영 테이블은 대리점별 조회, 정산, 감사, 장애추적을 위해 `agency_id` 직접 저장을 고려한다.
- `client_id`가 있는 row는 요청 body가 아니라 `clients.agency_id` 기준으로 `agency_id`를 확정한다.
- 모든 업무 데이터는 `client_id` scope를 반드시 가진다.
- 창고 업무 데이터는 `warehouse_id` scope를 반드시 가진다.
- 고객사 사용자는 자기 `client_id`로 고정된다.
- 내부 운영자는 `role` 기준으로 고객사를 선택할 수 있다.
- 고객사 선택 가능 여부를 `client_id` 유무로 판단하지 않는다.

## 비교용 정규화 원칙

- 운송장번호, 상품코드, 바코드는 비교용 정규화 기준을 둔다.
- 원본 값은 보존하고, 비교용 값은 별도 normalized 필드 또는 계산 기준으로 관리한다.
- 공백, 하이픈, 대소문자, 앞뒤 특수문자 처리 기준을 문서화한다.
- 정규화 결과가 같아도 원본 값은 감사와 추적을 위해 유지한다.

## import job 구조

- `import_jobs`: 업로드 단위, source type, 업로드 사용자, 상태, 생성 시각을 관리한다.
- `import_job_rows`: 원본 row 단위 데이터를 보존한다.
- `import_validation_errors`: row별 검증 오류와 경고를 관리한다.
- 실제 업무 테이블과 import job은 분리한다.
- import job은 업무 처리의 준비 단계이며 업무 원장 자체가 아니다.

## Smart Import Mapper UX 기준

Smart Import Mapper와 저장전검증 화면은 `docs/db/smart-import-mapper-pipeline.md`를 따른다.

- 같은 운송장 여러 상품은 무조건 확인필요가 아니다. 출고도 합포장이고 반품도 나간 만큼 들어온 경우 정상일 수 있다.
- 기존 저장자료 중복은 “오류” 하나로만 표시하지 않고 “이미 저장됨”, “중복 후보”, “재등록 확인” 등으로 구분한다.
- 기존 저장자료와 값이 다르면 어떤 컬럼이 다른지 기존 값/업로드 값을 함께 보여준다.
- 컬럼매핑 수정 후에는 변경 전/후, 재검증 범위, 결과를 명확히 보여준다.
- 원본보기, 수정보기, 검증결과보기 상태를 구분한다.

## 원본 보존 원칙

- `row_no`를 보존한다.
- `row_hash`를 보존해 중복과 변경 여부를 비교할 수 있게 한다.
- `source_row_key`를 보존해 외부 원본과 연결할 수 있게 한다.
- 원본 컬럼과 매핑 후 컬럼을 구분한다.
- 원본이 잘못되었더라도 임의 수정하지 않고 검증 결과로 표시한다.

## `batch_id` 원칙

- `batch_id`는 원본 추적과 이력 조회를 위한 보조키다.
- `batch_id`를 업무 처리 중심키로 사용하지 않는다.
- 업무 처리 상태는 업무 테이블의 고유 식별자와 상태값으로 관리한다.
- 여러 import batch가 하나의 업무 대상에 연결될 수 있고, 하나의 batch가 여러 업무 대상으로 분리될 수 있다.

## bulk insert/upsert 원칙

- 대량 업로드는 bulk insert를 우선한다.
- 중복 가능성이 있는 기준정보와 외부 원본 연결은 명확한 unique key를 정한 뒤 upsert한다.
- upsert는 데이터 덮어쓰기 정책을 문서화한 뒤 사용한다.
- 검증 실패 row는 업무 테이블에 반영하지 않는다.

## 재고 원장 원칙

- `inventory_events`는 재고 이벤트 원장이다.
- `current_inventory`는 현재고 요약이다.
- 현재고는 원장 이벤트의 결과로 관리되어야 한다.
- 원장 이벤트 없이 현재고만 직접 수정하지 않는다.
- 수량 보정도 별도 이벤트로 기록한다.

## 스캔과 재고 분리

- `scan_events`는 스캔 이벤트 로그다.
- `scan_events`는 재고 원장이 아니다.
- 스캔 성공이 곧 재고 반영을 의미하지 않는다.
- 재고 반영은 서버 업무 확정 흐름에서 `inventory_events` 생성으로 처리한다.

## 멱등성과 취소 원칙

- 외부 이벤트, 스캔 확정, 재고 반영에는 `idempotency_key` 기준을 둔다.
- 동일 작업이 반복 호출되어도 중복 반영되지 않아야 한다.
- 취소나 반전 처리는 원본 이벤트를 삭제하지 않고 `reverse_event_id`로 연결한다.
- 감사 추적을 위해 원장 이벤트는 가능한 한 수정보다 반전 이벤트를 사용한다.

## Codex 구현 전 체크

- `client_id`와 `warehouse_id` scope가 명확한가?
- `agency_id`가 필요한 운영 row에서 누락되지 않았는가?
- request body의 `agency_id`를 그대로 믿고 있지 않은가?
- 원본 row와 업무 테이블이 분리되어 있는가?
- `batch_id`를 업무 처리 중심키로 사용하지 않았는가?
- `row_no`, `row_hash`, `source_row_key`를 보존하는가?
- `scan_events`와 `inventory_events`가 분리되어 있는가?
- 재고 변경이 서버 업무 확정 흐름에서만 발생하는가?
- 멱등성과 반전 이벤트 기준이 있는가?
