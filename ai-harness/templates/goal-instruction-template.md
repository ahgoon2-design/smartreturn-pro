# Goal Instruction Template

실행 대상: Claude Code 또는 Codex 중 정확히 하나
모드: 플랜모드 / 목표추진모드 / 일반 지시
이유:

현재 작업 중인 프로젝트폴더를 `<PROJECT_ROOT>`로 간주한다.

1. `<PROJECT_ROOT>/AGENTS.md`를 먼저 읽고 지시를 따른다.
2. Claude Code로 실행 중이면 `<PROJECT_ROOT>/CLAUDE.md`를 읽는다.
3. Codex로 실행 중이면 `<PROJECT_ROOT>/CODEX.md`를 읽는다.
4. 모든 경로는 `<PROJECT_ROOT>` 기준 상대경로로 처리한다.
5. 로컬 절대경로를 하드코딩하지 않는다.
6. Karpathy 보강분 A~D 적용 (AGENTS.md 참조)

## 목표

작성 예정

## 작업 범위

작성 예정

## 정상 dirty 예상

작성 예정

## 금지

- secret/env/local secret 파일 읽기/출력 금지
- API key/token/password/password_hash 값 출력 금지
- 사용자 명시 없는 destructive 작업 금지
- 기존 공통 구조 확인 없이 중복 구현 금지
- `git add .`, `git add -A`, 무단 commit/push 금지
- 실행대상을 "Claude Code 또는 Codex"처럼 열린 선택지로 남기지 않는다. 병렬 작업은 `joint-worker-instruction-template.md`로 별도 카드화한다.

## 검증

- git status --short
- git diff --check
- 관련 test/build

## 중단 조건

- 같은 오류 또는 같은 명령 실패 3회 반복
- 작업 범위 이탈
- 예상 외 dirty 혼입
- secret/local/settings 내용을 봐야 진행 가능한 상황

## 똘고리 판정

- 똘고리 통과 / 보완 후 통과 / 중단 / SPEC 요구 / 범위분리 요구 중 하나
