# Common Reference

## Core Rules

- 모든 경로는 `<PROJECT_ROOT>` 기준 상대경로로 처리한다.
- 로컬 절대경로를 하드코딩하지 않는다.
- secret/env/key/local secret 파일을 읽거나 출력하지 않는다.
- 기존 공통 컴포넌트와 기존 API를 먼저 검색한다.
- 새 구조를 만들기 전에 기존 구조 재사용 가능성을 검토한다.
- 운영 데이터 삭제, destructive migration, 대량 cleanup은 사용자 명시 없이는 금지한다.
- 변경 후 가능한 검증을 실행하고 결과를 보고한다.

## Project Principles

- 고객 포털과 내부 운영 화면은 가능한 한 같은 DB와 같은 처리 루틴을 공유한다.
- 권한/로그인에 따라 보이는 화면과 접근 범위만 달라진다.
- agency_id → client_id → client_unit_id 범위를 고려한다.
- 조회형 화면은 loading state, 복사 가능성, 엑셀 다운로드 정책을 고려한다.

## Read First

- `AGENTS.md`
- `CLAUDE.md`
- `docs/smartreturn-pro-core-principles.md`
- `docs/smartreturn-pro-doc-index.md`
- `docs/skills/smartreturn-pro-workflow.md`
