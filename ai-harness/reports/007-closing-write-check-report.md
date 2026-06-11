# 007 보고 - 반품 일마감/재고반영(쓰기) 검증

- 화면: `/returns/closing` + closing confirm API / ahgoon / 브랜치 smartreturn-pro
- 대상: `V3WRITE-RTN-002` (row_id=12, REFURB_A, client_id=8) 단건만

## 결과: 통과 (PASS)

| 항목 | 결과 |
|---|---|
| 후보 목록에 테스트 건 표시 | ✅ client_id=8 후보 = row#12 단건(REFURB_A, 재고 미반영) |
| 처리완료 전 자료 미혼입 | ✅ (후보는 COMPLETED만) |
| 대조 방식이 판정과 일치 | ✅ REFURB_A → 반품관리번호 보유(1:1 대조 대상) |
| 마감 확정 전 재고 미반영 | ✅ inv=false → |
| 마감 확정 성공 | ✅ result REFLECTED, inventory_event_id=3, warehouse_id=9 |
| 마감 후 재고반영 결과 명확 | ✅ inv=true, followup=INVENTORY_REFLECTED |
| 동일 건 중복 마감 방지 | ✅ 마감 후 closing 후보(client_id=8)=0건 |
| 다음 단계 외부반출 대상 | ✅ 외부반출 후보로 이월(외부반출상태 READY) |

## 안전 격리
- **row_ids=[12] 명시**로 단건만 확정(closing confirm은 row_ids 1:1). 기존 데이터/타 후보 무영향(client_id=8 한정, 후보 1건).

## 실제 버그 vs 데이터/위험
- 버그 없음. 처리완료 시 미반영 → 마감확정 시 반영 정책 정상.

## 수정 파일
- 없음.

## 실행 조작
- Playwright: /returns/closing 진입 → closing/candidates(client_id=8) 확인 → closing/confirm {row_ids:[12], client_id:8} → 마감 후 candidates/history/outbound 재확인. (모두 백엔드 절대주소 API)

## 다음
- 외부반출 대상 → `008-outbound-write-check.md` 진행.
