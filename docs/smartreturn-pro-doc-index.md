# SmartReturn Pro 문서 색인

이 문서는 SmartReturn Pro 신규 프로젝트에서 Codex와 개발자가 구현 전 확인해야 하는 기준 문서 목록이다. 모든 문서는 기존 SmartReturn 구현기록을 복사하기 위한 자료가 아니라, Pro 신규 제작 기준을 고정하기 위한 문서다.

| 문서 | 이 문서의 역할 | 언제 읽어야 하는지 | 구현 전 필수 여부 |
| --- | --- | --- | --- |
| `README.md` | 저장소 첫 화면에서 프로젝트 목적, 현재 단계, 추천 제작 순서, 주요 문서 링크를 안내한다. | 저장소를 처음 열거나 신규 참여자가 전체 맥락을 파악할 때 | 권장 |
| `docs/smartreturn-pro-core-principles.md` | 프로젝트 전체 제작 원칙, 제외 범위, 설계 우선 원칙을 정한다. | 신규 기능, 화면, DB, 업무 흐름을 설계하기 전 | 필수 |
| `docs/ui/smartreturn-pro-ui-page-templates.md` | 화면 타입별 페이지 골격과 레이아웃 계약을 정한다. | 화면 또는 사용자 흐름을 만들기 전 | UI 작업 시 필수 |
| `docs/ui/smartreturn-pro-common-components.md` | 공통 UI 컴포넌트 후보와 사용 원칙을 정한다. | 화면별 table/input/button/select/modal을 만들기 전 | UI 작업 시 필수 |
| `docs/ui/smartreturn-pro-common-component-props.md` | SmartReturn Pro 공통 UI 컴포넌트의 책임, props 후보, 상태 처리, 금지 패턴을 정리하는 문서다. | 프론트 공통 컴포넌트 구현 전 또는 반품 화면 구현 전 | 프론트 UI 구현 전 필수 |
| `docs/ui/smartreturn-pro-return-screen-design.md` | 반품 MVP 5개 화면의 레이아웃, 영역 책임, 공통 컴포넌트, 금지 기능, 실패 기준을 정리하는 문서다. | 반품 프론트 화면 구현 전 | 반품 UI 구현 전 필수 |
| `docs/ui/smartreturn-pro-return-field-column-map.md` | 반품 MVP 화면별 표시 필드, 그리드 컬럼, 우측 패널 정보, 상태 배지 표시 기준을 정리하는 문서다. | 반품 프론트 화면 구현 전 또는 반품 API DTO를 화면에 연결하기 전 | 반품 UI 구현 전 필수 |
| `docs/db/smartreturn-pro-db-and-import-policy.md` | DB scope, import job, 원장, 이벤트, 정규화 기준을 정한다. | 테이블, 마이그레이션, import 흐름을 설계하기 전 | DB/업무 작업 시 필수 |
| `docs/db/smartreturn-pro-initial-erd.md` | 초기 ERD 수준에서 도메인별 테이블 후보와 원장 관계를 정리한다. | migration 작성 전 DB 큰 구조와 테이블 경계를 검토할 때 | DB 설계 시 필수 |
| `docs/db/smartreturn-pro-p0-table-columns.md` | P0 기반 테이블의 핵심 컬럼, 제약, 인덱스 후보를 정리한다. | 백엔드 모델, migration, ERD 구현 전 | DB 구현 전 필수 |
| `docs/db/smartreturn-pro-return-p1-table-columns.md` | 반품 MVP P1 테이블의 핵심 컬럼, 상태값, 제약조건, 관계를 정리하는 문서다. | 반품 DB 모델, migration, API schema 구현 전 | 반품 DB 구현 전 필수 |
| `docs/db/smartreturn-pro-table-priority.md` | 초기 ERD의 테이블 후보를 P0/P1/P2/P3/HOLD 개발 우선순위로 정리한다. | 테이블 설계 순서, MVP DB 범위, 후속 보류 대상을 정할 때 | DB 설계 시 필수 |
| `docs/business/smartreturn-pro-master-data-policy.md` | 고객사, 상품, 창고, 공통코드, 사용자/권한 기준정보 정책을 정한다. | 기준정보 메뉴나 선택/조회 기능을 만들기 전 | 기준정보 작업 시 필수 |
| `docs/business/smartreturn-pro-mvp-scope.md` | 1차 MVP 포함/제외 범위와 반품 MVP 선행 기반 순서를 확정한다. | 개발 범위, 업무 우선순위, 반품 MVP 착수 여부를 판단할 때 | MVP 범위 판단 시 필수 |
| `docs/business/smartreturn-pro-menu-and-screen-map.md` | 1차 메뉴 구조, 화면 목록, 화면별 책임과 넣지 말 것을 정한다. | 라우팅, 메뉴, 화면 설계를 시작하기 전 | UI/업무 설계 시 필수 |
| `docs/business/smartreturn-pro-return-policy.md` | 반품접수, 반품예정, 반품처리, 마감, 반출의 경계를 정한다. | RETURN 메뉴 또는 반품 관련 데이터 흐름을 만들기 전 | 반품 작업 시 필수 |
| `docs/business/smartreturn-pro-return-mvp-flow.md` | 반품 MVP의 실제 업무흐름과 화면 책임을 고정한다. | 반품 관련 DB/API/화면 구현 전 | 반품 작업 시 필수 |
| `docs/business/smartreturn-pro-return-api-policy.md` | 반품 MVP API 책임, 엔드포인트 후보, 권한, 상태 전이, 재고/스캔 이벤트 연결 기준을 정리하는 문서다. | 반품 백엔드 router/service/schema 구현 전 | 반품 API 구현 전 필수 |
| `docs/business/smartreturn-pro-return-api-schema.md` | 반품 MVP API request/response schema 후보와 결과코드, sound_code, UI 노출 기준을 정리하는 문서다. | 반품 Pydantic schema, API router/service 구현 전 | 반품 schema 구현 전 필수 |
| `docs/business/smartreturn-pro-inbound-outbound-policy.md` | 입고/출고 자료 준비, 검수, 확정, 재고 반영 원칙을 정한다. | 입고 또는 출고 업무를 설계하기 전 | 입출고 작업 시 필수 |
| `docs/business/smartreturn-pro-scan-local-agent-inventory-policy.md` | 스캔 매칭, Local Agent 역할, 재고 이벤트 반영 기준을 정한다. | 스캔, 프린터, 사운드, 재고 반영 기능을 만들기 전 | 스캔/재고 작업 시 필수 |
| `docs/business/smartreturn-pro-auth-password-policy.md` | role 기준 권한, 고객사 scope, 첫 로그인 비밀번호 정책을 정한다. | 인증, 권한, 사용자 관리 기능을 만들기 전 | 인증/권한 작업 시 필수 |
| `docs/business/smartreturn-pro-auth-client-scope-api-policy.md` | SmartReturn Pro 모든 API의 role, client scope, warehouse scope 권한 기준을 정리하는 문서다. | 백엔드 인증/권한, 기준정보 API, 반품/입고/출고/재고 API 구현 전 | API 구현 전 필수 |
| `docs/dev/smartreturn-pro-test-and-release-policy.md` | 테스트, 빌드, 커밋 전 점검, 배포 제외 범위를 정한다. | 검증, 릴리스, 커밋 요청을 처리하기 전 | 변경 완료 전 필수 |

## 사용 원칙

- 신규 기능 구현 전에는 `AGENTS.md`와 이 색인을 먼저 확인한다.
- 저장소 전체 맥락은 `README.md`에서 먼저 확인한다.
- 작업 범위와 맞는 세부 문서를 읽은 뒤 설계와 구현을 진행한다.
- 여러 업무가 걸친 기능은 관련 문서를 모두 읽는다.
- 문서 간 충돌이 있으면 `AGENTS.md`와 핵심 원칙 문서를 우선 기준으로 보고, 충돌 내용을 먼저 정리한다.
