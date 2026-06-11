# Next Instruction

> Phase 1 frontend(Claude Code)는 완료. 아래는 Phase 1을 마무리하기 위한 **Codex(backend) 후속 지시문 초안**이다.

---

실행 대상: Codex (backend 레인)
모드: 목표추진모드
이유: `/returns/processing` Phase 1의 frontend(엑셀 다운로드 + generic REFURB 제거)는 완료됐고, 판정 enum 정합과 DEFECTIVE 지원, 테스트 보강이 backend에 남아 있다.

현재 작업 중인 프로젝트폴더를 `<PROJECT_ROOT>`로 간주한다.
`<PROJECT_ROOT>/AGENTS.md`, `<PROJECT_ROOT>/CODEX.md`를 먼저 읽는다.
현재 브랜치 `smartreturn-pro`(SmartReturn Pro 라인) 기준으로만 작업하고, `main` 병합/동기화는 제안하지 않는다.

## 정본 판정 코드
`GOOD / REFURB_A / REFURB_B / REFURB_C / MANUFACTURER_RETURN / SAMPLE / HOLD / DISPOSAL / DEFECTIVE`
(generic `REFURB`는 신규 저장 기준에서 사용하지 않음. 레거시 데이터 호환은 mapping으로만.)

## 목표 (backend)
1. **외부반출 후보 쿼리 정합**: `return_intake_repository.py`의 generic `("REFURB", ...)` 필터를 `REFURB_A/B/C` 포함 기준으로 수정(레거시 `REFURB` 호환 포함 검토). closing/outbound/inventory 분기의 판정 기준 통일.
2. **DEFECTIVE 지원**: 판정 코드로 저장/조회 가능하게 하고, 고객사 창고 라우팅(`return_warehouse_routes`)에 DEFECTIVE 경로가 없을 때의 처리(미배정 시 처리완료 차단 유지)를 명확히.
3. **테스트 보강**: judge / manual-row / closing(일마감 시에만 재고반영) / agency·client scope 회귀 pytest 추가.

## 금지
- 처리완료 시 재고 즉시 반영으로 변경 금지(일마감/반출 확정에서만 반영).
- frontend 임의 수정 금지(완료된 frontend 계약 유지).
- secret/env/local secret 읽기·출력 금지, main 병합/동기화 제안 금지.

## backend 계약 변경 후 frontend 후속(Claude Code)
- backend가 DEFECTIVE를 정식 지원하면, frontend `JUDGEMENT_OPTIONS`에 `DEFECTIVE`(라벨 "불량") 추가.

## 검증
- `python -m pytest`(반품 관련 범위)
- `git diff --check`, `git status --short`
- 보고: `ai-harness/workflow/02-agent-report.md`(backend 섹션), `03-test-report.md`
