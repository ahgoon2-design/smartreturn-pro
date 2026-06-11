# Next Instruction

> DEFECTIVE 정책 확정 + frontend "불량" 노출 완료. 남은 후속 작업.

## 후속 1 — 엑셀 다운로드 확대 (Claude Code, frontend)
- `exportFileName`을 다른 조회형 화면(반품 이력/마감 후보/외부반출 후보/보류/폐기 후보)에 적용.
- 각 화면 그리드 id류 컬럼에 `exportAsText`, 상태/판정 컬럼에 `exportValue`(한글 라벨) 부여.
- `npm run build`.

## 후속 2 — 불량(DEFECTIVE) 재고화 정책 (보류, 정책 확정 후)
- 불량 전용 재고 타입/창고 흐름(불량/클레임/비가용 재고) 설계가 필요할 때 별도 작업으로 진행.
- 확정 전까지 `INVENTORY_REFLECTABLE_JUDGEMENT_STATUSES`/`EXTERNAL_OUTBOUND_JUDGEMENT_STATUSES`에 DEFECTIVE를 넣지 않는다.

## 후속 3 — 사용자 브라우저 검증
- REFURB_A/B/C 외부반출 후보 노출.
- DEFECTIVE: 고객사 DEFECTIVE 창고 라우팅 설정 후 처리완료 확인(설정 없으면 차단).

## 공통 규칙
- 현재 브랜치 `smartreturn-pro`(SmartReturn Pro 라인), `main` 병합/동기화 제안 금지.
- 처리완료 시 재고 즉시 반영 금지(일마감/반출 확정에서만), DEFECTIVE는 양품재고/외부반출 자동후보 금지.
- secret/env/local secret 읽기·출력 금지, default 창고 하드코딩 금지.
