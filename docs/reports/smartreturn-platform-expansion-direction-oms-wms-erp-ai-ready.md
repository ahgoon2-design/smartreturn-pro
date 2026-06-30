# SmartReturn SaaS Platform Expansion Direction

문서 성격: 똘순이 정책 결정문 / 후속 SPEC 상위 기준  
적용 대상: SmartReturn-platform  
권장 저장 경로: `docs/decisions/smartreturn-platform-expansion-direction-oms-wms-erp-ai-ready.md`  
구현 여부: 본 문서는 구현 지시가 아니며, 후속 SPEC 설계의 기준 문서다.  
위험도: 고위험 플랫폼 확장 기준 문서  
핵심 원칙: 지금 모든 기능을 만들지는 않되, 나중에 뒤집지 않도록 데이터·권한·연동·운영 뼈대를 선행한다.

---

## 1. 목적

SmartReturn은 단순 반품 처리 프로그램이 아니라, 대리점·고객사·처리센터·본사가 함께 사용하는 SaaS 플랫폼으로 확장한다.

향후 SmartReturn은 다음 시스템과 연결 가능한 구조를 가져야 한다.

- OMS: 주문, 판매채널, 반품 요청, 고객 주문 정보
- WMS: 입고, 검수, 보관, 로케이션, 재고 이동, 출고
- ERP: 정산, 청구, 세금계산, 회계, 수수료, 사용료
- AI 운영 레이어: 반품 판정 보조, 이미지/영상 분석, 이상탐지, 운영 리포트, 비용/정확도 관리

본 결정문의 목적은 지금 단계에서 모든 OMS/WMS/ERP/AI 기능을 구현하는 것이 아니다.  
목적은 나중에 해당 기능을 붙일 때 DB/API/권한/재고/정산 구조를 크게 뒤집지 않도록 선행 데이터 구조와 운영 원칙을 고정하는 것이다.

---

## 2. SmartReturn의 플랫폼 위치

SmartReturn은 OMS, WMS, ERP 전체를 대체하는 시스템으로 시작하지 않는다.

SmartReturn의 1차 위치는 다음과 같다.

```text
SmartReturn = 반품 중심 SaaS 허브
```

시스템 관계는 다음과 같이 본다.

```text
OMS
주문 / 반품 요청 / 판매채널 데이터
        ↓
SmartReturn
반품 접수 / 스캔 / 검수 / 판정 / 보류 / 재고반영 / 정산근거 / AI보조
        ↓
WMS
창고 입고 / 로케이션 / 실물 재고 / 이동 / 출고
        ↓
ERP
청구 / 정산 / 세금 / 회계 / 수수료 / 플랫폼 사용료
```

SmartReturn은 반품 처리 결과와 증거를 표준화하고, OMS/WMS/ERP가 사용할 수 있는 이벤트와 정산 근거를 생성하는 중심 허브가 된다.

---

## 3. 플랫폼 확장 기본 원칙

### 3.1 외부 시스템 종속 금지

특정 OMS/WMS/ERP 전용 컬럼을 핵심 본 테이블에 직접 박지 않는다.

금지 예시:

```text
oms_order_id
cafe24_order_id
shopify_order_id
wms_receipt_id
erp_invoice_id
external_status_1
external_status_2
```

대신 외부 ID는 `external_references` 구조로 분리한다.

원칙:

```text
내부 정본 ID는 SmartReturn이 가진다.
외부 시스템 ID는 매핑 테이블에서 관리한다.
```

---

### 3.2 주문, 반품요청, 실제입고 분리

OMS에서 넘어오는 반품 요청과 현장에서 실제 도착한 물건은 다를 수 있다.

따라서 아래 개념은 분리한다.

```text
sales_order
= 원주문

return_authorization
= OMS/고객사/고객이 요청한 반품

return_receipt
= 실제 현장에 도착해 스캔된 입고

return_item
= 실제 상품 단위 검수/판정 결과
```

이 분리를 하지 않으면 다음 상황을 처리하기 어렵다.

- 반품 요청은 있었지만 물건이 도착하지 않음
- 요청 없이 물건만 도착함
- 운송장은 맞지만 상품이 다름
- 한 운송장에 여러 상품이 들어 있음
- 주문정보 없이 수기 반품 처리 필요
- AI가 주문/상품 매칭 후보를 추천해야 함

---

### 3.3 재고는 이벤트 원장 방식으로 관리

재고 수량만 직접 수정하는 구조로 가지 않는다.

재고는 반드시 이벤트 원장을 기준으로 한다.

```text
inventory_events
= 모든 재고 증감의 원장

current_inventory
= 현재 재고 조회용 집계
```

원칙:

```text
재고 수량은 이벤트 결과다.
재고 이벤트 없이 현재 수량만 바꾸는 구조는 금지한다.
```

필수 개념:

- qty_delta
- source_entity_type
- source_entity_id
- idempotency_key
- occurred_at
- created_by
- stock_status
- warehouse_id
- location_id
- product_id

---

### 3.4 정산은 라인 원장 방식으로 관리

정산 총액만 저장하지 않는다.

정산은 반드시 라인 근거를 가진다.

```text
settlement_documents
= 정산 문서 헤더

settlement_lines
= 정산 근거 라인
```

정산 라인은 다음 출처와 연결될 수 있어야 한다.

- return_item
- inventory_event
- service_fee
- storage_fee
- disposal_fee
- vendor_return_fee
- center_processing_fee
- platform_fee
- ai_usage_fee

원칙:

```text
ERP로 넘길 수 있는 정산 근거를 처음부터 라인 단위로 쌓는다.
```

---

### 3.5 모든 연동은 idempotency를 가져야 한다

외부 시스템은 같은 이벤트를 여러 번 보낼 수 있다.  
따라서 중복 처리 방지를 위해 모든 연동 이벤트에는 idempotency key가 있어야 한다.

적용 대상:

- OMS 반품 요청 수신
- WMS 입고/출고/재고 이벤트 수신
- ERP 정산 export
- 엑셀 import
- webhook 수신
- AI 분석 요청
- 재고 반영
- 정산 확정

원칙:

```text
같은 이벤트가 여러 번 들어와도 결과는 한 번만 반영되어야 한다.
```

---

### 3.6 모든 데이터는 tenant scope를 가진다

SmartReturn은 SaaS 플랫폼이다.  
따라서 모든 핵심 데이터는 대리점·고객사·창고·처리센터 범위를 가져야 한다.

필수 scope 후보:

```text
owner_agency_id
processing_agency_id
client_id
warehouse_id
user_id
role
allowed_client_ids
allowed_warehouse_ids
```

원칙:

```text
frontend 표시 제어만으로 권한을 처리하지 않는다.
backend API와 DB 조회 단계에서 tenant scope를 강제한다.
```

---

## 4. 대리점 보호형 처리망 원칙

SmartReturn은 대리점 고객 소유권을 보호한다.

원칙:

```text
고객사 소유권 = 대리점
처리 수행권 = 위임 가능
본사 직영/처리센터 = 처리 수행자
```

따라서 처리센터가 반품을 처리하더라도 고객 소유권은 처리센터로 넘어가지 않는다.

필수 구분:

```text
owner_agency_id
= 고객 소유권을 가진 대리점

processing_agency_id
= 실제 처리를 수행하는 대리점/센터
```

처리센터는 위임받은 데이터만 조회·처리할 수 있다.  
고객사 전체 데이터나 대리점 소유권을 가져갈 수 없다.

---

## 5. 선행 데이터 구조

### 5.1 External References

목적: 외부 시스템 ID 매핑

```text
external_references
- id
- agency_id
- client_id
- entity_type
- entity_id
- external_system
- external_entity_type
- external_id
- external_status
- source_payload_hash
- first_seen_at
- last_synced_at
- is_primary
```

적용 예시:

```text
SmartReturn return_id ↔ OMS return_order_id
SmartReturn receipt_id ↔ WMS receipt_id
SmartReturn settlement_id ↔ ERP document_id
SmartReturn product_id ↔ 고객사 SKU
```

---

### 5.2 Status Mappings

목적: 내부 상태와 외부 상태 매핑

```text
status_mappings
- id
- mapping_group
- internal_status
- external_system
- external_status
- direction
- is_active
```

예시:

```text
SmartReturn 완료 ↔ WMS inspected
SmartReturn 정산확정 ↔ ERP exported
OMS return_requested ↔ SmartReturn 반품요청
```

---

### 5.3 Integration Inbox / Outbox

목적: 외부 연동 이벤트 수신/발신 기록

```text
integration_inbox
- id
- external_system
- event_type
- external_event_id
- payload
- payload_hash
- received_at
- processed_at
- processing_status
- error_message
- retry_count
```

```text
integration_outbox
- id
- target_system
- event_type
- entity_type
- entity_id
- payload
- status
- retry_count
- next_retry_at
- sent_at
- error_message
```

원칙:

```text
외부 연동은 API 호출 성공 여부만 보지 않는다.
무엇을 받았고, 무엇을 처리했고, 무엇을 보냈는지 기록한다.
```

---

### 5.4 Product Master

목적: OMS/WMS/ERP/AI가 함께 사용할 상품 기준

```text
products
- id
- agency_id
- client_id
- product_code
- sku
- gtin
- product_name
- brand
- option_name
- category
- unit
- is_active
```

```text
product_barcodes
- id
- product_id
- barcode
- barcode_type
- is_primary
- valid_from
- valid_to
```

원칙:

```text
상품 바코드는 1개라고 가정하지 않는다.
상품 코드, SKU, GTIN, 내부 바코드, 박스 바코드, 옵션 바코드를 수용할 수 있어야 한다.
```

---

### 5.5 Warehouse / Location

목적: WMS 확장 대비

```text
warehouses
- id
- agency_id
- warehouse_code
- warehouse_name
- warehouse_type
- address
- is_active
```

```text
warehouse_locations
- id
- warehouse_id
- location_code
- zone
- aisle
- rack
- shelf
- bin
- location_type
- is_active
```

필수 논리 위치:

```text
입고대기
검수중
보류
식별불가
처분대기
정상재고
폐기대기
제조사반품대기
외부반출대기
```

---

### 5.6 Order / Return / Receipt

목적: OMS 확장 대비

```text
sales_orders
- id
- agency_id
- client_id
- order_no
- order_date
- customer_ref
- sales_channel
- external_order_id
- order_status
```

```text
sales_order_lines
- id
- sales_order_id
- line_no
- product_id
- sku
- ordered_qty
- shipped_qty
- unit_price
- discount_amount
- tax_amount
```

```text
return_authorizations
- id
- agency_id
- client_id
- source_system
- external_return_id
- sales_order_id
- requested_at
- reason_code
- status
```

```text
return_receipts
- id
- agency_id
- client_id
- warehouse_id
- tracking_number
- received_at
- received_by
- source
- status
```

```text
return_receipt_links
- id
- return_receipt_id
- return_authorization_id
- match_type
- confidence
```

```text
return_items
- id
- return_receipt_id
- sales_order_line_id
- product_id
- expected_qty
- received_qty
- judged_qty
- final_disposition
```

---

### 5.7 Inventory Ledger

목적: WMS/재고/마감/정산 연결

```text
inventory_events
- id
- agency_id
- client_id
- warehouse_id
- location_id
- product_id
- event_type
- qty_delta
- unit
- source_entity_type
- source_entity_id
- idempotency_key
- occurred_at
- created_by
```

```text
current_inventory
- agency_id
- client_id
- warehouse_id
- location_id
- product_id
- stock_status
- qty
- updated_at
```

재고 이벤트 예시:

```text
return_received
inspection_passed
hold
unidentified
disposal_wait
disposed
vendor_return_wait
vendor_returned
external_transfer_out
adjustment
transfer_in
transfer_out
```

---

### 5.8 Settlement Ledger

목적: ERP/청구/정산 연결

```text
settlement_documents
- id
- agency_id
- client_id
- settlement_period_start
- settlement_period_end
- settlement_type
- status
- total_amount
- tax_amount
- confirmed_at
```

```text
settlement_lines
- id
- settlement_document_id
- source_entity_type
- source_entity_id
- service_code
- qty
- unit_price
- amount
- tax_amount
```

```text
service_codes
- id
- code
- name
- billable
- taxable
- default_unit
```

```text
rate_cards
- id
- agency_id
- client_id
- service_code
- unit_price
- effective_from
- effective_to
```

```text
erp_exports
- id
- settlement_document_id
- erp_system
- export_status
- external_document_id
- exported_at
- error_message
```

---

### 5.9 Import / Export Jobs

목적: API 연동 전 엑셀·CSV 기반 현장 대응

```text
import_jobs
- id
- source_type
- import_type
- file_id
- status
- total_rows
- success_rows
- failed_rows
- created_by
- created_at
```

```text
import_job_errors
- id
- import_job_id
- row_no
- field_name
- error_code
- error_message
- raw_row
```

```text
export_jobs
- id
- export_type
- target_system
- file_id
- status
- created_by
- created_at
```

원칙:

```text
초기 고객 연동은 API보다 엑셀 import/export가 먼저 올 수 있다.
엑셀도 정식 연동 경로로 취급하고 로그와 오류를 남긴다.
```

---

## 6. AI-ready 선행 구조

AI 기능은 나중에 붙여도 된다.  
하지만 AI가 사용할 데이터와 증거는 지금부터 쌓아야 한다.

### 6.1 AI 요청/응답 로그

```text
ai_requests
- id
- agency_id
- client_id
- warehouse_id
- return_id
- request_type
- model_provider
- model_name
- prompt_version
- input_hash
- created_by
- created_at
```

```text
ai_outputs
- id
- ai_request_id
- raw_output
- parsed_output
- confidence
- reason
- created_at
```

```text
ai_decisions
- id
- return_id
- ai_output_id
- suggested_result
- human_final_result
- accepted_by_user
- corrected_by_user
- correction_reason
- finalized_at
```

```text
ai_feedback
- id
- return_id
- ai_decision_id
- feedback_type
- feedback_note
- created_by
- created_at
```

---

### 6.2 AI 사용 원칙

AI는 초기에는 추천만 수행한다.

허용:

```text
반품 판정 추천
상품 매칭 후보 추천
운송장/상품 바코드 구분 보조
사진/영상 이상탐지
고객사 규정 요약
정산 이상 후보 탐지
운영 리포트 생성
```

금지:

```text
반품 완료 자동 확정
재고 자동 반영
정산 자동 확정
권한 변경
고객 소유권 변경
데이터 삭제
위임 처리 자동 승인
사람 확인 없는 고위험 결정
```

원칙:

```text
AI 추천값과 사람 최종확정값은 반드시 분리한다.
AI가 틀렸을 때 사람이 수정한 이유를 남긴다.
AI 결과는 감사로그와 비용 로그를 가진다.
```

---

### 6.3 RAG / pgvector 선행 원칙

향후 고객사별 규정, 상품별 판정 기준, 과거 반품 사례, 작업 매뉴얼을 RAG로 사용할 수 있다.

필수 원칙:

```text
embedding 데이터에도 tenant scope를 가진다.
검색 시 agency_id/client_id/warehouse_id scope를 강제한다.
검색 근거 문서와 버전을 남긴다.
고객사 A의 문서가 고객사 B의 답변에 사용되면 안 된다.
```

---

## 7. SaaS 운영 선행 구조

SmartReturn은 유료 SaaS로 운영될 수 있어야 한다.

필수 운영 구조:

```text
local
dev
test
staging
production
```

필수 운영 기능:

```text
자동 백업
복구 리허설
배포 절차
rollback 절차
장애 알림
slow query 관측
API 응답시간 관측
파일 업로드 실패 관측
로그인 실패 관측
정산/마감 실패 관측
```

현장 도입 전 최소 조건:

```text
대리점/고객사/창고/사용자 기본 데이터
바코드 스캐너 테스트
반품처리 화면
권한 차단
감사로그
백업
장애 시 대체 절차
파일럿 피드백 양식
```

---

## 8. 보안·개인정보 선행 원칙

SmartReturn은 운송장, 고객명, 연락처, 주소, 상품 사진, 반품 이력 등을 다룰 수 있다.

필수 문서:

```text
개인정보처리방침
개인정보 처리위탁 특약
서비스 이용약관
서비스 이용계약서
데이터 보관/파기 정책
장애/보안 사고 고지 정책
AI 사용 고지 문구
```

필수 기술 원칙:

```text
secret/token/password 실값 저장 금지
로그에 개인정보 과다 기록 금지
권한 변경 감사로그
관리자 조작 감사로그
파일/사진/영상 보관기간
삭제/파기 절차
```

---

## 9. 현장 도입 테스트 원칙

현장 테스트는 기능을 배우는 과정으로 사용한다.  
다만 아래 핵심 구조는 현장에서 즉흥 변경하지 않는다.

현장에서 바꿔도 되는 것:

```text
버튼 위치
화면 문구
필터
컬럼
단축키
알림 문구
현장 메모
작업 순서 편의
```

현장에서 즉흥 변경하면 안 되는 것:

```text
DB 기본 구조
tenant scope
권한 구조
반품 상태값
재고 반영 원칙
정산 기준
외부 ID 관리 방식
감사로그 구조
migration 방식
```

현장도입은 다음 단계로 진행한다.

```text
1. 실데이터 모의운영
2. 제한 실운영
3. 병행 운영
4. 유료 전환 판단
```

---

## 10. 후속 SPEC 후보

본 결정문 이후 다음 SPEC으로 분리한다.

### 10.1 Integration-ready Data Model SPEC

목적:

```text
OMS/WMS/ERP 확장 대비 공통 데이터 모델 정의
```

포함:

```text
external_references
status_mappings
product/product_barcode
order/return/receipt 분리
inventory_events
settlement_documents/lines
```

---

### 10.2 External Reference & Idempotency SPEC

목적:

```text
외부 ID 매핑과 중복 이벤트 방지 기준 정의
```

포함:

```text
external_references
idempotency_key
payload_hash
source_system
external_event_id
```

---

### 10.3 Order / Return / Receipt Separation SPEC

목적:

```text
주문, 반품요청, 실제입고, 상품단위 판정 분리
```

포함:

```text
sales_orders
sales_order_lines
return_authorizations
return_receipts
return_receipt_links
return_items
```

---

### 10.4 Inventory Event Ledger SPEC

목적:

```text
재고 원장 기반 구조 확정
```

포함:

```text
inventory_events
current_inventory
stock_status
idempotency_key
source_entity_type
source_entity_id
```

---

### 10.5 Settlement Line Ledger SPEC

목적:

```text
정산 라인 근거 구조 확정
```

포함:

```text
settlement_documents
settlement_lines
service_codes
rate_cards
erp_exports
```

---

### 10.6 Integration Inbox / Outbox SPEC

목적:

```text
외부 연동 이벤트 수신/발신 구조 확정
```

포함:

```text
integration_inbox
integration_outbox
retry
error log
payload version
```

---

### 10.7 Import / Export Contract SPEC

목적:

```text
엑셀·CSV·API import/export 구조 확정
```

포함:

```text
import_jobs
import_job_errors
export_jobs
file_id
row-level error
```

---

### 10.8 AI Data & Audit Baseline SPEC

목적:

```text
AI 요청/응답/추천/사람수정/최종확정 로그 구조 확정
```

포함:

```text
ai_requests
ai_outputs
ai_decisions
ai_feedback
prompt_version
model_version
tenant scope
```

---

### 10.9 SaaS Pilot Readiness SPEC

목적:

```text
현장도입 전 최소 준비 조건 확정
```

포함:

```text
계정
권한
기준 데이터
바코드 스캔
백업
장애 대응
피드백 양식
```

---

## 11. 구현 금지 사항

본 결정문 작성 또는 반영 단계에서는 다음을 금지한다.

```text
코드 변경
DB 접속
migration 생성
DDL 실행
테이블 생성
권한 로직 변경
반품/재고/정산 상태 변경
운영 데이터 변경
secret/token/password 실값 기록
git add .
무승인 push
```

본 문서는 상위 정책 결정문이며, 실제 구현은 후속 SPEC과 독립검수 후에만 진행한다.

---

## 12. 적용 순서

권장 순서:

```text
1. 본 결정문 작성
2. ChatGPT 지휘소가 후속 SPEC 분리 계획 수립
3. Integration-ready Data Model SPEC 작성
4. 독립검수
5. External Reference & Idempotency SPEC 작성
6. Order/Return/Receipt Separation SPEC 작성
7. Inventory Event Ledger SPEC 작성
8. Settlement Line Ledger SPEC 작성
9. Integration Inbox/Outbox SPEC 작성
10. Import/Export Contract SPEC 작성
11. AI Data & Audit Baseline SPEC 작성
12. SaaS Pilot Readiness SPEC 작성
13. 구현 착수 판단
```

현재 PostgreSQL/Alembic/JSONB 전환 작업이 진행 중인 경우, 실제 DB 구현은 해당 기준이 안정화된 뒤 진행한다.

---

## 13. 검수 기준

본 결정문 검수자는 아래를 확인한다.

```text
1. SmartReturn이 OMS/WMS/ERP 전체 대체가 아니라 반품 중심 허브로 정의되었는가
2. 외부 ID를 본 테이블에 박지 않는 원칙이 있는가
3. 주문/반품요청/실제입고/상품판정이 분리되었는가
4. 재고가 이벤트 원장 방식으로 정의되었는가
5. 정산이 라인 원장 방식으로 정의되었는가
6. 모든 연동이 idempotency를 갖도록 요구하는가
7. 모든 데이터에 tenant scope가 요구되는가
8. 대리점 보호형 처리망 원칙과 충돌하지 않는가
9. AI 추천과 사람 확정이 분리되었는가
10. 현장 테스트에서 바꿔도 되는 것과 안 되는 것이 분리되었는가
11. 후속 SPEC 후보가 구현 가능한 단위로 분리되었는가
12. 본 문서 자체가 코드/DB 변경을 지시하지 않는가
```

---

## 14. 최종 결정

SmartReturn은 앞으로 다음 방향으로 확장한다.

```text
SmartReturn은 반품 중심 SaaS 허브다.
OMS/WMS/ERP 전체를 지금 대체하지 않는다.
하지만 OMS/WMS/ERP와 연결 가능한 데이터·이벤트·정산·재고·AI-ready 뼈대는 지금부터 선행한다.
```

핵심 선행 구조는 다음과 같다.

```text
external_references
status_mappings
integration_inbox
integration_outbox
product_barcodes
warehouse_locations
sales_orders
return_authorizations
return_receipts
inventory_events
settlement_documents
settlement_lines
import_jobs
ai_requests
ai_outputs
ai_decisions
audit_logs
```

본 결정문은 후속 SPEC의 상위 기준으로 사용한다.
