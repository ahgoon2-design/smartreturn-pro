# 011 - 규칙/공통컴포넌트/로그인·권한·저장 흐름 점검 보고

- 실행: Claude(Fable 5) + 똘망이(브라우저는 이번 미사용, 코드 검색 중심) / 플랜+점검모드 / 브랜치 smartreturn-pro
- 앱 코드 수정: **없음** (분석/보고만)

## 1. 확인한 규칙/md/skills 파일
- `AGENTS.md`(SmartReturn Pro 기준 + Harness 헌법 + Platform Branch Rule)
- `CLAUDE.md`(프로젝트 규칙 + Claude 운영 가이드)
- `docs/skills/`: README, frontend-app, backend-api, ui-design-system, ui-grid, git-security-check (main 유래 구버전 세트)
- `docs/`(재편 세트): smartreturn-pro-core-principles, doc-index, business/auth-client-scope-api-policy, ui/common-component-props 등
- `ai-harness/`: references 10종, workflow 5종, instructions/current 001~009

규칙 키워드 스캔 결과:
| 규칙 | 존재 여부 |
|---|---|
| 화면 수정 전 기존 컴포넌트 확인 / 새 컴포넌트 남발 금지 | ✅ 있음(AGENTS·frontend-app·references/frontend) |
| 로그인/권한/스코프 확인 | ✅ 있음(backend-api 6건, auth-client-scope-api-policy) |
| **저장 API 수정 시 FE/BE 동시 확인** | ❌ **없음** — frontend-app·backend-api 모두 "저장" 규칙 0건 |
| 고객사/대리점/내부 분기 | ✅ 원칙은 있음(role 기준) — 단 "저장 가능 role 매트릭스"는 없음 |
| 하드코딩 금지 | ✅ 있음(backend-api: business code/status) — 단 "기본 창고 금지"는 산재 |
| **중복/충돌** | ⚠️ **docs/skills(구) vs docs/business·ui(재편) 이중 체계** — 같은 주제 문서 2벌, 정본 미정(기존 식별 사항) |

## 2. 확인한 공통 컴포넌트
- 있음: `MainLayout`/`PortalLayout`(AppShell), `AuthContext`, `RouteGuard`(area 가드), `api/client`(토큰/401/ApiClientError), `SmartDataGrid`(+export/copy), `SmartPage/PageHeader/Toolbar/ActionBar/DataSection/ModalShell/ScanPanel/StatusBadge/SummaryCard/ErrorNotice`
- **없음(규칙은 요구)**: `SmartLookupModal`/`SmartCommonCodeSelect` 등 **공통 고객사/창고/상품 선택 컴포넌트** → AGENTS·CLAUDE가 명시 요구하지만 미구현
- 실측: **15개 화면이 각자 `listClients` 호출 + 개별 Select**로 고객사 선택 구현(returns 9, inventory 2, import 2, channels 1, master 1) → 고객 사용자(client 고정) 분기·기본값 처리·옵션 표기 화면마다 제각각일 위험. 창고/상품 선택도 화면별 구현(처리화면 내 listProducts 등)
- 저장/수정 모달: `SmartModalShell`은 있으나 저장 버튼 로딩/disabled/에러표기 패턴은 화면별 자체 구현(공통 SaveBar 없음)

## 3. 로그인/권한/저장 흐름 요약
- 로그인 → `/api/auth/context` → AuthContext(roles/permissions/is_internal·agency·client/client_id/agency_id/client_unit_id=null) → RouteGuard(area)
- API: Bearer 헤더 자동 첨부, 401 시 unauthorized handler. `ApiClientError`가 backend `result_code/message` 보존.
- 저장 검증(backend): `require_roles` + `require_permission` + `resolve_effective_client_id`(고객=자기 client 고정, 타 client 차단; 내부=요청값 신뢰).
- FE payload: 마스터/반품 화면은 선택된 clientId를 payload·query에 명시(누락 패턴 미발견). 고객 사용자가 client를 임의 선택하는 화면도 미발견(단, 15개 개별 Select라 보장은 아님 — 2번 위험).

## 4. 저장이 안 될 수 있는 위험 지점 (핵심)
| # | 위험 | 근거 | 증상 |
|---|---|---|---|
| R1 | **FE permission vs BE role 가드 비대칭** | FE는 `hasPermission(MASTER_MANAGE 등)`만 검사(예: CommonCode/ProductDetail). BE master 저장은 `require_roles({SUPER_ADMIN, INTERNAL_ADMIN[,WORKER]})`까지 요구(master_service 99~117) | permission만 가진 사용자(예: AGENCY_ADMIN에 향후 MANAGE 부여 시)는 버튼 활성인데 저장 403 → "저장이 안 됨" |
| R2 | **반품 쓰기 role 목록 vs seed permission 불일치** | `_require_return_prepare`는 role 목록에 CLIENT_ADMIN/CLIENT_USER 포함(222행)하지만 seed에서 두 role엔 `RETURN_PREPARE` 없음(AGENCY_ADMIN만 보유) | 고객 계정이 반품 쓰기 API 호출 시 무조건 403. "고객도 접수 가능" 의도라면 seed 누락, 아니면 role 목록 과대 — **의도 확정 필요** |
| R3 | **권한 403이 화면에서 일반 실패로 보일 수 있음** | 화면별 `toUserMessage(error, fallback)`은 ApiClientError.message를 쓰지만, 일부 흐름은 fallback 고정 문구 사용. PERMISSION_DENIED/CLIENT_SCOPE_DENIED를 구분 표시하는 공통 규칙 없음 | 사용자는 원인 모른 채 "저장 실패"로 인지 → 반복 재시도/재요청 |
| R4 | **창고 라우팅 미설정 시 처리완료 차단(정상 가드지만 혼동 1순위)** | `_ensure_processing_task_can_complete` — v3 검증에서 실측(라우팅 없으면 버튼 비활성+안내) | "저장(처리완료) 안 됨" 신고의 가장 흔한 비버그 원인 |
| R5 | agency_id 없는 데이터 | closing 이벤트는 `clients.agency_id` fallback 있음 → 저장 차단은 안 됨. 단 agency 리포트/scope 집계 누락 가능 | 저장은 되나 대리점 통계 빠짐 |
| R6 | 필드명 불일치 | types/returns.ts·schemas 대조상 불일치 미발견(snake_case 일치). 단 자동 검증 장치 없음 | 향후 회귀 위험만 |

"저장 성공처럼 보이나 DB 미반영": closing/judge는 commit+refresh 후 응답이라 해당 패턴 미발견. idempotency_key로 중복 반영도 차단됨(v3 검증 실측).

## 5. 화면 수정이 반복 실패하는 원인 후보
1. **규칙 문서 이중 체계**(docs/skills 구버전 vs docs/business·ui 재편) — 작업마다 다른 세트를 참조해 기준이 흔들림. ai-harness references는 양쪽을 혼합 인덱싱.
2. **공통 선택 컴포넌트 부재** — "고객사 선택" 같은 동일 요구를 화면마다 다시 구현 → 수정 지시가 한 화면에만 반영되고 나머지는 그대로.
3. **거대 화면 파일** — `ReturnProcessingWorkspacePage.tsx` 1,690여 줄 단일 파일. 부분 수정 시 컨텍스트 누락/충돌 잦음.
4. R3(에러 불투명)로 인해 "반영 안 됨"과 "권한/라우팅 차단"이 같은 증상으로 보고됨.
5. 지시문에 "대상 파일/컴포넌트 경로"가 없으면 작업자가 유사 파일을 다르게 고를 수 있음(협업 규칙 부재).

## 6. 규칙 md에 추가해야 할 내용 (제안 — 승인 후 반영)
- (frontend-app/backend-api 공통) **저장 흐름 체크리스트**: 저장 API 변경 시 ① BE role+permission 가드 ② seed 권한 ③ FE 버튼 가드 ④ payload 필드명 4종을 한 세트로 확인.
- **저장 가능 role 매트릭스**(업무×role 표: master/returns/import/inventory) 1장 — R1/R2 류 비대칭 예방.
- **에러 표시 규칙**: PERMISSION_DENIED/CLIENT_SCOPE_DENIED/WAREHOUSE_REQUIRED는 일반 실패 문구로 덮지 말고 backend message 그대로 노출.
- **문서 정본 선언**: docs/skills(구) vs docs/business·ui(재편) 중 정본 지정, 나머지는 archive 표시.

## 7. 공통 컴포넌트로 정리해야 할 후보 (우선순위순)
1. `SmartClientSelect`(고객사 선택; 고객 사용자=고정 표시, 내부/대리점=선택) — 15개 화면 치환 대상
2. `SmartWarehouseSelect` / `SmartProductLookup`(상품 검색·스캔 결합)
3. `SmartSaveBar`(저장 버튼+로딩+권한 disabled+에러 표준 표기)
4. `SmartCommonCodeSelect`(규칙에 명시되어 있으나 미구현)

## 8. 즉시 수정 추천 (승인 시 별도 작업으로)
1. **R2 의도 확정 + 정합**: 고객 반품접수 허용 여부 결정 → seed(RETURN_PREPARE) 또는 role 목록 한쪽 수정 + 테스트.
2. **R3 에러 표기**: 공통 `toUserMessage`가 403/scope 계열 result_code를 구분 노출하도록 1곳 수정.
3. **규칙 1쪽 추가**: "저장 흐름 체크리스트" + role 매트릭스(문서만, 코드 무변경).

## 9. 나중에 수정해도 되는 항목
- SmartClientSelect 등 공통 선택 컴포넌트 도입(15개 화면 치환 — 효과 크지만 범위 큼, Phase로 분할)
- ReturnProcessingWorkspacePage 분할 리팩터
- docs/skills↔docs 정본 정리(아카이브 이동)
- R5 agency_id backfill, R6 필드명 자동 대조(스키마 스냅샷 테스트)

## 10. Fable + 똘망이 + Codex 협업 규칙 제안
- **지시문 필수 필드**: 대상 화면 route + **대상 파일 경로** + 사용할 공통 컴포넌트 명시(없으면 "신규 금지, 보고").
- **레인 고정**: Codex=backend(service/seed/test), Fable+똘망이=frontend+브라우저 검증. 같은 파일 동시 수정 금지(기존 규칙 유지).
- **저장 기능 작업은 항상 4종 세트 확인**(6번 체크리스트)을 지시문 템플릿(goal-instruction-template)에 추가.
- **검증 분담**: 구현자 외 검수(똘망이 브라우저 스모크 → Codex 코드리뷰) 후 커밋 승인 요청 — 현 번호 큐 방식 유지가 효과적이었음(001~010).
- 화면 수정 지시는 "변경 전/후 스크린샷 또는 DOM 검증 포인트"를 완료 조건에 포함(반영 안 됨 분쟁 차단).

## 11. 앱 코드 수정 여부
- **없음.** (작업트리의 `return_intake_service.py` 수정 + `test_closing_reflected_message.py`는 **직전 승인 대기 작업**(마감 메시지 문구)의 잔여이며 이번 점검과 무관, 미변경 유지)

## 12. 커밋 필요 여부
- 본 보고서 1개 신규. **승인 전 커밋하지 않음.** push 금지 유지.
