# SmartReturn Pro 메뉴 및 화면 목록

이 문서는 SmartReturn Pro의 메뉴 구조와 화면 목록을 고정하기 위한 기준 문서다. 아직 화면을 구현하지 않으며, 기존 SmartReturn 화면 구성을 그대로 따르지 않는다.

## 메뉴 설계 원칙

- 큰 업무는 메인 메뉴로 둔다.
- 실제 반복 작업은 서브 메뉴로 둔다.
- 관련 정보 묶음은 탭 또는 섹션으로 둔다.
- 짧은 보조작업은 모달로 처리한다.
- 한 화면에 서로 다른 업무를 섞지 않는다.
- 작업자 화면과 관리자 화면을 섞지 않는다.
- 화면 이름은 사용자가 이해하는 업무명으로 작성한다.
- 내부 key는 영어를 사용할 수 있으나 화면 표시명은 한글로 작성한다.

## 1차 메뉴 구조

### 대시보드

- 메인 대시보드
- 작업 시작

### 기준정보

- 고객사 관리
- 상품 관리
- 창고 관리
- 공통코드 관리
- 사용자/권한 관리

### 반품

- 반품자료 준비
- 반품처리 작업
- 반품 마감
- 반품 반출
- 반품 통합추적

### 입고

- 입고자료 준비
- 입고검수 작업
- 입고확정
- 입고 이력조회

### 출고

- 출고자료 준비
- 출고검수 작업
- 출고확정
- 출고 이력조회

### OMS

- 주문자료 준비
- 주문 조회
- 출고대상 생성
- 주문 이력조회

### 재고

- 재고현황
- 재고이력
- 재고조정
- 재고실사

### 정산

- 계약/단가 관리
- 정산 생성
- 정산 검토
- 정산 마감
- 거래명세서

### 연동/설정

- 택배사 연동
- ERP 연동
- 구글시트 연동
- Local Agent 관리
- 시스템 설정

### 고객사 포털

- 포털 대시보드
- 출고 조회
- 재고 조회
- 반품 조회
- 정산 조회
- 자료 업로드

## 화면별 책임표

| 메뉴 | 화면명 | 화면 타입 | 사용자 | 주요 기능 | 넣지 말 것 | 관련 정책 문서 |
| --- | --- | --- | --- | --- | --- | --- |
| 대시보드 | 메인 대시보드 | 대시보드형 | 내부 운영자 | 업무 상태, 예외, 지연, 주요 KPI 확인 | 확정 처리, 대량 편집 | `docs/ui/smartreturn-pro-ui-page-templates.md` |
| 대시보드 | 작업 시작 | 대시보드형 | 내부 운영자, 작업자 | 반복 작업 진입 버튼 제공 | 업무 확정, 상세 설정 | `docs/ui/smartreturn-pro-ui-page-templates.md` |
| 기준정보 | 고객사 관리 | 관리자 조회형 | 내부 운영자 | 고객사 등록, 수정, 사용중지, 사용창고 연결 | 창고 업무 처리, 주문/반품 처리 | `docs/business/smartreturn-pro-master-data-policy.md` |
| 기준정보 | 상품 관리 | 관리자 조회형 | 내부 운영자, 고객사 관리자 | 상품 기준정보, 대표 바코드, 추가 바코드 관리 | 재고 직접 변경, 출고 확정 | `docs/business/smartreturn-pro-master-data-policy.md` |
| 기준정보 | 창고 관리 | 관리자 조회형 | 내부 운영자 | 창고, 위치, 고객사 연결 관리 | 입고/출고 처리 | `docs/business/smartreturn-pro-master-data-policy.md` |
| 기준정보 | 공통코드 관리 | 관리자 조회형 | 내부 운영자 | 상태, 사유, 택배사, 소스 코드 관리 | 화면별 하드코딩 | `docs/business/smartreturn-pro-master-data-policy.md` |
| 기준정보 | 사용자/권한 관리 | 관리자 조회형 | 내부 운영자 | 사용자, role, 권한, 비밀번호 초기화 관리 | 비밀번호 조회, 평문 응답 | `docs/business/smartreturn-pro-auth-password-policy.md` |
| 반품 | 반품자료 준비 | 업로드/검증형 | 내부 운영자 | 입력소스 등록, 업로드, 동기화, 검증, 저장, 조회 | 실제 판정, 마감, 반출, 재고처리 | `docs/business/smartreturn-pro-return-policy.md` |
| 반품 | 반품처리 작업 | 작업자 스캔형 | 작업자 | 운송장/입고번호 스캔, 상품 확인, 판정, 사진/메모, 라벨 출력, 처리완료 | 구글시트 동기화, 업로드 이력, 마감, 반출, 재고 이벤트 상세 | `docs/business/smartreturn-pro-return-policy.md` |
| 반품 | 반품 마감 | 마감/대조형 | 내부 운영자 | 기간/고객사/판정상태 조회, 판정별 수량 대조, 마감 대조 | 재고반영, 반출확정, 개별 판정 | `docs/business/smartreturn-pro-return-policy.md` |
| 반품 | 반품 반출 | 작업자 스캔형 | 내부 운영자, 작업자 | 외부반출 대상 묶음, 반품관리번호 스캔, 반출확정 | 판정, 마감 대조, 구글시트 push | `docs/business/smartreturn-pro-return-policy.md` |
| 반품 | 반품 통합추적 | 관리자 조회형 | 내부 운영자, 고객사 사용자 | 운송장번호, 반품관리번호, `work_batch_id`, `external_ref_no` 기준 조회 | 판정, 마감, 반출, 구글시트 push 조작 | `docs/business/smartreturn-pro-return-policy.md` |
| 입고 | 입고자료 준비 | 업로드/검증형 | 내부 운영자 | 예정입고 자료 업로드, 검증, 저장 | 재고 반영, 입고 확정 | `docs/business/smartreturn-pro-inbound-outbound-policy.md` |
| 입고 | 입고검수 작업 | 작업자 스캔형 | 작업자 | 예정/무예정 입고 검수, 상품/수량 확인 | 확정 전 재고 반영 | `docs/business/smartreturn-pro-inbound-outbound-policy.md` |
| 입고 | 입고확정 | 마감/대조형 | 내부 운영자 | 검수 결과 확인, 예외 점검, 입고 확정 | 원본 업로드, 스캔 입력 | `docs/business/smartreturn-pro-inbound-outbound-policy.md` |
| 입고 | 입고 이력조회 | 관리자 조회형 | 내부 운영자, 고객사 사용자 | 입고 결과와 이력 조회 | 신규 입고 처리, 재고 직접 수정 | `docs/business/smartreturn-pro-inbound-outbound-policy.md` |
| 출고 | 출고자료 준비 | 업로드/검증형 | 내부 운영자 | 출고자료 업로드, 검증, 저장 | 출고검수, 재고 차감 | `docs/business/smartreturn-pro-inbound-outbound-policy.md` |
| 출고 | 출고검수 작업 | 작업자 스캔형 | 작업자 | 출고 상품 스캔, 수량 검수, 예외 표시 | 스캔 중 재고 차감 | `docs/business/smartreturn-pro-inbound-outbound-policy.md` |
| 출고 | 출고확정 | 마감/대조형 | 내부 운영자 | 검수 완료 대상 확정, 서버 재고 이벤트 생성 | 신규 업로드, 개별 스캔 | `docs/business/smartreturn-pro-inbound-outbound-policy.md` |
| 출고 | 출고 이력조회 | 관리자 조회형 | 내부 운영자, 고객사 사용자 | 출고 결과, 검수 이력, 예외 조회 | 출고 확정, 재고 조정 | `docs/business/smartreturn-pro-inbound-outbound-policy.md` |
| OMS | 주문자료 준비 | 업로드/검증형 | 내부 운영자, 고객사 사용자 | 주문자료 업로드, 검증, 저장 | 출고검수, 재고 차감 | `docs/db/smartreturn-pro-initial-erd.md` |
| OMS | 주문 조회 | 관리자 조회형 | 내부 운영자, 고객사 사용자 | 주문 상태, 주문 상품, 오류 조회 | 출고확정, 재고조정 | `docs/db/smartreturn-pro-initial-erd.md` |
| OMS | 출고대상 생성 | 마감/대조형 | 내부 운영자 | 주문 기반 출고대상 생성 | 스캔 작업, 재고 차감 | `docs/db/smartreturn-pro-initial-erd.md` |
| OMS | 주문 이력조회 | 관리자 조회형 | 내부 운영자, 고객사 사용자 | 주문 변경과 처리 이력 조회 | 주문 편집, 확정 처리 | `docs/db/smartreturn-pro-initial-erd.md` |
| 재고 | 재고현황 | 관리자 조회형 | 내부 운영자, 고객사 사용자 | 현재고 조회, 고객사/창고/상품별 필터 | 원장 없는 현재고 직접 수정 | `docs/db/smartreturn-pro-db-and-import-policy.md` |
| 재고 | 재고이력 | 관리자 조회형 | 내부 운영자 | `inventory_events` 원장 조회 | 재고 직접 변경 | `docs/business/smartreturn-pro-scan-local-agent-inventory-policy.md` |
| 재고 | 재고조정 | 마감/대조형 | 내부 운영자 | 조정 사유 입력, 조정 이벤트 생성 | `current_inventory` 직접 수정 | `docs/db/smartreturn-pro-db-and-import-policy.md` |
| 재고 | 재고실사 | 작업자 스캔형 | 내부 운영자, 작업자 | 실사 스캔, 차이 확인, 실사 결과 저장 | 자동 재고 반영 | `docs/business/smartreturn-pro-scan-local-agent-inventory-policy.md` |
| 정산 | 계약/단가 관리 | 관리자 조회형 | 내부 운영자 | 고객사별 계약/단가 기준 관리 | 정산 확정, 업무 처리 | `docs/db/smartreturn-pro-initial-erd.md` |
| 정산 | 정산 생성 | 마감/대조형 | 내부 운영자 | 운영 이벤트 기반 정산 초안 생성 | 단가 정책 고도화 | `docs/dev/smartreturn-pro-test-and-release-policy.md` |
| 정산 | 정산 검토 | 관리자 조회형 | 내부 운영자 | 정산 라인 검토, 예외 확인 | 출고/반품 처리 | `docs/db/smartreturn-pro-initial-erd.md` |
| 정산 | 정산 마감 | 마감/대조형 | 내부 운영자 | 정산 마감, 마감 이력 생성 | 상세 단가 정책 임의 확정 | `docs/db/smartreturn-pro-initial-erd.md` |
| 정산 | 거래명세서 | 관리자 조회형 | 내부 운영자, 고객사 사용자 | 거래명세서 조회와 출력 후보 | 정산 재계산 | `docs/db/smartreturn-pro-initial-erd.md` |
| 연동/설정 | 택배사 연동 | 관리자 조회형 | 내부 운영자 | 택배사 기준, 연동 설정 확인 | 현장 스캔 처리 | `docs/business/smartreturn-pro-master-data-policy.md` |
| 연동/설정 | ERP 연동 | 관리자 조회형 | 내부 운영자 | ERP 연동 설정 후보 관리 | ERP 실제 API 직접 전송 | `docs/smartreturn-pro-core-principles.md` |
| 연동/설정 | 구글시트 연동 | 관리자 조회형 | 내부 운영자 | 구글시트 source 설정과 동기화 상태 확인 | 반품처리 작업 중 직접 호출 | `docs/business/smartreturn-pro-return-policy.md` |
| 연동/설정 | Local Agent 관리 | 관리자 조회형 | 내부 운영자 | 장치 상태, 프린터, 사운드, 설정 이력 확인 | 재고 직접 변경, 자동 업데이트 | `docs/business/smartreturn-pro-scan-local-agent-inventory-policy.md` |
| 연동/설정 | 시스템 설정 | 관리자 조회형 | 내부 운영자 | 시스템 공통 설정 조회/관리 | 업무 처리 화면 대체 | `docs/smartreturn-pro-core-principles.md` |
| 고객사 포털 | 포털 대시보드 | 대시보드형 | 고객사 사용자 | 고객사 업무 상태 요약 | 내부 운영자 설정, 전체 고객사 조회 | `docs/business/smartreturn-pro-auth-password-policy.md` |
| 고객사 포털 | 출고 조회 | 관리자 조회형 | 고객사 사용자 | 자기 `client_id` 출고 조회 | 타 고객사 조회, 출고확정 | `docs/business/smartreturn-pro-auth-password-policy.md` |
| 고객사 포털 | 재고 조회 | 관리자 조회형 | 고객사 사용자 | 자기 `client_id` 재고 조회 | 재고조정, 원장 수정 | `docs/business/smartreturn-pro-auth-password-policy.md` |
| 고객사 포털 | 반품 조회 | 관리자 조회형 | 고객사 사용자 | 자기 `client_id` 반품 조회 | 판정, 마감, 반출 조작 | `docs/business/smartreturn-pro-return-policy.md` |
| 고객사 포털 | 정산 조회 | 관리자 조회형 | 고객사 사용자 | 자기 `client_id` 정산 조회 | 정산 생성, 단가 변경 | `docs/db/smartreturn-pro-initial-erd.md` |
| 고객사 포털 | 자료 업로드 | 업로드/검증형 | 고객사 사용자 | 허용된 주문/반품 자료 업로드 | 내부 확정, 재고 반영 | `docs/db/smartreturn-pro-db-and-import-policy.md` |

## 반품 화면 책임 상세

### 반품자료 준비

- 입력소스 등록, 업로드, 동기화, 검증, 저장, 조회를 담당한다.
- 구글시트는 업체 반품접수/회신 채널로만 다룬다.
- CJ/택배 엑셀은 반품예정 자료로 다룬다.
- 실제 판정, 마감, 반출은 하지 않는다.
- 재고 이벤트를 생성하지 않는다.

### 반품처리 작업

- 운송장 또는 입고번호를 스캔한다.
- 상품을 확인한다.
- 판정을 입력한다.
- 사진과 메모를 남긴다.
- 라벨 출력과 재출력을 수행할 수 있다.
- 처리완료를 저장한다.
- 구글시트 동기화, 업로드 이력, 마감, 반출, 재고 이벤트 상세를 넣지 않는다.
- 라벨 출력 실패는 판정 저장 실패가 아니다.

### 반품 마감

- 기간, 고객사, 판정상태 기준으로 조회한다.
- 판정별 수량을 대조한다.
- 양품/폐기는 상품바코드 수량을 대조한다.
- 리퍼/제조사반품/샘플/보류는 반품관리번호 1:1로 대조한다.
- 반품 마감은 재고반영이 아니라 마감 대조다.

### 반품 반출

- 외부반출 대상 묶음을 만든다.
- 반품관리번호를 스캔한다.
- 반출확정을 수행한다.
- 판정과 마감과는 별도 화면으로 둔다.

### 반품 통합추적

- 읽기 전용 조회 화면이다.
- 운송장번호, 반품관리번호, `work_batch_id`, `external_ref_no` 기준으로 조회한다.
- 판정, 마감, 반출, 구글시트 push 조작을 금지한다.

## 작업 시작 화면 대표 버튼

추천 대표 버튼 순서는 다음과 같다.

1. 출고검수 작업
2. 반품처리 작업
3. 입고검수 작업
4. 반품 마감

실제 대표 버튼은 추후 운영 우선순위, 작업량, 사용자 역할에 따라 조정할 수 있다.

## Codex 구현 전 체크

- 큰 업무는 메인 메뉴, 반복 작업은 서브 메뉴로 분리했는가?
- 작업자 화면과 관리자 화면을 섞지 않았는가?
- 화면 1개가 업무 목적 1개만 가지는가?
- 화면 타입이 `docs/ui/smartreturn-pro-ui-page-templates.md`의 타입을 따르는가?
- 반품자료 준비, 반품처리 작업, 반품 마감, 반품 반출, 반품 통합추적의 책임이 분리되어 있는가?
- 고객사 포털 화면이 자기 `client_id` 범위를 벗어나지 않는가?
- 초기 제외 범위인 고객사 포털 전체 구현, ERP 실제 API 전송, 정산 고도화를 확정 구현처럼 다루지 않았는가?
