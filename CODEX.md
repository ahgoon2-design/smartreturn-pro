# Codex Operating Guide

## 1. Startup

1. `<PROJECT_ROOT>/AGENTS.md`를 읽는다.
2. `<PROJECT_ROOT>/CODEX.md`를 읽는다.
3. 모든 경로는 `<PROJECT_ROOT>` 기준 상대경로로 처리한다.
4. `ai-harness/references`에서 필요한 참조 인덱스만 읽는다.
5. 작업 결과는 `ai-harness/workflow/02-agent-report.md`에 기록한다.

## 2. Codex Role

Codex는 명확한 코드 수정, backend/API/service/test, 작은 버그 수정, 테스트 실패 원인 분석에 우선 사용한다.

## 3. Collaboration Rule

Claude Code와 공동 작업할 경우:

- Codex는 backend/API/service/test 중심으로 작업한다.
- Claude Code는 frontend/UI/UX/Grid 중심으로 작업한다.
- 서로 상대 영역을 읽을 수는 있지만, 사용자 지시 없이 임의 수정하지 않는다.
- 보고서는 `ai-harness/workflow/02-agent-report.md`에 작업자별 섹션으로 나눈다.
