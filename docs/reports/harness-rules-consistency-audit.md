# 하네스·규칙 md 일관성 감사 보고서

[요약]
- 보강 파일은 하위 문서 9개이며, 보강 항목은 10건이다.
- 결정 필요로 남긴 항목은 5건이다.
- AGENTS.md와 CLAUDE.md는 헌법 파일로 보고만 했고 수정하지 않았다.
- 가장 위험한 구멍 Top 3는 SPEC-004 후보 문서의 기본안 표현, 사진 필수 정책의 문서 간 차이, 폐기·제조사반품 재고반영 정책의 과거 문서 잔존이다.
- 똘고리, 작업물 루프, consensus-loop는 현재 기준 문서에서 구분되어 있으며, 템플릿 쪽 누락만 보강했다.
- 끊긴 Markdown 링크와 docs/skills README 인덱스 불일치는 발견하지 못했다.
- 기존 dirty인 `docs/specs/SPEC-004-return-inventory-ledger-contract.md`는 이번 감사 보강과 섞지 않았고 결정 필요 항목으로만 기록했다.

## 감사 범위

- 루트 문서: `AGENTS.md`, `CLAUDE.md`, `README.md`
- 하네스 문서: `ai-harness/**/*.md`
- 프로젝트 문서: `docs/**/*.md`
- 감사 기준: 용어 일관성, 규칙 구멍, 문서 간 모순, Pro/legacy 혼입, 끊긴 참조, 반품 업무정책 일관성

## 보강 완료

1. [문구·일관성] `ai-harness/templates/instruction.md:25`, `:35`, `:43`
   - before: 일반 지시문 템플릿에 정상 dirty 예상, 똘고리 판정, 표준 secret/local/settings 안전라인이 빠져 있었다.
   - after: 정상 dirty 예상, 5택1 똘고리 판정, secret/local/settings/API key/token/password/password_hash 출력 금지, 3회 반복·범위이탈·예상 외 dirty 중단조건을 추가했다.

2. [문구·일관성] `ai-harness/templates/instruction.md:46`
   - before: `git add .`, `git add -A`, 무단 commit/push 금지가 일반 템플릿 필수요소로 고정되어 있지 않았다.
   - after: 일반 지시문 작성 시 해당 금지라인을 반드시 명시하도록 보강했다.

3. [문구·일관성] `ai-harness/templates/joint-worker-instruction-template.md:17`, `:18`, `:27`, `:28`, `:38`
   - before: 공동 작업 카드에 정상 dirty 예상과 똘고리 판정 필드가 없고, 공통 안전라인이 약했다.
   - after: 각 작업 카드에 정상 dirty 예상과 똘고리 판정을 추가하고, secret 출력 금지, 3회 반복 중단, 범위이탈 중단, `git add .`/`git add -A` 금지를 넣었다.

4. [문구·일관성] `ai-harness/templates/goal-instruction-template.md:3`, `:23`, `:33`, `:44`, `:49`
   - before: 실행 대상이 열린 선택지처럼 보일 수 있고, 정상 dirty·중단조건·똘고리 판정이 부족했다.
   - after: 실행 대상은 Claude Code 또는 Codex 중 정확히 하나로 고정하고, 정상 dirty 예상, 안전라인, 3회 반복·범위이탈 중단, 똘고리 판정을 추가했다.

5. [문구·일관성] `ai-harness/dev-team/REQUEST-TEMPLATE.md:17`, `:32`, `:112`, `:115`, `:121`
   - before: 요청 템플릿에 실행대상 단일 지정, 정상 dirty 예상, `git add -A` 금지, password_hash 포함 secret 안전라인, 3회 반복·범위이탈 중단조건이 약했다.
   - after: 실행대상 단일 지정 필드와 정상 dirty 예상 필드를 추가하고, 표준 금지·중단조건을 확장했다.

6. [문구·일관성] `ai-harness/dev-team/REQUEST-TEMPLATE.md:131`, `:139`, `:148`
   - before: 예시 지시문이 실행대상을 항상 명확히 고정한다는 기준을 충분히 보여주지 않았다.
   - after: 예시 지시문에도 실행대상을 정확히 하나로 고정하라는 문구를 보강했다.

7. [문구·일관성] `docs/skills/ai-team-operation.md:15`, `:67`, `:72`, `:75`
   - before: 작업물 루프가 똘고리와 어떻게 다른지, 최종 지시문에 들어가야 할 표준 요소가 한곳에 정리되어 있지 않았다.
   - after: 작업물 루프를 구축물·수정물 실행/재검수 루프로 정의하고, 정상 dirty 예상, 표준 안전라인, 3회 반복·범위이탈 중단, 5택1 똘고리 판정 태그를 지시문 필수요소로 추가했다.

8. [문구·일관성] `ai-harness/loop/README.md:24`, `:43`
   - before: 파일 루프 번호와 AGENTS.md 5게이트의 관계, `[요약/판정]`과 상위 게이트의 관계가 더 분명할 필요가 있었다.
   - after: 파일 루프 번호는 로컬 기록 순번이며 AGENTS.md 5게이트를 대체하지 않는다고 명시하고, `[요약/판정]`은 상위 게이트 판정을 대체하지 않는다고 보강했다.

9. [문구·일관성] `ai-harness/loop/_template/00-goal.md:3`, `:8`, `:9`, `:10`, `ai-harness/loop/_template/_index.md:6`, `:7`
   - before: 작업물 루프 템플릿에 실행대상 단일 지정, 정상 dirty 예상, 표준 안전·중단라인, 똘고리 판정 기록 필드가 부족했다.
   - after: 실행대상 정확히 하나, 정상 dirty 예상, secret 출력 금지, `git add .`/`git add -A` 금지, 3회 반복·범위이탈 중단, 똘고리 판정 기록 필드를 추가했다.

10. [문구·일관성] `ai-harness/agents/common/spec-writer.md:7`, `:39`
    - before: SmartReturn Pro 전용 spec-writer 문서에 로컬 절대경로가 남아 있었고, `나버클라우드` 오기가 있었다.
    - after: 로컬 절대경로를 `<PROJECT_ROOT>` 기준 표현으로 바꾸고, `네이버클라우드`로 교정했다.

## 결정 필요 — 미보강

1. [구조·결정] SPEC-004 후보 문서의 기본안 표현
   - 근거: `docs/specs/SPEC-004-return-inventory-ledger-contract.md:48`, `:55`, `:64`, `:70`, `:170`, `:185`, `:193`
   - 충돌·갈림길: 감사 결과를 근거로 SPEC을 만들었지만, `기본안`, `유지 대상` 표현이 운영정책을 사실상 확정하는 문구로 읽힐 수 있다.
   - 선택지: A) 모든 운영정책 후보를 `결정 필요`로 낮춘 뒤 재검수한다. B) 현재 기본안을 사용자 승인 대상 정책으로 명시한다.
   - 권고: A. 아직 untracked 문서이므로 별도 보정 지시문에서 결정 필요 표현을 먼저 정리한 뒤 커밋한다.

2. [구조·결정] 사진 필수 정책의 문서 간 차이
   - 근거: `docs/business/return-processing-workflow-ux-design.md:58`, `docs/reports/return-writeflow-tenancy-audit.md:78`, `:80`, `:81`, `:83`
   - 충돌·갈림길: 업무 UX 문서는 고객사 설정에 따라 사진/영상 필수 가능성을 열어두지만, 최신 read-only 감사는 현재 구현에서 사진 필수 강제를 발견하지 못했다고 기록한다.
   - 선택지: A) 사진은 항상 선택으로 확정한다. B) 고객사 설정 기반 필수화를 별도 SPEC으로 다룬다. C) 현재 구현은 선택, 미래 정책은 결정 필요로 분리한다.
   - 권고: C. 구현 변경 없이 현재 상태와 미래 정책 후보를 분리한다.

3. [구조·결정] 폐기·제조사반품 재고반영 정책의 과거 문서 잔존
   - 근거: `docs/specs/SPEC-001-grade-based-inventory-closing.md:48`, `:49`, `:66`, `docs/return-closing-inventory-flow-plan-2026-05-29.md:170`, `docs/reports/return-writeflow-tenancy-audit.md:50`, `:53`
   - 충돌·갈림길: 폐기·제조사반품을 일마감에서 제외하려던 과거/대체 문서 내용과, 최신 감사의 “일마감 사용 확인, 외부반출/폐기 이벤트는 SPEC 필요” 판단이 함께 존재한다.
   - 선택지: A) 과거 문서에 더 강한 폐기/대체 표식을 추가한다. B) 과거 문서를 그대로 두고 최신 SPEC/보고서만 기준으로 삼는다. C) 반품 재고정책 통합 SPEC에서 과거 문서 내용을 흡수·정리한다.
   - 권고: C. 정책 의미가 바뀌는 영역이므로 이번 보강에서는 수정하지 않는다.

4. [구조·결정] legacy 절대경로가 포함된 과거 로컬 에이전트 계획 문서
   - 근거: `docs/local-agent-label-print-integration-plan-2026-05-29.md:22`, `:23`, `:29`, `:30`
   - 충돌·갈림길: AGENTS.md는 현재 하네스 문서에 로컬 절대경로 고정을 금지하지만, 과거 검토 문서는 실제 조사 대상 경로로 `C:\donghyun-logistics-platform`를 남기고 있다.
   - 선택지: A) 과거 조사 기록은 보존한다. B) 과거 문서도 `<LEGACY_ROOT>` 같은 표현으로 정리한다. C) archive/legacy 표식을 추가해 운영 기준 문서와 분리한다.
   - 권고: C. 기록성은 보존하되 운영 기준으로 오인되지 않게 분리하는 편이 안전하다.

5. [구조·결정] read-only 사전감사 실행주체 기준의 명시 수준
   - 근거: `AGENTS.md:106`, `:114`, `:239`, `:275`, `docs/skills/ai-team-operation.md:21`, `:22`, `:41`, `:44`
   - 충돌·갈림길: AGENTS.md와 ai-team-operation은 검증/독립 검수는 Codex 중심, 정책·스펙 검토는 Claude 중심으로 나누지만, “read-only 사전감사”라는 세부 유형을 항상 Codex로 고정할지까지는 헌법 수준에서 완전히 단일 문장으로 고정하지 않는다.
   - 선택지: A) read-only 사전감사는 기본 Codex로 고정한다. B) 정책/스펙 read-only는 Claude, 코드/테스트/커밋 read-only는 Codex로 나눈다. C) 현재처럼 지시문마다 실행대상을 정확히 하나로 지정한다.
   - 권고: C. 현재 운영과 가장 잘 맞고, 이번 보강도 실행대상 단일 지정 원칙을 하위 문서에 추가하는 선에서 마무리했다.

## 추가 확인 결과

- [문구·일관성] Markdown 상대 링크 누락은 발견하지 못했다.
- [문구·일관성] `docs/skills/README.md`에 나열된 skill 문서와 실제 `docs/skills/*.md` 파일의 불일치는 발견하지 못했다.
- [문구·일관성] `CODEX.md`는 실제 파일이 존재해 AGENTS.md의 참조가 끊기지 않았다.
- [문구·일관성] 똘고리와 consensus-loop가 현재 기준 문서에서 같은 개념으로 혼용된 곳은 발견하지 못했다.
- [문구·일관성] current_inventory/inventory_events 즉시 변경 금지와 판정별 warehouse_id 필수 원칙은 AGENTS.md와 최신 감사 문서에서 큰 충돌 없이 유지된다.

## 작업 상태 메모

- 이번 보강은 하위 md 문서만 수정했다.
- `AGENTS.md`와 `CLAUDE.md`는 수정하지 않았다.
- 코드/API/DB/schema/migration/seed 파일은 수정하지 않았다.
- secret/local/settings/API key/token/password/password_hash 값은 출력하지 않았다.
- 기존 untracked `docs/specs/SPEC-004-return-inventory-ledger-contract.md`는 이번 보강과 분리해야 한다.
- commit/push는 하지 않았다.
