# Import Preview 화면 Skeleton 구현 마감

## 1. 구현 목적

`docs/import-preview-screen-contract-draft-2026-05-29.md` 계약 초안을 기준으로 import preview 화면 skeleton을 구현했다.

이번 구현은 실사용 완성 화면이 아니라 아래 API 흐름이 프론트에서 연결되는지 확인하기 위한 최소 skeleton이다.

1. `POST /api/import-jobs`
2. `POST /api/import-jobs/{job_id}/rows/paste`
3. `POST /api/import-jobs/{job_id}/validate`
4. `GET /api/import-jobs/{job_id}/rows`
5. `GET /api/import-jobs/{job_id}/errors`

## 2. 구현한 화면/파일 목록

프론트 기존 상태:

- 기존 `frontend`에는 실제 앱 skeleton, `package.json`, 라우팅, 메뉴, API client가 없었다.
- 따라서 기존 화면을 중복 생성하지 않고, `frontend` 아래에 단일 정적 skeleton 앱을 추가했다.
- 외부 패키지 설치 없이 `node`만으로 build 확인이 가능하게 구성했다.

추가 파일:

- `frontend/package.json`
- `frontend/index.html`
- `frontend/scripts/build.mjs`
- `frontend/src/app.js`
- `frontend/src/lib/apiClient.js`
- `frontend/src/api/master.js`
- `frontend/src/api/importJobs.js`
- `frontend/src/screens/importPreviewScreen.js`
- `frontend/src/styles.css`

문서:

- `docs/import-preview-screen-skeleton-closeout-2026-05-29.md`
- `docs/smartreturn-pro-doc-index.md`

## 3. 연결한 API 목록

고객사 조회:

- `GET /api/master/clients`

import job:

- `POST /api/import-jobs`
- `POST /api/import-jobs/{job_id}/rows/paste`
- `POST /api/import-jobs/{job_id}/validate`
- `GET /api/import-jobs/{job_id}/rows?page=1&page_size=200`
- `GET /api/import-jobs/{job_id}/errors?page=1&page_size=200`

## 4. 구현한 화면 구성

상단:

- API 서버 주소 입력
- 고객사 선택
- `import_type` 선택
- `source_type` 선택
- 현재 job status 표시

입력 영역:

- paste 입력 textarea
- 붙여넣기 초기화
- 미리보기/행 저장
- 검증 실행

요약 영역:

- 전체 행
- 정상 행
- 경고 행
- 오류 행
- 오류 발생 행
- 진행률
- job status
- import_type
- source_type

grid 영역:

- 행번호
- validation_status
- 오류/경고 수
- `product_code`
- `product_name`
- `barcode`
- `barcode_type`
- `unit_qty`
- 처리 메시지

오류/경고 상세:

- severity
- row 번호
- error_code
- error_message

하단:

- 다음 단계 진행 버튼은 skeleton 범위에서 비활성 상태로 표시한다.

## 5. 상태/필터/요약 표시

validation_status 표시:

- `VALID`: 정상
- `WARNING`: 경고
- `INVALID`: 오류
- `NOT_VALIDATED`: 검증 전

job status 표시:

- `DRAFT`: 작성 중
- `READY_TO_VALIDATE`: 검증 대기
- `VALIDATING`: 검증 중
- `VALIDATED`: 검증 완료
- `HAS_ERRORS`: 오류 있음
- `FAILED`: 실패

필터:

- 전체 보기
- 오류 행만 보기
- 경고 행만 보기
- 원본 순서 보기

원본 순서:

- rows 조회 결과는 `row_no asc` 기준으로 다시 정렬해 표시한다.
- 필터를 바꿔도 `row_no` 기준 순서를 유지한다.

## 6. 버튼 활성/비활성 기준

- 고객사, `import_type`, paste 내용, 파싱된 row가 있어야 미리보기/행 저장을 실행할 수 있다.
- rows 저장 전에는 검증 실행 버튼을 비활성화한다.
- `READY_TO_VALIDATE` 상태이고 rows가 1건 이상일 때만 검증 실행을 활성화한다.
- 저장/검증 진행 중에는 중복 클릭을 막는다.
- `VALIDATED` 또는 `HAS_ERRORS` 이후 재검증은 skeleton 화면에서 비활성화한다.
- 다음 단계 진행은 이번 범위에서 비활성 상태다.

## 7. 오류 처리

아래 result_code를 사용자 문구로 변환해 표시한다.

- `NOT_AUTHENTICATED`
- `INVALID_TOKEN`
- `IMPORT_JOB_NOT_FOUND`
- `IMPORT_JOB_VALIDATE_ALREADY_DONE`
- `IMPORT_JOB_VALIDATE_FORCE_UNSUPPORTED`
- `IMPORT_JOB_VALIDATE_SOURCE_TYPE_INVALID`
- `IMPORT_JOB_VALIDATE_STATUS_INVALID`
- `IMPORT_JOB_VALIDATE_NO_ROWS`
- `API_BASE_URL_REQUIRED`
- 일반 서버 오류

화면과 console에 실제 token, password, secret, password_hash 값을 출력하지 않는다.

## 8. API 응답 필드 부족 여부

이번 skeleton 구현에서 API 응답 부족으로 화면 구현이 막힌 항목은 없었다.

다만 다음 항목은 실사용 화면 전에 보강 여부를 검토할 후보로 남긴다.

- rows response에 row별 ERROR/WARNING count를 직접 포함할지 여부
- job summary/detail에 `warning_rows`를 항상 포함할지 여부
- job detail에 고객사 표시명을 항상 포함할지 여부
- import_type별 grid column metadata를 API로 내려줄지 여부

현재 skeleton에서는 아래 방식으로 처리했다.

- `warning_rows`는 validate response의 `warning_rows`를 우선 사용하고, 없으면 errors를 row 단위로 집계한다.
- row별 오류/경고 수는 errors 조회 결과를 `row_id` 또는 `row_no` 기준으로 프론트에서 집계한다.
- 고객사 표시명은 `GET /api/master/clients` 결과를 사용한다.

## 9. 검증 결과

프론트 build:

```powershell
npm.cmd run build
```

결과:

- `frontend build completed`

브라우저 렌더링:

- 빌드 산출물을 임시 로컬 HTTP 서버로 열어 확인했다.
- `Import Preview Skeleton`
- `미리보기/행 저장`
- `검증 실행`

확인 결과 위 요소가 화면에 렌더링되었다.

참고:

- `file://` 직접 열기는 인앱 브라우저 정책상 차단되어, `http://127.0.0.1` 임시 서버로 확인했다.
- 임시 서버는 검증 후 종료한다.

## 10. 미구현 항목

- 실제 로그인 화면 연동
- 메뉴/라우팅 연결
- React/Vite/TypeScript 전환
- 공통 `SmartDataGrid` 구현
- 파일 업로드 UI
- `EXCEL_FILE` rows 저장
- 다음 단계 진행
- confirm/save API 연동

현재 프론트 기반 앱이 아직 없으므로, 위 항목은 후속 프론트 스캐폴드 또는 공통 UI 구현 시 연결해야 한다.

## 11. 다음 작업 추천

추천 다음 작업은 “프론트 앱 스캐폴드 기준 확정”이다.

이유:

- 현재 `frontend`에는 실제 React/Vite 앱, 라우팅, 메뉴, auth context, 공통 API client가 없다.
- 이번 skeleton은 API 흐름과 표시 계약을 확인하기 위한 단일 정적 화면이다.
- 실사용 화면으로 확장하려면 먼저 프론트 앱 구조, 인증 토큰 보관 위치, 메뉴 라우팅, 공통 grid wrapper 기준을 확정해야 한다.

그 다음 단계로 import preview 화면을 정식 라우트에 연결하고, 필요하면 API 응답 필드 보강을 별도 작업으로 분리한다.
