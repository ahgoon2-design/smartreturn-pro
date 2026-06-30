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

## 반품처리 화면/권한 구조 원칙
- 반품처리 백엔드 흐름과 API를 먼저 단단하게 만든다. 화면은 그 다음이다.
- 현장용 반품처리 화면 1개를 먼저 제대로 완성한다. 대리점/동현/고객사/처리센터 화면을 처음부터 따로 크게 만들지 않는다.
- 기준 반품처리 화면을 기반으로 공통 컴포넌트를 뽑고, 역할별 차이는 wrapper/껍데기 수준(조회 필터, 버튼 노출 여부, 수정 가능 범위, 화면 문구)으로 제한한다. 같은 기능을 복붙 화면으로 늘리지 않는다.
- 권한과 데이터 차단은 프론트가 아니라 백엔드 API에서 강제한다. 프론트 껍데기는 헷갈림 방지용 UX일 뿐이다.
- 고객 소유권(`owner_agency_id`)과 처리 담당(`processing_agency_id`)을 반드시 분리한다. 처리 의뢰는 반품 업무만 다른 처리 주체에게 배정하는 절차이며, 고객 이관(고객 소유권 변경)과 혼동하지 않는다.
- 기본 반품처리 흐름은 하나로 유지한다: 접수/수집 → 입고 → 검수 → 판정 → 처리완료 → 일마감 → 재고반영 → 정산.

## 작업 원칙
- 신규 기능 구현 전 반드시 관련 `docs` 문서를 먼저 읽는다.
- 커밋 전 `config.json`, `logs`, `outputs`, `dist`, `build`, `zip`, `exe`, `__pycache__`, `.env`, 민감정보가 포함되지 않았는지 확인한다.
- Codex 완료 보고에는 변경 파일, 테스트/검증 결과, 미실행 항목, 위험요소를 포함한다.
- 커밋은 사용자가 명시적으로 지시하기 전에는 하지 않는다.

## AI 작업 기본 원칙

모든 AI 작업자(Claude Code, Codex, Claude)에게 공통 적용한다.

1. **작업 전 판단** — 가정하지 않는다. 불확실하면 묻거나 중단 보고한다. 여러 해석이 가능하면 선택지를 제시한다. 더 단순한 방법이 있으면 제안한다.
2. **단순 우선** — 요청받지 않은 기능을 추가하지 않는다. 한 번만 쓰는 추상화를 만들지 않는다. 과설계 금지. 더 짧고 명확하게 해결 가능하면 단순화한다.
3. **최소 수정** — 필요한 파일만 수정한다. 인접 코드·주석·포맷을 임의로 개선하지 않는다. 기존 죽은 코드는 삭제하지 말고 보고만 한다. 내가 만든 불필요 코드만 정리한다.
4. **검증 기준** — 작업 전 성공 기준을 확인한다. 수정 후 검증한다. 검증하지 못한 항목을 통과라고 쓰지 않는다. 실패하면 원인과 다음 조치를 짧게 보고한다.

## 슬라이스 스펙 우선 원칙 (똘망이 게이트)

### 실행 주체 기본 배정 (2026-06-30 갱신, 신규 작업부터 적용)
- 이 시점 이후 신규 작업의 기본 배정: 실제 구현 = Codex(코덱), 독립검수 + 수문장 커밋·push = Claude Code(클코).
- 2026-06-30 이전 작업·문서·인계문·리포트는 종전 배정(구현=클코 / 독립검수·수문장커밋=코덱) 기준이며 그대로 둔다. 과거 문서를 신규 배정으로 반전하지 않는다.
- 이 배정은 운영 편의 기본값이며 도구명 영구 고정이 아니다. 사용량·도구 접근성·위험도·가용성에 따라 지휘소가 배정·대체할 수 있다.
- 불변(절대): 같은 작업에서 구현 주체와 독립검수·커밋 주체는 반드시 다르다. 둘이 같은 주체가 되는 지시문은 형식 위반으로 본다.
- 수문장 책임(git add 선별·git add . 금지·git log --oneline @{u}.. 확인·push gate 3종 체크·secret 실값 0)은 신규 작업에서 클코가 수행한다.

- 역할 분담: 기획·스펙·UX·정책 검토는 Claude(채팅 작업방)이 맡고, 실제 구현은 Codex, 독립검수·검증·테스트·수문장 커밋은 Claude Code가 맡는다. (기본 예시: 지휘소 ChatGPT, 설계 Claude, 구현 Codex, 독립검수/수문장 Claude Code; 2026-06-30 갱신. 도구명 고정 아님)
- 신규 화면/기능은 구현 전에 docs/specs/ 아래 해당 슬라이스 스펙 문서가 존재하고 사용자 승인을 받아야 한다. 스펙 없는 구현은 시작하지 않는다.
- 스펙은 docs/specs/_slice-spec-template.md 형식을 따른다.
- 파일명과 번호는 구현자가 자동 부여하며 사용자가 직접 정하지 않는다. 규칙:
  - 스펙: docs/specs/SPEC-NNN-<영문슬러그>.md (NNN은 docs/specs 안 기존 SPEC 최대 번호 +1, 세 자리)
  - 빌드 보고서: docs/reports/SPEC-NNN-build.md
  - 검증 보고서: docs/reports/SPEC-NNN-verify.md
  - 한 슬라이스의 스펙/빌드보고서/검증보고서는 같은 NNN 번호를 공유한다.
- 작업은 5게이트 순서로 진행한다: ① 스펙 작성(Claude) → ② 스펙 승인(사용자) → ③ 구현 + 빌드 보고서(구현 주체) → ④ 검증 + 검증 보고서(독립검수 주체) → ⑤ 화면 인수·커밋 승인(사용자). 커밋은 사용자 승인 후 독립검수·수문장 주체가 실행한다. (2026-06-30 기본배정: 구현 Codex / 독립검수·수문장 Claude Code, 도구명 고정 아님 — §실행 주체 기본 배정 참조)
- 모든 보고서에는 스펙 완료기준 항목별 충족/미충족을 포함한다.
- 사용자 스펙 승인 전 구현, 사용자 인수 전 커밋은 금지한다.
- 스펙과 구현이 어긋나면 우선 스펙을 기준으로 판단하고, 변경이 필요하면 스펙을 먼저 갱신한 뒤 구현한다.
- 게이트 ① 스펙 작성은 .claude/agents/spec-writer.md 서브에이전트가 수행한다. Claude Code는 새 화면/기능/수정 전 이 서브에이전트로 스펙을 만들고, 사용자 승인(②) 전에는 구현하지 않는다.

## AI 팀 운영 기준
- Codex/Claude/ChatGPT 동시 작업은 `docs/skills/ai-team-operation.md`의 똘망이 팀 큐 구조를 따른다.
- 똘망이는 별도 작업자가 아니라 작업 큐, 보고 체계, 충돌 방지, 커밋 통제 프레임이다.
- 똘망이는 개발용 오케스트레이터이고, 똘순이는 사업용 오케스트레이터다. 사업계획, 영업, 가격, 운영정책, 법무·재무 리스크, 고객 공개 문서는 똘순이가 초안/검수/보고로 정리하고, 화면/DB/API/권한/테스트/배포 구현은 똘망이로 넘긴다.
- 똘순이에서 똘망이로 넘길 때는 사업 목적, 고객 공개 여부, 운영정책, 금지 조건, 필요한 화면/API/데이터 변경 후보, 검수 상태, 남은 보류를 명시한다.
- 같은 작업트리에서 동시 작업할 때는 수정 가능 파일과 금지 파일을 분리하고, 다른 작업자의 변경분을 무단으로 덮어쓰지 않는다.

## `/docs/skills` 보조 기준
- 모든 작업은 이 `AGENTS.md`를 먼저 읽고, 작업 유형에 따라 `/docs/skills/*.md`를 추가로 읽는다.
- `/docs/skills` 문서는 이 파일을 대체하지 않고 작업별 세부 기준을 보완한다.
- `/docs/skills` 문서와 `AGENTS.md`가 충돌하면 `AGENTS.md`의 보안, 중단 조건, 문서 언어 규칙이 항상 우선한다.
- 모든 작업 공통:
  - `docs/skills/smartreturn-pro-workflow.md`
  - `docs/skills/git-security-check.md`
- Codex 검수 작업:
  - `docs/skills/smartreturn-review.md`
  - `docs/skills/git-security-check.md`
- Codex/Claude/ChatGPT 동시 작업 또는 똘망이 운영 큐 작성:
  - `docs/skills/ai-team-operation.md`
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

## 7. Platform Branch Rule

- `main`은 SmartReturn 플랫폼 라인이다.
- `smartreturn-pro`는 SmartReturn Pro 플랫폼 라인이다.
- 두 브랜치는 단순 main/feature 관계가 아니라 서로 다른 플랫폼 라인이다.
- 현재 브랜치가 `smartreturn-pro`이면 SmartReturn Pro 규칙과 문서를 기준으로 작업한다.
- 사용자가 명시적으로 요청하지 않는 한 `smartreturn-pro`를 `main`에 병합·동기화하라고 제안하지 않는다.
- 브랜치 전략을 권고하기 전에 항상 현재 브랜치를 먼저 확인한다.

## 8. 루프 중단조건 / 반복결함 방지

- 구현 게이트④ 검증은 build 보고서(`docs/reports/SPEC-NNN-build.md`)가 없으면 시작하지 않는다. 단, 문서 감사, 하네스 점검, 커밋 선별, 보안 점검처럼 구현 산출물 검증이 아닌 작업은 build 보고서 없이 진행할 수 있으며 그 범위를 명확히 보고한다.
- 작업 시작 시 `git status`를 확인한다. dirty면 무엇이 섞였는지 먼저 분리·보고한 뒤 진행한다(clean 전제 금지).
- 검증/검수 작업 중엔 코드를 고치지 않는다. 빨간 게 나오면 구현자(클코)로 되돌려 수정→재검증, 깨끗할 때까지 반복한다.
- 빨간 테스트는 base-comparison으로 '의도된 차단 / 기존 실패 / 신규 회귀'를 구분한다. 억지로 green 만들지 않는다.
- 권한/테넌트/격리 작업은 DB 실제 상태를 확인한 뒤 판단한다.
- 커밋 후보에 작업 외 파일을 섞지 않는다.
- 한 결정은 한 오케스트레이터만 소유한다. 부딪히면 사용자 최종.
- 빨간불(검수 실패)은 무마하거나 미루지 않는다. 클린이 될 때까지 수정→재검수를 반복한다.
- 단 무한루프 금지: 동일 문제의 수정→재검수는 최대 3회까지.
- 3회 안에 못 잡으면 멈춘다. 같은 방식으로 4번째를 돌리지 않는다. → 멈추고 "왜 안 잡히나" 원인부터 재분석하고, 접근을 바꿔 새로 시작한다.
- "검수자가 잡은 빨간불을 통과시키지 않는다"가 루프 신뢰의 핵심이다.

### 빨간불 되돌림 — 구현자(클코) 측 규칙
검수자(코덱)가 빨간불을 주고 구현자(클코)로 되돌릴 때, 구현자는 다음을 지킨다.

- 검수자가 "코드 동작은 맞다"고 확인한 부분은 코드 동작을 바꾸지 말고 테스트로 못박는다. 빨간불을 없애려고 올바른 동작을 바꾸지 않는다.
- 보안/격리 테스트의 기대값(차단=403/404, 누수=0)을 약화하지 않는다. 테스트를 코드에 맞추지 말고, 올바른 차단/0건을 단언하는 테스트를 새로 쓴다.
- 권한/테넌트 범위/DB 구조/업무 정책을 바꿔야 하는 상황이면 멈추고 사용자에게 보고한다(임의 변경 금지).
- 이번 슬라이스와 무관한 파일·기능은 손대지 않는다.
- 되돌림 작업에서도 커밋/push/git add 하지 않는다.
- 되돌림 완료 보고에는 추가·수정한 테스트와 그 통과 결과, 빨간 테스트의 base-comparison 근거(의도된 차단 / 기존 실패 / 신규 회귀)를 포함한다.

## 9. 작업 분배 / 토큰 예산

- Agent Teams(`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`)는 단일 세션 대비 약 7배 토큰을 쓴다.
- Agent Teams는 기본 OFF(단일 세션)다. "어렵다"가 아니라 "넓다/병렬 이득이 크다"로 판단한다.
- Agent Teams ON 대상:
  - 권한·격리 누수 전수 점검
  - 여러 파일·여러 영역 동시 탐색이 필요한 큰 분석
  - 새 큰 기능의 초기 구조 설계
  - 회귀 위험이 큰 대규모 리팩터링
- Agent Teams OFF 대상:
  - 슬라이스 스펙 작성
  - 한 화면·한 기능 보강
  - 버그 수정, 작은 변경, 검수, 문서 갱신
  - 테스트 수정, 보고서 갱신, 하네스 파일 생성, 단순 리팩터
  - 독립 검수(= Codex 담당)
- 순서가 정해진 작업(DB→API→화면)은 어려워도 단일 세션으로 처리한다.
- 단순·반복·기계적 작업은 기본적으로 Codex에 배정한다.
- 작업 시작 전 "이게 7배 값을 하는 작업인가?"를 판단한다. 아니면 Agent Teams를 끈다.
- 작업 시작 시 "Agent Teams ON/OFF: [사유]"를 한 줄로 선언하고 들어간다.

## 10. 한 작업은 깨끗한 트리에서

- 한 작업(스펙/하네스)을 검수·커밋할 때, 다른 작업의 변경이 트리에 섞여 있으면 먼저 분리하거나 별도 커밋으로 빼낸 뒤 진행한다.
- doc-only 작업을 검수할 때 코드 변경이 섞여 있으면 검수자가 오판할 수 있으므로, 작업 단위로 트리를 깨끗이 유지한다.

## 11. Agent Teams / 동시작업 운영

- Agent Teams는 기본 OFF처럼 다룬다. 지시문에 "팀으로"가 명시될 때만 사용한다.
  (설정 플래그가 켜져 있어도, 명시 없으면 단일 세션으로 동작.)
- 클코가 스스로 팀을 꾸리지 않는다. 팀 사용은 지시문 또는 사용자가 정한다.
- 팀은 §9 기준(넓은 탐색/병렬 이득: 권한·격리 전수 점검, 큰 분석, 새 큰 기능 구조 설계, 대규모 리팩터링)에만.
- 동시작업(병렬) 조건 — 아래를 모두 만족할 때만 허용:
  · 서로 다른 작업이다 (같은 작업의 빌드↔검수는 동시 금지, 순서로 한다)
  · 서로 다른 파일/영역이다 (같은 파일 동시 수정 금지)
  · 각자 다른 git worktree에서 돈다 (한 트리에서 두 작업 동시 진행 금지)
- 안전장치: worktree로 트리를 격리하고, 빌더가 같은 파일을 수정 중이면 검수를 시작하지 않으며, 사용자 승인 전에는 커밋하지 않는다.
- 같은 작업에서 빌더(클코)가 수정 중이면 검수(코덱)는 시작하지 않는다.
  빌더가 멈춘 뒤 검수한다. 검수 빨간불이면 빌더로 되돌린다(§8 3회 룰).
- 병렬로 끝낸 작업은 병합 전 충돌·중복 변경을 확인하고, 작업별로 커밋을 분리한다(§10).

### Codex /goal 사용 규칙

- /goal은 추상적 한 줄로 쓰지 않는다. 아래 4요소를 모두 명시한다:
  · 달성: 무엇을 끝내야 하는가
  · 금지: 무엇을 바꾸면 안 되는가
  · 검증: 무엇으로 진행을 확인하는가
  · 멈춤: 측정 가능한 종료 조건 (예: 권한 누수 0, 테스트 green)
- 멈춤 조건에 "완료" "검수 완료" 같은 판단형 표현을 쓰지 않는다.
  반드시 측정 가능한 사실로 적는다.
- /goal은 구현/탐색 작업에만 쓴다. 독립 검수에는 쓰지 않는다.
  (검수자가 자기 목표를 스스로 "끝"이라 판단하면 독립성이 깨진다.)
- 모호한 목표는 할당량을 태우거나 빗나간 변경을 만들 수 있으므로, 4요소 없는 /goal은 금지한다.
