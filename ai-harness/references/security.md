# Security Reference

## Read First

- `docs/skills/git-security-check.md`
- `docs/business/smartreturn-pro-auth-password-policy.md`
- `docs/business/smartreturn-pro-auth-client-scope-api-policy.md`

## Forbidden

- secret/env/key/token/local secret 파일 읽기 또는 출력
- 운영 데이터 삭제
- 사용자 명시 없는 destructive migration
- 비밀번호/토큰 로그 출력
- 금지 파일 git 포함

## Required

- 민감 파일은 존재 여부만 확인하고 내용 출력 금지
- 위험 작업은 중단하고 보고
