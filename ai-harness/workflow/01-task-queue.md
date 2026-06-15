# Task Queue

## Pending

- [ ] (P1) 판정 enum 정합 확정: FE의 `REFURB`(generic) vs 설계 7등급(`REFURB_A/B/C`) — 정본 enum 결정 후 FE/BE/문서 일치
- [ ] (P1) `SmartDataGrid` 엑셀 다운로드 기능 추가 → 조회형 화면(반품 이력/마감·반출·보류·폐기 후보)에 적용 (Ctrl+C 복사는 이미 있음)
- [ ] (P1) 반품처리 핵심 경로 backend 테스트 보강: `judge_return_processing_task`, `create_return_processing_manual_row`, 일마감 재고 반영(`confirm_return_closing`)
- [ ] (P2) 라벨 출력 Local Agent 연동(현재 준비중 placeholder) — MVP 후속
- [ ] (P2) 그리드 "사진" 컬럼이 "후속"으로 표기되나 첨부 업로드는 동작 → 표기 정합 정리
- [ ] (P2) Basic/Pro/Ultra plan feature gate(반품 고급기능) — 후속 plan_limits 작업과 연계
- [ ] SPEC-002 게이트④ 독립 검증(코덱) + 검증 보고서(docs/reports/SPEC-002-verify.md) — 다음 작업
- [ ] (후속) DEFECTIVE vs DISPOSAL 재고 처리 일관성 — 불량 전용 재고화 여부 (D-004 후보)

## In Progress

- [ ] (현재) 묶음5 운영문서 정합/커밋 (handoff·loop-state·task-queue)

## Done

- [x] seed/login 테스트 계정 커밋(28bec5e7), 플랫폼 브랜치 규칙(0464a7ec), 로컬 산출물 ignore(d64c9794)
- [x] Smart AI Dev Harness 구축(ee8913c3)
- [x] 묶음1~4 문서 선별 커밋(4커밋): 하네스 구조/게이트, SPEC-001 폐기·결정, SPEC-002 스펙, 게이트·Agent Teams 정책
- [x] SPEC-002 게이트③ 구현 + 빌드 보고서(docs/reports/SPEC-002-build.md) — 미커밋(트리 dirty)

## 보류 (미커밋)

- SPEC-002 구현 코드 8개 + SPEC-002-build.md
- 반품 화면 6개(ReturnClosing/Disposal/ExternalOutbound/Hold/IntakeHub/UnitAssignment)
- docs/decisions/tenancy-and-permission-model.md, docs/reports/return-spine-status-audit.md
