# 010 보고 - GOOD 쓰기 흐름(처리완료→일마감→양품재고) 검증

- 대상: `V3WRITE-RTN-001` (task#11), 판정 GOOD, client V3WRITE-CLIENT(id=8), product V3WRITE-P001(pid=4), warehouse V3WRITE-WH(id=9)
- 실행: Claude Code(브라우저 + 백엔드 절대주소 API) / ahgoon / 브랜치 smartreturn-pro

## 결과: 통과 (PASS) — 버그 없음

| 목표 항목 | 결과 |
|---|---|
| 처리완료 성공 | ✅ `/returns/processing`에서 단건 처리완료(status COMPLETED, judge GOOD) |
| 처리완료 직후 재고 미반영 | ✅ inv=false, followup=JUDGED, rmn=null(GOOD은 라벨/반품관리번호 없음) |
| GOOD 상품바코드 수량대조 흐름 | ✅ GOOD은 반품관리번호 미부여 → 바코드 수량대조 대상(마감 후보로 노출) |
| 일마감 성공 | ✅ row_ids=[11] 단건 마감 → REFLECTED, inventory_event_id=4, warehouse_id=9 |
| inventory_event 생성 | ✅ event#4 |
| current_inventory 증가 | ✅ wh9/pid4 **stock_status=GOOD, qty=1** 신규 반영 (기존 REFURB_A qty1과 stock_status로 분리) |
| 마감 후 재고반영 상태 | ✅ inv=true, followup=INVENTORY_REFLECTED, 마감 후 closing 후보에서 제외 |
| GOOD 외부반출 후보 미포함 | ✅ outbound candidates(client_id=8)에 V3WRITE-RTN-001 없음 |

## 재고 상세(마감 후 current_inventory, client_id=8)
- {wh9, pid4, stock_status=GOOD, qty=1}  (inventory_id=4, 이번 GOOD 마감)
- {wh9, pid4, stock_status=REFURB_A, qty=1} (inventory_id=3, 007 REFURB_A 마감)
→ 동일 창고/상품이라도 **stock_status로 분리 집계**(양품/리퍼 구분). 중복 행 아님.

## 실패/확인불가
- 없음.

## 실제 버그 vs 데이터 부족 vs 위험 회피
- **버그 0건.** (초기 "동일 키 2행" 관찰은 stock_status=GOOD vs REFURB_A 분리로 정상 확인.)
- 참고(경미): closing row_result 메시지가 GOOD/REFURB 모두 "정상재고에 반영했습니다"로 동일 문구지만, 실제 stock_status는 정확히 구분됨(문구만 일반적 — 기능 영향 없음, 보고만).
- 위험 회피: 처리완료/마감 모두 V3WRITE-RTN-001 단건(row_ids=[11], client_id=8)만 대상. 기존 데이터 무영향.

## 수정 파일
- 없음(앱 코드 변경 0).

## 실행한 브라우저 조작/테스트 명령
- Playwright UI: /returns/processing?tracking_no=V3WRITE-RTN-001 → 선택 상품 확인 → 양품 → 처리완료.
- 백엔드 절대주소 API: closing/candidates·closing/confirm(row_ids=[11])·inventory/current·history·external-outbound/candidates 조회.

## 커밋 필요 여부
- 보고서 1개(010). **사용자 승인 전 커밋하지 않음.** push 없음. main 병합/동기화 제안 없음.
