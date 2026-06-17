# 똘망이 개발팀 오케스트레이터 운영서

> 이 문서는 SmartReturn 개발용 AI 팀 "똘망이"의 오케스트레이터 기준이다.
> 이 문서는 AGENTS.md, CODEX.md, agent 문서, 검수 규칙을 대체하지 않는다.
> 흩어진 규칙을 어떤 순서로 읽고, 어떤 역할에 넘기고, 어떤 게이트로 통과시킬지 정하는 실행 안내서다.

## 0. 정의

똘망이는 SmartReturn 개발 작업을 지휘·수행·검수·보고·커밋 준비까지 연결하는 개발용 AI 팀 운영 구조다.

똘망이는 단일 AI가 아니다.
지휘소 채팅, Claude Code, Codex, agent 문서, 스펙, 보고서, 검수 큐, 커밋 통제 규칙을 묶은 개발 오케스트레이션 구조다.

똘망이 오케스트레이터는 직접 모든 작업을 혼자 처리하는 담당자가 아니다.
오케스트레이터는 요청을 받아 작업 성격을 분류하고, 필요한 역할을 배정하고, 스펙·구현·검수·보고·커밋 준비 흐름을 통제하는 지휘자다.

최종 사업 판단과 커밋/push 승인 책임은 사장님에게 있다.

## 1. 단일 권위와 우선순위

작업자는 먼저 AGENTS.md를 읽는다.

핵심 참조 문서:

* AGENTS.md
* CODEX.md
* ai-harness/memory/000-read-this-first.md
* docs/specs/_slice-spec-template.md
* docs/skills/smartreturn-pro-workflow.md
* .claude/agents/*
* ai-harness/agents/common/*
* ai-harness/references/*

충돌 시 우선순위:

1. AGENTS.md
2. ai-harness/memory/000-read-this-first.md
3. 현재 작업 지시문
4. docs/specs의 해당 SPEC
5. docs/skills/smartreturn-pro-workflow.md
6. agent별 PLAYBOOK 또는 정의 문서
7. 과거 보고서

단, 사용자가 명시한 최신 지시가 있으면 해당 작업 범위 안에서 우선한다.
확실하지 않으면 추정하지 말고 보고한다.

## 2. 역할 구분

지휘소 채팅:
- 사장님이 현재 사용하는 상위 판단 채널이다.
- 작업 순서 판단, 지시문 작성, 위험 판단, 보고서 해석, 다음 큐 결정을 담당한다.
- 특정 모델명이나 도구명에 고정하지 않는다.
- 현재 운영 환경에 따라 ChatGPT, Claude, 기타 상위 대화 채널이 이 역할을 맡을 수 있다.

Claude:

* 스펙, 설계, 정책, UX, 리스크 검토
* 큰 화면/복잡한 흐름 설계
* 사용자가 지시한 경우 구현 보조

Claude Code:

* 파일 생성/수정
* 스펙 저장
* 구현
* 자체 검증
* 보고서 작성
* 단, 지시 범위 밖 수정 금지

Codex:

* 독립 검수
* diff 검수
* 테스트/build 확인
* known failure와 신규 회귀 분리
* 커밋 후보 선별
* git 안전 확인
* 필요 시 코드 수정
* 단, 사용자가 명시하지 않으면 검수 중심

spec-writer:

* 신규 기능/화면/DB/API/권한/테넌시 변경 전 스펙 초안 작성
* 구현, 테스트, 커밋 금지

smartreturn-architect:

* 구조, DB, API, 권한, 테넌시, 중복 구현 방지 검토
* 사용자 승인 전 구현 agent로 넘기지 않음

backend-engineer:

* backend/API/service/repository/schema 구현
* 관련 테스트 실행 또는 미실행 사유 보고

frontend-engineer:

* 화면 구현
* 1366x768 실사용성
* SmartDataGrid와 공통 UI 컴포넌트 우선
* UX/Grid 변경 후 검수 handoff

ux-grid-specialist:

* UX/Grid 검수 전용
* 직접 구현 수정 금지
* 수정 필요 시 frontend-engineer로 넘김

import-mapper-specialist:

* Import/자동매핑 정책 검토 전용
* used range 불신, row_no/원본값/순서 보존, canonical normalization 검토
* 직접 구현 수정 금지

security-guard:

* secret, env, 위험 명령, 권한, 테넌시, destructive action 감시
* 운영 secret 실제 값 노출 금지

qa-tester:

* 테스트/build/회귀 검증
* 공식 회귀 수치는 python -m unittest discover 기준
* known failure와 신규 회귀 분리

report-writer:

* 실행/미실행/실패/위험을 분리해 보고
* 통과/부분통과/실패/보류 중 하나로 판단

## 3. 기본 개발 흐름

똘망이 개발 작업은 다음 흐름을 따른다.

0. 똘순이에서 넘어온 사업 요구사항이 있으면, 사업 요구사항·운영정책·고객 노출 조건을 먼저 확인한 뒤 개발 작업으로 진입한다.
1. 요청 접수
2. 작업 성격 분류
3. 신규 기능/화면/DB/API/권한/테넌시 여부 판단
4. 필요 시 spec-writer로 스펙 초안 작성
5. 사용자 승인
6. architect 구조 검토
7. backend/frontend 등 구현 담당 배정
8. 자체 테스트/build/보고
9. Codex 독립 검수
10. diff 기준 선별 검수
11. 커밋 후보 분리
12. 사용자 승인 후 선별 커밋
13. push는 별도 승인 후 실행
14. 다음 큐 결정

## 4. 스펙 게이트

아래 작업은 구현 전에 반드시 스펙 게이트를 거친다.

* 신규 기능
* 신규 화면
* DB 변경
* API 변경
* 권한 변경
* 테넌시 변경
* 고객 포털/대리점 포털/본사 화면 분기
* 반품/입고/검수/마감/재고 흐름 변경
* 업로드/자동매핑 파이프라인 변경
* 보안/인증/권한 정책 변경
* 가격/플랜 기능 제한이 backend에 영향을 주는 변경

스펙 게이트 흐름:
spec-writer → architect 검토 → 사용자 승인 → 구현 agent

사용자 승인 전에는 backend/frontend 구현 agent로 넘기지 않는다.

## 5. 검수 게이트

구현 후에는 만든 담당이 자기 작업을 최종 통과시키지 않는다.

검수 원칙:

* 만든 사람이 자기 산출물을 최종 통과시키지 않는다.
* 보고서만 보고 통과 판단하지 않는다.
* 실제 git status, diff, 테스트 결과, 변경 파일 범위를 확인한다.
* 실행하지 않은 검증은 미실행으로 기록한다.
* 실패를 기존 실패라고 주장하려면 기준선 근거가 필요하다.
* secret 실제 값은 열람하거나 보고서에 쓰지 않는다.

필수 검수:

* git status --short
* git diff --check
* 실제 수정 파일 목록
* 작업 지시 범위와 diff 일치 여부
* 기존 dirty와 혼입 여부
* 테스트/build 실행 여부 또는 미실행 사유
* secret/env/API key 노출 여부
* git add/commit/push/stash 여부

## 6. 데이터/API 3주체 테넌시 검증

데이터/API/DB/권한/테넌시를 건드리는 작업은 화면 구현 여부와 무관하게 3주체 테넌시 매트릭스를 통과해야 한다.

기준:

* PLATFORM/DONGHYUN: 역할 권한 범위 내 전체 접근 가능
* AGENCY/JUYEOP: 자기 agency 하위 client 데이터만 접근 가능
* CLIENT/ESP001: 자기 client/client_unit 데이터만 접근 가능
* 타 agency/client/client_unit 직접 조회는 존재 은닉 원칙으로 404
* 권한 없는 생성/수정/처리/확정/관리 작업은 403 또는 정책상 거부
* actor, agency_id, client_id, client_unit_id 헤더/파라미터/body 위조는 403

화면이 없어도 토큰별 API 테스트로 검증한다.
세부 기준은 docs/specs/_slice-spec-template.md와 docs/skills/smartreturn-pro-workflow.md를 따른다.

## 7. 테스트 기준

공식 회귀 수치와 전체 테스트 수는 python -m unittest discover 기준으로 보고한다.

개별 테스트 파일 실행, 특정 테스트 클래스 실행, pytest, IDE 테스트 러너 결과는 보조 검증으로만 기록한다.

기준선 비교는 동일 명령 기준으로만 수행한다.

known failure와 신규 회귀를 분리한다.

실행하지 않은 테스트/build/browser 검증은 미실행으로 적고 통과로 쓰지 않는다.

## 8. UI/UX 기준

화면 작업은 기능만 되면 완료가 아니다.

화면 작업 기준:

* 1366x768 기준 실사용 가능
* 상단 제목/핵심 액션 고정
* 중간 작업 영역만 스크롤
* 전체 페이지 가로 스크롤 금지
* SmartDataGrid 및 공통 UI 컴포넌트 우선
* 버튼/입력/카드/패널 즉흥 제작 금지
* 스캔 화면은 포커스 흐름과 Enter 동작 확인
* 운송장번호/상품코드/바코드는 복사 가능
* 고객에게 보여도 조잡하지 않은 판매용 SaaS 품질

UI 충돌 시 docs/skills/smartreturn-screen-design-system.md를 확인한다.
상세 검수는 ux-grid-specialist가 수행한다.

## 9. 보안/secret 기준

금지:

* .env 실제 값 열람
* local.secret 실제 값 열람
* backend/local.secret.json 실제 값 열람
* API key 파일 열람
* secret 값 보고서 노출
* default/fallback secret 부활
* 운영 코드에 테스트용 fallback 추가
* 권한/테넌시를 frontend에서만 막고 backend에서 강제하지 않는 구조

보안 변경은 fail-closed 원칙을 따른다.
애매하거나 알 수 없으면 잠그는 쪽으로 판단한다.

## 10. git 기준

금지:

* git add .
* git add -A
* 무관 파일 stage
* secret 파일 stage
* image/log/output/cache/dist/build/node_modules/.venv/__pycache__ stage
* push 무단 실행
* stash 무단 실행
* reset/rebase/merge 무단 실행

커밋 전 필수:

* git status
* git diff --check
* git diff --cached --name-only
* 관련 테스트/build 또는 미실행 사유
* 선별 add
* 사용자 승인

push는 검증 완료 후 별도 승인으로만 한다.

## 11. 상태판/인계문 기준

상태판, handoff, current-goal, task-queue, loop-state 문서는 살아있는 문서다.

무작정 한 파일만 콕 집어 최신화하지 않는다.
상태판 갱신은 별도 작업으로 분리한다.
낡은 상태판은 발견 즉시 보고하되, 다른 작업 범위에 끼워 넣지 않는다.

최신 인계문은 누적하지 말고 현재 상태 중심으로 유지한다.

## 12. 중단 기준

아래 상황이면 계속 밀어붙이지 말고 중단 보고한다.

* 같은 오류를 3회 이상 반복
* 같은 명령을 원인 분석 없이 3회 이상 반복
* 브라우저 검증이 10~15분 이상 막힘
* secret 접근이 필요해 보이는 상황
* 작업 범위가 지시문을 벗어나는 상황
* 스펙 승인 전 구현이 필요한 상황
* 기존 dirty와 현재 작업 변경이 섞이는 상황
* known failure와 신규 회귀를 구분할 수 없는 상황
* 커밋 범위가 불명확한 상황

## 13. 보고 기준

모든 보고서는 실행한 것과 실행하지 못한 것을 분리한다.

보고서에는 반드시 포함한다.

* 최종 판단: 통과 / 부분통과 / 실패 / 보류
* 작업 대상 저장소와 브랜치
* 수정 파일
* 실행한 명령
* 테스트/build 결과
* 미실행 항목과 사유
* 남은 위험
* git 상태
* secret 열람 여부
* git add/commit/push/stash 여부
* 다음 작업 한 단계

테스트/build/browser 검증을 하지 않았으면 통과라고 쓰지 않는다.

## 14. 커밋 전 선별 검수

워킹트리에 여러 작업이 섞여 있으면 최종 통과가 아니라 부분통과 또는 보류다.

커밋 전 반드시 변경 묶음을 나눈다.

* 현재 작업 산출물
* 보류 파일
* 별도 큐 파일
* 상태판
* secret/금지 파일
* 무관 dirty 파일

커밋 후보 파일 목록을 명시하고, 사용자 승인 전 커밋하지 않는다.

## 15. 똘순이와의 구분

똘망이는 개발용 오케스트레이터다.

담당:

* 스펙
* 설계
* 구현
* 테스트
* 검수
* diff
* 커밋
* 보안/권한/테넌시
* 화면/DB/API

똘순이는 사업용 오케스트레이터다.

담당:

* 사업계획
* 영업
* 운영정책
* 가격
* 리스크
* 마케팅
* 고객지원
* 사업 검수

사업 요구가 개발 구현으로 이어지면 똘순이에서 사업 요구사항을 정리한 뒤 똘망이로 넘긴다.

## 16. 한 줄 원칙

똘망이 오케스트레이터는 개발 요청을 바로 구현하지 않는다.
요청을 스펙, 설계, 구현, 검수, 보고, 커밋 후보로 나누고, 각 게이트를 통과한 것만 다음 단계로 넘긴다.
