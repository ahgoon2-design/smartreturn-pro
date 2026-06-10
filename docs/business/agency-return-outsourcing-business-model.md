# CJ대리점 청구형 반품대행 사업모델

이 문서는 SmartReturn Pro의 운영/시스템 설계 기준이다. 법률 자문이나 계약서가 아니며, 실제 계약서, 요율표, 개인정보 처리, 택배사 약관, 책임 범위는 별도 계약/법무 검토가 필요하다.

## 기본 모델

SmartReturn Pro는 CJ대한통운 대리점 기반 이커머스 풀필먼트/반품 SaaS를 전제로 한다.

```text
platform_owner
→ agency_id
→ client_id
→ client_unit_id
→ warehouse_id
```

- `platform_owner`: SmartReturn 본사/플랫폼 운영자.
- `agency_id`: CJ대한통운 대리점 또는 본사 직영 운영 단위.
- `client_id`: 대리점이 관리하는 업체/셀러.
- `client_unit_id`: 업체 내부 팀, 브랜드, 운영단위.
- `warehouse_id`: 실제 처리, 보관, 판정별 재고 위치.

## 청구형 반품대행 구조

CJ대리점이 자기 관리/계약 업체의 반품 물량을 우리 센터에 의뢰한다. 우리 센터는 업체 반품을 받아 입고, 검수, 판정, 사진/영상 선택 기록, 일마감, 재고, 반출, 폐기, 부품적출을 대행 처리한다.

비용은 실제 업체가 아니라 CJ대리점에 청구할 수 있다. 계약 정책에 따라 업체에게 직접 청구하거나 대리점과 업체 간 정산으로 넘길 수도 있지만, 시스템 기본 모델은 `agency_id`를 청구/조회/정산 상위 단위로 본다.

| 구분 | 의미 |
| --- | --- |
| 서비스 계약 고객 | CJ대리점 |
| 실제 화주/업체 | `client` |
| 작업 수행자 | 우리 센터 |
| 비용 부담자 | CJ대리점 또는 계약 정책에 따른 청구 대상 |
| 데이터 소유/조회 기준 | `agency_id → client_id → client_unit_id` |

## 책임 범위

### CJ대리점

- 업체 영업/계약.
- 업체 반품 물량 유치.
- 비용 지급 또는 업체 정산 중계.
- 업체와의 기본 약정 관리.
- 반품 주소 전환 안내 지원.

### 우리 센터

- 입고 스캔.
- 박스 해체.
- 상품/구성품/사은품 확인.
- 사진/영상 선택 기록.
- 고객사별 판정 기준에 따른 판정 처리.
- 판정별 창고 확정.
- 일마감/재고반영.
- 제조사반출/폐기/부품적출 처리 지원.
- 대리점/업체 리포트 제공.

### 업체/client

- 상품마스터 제공.
- 반품 세부정보 제공 또는 자동수집 연동 허용.
- 고객사별 판정 기준 제공.
- 판정표/매뉴얼 협의.
- 세트/구성품/사은품 정보 제공.
- 제조사반출/폐기/보류 회신.

## 정산 기준 후보

정산은 운영 이벤트와 마감 결과를 기준으로 산출한다. 초기 구현은 상세 요율 계산보다 정산 기초자료를 정확히 남기는 데 집중한다.

```text
agency_id
client_id
client_unit_id
warehouse_id
billing_target_type
billing_target_id
work_type
quantity
unit_price
amount
settlement_month
```

`billing_target_type`은 대리점 청구, 업체 청구, 내부 비용, 예외 청구 같은 확장을 고려한다. 다만 요청 body의 `agency_id`를 그대로 신뢰하지 않고 `client_id → clients.agency_id` 기준으로 확정해야 한다.

## 시스템 설계 원칙

- 핵심 운영 테이블은 대리점별 조회, 장애추적, 정산, 감사에 필요하므로 `agency_id`를 직접 저장한다.
- `client_id`가 있는 row는 `clients.agency_id` 기준으로 `agency_id`를 확정한다.
- `client_unit_id`와 `warehouse_id`는 해당 `client_id`와 scope가 맞아야 한다.
- `AGENCY_ADMIN`은 자기 `agency_id` 범위만 조회/관리한다.
- 대리점 청구형 모델이어도 실제 업무 확정은 고객사/운영단위/창고/상품/판정 기준으로 남긴다.

## Codex 구현 전 체크

- 이 기능이 대리점 청구형 모델에서 `agency_id` 조회/정산 기준을 유지하는가?
- 실제 작업 row가 `client_id`, `client_unit_id`, `warehouse_id`를 잃지 않는가?
- 고객사별 비용과 대리점 청구 비용을 혼동하지 않았는가?
- 계약/요율/개인정보/택배사 약관을 시스템 문서만으로 확정하지 않았는가?
