# Next Instruction

> /returns/processing Phase 1(frontend/backend/DEFECTIVE) 커밋 완료 + 브라우저 스모크 검증 완료. 데이터 의존 항목은 `03-test-report.md`의 User Browser Test Checklist 참조.

## 후속 1 — 사용자 브라우저 테스트 결과 반영
- 사용자가 처리대기 데이터 준비 후 체크리스트(A/B/C) 확인 → 문제 발견 시 해당 영역만 수정.

## 후속 2 — 엑셀 다운로드 확대 (Claude Code, frontend)
- `exportFileName`을 다른 조회형 화면(반품 이력/마감·반출·보류·폐기 후보)에 적용.
- id류 컬럼 `exportAsText`, 상태/판정 컬럼 `exportValue`(한글 라벨).

## 후속 3 — 불량(DEFECTIVE) 재고화 정책 (보류, 정책 확정 후)
- 불량/클레임/비가용 재고 흐름 필요 시 별도 설계. 확정 전까지 inventory/outbound 세트에 DEFECTIVE 미포함 유지.

## 후속 4 — GitHub push 여부 결정
- 현재 `smartreturn-pro`가 origin보다 앞서 있음(다수 미푸시 커밋). push 여부는 사용자 결정 필요. (main 병합/동기화는 명시 없이 제안하지 않음)

## 공통 규칙
- 현재 브랜치 `smartreturn-pro`(SmartReturn Pro 라인), `main` 병합/동기화 제안 금지.
- 처리완료 시 재고 즉시 반영 금지, DEFECTIVE 양품재고/외부반출 자동후보 금지, default 창고 하드코딩 금지.
- secret/env/local secret 읽기·출력 금지.
