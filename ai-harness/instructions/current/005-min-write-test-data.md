# 005 - 쓰기 흐름용 최소 테스트 데이터 준비/확인

> 실행 전 `<PROJECT_ROOT>/AGENTS.md`, `CLAUDE.md`를 읽는다. 브랜치 `smartreturn-pro`(SmartReturn Pro 라인) 기준. main 병합/동기화 제안 금지, push 금지. 개발 DB 테스트 데이터만.

## 목표
처리완료 → 일마감 → 외부반출 쓰기 흐름 검증에 필요한 **최소 테스트 데이터와 라우팅 조건**을 확인/준비한다.

## 담당 화면 또는 기능
- 테스트 고객사 / 상품 / 창고 / 판정별 창고 라우팅 / 처리대기 반품 데이터 준비 확인 (기준정보 + 반품 intake)

## 사전 조건
- SUPER_ADMIN(`ahgoon`) 로그인 가능, 서버 5173/8000 가용
- 개발 DB 사용(운영 DB 아님 — 의심 시 중단)
- 기존 테스트 고객사 또는 새 테스트 식별자 사용 가능

## 실행 범위 (1세트만)
- 가능하면 `V3WRITE-` prefix 사용. 최소:
  - 테스트 고객사 1곳(예 `V3WRITE-CLIENT`)
  - 테스트 상품 1~2개(예 `V3WRITE-P001`)
  - 테스트 창고 1~2개
  - GOOD(또는 RETURN_GOOD 사용창고) 또는 REFURB_A 판정 라우팅
  - 외부반출 검증용이면 REFURB_A 또는 MANUFACTURER_RETURN 1건 라우팅
  - 처리대기 반품 1~2건
- 기존 운영성 데이터는 수정하지 않는다. 준비는 정식 API 흐름(+ 일회성 `tmp/` 스크립트)만, 자동화 루프/스크립트 신규 구축 금지.

## 필수 확인 항목
- [ ] 고객사 선택 가능
- [ ] 상품 검색 가능(`V3WRITE-` 상품 조회됨)
- [ ] 창고 라우팅 설정 존재(GOOD/REFURB_A/MANUFACTURER_RETURN 중 필요분)
- [ ] 처리대기 row가 `/returns/processing`에 표시될 상태(READY_FOR_PROCESSING)
- [ ] REFURB_A 또는 MANUFACTURER_RETURN 건이 이후 외부반출 후보가 될 정책 상태
- [ ] 테스트 데이터 식별자(client_id, 상품코드, 운송장, 라우팅 판정코드)가 보고서에 기록됨

## 위험 회피 조건
- 기존(비 `V3WRITE-`) 고객사 실데이터 상태 변경 필요 시 중단
- 대량 데이터 생성 필요 시 중단
- 삭제/초기화 필요 시 중단
- 구조 불명확으로 임의 DB insert가 위험하면 중단(정식 API만 사용)

## 중단 조건
- 서버/DB 10~15분 이상 막힘 → 중단, 수동 준비 필요 보고
- 창고 라우팅 생성 막힘으로 처리완료 전제 불충족 → 사유 기록 후 중단

## 보고 위치
- `ai-harness/reports/005-min-write-test-data-report.md`

## 다음 지시문
- 조건 충족 시 `006-processing-write-check.md`
- 조건 불충족/위험 발생 시 중단(다음으로 넘어가지 않음)
