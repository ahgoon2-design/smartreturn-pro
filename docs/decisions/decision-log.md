# Decision Log — SmartReturn Pro
## D-001 [확정] 판정 enum 정본
- GOOD / REFURB_A / REFURB_B / REFURB_C / SAMPLE / MANUFACTURER_RETURN / HOLD / DISPOSAL / DEFECTIVE.
- generic REFURB: 신규 선택지 아님(FE 제거), 외부반출 후보·조회는 레거시 호환만.
## D-002 [확정] DEFECTIVE(불량) 처리 정책
- 판매가능 재고 아님 / 외부반출 자동후보 아님 / 고객사 창고 라우팅 있어야 처리완료(없으면 차단, default 창고 하드코딩 금지) / 처리완료 시 재고 미반영 / 라벨(반품관리번호) 대상. 불량 전용 재고화는 후속 TODO.
## D-003 [확정] 폐기/제조사반품 일마감 재고반영 — 유지
- 결정: DISPOSAL/MANUFACTURER_RETURN을 일마감 재고반영에 포함(유지). 코드 변경 없음.
- 근거: current_inventory가 stock_status별 별도 행(UniqueConstraint: client_id+warehouse_id+location_id+product_id+stock_status, models/inventory.py:48-55). stock_status=판정값으로 적재(service.py:1704)되어 판매가능(GOOD)과 합산되지 않고 분리됨. SPEC-001의 "판매가능 재고 혼입" 우려는 구조상 발생하지 않음.
- 외부반출: 제조사반품=자동후보 포함 / 폐기=별도 폐기 followup 경로(외부반출 후보 아님). 현행 유지.
- 날짜: 2026-06-15
