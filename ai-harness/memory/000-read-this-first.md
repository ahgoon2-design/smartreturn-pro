# Read This First — SmartReturn Pro

이 저장소는 **SmartReturn Pro** (PostgreSQL)다.
구버전 SmartReturn(donghyun-logistics-platform, MySQL)과 혼동하지 않는다.

매 작업 전 읽기:
1. AGENTS.md
2. ai-harness/SOP-work-routine.md
3. ai-harness/handoff/latest-handoff.md

절대 규칙:
- 스펙 승인 전 구현 금지. 사용자 인수 전 커밋 금지.
- 구현자(클코)와 검수자(코덱)를 분리한다. 검수 중 코드 수정 금지.
- git add . 금지, 선별 stage. 커밋/push는 Codex가 사용자 승인 후.
- secret/.env/local.secret.json 출력·커밋 금지.
- 권한/테넌시: agency_id → client_id → client_unit_id → warehouse_id scope, 백엔드 강제.
- 반품처리 화면 구조: 백엔드/공통 코어 먼저 → 역할별 화면은 wrapper만. 권한·데이터 차단은 백엔드. `owner_agency_id`(소유권) ≠ `processing_agency_id`(처리 담당). 처리 의뢰 ≠ 고객 이관.
- 모든 경로는 <PROJECT_ROOT> 기준.

정체성: "똘망이"는 한 명이 아니라 클코·코덱·spec-writer를 게이트로 굴리는 운영 체계의 별칭이다.
