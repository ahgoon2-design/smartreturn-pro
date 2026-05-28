# P0 공통코드 관리 API 수동 검증 완료 기록

이 문서는 SmartReturn Pro 신규 기준 문서이며, 기존 SmartReturn 구현 기록을 그대로 복사하지 않는다.

## 검증 목적

P0 기준정보 관리 API 2차 범위인 `common_code_groups`와 `common_codes` 관리 API가 로컬 환경에서 실제로 동작하는지 수동 검증한 결과를 기록한다.

## 검증 환경

- 검증일: 2026-05-28
- 검증 DB: 로컬 개발 DB
- 검증 계정: `local_super_admin`
- `backend/local.secret.json`: git 제외 상태 유지
- 검증 전 전체 테스트: `141 passed`
- `/health`: HTTP 200, `status=ok`, `app_name=SmartReturn Pro`

## AuthContext 확인

- role: `SUPER_ADMIN`
- permissions count: 31
- `MASTER_VIEW`: true
- `COMMON_CODE_MANAGE`: true
- `is_internal_user`: true
- `must_change_password`: false

## 공통코드 그룹 API 검증 결과

아래 API를 Bearer token 기반으로 호출해 정상 동작을 확인했다.

- `POST /api/master/common-code-groups`: HTTP 200, `MASTER_COMMON_CODE_GROUP_CREATED`
- `POST /api/master/common-code-groups`: 같은 `group_code` 중복 생성 차단, HTTP 400
- `PATCH /api/master/common-code-groups/{group_id}`: HTTP 200, `MASTER_COMMON_CODE_GROUP_UPDATED`
- `PATCH /api/master/common-code-groups/{group_id}`: `group_code` 변경 시도 시 기존 값 유지
- `POST /api/master/common-code-groups/{group_id}/disable`: HTTP 200, `MASTER_COMMON_CODE_GROUP_DISABLED`, `active_yn=false`
- `POST /api/master/common-code-groups/{group_id}/enable`: HTTP 200, `MASTER_COMMON_CODE_GROUP_ENABLED`, `active_yn=true`

## 공통코드 API 검증 결과

아래 API를 Bearer token 기반으로 호출해 정상 동작을 확인했다.

- inactive group에 `POST /api/master/common-codes` 요청 시 생성 차단, HTTP 400
- `POST /api/master/common-codes`: HTTP 200, `MASTER_COMMON_CODE_CREATED`
- `POST /api/master/common-codes`: 같은 `group_id + code_value` 중복 생성 차단, HTTP 400
- `PATCH /api/master/common-codes/{code_id}`: HTTP 200, `MASTER_COMMON_CODE_UPDATED`
- `PATCH /api/master/common-codes/{code_id}`: `code_value` 변경 시도 시 기존 값 유지
- `POST /api/master/common-codes/{code_id}/disable`: HTTP 200, `MASTER_COMMON_CODE_DISABLED`, `active_yn=false`
- `POST /api/master/common-codes/{code_id}/enable`: HTTP 200, `MASTER_COMMON_CODE_ENABLED`, `active_yn=true`

## locked/system 제한 검증

- 수동 검증 가능한 `locked_yn=true` 또는 `system_yn=true` 후보 데이터가 없어 수동 검증은 생략했다.
- locked code 수정 차단과 system/locked code disable 차단은 자동 테스트에서 검증된 범위로 기록한다.
- 운영 seed 또는 system code fixture가 생기면 수동 재검증 후보로 남긴다.

## 보안 확인

- 응답 요약에 stack trace, secret, token 전체값, password, `password_hash`가 노출되지 않음을 확인했다.
- `backend/local.secret.json`은 git 추적 및 커밋 대상에 포함되지 않았다.

## 참고 사항

- common code 관리 API는 DELETE 없이 `active_yn` 기반 disable/enable만 사용한다.
- `group_code`와 `code_value`는 생성 후 변경하지 않는 원칙을 유지한다.
- system/locked code 수동 검증용 fixture 정책은 후속으로 검토한다.
