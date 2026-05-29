# SmartReturn Pro 작업 기준

## 프로젝트 기본
- 프로젝트명: SmartReturn Pro
- 목적: 3PL 고객사 관리 통합 플랫폼. OMS, WMS, RETURN, 재고, 정산, 고객사 포털까지 확장 가능한 구조.
- 운영사: 동현물류
- 고객사/화주: `client`
- 내부 운영자와 고객사 사용자는 `role` 기준으로 구분한다.

## 문서 작성 언어 규칙
- SmartReturn Pro의 모든 기준 문서, 설계 문서, 운영 문서, Codex 지시문으로 생성되는 문서는 한글로 작성한다.
- 파일명은 영어/케밥케이스를 사용할 수 있다.
- 코드 식별자, DB 컬럼명, API path, enum 값, 함수명은 영어를 유지한다.
- 본문 설명, 정책, 판단 기준, 주의사항, 완료 보고는 한글로 작성한다.
- 영어 문서나 영어 요약본은 사용자가 별도로 요청할 때만 만든다.
- 기존 참고 문서에 영어가 섞여 있어도 SmartReturn Pro 신규 문서는 한글 기준으로 재작성한다.

## 표준 role
- `SUPER_ADMIN`
- `INTERNAL_ADMIN`
- `INTERNAL_WORKER`
- `CLIENT_ADMIN`
- `CLIENT_USER`
- `READ_ONLY`

## 권한 원칙
- 고객사 선택 가능 여부는 `client_id` 유무가 아니라 `role` 기준이다.
- 내부 운영자는 고객사를 선택할 수 있다.
- 고객사 사용자는 자기 `client_id`로 고정된다.
- 모든 업무 데이터는 `client_id` scope를 반드시 지킨다.
- 창고 업무는 `warehouse_id` scope를 반드시 지킨다.
- 내부 운영자에게 `client_id`가 있어도 고객사 사용자로 판단하지 않는다.

## 화면 원칙
- 화면은 업무 목적 1개만 가진다.
- 한 화면에 업로드, 조회, 이력, 처리, 판정, 정산, 설정을 섞지 않는다.
- 화면 먼저 만들지 말고, 공통 UI/DB/업무 기준을 먼저 만든다.
- 기존 SmartReturn 화면/DB/문서를 그대로 복사하지 않는다.
- 기존 SmartReturn은 참고자료일 뿐이며, Pro는 신규 기준으로 만든다.
- 샘플 디자인은 느낌만 흉내 내지 말고, 페이지 템플릿과 레이아웃 계약으로 강제한다.

## 공통 UI 원칙
- AG Grid를 직접 쓰지 말고 `SmartDataGrid`/`SmartEditableDataGrid` 같은 공통 래퍼를 만든 뒤 사용한다.
- 엑셀 원본 preview는 `SmartExcelPreviewGrid` 기준으로 한다.
- 고객사/상품/창고/공통코드 선택은 화면별 Select가 아니라 `SmartLookupModal`/`SmartCommonCodeSelect` 기준으로 한다.
- 공통모달은 내용만 다르고 크기, footer, 버튼 위치, 입력 폭은 통일한다.
- 버튼이 아닌 정보 카드/패널은 버튼처럼 보이면 안 된다.
- 그리드가 화면의 주인공이어야 하며, 안내문과 카드가 그리드를 밀어내면 실패다.
- 1366x768 기준 핵심 입력, 그리드 첫 5행, 우측 정보패널, 하단 액션바가 보여야 한다.

## DB/업무 원장 원칙
- import job과 업무 테이블을 분리한다.
- `batch_id`는 원본 추적/이력 보조키이며 업무 처리 중심키가 아니다.
- `inventory_events`는 재고 원장, `current_inventory`는 현재고 요약이다.
- `scan_events`는 스캔 이벤트 로그이며 재고 원장이 아니다.
- Local Agent/로컬 클라이언트는 재고를 직접 변경하지 않는다.
- 운송장번호, 상품코드, 바코드는 비교용 정규화 기준을 둔다.

## 반품 핵심 원칙
- 반품 구글시트는 반품처리 원장이 아니라 업체 반품접수/회신 채널이다.
- CJ/택배 엑셀은 반품예정 자료다.
- 반품처리는 실제 창고 스캔/판정 원장이다.
- 반품접수자료와 반품예정자료는 매칭될 수도 있고 안 될 수도 있다.
- 매칭은 필수 관문이 아니라 참고/정확도 보조 기능이다.
- 현장 스캔 중 Google Sheets API를 직접 호출하지 않는다.
- 반품 예정자료의 상품정보는 후보/참고값이며, 실제 상품/수량/판정은 반품처리 작업에서 확정한다.
- 내부 반품입고예정 화면에는 구글시트 동기화, 업체 반품접수, 판정, 재고처리를 넣지 않는다.

## 작업 원칙
- 신규 기능 구현 전 반드시 관련 `docs` 문서를 먼저 읽는다.
- 커밋 전 `config.json`, `logs`, `outputs`, `dist`, `build`, `zip`, `exe`, `__pycache__`, `.env`, 민감정보가 포함되지 않았는지 확인한다.
- Codex 완료 보고에는 변경 파일, 테스트/검증 결과, 미실행 항목, 위험요소를 포함한다.
- 커밋은 사용자가 명시적으로 지시하기 전에는 하지 않는다.

## `/docs/skills` 보조 기준
- 모든 작업은 이 `AGENTS.md`를 먼저 읽고, 작업 유형에 따라 `/docs/skills/*.md`를 추가로 읽는다.
- `/docs/skills` 문서는 이 파일을 대체하지 않고 작업별 세부 기준을 보완한다.
- `/docs/skills` 문서와 `AGENTS.md`가 충돌하면 `AGENTS.md`의 보안, 중단 조건, 문서 언어 규칙이 항상 우선한다.
- 모든 작업 공통:
  - `docs/skills/smartreturn-pro-workflow.md`
  - `docs/skills/git-security-check.md`
- 문서 작성 또는 closeout:
  - `docs/skills/document-style.md`
- backend API 작업:
  - `docs/skills/backend-api.md`
  - `docs/skills/git-security-check.md`
- frontend 작업:
  - `docs/skills/frontend-app.md`
  - `docs/skills/ui-design-system.md`
- 화면 디자인 또는 공통 UI 작업:
  - `docs/skills/ui-design-system.md`
  - `docs/skills/frontend-app.md`
- grid/table/UI 작업:
  - `docs/skills/ui-grid.md`
  - `docs/skills/ui-design-system.md`
  - `docs/skills/frontend-app.md`
- 작업자용 스캔 화면 작업:
  - `docs/skills/worker-screen-ux.md`
  - `docs/skills/ui-design-system.md`
  - `docs/skills/ui-grid.md`
- import preview 작업:
  - `docs/skills/import-preview.md`
  - `docs/skills/frontend-app.md`
  - `docs/skills/ui-grid.md`
  - `docs/skills/ui-design-system.md`
