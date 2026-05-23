# SmartReturn Pro 문서 색인

이 문서는 SmartReturn Pro 신규 프로젝트에서 Codex와 개발자가 구현 전 확인해야 하는 기준 문서 목록이다. 모든 문서는 기존 SmartReturn 구현기록을 복사하기 위한 자료가 아니라, Pro 신규 제작 기준을 고정하기 위한 문서다.

| 문서 | 이 문서의 역할 | 언제 읽어야 하는지 | 구현 전 필수 여부 |
| --- | --- | --- | --- |
| `docs/smartreturn-pro-core-principles.md` | 프로젝트 전체 제작 원칙, 제외 범위, 설계 우선 원칙을 정한다. | 신규 기능, 화면, DB, 업무 흐름을 설계하기 전 | 필수 |
| `docs/ui/smartreturn-pro-ui-page-templates.md` | 화면 타입별 페이지 골격과 레이아웃 계약을 정한다. | 화면 또는 사용자 흐름을 만들기 전 | UI 작업 시 필수 |
| `docs/ui/smartreturn-pro-common-components.md` | 공통 UI 컴포넌트 후보와 사용 원칙을 정한다. | 화면별 table/input/button/select/modal을 만들기 전 | UI 작업 시 필수 |
| `docs/db/smartreturn-pro-db-and-import-policy.md` | DB scope, import job, 원장, 이벤트, 정규화 기준을 정한다. | 테이블, 마이그레이션, import 흐름을 설계하기 전 | DB/업무 작업 시 필수 |
| `docs/business/smartreturn-pro-master-data-policy.md` | 고객사, 상품, 창고, 공통코드, 사용자/권한 기준정보 정책을 정한다. | 기준정보 메뉴나 선택/조회 기능을 만들기 전 | 기준정보 작업 시 필수 |
| `docs/business/smartreturn-pro-return-policy.md` | 반품접수, 반품예정, 반품처리, 마감, 반출의 경계를 정한다. | RETURN 메뉴 또는 반품 관련 데이터 흐름을 만들기 전 | 반품 작업 시 필수 |
| `docs/business/smartreturn-pro-inbound-outbound-policy.md` | 입고/출고 자료 준비, 검수, 확정, 재고 반영 원칙을 정한다. | 입고 또는 출고 업무를 설계하기 전 | 입출고 작업 시 필수 |
| `docs/business/smartreturn-pro-scan-local-agent-inventory-policy.md` | 스캔 매칭, Local Agent 역할, 재고 이벤트 반영 기준을 정한다. | 스캔, 프린터, 사운드, 재고 반영 기능을 만들기 전 | 스캔/재고 작업 시 필수 |
| `docs/business/smartreturn-pro-auth-password-policy.md` | role 기준 권한, 고객사 scope, 첫 로그인 비밀번호 정책을 정한다. | 인증, 권한, 사용자 관리 기능을 만들기 전 | 인증/권한 작업 시 필수 |
| `docs/dev/smartreturn-pro-test-and-release-policy.md` | 테스트, 빌드, 커밋 전 점검, 배포 제외 범위를 정한다. | 검증, 릴리스, 커밋 요청을 처리하기 전 | 변경 완료 전 필수 |

## 사용 원칙

- 신규 기능 구현 전에는 `AGENTS.md`와 이 색인을 먼저 확인한다.
- 작업 범위와 맞는 세부 문서를 읽은 뒤 설계와 구현을 진행한다.
- 여러 업무가 걸친 기능은 관련 문서를 모두 읽는다.
- 문서 간 충돌이 있으면 `AGENTS.md`와 핵심 원칙 문서를 우선 기준으로 보고, 충돌 내용을 먼저 정리한다.
