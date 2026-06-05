# 사용자 브라우저 테스트 체크리스트: 반품 처리 흐름

## 목적

사용자가 SmartReturn Pro를 직접 브라우저에서 실행하고, 반품 접수부터 판정별 후속 처리와 재고/이력 조회까지 한 바퀴 확인하기 위한 최소 체크리스트다.

## A. 서버 실행

1. backend 실행: `scripts/run_backend_dev.bat`
2. frontend 실행: `scripts/run_frontend_dev.bat`
3. 브라우저 접속: `http://127.0.0.1:5173/login`
4. backend 확인: `http://127.0.0.1:8000/health`

서버 종료는 각 실행 창에서 `Ctrl+C`를 사용한다.

## B. 로그인

- `/login` 화면이 보이는지 확인한다.
- 테스트 계정으로 로그인한다.
- 로그인 후 메뉴가 표시되는지 확인한다.
- 권한/역할 표시가 깨지지 않는지 확인한다.

## C. 기준정보 확인

- 고객사/셀러: `/master/clients`
- 상품/바코드: `/master/products`
- 고객사 상세 창고/처리장소 설정: `/master/clients/:clientId`
- 공통코드: `/master/common-codes`

## D. Import 확인

- Import Preview에서 Paste 또는 Excel 업로드를 실행한다.
- validate 결과를 확인한다.
- confirm 후 상품/바코드 마스터 반영 여부를 확인한다.

## E. 반품 접수

- 반품 접수 허브: `/returns/intake`
- batch 생성
- rows 저장
- validate
- 처리대상 생성

## F. 반품처리

- 반품처리 작업: `/returns/processing`
- 운송장번호 스캔 또는 입력
- 상품 바코드 스캔
- 판정 저장
- 필요한 경우 사진/증빙 선택 첨부
- 반품관리번호/라벨번호 생성 여부 확인
- Local Agent 미연결 안내와 라벨상태 표시 확인

## G. 판정별 후속

- GOOD: `/returns/closing`에서 일마감 후 `/inventory/current`, `/inventory/events` 확인
- REFURB / MANUFACTURER_RETURN / SAMPLE: `/returns/external-outbound`에서 스캔 검수와 반출 확정 후 `/returns/external-outbound/batches` 확인
- HOLD: `/returns/hold`에서 보류 메모 저장과 재판정 확인
- DISPOSAL: `/returns/disposal`에서 폐기 확정 확인

## H. 조회

- 반품 이력조회: `/returns/history`
- 재고현황: `/inventory/current`
- 재고 이벤트: `/inventory/events`

## I. 아직 안 되는 것

- Local Agent 실제 라벨 출력
- 브라우저 직접 카메라 촬영
- 정산
- 고객사/셀러 포털
- 외부 API 연동

## 확인 메모

- 사진은 선택사항이다. 사진이 없어도 판정, 재판정, 폐기 확정은 가능해야 한다.
- GOOD 외 판정은 정상재고로 바로 반영되지 않는다.
- secret, token, password 값은 화면이나 console에 출력하지 않는다.
