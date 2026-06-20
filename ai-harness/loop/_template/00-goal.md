# 작업 목표 — <TASK-ID>
- 작업명:
- 실행대상: Claude Code 또는 Codex 중 정확히 하나
- 범위:
- 제외:
- 게이트: read-only / 문서 / 구현 / 검수 / 커밋 중 무엇 + SPEC 필요 여부
- 산출물:
- 정상 dirty 예상:
- 금지: secret/local/settings/API key/token/password/password_hash 출력 금지, `git add .`/`git add -A` 금지, 무단 commit/push 금지
- 중단: 같은 오류/명령 실패 3회 반복, 범위이탈, 예상 외 dirty 혼입
