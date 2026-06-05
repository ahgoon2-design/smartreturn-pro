# SmartReturn Pro Codex Skill Guides

## 목적

`/docs/skills`는 Codex가 SmartReturn Pro 작업을 반복 수행할 때 작업 유형별로 추가로 읽는 보조 기준 문서 모음이다.

이 문서들은 `AGENTS.md`를 대체하지 않는다. `AGENTS.md`는 항상 최우선 기준이며, `/docs/skills` 문서는 세부 작업 방식과 반복 체크리스트를 보완한다.

`AGENTS.md`와 `/docs/skills` 문서 내용이 충돌하면 `AGENTS.md`의 보안 규칙, 중단 조건, 문서 언어 규칙이 우선한다.

## 문서 목록

| 문서 | 언제 읽는가 | 역할 |
| --- | --- | --- |
| `smartreturn-pro-workflow.md` | 모든 작업 시작 전 | 저장소 확인, 진행 모드, 중단 조건, 완료 보고 기준을 정리한다. |
| `git-security-check.md` | 커밋, push, 파일 변경 작업 전 | 민감 파일 staged/tracked 금지와 커밋 전 보안 체크를 정리한다. |
| `document-style.md` | 문서 작성, closeout, 인덱스 수정 시 | 한글 문서 작성 기준과 closeout 문서 구성을 정리한다. |
| `backend-api.md` | FastAPI backend API 작업 시 | ApiResult, 인증/권한, client scope, 테스트 기준을 정리한다. |
| `frontend-app.md` | React/Vite/TypeScript frontend 작업 시 | 앱 구조, 라우팅, 인증 context, API client 기준을 정리한다. |
| `ui-design-system.md` | 화면 디자인, 공통 UI 작업 시 | Ant Design 기반 공통 UI와 화면 밀도 기준을 정리한다. |
| `ui-grid.md` | grid/table/preview 화면 작업 시 | SmartDataGrid wrapper, row 순서, 상태 표시 기준을 정리한다. |
| `worker-screen-ux.md` | 스캔/검수/작업자 화면 작업 시 | 정확도, 속도, 자동화 중심의 작업자 UX 기준을 정리한다. |
| `import-preview.md` | import preview, paste rows, validation 화면 작업 시 | import job 생성, rows 저장, validate, rows/errors 표시 계약을 정리한다. |
| `return-client-unit-routing.md` | 반품/재고/창고/기준정보 작업 시 | 고객사 운영단위/팀 기준 반품·창고·재고 라우팅 규칙을 정리한다. |

## 사용 원칙

- 작업 시작 전 `AGENTS.md`를 먼저 읽는다.
- 작업 유형이 정해지면 위 표의 관련 문서를 추가로 읽는다.
- 문서가 여러 개 해당되면 공통 문서부터 읽고 도메인 문서를 읽는다.
- 기존 SmartReturn 기준과 SmartReturn Pro 기준이 다르면 SmartReturn Pro 기준을 우선한다.
- 반품 접수, 반품처리, 창고설정, 재고반영, 기준정보 작업은 `return-client-unit-routing.md`를 함께 읽는다.
- 실제 secret, token, password, password_hash 값은 어떤 문서에도 쓰지 않는다.
