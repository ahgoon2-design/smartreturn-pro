---
name: import-preview
description: >-
  import preview, paste rows, validation 화면과 관련 API 흐름 작업 시 적용하는 import preview
  스킬. POST /api/import-jobs, rows/paste, validate, rows/errors 표시 계약과 import job
  생성·검증·표시 기준을 정리하므로 업로드/붙여넣기 preview 작업 시 반드시 이 스킬을 적용한다.
---

# Import Preview Skill

## 목적

SmartReturn Pro import preview 화면과 관련 API 흐름을 작업할 때 적용할 기준을 정리한다.

## 관련 API 흐름

1. `POST /api/import-jobs`
2. `POST /api/import-jobs/{job_id}/rows/paste`
3. `POST /api/import-jobs/{job_id}/validate`
4. `GET /api/import-jobs/{job_id}/rows`
5. `GET /api/import-jobs/{job_id}/errors`

업로드, 파싱, 업무 테이블 확정은 별도 단계로 분리한다.

## 상태 표시 기준

row 상태:

- `NOT_VALIDATED`: 검증 전
- `VALID`: 정상
- `WARNING`: 경고
- `INVALID`: 오류

job 상태:

- `DRAFT`: 작성 중
- `READY_TO_VALIDATE`: 검증 대기
- `VALIDATED`: 검증 완료
- `HAS_ERRORS`: 오류 있음
- `FAILED`: 실패

상태는 색상만 쓰지 말고 한글 문구와 badge를 함께 사용한다.

## row 순서 기준

- 원본 `row_no` 순서를 기본으로 유지한다.
- 필터를 바꿔도 `row_no asc` 기준을 유지한다.
- 사용자가 원본 순서로 되돌릴 수 있어야 한다.

## 필터 기준

최소 필터:

- 전체 보기
- 오류 행만 보기
- 경고 행만 보기
- 원본 순서 보기

오류와 경고는 `ImportValidationError`의 `severity`, `row_id`, `row_no`를 기준으로 rows와 연결한다.

## PASTE와 EXCEL_FILE 공통화

- `PASTE`는 현재 구현된 rows 저장과 validation 흐름을 사용한다.
- `EXCEL_FILE`은 후속 파일 업로드 skeleton에서 같은 `import_job`, rows, validation, errors 구조로 연결한다.
- preview 결과 grid와 오류 패널은 source_type이 달라도 재사용해야 한다.
- 파일 업로드 UI와 validation 결과 UI를 분리한다.

## API 응답 기준

- API path를 추정하지 않는다.
- 응답 필드를 프론트에서 억지로 추정하지 않는다.
- 부족하거나 애매한 필드는 “API 응답 보강 필요”로 분리 보고한다.
- 실제 secret, token, password, password_hash를 화면이나 console에 출력하지 않는다.

## 함께 읽을 문서

- `docs/import-preview-screen-contract-draft-2026-05-29.md`
- `docs/import-preview-screen-skeleton-closeout-2026-05-29.md`
- `docs/import-validation-api-manual-verification-closeout-2026-05-29.md`
- `docs/frontend-app-scaffold-plan-2026-05-29.md`

## Smart Import Mapper 4차 매핑 규칙

- 자동매핑은 자동 저장이 아니라 추천이다. 저장 전에는 검증, 미리보기, 사용자 확정, backend final safety check를 반드시 거친다.
- 매핑 추천은 `ALIAS`, `PROFILE`, `DECISION_HISTORY`, `RULE` provider를 합산해 판단한다. `FUTURE_AI` provider는 후속 확장 자리로만 둔다.
- 필드별 판정은 `AUTO_APPLY`, `NEEDS_REVIEW`, `LOW_CONFIDENCE`, `BLOCKED`로 구분한다.
- `AUTO_APPLY`라도 사용자가 수정할 수 있어야 하며, `NEEDS_REVIEW`와 `LOW_CONFIDENCE`는 사용자가 확인하기 전 확정 저장하지 않는다.
- 필수 필드 미매핑, 위험 필드 충돌, 중복 후보, 과거 `REJECTED` 이력은 자동적용을 금지한다.
- 사용자가 수정/확정/거절한 매핑은 decision 이력으로 저장하되, 개인정보나 원본 row 전체를 저장하지 않는다.
- 다음 업로드에서는 같은 고객사, source type, header signature, decision 이력을 우선 참고하되 양식이 달라지면 확인필요로 낮춘다.
- frontend가 실수로 확정 요청을 보내도 backend confirm 단계에서 mapping safety를 다시 검사해 차단해야 한다.
