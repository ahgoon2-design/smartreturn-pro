# Workflow Reference

## Modes

- 플랜모드: 설계, 영향 분석, 구현 순서 작성
- 목표추진모드: 구현, 검증, 보고까지 진행
- 일반 지시: 작은 수정 또는 단순 확인

## Standard Flow

1. PM 판단
2. Architect 검토
3. 구현 agent 작업
4. UX/Grid 또는 Security 검수
5. QA 검증
6. Report 작성

## Reports

- 현재 목표: `ai-harness/workflow/00-current-goal.md`
- 작업 큐: `ai-harness/workflow/01-task-queue.md`
- agent 보고: `ai-harness/workflow/02-agent-report.md`
- test 보고: `ai-harness/workflow/03-test-report.md`
- 다음 지시: `ai-harness/workflow/04-next-instruction.md`

## Platform Branch Rule

- `main`은 SmartReturn 플랫폼 라인이다.
- `smartreturn-pro`는 SmartReturn Pro 플랫폼 라인이다.
- 두 브랜치는 단순 main/feature 관계가 아니라 서로 다른 플랫폼 라인이다.
- 현재 브랜치가 `smartreturn-pro`이면 SmartReturn Pro 규칙과 문서를 기준으로 작업한다.
- 사용자가 명시적으로 요청하지 않는 한 `smartreturn-pro`를 `main`에 병합·동기화하라고 제안하지 않는다.
- 브랜치 전략을 권고하기 전에 항상 현재 브랜치를 먼저 확인한다.
