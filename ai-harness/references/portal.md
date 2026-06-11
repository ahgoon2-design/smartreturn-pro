# Portal Reference

## Read First

- `docs/business/smartreturn-pro-auth-client-scope-api-policy.md`
- `docs/business/smartreturn-pro-menu-and-screen-map.md`
- `docs/skills/smartreturn-platform-business-architecture.md`
- `docs/business/agency-return-outsourcing-business-model.md`

## Rules

- 고객 포털과 내부 운영 화면은 같은 DB와 처리 루틴을 공유한다.
- 고객 사용자는 자기 client/client_unit 범위 내 자료만 접근한다.
- 내부 운영자는 권한에 따라 고객사/대리점 범위를 선택할 수 있다.
- 로그인 후 사용자 유형에 따라 내부 운영 화면 또는 고객 포털로 진입한다.
