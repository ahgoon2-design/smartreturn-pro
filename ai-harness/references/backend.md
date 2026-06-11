# Backend Reference

## Read First

- `docs/skills/backend-api.md`
- `docs/skills/git-security-check.md`
- `docs/skills/naver-cloud-saas-architecture.md`
- `docs/business/smartreturn-pro-return-api-policy.md`
- `docs/business/smartreturn-pro-auth-client-scope-api-policy.md`
- `docs/db/smartreturn-pro-p0-table-columns.md`
- `docs/db/smartreturn-pro-table-priority.md`

## Rules

- API 변경 전 기존 endpoint와 service layer를 검색한다.
- 권한 scope, agency/client/client_unit 범위를 확인한다.
- business code/status를 하드코딩하지 않는다.
- 판정 코드 정본: `GOOD/REFURB_A/REFURB_B/REFURB_C/MANUFACTURER_RETURN/SAMPLE/HOLD/DISPOSAL/DEFECTIVE`. generic `REFURB`는 신규 저장 기준 아님(레거시 호환만).
- `DEFECTIVE`(불량)는 판매가능 재고/외부반출 자동후보에 넣지 않는다. 창고 라우팅 설정이 있어야 처리완료 가능(default 창고 하드코딩 금지). 정책 상세는 `docs/business/return-processing-workflow-ux-design.md`.
- 가능한 경우 관련 backend test를 추가 또는 실행한다.
