# SPEC-003 반품 쓰기흐름·테넌시 read-only 탐색 보고서

## 0. 검수 범위와 전제

- 이번 검수는 SPEC이 아니라 read-only 탐색이다.
- 이번 검수는 반품처리 모듈 스코프만 확인했다.
- 반품 외 모듈 스코프는 미확인이다.
- 반품 외 모듈의 deny-by-default/RLS/중앙화 격리 구조는 별도 구조 SPEC으로 보류한다.
- UX/Help는 후속 작업이다.
- 보강이 단순 버그수정인지, 로직변경으로 SPEC이 필요한지는 본 보고 기준으로 별도 판단해야 한다.
- 보고서 한계사항: 최초 read-only 검수 시작 시점의 `git status --short` 출력이 보고서에 남지 않았다. 따라서 작업 전 상태는 재현하지 않고 "미수집/출력 누락"으로 기록한다.
- 이 보정은 보고서 문서 보정이며, 반품 쓰기흐름 검수 결론 자체를 바꾸지 않는다.
- 검수 대상 화면은 `ReturnIntakeHubPage`, `ReturnProcessingWorkspacePage`, `ReturnUnitAssignmentPage`, `ReturnHoldManagementPage`, `ReturnDisposalManagementPage`, `ReturnExternalOutboundPage`, `ReturnClosingPage` 7개다.
- 작업 전 확인: 저장소 `C:\smartreturn-pro`, 브랜치 `smartreturn-pro`, 최초 검수 시작 시점 `git status --short` 출력은 미수집/출력 누락, `origin/smartreturn-pro...HEAD` 결과 `0 2`.

## A. 반품 쓰기흐름 검수

### A1. 7화면 실제 API 매핑표

| 화면 | frontend 파일 | 호출 API / method | 호출 함수 | backend router/service/repository | 읽기/쓰기 | mock/stub/미연결 | 근거 |
|---|---|---|---|---|---|---|---|
| ReturnIntakeHubPage | `frontend/src/features/returns/ReturnIntakeHubPage.tsx` | `/api/returns/intake/batches` POST, `/rows/paste` POST, `/validate` POST, `/prepare-processing` POST, 관련 GET | `createReturnIntakeBatch`, `pasteReturnIntakeRows`, `validateReturnIntakeBatch`, `prepareReturnIntakeBatchForProcessing`, `listReturnIntakeBatches`, `listReturnIntakeRows`, `listReturnProcessingTasks` | `backend/app/routers/returns.py` -> `return_intake_service` -> `return_intake_repository` | 읽기+쓰기 | 실제 연결 | [버그수정급 — 이후 SPEC 불요] `ReturnIntakeHubPage.tsx:7`, `:213`, `:305`, `:311`, `:331`, `:357`; `frontend/src/api/returnIntake.ts:47`, `:68`, `:82`, `:88`; `backend/app/routers/returns.py:34`, `:84`, `:115`, `:129`; `backend/app/services/return_intake_service.py:808`, `:874`, `:1048`, `:1100` |
| ReturnProcessingWorkspacePage | `frontend/src/features/returns/ReturnProcessingWorkspacePage.tsx` | `/api/returns/processing/tasks` GET, `/judge` POST, `/manual-rows` POST, `/attachments` POST/GET, `/attachments/{id}/disable` POST | `listReturnProcessingTasks`, `judgeReturnProcessingTask`, `createReturnProcessingManualRow`, `uploadReturnProcessingAttachment`, `listReturnProcessingAttachments`, `disableReturnProcessingAttachment` | `returns.py` -> `list_return_processing_tasks`, `judge_return_processing_task`, `create_return_processing_manual_row`, attachment services | 읽기+쓰기 | 실제 연결. AI 판정 도우미/라벨 출력은 화면상 준비중 | [버그수정급 — 이후 SPEC 불요] `ReturnProcessingWorkspacePage.tsx:8`, `:322`, `:897`, `:963`, `:993`, `:1371`, `:1413`; `returnIntake.ts:135`, `:154`, `:161`, `:168`, `:187`, `:198`; `returns.py:182`, `:210`, `:225`, `:239`, `:266`, `:286`; `return_intake_service.py:1167`, `:1200`, `:1332`, `:1403` |
| ReturnUnitAssignmentPage | `frontend/src/features/returns/ReturnUnitAssignmentPage.tsx` | `/api/returns/intake/unit-assignment-pending` GET, `/api/returns/intake/rows/{row_id}/assign-unit` POST | `listReturnUnitAssignmentPending`, `assignReturnIntakeRowUnit` | `returns.py` -> `list_return_unit_assignment_pending`, `assign_return_intake_row_unit` -> repository pending-row query | 읽기+쓰기 | 실제 연결 | [버그수정급 — 이후 SPEC 불요] `ReturnUnitAssignmentPage.tsx:6`, `:78`, `:116`; `returnIntake.ts:104`, `:119`; `returns.py:143`, `:167`; `return_intake_service.py:987`, `:1015`; `return_intake_repository.py:238` |
| ReturnHoldManagementPage | `frontend/src/features/returns/ReturnHoldManagementPage.tsx` | `/api/returns/hold/candidates` GET, `/api/returns/hold/tasks/{task_id}` PATCH, `/rejudge` POST | `listReturnHoldCandidates`, `updateReturnHoldTask`, `rejudgeReturnHoldTask` | `returns.py` -> hold service -> repository candidate query | 읽기+쓰기 | 실제 연결 | [버그수정급 — 이후 SPEC 불요] `frontend/src/api/returnIntake.ts:336`, `:361`, `:368`; `backend/app/routers/returns.py:469`, `:501`, `:516`; `backend/app/services/return_intake_service.py:2092`, `:2134`, `:2178`; `backend/app/repositories/return_intake_repository.py:493` |
| ReturnDisposalManagementPage | `frontend/src/features/returns/ReturnDisposalManagementPage.tsx` | `/api/returns/disposal/candidates` GET, `/api/returns/disposal/tasks/{task_id}/confirm` POST | `listReturnDisposalCandidates`, `confirmReturnDisposalTask` | `returns.py` -> disposal service -> repository candidate query | 읽기+쓰기 | 실제 연결 | [버그수정급 — 이후 SPEC 불요] `frontend/src/api/returnIntake.ts:386`, `:411`; `backend/app/routers/returns.py:531`, `:563`; `backend/app/services/return_intake_service.py:2243`, `:2285`; `backend/app/repositories/return_intake_repository.py:543` |
| ReturnExternalOutboundPage | `frontend/src/features/returns/ReturnExternalOutboundPage.tsx` | `/api/returns/external-outbound/candidates` GET, `/api/returns/external-outbound/confirm` POST | `listReturnExternalOutboundCandidates`, `confirmReturnExternalOutbound` | `returns.py` -> outbound service -> repository candidate/batch query | 읽기+쓰기 | 실제 연결 | [버그수정급 — 이후 SPEC 불요] `ReturnExternalOutboundPage.tsx:8`, `:147`, `:208`; `returnIntake.ts:252`, `:278`; `returns.py:381`, `:455`; `return_intake_service.py:1803`, `:1850`; `return_intake_repository.py:324`, `:368`, `:383` |
| ReturnClosingPage | `frontend/src/features/returns/ReturnClosingPage.tsx` | `/api/returns/closing/candidates` GET, `/api/returns/closing/confirm` POST | `listReturnClosingCandidates`, `confirmReturnClosing` | `returns.py` -> closing service -> repository + `inventory_repository` | 읽기+쓰기 | 실제 연결 | [버그수정급 — 이후 SPEC 불요] `ReturnClosingPage.tsx:8`, `:158`, `:191`; `returnIntake.ts:216`, `:235`; `returns.py:339`, `:367`; `return_intake_service.py:1552`, `:1589`; `return_intake_repository.py:275`, `:309`; `inventory_repository.py:12`, `:16`, `:44` |

### A2. 쓰기 액션별 구현 상태

| 액션 | 분류 | 확인 결과 | 근거 |
|---|---|---|---|
| 판정 | 구현됨 | `POST /processing/tasks/{task_id}/judge`가 row 조회, client scope 재검증, 상태/검증값 확인 후 `_apply_return_judgement`를 호출한다. | [버그수정급 — 이후 SPEC 불요] `frontend/src/api/returnIntake.ts:154`, `backend/app/routers/returns.py:210`, `backend/app/services/return_intake_service.py:1332`, `:1347`, `:1375`, `:1381`, `:2546` |
| 처리완료 | 구현됨 | 별도 처리완료 API가 아니라 판정 저장과 함께 `row.status = COMPLETED`로 확정된다. | [버그수정급 — 이후 SPEC 불요] `backend/app/services/return_intake_service.py:2572`; `frontend/src/features/returns/ReturnProcessingWorkspacePage.tsx:853`, `:897`, `:913` |
| 보류/HOLD | 구현됨 | HOLD 판정 시 hold 상태가 `PENDING`으로 생성되고, 관리 화면에서 PATCH 저장 및 POST 재판정을 수행한다. | [버그수정급 — 이후 SPEC 불요] `backend/app/services/return_intake_service.py:2581`, `:2134`, `:2178`; `backend/app/routers/returns.py:501`, `:516`; `frontend/src/api/returnIntake.ts:361`, `:368` |
| 폐기 | 구현됨 | DISPOSAL 판정 후 폐기 확정 API가 row의 `disposal_status`, 사유, 메모, 확정자/확정시각을 저장한다. 정상재고/current_inventory는 변경하지 않는다. | [로직/계약 변경급 — SPEC 먼저] `backend/app/services/return_intake_service.py:2590`, `:2285`, `:2305`, `:2316`; `backend/app/routers/returns.py:563`; `frontend/src/features/returns/ReturnDisposalManagementPage.tsx:164`, `:203` |
| 외부반출 | 구현됨 | 외부반출 대상 후보 조회와 확정 API가 있고, 확정 시 row 상태와 outbound batch를 만든다. 정상재고/current_inventory는 변경하지 않는다. | [로직/계약 변경급 — SPEC 먼저] `backend/app/services/return_intake_service.py:1850`, `:1954`, `:1975`, `:1991`; `backend/app/routers/returns.py:455`; `frontend/src/features/returns/ReturnExternalOutboundPage.tsx:200`, `:208`, `:251` |
| 일마감 | 구현됨 | `POST /closing/confirm`에서 완료 row를 대상으로 `InventoryEvent`를 만들고 `CurrentInventory`를 증가시킨다. | [버그수정급 — 이후 SPEC 불요] `backend/app/services/return_intake_service.py:1589`, `:1729`, `:1759`, `:1760`; `backend/app/repositories/inventory_repository.py:16`, `:44` |
| 재고반영 | 구현됨 | 독립 API는 없고 일마감 확정의 일부로 구현되어 있다. | [로직/계약 변경급 — SPEC 먼저] `frontend/src/features/returns/ReturnClosingPage.tsx:191`; `backend/app/services/return_intake_service.py:1729`, `:1759`, `:1760`, `:1770` |

### A3. 정책위반 후보 확인

| 항목 | 결론 | 근거 |
|---|---|---|
| 판정 시점 current_inventory 변경 | 발견하지 못함 | [버그수정급 — 이후 SPEC 불요] 판정 경로는 `_apply_return_judgement`에서 row 상태/후속 상태만 갱신한다. `backend/app/services/return_intake_service.py:1332`, `:1381`, `:2546`, `:2572` |
| 처리완료 시점 current_inventory 변경 | 발견하지 못함 | [버그수정급 — 이후 SPEC 불요] 처리완료는 `row.status = COMPLETED`이며 inventory repository 호출은 closing confirm 경로에서만 확인됐다. `backend/app/services/return_intake_service.py:2572`, `:1729`, `:1759`, `:1760` |
| 판정 시점 inventory_events 생성 | 발견하지 못함 | [버그수정급 — 이후 SPEC 불요] 판정 요청 스키마에 재고 이벤트 입력이 없고, 서비스 판정 경로에 `InventoryEvent` 생성이 없다. `backend/app/schemas/returns.py:274`; `backend/app/services/return_intake_service.py:1332`, `:2546` |
| 처리완료 시점 inventory_events 생성 | 발견하지 못함 | [버그수정급 — 이후 SPEC 불요] `InventoryEvent` 생성은 closing confirm 내부에서 확인된다. `backend/app/services/return_intake_service.py:1729`; `backend/app/models/inventory.py:10` |
| inventory_events 생성 단계 | 일마감 확정에서 사용 확인. 외부반출/폐기 확정에서는 이벤트 생성 발견하지 못함 | [로직/계약 변경급 — SPEC 먼저] 일마감 이벤트 생성 `backend/app/services/return_intake_service.py:1729`, `:1759`; 외부반출/폐기는 상태만 변경 `:1954`, `:2305` |

★정책위반 후보 목록:
- 판정/처리완료 시점의 `current_inventory` 변경 또는 `inventory_events` 생성은 발견하지 못했다.
- [로직/계약 변경급 — SPEC 먼저] 외부반출 확정/폐기 확정이 “확정단계 이후 재고 반영” 정책상 어떤 원장 이벤트를 가져야 하는지는 현재 코드가 상태 변경까지만 수행하므로 별도 SPEC 판단이 필요하다. 근거: `backend/app/services/return_intake_service.py:1954`, `:2305`, `frontend/src/features/returns/ReturnExternalOutboundPage.tsx:251`, `frontend/src/features/returns/ReturnDisposalManagementPage.tsx:164`.

### A4. 중복 차단 확인

| 대상 | service-level guard | DB unique/index | transaction/locking | 상태값 기반 차단 | 결론 |
|---|---|---|---|---|---|
| 중복 마감 | `inventory_reflected_yn` 검사, idempotency key 재조회 | `InventoryEvent.idempotency_key` unique | 명시적 row lock 발견하지 못함 | 있음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:1621`, `:1710`, `:1711`; `backend/app/models/inventory.py:13`; `inventory_repository.py:12` |
| 중복 외부반출 | 이미 `CONFIRMED`면 skip | outbound batch `batch_no` unique만 확인 | 명시적 row lock 발견하지 못함 | 있음 | [로직/계약 변경급 — SPEC 먼저] `return_intake_service.py:1892`, `:1975`; `backend/app/models/returns.py:181`; row별 idempotency/unique는 발견하지 못함 |
| 중복 폐기 | 이미 `CONFIRMED`면 오류 | disposal row별 unique/idempotency 발견하지 못함 | 명시적 row lock 발견하지 못함 | 있음 | [로직/계약 변경급 — SPEC 먼저] `return_intake_service.py:2302`; `backend/app/models/returns.py:41` |
| 중복 inventory_events | idempotency key 재조회 | `uq_inventory_events_idempotency_key` | 명시적 row lock 발견하지 못함 | 있음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:1710`, `:1711`; `backend/app/models/inventory.py:13`; `inventory_repository.py:12` |
| 중복 재고반영 | `inventory_reflected_yn`, existing event skip | current inventory unique scope 있음 | 명시적 row lock 발견하지 못함 | 있음 | [로직/계약 변경급 — SPEC 먼저] `return_intake_service.py:1621`, `:1711`, `:1770`; `backend/app/models/inventory.py:49` |

### A5. OVER/초과 이력 처리 확인

- [로직/계약 변경급 — SPEC 먼저] `OVER`, `EXCESS`, `SURPLUS`, `초과` 전용 enum/status/분기/화면 표시는 검수 대상 반품 화면·서비스·스키마·모델에서 발견하지 못했다. 검색 결과는 `warehouse_override_reason` 및 일반 frontend `overrides`만 확인됐다. 근거: `backend/app/services/return_intake_service.py:428`, `:492`, `:542`, `:766`; `frontend/src/features/returns/ReturnHistoryPage.tsx:196`.
- OVER/초과 이력이 삭제되는지, 무시되는지, 정상 확정 가능 건과 확인필요 건으로 분리되는지는 현재 코드 근거로 확인할 수 없다. 별도 정책/SPEC 확인이 필요하다.

### A6. 판정별 warehouse_id 처리 확인

- [버그수정급 — 이후 SPEC 불요] frontend는 판정 저장 가능 조건에 `selectedWarehouseRoute?.warehouse_id`를 포함하고, 저장 handler에서도 창고 미확정 시 처리완료를 차단한다. 근거: `frontend/src/features/returns/ReturnProcessingWorkspacePage.tsx:267`, `:282`, `:885`.
- [버그수정급 — 이후 SPEC 불요] backend도 처리완료 직전 `_ensure_processing_task_can_complete`에서 판정별 라우트/창고를 재계산하고 창고가 없으면 오류를 던진다. 근거: `backend/app/services/return_intake_service.py:2416`, `:2424`, `:2430`.
- [버그수정급 — 이후 SPEC 불요] 고객사/운영단위별 창고 범위는 `client_id`, `client_unit_id` 라우트 조회 후 활성 고객사 창고 매핑으로 재검증한다. 근거: `backend/app/services/return_intake_service.py:2474`, `:2481`, `:2500`; `backend/app/models/master.py:141`.
- [로직/계약 변경급 — SPEC 먼저] 양품 GOOD은 고객사 기본 반품/입고 창고 fallback을 사용한다. 이 동작은 “임의 자동 선택”은 아니지만 정책상 고객사 기본 창고 사용 허용 범위를 SPEC에서 명확히 해야 한다. 근거: `backend/app/services/return_intake_service.py:2426`, `:2459`.

### A7. 사진 필수 강제 여부 확인

- [버그수정급 — 이후 SPEC 불요] 판정 request schema에는 사진/첨부 필드가 없고, 사진은 별도 attachment API로 분리되어 있다. 근거: `backend/app/schemas/returns.py:274`, `:352`; `backend/app/routers/returns.py:239`.
- [버그수정급 — 이후 SPEC 불요] 처리 화면은 “사진이 없어도 처리완료 가능” 문구를 노출하고, upload handler는 선택된 파일이 있을 때만 업로드한다. 근거: `frontend/src/features/returns/ReturnProcessingWorkspacePage.tsx:929`, `:963`, `:1530`.
- [버그수정급 — 이후 SPEC 불요] HOLD/폐기 화면도 사진 선택사항 문구가 있다. 근거: `frontend/src/features/returns/ReturnHoldManagementPage.tsx:381`; `frontend/src/features/returns/ReturnDisposalManagementPage.tsx:270`, `:331`.
- 사진 필수 강제 코드나 DB NOT NULL 형태의 첨부 필수 연결은 발견하지 못했다.

## B. 테넌트 스코프 검수 — 반품 엔드포인트 한정

### B1. 쓰기 API의 backend 스코프 재검증

| 쓰기 API | scope/권한 확인 | 프론트 값 신뢰 위험 | 결론 |
|---|---|---|---|
| `POST /intake/batches` | `_require_return_intake_submit`, `resolve_effective_client_id`, client unit 검증 | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:808`, `:810`, `:816`; `auth_context.py:119` |
| `POST /intake/batches/{batch_id}/rows/paste` | batch를 auth scope로 조회, unit이 batch client와 일치하는지 검증 | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:874`, `:881`, `:886`, `:893` |
| `POST /intake/batches/{batch_id}/validate` | batch auth scope 조회 | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:1048`, `:1050` |
| `POST /intake/batches/{batch_id}/prepare-processing` | 내부 role/permission + batch auth scope 조회 | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:1100`, `:1101`, `:1102` |
| `POST /intake/rows/{row_id}/assign-unit` | 내부 prepare role + row client scope + client unit 검증 | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:1015`, `:1021`, `:1026`, `:1031` |
| `POST /processing/manual-rows` | RETURN_PROCESS role + requested client scope + product/client_unit 검증 | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:1200`, `:1205`, `:1206`, `:1221` |
| `POST /processing/tasks/{task_id}/judge` | RETURN_JUDGE role + row client scope + 상태/상품/창고 검증 | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:1332`, `:1338`, `:1347`, `:1375` |
| attachment upload/disable | RETURN_PROCESS role + row client scope | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:1403`, `:1414`, `:2609`, `:2618` |
| `POST /closing/confirm` | RETURN_CLOSE role + requested row ids를 effective client로 제한 + row별 client scope 재검증 | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:1589`, `:1594`, `:1595`, `:1597`, `:1620`; `return_intake_repository.py:309`, `:319` |
| `POST /external-outbound/confirm` | RETURN_OUTBOUND role + requested row ids를 effective client로 제한 + row별 client scope 재검증 | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:1850`, `:1855`, `:1856`, `:1863`, `:1891`; `return_intake_repository.py:368`, `:378` |
| `PATCH /hold/tasks/{task_id}` | RETURN_JUDGE role + row client scope | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:2134`, `:2140`, `:2145` |
| `POST /hold/tasks/{task_id}/rejudge` | RETURN_JUDGE role + row client scope | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:2178`, `:2184`, `:2189` |
| `POST /disposal/tasks/{task_id}/confirm` | RETURN_OUTBOUND role + row client scope | 낮음 | [버그수정급 — 이후 SPEC 불요] `return_intake_service.py:2285`, `:2291`, `:2296` |

스코프 누락 엔드포인트 목록:
- 반품 쓰기 API에서 명백한 client scope 누락 엔드포인트는 발견하지 못했다.
- [로직/계약 변경급 — SPEC 먼저] 다만 `ReturnExternalOutboundBatch`는 `client_id`가 nullable이고, 외부반출 확정 시 여러 client가 섞이는 경우 batch client를 `effective_client_id` 또는 `None`으로 둘 수 있는 구조다. 현 화면은 selected client 기반으로 호출하지만, batch 단위 테넌시 계약은 별도 SPEC에서 명확히 하는 편이 안전하다. 근거: `backend/app/models/returns.py:190`; `backend/app/services/return_intake_service.py:1972`, `:1974`, `:1975`; `backend/app/repositories/return_intake_repository.py:416`.

### B2. 권한 실패/타 고객사 접근 응답 패턴

- [버그수정급 — 이후 SPEC 불요] `ClientScopeDeniedError`와 `PermissionDeniedError`는 403 계열로 정의되어 있고, 공통 error handler가 `status_code=exc.status_code`로 응답한다. 근거: `backend/app/core/exceptions.py:53`, `:59`; `backend/app/core/error_handlers.py:13`, `:19`.
- [버그수정급 — 이후 SPEC 불요] 인증 실패는 401, 권한/스코프 실패는 403 패턴이다. 근거: `backend/app/core/exceptions.py:29`, `:53`, `:59`.
- [로직/계약 변경급 — SPEC 먼저] row 조회 자체는 repository에서 id만으로 찾은 뒤 service에서 `resolve_effective_client_id`로 403을 내는 패턴이 섞여 있다. 클라이언트 존재 여부 정보노출을 404로 숨길지, 403으로 명시할지는 공통 API 계약 SPEC에서 결정해야 한다. 근거: `backend/app/repositories/return_intake_repository.py:229`; `backend/app/services/return_intake_service.py:1339`, `:1347`; `backend/app/core/auth_context.py:134`, `:137`.

### B3. 반품 관련 모델의 테넌시 컬럼 보유표

| 모델 | agency_id | client_id | client_unit_id | warehouse_id | created_by/updated_by | FK/Index/Unique | 근거 |
|---|---|---|---|---|---|---|---|
| ReturnDownloadBatch | 발견하지 못함 | 발견하지 못함 | 발견하지 못함 | 발견하지 못함 | 발견하지 못함 | 모델명 발견하지 못함 | [로직/계약 변경급 — SPEC 먼저] `rg class ReturnDownload` 결과 없음 |
| ReturnDownloadRow | 발견하지 못함 | 발견하지 못함 | 발견하지 못함 | 발견하지 못함 | 발견하지 못함 | 모델명 발견하지 못함 | [로직/계약 변경급 — SPEC 먼저] `rg class ReturnDownload` 결과 없음 |
| ReturnIntakeBatch | O | O | O | X | created_by O / updated_by X | agency/client/client_unit index | [버그수정급 — 이후 SPEC 불요] `backend/app/models/returns.py:10`, `:13`, `:20`, `:21`, `:22`, `:29` |
| ReturnIntakeRow | O | O | O | recommended/final warehouse O | assigned_by/judged_by 등 O / updated_by X | client/status/unit/judgement/warehouse indexes, label unique | [버그수정급 — 이후 SPEC 불요] `backend/app/models/returns.py:41`, `:45`, `:49`, `:50`, `:51`, `:52`, `:87`, `:88`, `:89`, `:118`, `:119` |
| ReturnProcessingAttachment | O | O | X | X | uploaded_by O / updated_by X | agency/client, row, uploaded indexes | [버그수정급 — 이후 SPEC 불요] `backend/app/models/returns.py:208`, `:211`, `:213`, `:217`, `:219`, `:224` |
| ReturnExternalOutboundBatch | O | O nullable | X | X | created_by/confirmed_by O / updated_by X | batch_no unique, agency/client index | [로직/계약 변경급 — SPEC 먼저] `backend/app/models/returns.py:179`, `:181`, `:183`, `:189`, `:190`, `:199`, `:201` |
| InventoryEvent | O | O | X | O | created_by O / updated_by X | event_no/idempotency unique, stock scope index | [버그수정급 — 이후 SPEC 불요] `backend/app/models/inventory.py:10`, `:13`, `:15`, `:19`, `:24`, `:25`, `:26`, `:40` |
| CurrentInventory | O | O | X | O | X / X | client/warehouse/location/product/status unique, stock scope index | [버그수정급 — 이후 SPEC 불요] `backend/app/models/inventory.py:45`, `:49`, `:56`, `:59`, `:63`, `:64`, `:65` |
| ClientUnit | O | O | 자기 id | default/return warehouse O | X / updated_at O | client/unit unique, agency/client index | [버그수정급 — 이후 SPEC 불요] `backend/app/models/master.py:111`, `:114`, `:115`, `:122`, `:123`, `:127`, `:128` |
| ReturnJudgmentWarehouseRoute | O | O | O nullable | O | X / updated_at O | client/unit/judgment/warehouse unique, scope indexes | [버그수정급 — 이후 SPEC 불요] `backend/app/models/master.py:141`, `:144`, `:151`, `:158`, `:159`, `:160`, `:162` |
| ScanCore 계열 | 발견하지 못함 | 발견하지 못함 | 발견하지 못함 | 발견하지 못함 | 발견하지 못함 | 검수 범위 내 모델명 발견하지 못함 | [로직/계약 변경급 — SPEC 먼저] `rg class Scan` 결과 없음 |

## C. 다음 격리 SPEC용 구조 메모

### C1. 공통 base model/mixin 존재 여부

- [로직/계약 변경급 — SPEC 먼저] `backend/app/db/base.py`에는 SQLAlchemy `DeclarativeBase`만 있고 `TenantScopedModel` 또는 테넌시 강제 mixin은 발견하지 못했다. 근거: `backend/app/db/base.py:1`, `:4`.
- [로직/계약 변경급 — SPEC 먼저] 테넌시 컬럼은 모델별로 수동 선언되어 있다. 근거: `backend/app/models/returns.py:20`, `:87`; `backend/app/models/inventory.py:24`, `:63`; `backend/app/models/master.py:96`, `:122`, `:158`.

### C2. 스코프 강제 방식 한 줄 결론

- [로직/계약 변경급 — SPEC 먼저] 결론: 혼재. `resolve_effective_client_id`와 role/permission helper로 service-level 검증은 반복 적용되어 있으나, repository/base model/RLS로 완전 중앙화된 형태는 아니다. 근거: `backend/app/core/auth_context.py:119`; `backend/app/services/return_intake_service.py:217`, `:249`, `:261`, `:267`; `backend/app/repositories/return_intake_repository.py:195`, `:275`, `:324`, `:543`.

### C3. PostgreSQL RLS 사용 여부

- [로직/계약 변경급 — SPEC 먼저] `backend/alembic`, `docs` 범위에서 `CREATE POLICY`, `ENABLE ROW LEVEL SECURITY`, `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`, `GRANT` 흔적을 발견하지 못했다.
- 결론: 미사용으로 판단한다. 단, 반품 외 모듈 전체 DB 정책은 이번 검수 범위 밖이다.

### C4. 다음 신규 SPEC 번호 확정

- 확인한 SPEC 파일:
  - `docs/specs/SPEC-001-grade-based-inventory-closing.md`
  - `docs/specs/SPEC-002-inventory-status-by-stock-status.md`
  - `docs/specs/SPEC-003-scan-first-return-processing.md`
- max 번호: `003`
- 다음 신규 SPEC 번호: `SPEC-004`
- 번호 충돌: 발견하지 못함.

## 결론 요약

### 1. ★정책위반 후보 목록

- 판정/처리완료 시점에 `current_inventory` 변경 또는 `inventory_events` 생성은 발견하지 못했다.
- [로직/계약 변경급 — SPEC 먼저] 외부반출 확정/폐기 확정이 재고 원장 이벤트를 만들어야 하는지 현재 정책 문구만으로는 계약이 불명확하다. 현재 구현은 상태 변경까지만 수행한다. 근거: `backend/app/services/return_intake_service.py:1954`, `:2305`.

### 2. 미구현/스텁 쓰기액션 목록

- [로직/계약 변경급 — SPEC 먼저] OVER/초과 이력 처리: 전용 enum/status/분기/화면 표시 발견하지 못함.
- [로직/계약 변경급 — SPEC 먼저] 독립 재고반영 API: 발견하지 못함. 현재 재고반영은 일마감 확정의 일부다.
- [로직/계약 변경급 — SPEC 먼저] 외부반출/폐기 확정 후 재고 원장 이벤트: 발견하지 못함.
- [버그수정급 — 이후 SPEC 불요] AI 판정 도우미와 라벨 출력은 화면상 준비중 표시다. 쓰기흐름 필수 API로 연결된 상태는 아니다. 근거: `frontend/src/features/returns/ReturnProcessingWorkspacePage.tsx:1371`, `:1413`.

### 3. 스코프 누락 엔드포인트 목록

- 명백한 반품 쓰기 API client scope 누락은 발견하지 못했다.
- [로직/계약 변경급 — SPEC 먼저] `ReturnExternalOutboundBatch.client_id` nullable 및 다중 client batch 가능성은 batch 단위 테넌시 계약을 별도 구조 SPEC에서 확정할 필요가 있다.

### 4. 다음 신규 SPEC 번호

- `SPEC-004`

### 5. 작업 상태 기록

- 작업 전 `git status --short`: 미수집/출력 누락.
- 한계사항: 최초 read-only 검수 시작 시점의 `git status --short` 출력이 보고서에 남지 않았다. 따라서 작업 전 상태는 재현하지 않고 "미수집/출력 누락"으로 기록한다.
- 작업 전 `git rev-list --left-right --count origin/smartreturn-pro...HEAD`: `0 2`.
- 현재 보정 시점 `git status --short`: `?? docs/reports/return-writeflow-tenancy-audit.md`.
- 현재 보정 시점 `git diff --check`: 출력 없음.
- 보정 시점 기준 dirty는 본 보고서 1개뿐이며, 코드/API/DB 변경은 없다.
- 코드/API/DB 변경 0: 코드/API/DB/schema/migration 파일을 수정하지 않았다.
- commit/push 하지 않았음.
