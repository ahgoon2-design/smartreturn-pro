# 채널 API 반품 자동수집 스킬

## 목적

SmartReturn Pro는 반품 전문성이 강하지만 “반품만 하는 프로그램”이 아니라 OMS + WMS + Returns 통합 운영 플랫폼이다.

네이버, 쿠팡, 카페24, 이지어드민, 택배사 API 등 외부 채널에서 들어오는 반품, 교환, 취소, 수거 정보를 자동수집하여 SmartReturn Pro의 공용 반품접수 흐름으로 연결해야 한다. 채널 API 자동수집은 엑셀 업로드를 대체하거나 보완하는 입력 채널이며, 최종적으로는 반품예정자료 생성, 현장 운송장 스캔, 판정, 일마감, 재고반영, 외부반출, 채널 역전송까지 이어져야 한다.

## 핵심 원칙

- 채널 API 자동수집은 화면별 개별 저장 로직으로 만들지 않는다.
- 네이버 API, 쿠팡 API, 카페24 API, 이지어드민 API, 택배사 API 등 입력 경로가 달라도 최종 저장 전에는 SmartReturn Pro의 공용 반품접수 canonical 구조로 정규화한다.
- API 수집자료도 엑셀, 붙여넣기, 구글시트와 동일하게 원본 보존, 정규화, 검증, 중복방지, 미리보기/상태관리, 예외처리를 거쳐야 한다.
- 자동수집은 자동저장이 아니라 안전한 자동등록 흐름이다.
- 사용자가 손대는 부분은 정상건 전체 검수가 아니라 예외처리 중심이어야 한다.
- 정상건은 자동으로 `READY_FOR_INTAKE` 상태까지 진행하고, 불확실한 건만 `TEAM_ASSIGN_PENDING`, `PRODUCT_MATCH_PENDING`, `RETURN_TRACKING_PENDING`, `NEEDS_REVIEW` 등으로 분리한다.
- 알 수 없는 반품을 무리하게 등록하지 않는다.
- 운송장 스캔 기준은 `return_tracking_no` 우선이며, `original_tracking_no`는 보조 조회 후보로만 둔다.
- 판정 저장 즉시 재고반영하지 않는다. 일마감/수량체크 확정 시 재고반영한다.
- 채널로 반품 승인, 보류, 거부 등을 역전송하는 기능은 수집, 후보 생성, 관리자 확인 전송, 안전조건 자동전송 순서로 단계화한다.

## 네이버 반품 자동수집 기준

네이버 스마트스토어/커머스API 연동은 채널 API 자동수집의 기준 예시로 삼는다.

권장 흐름:

1. 고객사별 네이버 계정을 `channel_accounts`에 연동한다.
2. API 인증 토큰 발급/갱신 구조를 둔다.
3. 변경 상품 주문, 클레임, 배송상태를 증분 수집한다.
4. `moreFrom`, `moreSequence` 또는 채널별 cursor 기반 이어조회를 사용한다.
5. 외부 응답 원본을 `channel_raw_events`에 저장한다.
6. 반품, 교환, 취소, 배송상태 변경 이벤트를 분류한다.
7. `productOrderId`, `orderId`, `claimId`, `return_tracking_no`, `original_tracking_no`, `product_name`, `option_name`, `qty`, `claim_reason`, `claim_status` 등을 canonical field로 변환한다.
8. `productOrderId`, `claimId`, `return_tracking_no` 기준으로 중복을 방지한다.
9. 고객사, `client_unit`, 상품, 송장을 자동매칭한다.
10. 자동매칭 완료 시 `READY_FOR_INTAKE`로 둔다.
11. 팀 미확정 시 `TEAM_ASSIGN_PENDING`으로 둔다.
12. 상품 미확정 시 `PRODUCT_MATCH_PENDING`으로 둔다.
13. 반품송장이 없으면 `RETURN_TRACKING_PENDING`으로 둔다.
14. 충돌 또는 불확실한 건은 `NEEDS_REVIEW`로 둔다.
15. 센터 현장에서는 운송장 스캔으로 자동조회 후 상품 스캔과 판정만 하도록 설계한다.

## 권장 DB 구조

이미 유사 테이블이 있으면 새로 만들기보다 기존 구조 재사용을 우선한다. 아래는 신규 설계 시 기준이 되는 개념이다.

### `channel_accounts`

고객사별 외부 채널 계정 연동 정보다.

주요 필드 후보:

- `client_id`
- `client_unit_id`
- `channel_type`
- `store_name`
- `credential` 또는 암호화된 secret 참조
- `token_status`
- `last_sync_at`
- `is_active`

### `channel_sync_jobs`

수집 배치/스케줄 실행 이력이다. 시작/종료 시각, 성공/실패, 수집 건수, 오류 건수, cursor 정보를 기록한다.

### `channel_raw_events`

외부 채널 원본 이벤트 보존 테이블이다.

주요 필드 후보:

- `raw_json`
- `raw_hash`
- `external_order_id`
- `external_product_order_id`
- `external_claim_id`
- `last_changed_at`

개인정보, 주소, 전화번호, 운송장번호 원문을 로그에 출력하지 않는다. 원본 접근권한은 제한한다.

### `external_order_links`

외부 주문, 상품주문, 클레임과 SmartReturn 내부 반품예정/처리 row를 연결한다.

### `return_channel_claims`

채널별 클레임 상태를 관리한다. 채널 상태와 내부 처리 상태를 분리해 추적한다.

### `product_channel_mappings`

외부 채널 상품명, 옵션명, 판매자상품코드와 SmartReturn 상품마스터 매칭을 기억한다.

### `channel_action_queue`

SmartReturn 판정 결과를 채널 API로 승인, 보류, 거부, 메모 전송하기 위한 대기열이다.

### `channel_sync_errors`

API 오류, 인증 오류, 매칭 오류, 중복/충돌 오류를 관리한다.

## 상태값 정책

상태값은 실제 기존 enum/상태 체계와 충돌하지 않게 맞추되, 아래 의미는 유지한다.

- `NAVER_COLLECTED` 또는 `CHANNEL_COLLECTED`: 외부 채널에서 원본 수집됨.
- `MAPPED`: 고객사, 상품, 팀 등 주요 매칭 완료.
- `TEAM_ASSIGN_PENDING`: 고객사는 알지만 팀/운영단위 미확정.
- `PRODUCT_MATCH_PENDING`: 상품마스터 매칭 필요.
- `RETURN_TRACKING_PENDING`: 반품송장 없음, 원송장만 있음.
- `READY_FOR_INTAKE`: 센터 운송장 스캔 처리 가능.
- `INTAKE_IN_PROGRESS`: 작업자가 처리 중.
- `JUDGED`: 판정 완료.
- `CLOSED`: 일마감 완료.
- `SYNC_BACK_PENDING`: 채널 승인/보류/메모 전송 대기.
- `SYNC_BACK_DONE`: 채널 처리 반영 완료.
- `SYNC_ERROR`: 채널 전송 실패.

## 송장 정책

- `return_tracking_no`는 반품 현장 스캔 기준이다.
- `original_tracking_no`는 원출고 송장으로 보조 조회 후보일 뿐이다.
- `return_tracking_no`가 있으면 `tracking_no_for_scan`은 `return_tracking_no` 기준으로 잡는다.
- `return_tracking_no`가 없고 `original_tracking_no`만 있으면 자동 입고확정하지 말고 `RETURN_TRACKING_PENDING` 또는 보조조회 후보로 둔다.
- `original_tracking_no`를 `return_tracking_no`처럼 자동확정하면 안 된다.
- 같은 `return_tracking_no`가 다른 `productOrderId` 또는 `claimId`와 충돌하면 자동 병합하지 않고 `NEEDS_REVIEW` 또는 충돌 상태로 보낸다.

## 상품 자동매칭 정책

상품 매칭 우선순위:

1. 외부 채널 `sellerProductCode`, `SKU`, 판매자상품코드 직접 일치
2. SmartReturn `product_code` 직접 일치
3. `barcode` 또는 `additional_barcode` 일치
4. 상품명 + 옵션명 정규화 매칭
5. 과거 `product_channel_mappings` 매칭 기억
6. 미확정 시 `PRODUCT_MATCH_PENDING`

주의사항:

- 상품명 유사도만으로 위험하게 자동확정하지 않는다.
- 동일 고객사, 동일 채널, 동일 상품명/옵션명, 충분한 확정 이력, 충돌 이력 없음 조건을 만족할 때만 자동추천 강도를 높인다.
- 작업자가 수정한 상품 매칭은 다음 수집에 반영하되, 충돌/거부 이력이 있으면 자동확정하지 않는다.

## 팀/client_unit 자동배정 정책

- SmartReturn Pro는 `client_id`만으로 반품 접수, 처리, 재고반영을 끝내면 안 된다.
- 채널 API 수집자료도 `client_unit_id`를 가능하면 접수 시점부터 배정해야 한다.
- 네이버 스토어, 채널 계정, 상품 카테고리, 출고창고, 고객사 설정을 기준으로 `client_unit` 자동배정 규칙을 둘 수 있다.
- 자동배정이 불확실하면 `TEAM_ASSIGN_PENDING`으로 둔다.
- 미배정 상태는 예외처리 화면에서 작업자가 처리한다.

## 중복방지/upsert 정책

강한 중복키:

- `client_id + channel_type + external_product_order_id + external_claim_id`

보조 중복키:

- `client_id + return_tracking_no + product_code`
- `client_id + original_tracking_no + external_product_order_id`
- `raw_hash`

정책:

- 이미 같은 `external_product_order_id + claim_id`가 있으면 신규 insert가 아니라 update/upsert한다.
- 같은 `return_tracking_no`가 있는데 외부 주문번호가 다르면 자동 병합하지 않는다.
- 같은 `productOrderId`인데 수량/상태가 변경되면 기존 row를 업데이트하고 이력을 기록한다.
- 이미 판정, 일마감, 재고반영 완료된 건은 외부 채널 상태 변경으로 내부 처리기록을 함부로 뒤집지 않는다.
- 외부 채널 상태는 별도로 업데이트하되, 재고/마감 확정자료는 수정 워크플로우 없이 직접 변경하지 않는다.

## 예외처리 화면 정책

사용자가 손 안 가게 하려면 정상건이 아니라 예외건만 보게 해야 한다.

필수 예외 그룹:

- 상품 매칭 필요
- 팀 배정 필요
- 반품송장 없음
- 중복/충돌
- API 인증 오류
- API 수집 오류
- 채널 역전송 실패
- 원본 데이터 확인 필요

자동수집 현황판 요약:

- 오늘 수집 건수
- 자동매칭 완료 건수
- `READY_FOR_INTAKE` 건수
- 상품확인 필요 건수
- 팀배정 필요 건수
- 송장없음 건수
- 충돌/오류 건수
- 마지막 수집 시각
- 다음 수집 예정 또는 스케줄 상태

## 채널 역전송 정책

SmartReturn 판정 결과를 네이버, 쿠팡 등 채널에 다시 보내는 기능은 단계적으로 구현한다.

1. 수집만 자동
2. 판정 결과 기준 승인/보류/거부 후보 생성
3. 관리자 확인 후 채널 API 전송
4. 안전조건을 만족하는 정상건만 자동 전송

자동 전송 허용 예시:

- 판정 `GOOD`
- 수량 일치
- 상품 일치
- 일마감 완료
- 재고반영 성공
- 보류 사유 없음
- 고객사별 자동승인 설정 ON
- 금액/기간/정책 제한 통과

자동 전송 금지 예시:

- 상품 불일치
- 수량 부족/초과
- 훼손/사용감/구성품 누락
- `HOLD` 또는 보류
- 미확인 반품
- 고객사 자동승인 OFF
- 채널 상태 충돌
- API 응답 불확실

## 보안/개인정보 정책

- API secret/token은 평문 저장하지 않고 암호화 저장 또는 안전한 secret 관리 구조를 사용한다.
- secret/token/password/password_hash 실제 값은 출력하지 않는다.
- 로그에 개인정보, 주소, 전화번호, 운송장번호 원문을 출력하지 않는다.
- `channel_raw_events`에는 업무상 필요한 원본을 저장하되 접근권한을 제한한다.
- decision, mapping, history에는 개인정보 원문 저장을 피하고 hash 또는 마스킹 summary를 사용한다.
- 고객사 사용자는 자기 `client_id`와 `client_unit` 범위의 채널 자료만 볼 수 있다.
- 내부 운영자도 role/permission에 따라 접근 범위를 제한한다.
- API 수집 실패 시 원문 전체를 화면에 노출하지 말고 안전한 오류 메시지와 추적 ID를 보여준다.

## Smart Import Mapper와의 관계

- 채널 API 자동수집은 엑셀 업로드와 같은 UI 매핑 과정이 필요 없을 수 있지만, 최종적으로는 SmartReturn 공용 canonical field 구조와 검증 규칙을 공유해야 한다.
- 엑셀, 붙여넣기, 구글시트, API 등 입력경로가 달라도 저장 전 검증, 원본 보존, 정규화, 중복방지, 상태분류 원칙은 같아야 한다.
- API 수집 데이터가 불확실하거나 채널별 필드가 달라 mapping decision이 필요한 경우 Smart Import Mapper의 profile, decision, history 구조와 연결할 수 있다.
- 화면별 개별 import/save 로직을 만들지 않는다.

## 구현 순서 권장

1차:

- 채널 계정 연동 skeleton
- 네이버 계정 등록/연결 테스트
- 토큰 발급/갱신 구조
- `channel_accounts`, `channel_sync_jobs`, `channel_raw_events` 기반 준비

2차:

- 네이버 변경 주문/반품/클레임 증분 수집
- cursor, `moreFrom`, `moreSequence` 이어조회
- raw event 저장
- 반품/교환/취소 이벤트 분류
- 중복 upsert

3차:

- SmartReturn 반품예정자료 자동 생성
- 고객사/팀/상품/송장 매칭
- `READY_FOR_INTAKE`, `TEAM_ASSIGN_PENDING`, `PRODUCT_MATCH_PENDING`, `RETURN_TRACKING_PENDING` 분리
- 반품처리 화면 운송장 스캔 연결

4차:

- 자동수집 현황판 및 예외처리 화면
- 상품매칭 필요, 팀배정 필요, 송장없음, 충돌, 오류 재처리

5차:

- 판정 결과 기준 채널 승인/보류 후보 생성
- `channel_action_queue`
- 관리자 확인 후 전송

6차:

- `GOOD` + 수량일치 + 일마감완료 + 재고반영성공 조건의 안전 자동승인
