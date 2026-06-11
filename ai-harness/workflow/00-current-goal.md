# Current Goal

## Goal

`/returns/processing`(반품 처리 센터) 실제 구현 전 gap list 작성. 현재 코드(FE/BE)와 SmartReturn Pro 설계 문서 간 격차를 확정한다. (이번 단계는 분석/계획만, 구현·커밋 없음)

## Mode

플랜모드

## Target Worker

분석: Claude Code 단독 / 후속 구현: Claude Code(프론트) + Codex(백엔드)

## Constraints

- 모든 경로는 `<PROJECT_ROOT>` 기준
- 로컬 절대경로 하드코딩 금지
- secret 출력 금지
- 현재 브랜치 `smartreturn-pro` = SmartReturn Pro 플랫폼 라인. `main` 병합/동기화 제안 금지.

## 결론 요약

`/returns/processing`은 FE(`ReturnProcessingWorkspacePage.tsx`)·BE(`routers/returns.py` + `return_intake_service.py`) 모두 **상당 부분 이미 구현**되어 있고 핵심 설계 원칙(스캔/그리드 이중 처리, 세부항목 없는 반품, 창고 확정 필수, 판정 시점 재고 미반영·일마감 반영, 한글 라벨)에 부합한다. 남은 것은 P1/P2 보완(엑셀 다운로드, 라벨 출력 연동, 판정 enum 정합, 테스트 보강)이다.
