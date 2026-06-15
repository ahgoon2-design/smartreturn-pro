# 똘망이 작업 루틴 (SOP) — SmartReturn Pro

> 새 작업 시작 시 항상 이 순서. "출근 → 퇴근" 체크리스트.
> 루프엔지니어링 이론 설명은 ai-harness/references/loop-engineering.md 참조.
> 정체성/역할/원칙 상세는 ai-harness/memory/000-read-this-first.md.

## 1. 출근 — 상태 파악 (작업 시작 시 반드시)
- [ ] AGENTS.md 읽기
- [ ] ai-harness/memory/000-read-this-first.md 읽기
- [ ] ai-harness/handoff/latest-handoff.md 읽기
- [ ] ai-harness/loops/loop-state.md 읽기 (현재 루프 어디까지)
- [ ] ai-harness/workflow/01-task-queue.md 읽기
- [ ] git status / git branch --show-current

## 2. 할 일 선택
- [ ] task-queue Pending에서 우선순위 1개
- [ ] 작업 모드 판단 (단일 / Agent Team / 일반)
- [ ] 주관 agent 선택 (CLAUDE.md 기준 — 현재 Pro 운영은 spec-writer만, 나머지는 필요 시 추가)

## 3. 작업 — 게이트대로
신규 화면/기능이면 5게이트:
1. spec-writer 슬라이스 스펙 (docs/specs/SPEC-NNN-*.md)
2. 사용자 스펙 승인 (게이트②)
3. Claude Code 구현 + 빌드 보고서 (docs/reports/SPEC-NNN-build.md)
4. Codex 검증 + 검증 보고서 (docs/reports/SPEC-NNN-verify.md)
5. 사용자 화면 인수·커밋 승인 (게이트⑤)

작은 수정/문서는 게이트 없이, 단 커밋은 항상 사용자 승인 후 Codex.

## 4. 검증 (구현이 있었으면)
- [ ] git diff --check
- [ ] 관련 backend test
- [ ] npm.cmd run build (frontend 변경 시)
- [ ] 브라우저 확인 (1366×768)

## 5. 퇴근 — 일지 갱신 (작업 종료 시 반드시)
- [ ] ai-harness/loops/loop-state.md 갱신
- [ ] ai-harness/handoff/latest-handoff.md 갱신 (누적 금지)
- [ ] ai-harness/workflow/01-task-queue.md 갱신
- [ ] ai-harness/workflow/00-current-goal.md 갱신
- [ ] 결과 보고서 작성

## 절대 규칙
- git add . 금지, 선별 stage
- 커밋/push는 Codex가 사용자 승인 후
- secret / backend/local.secret.json 출력 금지
- 운영 데이터 사용 금지
- 기존 SUPER_ADMIN/내부 운영자 흐름 안 깨뜨림
- 모든 경로는 <PROJECT_ROOT> 기준
