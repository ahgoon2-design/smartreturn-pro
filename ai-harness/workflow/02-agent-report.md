# Agent Report

## Summary

`/returns/processing` 구현 전 gap 분석. 현재 브랜치 `smartreturn-pro`(SmartReturn Pro 플랫폼), 작업트리 클린. 결론: 처리화면은 FE/BE 모두 이미 구현되어 핵심 설계에 부합. 남은 격차는 P1/P2 보완 위주.

## Agent Logs

### smartreturn-pm

- 모드: 플랜모드. 분석은 Claude Code 단독, 후속 구현은 Claude(프론트)+Codex(백엔드) 분담 권장.
- 범위: `/returns/processing` 한 화면 + 직접 연결된 backend API/일마감 재고 반영 경계까지만. 입고/정산 등 확장 제외.

### smartreturn-architect

- 데이터 흐름 확인: intake batch → validate → prepare-processing → (unit-assign) → processing tasks(READY_FOR_PROCESSING) → judge(처리완료) → closing(일마감 시 재고 반영).
- 설계 부합: 판정 시점 `current_inventory` 미변경, 재고는 `confirm_return_closing`에서 `create_inventory_event`+`increase_current_inventory`로 반영. scope는 `resolve_effective_client_id`(agency/client)로 전반 적용. 창고는 고객사 `return_warehouse_routes`/창고설정으로 배정.
- 위험: 판정 enum 이원화(REFURB vs REFURB_A/B/C)로 데이터 정합/집계 혼선 가능. client_unit_id 세부권한은 보류 상태(기존 결정).

### backend-engineer (현황 파악)

- `routers/returns.py`: intake/unit-assign/processing(list·judge·manual-rows·attachments)/history/closing/external-outbound/hold/disposal 엔드포인트 존재. 모든 endpoint가 `get_current_auth_context` + `require_password_change_completed` 적용.
- `return_intake_service.py`: judge/manual-row/closing 구현. 권한 `require_permission`(RETURN_VIEW/PREPARE 등) 사용, 일마감에서만 재고 반영.
- 테스트: `test_return_intake_api.py`만 존재 → judge/manual/closing/재고반영 직접 테스트 보강 필요.

### frontend-engineer (현황 파악)

- `ReturnProcessingWorkspacePage.tsx`(1680줄): 운송장 스캔 → 그리드/상세 → 상품 스캔 확인(MATCHED/MISMATCHED) + "선택 상품 확인"(그리드 선택) **이중 처리 지원**, 세부항목 없는 반품(고객사 선택+상품검색/스캔으로 manual row 추가), 판정 버튼(고객사 라우팅 기준), 창고 확정 필수(`canSaveJudgement`), 처리완료, 첨부(사진) 업로드, 라벨=준비중. 한글 라벨 매핑(enum 원문 미노출). SmartDataGrid `enableCopy`/`preserveOriginalOrder`/loading 사용.

### ux-grid-specialist

- 충족: Ctrl+C 복사(enableCopy), loading state, copyable 컬럼, 처리완료 후 "재고 미반영" 안내, 1~5단계 흐름 strip.
- 미충족: **엑셀 다운로드**(SmartDataGrid에 export 미구현) → 조회형 화면 공통 gap. "사진" 컬럼 "후속" 표기 vs 실제 첨부 동작 불일치(경미).

### security-guard

- 위험 없음. secret/env 미열람. 코드 미수정. 처리 API scope/권한 검증 존재.

---

## /returns/processing Gap List

### A. 현재 이미 충족된 항목

| 영역 | 항목 | 근거 파일 | 비고 |
|---|---|---|---|
| route | `/returns/processing` 존재·가드 | `routes/router.tsx`, `RouteGuard.tsx` | 내부 영역 |
| 조회 | 운송장 스캔/조회 | `ReturnProcessingWorkspacePage.tsx` `loadTasks` | status=READY_FOR_PROCESSING |
| 처리 | 스캔 처리 + 그리드 선택 처리 | `handleProductScanEnter`/`handleGridSelectConfirm` | 둘 다 지원 |
| 세부항목 없는 반품 | 고객사 선택+상품검색/스캔 추가 | `createReturnProcessingManualRow` | manual row |
| 판정 | 판정 버튼 + 고객사 라우팅 | `judgeReturnProcessingTask`, `listReturnWarehouseRoutes` | |
| 창고 | 창고 확정 필수 | `canSaveJudgement`(warehouse_id 필수) | 설계 부합 |
| 재고 | 처리완료 시 재고 미반영, 일마감서 반영 | `confirm_return_closing`(1644~1711) | 설계 부합 |
| scope | agency/client scope 검증 | `resolve_effective_client_id` 전반 | |
| UX | Ctrl+C 복사/loading/한글 라벨 | `SmartDataGrid enableCopy` | |

### B. 미충족 항목

| 우선순위 | 영역 | gap | 필요한 작업 | 관련 파일 |
|---|---|---|---|---|
| P1 | UX/Grid | 조회형 엑셀 다운로드 없음 | SmartDataGrid에 엑셀 export 추가 후 조회형 화면 적용 | `components/grid/SmartDataGrid.tsx` |
| P1 | 데이터 | 판정 enum 이원화(REFURB vs A/B/C) | 정본 enum 확정 후 FE/BE/문서 일치 | `ReturnProcessingWorkspacePage.tsx`, `schemas/returns.py` |
| P1 | 테스트 | judge/manual/closing 재고반영 테스트 부족 | pytest 보강 | `backend/tests/` |
| P2 | 라벨 | Local Agent 라벨 출력 미연동(준비중) | endpoint 확정 후 연동 (MVP 후속) | 처리화면 라벨 패널 |
| P2 | UX | 그리드 "사진" 컬럼 "후속" 표기 vs 첨부 동작 불일치 | 표기 정합 | 처리화면 columns |
| P2 | plan | Basic/Pro/Ultra feature gate 미적용 | plan_limits 작업과 연계 | 후속 |

### C. 위험 항목

| 위험 | 설명 | 대응 |
|---|---|---|
| 판정 enum 혼선 | REFURB(generic)와 A/B/C 공존 → 집계/마감/반출 분류 오차 | 정본 enum 먼저 확정 후 구현 |
| 테스트 공백 | 처리완료/재고반영 회귀 미검출 가능 | 구현 전/후 pytest 보강 |
| 라벨 미연동 | 현장 라벨 출력 불가(준비중) | MVP 범위 확인, Local Agent 후속 |

### D. 구현 전 결정 필요 항목

| 결정사항 | 선택지 | 추천 |
|---|---|---|
| 판정 enum 정본 | (a) A/B/C만 + generic REFURB 제거 / (b) generic 유지 | (a) 설계 7등급 기준 |
| 엑셀 다운로드 범위 | (a) 공통 그리드 기능 / (b) 화면별 | (a) SmartDataGrid 공통 |
| 라벨 출력 | (a) 이번 제외 유지 / (b) 지금 연동 | (a) MVP 후속 |

## Recommended Implementation Plan

### Phase 1. 처리화면 정합/품질 보완 (P1)
- 목표: 판정 enum 정본화 + 엑셀 다운로드 + 테스트 보강
- backend(Codex): 판정 enum 정합(schemas/service), judge/closing 테스트 추가
- frontend(Claude): SmartDataGrid 엑셀 export, 판정 버튼 enum 정리, 조회형 화면 적용
- 완료 기준: 판정 enum 단일 기준, 조회형 엑셀 다운로드 동작, pytest+build 통과

### Phase 2. 라벨/사진 정합 (P2)
- 목표: 사진 컬럼 표기 정합 + 라벨 정책 표시 정리(연동은 후속)
- 완료 기준: 화면 표기와 실제 동작 일치, 라벨 "후속" 명확화

### Phase 3. plan feature gate (후속)
- plan_limits 작업과 묶어 진행

---

## Returns Processing Phase 1 실행 로그 (Claude Code, frontend 레인)

### frontend-engineer (완료)
- `SmartDataGrid` 공통 "엑셀 다운로드"(CSV, UTF-8 BOM) 구현: `SmartDataGrid.export.ts`(신규), `SmartDataGrid.types.ts`(컬럼 export 옵션 + `exportFileName`), `SmartGridToolbar.tsx`(버튼), `SmartDataGrid.tsx`(연결).
- 컬럼 export 규칙: dataIndex/exportValue 있는 컬럼만, 액션/사진/버튼·작업상태(중복) 제외, 운송장/주문/상품코드/바코드/라벨번호는 `exportAsText`로 문자열 보존, 상태/검증/판정/출처는 한글 라벨 export, 원본 행 순서 유지, 기존 Ctrl+C 복사 정책 유지.
- `/returns/processing` 그리드에 `exportFileName="반품처리"` 적용 → 다운로드 버튼 노출.
- 판정 UI: generic `REFURB` 선택지 제거(`JUDGEMENT_OPTIONS`/`LABEL_REQUIRED_JUDGEMENTS`), 레거시 표시용 라벨 맵(`toJudgementLabel`)은 유지. `DEFECTIVE`는 backend 정합 선행 필요로 미노출.
- 검증: `npm run build` 통과(3103 modules). 처리완료 전 재고 미반영 로직 미변경.

### backend (Codex 담당, 미실행 — 분석만)
- 판정 enum 정합 필요: `schemas/returns.py`의 `judgement_status`는 enum 제약 없는 자유 문자열(validator는 strip+upper만). **`return_intake_repository.py:687`의 외부반출 후보 쿼리가 generic `("REFURB","SAMPLE","MANUFACTURER_RETURN")`로 필터** → 데이터가 `REFURB_A/B/C`면 누락되는 정합 버그. closing/outbound/inventory 분기의 판정 코드 기준 통일 필요.
- `DEFECTIVE`(신규 정본 코드): backend enum 처리 + 고객사 창고 라우팅(`return_warehouse_routes`)에 DEFECTIVE 경로가 있어야 frontend에서 선택·처리완료 가능.
- judge/manual/closing(재고반영) pytest 보강 필요.
- ⚠️ Claude Code는 backend 미수정. 위 항목은 Codex가 backend 계약 확정 후 처리하고, 그 뒤 frontend에서 DEFECTIVE 노출을 추가한다.
