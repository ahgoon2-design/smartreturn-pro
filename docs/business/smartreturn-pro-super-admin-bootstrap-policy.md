# SmartReturn Pro 초기 SUPER_ADMIN bootstrap 정책

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

이 문서는 실제 bootstrap 코드가 아니다. 실제 초기 관리자 계정 생성 구현 전에 보안 기준과 실행 방식을 확정하는 문서다.

## 1. 문서 목적

- SmartReturn Pro 최초 운영 관리자 계정 생성 정책을 문서로 확정한다.
- 초기 `SUPER_ADMIN` 계정 생성 방식, 비밀번호 보안, `must_change_password` 정책을 정리한다.
- 평문 비밀번호가 코드, 문서, 로그, 커밋에 남지 않도록 금지 기준을 고정한다.
- role/permission seed와 사용자 bootstrap의 책임을 분리한다.
- 실제 구현 전 어떤 방식으로 초기 계정을 만들지 후보와 추천안을 정리한다.

## 2. 기본 원칙

- role/permission seed와 사용자 계정 bootstrap은 분리한다.
- role/permission seed는 반복 실행 가능해야 한다.
- `SUPER_ADMIN` bootstrap은 최초 1회 또는 관리자 복구용으로 제한한다.
- 초기 `SUPER_ADMIN` 계정은 필요하지만, 평문 비밀번호를 코드, 문서, 커밋에 남기지 않는다.
- 운영사 관리자는 실제 비밀번호를 조회할 수 없다.
- 비밀번호 초기화/재발급은 가능하지만 조회는 불가능하다.
- 초기 생성 계정은 `must_change_password=true`를 기본값으로 둔다.
- 첫 로그인 후 비밀번호 변경 전에는 일반 업무 API를 사용할 수 없어야 한다.
- 고객사 계정은 P0 bootstrap에서 만들지 않는다.
- 실제 고객사 개인정보를 seed/bootstrap에 넣지 않는다.

## 3. bootstrap 대상

초기 bootstrap 대상은 아래 하나로 제한한다.

- `SUPER_ADMIN` 사용자 1명

후보 필드:

- `login_id`
- `user_name`
- `email`
- `password_hash`
- `must_change_password`
- `active_yn`
- `remarks`
- `created_at`
- `updated_at`

정책:

- `login_id`는 실행 시 입력받거나 환경변수로 주입한다.
- `user_name`도 실행 시 입력받거나 기본값을 사용할 수 있다.
- `email`은 선택값 후보로 둔다.
- `password_hash`만 DB에 저장한다.
- plain password는 DB에 저장하지 않는다.
- plain password는 로그에 출력하지 않는다.
- plain password는 문서에 예시로 쓰지 않는다.
- `client_id`는 기본적으로 비워 둔다. 내부 운영자는 `client_id` 유무가 아니라 role로 판단한다.

## 4. 초기 비밀번호 처리 정책

- 초기 비밀번호는 코드에 하드코딩하지 않는다.
- 초기 비밀번호는 문서에 쓰지 않는다.
- 초기 비밀번호는 Git에 남기지 않는다.
- 초기 비밀번호는 실행 시 콘솔 입력을 받거나 환경변수로 1회 주입한다.
- 환경변수 사용 시 변수명 후보만 문서화하고 값은 쓰지 않는다.
- 비밀번호는 해시 처리 후 저장한다.
- 해시 알고리즘은 후속 구현에서 `passlib`/`bcrypt` 또는 동등한 안전한 방식으로 결정한다.
- 임시 비밀번호를 화면이나 로그에 장기간 남기지 않는다.
- 비밀번호 생성/표시는 후속 관리자 재발급 기능에서 별도 정책으로 다룬다.

환경변수 후보:

- `BOOTSTRAP_ADMIN_LOGIN_ID`
- `BOOTSTRAP_ADMIN_NAME`
- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD`

주의:

- 위 변수명만 문서화하고 실제 값은 쓰지 않는다.
- 환경변수 값을 출력하는 debug log, shell history, CI log가 남지 않도록 후속 구현에서 별도 주의한다.

## 5. bootstrap 실행 방식 후보

### 후보 A: 콘솔 대화형 명령

예:

```powershell
python scripts/bootstrap_super_admin.py
```

실행 중 `login_id`, `name`, `password`를 입력받는다.

장점:

- 비밀번호가 파일에 남지 않는다.
- 로컬/운영에서 수동 통제하기 쉽다.
- 최초 구축 담당자가 실행 시점과 입력값을 확인할 수 있다.

단점:

- 자동화가 어렵다.
- 입력 실수가 있을 수 있다.
- 원격 서버에서 콘솔 접근 권한 관리가 필요하다.

### 후보 B: 환경변수 기반 명령

예:

```powershell
python scripts/bootstrap_super_admin.py
```

실행 전 환경변수로 `login_id`, `password`를 주입한다.

장점:

- 배포 자동화와 궁합이 좋다.
- CI/CD나 서버 초기화에서 쓰기 쉽다.
- 입력 프롬프트가 없는 환경에서도 실행할 수 있다.

단점:

- 환경변수 관리 부주의 시 노출 위험이 있다.
- 로그 출력 금지가 반드시 필요하다.
- shell history, CI variable, 서버 환경변수 관리 기준을 별도로 둬야 한다.

### 후보 C: `seed_p0.py`에 포함

장점:

- 한 번에 seed 실행이 가능하다.
- 실행 순서가 단순해 보인다.

단점:

- role/permission seed와 사용자 생성 책임이 섞인다.
- 평문 비밀번호 처리 위험이 커진다.
- 반복 실행 가능한 seed와 최초 1회성 bootstrap의 idempotency 기준이 충돌할 수 있다.
- 운영/개발 환경 차이에 따라 의도치 않은 관리자 계정 생성 위험이 생긴다.

추천:

- P0에서는 후보 A 또는 후보 B를 사용한다.
- `seed_p0.py`에는 role/permission만 유지한다.
- `SUPER_ADMIN` bootstrap은 별도 스크립트로 분리한다.
- 로컬 개발 초기에는 후보 A를 우선하고, 서버 자동화가 필요해지는 시점에 후보 B를 추가 검토한다.

## 6. idempotency 정책

- 같은 `login_id`가 이미 있으면 중복 생성하지 않는다.
- 이미 `SUPER_ADMIN` 사용자가 존재하면 기본적으로 새로 만들지 않는다.
- 이미 계정이 있는데 `must_change_password`나 `active_yn`만 보정할지 여부는 후속 구현에서 명시적으로 결정한다.
- bootstrap은 실수로 여러 명의 `SUPER_ADMIN`을 만드는 것을 막아야 한다.
- 강제 재생성 옵션은 만들지 않는다.
- 비밀번호 재설정은 별도 관리자 기능 또는 별도 복구 명령으로 분리한다.
- 실패 시 DB transaction을 rollback해야 한다.

후보 결과 코드:

- `CREATED`
- `ALREADY_EXISTS`
- `SUPER_ADMIN_EXISTS`
- `INVALID_INPUT`
- `PASSWORD_POLICY_FAILED`
- `ROLE_NOT_SEEDED`
- `ERROR`

## 7. role/permission seed와의 관계

- bootstrap 실행 전 role/permission seed가 먼저 완료되어야 한다.
- `SUPER_ADMIN` role이 없으면 bootstrap은 중단한다.
- permission seed가 없더라도 role 기반 최소 접근은 가능할 수 있지만, P0 기준에서는 `seed_p0.py` 먼저 실행을 요구한다.
- bootstrap 스크립트가 role/permission seed를 자동으로 실행할지 여부는 후속 구현에서 결정한다.
- 기본 추천은 “`seed_p0.py` 실행 후 `bootstrap_super_admin.py` 실행”이다.
- role/permission seed는 여러 번 실행해도 안전해야 하지만, 사용자 bootstrap은 최초 생성/복구 명령으로 제한한다.

실행 순서 후보:

```powershell
cd backend
python scripts/seed_p0.py
python scripts/bootstrap_super_admin.py
```

## 8. 보안 금지사항

- 평문 비밀번호 코드 하드코딩 금지.
- 평문 비밀번호 README/docs에 기록 금지.
- 평문 비밀번호 로그 출력 금지.
- 평문 비밀번호 DB 저장 금지.
- 초기 관리자 계정 정보를 Git에 남기기 금지.
- 고객사 실제 개인정보를 bootstrap에 사용 금지.
- `SUPER_ADMIN`을 여러 명 자동 생성 금지.
- bootstrap에서 고객사 계정 생성 금지.
- bootstrap에서 `clients`, `products`, `warehouses` seed 생성 금지.
- 운영 DB를 실수로 초기화하는 명령 금지.
- `DROP`/`DELETE` 기반 초기화 금지.
- `seed_p0.py`에 사용자 생성 로직 추가 금지.

## 9. `must_change_password` 정책

- 초기 `SUPER_ADMIN`은 `must_change_password=true`로 생성한다.
- 최초 로그인 후 비밀번호를 변경해야 업무 화면에 접근할 수 있다.
- `must_change_password=true` 상태에서는 비밀번호 변경 API 외 일반 업무 API를 차단한다.
- 비밀번호 변경 성공 후 `must_change_password=false`가 된다.
- 첫 로그인 강제 변경 화면과 일반 비밀번호 변경 모달은 후속 프론트 구현에서 분리한다.
- `must_change_password` 차단은 프론트 화면 제한이 아니라 백엔드 API guard에서 강제해야 한다.

## 10. 감사로그 후보

P0에서 바로 구현하지 않더라도 아래 항목은 후보로 둔다.

- bootstrap 실행 시각
- 실행자 또는 실행 환경
- 생성된 `login_id`
- 성공/실패 결과
- 실패 사유
- 비밀번호 값 제외

정책:

- 비밀번호, secret, token은 감사로그에 남기지 않는다.
- 로그 파일 저장은 후속 정책으로 분리한다.
- 실패 사유는 운영자가 조치할 수 있을 만큼만 남기고, 내부 stack trace를 기본 운영 로그에 노출하지 않는다.

## 11. 후속 구현 순서

1. 비밀번호 해시 유틸 구현
2. `SUPER_ADMIN` bootstrap 스크립트 구현
3. bootstrap 테스트 작성
4. `seed_p0.py`와 bootstrap 실행 순서 문서화
5. `AuthContext` 구현
6. 로그인 API 구현
7. `must_change_password` API guard 구현
8. 관리자 비밀번호 초기화/재발급 기능 구현

## 12. Codex 구현 전 체크

- role/permission seed와 사용자 bootstrap을 분리했는가?
- 초기 `SUPER_ADMIN` 계정을 꼭 1명만 만들도록 설계했는가?
- 평문 비밀번호가 코드/문서/로그/커밋에 남지 않는가?
- `password_hash`만 DB에 저장하는가?
- `must_change_password=true`로 시작하는가?
- `SUPER_ADMIN` role이 없으면 중단하는가?
- 고객사 계정을 bootstrap에서 만들지 않는가?
- 운영 DB를 초기화하는 위험 명령이 없는가?
- 실패 시 rollback되는가?
- 실행 결과에 비밀번호가 출력되지 않는가?
