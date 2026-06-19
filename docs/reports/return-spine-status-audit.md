# SmartReturn Pro 반품 척추 실제 작동 상태 점검

## 1. 점검 개요

- 작성일: 2026-06-13
- 점검 범위: 반품처리, 반품 일마감, 재고 이벤트, 보류/폐기/외부반출 확정, 권한, 사용자/권한 관리 화면·API, 관련 테스트와 프론트 빌드
- 점검 방식: 코드 읽기, 테스트 실행, 프론트 빌드 실행, 미커밋 프론트 반품 화면 diff 확인
- 변경 범위: 이 보고서 1개만 생성했다. 코드 수정과 커밋은 하지 않았다.

## 2. 항목별 점검 결과

| 번호 | 확인 항목 | 판정 | 근거 파일경로 | 근거 요약 |
| --- | --- | --- | --- | --- |
| 1 | 반품 처리(`returns/processing`) 판정 시 `current_inventory`가 변하지 않는지 | 확인됨 | `backend/app/services/return_intake_service.py:1332`, `backend/app/services/return_intake_service.py:2546`, `backend/tests/test_return_intake_api.py:2824` | `judge_return_processing_task()`는 `_apply_return_judgement()`로 row 판정/상태/라벨/후속 상태만 저장한다. `inventory_repository.increase_current_inventory()` 호출은 이 함수 경로에 없다. 실패 케이스 테스트도 `inventory_reflected_yn=False`, `InventoryEvent=0`을 확인한다. |
| 2 | 반품 일마감(`returns/closing`) 확정 시에만 `inventory_events`가 생성되는지, Track A(SKU 바코드)·Track B(반품관리번호 라벨) 두 경로가 다 있는지 | 안 됨 | `backend/app/services/return_intake_service.py:1589`, `backend/app/services/return_intake_service.py:1729`, `backend/app/services/return_intake_service.py:1760`, `backend/tests/test_return_intake_api.py:1470`, `backend/tests/test_return_intake_api.py:1958` | 일마감 확정에서 `InventoryEvent` 생성과 `current_inventory` 증가가 일어나는 것은 확인된다. Track A 성격의 상품코드/바코드 기반 재고반영 테스트도 있다. 다만 Track B를 별도 재고반영 경로로 분리한 코드나 테스트는 확인되지 않았다. 반품관리번호/라벨번호는 event `raw_json`에 보존되지만 별도 Track B 확정 경로로 보기는 어렵다. |
| 3 | 같은 마감을 두 번 확정해도 재고가 중복 반영되지 않는 idempotency 가드가 있는지 | 확인됨 | `backend/app/services/return_intake_service.py:1621`, `backend/app/services/return_intake_service.py:1710`, `backend/app/repositories/inventory_repository.py:12`, `backend/app/models/inventory.py:14`, `backend/tests/test_return_intake_api.py:1489` | row의 `inventory_reflected_yn`으로 1차 skip하고, `return-closing:{row.id}:{stock_status}` idempotency key로 기존 event를 조회한다. `inventory_events.idempotency_key` unique constraint도 있다. 테스트에서 같은 row를 두 번 확정해 event count가 1건임을 확인한다. |
| 4 | 수량 차이/자료 불일치 건이 자동 확정 안 되고 HOLD로 분리되는지 | 안 됨 | `backend/app/services/return_intake_service.py:2696`, `backend/app/services/return_intake_service.py:2416`, `backend/app/services/return_intake_service.py:2581`, `backend/tests/test_return_intake_api.py:2828` | 잘못된 수량은 `INVALID`, 미등록 상품은 `WARNING` 또는 판정 시 `RETURN_PROCESSING_PRODUCT_NOT_FOUND`로 차단된다. 그러나 수량 차이/자료 불일치를 자동 `HOLD` 판정으로 전환하는 로직은 확인되지 않았다. `HOLD`는 작업자가 판정값으로 선택했을 때만 `HOLD_PENDING`으로 설정된다. |
| 5 | returns 확정 액션(마감/외부반출/폐기) 백엔드 권한이 `RETURN_VIEW`와 별개로 세분화돼 있는지 | 확인됨 | `backend/app/services/return_intake_service.py:217`, `backend/app/services/return_intake_service.py:261`, `backend/app/services/return_intake_service.py:267`, `backend/app/seed/roles_permissions.py:122`, `backend/app/seed/roles_permissions.py:152` | 조회는 `RETURN_VIEW`, 마감 확정은 `RETURN_CLOSE`, 외부반출/폐기 확정은 `RETURN_OUTBOUND`를 service 내부에서 요구한다. seed에도 `RETURN_VIEW`, `RETURN_CLOSE`, `RETURN_OUTBOUND`가 별도 권한으로 정의되어 있다. |
| 6 | 사용자/권한 관리 화면·API가 실제로 없는지 | 확인됨 | `frontend/src/layouts/MainLayout.tsx:152`, `backend/app/main.py`, `backend/app/routers/auth.py`, `backend/app/routers/password.py` | 좌측 메뉴에는 `사용자/권한 준비중` disabled 항목만 있다. backend router는 auth/password/master/channels/imports/returns/inventory 등만 include되어 있고 사용자/권한 관리 전용 router는 확인되지 않았다. |
| 7 | 관련 backend test와 frontend build를 돌려 통과/실패 결과 | 확인됨 | 실행 명령 결과 | Backend: `backend/.venv/Scripts/python.exe -m pytest tests/test_return_intake_api.py tests/test_closing_reflected_message.py tests/test_db_models_import.py -p no:cacheprovider` → 89 passed. Frontend: `npm.cmd run build` → 통과. 최초 `npm run build`는 PowerShell 실행 정책으로 실패했고, `npm.cmd run build`의 첫 실행은 sandbox EPERM으로 실패했으나 승인 실행에서 통과했다. |
| 8 | git에 수정된 채 커밋 안 된 반품 화면 6개가 각각 뭘 바꾼 건지 요약 | 확인됨 | `git diff -- frontend/src/features/returns/*.tsx` | 아래 3장에 파일별 1줄 요약을 남겼다. |

## 3. 미커밋 프론트 반품 화면 6개 diff 요약

| 파일 | 1줄 요약 |
| --- | --- |
| `frontend/src/features/returns/ReturnClosingPage.tsx` | Ant Design `Modal.confirm`/`message` 정적 호출을 `Modal.useModal()`/`message.useMessage()` 훅 기반 호출과 context holder 렌더링으로 변경했다. |
| `frontend/src/features/returns/ReturnDisposalManagementPage.tsx` | 폐기 확정 모달과 성공/경고 메시지를 훅 기반 `modal`/`messageApi`로 변경하고 context holder를 추가했다. |
| `frontend/src/features/returns/ReturnExternalOutboundPage.tsx` | 외부반출 스캔 대상 미선택 경고 메시지를 `message.useMessage()` 기반으로 변경하고 context holder를 추가했다. |
| `frontend/src/features/returns/ReturnHoldManagementPage.tsx` | 보류 저장/재판정 경고·성공 메시지를 `messageApi` 기반으로 바꾸고 context holder를 추가했다. |
| `frontend/src/features/returns/ReturnIntakeHubPage.tsx` | 반품자료 저장/검증/처리대상 생성 메시지와 처리대상 생성 confirm을 훅 기반 `messageApi`/`modal`로 변경했다. |
| `frontend/src/features/returns/ReturnUnitAssignmentPage.tsx` | 팀배정 경고/성공/오류 메시지를 `messageApi` 기반으로 변경하고 context holder를 추가했다. |

## 4. 테스트 및 빌드 결과

### Backend

- 명령: `backend/.venv/Scripts/python.exe -m pytest tests/test_return_intake_api.py tests/test_closing_reflected_message.py tests/test_db_models_import.py -p no:cacheprovider`
- 결과: 통과
- 상세: 89 passed in 93.01s

### Frontend

- 1차 명령: `npm run build`
- 결과: 실패
- 원인: PowerShell 실행 정책으로 `npm.ps1` 로드 차단

- 2차 명령: `npm.cmd run build`
- 결과: 실패
- 원인: sandbox 환경에서 Vite/esbuild config load 중 `spawn EPERM`

- 3차 명령: `npm.cmd run build` 승인 실행
- 결과: 통과
- 상세: Vite build 완료, 3109 modules transformed, built in 8.44s
- 경고: 번들 chunk가 500 kB 초과한다는 Vite 경고가 있다.

## 5. 주요 리스크

- Track B(반품관리번호 라벨) 기반 재고 이벤트 확정 경로가 별도 코드/테스트로 분리되어 있지 않다. 현재는 일마감 event `raw_json`에 `return_management_no`와 `return_label_no`를 보존하는 수준으로 보인다.
- 수량 차이/자료 불일치 건을 자동 `HOLD`로 분리하는 정책은 코드로 확인되지 않았다. 현재는 validation 오류/경고 또는 판정 차단 중심이다.
- 라우터 레벨에서는 returns 확정 액션별 권한 Depends가 보이지 않고, service 내부 권한 검증으로 처리한다. 현재 동작상 세분 권한은 확인되지만, 라우터 계약만 보고 권한을 파악하기는 어렵다.
- 사용자/권한 관리는 seed와 auth context 기반은 있으나 관리 화면/API가 없다.

## 6. 보안 및 변경 확인

- `.env`와 `backend/local.secret.json` 내용은 읽거나 출력하지 않았다.
- 코드 수정은 하지 않았다.
- 커밋은 하지 않았다.
- 보고서 작성 전 git 상태에는 프론트 반품 화면 6개만 수정 상태로 남아 있었다.
