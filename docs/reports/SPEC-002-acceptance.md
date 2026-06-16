# SPEC-002 화면 인수 보고서

## 1. 인수 개요

- 브랜치: `smartreturn-pro`
- 인수 일시: 2026-06-16
- 대상 화면: 재고현황 `/inventory/current`
- 대상 스펙: `docs/specs/SPEC-002-inventory-status-by-stock-status.md`
- 게이트④ verify: PASS (`docs/reports/SPEC-002-verify.md`)
- 인수 주체: 사장님 + Claude
- 최종 판정: 통과(인수)

## 2. 사장님 육안 확인 4항목

| 확인 항목 | 판정 | 근거 |
| --- | --- | --- |
| 1366x768 밀도/그리드 | OK | 1366x768 기준으로 필터, 합산 안내, 요약, 그리드 핵심 영역이 업무 화면으로 확인 가능하다. |
| 한글 라벨 | OK | 재고상태와 구분이 한글 라벨로 표시되며 `GOOD`, `REFURB_A` 같은 영어 enum이 화면에 그대로 노출되지 않는다. |
| 판매가능·처분대기 구분 | OK | 재고상태별 group label/tone으로 판매가능과 처분대기 계열을 구분해 표시한다. |
| 합산 안내 문구 | OK | 창고 미선택 시 창고 전체 합산 보기 안내가 표시되고, 특정 창고 선택 시 특정 창고 보기 안내로 구분된다. |

## 3. Claude 스펙·UX·안전 기준 확인

| 기준 | 판정 | 근거 |
| --- | --- | --- |
| `stock_status` 분리행 | 충족 | 같은 상품도 `stock_status`가 다르면 별도 행으로 표시하는 구현과 테스트가 확인되었다. |
| group label/tone | 충족 | `stockStatus.ts`와 `SmartStatusBadge` 기준으로 상태 표시 정책을 공통화했다. |
| 재고변경 호출 없음 | 충족 | 조회 화면에는 조회, 새로고침, 초기화 중심 동작만 있고 재고 반영/조정/마감 호출을 추가하지 않았다. |
| 조회 전용 안전성 | 충족 | `inventory_events` 생성이나 `current_inventory` 수량 변경 경로와 연결되지 않는다. |

## 4. 게이트④ verify 참조

- 검증 보고서: `docs/reports/SPEC-002-verify.md`
- 게이트④ 판정: PASS
- backend test: `3 passed, 0 failed`
- frontend build: 1차 `spawn EPERM` 실행환경 noise 후 승인 재시도 통과
- 추가 필수 수정: 없음

## 5. 결론

- 판정: 통과(인수)
- 게이트⑤ 인수 완료로 SPEC-002 구현 커밋 가능
- 커밋 포함 대상: SPEC-002 구현 파일 8개 + `SPEC-002-build.md` + `SPEC-002-verify.md` + `SPEC-002-acceptance.md`
- 커밋 제외 대상: 반품 화면 6개, `docs/decisions/tenancy-and-permission-model.md`, `docs/reports/return-spine-status-audit.md`, `spec-002-login-1366x768.png`
