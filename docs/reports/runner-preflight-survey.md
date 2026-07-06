# 러너 구현 착수 전 선행조사 보고서

- 작업 성격: 러너 구현 착수 전 미확정 항목 실물 조사
- 위험도: R1 읽기 전용 선행조사
- 작성 기준: 저장소 코드, 설정, DB는 변경하지 않고 본 보고서만 작성
- 주의: secret/key/token/password/password_hash 값은 취득하거나 기록하지 않음

## 1. 코덱 비대화형(headless) 실행 방법

### 확인한 사실

- `codex` CLI가 현재 환경에서 감지되었다.
- `codex --help` 기준으로 `exec` 하위 명령이 있으며, 설명은 비대화형 실행이다.
- `codex exec --help` 기준으로 지시문 입력과 결과 파일 저장에 필요한 옵션이 존재한다.
  - `[PROMPT]`를 생략하거나 `-`를 사용하면 stdin에서 지시문을 읽는다.
  - `-C, --cd <DIR>`로 작업 루트를 지정할 수 있다.
  - `-s, --sandbox <SANDBOX_MODE>`로 `read-only`, `workspace-write`, `danger-full-access`를 지정할 수 있다.
  - `-a, --ask-for-approval <APPROVAL_POLICY>`로 승인 정책을 지정할 수 있다.
  - `--json`으로 JSONL 이벤트를 stdout에 출력할 수 있다.
  - `-o, --output-last-message <FILE>`로 마지막 응답을 파일에 저장할 수 있다.
- 지시문 파일을 입력으로 주고 결과를 파일로 받는 형태는 도움말 기준 아래 방식으로 구성 가능하다.

```powershell
Get-Content <instruction.md> -Raw | codex exec -C <repo-root> --sandbox read-only --ask-for-approval never -o <result.md> -
```

### 확인 못함

- 없음. 단, 실제 모델 호출은 수행하지 않았고 이번 항목은 설치된 CLI 도움말의 명령·플래그 확인으로 한정했다.

## 2. 클코 비대화형(headless) 실행 방법

### 확인한 사실

- `claude` CLI가 현재 환경에서 감지되었다.
- `claude --help` 기준으로 `-p, --print` 옵션이 비대화형 출력 모드다.
- `--input-format <format>`은 `--print`와 함께 사용하며 `text`, `stream-json`을 지원한다.
- `--output-format <format>`은 `--print`와 함께 사용하며 `text`, `json`, `stream-json`을 지원한다.
- `--permission-mode <mode>`로 권한 모드를 지정할 수 있다.
- `--no-session-persistence`는 `--print`와 함께 사용할 수 있다.
- CLI 자체의 전용 output-file 옵션은 확인되지 않았으나, stdout redirection으로 결과 파일 저장은 구성 가능하다.
- 지시문 파일을 입력으로 주고 결과를 파일로 받는 형태는 도움말 기준 아래 방식으로 구성 가능하다.

```powershell
Get-Content <instruction.md> -Raw | claude -p --input-format text --output-format text --permission-mode dontAsk > <result.txt>
```

### 확인 못함

- 없음. 단, 실제 모델 호출은 수행하지 않았고 이번 항목은 설치된 CLI 도움말의 명령·플래그 확인으로 한정했다.

## 3. 인증·과금 방식

### 확인한 사실

- `codex login --help` 기준으로 Codex CLI는 다음 인증 방식을 지원한다.
  - `login status`
  - `--with-api-key`: stdin으로 API key 입력
  - `--with-access-token`: stdin으로 access token 입력
  - `--device-auth`
- `claude auth --help` 기준으로 Claude CLI는 `auth login`, `auth logout`, `auth status`를 제공한다.
- `claude --help` 기준으로 `setup-token`은 Claude subscription이 필요하다고 표시된다.
- `claude --help` 기준으로 `--bare` 모드에서는 `ANTHROPIC_API_KEY` 또는 `apiKeyHelper` 설정 방식만 사용한다고 표시된다.

### 확인 못함

- 현재 환경의 Codex가 구독 기반 로그인으로 동작하는지, 별도 API key/access token 기반인지 실제 현재 인증 상태는 확인하지 않았다.
- 현재 환경의 Claude Code가 구독 기반 로그인으로 동작하는지, 별도 API key 기반인지 실제 현재 인증 상태는 확인하지 않았다.

## 4. 자동 빨강게이트 스위트 실재

### 확인한 사실

| 항목 | 확인 결과 | 확인 경로 |
|---|---|---|
| 테넌트 격리 회귀 | 분산 테스트와 감사 문서는 있음. 단일 `red gate` 실행 스위트는 확인되지 않음 | `backend/tests/test_auth_context.py`, `backend/tests/test_permissions.py`, `backend/tests/test_master_api_readonly.py`, `backend/tests/test_return_intake_api.py`, `backend/tests/test_channel_api.py`, `docs/reports/tenant-isolation-audit.md`, `docs/reports/return-writeflow-tenancy-audit.md` |
| 정산 불변식(D2) | 없음(구축 선행 필요) | `backend/tests/test_db_models_import.py`의 모델 import 확인 외 실행 테스트 없음. 정산 관련 내용은 주로 `docs/specs/`, `docs/business/`, `docs/reports/` 문서에 존재 |
| 권한 fail-closed | 분산 테스트는 있음. 단일 `red gate` 실행 스위트는 확인되지 않음 | `backend/tests/test_permissions.py`, `backend/tests/test_auth_error_responses.py`, `backend/tests/test_seed_roles_permissions.py`, `backend/tests/test_return_intake_api.py`, `backend/tests/test_master_api_manage_warehouses.py`, `backend/tests/test_master_api_readonly.py` |
| 반품 판정·재고 반영 | SPEC-005 관련 테스트 있음 | `backend/tests/test_spec005_return_inventory_apply.py`, `backend/tests/test_return_intake_api.py`, `backend/tests/test_inventory_current_api.py` |
| 음성테스트 | 없음(구축 선행 필요) | `voice/audio/speech/STT/TTS/음성` 검색 기준 실제 음성 기능 테스트 확인 안 됨. `backend/tests/test_inventory_current_api.py`의 `음성` 문자열은 음성 기능이 아니라 주석 문맥으로 보임 |

### 확인 못함

- 없음. 없거나 구축이 필요한 항목은 위 표에 `없음(구축 선행 필요)`로 기록했다.

## 5. 클코 별도 체크아웃 방식

### 확인한 사실

- `git worktree list`가 실행되며 현재 저장소 worktree가 표시된다.
- `git worktree -h` 기준으로 `add`, `list`, `lock`, `move`, `prune`, `remove`, `repair`, `unlock` 하위 명령이 확인된다.
- `claude --help` 기준으로 `-w, --worktree [name]` 옵션이 있으며, 세션용 git worktree 생성 기능으로 설명된다.
- 따라서 별도 체크아웃은 Git worktree와 Claude CLI worktree 옵션을 기준으로 구성 가능하다.

### 확인 못함

- 없음. 단, `git worktree --help`의 전체 manual 출력은 권한 오류가 발생해 `git worktree -h`로 대체 확인했다.

## 6. commit-gate 스크립트 실재

### 확인한 사실

- `tools/git-safe-commit.ps1`은 현재 저장소에 존재하지 않는다.
- 확인 명령은 존재 여부 확인만 수행했고, 스크립트 실행은 하지 않았다.

### 확인 못함

- 없음.

## 조사 명령 요약

- `git status --short`
- `Get-Command codex`
- `codex --help`
- `codex exec --help`
- `codex login --help`
- `Get-Command claude`
- `claude --help`
- `claude auth --help`
- `rg` 기반 테스트·문서 경로 검색
- `git worktree list`
- `git worktree -h`
- `Test-Path tools/git-safe-commit.ps1`

## 요약

- 확인 못함 항목 수: 1개
- 확인 못함 세부:
  1. Codex/Claude의 실제 현재 인증·과금 상태
- `git worktree --help` 전체 manual 출력은 권한 오류로 미확인했으나, `git worktree list`와 `git worktree -h`로 worktree 사용 가능성은 확인했다.
