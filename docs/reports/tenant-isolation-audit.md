# 테넌트 격리 현황 점검 보고서

## 1. 점검 개요

- 점검 일시: 2026-06-16
- 브랜치: `smartreturn-pro`
- 실행 모드: 읽기 전용 진단 + 표본 테스트 실행
- 수정 범위: 본 보고서 생성만 수행
- stage/commit/push/stash: 수행하지 않음

## 2. 사전 상태

- `git branch --show-current`: `smartreturn-pro`
- `git status --short`: 기존 dirty/보류 파일이 존재한다.
  - `AGENTS.md`, `docs/skills/*`, `ai-harness/instructions/*`의 Claude/Fable 용어 정리 변경
  - 반품 화면 6개 변경
  - `docs/decisions/tenancy-and-permission-model.md`
  - `docs/reports/return-spine-status-audit.md`
  - `spec-002-login-1366x768.png`
- `git diff --cached --name-only`: 빈 결과. staged 파일 없음.

## 3. 중앙 격리 자물쇠 판정

| 항목 | 판정 | 근거 |
| --- | --- | --- |
| ORM 세션 이벤트 기반 전역 필터 | 없음 | `with_loader_criteria`, `do_orm_execute`, `SessionEvents`, `event.listen`, `BaseRepository` 계열 검색 결과 없음 |
| 공통 dependency 기반 AuthContext | 있음 | `backend/app/core/dependencies.py:48`에서 `get_current_auth_context()`가 현재 사용자 기준 `AuthContext`를 구성 |
| 공통 scope 해석 함수 | 있음 | `backend/app/core/auth_context.py:119` `resolve_effective_client_id()`, `backend/app/core/auth_context.py:157` `resolve_effective_agency_id()` |
| deny-by-default 중앙 쿼리 필터 | 없음 | 리포지토리/서비스가 `client_id`, `agency_id`를 넘겨 필터링하는 opt-in 구조 |

### 종합 판정

- 중앙 자물쇠: 있음(opt-in)
- 의미: API/서비스가 `resolve_effective_client_id()`와 `resolve_effective_agency_id()`를 호출하고, 그 값을 리포지토리에 넘겨야 scope가 적용된다.
- deny-by-default는 아니다. 쿼리 작성자가 필터를 빼먹으면 ORM/DB 계층에서 자동 차단하지 않는다.

## 4. 업무 API scope 표본 점검

| 표본 | 서버 scope 강제 | 근거 |
| --- | --- | --- |
| 반품 history | 확인됨 | 라우터는 `backend/app/routers/returns.py:301`에서 `get_current_auth_context`를 받고, 서비스는 `backend/app/services/return_intake_service.py:1512`에서 `RETURN_VIEW`, `1513`에서 `resolve_effective_client_id()`를 호출, 리포지토리는 `backend/app/repositories/return_intake_repository.py:626`에서 `ReturnIntakeRow.client_id` 필터 적용 |
| 반품 intake 생성/상세 | 확인됨 | 생성은 `backend/app/services/return_intake_service.py:810`에서 요청 client scope를 확정하고, batch 상세/row 계열은 row/batch의 `client_id`에 대해 `resolve_effective_client_id()` 재검증 패턴이 존재 |
| 재고 current | 확인됨 | `backend/app/routers/inventory.py:18` endpoint가 auth를 받고, `backend/app/services/inventory_service.py:32`에서 `INVENTORY_VIEW`, `33~34`에서 client/agency scope 계산, `backend/app/repositories/inventory_repository.py:102~107`, `188~191`에서 필터 적용 |
| 마스터 clients | 확인됨 | `backend/app/routers/master.py:72` endpoint가 `MASTER_VIEW` 후 `get_accessible_clients()` 호출, `backend/app/services/master_service.py:439~447`에서 내부/대리점/고객사 role별 반환 범위 분기 |
| 마스터 products | 확인됨 | `backend/app/routers/master.py:591` endpoint가 `MASTER_VIEW` 후 `get_products()` 호출, `backend/app/services/master_service.py:1177~1184`에서 client/agency scope를 리포지토리에 전달, `backend/app/repositories/master_repository.py:596~599`에서 필터 적용 |

## 5. require_permission 커버리지

| 영역 | 결과 | 근거 |
| --- | --- | --- |
| 공통 권한 함수 | 확인됨 | `backend/app/core/permissions.py:25` `require_permission()` |
| 반품 조회 | 확인됨 | `backend/app/services/return_intake_service.py:217~218` `_require_return_view()` |
| 반품 처리완료/판정 | 확인됨 | `backend/app/services/return_intake_service.py:249~258`에서 `RETURN_PROCESS`, `RETURN_JUDGE` 분리 |
| 반품 일마감 확정 | 확인됨 | `backend/app/services/return_intake_service.py:261~264` `_require_return_close()`가 `RETURN_CLOSE` 요구, `1594`에서 호출 |
| 반품 외부반출 확정 | 확인됨 | `backend/app/services/return_intake_service.py:267~270` `_require_return_outbound()`가 `RETURN_OUTBOUND` 요구, `1855`에서 호출 |
| 반품 폐기 확정 | 부분 구멍 | `backend/app/services/return_intake_service.py:2291`에서 폐기 확정도 `_require_return_outbound()`를 사용한다. 별도 `RETURN_DISPOSAL` 권한은 seed에서 확인되지 않음 |
| 재고 조회 | 확인됨 | `backend/app/services/inventory_service.py:32`, `135`에서 `INVENTORY_VIEW` 요구 |
| 마스터 조회/관리 | 확인됨 | `backend/app/routers/master.py:41`, `47~69`에서 조회/관리 권한 함수 분리 |

### 권한 구멍 판정

- 과거 지목된 "반품 확정 권한 강제 구멍"은 완전 무권한 상태는 아니다.
- 일마감은 `RETURN_CLOSE`, 외부반출은 `RETURN_OUTBOUND`로 `RETURN_VIEW`와 분리되어 있다.
- 단, 폐기 확정은 별도 폐기 권한이 아니라 `RETURN_OUTBOUND`를 재사용하므로 권한 모델 세분화 기준에서는 구멍이다.

## 6. bootstrap / 로그인 권한 재부여 패턴

| 항목 | 결과 | 근거 |
| --- | --- | --- |
| 로그인 시 role/permission 조회 | 확인됨 | `backend/app/services/auth_service.py:98~113`에서 사용자, role, permission, allowed client 목록을 DB에서 읽어 AuthContext 구성 |
| 로그인마다 ADMIN 강제 재부여 | 확인 안 됨 | `backend/app/services/auth_service.py:116~149` 로그인은 token 발급과 login log 기록 중심이며 role 부여/갱신 코드는 없음 |
| 초기 SUPER_ADMIN bootstrap | 확인됨 | `backend/app/seed/super_admin.py:24~31` 초기 관리자 생성 함수, `51~63` 기존 SUPER_ADMIN 있으면 중단, `99`에서 최초 생성 사용자에게만 `UserRole` 추가 |

### 판정

- "매 로그인마다 ADMIN/권한 재부여" 패턴은 발견되지 않았다.
- 로그인은 현재 DB의 role/permission을 매번 읽어 AuthContext를 새로 만드는 구조다.
- 권한 seed/로컬 테스트 계정 seed는 별도 스크립트 영역이며 운영 로그인 흐름과 분리되어 있다.

## 7. 누수 테스트 결과

### 실행 명령

```bash
cd backend
$env:PYTHONDONTWRITEBYTECODE='1'
.\.venv\Scripts\python.exe -m pytest tests/test_auth_context.py tests/test_permissions.py tests/test_master_api_readonly.py::test_client_user_cannot_get_other_client_detail tests/test_master_api_readonly.py::test_products_return_page_data_and_apply_client_scope tests/test_master_api_readonly.py::test_client_user_cannot_request_other_client_products tests/test_master_api_readonly.py::test_product_detail_validates_client_scope tests/test_return_intake_api.py::test_client_user_can_submit_own_return_intake_but_not_other_client tests/test_return_intake_api.py::test_client_user_cannot_access_other_client_batch tests/test_inventory_current_api.py -p no:cacheprovider
```

### 결과

- 33 passed
- 실패 없음
- secret/실계정 열람 없음

### 테스트 근거

| 테스트 | 확인 내용 |
| --- | --- |
| `backend/tests/test_auth_context.py:91~95` | 고객사 사용자가 다른 `client_id` 요청 시 `ClientScopeDeniedError` |
| `backend/tests/test_permissions.py:73~83` | `require_client_access()`가 타 고객사 접근 차단 |
| `backend/tests/test_master_api_readonly.py:287~302` | 고객사 사용자가 다른 고객사 상세 조회 시 403/`CLIENT_SCOPE_DENIED` |
| `backend/tests/test_master_api_readonly.py:361~377` | 상품 목록이 자기 고객사 상품만 반환 |
| `backend/tests/test_master_api_readonly.py:413~419` | 다른 고객사 상품 목록 요청 시 403/`CLIENT_SCOPE_DENIED` |
| `backend/tests/test_return_intake_api.py:476~485` | 고객사 사용자가 다른 고객사 반품 batch 생성 시 403/`CLIENT_SCOPE_DENIED` |
| `backend/tests/test_return_intake_api.py:2915~2921` | 고객사 사용자가 다른 고객사 반품 batch 상세 접근 시 403/`CLIENT_SCOPE_DENIED` |

## 8. 구멍 목록과 위험도

| 위험도 | 구멍 | 근거 | 영향 |
| --- | --- | --- | --- |
| 높음 | 중앙 deny-by-default 쿼리 필터 없음 | ORM 전역 필터/공통 BaseRepository 검색 결과 없음, 리포지토리별 opt-in 필터 구조 | 새 모듈이 scope 함수 호출이나 필터 전달을 누락하면 데이터 누수 가능 |
| 중간 | 폐기 확정 권한이 `RETURN_OUTBOUND`에 묶임 | `backend/app/services/return_intake_service.py:2291` | 폐기 권한을 외부반출 권한과 별도로 통제하기 어려움 |
| 중간 | warehouse scope 중앙 강제 미흡 | `require_warehouse_access()`는 있으나 대표 조회 API는 `warehouse_id`를 리포지토리 필터로 전달하는 방식 | 창고 권한 allow-list가 모듈별로 빠질 수 있음 |
| 낮음 | 대리점 사용자의 전체 client 조회는 `allow_all_clients=True`일 때 `None`으로 흐름 | `backend/app/core/auth_context.py:145~146`, 서비스에서 agency 필터 병행 필요 | agency 필터를 함께 빼먹으면 대리점 범위 초과 위험 |

## 9. 확장 안전 판정

- 현재 반품/재고/마스터 표본은 서버에서 client/agency scope를 적용하고, 표본 테스트도 통과했다.
- 그러나 중앙 deny-by-default가 없으므로 새 재무/ERP/정산 모듈을 바로 대규모 확장하는 것은 안전하지 않다.
- 확장 전 선결:
  1. 공통 scope dependency 또는 BaseRepository 정책을 정하고 새 모듈의 기본 쿼리 계약으로 강제
  2. client/agency/warehouse scope 누락을 잡는 테스트 템플릿 추가
  3. 폐기 확정 전용 권한(`RETURN_DISPOSAL` 또는 동급) 도입 여부 결정
  4. warehouse allow-list/고객사-창고 연결 검증을 조회/확정 API에 일관 적용

## 10. 최종 판정

| 항목 | 판정 |
| --- | --- |
| 중앙 자물쇠 | 있음(opt-in), deny-by-default 아님 |
| 누수 차단 | 표본 기준 확인됨 |
| require_permission | 대체로 확인됨, 폐기 확정 권한 세분화는 미흡 |
| bootstrap 재부여 | 매 로그인 ADMIN 재부여 패턴 없음 |
| 확장 안전 | 조건부 보류. 재무/ERP 대형 확장 전 중앙 scope 강제 슬라이스 필요 |

## 11. 다음 제안

- SPEC 후보: `SPEC-003-tenant-scope-guard-and-permission-hardening`
- 핵심 범위:
  - 공통 `TenantScope` dependency 또는 repository guard 설계
  - `client_id`, `agency_id`, `warehouse_id` scope 테스트 템플릿
  - `RETURN_DISPOSAL` 권한 분리
  - 새 모듈 생성 시 scope 가드 체크리스트 추가
