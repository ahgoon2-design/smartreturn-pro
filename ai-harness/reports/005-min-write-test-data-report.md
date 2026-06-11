# 005 보고 - 쓰기 흐름용 최소 테스트 데이터 준비

- 실행: Claude Code / ahgoon(SUPER_ADMIN) / 개발 DB / 브랜치 smartreturn-pro
- 준비 수단: 정식 API 흐름(일회성 `tmp/prep_v3write.py`, gitignore). 기존 데이터 미변경.

## 결과: 통과 (PASS)

| 항목 | 값/결과 |
|---|---|
| 테스트 고객사 | `V3WRITE-CLIENT` (client_id=8) — 신규 생성 |
| 테스트 상품 | `V3WRITE-P001` / barcode `8809999100001` |
| 테스트 창고 | `V3WRITE-WH` (warehouse_id=9), RETURN_GOOD 사용설정(is_default) |
| 판정 라우팅 | GOOD / REFURB_A / MANUFACTURER_RETURN → warehouse_id=9 |
| 반품 intake | batch_id=10, 행 2건, 검증 VALID 2건 |
| 처리대기 | task#11 `V3WRITE-RTN-001`, task#12 `V3WRITE-RTN-002` (READY_FOR_PROCESSING, VALID) |

## 필수 확인 항목
- [x] 고객사 선택 가능 / 상품 검색 가능(V3WRITE-P001)
- [x] 창고 라우팅 설정 존재(GOOD/REFURB_A/MANUFACTURER_RETURN)
- [x] 처리대기 row 2건이 `/returns/processing` 표시 가능 상태
- [x] REFURB_A/MANUFACTURER_RETURN 라우팅 존재 → 이후 외부반출 후보 가능
- [x] 식별자 기록(client_id=8, wh=9, batch=10, task 11/12, 운송장 V3WRITE-RTN-001/002)

## 위험 회피
- 기존(비 V3WRITE) 데이터 미변경. 신규 식별자만 사용. 대규모 시드 아님(고객사1·상품1·창고1·반품2).

## 수정 파일
- 없음(앱 코드/문서 변경 없음). 준비 스크립트는 `tmp/`(gitignore).

## 실행 명령
- `backend\.venv\Scripts\python.exe tmp\prep_v3write.py` (login→client→product→warehouse→setting→routes→batch→paste→validate→prepare-processing)

## 다음
- 조건 충족 → `006-processing-write-check.md` 진행. 006 대상: task#12(V3WRITE-RTN-002)를 REFURB_A로 처리완료(외부반출 체인 연결용).
