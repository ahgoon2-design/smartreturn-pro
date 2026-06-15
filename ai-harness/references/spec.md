# Spec Reference (spec-writer 참조) — SmartReturn Pro

> spec-writer agent가 슬라이스 스펙을 작성할 때 따르는 기준. 상세 책임은 `.claude/agents/spec-writer.md`를 본다.

## 게이트 위치

5게이트 중 ①에 해당한다: `① 스펙 작성 → ② 스펙 승인(사용자) → ③ 구현+빌드 → ④ 검증 → ⑤ 인수·커밋 승인`. 스펙 없는 구현은 시작하지 않는다.

## 파일/번호 규칙

- 템플릿: `docs/specs/_slice-spec-template.md`
- 스펙: `docs/specs/SPEC-NNN-<영문슬러그>.md`
- 빌드 보고서: `docs/reports/SPEC-NNN-build.md`
- 검증 보고서: `docs/reports/SPEC-NNN-verify.md`
- NNN은 `docs/specs` 안 기존 SPEC 최대 번호 +1(세 자리). 구현자가 자동 부여하며 사용자가 직접 정하지 않는다.
- 한 슬라이스의 스펙/빌드/검증 보고서는 같은 NNN을 공유한다.

## 작성 체크리스트

- 템플릿 7개 섹션을 모두 채운다.
- 완료기준은 비개발자가 화면에서 확인할 수 있는 한국말로 쓴다(개발자 용어 금지).
- ⑤"없어야 할 것"에 인접 기능 제외(범위 경계)를 명시한다. 한 슬라이스 = 업무 목적 1개.
- 코드로 확인 안 되는 부분은 ⑦리스크의 "선행 확인 항목"으로 분리한다(추측 금지).
- 기존 자산(route/API/공통 컴포넌트)을 먼저 확인해 ④에 적고 재사용을 우선한다.

## 금지

- 코드 구현, 스펙 파일 외 파일 수정, 테스트 실행, `git add`/`commit`.
- 사용자 스펙 승인 전 구현, 사용자 인수 전 커밋.

## Handoff

- 스펙 초안 → (필요 시) `smartreturn-architect` 구조/중복/권한 검토 → 사용자 승인 → 구현(클코).
