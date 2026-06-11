# Goal Instruction Template

실행 대상: Claude Code / Codex / Claude Code + Codex
모드: 플랜모드 / 목표추진모드 / 일반 지시
이유:

현재 작업 중인 프로젝트폴더를 `<PROJECT_ROOT>`로 간주한다.

1. `<PROJECT_ROOT>/AGENTS.md`를 먼저 읽고 지시를 따른다.
2. Claude Code로 실행 중이면 `<PROJECT_ROOT>/CLAUDE.md`를 읽는다.
3. Codex로 실행 중이면 `<PROJECT_ROOT>/CODEX.md`를 읽는다.
4. 모든 경로는 `<PROJECT_ROOT>` 기준 상대경로로 처리한다.
5. 로컬 절대경로를 하드코딩하지 않는다.

## 목표

작성 예정

## 작업 범위

작성 예정

## 금지

- secret/env/local secret 파일 읽기/출력 금지
- 사용자 명시 없는 destructive 작업 금지
- 기존 공통 구조 확인 없이 중복 구현 금지

## 검증

- git status --short
- git diff --check
- 관련 test/build
