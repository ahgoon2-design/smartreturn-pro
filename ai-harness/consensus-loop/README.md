# SmartReturn Pro consensus-loop

SmartReturn Pro용 지시문 생성 보조 도구다.

사용자는 초안/보고서를 화면 텍스트 박스에 붙여넣고 버튼을 누른다. 프로그램은 API로 지시문을 보강한 뒤 결과 영역에 하나의 `text` 코드블록으로 출력한다. 사용자는 결과를 복사해서 Claude Code, Codex, ChatGPT에 직접 붙여넣는다.

자동 실행, 자동 커밋, 자동 푸시는 하지 않는다. 파일 기반 자동 루프가 주 목적도 아니다.

## GUI 실행

```bash
python consensus_gui.py
```

키 없이 화면 흐름만 확인할 때:

```bash
python consensus_gui.py --mock converge
```

## 3개 핵심 버튼

- 작업지시문 생성
  - 입력: 사용자가 적은 초기 작업 초안
  - 출력: Claude Code 등에 바로 붙여넣을 최종 작업지시문

- 검수지시문 생성
  - 입력: Claude Code 또는 작업자가 작성한 완료보고서
  - 출력: Codex에 바로 붙여넣을 검수지시문

- 최종판단/다음작업 생성
  - 입력: Codex 검수보고서
  - 출력: 최종 판단, 커밋 가능 여부, 커밋 후보/제외, 남은 위험, 다음 작업 초안

모든 결과는 하나의 `text` 코드블록으로 감싼다. 결과 영역의 [복사] 버튼으로 그대로 복사할 수 있다.

## API 키

- `OPENAI_API_KEY` 또는 `ANTHROPIC_API_KEY` 환경변수를 사용한다.
- 화면의 [키 입력]으로 넣은 키는 실행 세션 메모리에만 둔다.
- API 키는 코드, `settings.json`, 로그, 결과 문서에 저장하지 않는다.
- API 호출 실패 시 화면에 안전한 오류 메시지만 표시한다.

## 안전 원칙

- 버튼 1회 클릭은 생성 흐름 1회만 수행한다.
- 무한 반복이나 자동 재호출을 하지 않는다.
- 같은 실패가 3회 반복되면 화면에 중단 경고를 표시한다.
- SmartReturn Pro 기준을 사용하며 SmartReturn 본체 경로와 혼동하지 않는다.
- 생성 지시문에는 `git add .` 금지, 사용자 승인 전 commit/push 금지, secret 출력 금지를 포함한다.

## 기존 CLI 합의 루프

`consensus.py`에는 기존 라운드 기반 합의 루프가 남아 있다. 필요하면 mock으로 로직을 확인할 수 있다.

```bash
python consensus.py draft.md --mock converge
python consensus.py draft.md --mock stubborn
python test_consensus.py
```

CLI 합의 루프는 실행 산출물을 `consensus-runs/` 아래에 만든다. 이 산출물은 커밋하지 않는다.

## 산출물/로컬 파일

커밋 제외:

- `consensus-runs/` 실행 산출물
- `settings.json`
- `build/`
- `dist/`
- `__pycache__/`
- `*.pyc`
- `*.spec`
