# 슬라이스 스펙: 스캔 우선·AI 보조형 반품처리 루틴

## 1. 한 줄 목적

현장 작업자가 스캐너만으로 정상건을 빠르게 처리하고, 문제건만 화면을 보도록 반품처리 루틴을 개선한다.

## 2. 사용자 / 권한 scope

- 누가 쓰나(role): INTERNAL_WORKER, INTERNAL_ADMIN, AGENCY_ADMIN
- scope: agency_id → client_id → client_unit_id → warehouse_id
- 내부 / 포털 구분: 내부 운영자 전용 (현장 작업자 화면)

## 3. 화면에서 하는 일 (흐름)

### 정상건 빠른 처리 루틴
1. 운송장번호 스캔 → 예상 반품자료 자동 조회 및 자동 선택
2. 상품 바코드 스캔 → 예상 상품 일치 확인(MATCHED)
3. 빠른 처리 모드 ON + GOOD 창고 라우팅 존재 → 자동 처리완료
4. 운송장 입력창 자동 포커스 이동 → 다음 건 스캔

### 문제건 처리 루틴 (자동완료 없음)
- 운송장 자료 없음 → 수동 상품 추가 모드
- 상품 불일치 (MISMATCHED) → 화면 확인 대기
- 판정: HOLD / DISPOSAL / MANUFACTURER_RETURN / DEFECTIVE → 자동완료 불가
- validation_status === "WARNING" → 자동완료 불가

### 판정 바코드 처리
- 운송장 입력창에 `JUDGE_GOOD` / `JUDGE_HOLD` / `JUDGE_DEFECTIVE` / `JUDGE_DISPOSAL` / `JUDGE_MANUFACTURER_RETURN` 스캔 → 해당 판정 선택
- `CANCEL_LAST` → 취소 API 준비 전 안내 메시지
- `REPRINT_LABEL` → Local Agent 미연결 안내
- `MANUAL_CHECK` → 선택 상품 확인 (그리드 선택 처리)
- GOOD 판정 바코드 + 빠른 처리 모드 + 조건 충족 → 자동완료

### AI 보조 자리 (이번 스펙: placeholder만 준비, API 미연동)
- 추천 판정 자리
- 주의/경고 자리 (반복 파손·보류 이력)
- HOLD 메모 초안 자리
- CS 안내 초안 자리

## 4. 재사용할 기존 자산 (먼저 확인 후 채움)

- route: `/returns/processing` (기존 ReturnProcessingWorkspacePage.tsx)
- API: `judgeReturnProcessingTask` (기존), `listReturnWarehouseRoutes` (기존)
- 공통 컴포넌트: SmartScanPanel, SmartDataGrid, SmartStatusBadge, SmartPageHeader (모두 기존)
- 기존 canSaveJudgement, selectJudgementOption, handleJudgementSave 활용
- 기존 findWarehouseRoute 활용

## 5. 있어야 할 것 / 절대 없어야 할 것

있어야:
- 빠른 처리 모드 ON/OFF 토글 (SmartScanPanel 상단 고정)
- 마지막 처리 취소 버튼 (disabled placeholder, API 준비 전)
- 판정 바코드 감지 (운송장 입력창에서 JUDGE_* 접두어)
- HOLD 메모 없을 때 처리완료 버튼 비활성 (경고 → 차단으로 강화)
- MANUFACTURER_RETURN 메모 권고 경고 (처리완료는 가능, 주의 표시)
- AI 보조 자리 placeholder (collapsed details, API 미연동)
- 최근 처리 10건 로그 (성공/경고/오류 색상 구분)
- 1366×768 기준 실사용 가능

없어야:
- HOLD/MANUFACTURER_RETURN/DISPOSAL/DEFECTIVE 자동 처리완료
- validation_status === "WARNING" 건 자동 처리완료
- 자동완료 시 current_inventory 즉시 변경
- 현장 작업자 화면에 DB 필드명/내부 enum 노출
- AI 추천 자동 판정 확정
- 임의 창고 선택 (warehouse_id는 고객사 라우팅 기준)

## 6. 완료기준 (사용자가 화면에서 직접 확인하는 체크리스트)

- [ ] 빠른 처리 모드 토글 ON/OFF 작동, 상태 표시 확인
- [ ] 빠른 처리 모드 ON + GOOD 조건 충족 → 상품 스캔 후 자동 처리완료 + 운송장 포커스
- [ ] HOLD 판정 + 메모 없음 → 처리완료 버튼 disabled 확인
- [ ] JUDGE_GOOD 운송장 스캔 → GOOD 판정 자동 선택 확인
- [ ] JUDGE_HOLD 스캔 → HOLD 판정 선택 + 메모 입력 요구 확인
- [ ] CANCEL_LAST 스캔 → 취소 불가 안내 메시지 확인
- [ ] AI 판정 추천 collapsed 섹션 표시(상품 MATCHED 후) 확인
- [ ] 최근 처리 로그 10건 표시, 색상 구분 확인
- [ ] MANUFACTURER_RETURN 선택 시 경고 안내 표시 확인
- [ ] 1366×768 화면에서 스캔 입력·판정 버튼·처리완료 버튼 모두 표시 확인

## 7. 리스크 / 보류(HOLD) 케이스

- 빠른 처리 모드 자동완료 후 취소 방법 없음 → CANCEL_LAST API 후속 구현 필요
- AI 보조 API 미연동 → placeholder만 준비, 실제 추천 로직 후속 구현
- 라벨 재출력 → Local Agent 미연결 상태에서 REPRINT_LABEL 스캔 → 안내 메시지만 표시
- 판정 바코드 시트 물리 인쇄 → 별도 인쇄용 바코드 시트 생성 기능 후속 과제
- MANUFACTURER_RETURN FE 강제 차단 → 이번 스펙은 경고만, 설정 기반 차단은 후속
