# SmartReturn Pro 플랫폼 tenancy 전수 점검

## 목적

SmartReturn Pro의 데이터 계층은 아래 순서로 고정한다.

```text
platform_owner
→ agency_id
→ client_id
→ client_unit_id
```

이번 점검은 다음 단계 작업으로 넘어가기 전에 DB 모델, migration, backend scope, API 응답 타입, 테스트에서 `agency_id → client_id → client_unit_id` 구조가 누락 없이 적용되었는지 확인하고, 실제 누락 지점을 보정한 결과를 남기기 위한 문서다.

## 적용 원칙

- 핵심 운영 테이블과 대량 이력 테이블은 `agency_id`를 직접 저장한다.
- `client_id`가 있는 row는 request body의 `agency_id`를 신뢰하지 않고 `clients.agency_id` 기준으로 `agency_id`를 확정한다.
- `client_unit_id`가 있으면 해당 `client_id` 소속인지 검증한다.
- `warehouse_id`가 있으면 고객사에 연결된 활성 창고인지 검증한다.
- 조회 API는 `AuthContext`의 role/scope 기준으로 `agency_id`, `client_id`, `client_unit_id` 필터를 적용한다.
- 확인 불가 기존 row는 기본 agency로 임의 보정하지 않고 검토 대상으로 남긴다.

## 전수 점검 결과표

| 영역 | 테이블/모델/API | agency_id 직접 저장 | client_id 보유 | client_unit_id 보유 | agency backfill | 생성 시 agency 확정 방식 | 조회 scope 적용 | 불일치 차단 | 조치 결과 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 본사/대리점 | `agencies` | 기준 테이블 | 아니오 | 아니오 | 해당 없음 | 직접 생성 | 내부 권한 | 해당 없음 | 완료 |
| 고객사 | `clients` | 예 | 자기 row | 아니오 | 기존 migration에서 기본 agency 또는 신규 생성 agency | 내부/대리점 권한 기준, request body agency 불신 | 내부 전체, 대리점 자기 agency, 고객사 자기 client | 대리점 범위 외 접근 차단 | 완료 |
| 사용자 | `users` | 예 | 선택 | 아니오 | `client_id → clients.agency_id`, 없으면 기존 migration 정책 | 사용자 생성/seed 기준 | auth context와 role 기반 | 고객사 사용자는 client 필수 | 완료 |
| 로그인 로그 | `auth_login_logs` | 예 | 예 | 아니오 | `user_id → users.agency_id/client_id`; user 확인 불가 row는 null 유지 | 로그인 성공/실패 시 `users.agency_id/client_id` | 조회 API 미구현 | 민감값 미저장 | 수정 완료 |
| 고객사 창고 설정 | `client_warehouse_settings` | 예 | 예 | 아니오 | `client_id → clients.agency_id` | `client_id → clients.agency_id` | 고객사별 조회 | 다른 고객사 창고 사용 차단 보조 기준 | 수정 완료 |
| 고객사 운영단위 | `client_units` | 예 | 예 | 자기 row | `client_id → clients.agency_id` | `client_id → clients.agency_id` | client scope 적용 | `default_warehouse_id/return_warehouse_id`는 고객사 연결 창고만 허용 | 수정 완료 |
| 판정별 창고 라우팅 | `return_judgment_warehouse_routes` | 예 | 예 | 선택 | `client_id → clients.agency_id` | `client_id → clients.agency_id` | client scope 적용 | `client_unit_id`와 `warehouse_id` 모두 client 범위 검증 | 수정 완료 |
| 창고 | `warehouses` | 예외 | 아니오 | 아니오 | 해당 없음 | 전역 물리 창고 마스터 | 내부 관리 API 중심 | 고객사 사용은 `client_warehouse_settings`로 검증 | 예외: 물리 창고 자체는 전역 마스터 |
| 로케이션 | `locations` | 예외 | 아니오 | 아니오 | 해당 없음 | `warehouse_id` 기준 | 창고 scope 후속 확장 대상 | 현재 직접 운영 API 제한적 | 예외: 창고 하위 전역 구조, client 연결은 창고 설정에서 처리 |
| 상품 | `products` | 예 | 예 | 아니오 | `client_id → clients.agency_id` | `client_id → clients.agency_id` | client/agency scope 적용 | 다른 client 접근 차단 | 수정 완료 |
| 상품 바코드 | `product_barcodes` | 예 | 예 | 아니오 | `client_id → clients.agency_id` | `product.client_id → clients.agency_id` | product/client scope 적용 | product client 범위 검증 | 수정 완료 |
| 반품 접수 batch | `return_intake_batches` | 예 | 예 | 선택 | 기존 migration 완료 | `client_id → clients.agency_id` | agency/client scope 적용 | client_unit client 일치 검증 | 완료 |
| 반품 접수/처리 row | `return_intake_rows` | 예 | 예 | 선택 | 기존 migration 완료 | batch/client 기준 | agency/client scope 적용 | client_unit, product, warehouse 확정 검증 | 완료 |
| 반품 처리 증빙 | `return_processing_attachments` | 예 | 예 | row 상속 | `client_id → clients.agency_id` | `return_intake_rows.agency_id` 우선, 없으면 client 기준 | task 접근 scope 적용 | task client scope 검증 | 수정 완료 |
| 반품 외부반출 batch | `return_external_outbound_batches` | 예 | 선택 | row 상속 | `client_id → clients.agency_id`; client 없는 혼합 batch는 null 유지 | 확정 row들의 agency가 하나면 저장 | agency/client scope 적용 | row 접근 scope와 중복 확정 차단 | 수정 완료 |
| 외부반출 scan row/event | 전용 모델 없음 | 보류 | 보류 | 보류 | 해당 없음 | 현재 외부반출 확정 결과가 `return_intake_rows`와 batch에 저장됨 | row/batch scope 적용 | 스캔번호 검증 적용 | 보류: 전용 scan event 테이블 생성 시 agency_id 필수 |
| 라벨 출력 로그 | 전용 모델 없음 | 보류 | 보류 | 보류 | 해당 없음 | 현재 라벨 상태는 `return_intake_rows`에 저장 | row scope 적용 | Local Agent 직접 재고 변경 없음 | 보류: `label_print_logs` 추가 시 agency_id 필수 |
| scan events | 전용 모델 없음 | 보류 | 보류 | 보류 | 해당 없음 | 현재 스캔 처리 이력은 row `raw_data/events`와 memo에 일부 저장 | row scope 적용 | backend 처리 검증 적용 | 보류: `scan_events` 추가 시 agency_id 필수 |
| audit logs | 전용 모델 없음 | 보류 | 보류 | 보류 | 해당 없음 | 로그인 로그 외 감사 테이블 미구현 | 미구현 | 미구현 | 보류: `audit_logs` 추가 시 agency_id/client_id 필수 |
| worker job logs | 전용 모델 없음 | 보류 | 보류 | 보류 | 해당 없음 | 채널 수집은 `channel_sync_jobs` 사용 | agency scope 적용 | account 기준 agency 상속 | 완료/보류: 범용 worker job 테이블은 미구현 |
| local agent event logs | 전용 모델 없음 | 보류 | 보류 | 보류 | 해당 없음 | Local Agent 이벤트 DB 모델 미구현 | 미구현 | 미구현 | 보류 |
| 채널 계정 | `channel_accounts` | 예 | 예 | 선택 | 기존 migration 완료 | `client_id → clients.agency_id` | agency/client scope 적용 | client_unit client 일치 검증 | 완료 |
| 채널 수집 job | `channel_sync_jobs` | 예 | account 상속 | account 상속 | account 기준 backfill | `channel_accounts.agency_id` | account/agency scope 적용 | account 접근 검증 | 완료 |
| 채널 raw event | `channel_raw_events` | 예 | account join | account 상속 | account 기준 backfill | `channel_accounts.agency_id` | agency/client/account scope 적용 | account 기준 저장 | 완료 |
| 채널 반품 후보 | `channel_return_candidates` | 예 | 예 | 선택 | 기존 migration 완료 | account/client 기준 | agency/client/unit scope 적용 | client_unit/product correction scope 검증 | 완료 |
| 상품 채널 매핑 | `product_channel_mappings` | 예 | 예 | 선택 | 기존 migration 완료 | candidate/account/client 기준 | agency/client/unit scope 적용 | product/client scope 검증 | 완료 |
| import job | `import_jobs` | 예 | `requested_client_id` | 아니오 | 기존 migration 완료 | `requested_client_id → clients.agency_id` | agency/client scope 적용 | requested warehouse client 연결 검증 | 수정 완료 |
| import row | `import_job_rows` | 예 | 예 | 아니오 | 기존 migration 완료 | job agency 상속 | job/client scope 적용 | confirm 시 client/product scope 검증 | 완료 |
| import 파일 | `import_job_files` | 예외 | job 상속 | 아니오 | 해당 없음 | job 하위 파일 메타 | job scope로 접근 | 단독 조회 API 없음 | 예외: 독립 운영 row가 아니라 job 하위 파일 메타 |
| import validation errors | `import_validation_errors` | 예외 | job/row 상속 | 아니오 | 해당 없음 | job/row 하위 오류 | job scope로 접근 | 단독 조회 API 없음 | 예외 |
| import mapping profile/decision | `import_mapping_profiles`, `import_mapping_decisions` | 예외 | 선택 | 아니오 | 해당 없음 | client별 또는 공용 mapper 기준 | client scope 적용 | mapper 정책 기준 | 예외: 대량 운영 원장 아님 |
| 재고 이벤트 | `inventory_events` | 예 | 예 | warehouse 기준 | 기존 migration 완료 | 반품 일마감 row agency 상속 | agency/client/warehouse scope 적용 | warehouse/product 확정 후 생성 | 완료 |
| 현재고 | `current_inventory` | 예 | 예 | warehouse 기준 | 기존 migration 완료 | inventory event agency 상속 | agency/client/warehouse scope 적용 | 일마감 후만 변경 | 완료 |
| 재고 조정/이동 이력 | 전용 모델 없음 | 보류 | 보류 | 보류 | 해당 없음 | 미구현 | 미구현 | 미구현 | 보류 |
| dashboard summary | 채널/반품/재고 source 참조 | source별 | source별 | source별 | source 기준 | source table agency 사용 | agency/client scope 적용 | source API 검증 재사용 | 완료 |
| 공통코드/role/permission | `common_*`, `roles`, `permissions` | 예외 | 아니오 | 아니오 | 해당 없음 | 전역 시스템 기준 | 관리 권한 | 업무 데이터 아님 | 예외 |
| 정산/월마감 | 전용 모델 없음 | 보류 | 보류 | 보류 | 해당 없음 | 미구현 | 미구현 | 미구현 | 보류: 생성 시 agency_id 필수 |
| 폐기/제조사반출 이력 | 전용 상세 모델 없음 | 보류 | row에 상태 저장 | row에 저장 | row 기준 | `return_intake_rows` 기준 | row scope 적용 | 현재고 즉시 변경 없음 | 보류: 전용 이력 테이블 추가 시 agency_id 필수 |

## 이번 작업에서 보정한 항목

- `client_units`, `client_warehouse_settings`, `return_judgment_warehouse_routes`, `products`, `product_barcodes`에 `agency_id` 직접 저장 컬럼과 인덱스를 추가했다.
- `return_external_outbound_batches`, `return_processing_attachments`, `auth_login_logs`에 `agency_id`를 추가했다.
- `auth_login_logs`에는 `client_id`도 추가해 로그인 감사 범위를 client 단위로 추적할 수 있게 했다.
- 신규 migration은 `client_id → clients.agency_id`, `user_id → users.agency_id/client_id` 기준으로 backfill한다.
- 확인 불가 row는 기본 agency로 임의 보정하지 않고 null로 남긴다.
- 상품 목록 조회에 agency scope 필터를 추가했다.
- `client_unit.default_warehouse_id`, `client_unit.return_warehouse_id`, `import_jobs.requested_warehouse_id`는 고객사에 연결된 활성 창고만 허용하도록 보강했다.
- 외부반출 batch 목록/상세 조회에 agency scope 필터를 추가했다.
- 반품 처리 증빙과 외부반출 batch API 응답 타입에 `agency_id`를 추가했다.
- frontend master/returns 타입에 누락된 `agency_id`를 추가했다.

## 테스트 보강

- 로그인 성공/실패 시 `auth_login_logs.agency_id/client_id` 저장 확인.
- 상품 생성과 추가 바코드 생성 시 `products/product_barcodes.agency_id` 저장 확인.
- `AGENCY_ADMIN` 상품 목록 조회가 자기 agency 상품만 반환하는지 확인.
- `client_unit` 생성 시 다른 고객사 창고를 차단하는지 확인.
- import job 생성 시 다른 고객사 창고를 차단하는지 확인.
- 반품 처리 증빙 생성/list 응답과 DB row의 `agency_id` 유지 확인.
- 외부반출 batch 생성/list/detail 응답과 DB row의 `agency_id` 유지 확인.

## 보류 항목

아래 전용 테이블은 현재 코드base에 모델/API가 없으므로 이번 작업에서 억지로 생성하지 않았다. 생성 시 반드시 `agency_id`, `client_id`, 필요 시 `client_unit_id`, `warehouse_id`를 직접 저장하고 scope helper를 적용한다.

- `scan_events`
- `audit_logs`
- `label_print_logs`
- `worker_job_logs`
- Local Agent event logs
- 외부반출 전용 scan row/event
- 월마감/정산/사용량 집계 테이블
- 재고 조정/이동 상세 이력 테이블
- 폐기/제조사반출 전용 상세 이력 테이블

## 검증 기준

이번 문서 기준의 완료 판단은 코드 검색만이 아니라 migration, 생성 service, 조회 scope, 테스트 결과를 함께 본다. “대부분 되어 있음”으로 처리하지 않고, 전역 공통 데이터와 미구현 테이블은 예외/보류 이유를 명시한다.
