# SmartReturn Pro

SmartReturn Pro는 3PL 고객사 관리 통합 플랫폼이다. OMS, WMS, RETURN, 재고, 정산, 고객사 포털까지 확장 가능한 구조를 목표로 한다.

## 기본 개념

- 운영사: 동현물류
- 고객사/화주: `client`
- 내부 운영자와 고객사 사용자는 `role` 기준으로 구분한다.
- 모든 업무 데이터는 `client_id` scope를 기준으로 관리한다.
- 창고 업무는 `warehouse_id` scope를 함께 지킨다.

## 핵심 제작 원칙

- 기존 SmartReturn 구현기록, 화면, DB를 그대로 복사하지 않는다.
- 문서와 설계를 먼저 확정하고 구현은 후순위로 진행한다.
- 화면 1개는 업무 목적 1개만 가진다.
- 공통 UI 컴포넌트를 먼저 만들고 화면별 임시 UI를 만들지 않는다.
- import job과 실제 업무 테이블을 분리한다.
- `inventory_events`와 `scan_events`를 분리한다.
- 반품 구글시트는 반품처리 원장이 아니라 업체 반품접수/회신 채널이다.

## 현재 단계

현재 저장소는 신규 프로젝트 기준 문서 작성 단계다. 아직 프론트엔드, 백엔드, DB 연결, 패키지 설치, 개발환경 세팅 전이다.

## 개발 폴더 구조

- `backend/`: 향후 FastAPI 백엔드가 들어갈 위치
- `frontend/`: 향후 React + TypeScript + Vite 프론트엔드가 들어갈 위치
- `local_agent/`: 향후 사운드, 라벨, 프린터, 장치 제어용 Local Agent가 들어갈 위치
- `scripts/`: 개발 보조 스크립트 후보 위치

현재 단계는 폴더와 설정 예시 준비 단계다. 실제 실행 환경은 아직 생성 전이며, `.env.example`을 복사해 `.env`로 사용하는 작업은 후속 개발환경 세팅에서 진행한다.

## 추천 제작 순서

1. 기준 문서 확정
2. DB ERD 확정
3. 메뉴/화면 구조 확정
4. 개발환경 세팅
5. 공통 UI 컴포넌트
6. 공통 백엔드/auth/client scope
7. 기준정보
8. import job / 업로드 엔진
9. 재고 이벤트 엔진
10. 반품 MVP
11. 입고 MVP
12. 출고 MVP
13. OMS/정산/고객사 포털 확장

## 주요 문서

- [AGENTS.md](AGENTS.md)
- [문서 색인](docs/smartreturn-pro-doc-index.md)
- [핵심 제작 원칙](docs/smartreturn-pro-core-principles.md)
- [UI 페이지 템플릿](docs/ui/smartreturn-pro-ui-page-templates.md)
- [공통 UI 컴포넌트 props](docs/ui/smartreturn-pro-common-component-props.md)
- [반품 MVP 화면 설계](docs/ui/smartreturn-pro-return-screen-design.md)
- [반품 MVP 필드/컬럼 맵](docs/ui/smartreturn-pro-return-field-column-map.md)
- [DB 및 import 정책](docs/db/smartreturn-pro-db-and-import-policy.md)
- [초기 ERD 설계](docs/db/smartreturn-pro-initial-erd.md)
- [P0 테이블 핵심 컬럼](docs/db/smartreturn-pro-p0-table-columns.md)
- [반품 P1 테이블 핵심 컬럼](docs/db/smartreturn-pro-return-p1-table-columns.md)
- [테이블 우선순위](docs/db/smartreturn-pro-table-priority.md)
- [MVP 범위](docs/business/smartreturn-pro-mvp-scope.md)
- [메뉴 및 화면 목록](docs/business/smartreturn-pro-menu-and-screen-map.md)
- [반품 MVP 상세 업무흐름](docs/business/smartreturn-pro-return-mvp-flow.md)
- [반품 MVP API 정책](docs/business/smartreturn-pro-return-api-policy.md)
- [반품 MVP API schema](docs/business/smartreturn-pro-return-api-schema.md)
- [권한/client scope API 정책](docs/business/smartreturn-pro-auth-client-scope-api-policy.md)
- [role/permission seed 정책](docs/business/smartreturn-pro-role-permission-seed-policy.md)
- [초기 SUPER_ADMIN bootstrap 정책](docs/business/smartreturn-pro-super-admin-bootstrap-policy.md)
- [P0 개발환경 세팅 전 계획](docs/dev/smartreturn-pro-p0-dev-environment-plan.md)

## 주의사항

- 모든 기준 문서, 설계 문서, 운영 문서의 본문은 한글로 작성한다.
- 파일명, 코드 식별자, DB 컬럼명, API path, enum 값은 영어를 사용할 수 있다.
- 커밋 전 `config.json`, `logs`, `outputs`, `dist`, `build`, `zip`, `exe`, `__pycache__`, `.env`, 민감정보가 포함되지 않았는지 확인한다.
- 커밋은 사용자가 명시적으로 요청한 경우에만 수행한다.
