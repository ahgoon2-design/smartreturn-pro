# SmartReturn Pro P0 개발환경 세팅 전 계획

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

이 문서는 실제 개발환경 생성 지시가 아니다. 실제 `backend`, `frontend`, `database`, `local_agent` 폴더와 패키지 파일을 만들기 전에 구조와 순서를 고정하는 문서다. 이번 문서 기준을 확정하기 전에는 프론트엔드, 백엔드, DB migration, Docker, 패키지 설치를 진행하지 않는다.

## 1. 문서 목적

- SmartReturn Pro 개발환경을 만들기 전에 백엔드, 프론트엔드, DB, Local Agent 후보 구조를 정리한다.
- PostgreSQL, FastAPI, React/Vite, Ant Design, AG Grid, Local Agent 후보를 어떤 순서로 세팅할지 고정한다.
- 개발환경 세팅 중 불필요한 산출물, 민감정보, 로컬 설정 파일이 커밋되지 않도록 기준을 만든다.
- 기준정보, auth, client scope 구현 착수 전에 필요한 P0 환경 준비 범위를 정한다.

## 2. P0 개발환경 목표

P0 개발환경의 목표는 다음과 같다.

- FastAPI 백엔드 기본 구조를 만들 준비
- React + TypeScript + Vite 프론트 기본 구조를 만들 준비
- PostgreSQL 기준 DB 연결 구조를 만들 준비
- Alembic migration 구조를 만들 준비
- 공통 auth/client scope 구조를 구현할 준비
- 기준정보 P0 테이블/API 구현을 시작할 준비
- 공통 UI 컴포넌트 구현을 시작할 준비

P0에서 아직 하지 않을 것은 다음과 같다.

- 반품 업무 API 실제 구현
- 반품 화면 실제 구현
- 입고/출고/정산 구현
- 고객사 포털 구현
- ERP 실제 API 연동
- Local Agent 실제 패키징
- Docker 운영 배포 구성
- CI/CD 자동 배포

## 3. 추천 기술 스택

### 3-1. 백엔드

추천 기술:

- Python
- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic
- `psycopg` 또는 `asyncpg` 중 선택 후보
- `pytest` 또는 `unittest` 중 선택 후보

정책:

- `service`, `repository`, `router`, `schema` 계층을 분리한다.
- DB 접근은 `repository` 계층에 모은다.
- `service`는 업무 흐름과 검증을 담당한다.
- `router`는 요청/응답과 dependency 연결만 담당한다.
- raw SQL은 `repository` 내부에만 격리한다.
- startup 자동 `ALTER TABLE` 의존을 피하고 Alembic migration을 기준으로 한다.
- 인증/권한은 모든 업무 router에 흩뿌리지 않고 공통 dependency로 연결한다.
- `client_id`와 `warehouse_id` 검증은 service 내부 임시 조건문이 아니라 공통 scope 처리 기준을 따른다.

### 3-2. 프론트엔드

추천 기술:

- React
- TypeScript
- Vite
- Ant Design
- AG Grid
- `lucide-react` 또는 `@ant-design/icons`
- React Router
- `fetch` 또는 `axios` 후보

정책:

- 화면별 직접 `AgGridReact` 사용을 금지한다.
- `SmartDataGrid`, `SmartEditableDataGrid`, `SmartExcelPreviewGrid` 공통 래퍼를 먼저 만든다.
- `SmartWorkLayout`, `SmartInfoPanel`, `SmartActionBar`, `SmartModalShell` 같은 공통 컴포넌트를 먼저 만든다.
- 화면별 CSS 땜질보다 공통 컴포넌트와 공통 CSS를 우선한다.
- 고객사, 상품, 창고, 공통코드 선택은 `SmartLookupModal` 또는 `SmartCommonCodeSelect` 계열로 통일한다.
- 반품 화면을 먼저 만들지 않고 공통 레이아웃과 그리드 계열 컴포넌트 skeleton을 먼저 만든다.

### 3-3. DB

추천 기술:

- PostgreSQL 우선
- 개발환경에서는 로컬 PostgreSQL 또는 Docker PostgreSQL 후보
- Alembic migration 기준

정책:

- DB 이름, 계정, 비밀번호는 `.env`로 관리하고 커밋하지 않는다.
- `.env.example`만 커밋한다.
- schema sync 자동 보정보다 migration을 우선한다.
- P0 테이블은 `users`, `roles`, `clients`, `warehouses`, `products`, `common_codes`, `import_jobs`, `inventory_events` 계열을 먼저 준비한다.
- 실제 고객 개인정보를 seed/test 데이터에 넣지 않는다.

### 3-4. Local Agent

P0에서는 Local Agent를 실제 구현하지 않는다.

문서상 준비만 한다.

- `local_agent` 또는 `local_tools` 폴더 후보
- 사운드/라벨/프린터 제어는 후속 단계
- Local Agent는 재고를 직접 변경하지 않는다.
- `config.json`은 커밋 금지다.
- `config.example.json`만 커밋 가능하다.
- Local Agent 실패가 업무 저장 실패가 되지 않도록 후속 설계에서 DB/API와 분리한다.

## 4. 추천 폴더 구조

아래 구조는 실제 생성 전 후보 구조다. 지금 작업에서는 이 폴더를 실제로 만들지 않는다.

```text
backend/
  app/
    core/
    db/
    models/
    schemas/
    repositories/
    services/
    routers/
    modules/
    tests/
  alembic/
  alembic.ini

frontend/
  src/
    components/
      common/
      layout/
      grid/
      modal/
      lookup/
      scan/
    pages/
    services/
    hooks/
    types/
    utils/
    styles/
  public/

docs/
  business/
  db/
  dev/
  ui/
  archive/
  reference/

local_agent/
  README.md
  config.example.json

scripts/
  README.md
```

주의:

- 지금 작업에서는 위 폴더와 파일을 실제로 만들지 않는다.
- 실제 폴더 생성은 다음 개발환경 세팅 작업에서 한다.
- `docs` 폴더는 이미 기준 문서 영역이며, 개발환경 파일과 섞지 않는다.

## 5. 백엔드 P0 구현 준비 순서

실제 백엔드 세팅은 아래 순서를 따른다.

1. `backend` 기본 폴더 생성
2. FastAPI 앱 최소 실행 구조
3. 설정 관리 구조
4. DB 연결 구조
5. SQLAlchemy `Base`/session 구조
6. Alembic migration 초기화
7. auth/core dependency 구조
8. P0 models 작성
9. P0 schemas 작성
10. P0 repositories 작성
11. P0 services 작성
12. P0 routers 작성
13. 기본 테스트 구조 작성

정책:

- 이번 문서 작업에서는 실제 생성하지 않는다.
- P0 models 작성 전 `docs/db/smartreturn-pro-p0-table-columns.md`를 다시 확인한다.
- auth/core dependency 작성 전 `docs/business/smartreturn-pro-auth-client-scope-api-policy.md`를 다시 확인한다.
- Alembic 초기화 전 PostgreSQL 연결 방식과 패키지 관리 방식을 먼저 확정한다.

## 6. 프론트 P0 구현 준비 순서

실제 프론트 세팅은 아래 순서를 따른다.

1. `frontend` Vite/React/TypeScript 생성
2. Ant Design/AG Grid/icon 라이브러리 설치
3. `AppShell` 기본 구조
4. `SmartWorkLayout`
5. `SmartButton`/`SmartField`/`SmartStatusBadge`
6. `SmartModalShell`
7. `SmartDataGrid`
8. `SmartEditableDataGrid`
9. `SmartExcelPreviewGrid`
10. `SmartLookupModal`
11. `SmartFilterPanel`
12. `SmartInfoPanel`
13. `SmartActionBar`
14. 기본 라우팅
15. 기준정보 화면 전 공통 컴포넌트 테스트 페이지 후보

정책:

- 이번 문서 작업에서는 실제 생성하지 않는다.
- 공통 컴포넌트 없이 반품 화면부터 만들지 않는다.
- `AgGridReact`는 공통 그리드 래퍼 내부에만 격리한다.
- 1366x768 기준을 공통 레이아웃 skeleton 단계부터 확인한다.

## 7. DB P0 구현 준비 순서

실제 DB 세팅은 아래 순서를 따른다.

1. PostgreSQL 연결 기준 확정
2. `.env.example` 후보 정의
3. Alembic 초기 migration
4. `roles`/`permissions`/`users`
5. `clients`/`warehouses`/`client_warehouse_settings`
6. `products`/`product_barcodes`
7. `common_code_groups`/`common_codes`
8. `import_jobs`/`import_job_rows`/`import_validation_errors`
9. `inventory_events`/`current_inventory`
10. seed 데이터 정책

주의:

- 실제 seed 데이터는 후속 문서에서 확정한다.
- 운영사/고객사 샘플 데이터에는 실제 고객 개인정보를 넣지 않는다.
- migration 없이 임의 테이블을 생성하지 않는다.
- schema 자동 보정으로 운영 DB 구조를 맞추지 않는다.

## 8. 환경변수 후보

아래는 후속 `.env.example` 파일에 넣을 수 있는 후보이며, 이번 작업에서는 실제 파일을 만들지 않는다.

```text
APP_ENV=
APP_NAME=
DATABASE_URL=
SECRET_KEY=
ACCESS_TOKEN_EXPIRE_MINUTES=
CORS_ORIGINS=
LOG_LEVEL=
LOCAL_AGENT_BASE_URL=
FILE_STORAGE_ROOT=
```

주의:

- 실제 비밀번호, secret, token은 문서에 적지 않는다.
- `.env`는 커밋 금지다.
- `.env.example`은 후속 개발환경 세팅 작업에서 만든다.
- `DATABASE_URL` 예시는 실제 계정/비밀번호가 아닌 placeholder로만 작성한다.

## 9. `.gitignore` 기준 후보

후속 개발환경 세팅 작업에서 `.gitignore`에 포함할 커밋 금지 후보는 다음과 같다.

```text
.env
.env.*
config.json
logs/
outputs/
dist/
build/
__pycache__/
*.pyc
*.log
*.tmp
*.bak
*.zip
*.exe
node_modules/
.venv/
.pytest_cache/
coverage/
frontend/dist/
local_agent/config.json
local_agent/logs/
local_agent/outputs/
```

커밋 가능 후보:

- `.env.example`
- `config.example.json`
- `README.md`
- `docs/*.md`
- 각 폴더의 설명용 `README.md`

주의:

- `.env.*`를 금지하더라도 `.env.example`은 예외 처리해야 한다.
- Local Agent 실제 설정 파일과 로그/출력물은 커밋하지 않는다.
- 빌드 산출물은 테스트 목적으로 생성되어도 커밋하지 않는다.

## 10. 개발환경 세팅 전 결정해야 할 것

| 항목 | 선택지 | 추천안 |
| --- | --- | --- |
| 백엔드 패키지 관리 | `pip`/`venv`, `poetry`, `uv` | 초기에는 `pip` + `.venv` 또는 팀 합의 시 `uv`를 추천한다. |
| DB 드라이버 | `psycopg`, `asyncpg` | FastAPI async 전략을 택하면 `asyncpg`, sync 전략이면 `psycopg`를 선택한다. 초기에는 한 전략으로 통일한다. |
| FastAPI 전략 | sync, async | P0에서는 복잡도를 낮추기 위해 하나로 통일한다. DB 드라이버 결정과 함께 확정한다. |
| 테스트 프레임워크 | `pytest`, `unittest` | `pytest`를 추천한다. |
| 프론트 패키지 매니저 | `npm`, `pnpm`, `yarn` | 특별한 팀 기준이 없으면 `npm`으로 시작한다. |
| CSS 전략 | 공통 CSS + class, CSS module | 공통 CSS 파일 + 컴포넌트 class 우선을 추천한다. |
| 상태관리 | React state, 별도 상태관리 | 초기에는 React state와 hooks 중심으로 시작한다. |
| API client | fetch wrapper, axios | 초기에는 fetch wrapper를 추천하되 인증/에러 처리가 복잡해지면 axios 후보를 검토한다. |
| 날짜/시간 라이브러리 | 미사용, dayjs 등 | Ant Design과 궁합이 좋은 `dayjs` 후보를 둔다. |
| Local Agent 폴더명 | `local_agent`, `local_tools` | `local_agent`를 추천한다. |

결정 원칙:

- 선택지를 오래 열어두지 않는다.
- P0 구현 시작 전에 위 항목을 한 번에 확정한다.
- 중간에 도구를 바꾸면 migration, 테스트, 문서 기준이 흔들리므로 변경 이유를 문서화한다.

## 11. P0 개발 착수 전 금지사항

- 문서 없이 코드부터 만들기 금지
- DB migration 없이 임의 테이블 생성 금지
- 화면별 CSS/컴포넌트 임시 생성 금지
- 공통 컴포넌트 없이 반품 화면부터 구현 금지
- PostgreSQL 기준 없이 SQLite/MySQL 전용 구조로 시작 금지
- Local Agent가 재고를 직접 변경하는 구조 금지
- 실제 고객 개인정보를 seed/test 데이터에 넣기 금지
- `.env`/`config.json` 커밋 금지
- zip/exe/dist/build 산출물 커밋 금지

## 12. P0 개발환경 세팅 작업 단위 후보

다음 실제 작업은 아래 단위로 나누어 진행한다.

1. 프로젝트 기본 폴더와 `.gitignore`/`.env.example` 생성
2. 백엔드 FastAPI 최소 앱 + DB 설정 구조
3. Alembic + P0 모델 skeleton
4. 프론트 Vite/React/TypeScript 기본 앱
5. 프론트 공통 레이아웃/버튼/필드 skeleton
6. `SmartDataGrid` 계열 skeleton
7. auth/client scope 백엔드 skeleton
8. 기준정보 P0 API skeleton

정책:

- 이번 작업에서는 실제 생성하지 말고 문서에만 적는다.
- 각 단위는 별도 커밋 후보로 관리한다.
- 백엔드와 프론트가 동시에 커지는 작업은 검증이 어려우므로 가능한 작게 나눈다.

## 13. Codex 구현 전 체크

- `AGENTS.md`를 읽었는가?
- 이번 작업이 문서 작업인지 코드 작업인지 구분했는가?
- 실제 개발환경 파일을 만들기 전에 문서 기준이 충분한가?
- DB는 PostgreSQL/Alembic 기준으로 갈 준비가 되었는가?
- P0 테이블 우선순위와 맞는가?
- 공통 UI 컴포넌트 구현 전 업무 화면을 만들지 않는가?
- `.env`/`config.json`/산출물 커밋 금지 기준을 지키는가?
- 실제 고객 개인정보가 들어가지 않는가?
