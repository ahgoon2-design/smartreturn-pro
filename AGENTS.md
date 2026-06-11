# SmartReturn Pro 작업 기준

## 프로젝트 기본
- 프로젝트명: SmartReturn Pro
- 목적: 3PL 고객사 관리 통합 플랫폼. OMS, WMS, RETURN, 재고, 정산, 고객사 포털까지 확장 가능한 구조.
- 운영사: 동현물류
- 고객사/화주: `client`
- 내부 운영자와 고객사 사용자는 `role` 기준으로 구분한다.
- SmartReturn Pro는 CJ대리점 기반 이커머스 풀필먼트/반품 SaaS다. 기본 계층은 `platform_owner → agency_id → client_id → client_unit_id → warehouse_id`이며 Basic/Pro/Ultra 플랜에 따라 변하지 않는다.
- Basic/Pro/Ultra는 기능 사용 범위, 화면 잠금, 정산 항목, AI 보조 수준을 제어한다. 상위 플랜 기능은 locked/disabled로 보여줄 수 있지만 실제 실행은 backend feature gate로 차단한다.
- 세트·구성품은 제조 BOM이 아니라 이커머스 풀필먼트 세트/사은품/합포장 기준이다. 부품적출/부품교체는 1차 `MEMO_ONLY` 이력 중심으로 설계하고, 고가/청구/분쟁 부품만 재고관리로 확장한다.
- SmartReturn Pro의 최종 목표는 반품 전용 프로그램이 아니라 CJ대한통운 대리점과 함께 운영 가능한 OMS + WMS + Returns 통합 SaaS 플랫폼이다. 초기 MVP는 반품 자동화 중심으로 시작하지만, 신규 기능/DB/권한/메뉴/화면/정산/채널연동은 본사 관리자, 대리점 관리자, 고객사/셀러, 현장 작업자가 함께 사용하는 플랫폼 기준으로 설계한다. 데이터 계층은 처음부터 `agency_id` → `client_id` → `client_unit_id` 3단계 구조를 기본으로 하며, 핵심 운영 테이블은 대리점별 권한/통계/정산/이력 추적을 위해 `agency_id`를 직접 저장한다. 자세한 기준은 `docs/skills/smartreturn-platform-business-architecture.md`를 따른다.

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
- `AGENCY_ADMIN`
- `CLIENT_ADMIN`
- `CLIENT_USER`
- `READ_ONLY`

## 권한 원칙
- 고객사 선택 가능 여부는 `client_id` 유무가 아니라 `role` 기준이다.
- 내부 운영자는 고객사를 선택할 수 있다.
- 고객사 사용자는 자기 `client_id`로 고정된다.
- 모든 업무 데이터는 `client_id` scope를 반드시 지킨다.
- 대리점 SaaS 범위의 업무 데이터는 `agency_id` scope를 함께 지키며, 프론트 메뉴 숨김만으로 권한을 처리하지 않는다.
- 창고 업무는 `warehouse_id` scope를 반드시 지킨다.
- 내부 운영자에게 `client_id`가 있어도 고객사 사용자로 판단하지 않는다.

## 화면 원칙
- 화면은 업무 목적 1개만 가진다.
- 한 화면에 업로드, 조회, 이력, 처리, 판정, 정산, 설정을 섞지 않는다.
- 화면 먼저 만들지 말고, 공통 UI/DB/업무 기준을 먼저 만든다.
- 주요 업무 화면은 메뉴 이동 후에도 마지막 조회조건, 그리드 상태, 선택 row, 처리중 작업을 가능한 범위에서 기억한다.
- 좌측 메뉴 클릭으로 화면에 진입할 때는 스크롤 위치를 맨 위로 초기화해 화면 제목과 주요 작업 영역을 먼저 보여준다.
- 상단 작업 탭 복귀는 마지막 작업 상태를 복원할 수 있지만, 주요 업무 화면은 아래로 스크롤해도 화면 제목과 핵심 작업바가 사라지지 않는 sticky 구조를 우선한다.
- 저장, 처리완료, 마감, 재고반영 같은 확정 액션은 화면 상태 복원으로 중복 실행되지 않게 backend 상태를 기준으로 재검증한다.
- 작업 탭은 무한정 열지 않고 최근 5~7개로 제한하며, 오늘 작업/반품 처리 같은 핵심 화면은 고정 탭으로 둘 수 있다.
- 기존 SmartReturn 화면/DB/문서를 그대로 복사하지 않는다.
- 기존 SmartReturn은 참고자료일 뿐이며, Pro는 신규 기준으로 만든다.
- 샘플 디자인은 느낌만 흉내 내지 말고, 페이지 템플릿과 레이아웃 계약으로 강제한다.

## 공통 UI 원칙
- SmartReturn Pro 화면은 `docs/skills/smartreturn-screen-design-system.md` 기준을 따른다. 화면은 은은한 빛이 도는 현대적인 물류 운영 SaaS 디자인을 목표로 하며, 진한 원색 배경을 피하고 푸른빛/연두빛/주황빛 계열의 부드러운 상태 표현을 사용한다.
- AG Grid를 직접 쓰지 말고 `SmartDataGrid`/`SmartEditableDataGrid` 같은 공통 래퍼를 만든 뒤 사용한다.
- 엑셀 원본 preview는 `SmartExcelPreviewGrid` 기준으로 한다.
- 고객사/상품/창고/공통코드 선택은 화면별 Select가 아니라 `SmartLookupModal`/`SmartCommonCodeSelect` 기준으로 한다.
- 관리 화면은 `SmartPage`, `SmartPageHeader`, `SmartToolbar`, `SmartDataSection`, `SmartDataGrid`, `SmartModalShell` 계열을 먼저 조합한다.
- 작업자 스캔 화면은 `SmartScanPanel`, 큰 입력, 명확한 피드백, 하단/상세 action 영역 기준으로 만든다.
- 공통모달은 내용만 다르고 크기, footer, 버튼 위치, 입력 폭은 통일한다.
- 버튼이 아닌 정보 카드/패널은 버튼처럼 보이면 안 된다.
- 그리드가 화면의 주인공이어야 하며, 안내문과 카드가 그리드를 밀어내면 실패다.
- 1366x768 기준 핵심 입력, 그리드 첫 5행, 우측 정보패널, 하단 액션바가 보여야 한다.
- 현장 작업자 화면에는 내부 enum, DB 필드명, 개발자 용어를 노출하지 않는다.
- 한 화면에 같은 의미의 안내문을 반복하지 않는다.
- 좌측 메뉴 클릭은 scroll top, 작업 탭 복귀는 마지막 상태 복원이 가능하다.
- 긴 화면은 제목/핵심 작업바만 sticky로 두고 일반 카드/안내 카드는 sticky로 고정하지 않는다.
- 화면별 디자인 문제가 반복되면 개별 화면 CSS보다 공통 컴포넌트와 공통 `sr-*`/`smart-*` class를 먼저 보정한다.
- 작은 기능 아이콘은 PNG/JPG 이미지 파일이 아니라 `lucide-react` 또는 `@ant-design/icons` 같은 SVG 아이콘 라이브러리를 우선 사용한다.

## DB/업무 원장 원칙
- import job과 업무 테이블을 분리한다.
- `batch_id`는 원본 추적/이력 보조키이며 업무 처리 중심키가 아니다.
- `inventory_events`는 재고 원장, `current_inventory`는 현재고 요약이다.
- `scan_events`는 스캔 이벤트 로그이며 재고 원장이 아니다.
- Local Agent/로컬 클라이언트는 재고를 직접 변경하지 않는다.
- 운송장번호, 상품코드, 바코드는 비교용 정규화 기준을 둔다.
- SmartReturn Pro는 네이버클라우드 SaaS 운영을 전제로 설계한다. 초기 운영은 단일 Cloud DB for PostgreSQL + `client_id`/`client_unit_id` 기반 멀티테넌트 구조를 기본으로 하며, 고객사별 DB 분리는 초기에는 하지 않는다. 모든 고객사 API는 backend에서 client scope를 재검증한다. 사진/첨부/라벨/업로드 원본/export 파일은 DB에 직접 저장하지 않고 Object Storage에 저장한다. `channel_raw_events`, `import_job_rows`, `inventory_events`, `scan_events`, `audit_logs` 같은 대량 이력 테이블은 인덱스, 보관기간, 파티셔닝, 아카이브를 고려한다. 자세한 기준은 `docs/skills/naver-cloud-saas-architecture.md`를 따른다.

## 반품 핵심 원칙
- 반품 구글시트는 반품처리 원장이 아니라 업체 반품접수/회신 채널이다.
- CJ/택배 엑셀은 반품예정 자료다.
- 반품처리는 실제 창고 스캔/판정 원장이다.
- 반품접수자료와 반품예정자료는 매칭될 수도 있고 안 될 수도 있다.
- 매칭은 필수 관문이 아니라 참고/정확도 보조 기능이다.
- 현장 스캔 중 Google Sheets API를 직접 호출하지 않는다.
- 반품 예정자료의 상품정보는 후보/참고값이며, 실제 상품/수량/판정은 반품처리 작업에서 확정한다.
- 내부 반품입고예정 화면에는 구글시트 동기화, 업체 반품접수, 판정, 재고처리를 넣지 않는다.
- 반품 판정은 고객사별 판정 설정을 우선하며, 공통 고정 판정 버튼으로 운영 기준을 대체하지 않는다. 판정은 고객사별 판정표/체크리스트/과거 확정 이력 기반으로 추천할 수 있지만 최종 확정은 작업자가 한다.
- 판정별 `warehouse_id`는 필수다. `warehouse_id`가 확정되지 않은 반품은 처리완료 또는 재고반영으로 진행하지 않는다.
- 반품 판정/처리완료 즉시 `current_inventory`를 변경하지 않는다. 재고는 일마감, 월마감, 반출/폐기 확정 같은 후속 확정 단계에서 반영한다.
- 세부항목 없는 반품도 반품처리 화면에서 상품 스캔 또는 상품 검색/선택으로 처리 row를 생성해 처리할 수 있어야 한다.
- 조회형 작업 화면은 스캔 처리와 그리드 선택 처리를 모두 지원하되, 둘 다 같은 backend 검증, 권한, 이력 저장을 거쳐야 한다.
- 부품적출은 폐기 메모가 아니라 폐기 전 재사용 가능한 부품을 분리해 재고화하는 별도 작업 흐름이다.
- 세트상품/구성품 구조는 출고와 반품 모두에서 사용한다. 세트상품은 주문/판매 단위이고 구성품은 실제 피킹/검수/재고 단위다.
- AI는 자동판정기가 아니라 고객사별 판정 기준과 체크리스트를 기반으로 작업자를 돕는 판정지원 도우미다. 최종 판정은 작업자가 확정한다. 사진/영상 AI 자동판별은 1차 목표가 아니며 사진은 증빙/분쟁 대응 중심이다.
- 네이버/쿠팡/카페24/이지어드민/택배사 API 등 외부 채널 반품 자동수집은 화면별 개별 저장 로직으로 만들지 말고 `docs/skills/channel-return-auto-collection.md`를 따른다. 외부 채널 자료는 원본 이벤트 보존, canonical 정규화, 중복 upsert, 고객사/팀/상품/송장 매칭, 예외상태 분리, 반품예정자료 생성, 현장 운송장 스캔 연결 순서로 처리한다. `return_tracking_no`는 반품 현장 스캔 기준이고 `original_tracking_no`는 보조 조회 후보이다. 채널 역전송은 수집, 후보 생성, 관리자 확인 전송, 안전조건 자동전송 순서로 단계화한다.

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
- 신규 기능/DB/메뉴/권한/포털/정산/채널연동/대시보드/사업 지표 설계 작업:
  - `docs/skills/smartreturn-platform-business-architecture.md`
- 문서 작성 또는 closeout:
  - `docs/skills/document-style.md`
- backend API 작업:
  - `docs/skills/backend-api.md`
  - `docs/skills/git-security-check.md`
- frontend 작업:
  - `docs/skills/frontend-app.md`
  - `docs/skills/ui-design-system.md`
- 화면 디자인 또는 공통 UI 작업:
  - `docs/skills/smartreturn-screen-design-system.md`
  - `docs/skills/ui-design-system.md`
  - `docs/skills/frontend-app.md`
- grid/table/UI 작업:
  - `docs/skills/smartreturn-screen-design-system.md`
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
- 반품/재고/창고 설계 또는 기준정보 작업:
  - `docs/skills/return-client-unit-routing.md`
- 반품 판정/창고/재고반영/세부항목 없는 반품/폐기/부품적출 작업:
  - `docs/skills/return-operational-judgment-policy.md`
- 세트상품/구성품/BOM/출고·반품 연결 작업:
  - `docs/skills/set-product-component-bom.md`
- AI 판정도우미/판정 매뉴얼/판정 체크리스트 작업:
  - `docs/skills/return-judgment-ai-assistant.md`
- 네이버/쿠팡/카페24/이지어드민/택배사 API 반품 자동수집 작업:
  - `docs/skills/channel-return-auto-collection.md`
- DB/파일/사진/로그/배포/채널 자동수집/백업/보안/대량 이력 테이블 작업:
  - `docs/skills/naver-cloud-saas-architecture.md`

# Smart AI Dev Harness - Agent Constitution

> 이 섹션은 위의 SmartReturn Pro 작업 기준을 대체하지 않고 보완한다. 충돌 시 보안·중단 조건·문서 언어 규칙이 우선한다.

## 1. Purpose

Smart AI Dev Harness는 ChatGPT, Claude Code, Codex를 함께 사용하여 프로젝트를 설계, 구현, 검증, 보고까지 반복 수행하기 위한 AI 개발팀 운영 하네스다.

## 2. Project Root Rule

- 모든 경로는 현재 작업 중인 프로젝트폴더(`<PROJECT_ROOT>`)를 기준으로 해석한다.
- 지시문, agent 문서, reference 문서, 예시 명령에는 로컬 절대경로를 하드코딩하지 않는다.
- 특정 PC의 폴더명이나 드라이브 경로를 문서에 고정하지 않는다.
- Claude Code/Codex는 실행 시작 시 현재 working directory를 `<PROJECT_ROOT>`로 간주한다.
- 작업 전 `<PROJECT_ROOT>/AGENTS.md` 존재 여부를 확인한다.

## 3. Worker Compatibility

- 이 하네스는 Claude Code 전용이 아니다.
- Claude Code와 Codex를 모두 작업자로 사용할 수 있다.
- Claude Code는 `CLAUDE.md`와 `.claude/agents/`를 추가로 따른다.
- Codex는 `CODEX.md`를 추가로 따른다.
- 공통 업무 규칙과 역할 정의는 `ai-harness/` 아래에 둔다.

## 4. Agent Chaining Rule

- 모든 agent 파일을 한 번에 읽지 않는다.
- 현재 작업의 주관 agent를 먼저 선택한다.
- 주관 agent의 참조 문서와 handoff 대상만 단계적으로 읽는다.
- agent 간 인수인계는 `ai-harness/workflow/02-agent-report.md`에 기록한다.
- QA 완료 전에는 최종 완료 보고를 작성하지 않는다.

## 5. Safety Rules

- secret, env, key, token, local secret 파일은 읽거나 출력하지 않는다.
- 운영 데이터 삭제, destructive migration, 대량 cleanup은 사용자 명시 없이는 금지한다.
- 기존 공통 컴포넌트와 기존 API를 먼저 확인하고 중복 구현하지 않는다.
- 문서만 만들고 완료하지 않는다. 구현 작업은 테스트 가능한 상태까지 진행한다.
- 실행하지 못한 검증은 통과라고 쓰지 말고 "미실행"으로 보고한다.

## 6. Verification Rules

가능한 경우 작업 후 아래 검증을 실행한다.

- `git status --short`
- `git diff --check`
- 관련 backend test
- 관련 frontend build

검증 실패 시 원인 파일과 실패 명령을 보고한다.
