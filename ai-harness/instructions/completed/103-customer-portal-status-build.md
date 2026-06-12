# 103 - 고객포털 처리현황 화면 제작(조회형)

## 목표
고객포털 처리현황을 조회 중심으로 실사용 가능한 수준까지 제작/정리.

## 담당 작업
- frontend 화면 제작/개선. **앱 코드 수정은 이 단계에서만 허용.**

## 사전 조건
- 102 통과(조회형으로 가능 판단). 기존 API/컴포넌트 재사용 가능.

## 실행 범위
- 기존 route/화면 있으면 개선, 없으면 최소 화면 신규.
- **조회형 한정**: 저장/수정/삭제/상태변경/마감/반출 추가 금지.
- backend 권한/seed/API guard 수정 금지. 기존 API 재사용(우선 `/api/returns/history`).
- 새 공통 컴포넌트 생성 전 재사용 후보 확인. 화면 파일 과대 시 최소 분리.
- 하드코딩(고객사/판정/상태값) 금지 — 기존 enum/formatter 재사용.
- client_id/agency_id/client_unit_id scope 우회 금지(서버 강제 유지).

## 필수 UI
- 제목: "고객 반품 처리현황"
- 고객 고정 사용자: 고객사 선택 숨김/비활성 / 내부 미리보기: 고객사 선택 가능
- 검색: 운송장번호, 반품관리번호, 상품코드/바코드, 처리상태, 기간
- 그리드: 운송장번호, 반품관리번호, 상품코드, 상품명, 바코드, 판정, 처리상태, 입고/처리일, 창고/후속처리 상태
- 운송장/반품관리번호/상품코드/바코드 copyable, 엑셀 다운로드(exportFileName)
- 0건 안내 / 로딩·에러 상태 / 권한·scope 에러는 backend 사유 노출
- 1366x768 비파손

## 필수 확인 항목
- [ ] 조회 전용(쓰기 버튼 없음)
- [ ] 기존 컴포넌트 재사용(SmartPage/DataGrid 등)
- [ ] 한글 라벨(enum 원문 비노출)
- [ ] build/typecheck 통과, `git diff --check`

## 중단 조건
- build 실패 15분+ 미해결 → 중단
- 권한/backend 수정이 필요해짐 → 중단·보고

## 보고 위치
- `ai-harness/reports/103-customer-portal-status-build-report.md`

## 다음 지시문
- build 통과 → `104-customer-portal-status-verify-report.md`
- 실패/backend 필요 → 중단
