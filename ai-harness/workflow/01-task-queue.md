# Task Queue

## 기준 상태

- 대상 저장소: `C:\smartreturn-pro`
- 브랜치: `smartreturn-pro`
- upstream: 작업 시작 시 `origin/smartreturn-pro`와 동기 상태 확인
- push: 금지

## Pending

- [ ] (P1) SPEC-005 게이트② 승인 여부 판단
  - 반품 재고반영 실행 구조 초안은 커밋 완료 상태다.
  - 사용자 승인 전 구현을 시작하지 않는다.
- [ ] (P1) AI-ready 플랫폼 데이터·판단 SPEC 착수 여부 판단
  - 개인정보/약관/reference/AI-ready 관련 untracked 문서는 별도 검토 및 별도 커밋 대상으로 분리한다.
  - SPEC-005 승인 판단과 동시에 실행하지 않는다.
- [ ] (P2) `ai-harness/consensus-loop/**` 삭제 묶음 처리 방향 결정
  - 현재 삭제 상태는 커밋 금지/보류다.
  - 별도 지시 없이는 stage, 복구, 커밋하지 않는다.

## In Progress

- [ ] 없음

## Done

- [x] SPEC-002: 재고현황 `stock_status` 화면 구현, 검증, 사용자 인수 완료.
- [x] SPEC-003: scan-first 반품처리 흐름 spec/report 커밋 완료.
- [x] SPEC-004: 반품 재고원장 계약 확정 완료.
- [x] SPEC-005: 반품 재고반영 실행 구조 초안 커밋 완료, 게이트② 승인 대기.
- [x] Tier 1 skills frontmatter 묶음 선별 커밋 완료.

## Hold / Separate

- [ ] `ai-harness/consensus-loop/**` 삭제 묶음: 커밋 금지/보류.
- [ ] `docs/business/**`: 별도 검토/별도 커밋 대상.
- [ ] `docs/legal/**`: 별도 검토/별도 커밋 대상.
- [ ] `docs/reference/**`: 별도 검토/별도 커밋 대상.
- [ ] `docs/reports/privacy-*.md`: 별도 검토/별도 커밋 대상.
- [ ] `docs/reports/terms-*.md`: 별도 검토/별도 커밋 대상.
- [ ] `docs/reports/smartreturn-platform-expansion-direction-oms-wms-erp-ai-ready.md`: 별도 검토/별도 커밋 대상.
