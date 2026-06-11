# Test Report

## Commands

- `git diff --check`
- `npm --prefix frontend run build` (tsc + vite)
- `python -m pytest tests/test_return_intake_api.py`
- Playwright: `/login` 로그인(ahgoon) → `/returns/processing` 진입 스모크

## Results

- git diff --check: clean (LF→CRLF 경고만).
- frontend build: ✅ 통과 — 3103 modules transformed.
- backend pytest(반품): ✅ **80 passed** (~1:50).
- Playwright 스모크: ✅ ahgoon(SUPER_ADMIN) 로그인 → `/returns/processing` 정상 진입(헤더 "반품 처리 센터", 스캔 패널, 1~5단계 strip, 그리드, 우측 패널). 크래시 없음. 현대화 사이드바 정상.

## Failed

- 없음.

## Not Run / 데이터 의존(수동 확인 필요)

현재 로컬 DB에 처리대기(READY_FOR_PROCESSING) 데이터가 0건이라 아래는 브라우저에서 직접 확인 못 함(데이터 시드 필요). 단, 해당 동작은 backend 테스트로 API 레벨 검증됨:
- 판정 버튼 "불량"(DEFECTIVE)·"리퍼A/B/C" 노출: 판정 패널은 처리대상 선택 시 렌더 → 데이터 필요. (코드/타입/라벨은 build 통과로 확인)
- 엑셀 다운로드 버튼: 그리드 rows > 0일 때만 노출 → 데이터 필요.
- REFURB_A/B/C 외부반출 후보 포함 / legacy REFURB 호환: `test_external_outbound_target_followup_includes_refurb_grades` 통과.
- DEFECTIVE 처리완료(라우팅 有/無): `test_defective_judgement_completes_with_client_warehouse_route`, `test_defective_judgement_blocked_without_warehouse_route` 통과.

## 콘솔 오류 참고

- 로그인 전 콘솔 error는 `favicon.ico 404` 및 미인증 `/api/auth/context` 401(정상 동작)로 앱 버그 아님.

---

## User Browser Test Checklist

> 로컬 서버(backend 8000 / frontend 5173) 구동 + 처리대기 반품 데이터(intake 등록 → 검증 → prepare-processing) 준비 후 확인. DEFECTIVE는 고객사 DEFECTIVE 창고 라우팅 설정 필요.

### A. 반품처리 화면 (`/returns/processing`)
- [ ] 화면 진입
- [ ] 처리대상 선택 시 판정 영역에 `불량` 버튼 노출
- [ ] generic `리퍼` 단일 버튼이 신규 선택지로 없음
- [ ] `리퍼A`, `리퍼B`, `리퍼C` 버튼 노출
- [ ] 그리드에 행이 있을 때 `엑셀 다운로드` 버튼 노출
- [ ] 다운로드 파일에서 운송장/주문/상품코드/바코드가 숫자 깨짐 없이 문자열 보존
- [ ] Ctrl+C 셀 복사 정상
- [ ] 처리완료 전 "재고 미반영" 안내 노출
- [ ] loading state 자연스러움 / 1366x768에서 버튼·그리드 안 밀림

### B. REFURB 외부반출 후보
- [ ] REFURB_A/B/C 판정 데이터가 외부반출 후보(또는 반품 이력 `EXTERNAL_OUTBOUND_TARGET` 필터)에 노출
- [ ] legacy `REFURB` 데이터 있으면 호환 조회
- [ ] GOOD/DISPOSAL/HOLD 오포함 없음

### C. DEFECTIVE 처리
- [ ] 고객사 DEFECTIVE 창고 라우팅 설정 시 처리완료 가능
- [ ] 설정 없으면 "판정별 창고 확정" 차단(정상)
- [ ] 처리완료 후 재고 즉시 반영 없음
- [ ] 외부반출 자동후보 미포함
