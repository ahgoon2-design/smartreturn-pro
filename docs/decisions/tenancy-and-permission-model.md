# 테넌시·권한 모델 (북극성) — SmartReturn Pro
> 권한/격리/인증 작업 전 반드시 읽는다.

- 계층: agency_id → client_id → client_unit_id → warehouse_id
- 동현물류 = 운영사. 고객사 = 동현물류가 관리하는 화주/업체.
- 내부 운영자(SUPER_ADMIN/INTERNAL_ADMIN/INTERNAL_WORKER)는 고객사 선택 가능.
- 고객 사용자(CLIENT_ADMIN/CLIENT_USER/READ_ONLY)는 자기 client_id로 고정.
- 고객 선택 가능 여부는 client_id 유무가 아니라 role 기준으로 판단한다.
- 프론트가 보낸 client_id를 권한 기준으로 신뢰하지 않는다. 백엔드 세션 scope가 source of truth.
- 고객 포털에는 내부 처리/판정/일마감/외부반출/재고반영 액션을 노출하지 않는다. 백엔드에서 강제.
- 상품/재고/입고/출고/반품/정산 화면은 client_id + warehouse_id 범위 검증 필수.
