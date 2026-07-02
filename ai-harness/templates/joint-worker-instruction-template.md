# 병렬 작업 카드 템플릿

서로 다른 작업, 서로 다른 파일/영역, 서로 다른 git worktree 조건을 모두 만족할 때만 사용한다.
같은 작업의 구축/검수/커밋을 한 지시문에서 동시에 열어두지 않는다.

## 공통 목표

작성 예정

## 작업 카드 A

- 실행대상: Claude Code나 Codex 중 정확히 하나를 지정
- 단계: 설계 / 구축 / 검수 / 커밋 중 하나
- 담당 범위:
- 수정 가능 파일:
- 수정 금지 파일:
- 정상 dirty 예상:
- 똘고리 판정:

## 작업 카드 B

- 실행대상: Claude Code나 Codex 중 정확히 하나를 지정
- 단계: 설계 / 구축 / 검수 / 커밋 중 하나
- 담당 범위:
- 수정 가능 파일:
- 수정 금지 파일:
- 정상 dirty 예상:
- 똘고리 판정:

## 공유 규칙

- 모든 경로는 `<PROJECT_ROOT>` 기준
- Karpathy 보강분 A~D 적용 (AGENTS.md 참조)
- 구현자와 최종 검수자는 반드시 다르게 배정
- 커밋은 검수 통과 후 별도 Codex 수문장 단계로 진행
- push는 사용자 별도 승인 후에만 진행
- 보고서는 `ai-harness/workflow/02-agent-report.md`에 작업자별로 작성
- 충돌 가능성이 있으면 중단하고 보고
- 각 작업 카드에는 secret/local/settings/API key/token/password/password_hash 값 출력 금지, 같은 오류/명령 실패 3회 반복 중단, 범위이탈 중단, `git add .`/`git add -A` 금지를 포함한다.
- 각 작업 카드 지시문은 최종 제출 전 `ai-harness/dev-team/SELF-FIX-LOOP.md`의 똘고리 지시문 생성 자가수정루프를 적용하고, 5개 판정 태그 중 하나를 남긴다.
