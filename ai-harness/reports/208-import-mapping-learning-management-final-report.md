# Smart Import Mapper 매핑 학습 관리 최종 보고

## 1. 완료 커밋

- `8a12d0a6`: mapping profile / decision 비활성화 backend API, migration, 테스트
- `a20e7ffa`: 내부 운영자용 매핑 학습 관리 화면

## 2. 최종 완료 범위

- `import_mapping_profiles`에 `deactivated_by`, `deactivated_at`, `deactivate_reason` 컬럼을 추가했다.
- `import_mapping_decisions`에 `active_yn`, `deactivated_by`, `deactivated_at`, `deactivate_reason` 컬럼을 추가했다.
- inactive profile은 `PROFILE` provider 후보에서 제외한다.
- inactive decision은 `DECISION_HISTORY` provider 후보에서 제외한다.
- mapping profile / mapping decision deactivate, activate API를 추가했다.
- mapping decisions 조회 API를 추가했다.
- mapping profiles 조회에 `include_inactive` 옵션을 추가했다.
- `REJECTED` decision 비활성화는 차단한다.
- `SUPER_ADMIN` / `INTERNAL_ADMIN` + `IMPORT_MANAGE`만 매핑 학습 관리 API를 사용할 수 있다.
- `AGENCY_ADMIN` / `CLIENT_ADMIN` / `CLIENT_USER`는 `PERMISSION_DENIED`로 차단한다.
- 물리 삭제 API는 만들지 않고 `active_yn` 기반 soft toggle만 제공한다.
- 기존 `ImportJobRow`, `raw_json`, `normalized_json`, `row_no`는 소급 변경하지 않는다.
- 내부 운영자용 `/imports/mapping-learning` 화면을 추가했다.
- 화면에 매핑 프로필 탭과 결정 이력 탭을 추가했다.
- active/inactive, `import_type`, `source_type`, client, 검색어, 기간 필터를 제공한다.
- 비활성화 사유는 5자 이상 필수로 입력해야 한다.
- 전역 학습 레코드는 비활성화 전 위험 경고를 표시한다.
- `REJECTED` decision은 화면에서 "끌 수 없음"으로 표시한다.
- 고객 포털에는 매핑 학습 관리 화면을 노출하지 않는다.

## 3. 검증 결과 요약

- `pytest learning admin`: 3 passed
- `pytest mapper/reception`: 22 passed
- `pytest import API`: 81 passed
- `alembic heads`: `3d4e5f6a7b80` 단일 head 확인
- `alembic upgrade head`: 로컬 DB 적용 성공
- DB 컬럼 반영 확인:
  - `import_mapping_profiles.deactivated_by`
  - `import_mapping_profiles.deactivated_at`
  - `import_mapping_profiles.deactivate_reason`
  - `import_mapping_decisions.active_yn`
  - `import_mapping_decisions.deactivated_by`
  - `import_mapping_decisions.deactivated_at`
  - `import_mapping_decisions.deactivate_reason`
- `npm.cmd run build`: 통과
- `git diff --check`: 통과
- API route smoke:
  - `/api/import-jobs/mapping-profiles` route 확인
  - `/api/import-jobs/mapping-profiles?include_inactive=true` route 확인
  - `/api/import-jobs/mapping-decisions` route 확인
  - `mapping-decisions`가 `/{job_id}`로 오파싱되어 422가 나는 문제는 해소됨
  - 비인증 요청은 401로 route guard까지 도달함

## 4. 보안/권한 확인

- 내부 운영자만 매핑 학습 관리를 사용할 수 있다.
- 고객 포털에는 매핑 학습 관리 메뉴와 route를 노출하지 않는다.
- `AGENCY_ADMIN`은 1차 정책상 미허용이다.
- `CLIENT_ADMIN` / `CLIENT_USER`는 미허용이다.
- `REJECTED` decision 차단 로직을 유지했다.
- 삭제 API는 없다.
- secret, token, password, API key 원문을 출력하거나 보고서에 포함하지 않았다.
- force push는 하지 않았다.

## 5. 남은 이슈

- 인증 세션 기반 `/imports/mapping-learning` 실브라우저 검수가 필요하다.
- 1366x768 기준 UX 최종 점검이 필요하다.
- audit 로그 공통 테이블 연동은 후속 작업이다.
- `AGENCY_ADMIN` 허용 여부는 후속 정책 판단이 필요하다.
- 최근 자동적용 화면에서 바로 끄기 기능은 후속 작업이다.
- 일괄 비활성화 기능은 후속 작업이다.
- 안전한 테스트 profile / decision 데이터를 사용한 deactivate / activate 브라우저 실동작 확인이 필요하다.

## 6. 다음 추천 큐

- 209: 인증 세션 기반 매핑 학습 관리 화면 브라우저 검수
- 또는 209: 최근 자동적용 화면에서 바로 끄기 UX/API 연결 설계
- 또는 209: 1366x768 내부 운영자 화면 UX 최종 점검
