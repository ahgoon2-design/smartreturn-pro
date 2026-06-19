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
| `ai-team-operation.md` | Codex/Claude/ChatGPT 동시 작업, 똘망이 운영 큐 작성, 충돌 방지, 보고/커밋 통제 작업 시 | Codex/Claude/ChatGPT를 똘망이 팀 큐 구조로 운영하기 위한 역할 분담, 충돌 방지, 보고, 커밋 통제 기준을 정리한다. |
| `smartreturn-platform-business-architecture.md` | 신규 기능 설계, DB 테이블 추가, 메뉴/권한 변경, 고객사 포털/대리점 포털, 정산/청구, 채널연동, 대시보드/사업 지표 작업 시 | SmartReturn Pro의 최상위 사업/제품 방향, CJ대한통운 대리점 기반 OMS + WMS + Returns 통합 SaaS 플랫폼 구조, 사용자 유형, `agency_id`/`client_id`/`client_unit_id` 데이터 계층, MVP/확장 로드맵, 신규 기능 설계 체크리스트 기준을 정리한다. |
| `backend-api.md` | FastAPI backend API 작업 시 | ApiResult, 인증/권한, client scope, 테스트 기준을 정리한다. |
| `frontend-app.md` | React/Vite/TypeScript frontend 작업 시 | 앱 구조, 라우팅, 인증 context, API client 기준을 정리한다. |
| `smartreturn-screen-design-system.md` | 신규 화면, 화면 개편, UI 수정, 아이콘/이미지 추가 작업 시 | SmartReturn Pro 화면 디자인 철학, 은은한 파스텔 색상 체계, SVG 라인 아이콘/이미지 사용 규칙, 관리자/작업자/고객사 화면 레이아웃, 상태 badge, 카드, 그리드, 모달, 버튼, 새 화면 제작 체크리스트 기준을 정리한다. |
| `ui-design-system.md` | 화면 디자인, 공통 UI 작업 시 | Ant Design 기반 공통 UI, 공통 컴포넌트 조합 순서, 화면 밀도 기준을 정리한다. |
| `ui-grid.md` | grid/table/preview 화면 작업 시 | SmartDataGrid wrapper, row 순서, 상태 표시, copyable 셀 기준을 정리한다. |
| `worker-screen-ux.md` | 스캔/검수/작업자 화면 작업 시 | SmartScanPanel, 정확도, 속도, 자동화 중심의 작업자 UX 기준을 정리한다. |
| `import-preview.md` | import preview, paste rows, validation 화면 작업 시 | import job 생성, rows 저장, validate, rows/errors 표시 계약을 정리한다. |
| `channel-return-auto-collection.md` | 네이버/쿠팡/카페24/이지어드민/택배사 API 반품 자동수집 작업 시 | 외부 채널 원본 수집, canonical 정규화, 중복 upsert, 예외상태 분리, 현장 스캔 연결, 채널 역전송 단계화 기준을 정리한다. |
| `return-client-unit-routing.md` | 반품/재고/창고/기준정보 작업 시 | 고객사 운영단위/팀 기준 반품·창고·재고 라우팅 규칙을 정리한다. |
| `return-operational-judgment-policy.md` | 반품 판정, 판정별 창고, 세부항목 없는 반품, 스캔/그리드 처리, 폐기/부품적출 작업 시 | 고객사별 판정 설정, `warehouse_id` 필수, 일마감 이후 재고반영, 세부항목 없는 반품 현장 처리, 부품적출 기준을 정리한다. |
| `set-product-component-bom.md` | 세트상품, 구성품, BOM, 출고 피킹/검수, 세트 반품 처리 작업 시 | 세트상품은 판매 단위, 구성품은 피킹/검수/재고 단위라는 기준과 출고/반품/부품적출 연결 규칙을 정리한다. |
| `return-judgment-ai-assistant.md` | AI 판정도우미, 고객사별 판정 매뉴얼, 판정 체크리스트, 사진/영상 증빙 데이터 작업 시 | AI를 최종 판정자가 아니라 판정지원 도우미로 설계하는 기준과 추천/체크리스트/데이터 누적 방향을 정리한다. |
| `naver-cloud-saas-architecture.md` | DB/파일/사진/로그/배포/채널 자동수집/백업/보안/대량 이력 테이블 작업 시 | 네이버클라우드 기반 SaaS 운영, 단일 DB 멀티테넌트, Object Storage 파일 저장, API/Worker/Scheduler 분리, 로그/백업/확장 기준을 정리한다. |

## 사용 원칙

- 작업 시작 전 `AGENTS.md`를 먼저 읽는다.
- 작업 유형이 정해지면 위 표의 관련 문서를 추가로 읽는다.
- 문서가 여러 개 해당되면 공통 문서부터 읽고 도메인 문서를 읽는다.
- 기존 SmartReturn 기준과 SmartReturn Pro 기준이 다르면 SmartReturn Pro 기준을 우선한다.
- Codex/Claude/ChatGPT 동시 작업이나 똘망이 운영 큐 작성 작업은 `ai-team-operation.md`를 함께 읽는다.
- 신규 기능 설계, DB 테이블 추가, 메뉴/권한 변경, 고객사 포털/대리점 포털, 정산/청구, 채널연동, 대시보드/사업 지표 작업은 `smartreturn-platform-business-architecture.md`를 함께 읽는다.
- 신규 화면, 화면 개편, UI 수정, 아이콘/이미지 추가 작업은 `smartreturn-screen-design-system.md`를 함께 읽는다.
- 반품 접수, 반품처리, 창고설정, 재고반영, 기준정보 작업은 `return-client-unit-routing.md`를 함께 읽는다.
- 반품 판정, 판정별 창고, 세부항목 없는 반품, 스캔/그리드 처리, 폐기/부품적출 작업은 `return-operational-judgment-policy.md`를 함께 읽는다.
- 세트상품, 구성품, BOM, 출고 피킹/검수, 세트 반품 작업은 `set-product-component-bom.md`를 함께 읽는다.
- AI 판정도우미, 판정 매뉴얼, 판정 체크리스트, 사진/영상 증빙 데이터 작업은 `return-judgment-ai-assistant.md`를 함께 읽는다.
- 네이버/쿠팡/카페24/이지어드민/택배사 API 등 외부 채널 반품 자동수집 작업은 `channel-return-auto-collection.md`를 함께 읽는다.
- DB, 파일, 사진, 로그, 배포, 채널 자동수집, 백업, 보안, 대량 이력 테이블 작업은 `naver-cloud-saas-architecture.md`를 함께 읽는다.
- 실제 secret, token, password, password_hash 값은 어떤 문서에도 쓰지 않는다.
