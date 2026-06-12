# 012 backend 권한/seed/API guard 정합화 보고서

작성일: 2026-06-11

## 1. 작업 전 상태

- `git status --short`: backend 변경 전에는 현재 세션 기준 추적 변경 없음, 이후 별도 세션으로 보이는 frontend/portal 변경이 작업트리에 존재함.
- `git status --short -uno`: 작업 전 기준 추적 변경 없음.
- branch: `smartreturn-pro`
- remote: `origin https://github.com/ahgoon2-design/smartreturn-pro.git`
- HEAD: `031a2afc`
- 최근 커밋: `031a2afc docs(harness): add screen build verify review templates`
- push: 수행하지 않음
- commit: 사용자 승인 전 금지 정책에 따라 수행하지 않음

## 2. 확인한 권한/role/permission 구조

확인 파일:

- `backend/app/core/permissions.py`
- `backend/app/core/auth_context.py`
- `backend/app/core/dependencies.py`
- `backend/app/core/error_handlers.py`
- `backend/app/seed/roles_permissions.py`
- `backend/app/services/return_intake_service.py`
- `backend/app/routers/returns.py`
- `backend/tests/test_seed_roles_permissions.py`
- `backend/tests/test_return_intake_api.py`
- `backend/tests/test_permissions.py`
- `backend/tests/test_auth_error_responses.py`

현재 구조:

- `require_roles`는 role을 확인하고 실패 시 `PERMISSION_DENIED` 403을 반환한다.
- `require_permission`은 permission을 확인하고 실패 시 `PERMISSION_DENIED` 403을 반환한다.
- `resolve_effective_client_id`는 CLIENT 계정의 타 고객사 접근을 `CLIENT_SCOPE_DENIED` 403으로 차단한다.
- FastAPI 공통 error handler는 `AuthError`를 `ApiResult` 형식의 401/403 응답으로 변환한다.
- `/api/returns` router는 대부분 service 함수에 guard를 위임한다.

## 3. 발견한 문제

기존 `return_intake_service._require_return_prepare`는 다음 의미를 동시에 갖고 있었다.

- 고객포털 반품 접수/예정자료 등록
- 내부 운영자의 반품 처리 준비
- 반품처리 수동 row 생성
- 판정 확정
- 일마감 확정
- 외부반출/폐기 확정

그 결과 `CLIENT_ADMIN` / `CLIENT_USER`를 role 목록에 포함하면서도 seed에는 `RETURN_PREPARE`가 없어 고객 접수/업로드는 막힐 수 있고, 반대로 seed를 단순히 열면 내부 처리 권한까지 섞일 위험이 있었다.

## 4. 최종 권한 매트릭스

| role | 고객포털 접수/업로드 | 자기 데이터 조회 | 내부 반품 처리/수동 row | 판정 확정 | 일마감 확정 | 외부반출/폐기 확정 | 비고 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `SUPER_ADMIN` | 가능 | 전체 가능 | 가능 | 가능 | 가능 | 가능 | `require_roles` 우회, 전체 permission 보유 |
| `INTERNAL_ADMIN` | 가능 | 내부 범위 가능 | 가능 | 가능 | 가능 | 가능 | `RETURN_PREPARE/PROCESS/JUDGE/CLOSE/OUTBOUND` 기준 |
| `INTERNAL_WORKER` | 제한 | 내부 범위 가능 | 가능 | 가능 | 가능 | 가능 | seed에는 내부 처리/판정/마감/반출 permission 보유, `RETURN_PREPARE`는 없음 |
| `AGENCY_ADMIN` | 가능 | 자기 agency/client scope | 가능 | 가능 | 가능 | 가능 | 기존 seed가 내부 처리 permission을 보유하므로 이번 작업에서는 확장/축소하지 않고 기존 정책 유지 |
| `CLIENT_ADMIN` | 가능 | 자기 client 가능 | 불가 | 불가 | 불가 | 불가 | `RETURN_CLIENT_SUBMIT`만 부여, 내부 처리 permission 없음 |
| `CLIENT_USER` | 가능 | 자기 client 가능 | 불가 | 불가 | 불가 | 불가 | `RETURN_CLIENT_SUBMIT`만 부여, 내부 처리 permission 없음 |
| `READ_ONLY` | 불가 | 허용 scope 조회 | 불가 | 불가 | 불가 | 불가 | write permission 없음 |

## 5. 수정 파일 목록

- `backend/app/seed/roles_permissions.py`
- `backend/app/services/return_intake_service.py`
- `backend/tests/test_return_intake_api.py`
- `backend/tests/test_seed_roles_permissions.py`
- `ai-harness/reports/012-auth-save-policy-fix-report.md`

frontend 파일은 수정하지 않았다.

## 6. seed 변경 내용

추가 permission:

- `RETURN_CLIENT_SUBMIT`: 고객포털에서 자기 고객사의 반품 접수/예정자료 등록 또는 업로드에 사용하는 권한

role-permission 변경:

- `CLIENT_ADMIN`: `RETURN_CLIENT_SUBMIT` 추가
- `CLIENT_USER`: `RETURN_CLIENT_SUBMIT` 추가
- `CLIENT_ADMIN` / `CLIENT_USER`에는 `RETURN_PREPARE`, `RETURN_PROCESS`, `RETURN_JUDGE`, `RETURN_CLOSE`, `RETURN_OUTBOUND`를 부여하지 않음

## 7. API guard 분리 내용

`return_intake_service`에 다음 guard를 추가해 기존 `_require_return_prepare`의 과도한 의미를 분리했다.

- `_require_return_intake_submit`: 고객포털 접수/업로드 및 내부 접수 등록
- `_require_return_internal_prepare`: 내부 처리대상 전환, 운영단위 배정
- `_require_return_process`: 내부 처리 row 생성, 처리 증빙 업로드/비활성
- `_require_return_judge`: 반품 판정, 보류 처리, 재판정
- `_require_return_close`: 일마감 확정
- `_require_return_outbound`: 외부반출/폐기 확정

적용 기준:

- batch 생성, row paste, validate는 고객포털 제출 guard를 사용한다.
- 처리대상 전환과 운영단위 배정은 내부 준비 guard를 사용한다.
- `/processing/manual-rows`, 처리 증빙 변경은 내부 처리 guard를 사용한다.
- `/processing/tasks/{task_id}/judge`, 보류/재판정은 판정 guard를 사용한다.
- `/closing/confirm`은 마감 guard를 사용한다.
- `/external-outbound/confirm`, `/disposal/tasks/{task_id}/confirm`은 반출 guard를 사용한다.

## 8. CLIENT_ADMIN/CLIENT_USER 가능/불가 작업

가능:

- 자기 고객사 기준 `RETURN_VIEW` 조회
- 자기 고객사 반품 접수 batch 생성
- 자기 고객사 반품 예정자료 row paste
- 자기 고객사 반품 접수자료 validate
- 자기 고객사 처리현황 조회에 필요한 조회 scope

불가:

- 타 `client_id`로 접수자료 생성
- 내부 반품 처리완료/판정 확정
- 내부 수동 처리 row 생성
- 일마감 확정
- 외부반출 확정
- 폐기 확정

## 9. SUPER_ADMIN/INTERNAL_ADMIN/WORKER/AGENCY_ADMIN 가능 작업

- `SUPER_ADMIN`: 전체 permission과 role guard 우회로 전체 가능
- `INTERNAL_ADMIN`: 내부 접수 준비, 처리, 판정, 일마감, 외부반출 가능
- `INTERNAL_WORKER`: seed 기준 처리/판정/마감/외부반출 가능, `RETURN_PREPARE`는 미보유라 내부 접수 준비 전환은 제한
- `AGENCY_ADMIN`: 기존 seed 기준 `RETURN_PREPARE/PROCESS/JUDGE/CLOSE/OUTBOUND`를 보유하므로 agency scope 내 내부 운영성 API도 가능하다. 이번 작업에서는 정책을 바꾸지 않고 보고서에 명시했다.

## 10. 추가/수정한 테스트 목록

수정:

- `backend/tests/test_seed_roles_permissions.py`
  - `RETURN_CLIENT_SUBMIT` seed 존재 확인
  - CLIENT role이 고객포털 제출 권한은 갖고 내부 처리 permission은 갖지 않는지 확인

추가:

- `test_client_user_can_submit_own_return_intake_but_not_other_client`
- `test_client_admin_without_portal_submit_permission_is_blocked`
- `test_client_user_cannot_confirm_internal_return_processing`
- `test_client_admin_cannot_confirm_return_closing`
- `test_client_user_cannot_confirm_external_outbound`
- `test_internal_worker_can_confirm_processing_with_operation_permission`

## 11. 고객포털 접수/업로드와 내부 처리 권한 분리 방식

고객포털 접수/업로드는 `RETURN_CLIENT_SUBMIT`으로 분리했다.

내부 처리 계열은 기존 내부 permission을 계속 사용한다.

- 내부 준비: `RETURN_PREPARE`
- 내부 처리: `RETURN_PROCESS`
- 판정 확정: `RETURN_JUDGE`
- 일마감 확정: `RETURN_CLOSE`
- 외부반출/폐기 확정: `RETURN_OUTBOUND`

이 분리로 고객 role에 `RETURN_PREPARE`를 열지 않아도 고객포털 등록이 가능하고, 고객 role이 내부 처리 API guard를 통과하지 못한다.

## 12. 권한 차단 응답

확인 결과:

- 인증 없음: 401, `NOT_AUTHENTICATED`
- permission/role 부족: 403, `PERMISSION_DENIED`
- 타 고객사 scope 접근: 403, `CLIENT_SCOPE_DENIED`
- 일반 500으로 뭉개지지 않음

frontend 공통 에러 표시 개선은 이번 작업 범위 밖이며 후속 검수 필요 항목으로 남긴다.

## 13. 실행한 테스트 명령과 결과

실행:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; backend\.venv\Scripts\python.exe -m pytest -p no:cacheprovider backend\tests\test_seed_roles_permissions.py backend\tests\test_return_intake_api.py -q
```

결과:

```text
92 passed in 99.75s
```

실행:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; backend\.venv\Scripts\python.exe -m pytest -p no:cacheprovider backend\tests\test_permissions.py backend\tests\test_auth_error_responses.py -q
```

결과:

```text
19 passed in 2.34s
```

실행:

```powershell
git diff --check
```

결과:

- 오류 없음
- CRLF 변환 경고만 표시됨

참고:

- 기본 `python -m pytest`는 현재 shell의 hermes python에 pytest가 없어 실패했다.
- `python -m py_compile`은 pycache 파일 쓰기 권한 문제로 실패했다.
- 이후 `backend\.venv\Scripts\python.exe`와 `-p no:cacheprovider`로 테스트를 정상 수행했다.

## 14. frontend 후속 필요 항목

이번 작업에서는 frontend를 수정하지 않았다.

후속 검수 필요:

- FE 버튼 노출이 `permission`만 보고 내부 처리 버튼을 활성화하는지 확인
- `RETURN_CLIENT_SUBMIT` 추가에 따른 고객포털 접수/업로드 버튼 permission 조건 정리
- 403 `PERMISSION_DENIED` / `CLIENT_SCOPE_DENIED`를 일반 실패 문구로 뭉개지 않도록 공통 에러 UI 개선

현재 작업트리에 Fable 작업으로 보이는 frontend 변경이 존재한다.

- `frontend/src/layouts/PortalLayout.tsx`
- `frontend/src/routes/routePaths.ts`
- `frontend/src/routes/router.tsx`
- `frontend/src/pages/portal/PortalReturnStatusPage.tsx`

Codex는 위 파일을 수정하지 않았다.

## 15. 남은 위험

- `AGENCY_ADMIN`은 기존 seed에서 내부 처리/마감/반출 permission을 보유한다. 이번 작업에서는 기존 정책 유지로 두었지만, 실제 운영에서 대리점 관리자가 내부 센터 작업을 직접 수행하지 않는 정책이라면 별도 결정이 필요하다.
- 고객포털 batch 생성 schema는 여전히 `client_id`를 필수로 요구한다. backend scope가 타 client_id를 차단하므로 보안상 문제는 없지만, UX/API 편의상 client 계정은 body client_id 생략을 허용할지 후속 검토할 수 있다.
- 기존 `_require_return_prepare` 함수는 호출부를 모두 새 guard로 전환했지만 파일에 남아 있다. 큰 리팩터링을 피하기 위해 삭제하지 않았다.
- 전체 `python -m pytest`는 실행하지 않았다. 이번 변경 영향 범위의 targeted backend 테스트를 우선 수행했다.

## 16. 작업트리 상태

Codex 변경:

- `backend/app/seed/roles_permissions.py`
- `backend/app/services/return_intake_service.py`
- `backend/tests/test_return_intake_api.py`
- `backend/tests/test_seed_roles_permissions.py`
- `ai-harness/reports/012-auth-save-policy-fix-report.md`

동시 작업으로 보이는 변경:

- `frontend/src/layouts/PortalLayout.tsx`
- `frontend/src/routes/routePaths.ts`
- `frontend/src/routes/router.tsx`
- `frontend/src/pages/portal/PortalReturnStatusPage.tsx`
- `ai-harness/instructions/current/101-commit-screen-templates.md`
- `ai-harness/instructions/current/102-customer-portal-status-plan.md`
- `ai-harness/instructions/current/103-customer-portal-status-build.md`
- `ai-harness/instructions/current/104-customer-portal-status-verify-report.md`
- `ai-harness/reports/101-commit-screen-templates-report.md`
- `ai-harness/reports/102-customer-portal-status-plan-report.md`
- `ai-harness/reports/103-customer-portal-status-build-report.md`
- `ai-harness/reports/104-customer-portal-status-final-report.md`

## 17. 커밋 필요 여부

커밋 가능 상태로 보이나, 사용자 승인 전 커밋 금지 지시에 따라 커밋하지 않았다.

권장 커밋 메시지:

```bash
git commit -m "fix: separate portal return submit permissions"
```
