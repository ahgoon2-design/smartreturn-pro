# GOOD 외 판정 후속 처리 / 외부반출 흐름 계획

## 1. 문서 목적

이 문서는 `GOOD` 외 반품 판정의 후속 처리 방향을 최소 기준으로 정리한다. `REFURB`, `SAMPLE`, `MANUFACTURER_RETURN`, `HOLD`, `DISPOSAL`을 같은 재고반영 흐름에 섞지 않고, 외부반출 검수 skeleton 구현 전에 필요한 범위만 고정한다.

이번 문서는 설계 기준 문서이며 backend, frontend, DB, migration, package는 변경하지 않는다.

## 2. 현재 완료된 반품처리 흐름

현재 1차 흐름은 다음 단계까지 완료되어 있다.

1. 반품 접수 batch 생성
2. 반품 접수 row 저장
3. 접수 row 검증
4. 검증된 row를 `READY_FOR_PROCESSING` 처리 대상으로 전환
5. 운송장 스캔으로 처리 대상 조회
6. 상품 바코드 확인
7. 판정 저장
8. 사진/증빙 선택 첨부
9. 추적 대상 판정의 `return_management_no`, `return_label_no` 생성
10. `GOOD` 판정 일마감 확정 후 `inventory_events` 생성 및 `current_inventory` 증가

현재 `return_intake_rows`에는 판정, 라벨, 사진 첨부 연결, GOOD 재고반영 추적 필드가 있다. 별도 외부반출 model/API/frontend 화면은 아직 없다.

## 3. 판정별 후속 처리 정책

`GOOD`

- 이미 1차 정상재고 반영 대상이다.
- 일마감 확정 후 `current_inventory`를 증가시킨다.
- 이 문서의 외부반출 대상이 아니다.

`REFURB`

- 정상재고가 아니다.
- 리퍼업체 반출, 리퍼 보관, 리퍼 검수 후보로 둔다.
- `return_management_no` 기준으로 추적한다.
- 외부반출 검수 대상 후보이다.
- 1차에서는 `REFURB_A/B/C` 세분화를 하지 않는다.

`SAMPLE`

- 정상재고가 아니다.
- 샘플 보관 또는 외부반출 대상이다.
- `return_management_no` 기준으로 추적한다.
- 외부반출 검수 대상 후보이다.

`MANUFACTURER_RETURN`

- 정상재고가 아니다.
- 제조사반품 외부반출 대상이다.
- `return_management_no` 기준 1:1 검수가 필요하다.
- 1차 외부반출 흐름의 핵심 대상이다.

`HOLD`

- 정상재고가 아니다.
- 고객사 확인 또는 재판정 대상이다.
- 외부반출 대상이 아니라 보류 목록/후속 처리 대상이다.
- 후속으로 고객사 회신, 메모, 증빙 추가, 재판정 흐름이 필요하다.

`DISPOSAL`

- 정상재고가 아니다.
- 폐기 확정/폐기 이력 대상이다.
- 1차에서는 외부반출 대상이 아니라 폐기 후속 처리 후보로 둔다.
- 사진은 선택사항이며, 사진 미첨부를 이유로 폐기 확정을 차단하지 않는다.

## 4. 외부반출 대상 정의

1차 외부반출 후보 판정은 다음 세 가지다.

- `REFURB`
- `SAMPLE`
- `MANUFACTURER_RETURN`

후보 조건은 다음과 같다.

- `return_intake_rows.status = COMPLETED`
- `judgement_status in (REFURB, SAMPLE, MANUFACTURER_RETURN)`
- `return_management_no` 또는 `return_label_no`가 존재
- 외부반출 미처리 상태
- `inventory_reflected_yn`은 GOOD 재고반영 여부이므로 외부반출 처리 여부와 별도 관리가 필요

## 5. 필요한 최소 DB 후보

현재 모델에는 외부반출 처리 상태 필드가 없다. 후속 구현에서 다음 후보를 검토한다.

`return_intake_rows` 최소 필드 후보:

- `external_outbound_required`
- `external_outbound_status`
- `external_outbound_at`
- `external_outbound_batch_id`
- `external_outbound_confirmed_by`

별도 테이블 후보:

- `return_external_outbound_batches`
- `return_external_outbound_rows`

1차 추천은 구현 복잡도를 줄이기 위해 `return_intake_rows`에 최소 상태 필드를 추가하는 방식부터 검토하는 것이다. 다만 실제 반출 묶음, 운송장 묶음, 업체별 반출 지시서가 필요해지면 batch/rows 테이블이 더 안전하다.

이번 문서에서는 DB를 변경하지 않는다.

## 6. 외부반출 후보 조회 API 후보

후속 구현 API 후보:

- `GET /api/returns/external-outbound/candidates`
- `POST /api/returns/external-outbound/confirm`

후보 조회 조건:

- `judgement_status in (REFURB, SAMPLE, MANUFACTURER_RETURN)`
- `status = COMPLETED`
- `external_outbound_status`가 미처리
- `client_id` 필터
- `judgement_status` 필터
- `date_from`, `date_to` 필터
- `return_management_no` 검색

응답에는 최소한 `row_id`, `client_id`, `client_name`, `return_management_no`, `return_label_no`, `judgement_status`, `product_code`, `barcode`, `product_name`, `qty`, `status`, `external_outbound_status` 후보를 포함한다.

## 7. 외부반출 검수 기준

외부반출 검수는 수량 카운트만으로 처리하지 않는다. 1차 기준은 `return_management_no` 또는 `return_label_no` 스캔 기반 1:1 검수다.

- 스캔한 번호가 후보에 있으면 확인 처리한다.
- 같은 번호의 중복 스캔은 차단한다.
- 후보에 없는 번호는 오류로 표시한다.
- 선택한 반출 대상이 모두 확인되면 반출 확정 가능 상태가 된다.
- 오류 메시지는 작업자가 바로 볼 수 있게 표시하되 stack trace는 노출하지 않는다.

## 8. 외부반출 확정 정책

확정 시 후속 구현 후보:

- `external_outbound_status = CONFIRMED`
- `external_outbound_at` 저장
- `external_outbound_confirmed_by` 저장
- 필요 시 `inventory_events`에 외부반출 이벤트 생성

1차 외부반출 skeleton에서는 `current_inventory` 증가/감소와 연결하지 않는다. `REFURB`, `SAMPLE`, `MANUFACTURER_RETURN`은 GOOD 정상재고가 아니며, 별도 추적 재고 또는 외부반출 이벤트 정책이 필요하기 때문이다.

후속 재고 이벤트 후보:

- `RETURN_EXTERNAL_OUT`
- `RETURN_REFURB_OUT`
- `RETURN_SAMPLE_OUT`
- `RETURN_MANUFACTURER_RETURN_OUT`

## 9. HOLD 후속 처리 방향

`HOLD`는 외부반출이 아니라 보류 처리다.

후속 후보:

- HOLD 목록 조회
- 고객사 회신 메모
- 사진/증빙 추가
- 재판정
- HOLD 해제 후 `GOOD`, `REFURB`, `MANUFACTURER_RETURN`, `DISPOSAL` 등으로 재분류

## 10. DISPOSAL 후속 처리 방향

`DISPOSAL`은 외부반출이 아니라 폐기 처리다.

후속 후보:

- 폐기 후보 조회
- 폐기 확정
- 폐기일시/작업자/메모 저장
- 폐기 증빙 사진 선택 첨부
- 폐기 이력 조회

사진은 선택사항이다. 사진 미첨부를 이유로 폐기 확정을 막는 정책은 만들지 않는다.

## 11. 1차 skeleton 구현 범위 제안

다음 목표추진 작업 범위는 다음을 추천한다.

1. `return_intake_rows`에 외부반출 관련 최소 필드 추가 여부 판단
2. `GET /api/returns/external-outbound/candidates`
3. `POST /api/returns/external-outbound/confirm`
4. `/returns/external-outbound` 화면 skeleton
5. `SmartDataGrid` 후보 목록
6. `return_management_no` 스캔 입력
7. 스캔 확인 및 중복 차단
8. 반출 확정 버튼
9. 결과 summary 표시
10. `current_inventory` 변경은 하지 않음

## 12. 구현하지 않을 것

- 제조사 API 연동
- 리퍼업체 API 연동
- 택배 출고 송장 생성
- 재고 차감
- 정산
- 복잡한 반출 batch 관리
- 폐기 확정
- HOLD 재판정
- 사진 필수 정책

## 13. Closeout 결론

다음 작업은 목표추진 모드로 외부반출 후보 조회/검수 skeleton 구현을 진행한다.

1차 외부반출 대상은 `REFURB`, `SAMPLE`, `MANUFACTURER_RETURN`이다. `HOLD`와 `DISPOSAL`은 외부반출 흐름에 넣지 않고 각각 보류/폐기 후속 처리로 분리한다. 외부반출 검수는 `return_management_no` 또는 `return_label_no` 기준 1:1 스캔을 우선한다.
