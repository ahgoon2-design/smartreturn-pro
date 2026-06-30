---
name: naver-cloud-saas-architecture
description: >-
  DB/파일/사진/로그/배포/채널 자동수집/백업/보안/대량 이력 테이블 작업 시 적용하는
  네이버클라우드 SaaS 아키텍처 스킬. 단일 DB 멀티테넌트, Object Storage 파일 저장,
  API/Worker/Scheduler 분리, 로그·백업·확장 기준을 정리하므로 인프라·저장소·대량 이력
  설계 작업 시 반드시 이 스킬을 적용한다.
---

# 네이버클라우드 SaaS 인프라/DB 운영 스킬

## 목적

SmartReturn Pro는 네이버클라우드에서 서비스하는 OMS + WMS + Returns 통합 운영 플랫폼이다.

이 문서는 SmartReturn Pro를 네이버클라우드 기반 SaaS로 운영하기 위한 인프라, DB, 파일 저장, 로그, 백업, 보안, 확장 기준을 정의한다. 앞으로 DB 테이블, 파일/사진 저장, 채널 자동수집, 배포, 로그, 백업, 대량 이력 테이블을 설계할 때 이 문서를 우선 기준으로 삼는다.

## 기본 운영 방향

- SmartReturn Pro의 초기 SaaS 운영은 단일 DB 멀티테넌트 구조를 기본으로 한다.
- 고객사별 DB를 처음부터 분리하지 않는다.
- 하나의 운영 DB 안에서 `agency_id`, `client_id`, `client_unit_id` 3단계 scope로 데이터를 분리한다.
- 고객사 사용자는 자기 `client_id` 범위만 조회하고 처리할 수 있어야 한다.
- 내부 운영자는 권한에 따라 전체 또는 선택 고객사 데이터를 볼 수 있다.
- 대리점 SaaS 확장을 위해 핵심 운영 테이블과 대량 이력 테이블에는 `agency_id` 직접 저장을 기본으로 검토한다.
- DB와 backend는 외부 인터넷에 직접 노출하지 않는다.
- 외부에는 Load Balancer와 웹 도메인만 노출한다.
- 사진, 첨부파일, 라벨, 업로드 원본은 DB에 직접 저장하지 않고 Object Storage에 저장한다.
- API, Worker, Scheduler 역할을 분리할 수 있게 설계한다.
- 대량 이력 테이블은 인덱스, 보관기간, 파티셔닝, 아카이브를 처음부터 고려한다.

## 네이버클라우드 권장 구성

초기 구성은 아래 서비스를 기준으로 잡는다. 실제 사양, 대수, 비용은 운영 부하와 계약 조건을 확인한 뒤 결정한다.

- VPC
- Load Balancer
- Server 1~2대
- Cloud DB for PostgreSQL
- Object Storage
- Cloud Log Analytics
- Cloud Insight
- Cloud Activity Tracer
- Sub Account

권장 요청 흐름:

```text
사용자
-> Load Balancer
-> Frontend
-> Backend API
-> Cloud DB for PostgreSQL
-> Object Storage
```

VPC 내부 구조:

| 영역 | 구성 요소 | 운영 기준 |
| --- | --- | --- |
| Public Subnet | Load Balancer | 외부 도메인과 HTTPS 진입점만 둔다. |
| Private Subnet | Backend API Server, Worker Server, Scheduler | 업무 API와 배치 작업은 외부에 직접 노출하지 않는다. |
| DB Subnet | Cloud DB for PostgreSQL | 운영 DB는 private network 기준으로 접근한다. |
| Object Storage | return photos, import originals, label previews, exports, archive/backups | 대용량 파일과 장기 보관 파일을 DB 밖에 둔다. |

## DB 기본 정책

- 운영 DB는 Cloud DB for PostgreSQL 기준으로 설계한다.
- 초기에는 하나의 PostgreSQL DB를 사용한다.
- 모든 고객사 운영 데이터는 `client_id`를 가진다.
- 대리점 권한, 통계, 정산, 대량 이력 조회가 필요한 핵심 운영 데이터는 `agency_id`도 직접 가진다.
- 팀/운영단위가 필요한 데이터는 `client_unit_id`를 가진다.
- 대리점 SaaS 확장을 고려하는 핵심 운영 데이터는 `agency_id`를 직접 저장한다.
- 고객사별 DB 분리는 초기에는 금지한다.
- 고객사별 DB 분리는 대형 고객 전용 요구, 법적/계약상 물리분리 요구, 특정 고객 트래픽 과다, 수억 row 이상 확장 시 검토한다.
- 운영 테이블과 대량 이력 테이블을 구분해 관리한다.

기본 멀티테넌트 구조 예시:

- `clients`
- `client_units`
- `products`
- `warehouses`
- `return_intake_rows`
- `inventory_events`
- `current_inventory`
- `channel_accounts`
- `channel_raw_events`
- `channel_return_candidates`
- `product_channel_mappings`

## client scope 보안 정책

- 프론트에서 숨기는 것만으로 권한을 처리하지 않는다.
- 모든 고객사 사용자 API는 backend에서 client scope를 재검증한다.
- 고객사 사용자는 `WHERE client_id = current_user.client_id` 범위로 제한한다.
- `client_unit` 권한이 필요한 경우 `client_unit_id`도 함께 검증한다.
- 내부 운영자도 role/permission에 따라 접근 범위를 제한한다.
- 대리점 사용자가 생기면 `agency_id` 범위까지 검증한다.
- `raw_json`, 사진, 첨부, 로그, export 파일도 client scope를 검증한다.
- super admin이라도 secret, token, password 원문은 응답하지 않는다.

## 필수 인덱스 정책

모든 대량 테이블은 고객사 기준 필터와 시간/상태 조회를 기본으로 한다.

대량 테이블 기본 인덱스 후보:

- `agency_id`
- `agency_id + client_id`
- `client_id`
- `client_id + created_at`
- `client_id + status`
- `client_id + client_unit_id`
- `client_id + source_type`

반품 인덱스 후보:

- `return_intake_rows(agency_id, client_id, return_tracking_no)`
- `return_intake_rows(client_id, return_tracking_no)`
- `return_intake_rows(client_id, status, created_at)`
- `return_intake_rows(client_id, client_unit_id, status)`
- `return_intake_rows(client_id, product_id)`

재고 인덱스 후보:

- `current_inventory(agency_id, client_id, warehouse_id, product_id)`
- `current_inventory(client_id, warehouse_id, product_id)`
- `inventory_events(agency_id, client_id, created_at)`
- `inventory_events(client_id, product_id, created_at)`
- `inventory_events(client_id, warehouse_id, created_at)`

채널 자동수집 인덱스 후보:

- `channel_raw_events(channel_account_id, raw_hash)`
- `channel_raw_events(agency_id, collected_at)`
- `channel_raw_events(channel_account_id, external_product_order_id, external_claim_id)`
- `channel_return_candidates(agency_id, client_id, match_status, created_at)`
- `channel_return_candidates(client_id, match_status, created_at)`
- `channel_return_candidates(client_id, return_tracking_no)`
- `product_channel_mappings(client_id, channel_type, external_seller_product_code)`

Import 인덱스 후보:

- `import_jobs(agency_id, requested_client_id, source_type, created_at)`
- `import_jobs(client_id, source_type, created_at)`
- `import_job_rows(agency_id, client_id, created_at)`
- `import_job_rows(import_job_id, row_no)`
- `import_job_rows(client_id, created_at)`

주의사항:

- 고객사 필터 없이 대량 테이블 전체 조회를 하지 않는다.
- 페이지네이션 없는 대량 목록 API를 만들지 않는다.
- 엑셀 다운로드는 건수 제한 또는 비동기 export로 처리한다.
- 검색 조건 없는 대량 조회를 만들지 않는다.

## 대량 이력 테이블 정책

아래 테이블은 대량 이력 테이블로 본다.

- `channel_raw_events`
- `channel_sync_jobs`
- `channel_return_candidates`
- `import_job_rows`
- `inventory_events`
- `scan_events`
- `audit_logs`
- `return_history`
- `label_print_logs`
- `worker_job_logs`

정책:

- `created_at` 기준 인덱스를 둔다.
- `client_id` 기준 인덱스를 둔다.
- 월별/분기별 파티셔닝 가능성을 고려한다.
- 최근 데이터와 장기 보관 데이터를 분리할 수 있게 설계한다.
- `raw_json`은 무기한 운영 조회 대상으로 두지 않는다.
- 오래된 `raw_json`, scan event, import row는 아카이브 정책을 둔다.
- 삭제가 어려운 회계, 재고, 감사 이력은 삭제 대신 아카이브/파티셔닝을 고려한다.

## Object Storage 파일 저장 정책

DB에 직접 저장하지 말아야 할 것:

- 반품 사진
- 검수 사진
- 증빙 사진
- 라벨 미리보기 이미지
- 업로드 원본 파일
- export 엑셀 파일
- 대용량 첨부파일
- 장기 보관 archive 파일

Object Storage 권장 bucket 또는 prefix:

- `smartreturn-prod-return-photos`
- `smartreturn-prod-import-originals`
- `smartreturn-prod-labels`
- `smartreturn-prod-exports`
- `smartreturn-prod-archive`

DB에는 아래 메타데이터만 저장한다.

- `id`
- `client_id`
- `client_unit_id` nullable
- related entity id
- `object_key`
- `thumbnail_object_key` nullable
- `file_size`
- `content_type`
- `checksum` 또는 `hash`
- `created_at`
- `created_by`

정책:

- `object_key`에도 `client_id` 기준 경로를 포함한다.
- 파일 접근 API는 backend에서 client scope를 검증한 뒤 signed URL 또는 proxy 방식으로 제공한다.
- 개인정보가 포함된 사진/파일은 공개 URL로 두지 않는다.
- 원본 업로드 파일은 보관기간 정책을 둔다.
- 삭제/보관 정책은 고객 계약 기준과 운영 정책을 따른다.

## API / Worker / Scheduler 분리 정책

역할:

| 역할 | 담당 업무 |
| --- | --- |
| API Server | 사용자 화면 요청, 반품처리, 재고/마감, 채널 설정 관리 |
| Worker | 네이버/쿠팡/카페24/택배사 채널 수집, `channel_raw_events` 저장, candidate 변환, `READY` 후보 생성, export 생성, 실패 재시도 |
| Scheduler | 주기적 수집 트리거, 보관기간/아카이브 작업, 정기 점검 작업, 알림 작업 |

정책:

- 긴 작업은 API 요청 안에서 오래 붙잡지 않는다.
- 대량 import/export는 worker job으로 분리한다.
- 채널 자동수집은 화면 요청과 분리된 scheduler/worker에서 수행한다.
- Worker job은 `job_id`, `client_id`, `status`, `started_at`, `finished_at`, `error_code`를 기록한다.
- 실패한 worker job은 재시도 가능해야 한다.
- 중복 실행 방지 lock 또는 idempotency key를 고려한다.

## 로그/모니터링 정책

네이버클라우드 기준:

- Cloud Log Analytics로 API, worker, error log를 수집한다.
- Cloud Insight로 서버, DB, 애플리케이션 지표를 모니터링한다.
- Cloud Activity Tracer로 콘솔/API 계정 활동을 추적한다.
- Sub Account로 운영자와 개발자 권한을 분리한다.

로그에 남겨도 되는 것:

- `client_id`
- `client_unit_id`
- `account_id`
- `job_id`
- `error_code`
- `tracking_hash`
- `raw_hash`
- `candidate_id`
- `request_id`

로그에 남기면 안 되는 것:

- `password`
- `password_hash`
- `token`
- API secret
- 전화번호 원문
- 주소 원문
- 운송장번호 원문 전체
- 개인정보가 포함된 `raw_json` 전체

권장 로그 예:

```text
client_id=3 channel_account_id=12 job_id=99 event=CHANNEL_SYNC_FAILED error_code=NAVER_AUTH_EXPIRED tracking_hash=...
```

## 백업/복구 정책

DB:

- Cloud DB for PostgreSQL 자동 백업을 사용한다.
- 운영 초기 자동 백업 보관은 7~14일 이상으로 잡는다.
- 정식 운영 후 30일 이상 보관을 검토한다.
- 중요 배포 전 수동 백업 또는 스냅샷을 생성한다.
- 월 1회 복구 테스트를 권장한다.

Object Storage:

- 사진, 첨부, 업로드 원본, exports, archives에 수명주기 정책을 적용한다.
- 최근 데이터와 장기 보관 데이터를 분리한다.
- 삭제 정책은 고객 계약과 개인정보 보관정책에 맞춘다.

복구:

- DB만 복구해서 끝내지 않는다.
- DB row의 `object_key`와 Object Storage 파일 연결이 유지되는지 확인한다.
- 샘플 고객사 기준 복구 테스트를 한다.
- 복구 절차를 문서화한다.

## 확장 단계 정책

1단계: 파일럿/초기 운영

- 단일 Cloud DB for PostgreSQL
- Server 1~2대
- Load Balancer
- Object Storage
- Cloud Log Analytics
- Cloud Insight

2단계: 고객 수십 곳

- Backend Server 2~3대
- Worker Server 분리
- DB 사양 증설
- Redis/Cache 검토
- Read replica 검토
- 대량 export worker 분리

3단계: 고객 수백 곳 / 대리점 확산

- NKS 또는 Auto Scaling 구조 검토
- API/Worker/Scheduler 컨테이너 분리
- PostgreSQL 파티셔닝
- 대량 이력 아카이브
- `agency_id` 기반 대리점 scope, 정산, 권한 정책 고도화

4단계: 대형 고객/전국 SaaS

- 대형 고객 전용 DB 분리 가능
- agency/region 단위 샤딩 검토
- 운영 DB와 리포트/분석 DB 분리
- 고객별 백업/복구 정책 고도화

## 고객사별 DB 분리 판단 기준

초기에는 고객사별 DB 분리를 기본값으로 두지 않는다. 아래 조건이면 검토한다.

- 특정 대형 고객이 전체 트래픽의 큰 비중을 차지함
- 고객이 계약상 전용 DB를 요구함
- 법적/보안상 물리 분리 필요
- 테이블이 수억 row 이상으로 성장
- 고객별 백업/복구를 독립적으로 해야 함
- 대리점/리전별 완전 독립 운영이 필요함

분리 순서:

1. 단일 DB + `client_id`
2. 대량 테이블 파티셔닝
3. 대형 고객만 별도 DB
4. agency/region 단위 샤딩
5. 분석 DB 별도 분리

## SmartReturn Pro 개발 시 적용 규칙

- 신규 운영 테이블에는 `client_id` 포함을 우선 검토한다.
- 팀/운영단위가 필요한 업무에는 `client_unit_id`를 포함한다.
- 대리점 확장 가능성이 있는 업무는 `agency_id` 추가 가능성을 막지 않는다.
- 파일, 사진, 첨부는 DB blob으로 저장하지 않는다.
- 대량 row 목록은 페이지네이션을 강제한다.
- export는 대량이면 worker job으로 분리한다.
- `channel_raw_events`, `inventory_events`, `import_job_rows`, `scan_events`는 대량 이력 테이블로 보고 인덱스, 보관, 파티셔닝을 고려한다.
- 모든 고객사 API는 backend에서 client scope를 검증한다.
- `raw_json`과 로그에는 개인정보, secret, token, password 원문을 남기지 않는다.
- 네이버클라우드 배포 기준으로 API/Worker/Scheduler 분리를 고려한다.
- 단기 개발속도 때문에 운영 보안, 백업, 로그 원칙을 깨지 않는다.
