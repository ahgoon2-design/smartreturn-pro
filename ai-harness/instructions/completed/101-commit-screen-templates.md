# 101 - 화면 제작/검증/검수 템플릿 커밋(기준점)

## 목표
Claude/똘망이/Codex 템플릿 3종을 기준점으로 커밋. 이미 커밋되어 있으면 중복/빈 커밋 없이 상태만 보고.

## 담당 작업
- git staging/commit (문서만)

## 사전 조건
- 브랜치 smartreturn-pro

## 실행 범위
- 대상 3개만 staging:
  - `ai-harness/instructions/templates/claude-screen-build-template.md`
  - `ai-harness/instructions/templates/ddolmangi-screen-verify-template.md`
  - `ai-harness/instructions/templates/codex-review-template.md`
- 커밋 메시지: `docs(harness): add screen build verify review templates`
- 앱 코드 포함 금지. 변경 없으면 빈 커밋 금지(이미 커밋 확인만).

## 필수 확인 항목
- [ ] 3개 파일이 이미 커밋되었는지(git log/ls-files)
- [ ] 미커밋이면 3개만 staging 후 커밋
- [ ] 커밋 후 `git status --short`

## 중단 조건
- 대상 외 파일이 섞이면 중단.

## 보고 위치
- `ai-harness/reports/101-commit-screen-templates-report.md`

## 다음 지시문
- 완료/이미 커밋 확인 → `102-customer-portal-status-plan.md`
