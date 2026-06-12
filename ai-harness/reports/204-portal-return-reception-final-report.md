# 고객 포털 반품 접수 업로드 최종 보고

## 1. 완료 커밋

- `d2f5cacb`: 고객 포털 반품 접수 권한 분리
- `ab589513`: 고객 포털 반품 처리현황 화면
- `c44aa9c7`: AI 팀 운영 기준 문서
- `4af5ef20`: ai-harness 처리현황 산출물 보관
- `92bd6a0f`: RETURN_RECEPTION import 권한/confirm 보강
- `1d0b8e0d`: 고객 포털 반품 접수 업로드 화면

## 2. 최종 완료 범위

- 고객 포털 `/portal/returns` 반품 처리현황 화면을 추가했다.
- 고객 포털 `/portal/returns/intake` 반품 접수 등록 화면을 추가했다.
- Smart Import Mapper 공용 파이프라인을 `RETURN_RECEPTION` 타입으로 고객 포털에서 사용할 수 있게 했다.
- 고객 계정은 `RETURN_RECEPTION` import 생성, 붙여넣기, 자동매핑, 검증, row/error 조회, confirm 흐름을 사용할 수 있다.
- `RETURN_RECEPTION` confirm은 고객 반품 접수 자료만 생성하며, 입고 처리, 판정, 일마감, 외부반출, 재고반영은 수행하지 않는다.
- 고객 scope를 backend에서 강제한다.
- 고객 포털 화면에는 내부 처리, 판정, 일마감, 외부반출, 재고반영 액션을 노출하지 않는다.
- `SmartImportLauncher`를 재사용해 고객 포털 전용 업로드 흐름을 구성했다.
- 원본 `row_no`, 원본 순서, `raw_json` 원본 값을 보존한다.
- 운송장번호 칸에 메모값이 들어오는 경우 검증 오류로 처리한다.
- 고객 화면에는 운송장 오류를 내부 필드명이나 영문 문구가 아닌 한글 작업자 문구로 표시하도록 보정했다.

## 3. 검증 결과 요약

### Backend 테스트

- backend import mapper: `14 passed`
- backend import API: `81 passed`
- backend return reception: `8 passed`

### Frontend 검증

- `npm.cmd run build`: 통과
- `git diff --check`: 통과

### 브라우저 E2E

- 고객 계정 로그인 성공
- `/portal/returns/intake` 진입 성공
- 반품 접수 자료 붙여넣기 성공
- 자동매핑 성공
- validation 성공
- confirm 성공
- `return_intake_batches` / `return_intake_rows` 생성 확인
- `/portal/returns` 처리현황에서 등록 자료 조회 확인
- 고객 포털에 내부 운영자 메뉴와 내부 처리 액션이 노출되지 않음

## 4. 보안/권한 확인

- `CLIENT_ADMIN` / `CLIENT_USER`는 `RETURN_CLIENT_SUBMIT` 권한으로 `RETURN_RECEPTION` import만 사용할 수 있다.
- 고객 계정은 `PRODUCT_MASTER`, `PRODUCT_BARCODE` 등 내부 관리자용 import type을 사용할 수 없다.
- 다른 `client_id` 접근은 `CLIENT_SCOPE_DENIED`로 차단한다.
- `backend/local.secret.json`, `.env`, token, password, API key, 쿠키, 세션값 원문을 출력하거나 커밋하지 않았다.
- 완료 커밋 묶음은 원격 `smartreturn-pro` 브랜치에 push 완료했다.
- force push는 수행하지 않았다.

## 5. 남은 이슈

- 운송장 오류 한글 문구 최종 화면 수동 확인이 필요하다.
- antd React 19 compatibility warning이 남아 있다.
- profile/decision 비활성화 API가 아직 없다.
- 구글시트 source-sync는 미구현 상태다.
- 상품명-only 후보 추천은 미구현 상태다.
- 1366x768 기준 고객 포털 접수 업로드 UX 최종 점검이 필요하다.

## 6. 다음 추천 큐

- `205`: profile/decision 비활성화 API 설계/구현
- 또는 `205`: 1366x768 고객 포털 접수 업로드 UX 최종 점검
- 또는 `205`: 고객 포털 접수 업로드 운영 테스트 시나리오 작성
