# SmartReturn Pro Workflow Skill

## 목적

SmartReturn Pro 작업을 시작하고 마감할 때 반복해서 적용할 기본 흐름을 정리한다.

## 작업 전 확인

작업 시작 전 아래를 먼저 확인한다.

1. `git rev-parse --show-toplevel` (현재 저장소 루트 확인)
2. `git branch --show-current` (브랜치 확인)
3. `git remote -v` (원격 저장소 참고 확인)
4. `git status --short` (변경 파일 확인)
5. `<PROJECT_ROOT>/AGENTS.md` 읽기

필요하면 작업 유형에 맞는 `/docs/skills/*.md`와 관련 `docs` 문서를 추가로 읽는다.

## 중단 조건 요약

아래 조건이면 작업을 시작하지 말고 보고한다.

- `git rev-parse --show-toplevel` 결과가 현재 작업 중인 SmartReturn Pro 저장소 루트가 아니거나, 구버전 SmartReturn 저장소로 보인다. (이번 환경 예시 경로: `C:\smartreturn-pro`)
- `git remote -v`로 확인한 원격 저장소가 SmartReturn Pro 원격이 아닌 것으로 의심된다. (원격 URL은 강제 기준이 아니라 확인 참고용이다.)
- branch가 `smartreturn-pro`가 아니다.
- 기존 SmartReturn 저장소로 보인다.
- `git status --short`가 깨끗해야 하는 작업인데 변경사항이 있다.
- `backend/local.secret.json`, `.env`, `config.json`, 실제 secret/local 파일이 staged 또는 tracked 상태다.
- 실제 secret, token, password, password_hash 값을 읽거나 출력해야만 진행할 수 있다.
- DB schema, migration, seed, 권한 정책 변경이 필요한데 사용자의 명시 지시가 없다.

## 진행 모드 기준

### 플랜모드 성격

바로 구현하지 않고 설계해야 하는 경우:

- 권한 정책, client scope, warehouse scope 판단이 필요한 경우
- DB schema, migration, seed 변경 가능성이 있는 경우
- 화면 구조, 공통 UI, API 계약을 먼저 고정해야 하는 경우
- 정산, 금액, 재고 원장처럼 오류 비용이 큰 정책을 다루는 경우

### 목표추진 성격

완료 조건과 금지 조건이 명확하고 안전한 경우:

- 문서 작성 또는 closeout 마감
- 테스트 실행과 결과 기록
- 이미 설계된 skeleton 구현
- 커밋과 push가 명시된 마감 작업
- secret 파일이 포함되지 않는 단순 문서/코드 변경

### 일반 지시 성격

범위가 작고 단일 작업인 경우:

- 특정 커밋 push
- 특정 명령 결과 확인
- 이미 완료된 작업의 상태 점검

## 주의해야 할 작업

아래는 사용자의 지시 범위와 `AGENTS.md` 기준을 다시 확인한다.

- DB migration
- seed 변경
- DELETE API
- schema 변경
- 권한 정책 변경
- 정산/금액 계산
- 보안 정책 변경
- 대규모 화면 제작 진입
- 운영 데이터 또는 실제 고객사명 fixture 사용

## 완료 보고 공통 항목

완료 보고에는 가능한 한 아래를 포함한다.

- 진행 모드
- 저장소 경로, remote, branch
- 변경 파일 목록
- 구현 또는 문서화 요약
- 테스트/검증 결과
- 미실행 항목과 이유
- secret/token/password/password_hash 미노출 확인
- 민감 파일 staged/tracked 없음 확인
- 최종 `git status --short`
- 커밋/푸시 여부와 커밋 해시
- 다음 추천 작업
