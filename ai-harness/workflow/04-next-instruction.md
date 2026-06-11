# Next Instruction

> Backend Phase 1(외부반출 generic REFURB 필터 버그 수정 + DEFECTIVE 지원 + 테스트)은 Claude Code(backend-engineer 체인)로 완료. 아래는 남은 후속 작업이다.

## 선결 정책 결정 (사용자 확정 필요)
- **DEFECTIVE 후속 흐름**: 일마감 재고반영(`INVENTORY_REFLECTABLE_JUDGEMENT_STATUSES`) 및 외부반출 자동후보(`EXTERNAL_OUTBOUND_JUDGEMENT_STATUSES`)에 DEFECTIVE를 포함할지. 현재는 미포함(판정/창고/라벨까지만). 정책 확정 시 해당 세트에 추가 + 테스트.

## 후속 1 — frontend DEFECTIVE 노출 (Claude Code)
- backend가 DEFECTIVE를 지원하므로(`ALLOWED` + 창고 라우팅 허용), `ReturnProcessingWorkspacePage.tsx` `JUDGEMENT_OPTIONS`에 `{ value: "DEFECTIVE", label: "불량" }` 추가.
- 라벨/창고 안내 문구 정합. 고객사에 DEFECTIVE 창고 라우팅이 없으면 처리완료 차단(정상)임을 화면 안내.
- `npm run build`.

## 후속 2 — 엑셀 다운로드 확대 (Claude Code)
- `exportFileName`을 다른 조회형 화면(반품 이력/마감·반출·보류·폐기 후보)에도 적용.
- 각 화면 그리드의 id류 컬럼에 `exportAsText`, 상태/판정 컬럼에 `exportValue`(한글 라벨) 부여.

## 후속 3 — DEFECTIVE 정책 반영 (backend, 정책 확정 후)
- 정책에 따라 `INVENTORY_REFLECTABLE_JUDGEMENT_STATUSES`/`EXTERNAL_OUTBOUND_JUDGEMENT_STATUSES`에 DEFECTIVE 추가 + 일마감/외부반출 테스트 보강.

## 공통 규칙
- 현재 브랜치 `smartreturn-pro`(SmartReturn Pro 라인) 기준, `main` 병합/동기화 제안 금지.
- 처리완료 시 재고 즉시 반영 금지(일마감/반출 확정에서만).
- secret/env/local secret 읽기·출력 금지.
