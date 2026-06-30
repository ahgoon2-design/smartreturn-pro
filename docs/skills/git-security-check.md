---
name: git-security-check
description: >-
  커밋·push·git add·stage·파일 변경·마감 커밋 전에 적용하는 보안 게이트.
  backend/local.secret.json, .env, config.json, *.secret.json, logs/, dist/, build/,
  node_modules 등 민감 파일이 staged/tracked 되지 않았는지와 git diff --check 통과를
  반드시 먼저 검사한다. secret/token/password/password_hash/.env 노출 확인이 필요한 모든
  작업에서 이 스킬을 무조건 먼저 적용한다.
---

# Git Security Check Skill

## 목적

SmartReturn Pro에서 커밋과 push 전에 민감 파일과 생성물이 포함되지 않도록 확인하는 기준이다.

## 커밋 금지 파일

아래 파일 또는 폴더는 staged/tracked 상태가 되면 즉시 중단한다.

- `backend/local.secret.json`
- `.env`
- `config.json`
- 실제 `*.secret.json`
- 실제 `*.local.json`
- `logs/`
- `outputs/`
- `dist/`
- `build/`
- `__pycache__/`
- `node_modules/`
- `*.zip`
- `*.exe`

예외:

- 예시 파일은 허용될 수 있다. 예: `backend/local.secret.example.json`
- 예시 파일에도 실제 secret, token, password 값을 쓰지 않는다.

## 출력 금지

아래 값은 터미널, 문서, 완료 보고, 브라우저 console에 출력하지 않는다.

- 실제 secret
- 실제 token 전체값
- 실제 password
- DB password
- password_hash
- `.env` 내용
- `backend/local.secret.json` 내용

## 기본 확인 명령

커밋 전 확인:

```powershell
git status --short
git diff --check
git diff --cached --name-only
```

tracked 여부 확인 후보:

```powershell
git ls-files backend/local.secret.json .env config.json
```

ignored 여부 확인 후보:

```powershell
git check-ignore -v backend/local.secret.json
```

단, secret 파일 내용은 읽거나 출력하지 않는다.

## 커밋 전 체크리스트

- 작업 범위와 무관한 파일이 staged 되지 않았는가?
- 민감 파일이 staged 되지 않았는가?
- 생성물, 로그, 캐시, 압축파일이 staged 되지 않았는가?
- `git diff --check`가 통과했는가?
- 문서 변경만 있는 작업에서 불필요한 build/test 산출물이 생기지 않았는가?
- 실제 secret/token/password/password_hash 값이 문서나 코드에 들어가지 않았는가?

## push 전 체크리스트

- push 대상 커밋 목록을 확인했는가?
- push 대상 커밋 파일 목록에 금지 파일이 없는가?
- `git status --short`가 기대 상태인가?
- `origin/main..HEAD`가 기대한 커밋만 포함하는가?

## 완료 보고 보안 항목

완료 보고에는 아래를 포함한다.

- 민감 파일 staged/tracked 없음 확인
- `backend/local.secret.json` 미커밋 확인
- secret/token/password/password_hash 미노출 확인
- 최종 `git status --short`
