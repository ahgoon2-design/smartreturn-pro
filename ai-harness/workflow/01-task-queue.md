# Task Queue

## 기준 상태

- 대상 저장소: `C:\smartreturn-pro`
- 브랜치: `smartreturn-pro`
- upstream: 작업 시작 시 `origin/smartreturn-pro`와 동기 상태 확인
- push: SPEC-005는 사장님 승인 하 수문장 push 완료(`origin/smartreturn-pro`, ahead/behind 0/0)

## Pending

- [ ] (다음 판단 필요) 아래 3개 중 하나만 사장님 선택 후 진행(임의 실행 금지, 동시 실행 금지)
  - A. AI-ready 플랫폼 데이터·판단 SPEC 착수
  - B. privacy/legal/reference 보류 문서 정리
  - C. 후속 프론트 슬라이스 SPEC 착수(후보명: SPEC-006 return inventory apply result UX wiring — BLOCKED_* 문구/over_review 표시/마감·폐기·외부반출 confirm 화면/1366×768 인수)
- [ ] (P2) `ai-harness/consensus-loop/**` 삭제 묶음 처리 방향 결정
  - 현재 삭제 상태는 커밋 금지/보류다.
  - 별도 지시 없이는 stage, 복구, 커밋하지 않는다.

## In Progress

- [ ] 없음

## Done

- [x] SPEC-002: 재고현황 `stock_status` 화면 구현, 검증, 사용자 인수 완료.
- [x] SPEC-003: scan-first 반품처리 흐름 spec/report 커밋 완료.
- [x] SPEC-004: 반품 재고원장 계약 확정 완료.
- [x] SPEC-005: 반품 재고반영 실행 구조 구현·독립검수·수문장 커밋(`20faa635`)·push 완료. 잠금 10개 충족, 테스트 15+87 통과.
- [x] SPEC-005 후속 인수검증(read-only): 백엔드 실행계약 인수 완료 — 재검증 15+87 passed, alembic 단일 head, diff --check 통과, tree clean 0/0. 1366×768 UX 인수는 후속 프론트 슬라이스로 분리.
- [x] Tier 1 skills frontmatter 묶음 선별 커밋 완료.

## Hold / Separate

- [ ] `ai-harness/consensus-loop/**` 삭제 묶음: 커밋 금지/보류.
- [ ] `docs/business/**`: 별도 검토/별도 커밋 대상.
- [ ] `docs/legal/**`: 별도 검토/별도 커밋 대상.
- [ ] `docs/reference/**`: 별도 검토/별도 커밋 대상.
- [ ] `docs/reports/privacy-*.md`: 별도 검토/별도 커밋 대상.
- [ ] `docs/reports/terms-*.md`: 별도 검토/별도 커밋 대상.
- [ ] `docs/reports/smartreturn-platform-expansion-direction-oms-wms-erp-ai-ready.md`: 별도 검토/별도 커밋 대상.
